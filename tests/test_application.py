# v1.0.0-1
import os
import sys

# Thêm đường dẫn gốc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.application.generate_cam_use_case import GenerateMoldCAMUseCase

def test_pipeline():
    print("--- BẮT ĐẦU TEST TOÀN TRÌNH (PIPELINE) ---")
    
    dummy_cad = "pipeline_test.step"
    output_nc = "pipeline_output.nc"
    
    # Tạo file dummy để pass check `os.path.exists`
    with open(dummy_cad, "w") as f:
        f.write("STEP FILE MOCK")
        
    use_case = GenerateMoldCAMUseCase(cad_filepath=dummy_cad, output_nc_path=output_nc)
    result = use_case.execute()
    
    print("\nKết quả Use Case:")
    print(result)
    
    # Đọc nội dung file NC nếu thành công
    if result.get("status") == "success" and os.path.exists(output_nc):
        print("\n--- G-CODE PREVIEW ---")
        with open(output_nc, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # In 15 dòng đầu tiên
            print("".join(lines[:15]))
            print("...")
            
    # Clean up
    if os.path.exists(dummy_cad): os.remove(dummy_cad)
    if os.path.exists(output_nc): os.remove(output_nc)
    
    print("--- HOÀN THÀNH TEST PIPELINE ---")

if __name__ == "__main__":
    test_pipeline()
