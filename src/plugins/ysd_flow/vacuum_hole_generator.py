import math
from typing import List, Dict, Any, Tuple
from shapely.geometry import Polygon, MultiPolygon, Point

class VacuumHoleGenerator:
    """
    Thuật toán sinh lỗ khoan mồi (Back Ana) dựa trên nguyên tắc:
    1. Xác định vị trí các lỗ hút chân không 0.6mm ở các góc/vách của mặt trước (Front Face).
    2. Chiếu dời (Offset) các vị trí này vào trong 1.5mm để mũi 0.6mm khoan chéo sẽ trúng khoảng không của lỗ mồi.
    3. Không quan tâm mũi D4.2 có vừa khít pocket ở mặt trước hay không, vì nó nằm chìm 2mm dưới đáy pocket.
    """
    def __init__(self, min_clearance: float = 1.0, min_flesh_z: float = 2.0):
        self.allowed_tools = [
            {'d': 4.2, 'max_depth': 60.0},
            {'d': 3.3, 'max_depth': 50.0},
            {'d': 2.2, 'max_depth': 20.0},
        ]
        self.min_flesh_z = min_flesh_z      # Thịt chừa lại ở đáy Z
        self.max_edge_gap = 20.0            # Khoảng cách tối đa rải lỗ dọc vách dài
        self.min_hole_distance = 3.0        # Khoảng cách tối thiểu giữa 2 lỗ khoan mồi
        self.bisector_offset = 1.5          # Khoảng cách dời lỗ mồi vào trong so với vách (để khoan nghiêng)

    def _dist(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def generate_holes_for_pocket(self, poly: Polygon, depth: float, actual_z: float) -> List[Dict[str, Any]]:
        """
        Sinh các vị trí lỗ khoan mồi D4.2 cho pocket.
        Tọa độ sinh ra là tọa độ đã xê dịch (offset) vào trong 1.5mm từ vách.
        """
        if not poly or not poly.is_valid:
            return []

        # 1. Bằng Toán học Hình Thái (Morphology), ta dùng Negative Buffer để vừa tìm góc, vừa tự động dời lỗ vào trong.
        # Các đỉnh của poly.buffer(-1.5) chính là các đỉnh của pocket ban đầu được lùi vào đúng 1.5mm theo đường phân giác!
        zone = None
        used_offset = self.bisector_offset
        
        # Fallback: Nếu pocket quá hẹp (vd: rãnh 2mm), offset -1.5 sẽ bị rỗng.
        # Khi đó ta tự động giảm offset để lấy đường tâm của rãnh.
        for offset_val in [self.bisector_offset, 1.0, 0.5, 0.2]:
            z = poly.buffer(-offset_val)
            if not z.is_empty:
                zone = z
                used_offset = offset_val
                break
                
        if not zone:
            return []

        safe_zone_geoms = []
        if zone.geom_type == 'Polygon':
            safe_zone_geoms = [zone]
        elif zone.geom_type == 'MultiPolygon':
            safe_zone_geoms = list(zone.geoms)

        holes_2d = []
        
        # 2. Trích xuất các góc (đỉnh) và rải lỗ trên cạnh dài
        for sz in safe_zone_geoms:
            holes_2d.extend(self._extract_holes_from_safe_zone(sz))
            
        # 3. Lọc bỏ các lỗ quá gần nhau để tránh khoan trùng
        holes_2d = self._filter_close_holes(holes_2d, min_dist=self.min_hole_distance)

        # 4. Chọn dao (Mặc định dùng D4.2, chỉ hạ cấp nếu độ sâu quá giới hạn)
        valid_tools = [t for t in self.allowed_tools if t['max_depth'] >= depth]
        if not valid_tools:
            valid_tools = [self.allowed_tools[0]]
        best_tool = valid_tools[0]
        
        diameter = best_tool['d']
        drill_depth = depth - self.min_flesh_z

        # Build kết quả
        results = []
        for (x, y) in holes_2d:
            results.append({
                'x': round(x, 3),
                'y': round(y, 3),
                'z': round(actual_z, 3),
                'diameter': diameter,
                'depth': round(drill_depth, 2),
                'hole_type': f'back_drill_{diameter}'
            })
            
        return results

    def _extract_holes_from_safe_zone(self, safe_poly: Polygon) -> List[Tuple[float, float]]:
        """
        Trích xuất vị trí lỗ từ Polygon đã lùi vào (Offset Polygon).
        - Đặt lỗ tại các đỉnh (Corners).
        - Rải lỗ trên các đoạn thẳng dài (Edges).
        """
        pts = list(safe_poly.exterior.coords)
        if not pts:
            return []
            
        if self._dist(pts[0], pts[-1]) < 1e-6:
            pts = pts[:-1]
            
        if len(pts) == 0:
            return []
            
        holes = []
        # Bước 1: Các đỉnh (Corners đã xê dịch)
        for p in pts:
            holes.append((p[0], p[1]))
            
        # Bước 2: Dọc theo các vách dài
        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i + 1) % len(pts)]
            dist = self._dist(p1, p2)
            if dist > self.max_edge_gap:
                segments = int(math.ceil(dist / self.max_edge_gap))
                for j in range(1, segments):
                    ratio = j / float(segments)
                    mx = p1[0] + (p2[0] - p1[0]) * ratio
                    my = p1[1] + (p2[1] - p1[1]) * ratio
                    holes.append((mx, my))
                    
        return holes

    def _filter_close_holes(self, holes: List[Tuple[float, float]], min_dist: float) -> List[Tuple[float, float]]:
        if not holes:
            return []
            
        filtered = []
        for h in holes:
            too_close = False
            for fh in filtered:
                if self._dist(h, fh) < min_dist:
                    too_close = True
                    break
            if not too_close:
                filtered.append(h)
        return filtered
