# v1.0.0-1
import os
import sys

# Thêm đường dẫn gốc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.domain.kinematic_clearance import HandDrillKinematics
from src.domain.edge_traversal import EdgeTraversalLogic

def test_kinematics():
    print("--- BẮT ĐẦU TEST KINEMATIC CLEARANCE ---")
    kinematics = HandDrillKinematics(bit_length=20.0, shank_diameter=6.0, penetration_depth=2.0)
    
    # Test góc nghiêng với vách sâu 25mm
    tilt = kinematics.calculate_tilt_angle(pocket_depth=25.0)
    print(f"1. Với pocket sâu 25mm, mũi khoan dài 20mm, cán 6mm:")
    print(f"   -> Góc nghiêng bắt buộc: {tilt:.2f} độ")
    
    # Test lượng tịnh tiến D4.2
    offset = kinematics.calculate_d42_outward_offset(tilt)
    print(f"   -> Lượng tịnh tiến lùi của tâm D4.2: {offset:.3f} mm")
    
    # Test lấy tọa độ thực tế
    # Giả sử điểm khoan nằm trên vách trái (Normal vector hướng về phía dương của trục X)
    # Tọa độ điểm 0.6: (0, 10, -25)
    # Wall normal: (1.0, 0.0) -> Vector hướng vào lòng khuôn
    edge_pt = (0.0, 10.0, -25.0)
    wall_normal = (1.0, 0.0)
    target = kinematics.get_back_ana_target(edge_pt, wall_normal, 25.0)
    print(f"2. Điểm mép khoan: {edge_pt}, Vector vách: {wall_normal}")
    print(f"   -> Tọa độ tâm D4.2 lý tưởng: ({target[0]:.3f}, {target[1]:.3f}, {target[2]:.3f})")
    # Giải thích kết quả: Vì mũi khoan nghiêng về hướng dương X (để né vách X=0), nó xiên xuống dưới.
    # Nên tâm khoan D4.2 phải chui lùi vào phần âm của trục X.
    print("--- HOÀN THÀNH TEST KINEMATICS ---\n")

def test_edge_traversal():
    print("--- BẮT ĐẦU TEST EDGE TRAVERSAL ---")
    logic = EdgeTraversalLogic(max_edge_gap=30.0)
    
    # Đoạn thẳng ngắn 20mm
    pts_short = logic.generate_points_for_line((0,0,0), (20,0,0))
    print(f"1. Đoạn ngắn (20mm): Trích xuất {len(pts_short)} điểm -> {pts_short}")
    
    # Đoạn thẳng dài 80mm
    pts_long = logic.generate_points_for_line((0,0,0), (80,0,0))
    print(f"2. Đoạn dài (80mm): Trích xuất {len(pts_long)} điểm -> {pts_long}")
    
    print("--- HOÀN THÀNH TEST EDGE TRAVERSAL ---")

if __name__ == "__main__":
    test_kinematics()
    test_edge_traversal()
