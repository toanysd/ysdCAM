import os
import sys
import io

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

import shutil
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import json
from typing import Optional

# Import các Use Case và Layer khác
from src.plugins.ysd_flow.generate_cam_use_case import GenerateMoldCAMUseCase
from src.post_processor.dxf_writer import DrillDXFWriter

app = FastAPI(title="AG-CAM Enterprise Backend", description="Backend xử lý hình học và xuất G-Code cho dự án cam-processing.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_workspace"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "AG-CAM Backend is running."}

@app.post("/api/analyze")
async def analyze_cad(
    file: Optional[UploadFile] = File(None), 
    dxf_file: Optional[UploadFile] = File(None),
    strategy: str = Form("polygon"),
    calc_mode: str = Form("3d_only"),
    tool_radius: float = Form(2.1),
    clearance: float = Form(2.0)
):
    """API Bước 1 & 2: Nhận file CAD/DXF, chạy thuật toán và trả về số lượng lỗ tìm được."""
    filepath = None
    if file and file.filename:
        filepath = os.path.join(TEMP_DIR, file.filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    dxf_filepath = None
    if dxf_file and dxf_file.filename:
        dxf_filepath = os.path.join(TEMP_DIR, dxf_file.filename)
        with open(dxf_filepath, "wb") as buffer:
            shutil.copyfileobj(dxf_file.file, buffer)
        
    # Chạy Use Case (Pipeline) với Strategy được chọn
    output_nc = os.path.join(TEMP_DIR, "output.nc")
    
    if calc_mode == "3d_drill":
        from src.plugins.ysd_flow.generate_drill_cam_use_case import GenerateDrillCAMUseCase
        use_case = GenerateDrillCAMUseCase(
            cad_filepath=filepath,
            output_nc_path=output_nc,
            tool_radius=tool_radius,
            clearance=clearance
        )
    else:
        use_case = GenerateMoldCAMUseCase(
            cad_filepath=filepath, 
            output_nc_path=output_nc, 
            strategy=strategy,
            dxf_filepath=dxf_filepath,
            calc_mode=calc_mode,
            tool_radius=tool_radius,
            clearance=clearance
        )
        
    try:
        result = use_case.execute()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        return {"status": "error", "message": err_msg}
        
    holes_data = result.get("holes", [])
    edges_data = result.get("edges", [])
    
    with open(os.path.join(TEMP_DIR, "holes.json"), "w") as f:
        json.dump({
            "holes": holes_data,
            "edges": edges_data
        }, f)
        
    # Lưu tạm kết quả holes vào UseCase (trong thực tế sẽ lưu database hoặc state)
    # Trả về số lượng và mảng tọa độ lỗ để Frontend vẽ 2D
    return {
        "status": "success", 
        "filename": file.filename, 
        "holes_processed": result.get("holes_processed", 0),
        "holes": holes_data,
        "edges": edges_data,
        "bounding_box": result.get("bounding_box"),
        "message": "Phân tích CAD thành công."
    }

@app.post("/api/export-dxf")
async def export_dxf(origin_x: float = Form(0.0), origin_y: float = Form(0.0)):
    """API xuất file DXF có đường tâm lỗ."""
    dxf_path = os.path.join(TEMP_DIR, "kiem_tra_lo_back_ana.dxf")
    writer = DrillDXFWriter(dxf_path)
    
    # Lấy dữ liệu thật từ file JSON (đã lưu ở bước Analyze)
    holes_file = os.path.join(TEMP_DIR, "holes.json")
    real_holes = []
    real_edges = []
    
    if os.path.exists(holes_file):
        with open(holes_file, "r") as f:
            data = json.load(f)
            # Tương thích ngược: Nếu lưu danh sách lỗ trực tiếp
            if isinstance(data, list):
                real_holes = data
            else:
                real_holes = data.get("holes", [])
                real_edges = data.get("edges", [])
    base_dxf_path = os.path.join(TEMP_DIR, "model_contour.dxf")
    success = writer.export(real_holes, origin=(origin_x, origin_y), edges=real_edges, base_dxf=base_dxf_path)
    if success and os.path.exists(dxf_path):
        return FileResponse(dxf_path, media_type='application/dxf', filename="kiem_tra_lo_back_ana.dxf")
    return {"status": "error", "message": "Lỗi khi tạo DXF."}

@app.post("/api/export-gcode")
async def export_gcode():
    """API xuất mã G-Code CNC."""
    nc_path = os.path.join(TEMP_DIR, "output.nc")
    if os.path.exists(nc_path):
        return FileResponse(nc_path, media_type='text/plain', filename="G83_DRILL_BACK_ANA.nc")
    return {"status": "error", "message": "Chưa có file G-Code được tạo. Vui lòng nạp CAD trước."}

import asyncio
export_lock = asyncio.Lock()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filepath = os.path.join(TEMP_DIR, file.filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return {"status": "success", "message": "File uploaded"}

@app.get("/api/export-3d")
async def export_3d(filename: str):
    """API xuất file STL để hiển thị 3D trên Frontend."""
    from src.core_geometry.cad_reader import StepFileReader
    filepath = os.path.join(TEMP_DIR, filename)
    stl_path = os.path.join(TEMP_DIR, f"{filename}.stl")
    
    if not os.path.exists(filepath):
        return {"status": "error", "message": "File không tồn tại."}
        
    async with export_lock:
        if os.path.exists(stl_path):
            return FileResponse(stl_path, media_type='application/sla', filename=f"{filename}.stl")
            
        reader = StepFileReader(filepath)
        if reader.load() and reader.export_stl(stl_path):
            return FileResponse(stl_path, media_type='application/sla', filename=f"{filename}.stl")
        
    return {"status": "error", "message": "Lỗi khi tạo file STL hoặc bạn đang chạy Mock Mode."}

if __name__ == "__main__":
    uvicorn.run("src.presentation.api:app", host="127.0.0.1", port=8888, reload=True)
