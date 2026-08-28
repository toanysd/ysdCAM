import math
from typing import List, Dict, Tuple

class GeometricHeuristics:
    @staticmethod
    def check_draft_angles(cad_faces: list, min_draft_threshold: float = 3.0) -> List[Dict]:
        """
        Quét toàn bộ các mặt trong mô hình CAD để tìm các vách đứng (Vertical Walls).
        Cảnh báo nếu góc vát thoát khuôn (Draft Angle) nhỏ hơn ngưỡng.
        """
        dangerous_faces = []
        try:
            import cadquery as cq
        except ImportError:
            return dangerous_faces

        for face in cad_faces:
            try:
                # Bỏ qua các mặt cong phức tạp
                if face.geomType() != 'PLANE':
                    continue
                
                normal = face.normalAt(face.Center())
                
                # Tính góc với trục Z (0, 0, 1)
                # dot product = cos(theta)
                z_dot = abs(normal.z)
                # Bắt lỗi domain của acos
                z_dot = min(1.0, max(0.0, z_dot))
                angle_with_z = math.degrees(math.acos(z_dot))
                
                draft_angle = 90.0 - angle_with_z
                
                # Bỏ qua các mặt nằm ngang (đáy pocket, đỉnh khuôn)
                if draft_angle > 85.0:
                    continue
                
                if draft_angle < min_draft_threshold:
                    center = face.Center()
                    dangerous_faces.append({
                        "center": (round(center.x, 2), round(center.y, 2), round(center.z, 2)),
                        "draft_angle": round(draft_angle, 2),
                        "severity": "HIGH" if draft_angle < 1.0 else "MEDIUM"
                    })
            except Exception as e:
                pass
                
        return dangerous_faces

    @staticmethod
    def calculate_stretching_ratio(face_obj) -> Tuple[float, float]:
        """
        Ước lượng độ dãn màng (Stretching Ratio) của một pocket.
        Tỷ lệ = Diện tích bề mặt 3D / Diện tích miệng pocket (2D Projected).
        Lưu ý: face_obj ở đây là mặt đáy (Bottom Face). Chúng ta có thể lấy Area của nó làm Area_2D_Opening (tạm xấp xỉ).
        Trong thực tế, nên quét các vách đứng xung quanh face_obj này.
        Ở đây, ta giả lập việc tính toán bằng cách đo chiều dài chu vi x chiều sâu (Depth).
        """
        try:
            # Ước lượng Diện tích 2D (Đáy pocket)
            area_2d = face_obj.Area()
            if area_2d < 0.1:
                return 1.0, 1.0
                
            # Khảo sát chu vi (Perimeter)
            perimeter = 0.0
            for w in face_obj.Wires():
                perimeter += w.Length()
                
            # Giả định chiều sâu pocket bằng 5.0mm nếu không có dữ liệu vách
            # Lý tưởng nhất là lấy từ `calculated_depth` ở use case
            pocket_depth = 5.0 
            
            # Ước lượng Diện tích 3D: Mặt đáy + Diện tích các vách (Chu vi * Độ sâu)
            area_3d = area_2d + (perimeter * pocket_depth)
            
            stretch_ratio = area_3d / area_2d
            
            # Tính hệ số nhân mật độ lỗ: ratio = 1 -> 1.0x, ratio > 2.5 -> 1.5x
            density_multiplier = min(1.5, max(1.0, stretch_ratio * 0.5))
            
            return round(stretch_ratio, 2), round(density_multiplier, 2)
            
        except Exception:
            return 1.0, 1.0

    @staticmethod
    def detect_trapped_air_zones(wire_edges_data: list, angle_threshold: float = 75.0) -> List[Dict]:
        """
        Tìm các góc kẹt khí (Trapped-Air Corners) bằng cách quét các cạnh liên tiếp 
        có góc gập nhỏ hơn angle_threshold (ví dụ: < 75 độ).
        """
        priority_zones = []
        if not wire_edges_data or len(wire_edges_data) < 3:
            return priority_zones
            
        n_edges = len(wire_edges_data)
        for i in range(n_edges):
            e1 = wire_edges_data[i]
            e2 = wire_edges_data[(i + 1) % n_edges]
            
            # Cần đảm bảo điểm nối tiếp nhau. (e1.end == e2.start)
            # Tính vector
            v1_x = e1['end'][0] - e1['start'][0]
            v1_y = e1['end'][1] - e1['start'][1]
            
            v2_x = e2['end'][0] - e2['start'][0]
            v2_y = e2['end'][1] - e2['start'][1]
            
            # Chuyển v1 thành hướng từ giao điểm đi ra (đảo chiều)
            u_x, u_y = -v1_x, -v1_y
            w_x, w_y = v2_x, v2_y
            
            len_u = math.hypot(u_x, u_y)
            len_w = math.hypot(w_x, w_y)
            
            if len_u < 0.001 or len_w < 0.001:
                continue
                
            dot_val = (u_x * w_x + u_y * w_y) / (len_u * len_w)
            dot_val = min(1.0, max(-1.0, dot_val))
            
            angle_deg = math.degrees(math.acos(dot_val))
            
            # Góc trong (internal angle) 
            if angle_deg < angle_threshold:
                priority_zones.append({
                    "x": round(e1['end'][0], 3),
                    "y": round(e1['end'][1], 3),
                    "type": "sharp_corner",
                    "angle": round(angle_deg, 1)
                })
                
        return priority_zones

    @staticmethod
    def detect_chamfers_and_fillets(cad_faces: list) -> Dict[str, List[Dict]]:
        """
        Nhận diện cơ bản các mặt vát (Chamfer) và bo tròn (Fillet) trong mô hình 3D.
        Trả về một dictionary chứa hai danh sách: 'chamfers' và 'fillets'.
        """
        results = {
            "chamfers": [],
            "fillets": []
        }
        
        try:
            import cadquery as cq
        except ImportError:
            return results

        for face in cad_faces:
            try:
                geom_type = face.geomType()
                
                # 1. Nhận diện Fillet (Mặt cong như Cylinder, Torus, B-Spline)
                if geom_type in ['CYLINDER', 'TORUS', 'BSPLINE', 'SURFACE_OF_REVOLUTION']:
                    center = face.Center()
                    results["fillets"].append({
                        "center": (round(center.x, 2), round(center.y, 2), round(center.z, 2)),
                        "type": geom_type
                    })
                    continue
                
                # 2. Nhận diện Chamfer (Mặt phẳng nghiêng)
                if geom_type == 'PLANE':
                    normal = face.normalAt(face.Center())
                    z_dot = abs(normal.z)
                    
                    # Nếu z_dot gần bằng 1 (mặt ngang) hoặc gần bằng 0 (mặt đứng thẳng), bỏ qua
                    if z_dot > 0.98 or z_dot < 0.05:
                        continue
                        
                    # Tính góc vát so với phương thẳng đứng
                    z_dot = min(1.0, max(0.0, z_dot))
                    import math
                    angle_with_z = math.degrees(math.acos(z_dot))
                    draft_angle = 90.0 - angle_with_z
                    
                    center = face.Center()
                    results["chamfers"].append({
                        "center": (round(center.x, 2), round(center.y, 2), round(center.z, 2)),
                        "draft_angle": round(draft_angle, 2),
                        "normal": (round(normal.x, 2), round(normal.y, 2), round(normal.z, 2))
                    })
            except Exception as e:
                pass
                
        return results
