# v1.0.0
"""
Module GenerateDrillCAMUseCase - Tầng Application
Luồng xử lý khoan lỗ 3D độc lập với FreeCAD.
- Nhận diện lỗ thông minh (Stepped holes, chamfers) qua HoleFeatureExtractor.
- Phân cụm và tối ưu hóa đường chạy dao (TSP Routing).
- Sinh mã G-Code chuẩn (TopSOLID/Mastercam).
"""
import os
import math
from typing import List, Dict

from src.core_geometry.cad_reader import StepFileReader
from src.post_processor.fanuc_post import FanucPostProcessor
from src.plugins.ysd_flow.hole_feature_extractor import HoleFeatureExtractor

class GenerateDrillCAMUseCase:
    def __init__(self, cad_filepath: str, output_nc_path: str, tool_radius: float = 2.1, clearance: float = 2.0):
        self.cad_filepath = cad_filepath
        self.output_nc_path = output_nc_path
        self.tool_radius = tool_radius
        self.clearance = clearance
        
        self.cad_reader = StepFileReader(self.cad_filepath)
        self.gcode_writer = FanucPostProcessor(self.output_nc_path)
        self.hole_extractor = HoleFeatureExtractor(min_radius=0.5, max_radius=50.0)

    def _optimize_toolpath_tsp(self, holes: List[Dict]) -> List[Dict]:
        """
        Sử dụng thuật toán Nearest Neighbor (TSP Approximation) để tối ưu hóa quãng đường di chuyển.
        """
        if not holes:
            return []
            
        unvisited = holes.copy()
        
        # Tìm điểm bắt đầu gần gốc tọa độ nhất (0,0) hoặc (x_min, y_min)
        # Giả định dao bắt đầu từ một điểm an toàn, ta chọn lỗ có x nhỏ nhất, y nhỏ nhất
        current_node = min(unvisited, key=lambda h: (h['x'], h['y']))
        unvisited.remove(current_node)
        
        optimized_path = [current_node]
        
        while unvisited:
            # Tìm điểm gần nhất với current_node
            next_node = min(unvisited, key=lambda h: math.hypot(h['x'] - current_node['x'], h['y'] - current_node['y']))
            optimized_path.append(next_node)
            unvisited.remove(next_node)
            current_node = next_node
            
        return optimized_path

    def execute(self) -> dict:
        print(f"[DRILL CAM] Bắt đầu phân tích file: {self.cad_filepath}")
        
        if not os.path.exists(self.cad_filepath):
            return {"status": "error", "message": "File CAD không tồn tại."}
            
        # 1. Khởi tạo và đo kích thước phôi
        self.cad_reader.load()
        bbox = self.cad_reader.get_bounding_box()
        safe_z = bbox.get("z_max", 36.0) + 10.0  # Chiều cao an toàn: Đỉnh phôi + 10mm
        
        # 2. Nhận diện các lỗ 3D
        try:
            from src.core_geometry.corner_relief import calculate_corner_reliefs
            
            # 1. Trích xuất lỗ 3D (Cylinders)
            holes = self.hole_extractor.extract_holes_from_step(self.cad_filepath)
            
            # 2. Trích xuất biên dạng 2D và nhận diện góc cần xả
            polygons = self.cad_reader.extract_2d_polygons_with_shapely()
            for poly in polygons:
                corner_holes = calculate_corner_reliefs(
                    polygon=poly,
                    tool_radius=self.tool_radius,
                    clearance=self.clearance,
                    z_top=safe_z - 10.0,
                    z_bot=0.0
                )
                holes.extend(corner_holes)
                
            print(f"[DRILL CAM] Tìm thấy {len(holes)} lỗ khoan (bao gồm lỗ 3D và xả góc).")
        except Exception as e:
            return {"status": "error", "message": f"Lỗi trích xuất lỗ: {e}"}
            
        if not holes:
            return {"status": "success", "message": "Không tìm thấy lỗ khoan nào.", "holes": [], "toolpaths": []}
            
        # 3. Phân loại lỗ theo đường kính (Tool Selection)
        grouped_by_tool = {}
        for h in holes:
            tool_dia = round(h['diameter'], 1)
            if tool_dia not in grouped_by_tool:
                grouped_by_tool[tool_dia] = []
            grouped_by_tool[tool_dia].append(h)
            
        # 4. Tối ưu đường chạy dao cho từng công cụ
        display_toolpaths = []
        for tool_dia, tool_holes in grouped_by_tool.items():
            optimized_holes = self._optimize_toolpath_tsp(tool_holes)
            grouped_by_tool[tool_dia] = optimized_holes
            
            # Lưu dữ liệu toolpath cho hiển thị Web 3D (Three.js)
            pts = []
            for h in optimized_holes:
                pts.append({"x": h['x'], "y": h['y'], "z": safe_z})
                pts.append({"x": h['x'], "y": h['y'], "z": h['z_top']})
                pts.append({"x": h['x'], "y": h['y'], "z": h['z_bot']})
                pts.append({"x": h['x'], "y": h['y'], "z": safe_z})
            display_toolpaths.append({
                "tool": f"D{tool_dia:.1f}",
                "points": pts,
                "hole_count": len(optimized_holes)
            })
            
        # 5. Xuất G-Code
        try:
            self.gcode_writer.generate_program(grouped_by_tool, z_safe=safe_z)
        except Exception as e:
            print(f"[DRILL CAM] Lỗi xuất G-Code: {e}")
            
        # Format lại JSON để trả về cho Frontend
        output_data = {
            "status": "success",
            "message": "Hoàn tất sinh mã NC khoan lỗ.",
            "total_holes": len(holes),
            "tool_groups": {f"D{d:.1f}": len(h) for d, h in grouped_by_tool.items()},
            "safe_z": safe_z,
            "toolpaths": display_toolpaths,
            "holes": holes
        }
        
        return output_data
