# v1.0.0-1
"""
Module KinematicClearance - Tầng Domain
Mô phỏng động học không gian của thao tác khoan thủ công bằng máy mài (Grinder).
Tuyệt đối không phụ thuộc vào thư viện CAD (Chỉ xử lý Toán học lượng giác).
"""
import math

class HandDrillKinematics:
    def __init__(self, bit_length: float = 20.0, shank_diameter: float = 6.0, penetration_depth: float = 2.0):
        """
        Khởi tạo thông số máy khoan cầm tay.
        - bit_length: Chiều dài mũi 0.6mm (mm)
        - shank_diameter: Đường kính cán dao/cổ máy mài (mm)
        - penetration_depth: Lớp thịt nhôm còn lại cần xuyên qua (mm)
        """
        self.bit_length = bit_length
        self.shank_radius = shank_diameter / 2.0
        self.penetration_depth = penetration_depth

    def calculate_tilt_angle(self, pocket_depth: float) -> float:
        """
        Tính toán góc nghiêng (độ) bắt buộc để cán dao không chạm vào thành vách đứng.
        - pocket_depth: Chiều sâu của vách (tính từ mặt phân khuôn xuống đáy)
        """
        if pocket_depth <= 0:
            return 0.0
            
        # Nếu vách nông hơn mũi khoan, về lý thuyết không bị vướng cán dao.
        # Nhưng thực tế công nhân vẫn phải nghiêng nhẹ tay để không cạ mâm cặp (Chuck) vào mép khuôn.
        # Chúng ta giả lập góc nghiêng tiêu chuẩn dựa trên cán dao.
        # Công thức: tan(theta) = Bán kính cán / Chiều dài mũi khoan
        tilt_radians = math.atan(self.shank_radius / self.bit_length)
        return math.degrees(tilt_radians)

    def calculate_d42_outward_offset(self, tilt_angle_deg: float) -> float:
        """
        Tính lượng tịnh tiến vector ngang (Offset ngang) cho tâm lỗ D4.2.
        - tilt_angle_deg: Góc nghiêng của mũi khoan 0.6mm.
        - Output: Khoảng cách (mm) cần dịch lùi tâm D4.2 chui vào bên dưới thành vách.
        """
        if tilt_angle_deg <= 0:
            return 0.0
            
        tilt_radians = math.radians(tilt_angle_deg)
        # Khoảng lệch Delta = Độ sâu xuyên x tan(Góc nghiêng)
        offset = self.penetration_depth * math.tan(tilt_radians)
        return offset

    def get_back_ana_target(self, edge_point: tuple, wall_normal_vector: tuple, pocket_depth: float) -> tuple:
        """
        Tính toán tọa độ X,Y,Z tuyệt đối của tâm lỗ D4.2.
        - edge_point: Tọa độ (X, Y, Z) của điểm trên mép khoan.
        - wall_normal_vector: Vector pháp tuyến của vách hướng VÀO TRONG lòng pocket (Vx, Vy).
        - pocket_depth: Độ sâu pocket.
        """
        theta = self.calculate_tilt_angle(pocket_depth)
        offset_dist = self.calculate_d42_outward_offset(theta)
        
        # Mũi khoan nghiêng né vách -> Tức là tâm dưới cùng bị lệch đi ngược hướng với normal_vector của vách.
        # Do wall_normal_vector là vector hướng từ vách vào lòng khuôn, 
        # ta cần dịch chuyển điểm D4.2 đi SÂU VÀO TRONG VÁCH (ngược hướng normal vector).
        vx, vy = wall_normal_vector
        # Chuẩn hóa vector
        length = math.hypot(vx, vy)
        if length == 0:
            return (edge_point[0], edge_point[1], edge_point[2] - self.penetration_depth)
            
        nvx = vx / length
        nvy = vy / length
        
        target_x = edge_point[0] - (nvx * offset_dist)
        target_y = edge_point[1] - (nvy * offset_dist)
        target_z = edge_point[2] - self.penetration_depth
        
        return (target_x, target_y, target_z)
