# v1.0.0-1
import os
import sys

# Thêm đường dẫn gốc để Python hiểu module src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.cad_reader import StepFileReader
from src.infrastructure.gcode_writer import DrillGCodeWriter

def test_step_file_reader():
    print("--- BẮT ĐẦU TEST CAD READER ---")
    reader = StepFileReader("dummy_file.step")
    
    # Ở chế độ Mock, nó vẫn load thành công dù file không tồn tại thực tế nếu ta bypass bằng try/except hoặc để mock mode chạy.
    # Trong code gốc ta có check os.path.exists, ta sẽ tạo một file rỗng để test.
    with open("dummy_file.step", "w") as f:
        f.write("STEP FILE MOCK")
        
    loaded = reader.load()
    print(f"Trạng thái load file: {loaded}")
    
    if loaded:
        faces = reader.extract_raw_faces()
        print(f"Số lượng mặt (Faces) trích xuất được: {len(faces)}")
        for f in faces:
            print(f" - {f}")
            
    # Clean up
    os.remove("dummy_file.step")
    print("--- HOÀN THÀNH TEST CAD READER ---\n")

def test_gcode_writer():
    print("--- BẮT ĐẦU TEST GCODE WRITER ---")
    output_path = "test_output.nc"
    writer = DrillGCodeWriter(output_path)
    
    # Giả lập 3 tọa độ lỗ Back Ana D4.2
    mock_holes = [
        (15.250, -20.500, -55.000),
        (85.100, -20.500, -55.000),
        (50.000, -80.000, -65.000)
    ]
    
    success = writer.write(mock_holes, tool_no=2, spindle_speed=2500, feed_rate=120, z_safe=5.0, peck_depth=2.5)
    print(f"Trạng thái ghi file NC: {success}")
    
    if success and os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            print("Nội dung G-Code sinh ra:")
            print("========================================")
            print(content)
            print("========================================")
        os.remove(output_path)
        
    print("--- HOÀN THÀNH TEST GCODE WRITER ---")

if __name__ == "__main__":
    test_step_file_reader()
    test_gcode_writer()
