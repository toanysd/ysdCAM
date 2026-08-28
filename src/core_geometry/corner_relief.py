# v1.0.0
"""
Module Corner Relief
Tính toán tọa độ các lỗ khoan góc (dog-bone/T-bone) cho các góc trong (inner corners) của biên dạng hốc (pocket).
Áp dụng tham số bán kính dao (tool_radius) và khoảng hở an toàn (clearance).
"""
import math

def get_angle(p1, p2, p3):
    """
    Tính góc (radians) tại đỉnh p2, cấu tạo bởi 3 điểm p1 -> p2 -> p3.
    """
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    det = v1[0] * v2[1] - v1[1] * v2[0]
    
    # atan2(det, dot) trả về góc có dấu (-pi đến pi)
    angle = math.atan2(det, dot)
    if angle < 0:
        angle += 2 * math.pi
    return angle

def normalize_vector(v):
    length = math.hypot(v[0], v[1])
    if length == 0:
        return (0, 0)
    return (v[0] / length, v[1] / length)

def calculate_corner_reliefs(polygon, tool_radius: float = 2.1, clearance: float = 2.0, z_top: float = 0.0, z_bot: float = -10.0):
    """
    Tìm các góc trong (interior angles) < 180 độ (ví dụ góc vuông 90 độ của hốc)
    và tính toán tọa độ xả dao (corner relief hole).
    
    polygon: shapely.geometry.Polygon
    tool_radius: Bán kính mũi khoan (ví dụ dao 4.2mm -> r=2.1)
    clearance: Khoảng cách an toàn dôi thêm (ví dụ 2.0mm)
    """
    relief_holes = []
    
    # Một Polygon có exterior (viền ngoài) và interiors (các lỗ/hốc rỗng bên trong).
    # Thông thường, "hốc" (pocket) cần phay là phần không gian nằm bên MẶT TRONG của Exterior,
    # hoặc phần KHÔNG GIAN BÊN TRONG của một pocket khép kín (nếu được định nghĩa là Exterior).
    
    # Tùy thuộc vào việc Polygon đại diện cho khối phôi (stock) hay hốc rỗng (pocket):
    # Dễ nhất là ta xét Exterior ring (nếu pocket là một đa giác riêng).
    # Hướng của exterior ring theo Shapely mặc định là CCW (ngược chiều kim đồng hồ).
    # Vậy góc "bên trong" hốc (tức là bên trái của các đoạn) sẽ được tính.
    
    coords = list(polygon.exterior.coords)
    if not coords or len(coords) < 4:
        return relief_holes
        
    # Loại bỏ điểm cuối trùng với điểm đầu
    if coords[0] == coords[-1]:
        coords = coords[:-1]
        
    n = len(coords)
    
    for i in range(n):
        p1 = coords[i - 1]
        p2 = coords[i]
        p3 = coords[(i + 1) % n]
        
        # Vì Exterior ring hướng CCW (vùng lõi nằm bên trái), góc bên trong đa giác sẽ tính bằng:
        # Góc từ (p2->p3) đến (p2->p1) 
        # Sử dụng hàm get_angle(p3, p2, p1) để ra góc trong
        angle_rad = get_angle(p3, p2, p1)
        angle_deg = math.degrees(angle_rad)
        
        # Nếu góc nhỏ hơn 180 độ (ví dụ 90 độ), dao tròn không thể đi sát vào góc nhọn
        # -> Cần xả góc
        if angle_deg < 175: # Ngưỡng để bỏ qua đường thẳng
            # Tính vector phân giác hướng vào bên trong góc
            v1 = normalize_vector((p1[0] - p2[0], p1[1] - p2[1]))
            v2 = normalize_vector((p3[0] - p2[0], p3[1] - p2[1]))
            
            # Vector tổng của v1 + v2 chính là hướng phân giác (bisector) 
            # chia đôi góc nhọn và đi thẳng ra bên ngoài của góc (tức là đi sâu vào trong đa giác)
            bisector = normalize_vector((v1[0] + v2[0], v1[1] + v2[1]))
            
            # Khoảng cách lùi dao = Bán kính dao + Clearance
            # Thường dog-bone fillet sẽ đẩy tâm dao theo đường phân giác một đoạn = r / sin(angle/2)
            # Tuy nhiên, nếu là relief hole tiêu chuẩn để lại clearance:
            # offset_dist = (tool_radius + clearance) / math.sin(angle_rad / 2.0)
            offset_dist = tool_radius + clearance
            
            hole_x = p2[0] + bisector[0] * offset_dist
            hole_y = p2[1] + bisector[1] * offset_dist
            
            relief_holes.append({
                'x': round(hole_x, 3),
                'y': round(hole_y, 3),
                'r': tool_radius,
                'diameter': tool_radius * 2,
                'z_top': z_top,
                'z_bot': z_bot,
                'depth': z_top - z_bot,
                'type': 'corner_relief'
            })
            
    # Lặp lại với các lỗ/cục nằm bên trong (Interiors)
    # Hướng CW -> bên trong pocket là phần bao quanh cục rỗng -> đảo góc.
    for interior in polygon.interiors:
        int_coords = list(interior.coords)
        if int_coords[0] == int_coords[-1]:
            int_coords = int_coords[:-1]
        m = len(int_coords)
        for i in range(m):
            p1 = int_coords[i - 1]
            p2 = int_coords[i]
            p3 = int_coords[(i + 1) % m]
            
            angle_rad = get_angle(p1, p2, p3) # Góc trong của interior ring ngược lại
            angle_deg = math.degrees(angle_rad)
            if angle_deg < 175:
                v1 = normalize_vector((p1[0] - p2[0], p1[1] - p2[1]))
                v2 = normalize_vector((p3[0] - p2[0], p3[1] - p2[1]))
                bisector = normalize_vector((v1[0] + v2[0], v1[1] + v2[1]))
                offset_dist = tool_radius + clearance
                hole_x = p2[0] + bisector[0] * offset_dist
                hole_y = p2[1] + bisector[1] * offset_dist
                
                relief_holes.append({
                    'x': round(hole_x, 3),
                    'y': round(hole_y, 3),
                    'r': tool_radius,
                    'diameter': tool_radius * 2,
                    'z_top': z_top,
                    'z_bot': z_bot,
                    'depth': z_top - z_bot,
                    'type': 'corner_relief'
                })
                
    return relief_holes
