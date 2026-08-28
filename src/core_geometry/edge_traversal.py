# v3.0.0
"""
Module EdgeTraversal - Tầng Domain (Canonical Hole Placement)
Phiên bản 3.0: Thuật toán đáng tin cậy, không phụ thuộc thứ tự Edge của CadQuery.

Quy tắc:
  1. ARC có thành đi lên → 1 lỗ tại đỉnh cung (mid_pt). Nếu cung lớn (chord >= 15mm) → thêm 2 tiếp tuyến.
  2. LINE có thành đi lên → 2 góc + trung điểm nếu L > max_edge_gap.
  3. Sắp xếp theo góc cực (polar angle từ tâm face) để đảm bảo thứ tự nhất quán.
  4. Lọc khoảng cách tối thiểu 5mm giữa các lỗ.
"""
import math
from typing import List, Tuple


class EdgeTraversalLogic:
    def __init__(self, max_edge_gap: float = 25.0, min_hole_clearance: float = 0.8,
                 bisector_offset: float = 1.5):
        self.max_edge_gap = max_edge_gap
        self.min_hole_clearance = min_hole_clearance
        self.bisector_offset = bisector_offset

    def calculate_distance(self, p1: tuple, p2: tuple) -> float:
        return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

    def _polar_angle(self, pt, center) -> float:
        return math.atan2(pt[1] - center[1], pt[0] - center[0])

    def _pull_toward_center(self, pt, face_center, offset=1.5):
        """Kéo điểm vào phía tâm pocket một khoảng offset nhỏ."""
        dx = face_center[0] - pt[0]
        dy = face_center[1] - pt[1]
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return pt
        nx, ny = dx / dist, dy / dist
        z = pt[2] if len(pt) > 2 else 0.0
        return (pt[0] + nx * offset, pt[1] + ny * offset, z)

    def generate_wire_holes(self, wire_edges_data: list, face_center: tuple) -> List[tuple]:
        """
        Tính các vị trí lỗ cho một pocket.

        Thuật toán:
        - Với mỗi edge có has_wall_up=True:
            ARC  → đỉnh cung (+ tiếp tuyến nếu cung lớn)
            LINE → 2 góc + trung điểm nếu dài
        - Kéo mỗi điểm 1.5mm về phía tâm pocket
        - Sắp xếp theo polar angle để nhất quán
        - Lọc khoảng cách tối thiểu 5mm
        """
        if not wire_edges_data:
            return []

        raw_candidates = []

        for edge in wire_edges_data:
            has_wall = edge.get('has_wall_up', True)
            if not has_wall:
                continue

            etype = edge['type']
            start = edge['start']
            end = edge['end']
            mid = edge.get('mid')

            if etype in ('ARC', 'CIRCLE'):
                if mid:
                    # Đỉnh cung - quan trọng nhất
                    raw_candidates.append(mid)
                    chord = self.calculate_distance(start, end)
                    if chord >= 15.0:
                        raw_candidates.append(start)
                        raw_candidates.append(end)
            else:
                # LINE: 2 góc
                raw_candidates.append(start)
                raw_candidates.append(end)
                # Trung điểm nếu cạnh dài
                length = self.calculate_distance(start, end)
                if length > self.max_edge_gap:
                    segments = math.ceil(length / self.max_edge_gap)
                    for i in range(1, segments):
                        ratio = i / segments
                        mx = start[0] + (end[0] - start[0]) * ratio
                        my = start[1] + (end[1] - start[1]) * ratio
                        mz = start[2] + (end[2] - start[2]) * ratio if len(start) > 2 else 0.0
                        raw_candidates.append((mx, my, mz))

        if not raw_candidates:
            return []

        # Kéo mỗi điểm về phía tâm pocket 1.5mm
        pulled = [self._pull_toward_center(p, face_center, self.bisector_offset) for p in raw_candidates]

        # Sắp xếp theo polar angle → nhất quán giữa các pocket cùng hình dạng
        pulled.sort(key=lambda p: self._polar_angle(p, face_center))

        # Lọc khoảng cách tối thiểu 5mm (per-face)
        result = []
        for p in pulled:
            too_close = any(self.calculate_distance(p, q) < 5.0 for q in result)
            if not too_close:
                result.append(p)

        return result

    # ── Legacy methods (kept for compatibility) ─────────────────────────────────
    def generate_points_for_line(self, start_pt: tuple, end_pt: tuple, is_step_down: bool = False) -> List[tuple]:
        if is_step_down:
            return []
        points = [start_pt, end_pt]
        length = self.calculate_distance(start_pt, end_pt)
        if length > self.max_edge_gap:
            segments = math.ceil(length / self.max_edge_gap)
            for i in range(1, segments):
                ratio = i / segments
                mx = start_pt[0] + (end_pt[0] - start_pt[0]) * ratio
                my = start_pt[1] + (end_pt[1] - start_pt[1]) * ratio
                mz = start_pt[2] + (end_pt[2] - start_pt[2]) * ratio if len(start_pt) > 2 else 0.0
                points.append((mx, my, mz))
        return points

    def generate_points_for_arc(self, start_pt: tuple, end_pt: tuple, mid_pt: tuple, is_concave: bool) -> List[tuple]:
        points = [mid_pt]
        if self.calculate_distance(start_pt, end_pt) >= 15.0:
            points.append(start_pt)
            points.append(end_pt)
        return points

    def deduplicate_and_enforce_clearance(self, points: List[tuple]) -> List[tuple]:
        if not points:
            return []
            
        # Ưu tiên các điểm quan trọng: góc, cung tròn, rãnh hẹp
        def get_priority(p):
            t = p[6] if len(p) > 6 else ''
            if t == 'sharp_corner': return 0
            if t == 'corner': return 1
            if t == 'arc': return 2
            if t == 'arc_end': return 3
            if t == 'slot_end': return 4
            if t == 'centroid': return 5
            return 6  # line / gentle_corner
            
        sorted_points = sorted(points, key=get_priority)
        
        valid = []
        for p in sorted_points:
            p_geom = list(p)
            p_dia = p_geom[5] if len(p_geom) > 5 else 4.2
            
            conflict_q_idx = -1
            for i, q in enumerate(valid):
                q_dia = q[5] if len(q) > 5 else 4.2
                # Khoảng cách tối thiểu = (D1/2) + (D2/2) + 0.8 (Khoảng hở tối thiểu)
                required_dist = (p_dia / 2.0) + (q_dia / 2.0) + 0.8
                
                if self.calculate_distance(p_geom, q) < required_dist:
                    conflict_q_idx = i
                    break
                    
            if conflict_q_idx != -1:
                # Có va chạm. Quyết định Merge (gộp) hay Delete (bỏ qua p)
                q_geom = list(valid[conflict_q_idx])
                p_pri = get_priority(p_geom)
                q_pri = get_priority(q_geom)
                
                # Nếu cả 2 đều là điểm hình học quan trọng (corner, arc, slot_end) -> GỘP TỌA ĐỘ để giữ đối xứng
                if p_pri <= 4 and q_pri <= 4:
                    q_geom[0] = (q_geom[0] + p_geom[0]) / 2.0
                    q_geom[1] = (q_geom[1] + p_geom[1]) / 2.0
                    valid[conflict_q_idx] = tuple(q_geom)
                # Nếu p là điểm rải trên cạnh (line, priority > 4), thì p bị XÓA BỎ hoàn toàn để không làm lệch q
            else:
                valid.append(tuple(p_geom))
                
        return valid

    def align_points_with_grid(self, points: List[tuple], snap_distance: float = 12.0) -> List[tuple]:
        if not points:
            return []
            
        # 1. Xác định tọa độ mỏ neo (Anchor points) từ các góc và cung
        anchor_xs = set()
        anchor_ys = set()
        for p in points:
            hole_type = p[6] if len(p) > 6 else ''
            if hole_type != 'line' and hole_type != 'slot_end':
                anchor_xs.add(round(p[0], 2))
                anchor_ys.add(round(p[1], 2))
                
        anchor_xs = sorted(list(anchor_xs))
        anchor_ys = sorted(list(anchor_ys))
        
        aligned_points = []
        for p in points:
            p_geom = list(p)
            hole_type = p_geom[6] if len(p_geom) > 6 else ''
            interior_dir = p_geom[7] if len(p_geom) > 7 else (0.0, 0.0)
            
            # Chỉ gióng cho lỗ nằm trên cạnh dài (line)
            if hole_type == 'line' and interior_dir != (0.0, 0.0):
                # Pháp tuyến hướng Y -> Cạnh NGANG -> Trượt dọc X
                if abs(interior_dir[1]) > 0.8 and anchor_xs:
                    nearest_x = min(anchor_xs, key=lambda x: abs(x - p_geom[0]))
                    if abs(nearest_x - p_geom[0]) <= snap_distance:
                        p_geom[0] = nearest_x
                        
                # Pháp tuyến hướng X -> Cạnh DỌC -> Trượt dọc Y
                elif abs(interior_dir[0]) > 0.8 and anchor_ys:
                    nearest_y = min(anchor_ys, key=lambda y: abs(y - p_geom[1]))
                    if abs(nearest_y - p_geom[1]) <= snap_distance:
                        p_geom[1] = nearest_y
                        
            aligned_points.append(tuple(p_geom))
            
        return aligned_points
