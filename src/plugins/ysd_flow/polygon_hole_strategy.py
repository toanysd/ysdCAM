"""
Module PolygonHoleStrategy - Tầng Domain v8
Chiến lược đặt lỗ hút chân không:
- Truyền trực tiếp `has_wall_up` từ CẠNH TẠO RA LỖ vào kết quả (thay vì tìm cạnh gần nhất bị sai ở các bậc thang hẹp).
- Trả về tuple: (x, y, z, hole_type, is_valid_wall)
"""
import math
from typing import List, Tuple
from shapely.geometry import Polygon, Point

class PolygonHoleStrategy:
    def __init__(self, max_edge_gap: float = 20.0, bisector_offset: float = 1.5, min_segment_len: float = 1.0):
        self.max_edge_gap = max_edge_gap
        self.bisector_offset = bisector_offset
        self.min_segment_len = min_segment_len

    def _normalize(self, vx, vy):
        length = math.hypot(vx, vy)
        if length < 1e-9:
            return (0.0, 0.0)
        return (vx / length, vy / length)
        
    def _dist(self, p1, p2):
        return math.hypot(p1[0]-p2[0], p1[1]-p2[1])

    def _sort_and_orient_edges(self, edges: list) -> list:
        if not edges:
            return []
            
        unvisited = edges.copy()
        sorted_edges = [unvisited.pop(0)]
        
        while unvisited:
            curr_end = sorted_edges[-1]['end']
            found = False
            
            for i, e in enumerate(unvisited):
                if self._dist(curr_end, e['start']) < 0.1:
                    sorted_edges.append(e)
                    unvisited.pop(i)
                    found = True
                    break
                elif self._dist(curr_end, e['end']) < 0.1:
                    rev_e = e.copy()
                    rev_e['start'], rev_e['end'] = e['end'], e['start']
                    if 'sampled_pts' in rev_e and rev_e['sampled_pts']:
                        rev_e['sampled_pts'] = list(reversed(rev_e['sampled_pts']))
                    sorted_edges.append(rev_e)
                    unvisited.pop(i)
                    found = True
                    break
                    
            if not found:
                break
                
        return sorted_edges

    def extract_polygon_from_wire(self, sorted_edges: list) -> Polygon:
        if not sorted_edges or len(sorted_edges) < 3:
            return None
            
        coords = []
        for edge in sorted_edges:
            pt = (edge['start'][0], edge['start'][1])
            if not coords or self._dist(coords[-1], pt) > 0.001:
                coords.append(pt)
            
            if edge.get('sampled_pts'):
                for sp in edge['sampled_pts']:
                    spt = (sp[0], sp[1])
                    if self._dist(coords[-1], spt) > 0.001:
                        coords.append(spt)
                        
        if len(coords) < 3:
            return None
            
        if self._dist(coords[-1], coords[0]) > 0.001:
            coords.append(coords[0])
            
        poly = Polygon(coords)
        if poly.is_valid:
            return poly
        else:
            clean_poly = poly.buffer(0)
            if isinstance(clean_poly, Polygon) and clean_poly.is_valid:
                return clean_poly
        return None

    def _deduplicate_holes(self, holes: List[tuple], min_dist: float = 5.0) -> List[tuple]:
        if not holes:
            return holes
            
        clusters = []
        for h in holes:
            added = False
            for cluster in clusters:
                if math.hypot(h[0] - cluster['x'], h[1] - cluster['y']) < min_dist:
                    cluster['points'].append(h)
                    cluster['x'] = sum(p[0] for p in cluster['points']) / len(cluster['points'])
                    cluster['y'] = sum(p[1] for p in cluster['points']) / len(cluster['points'])
                    added = True
                    break
            if not added:
                clusters.append({
                    'x': h[0], 'y': h[1], 'points': [h]
                })
                
        result = []
        for c in clusters:
            best_h = c['points'][0]
            result.append((c['x'], c['y'], best_h[2], best_h[3], best_h[4], best_h[5], best_h[6]))
            
        return result

    def _get_arc_params(self, edge: dict):
        p1 = edge['start']
        p3 = edge['end']
        p2 = edge.get('mid')
        if not p2:
            pts = edge.get('sampled_pts', [])
            if len(pts) > 0:
                p2 = pts[len(pts)//2]
            else:
                return None
                
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]
        x3, y3 = p3[0], p3[1]
        
        D = 2 * (x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2))
        if abs(D) < 1e-4:
            return None # Collinear
            
        cx = ((x1**2 + y1**2)*(y2 - y3) + (x2**2 + y2**2)*(y3 - y1) + (x3**2 + y3**2)*(y1 - y2)) / D
        cy = ((x1**2 + y1**2)*(x3 - x2) + (x2**2 + y2**2)*(x1 - x3) + (x3**2 + y3**2)*(x2 - x1)) / D
        R = math.hypot(cx - x1, cy - y1)
        
        return (cx, cy, R)

    def _merge_collinear_lines(self, sorted_edges: list) -> list:
        if not sorted_edges: return []
        merged = []
        for edge in sorted_edges:
            if not merged:
                merged.append(edge.copy())
            else:
                last_edge = merged[-1]
                if last_edge['type'] == 'LINE' and edge['type'] == 'LINE':
                    # Check collinearity using cross product
                    dx1 = last_edge['end'][0] - last_edge['start'][0]
                    dy1 = last_edge['end'][1] - last_edge['start'][1]
                    dx2 = edge['end'][0] - edge['start'][0]
                    dy2 = edge['end'][1] - edge['start'][1]
                    
                    cross = dx1 * dy2 - dy1 * dx2
                    l1 = math.hypot(dx1, dy1)
                    l2 = math.hypot(dx2, dy2)
                    
                    if l1 > 1e-5 and l2 > 1e-5 and abs(cross / (l1 * l2)) < 0.02:
                        # Collinear, check if they share an endpoint
                        if self._dist(last_edge['end'], edge['start']) < 0.1:
                            last_edge['end'] = edge['end']
                            if 'sampled_pts' in last_edge and 'sampled_pts' in edge:
                                last_edge['sampled_pts'].extend(edge['sampled_pts'])
                            # update mid
                            last_edge['mid'] = ((last_edge['start'][0] + last_edge['end'][0])/2, (last_edge['start'][1] + last_edge['end'][1])/2)
                            continue
                merged.append(edge.copy())
                
        # Check closed loop merge
        if len(merged) > 1 and merged[0]['type'] == 'LINE' and merged[-1]['type'] == 'LINE':
            last_edge = merged[-1]
            first_edge = merged[0]
            dx1 = last_edge['end'][0] - last_edge['start'][0]
            dy1 = last_edge['end'][1] - last_edge['start'][1]
            dx2 = first_edge['end'][0] - first_edge['start'][0]
            dy2 = first_edge['end'][1] - first_edge['start'][1]
            cross = dx1 * dy2 - dy1 * dx2
            l1 = math.hypot(dx1, dy1)
            l2 = math.hypot(dx2, dy2)
            if l1 > 1e-5 and l2 > 1e-5 and abs(cross / (l1 * l2)) < 0.02:
                if self._dist(last_edge['end'], first_edge['start']) < 0.1:
                    first_edge['start'] = last_edge['start']
                    if 'sampled_pts' in first_edge and 'sampled_pts' in last_edge:
                        first_edge['sampled_pts'] = last_edge['sampled_pts'] + first_edge['sampled_pts']
                    first_edge['mid'] = ((first_edge['start'][0] + first_edge['end'][0])/2, (first_edge['start'][1] + first_edge['end'][1])/2)
                    merged.pop()
                    
        return merged

    def _filter_short_segments(self, edges: list) -> list:
        """Loại bỏ các segment quá ngắn (noise từ bo góc nhỏ của CAD model).
        
        Các cung/đoạn thẳng < min_segment_len mm thường là bo góc phụ của feature
        (rivet, boss) không cần đặt lỗ riêng. Giữ lại nếu là segment duy nhất.
        """
        if len(edges) <= 4:
            return edges  # Không filter nếu ít segment (tránh mất shape)
        result = []
        for e in edges:
            sx, sy = e['start'][0], e['start'][1]
            ex, ey = e['end'][0], e['end'][1]
            seg_len = math.hypot(ex - sx, ey - sy)
            if seg_len >= self.min_segment_len:
                result.append(e)
        return result if len(result) >= 4 else edges  # Fallback nếu filter quá mạnh

    def get_fused_edges(self, wire_edges_data: list) -> list:
        """Trả về danh sách đường biên đã được nối mạch (Merged lines & arcs)."""
        if not wire_edges_data:
            return []
        sorted_edges = self._sort_and_orient_edges(wire_edges_data)
        merged_lines = self._merge_collinear_lines(sorted_edges)
        merged_arcs = self._merge_contiguous_arcs(merged_lines)
        # Lọc segment quá ngắn (bo góc phụ của CAD model) để tránh candidate nhiễu
        filtered = self._filter_short_segments(merged_arcs)
        return filtered

    def _merge_contiguous_arcs(self, sorted_edges: list) -> list:
        if not sorted_edges: return []
        merged = []
        for edge in sorted_edges:
            params = self._get_arc_params(edge)
            is_arc_part = (params is not None) and (edge['type'] in ('ARC', 'BSPLINECURVE') or (edge['type'] == 'LINE' and math.hypot(edge['end'][0]-edge['start'][0], edge['end'][1]-edge['start'][1]) < 3.0))
            
            if not merged:
                new_edge = edge.copy()
                new_edge['is_arc_group'] = is_arc_part
                new_edge['arc_params'] = params
                new_edge['arc_points'] = [edge['start'], edge.get('mid') or edge['start'], edge['end']]
                merged.append(new_edge)
            else:
                last_edge = merged[-1]
                last_params = last_edge.get('arc_params')
                
                can_merge = False
                if last_edge['is_arc_group'] and is_arc_part and last_params and params:
                    dc = math.hypot(last_params[0]-params[0], last_params[1]-params[1])
                    dr = abs(last_params[2]-params[2])
                    # Nếu tâm và bán kính lệch dưới 0.15mm -> Chắc chắn cùng 1 cung tròn
                    if dc < 0.15 and dr < 0.15:
                        can_merge = True
                        
                if can_merge:
                    # Gộp vào last_edge
                    last_edge['end'] = edge['end']
                    last_edge['arc_points'].extend([edge.get('mid') or edge['start'], edge['end']])
                    mid_idx = len(last_edge['arc_points']) // 2
                    last_edge['mid'] = last_edge['arc_points'][mid_idx]
                    last_edge['type'] = 'ARC'
                    
                    # Update parameters (trung bình hóa để tăng độ chính xác)
                    new_cx = (last_params[0] + params[0]) / 2.0
                    new_cy = (last_params[1] + params[1]) / 2.0
                    new_r = (last_params[2] + params[2]) / 2.0
                    last_edge['arc_params'] = (new_cx, new_cy, new_r)
                else:
                    new_edge = edge.copy()
                    new_edge['is_arc_group'] = is_arc_part
                    new_edge['arc_params'] = params
                    new_edge['arc_points'] = [edge['start'], edge.get('mid') or edge['start'], edge['end']]
                    merged.append(new_edge)
                    
        # Kiểm tra gộp vòng lặp (nối đuôi - đầu)
        if len(merged) > 1 and merged[0]['is_arc_group'] and merged[-1]['is_arc_group']:
            p0 = merged[0].get('arc_params')
            p1 = merged[-1].get('arc_params')
            if p0 and p1 and math.hypot(p0[0]-p1[0], p0[1]-p1[1]) < 0.15 and abs(p0[2]-p1[2]) < 0.15:
                if math.hypot(merged[0]['start'][0] - merged[-1]['end'][0], merged[0]['start'][1] - merged[-1]['end'][1]) < 0.5:
                    merged[0]['start'] = merged[-1]['start']
                    merged[0]['arc_points'] = merged[-1]['arc_points'] + merged[0]['arc_points']
                    mid_idx = len(merged[0]['arc_points']) // 2
                    merged[0]['mid'] = merged[0]['arc_points'][mid_idx]
                    merged.pop()
                
        return merged

    def calculate_holes(self, wire_edges_data: list, face_center: tuple, density_multiplier: float = 1.0) -> List[tuple]:
        if not wire_edges_data:
            return []
            
        sorted_edges = self._sort_and_orient_edges(wire_edges_data)
        merged_edges = self.get_fused_edges(wire_edges_data)
        
        for edge in merged_edges:
            if 'arc_points' in edge and not edge.get('sampled_pts'):
                edge['sampled_pts'] = edge['arc_points']
                
        poly = self.extract_polygon_from_wire(merged_edges)
        if not poly or not poly.is_valid:
            return []
            
        clean_poly = poly.simplify(0.1, preserve_topology=True)
        if not clean_poly or not clean_poly.is_valid or clean_poly.geom_type != 'Polygon':
            clean_poly = poly
            
        holes_2d = []
        face_z = face_center[2]
        n_edges = len(merged_edges)
        
        def get_wall_property(px, py):
            min_dist = float('inf')
            wall_up = True
            for edge in sorted_edges:
                pmx = (edge['start'][0] + edge['end'][0]) / 2.0
                pmy = (edge['start'][1] + edge['end'][1]) / 2.0
                d = math.hypot(px - pmx, py - pmy)
                if d < min_dist:
                    min_dist = d
                    wall_up = edge.get('has_wall_up', True)
            return wall_up
        
        for i in range(n_edges):
            prev_edge = merged_edges[(i - 1) % n_edges]
            curr_edge = merged_edges[i]
            
            p_curr = curr_edge['start']
            
            if prev_edge.get('is_arc_group') and prev_edge.get('arc_params'):
                cx, cy, r = prev_edge['arc_params']
                tx = -(p_curr[1] - cy)
                ty = (p_curr[0] - cx)
                if math.hypot(p_curr[0]-tx - prev_edge['mid'][0], p_curr[1]-ty - prev_edge['mid'][1]) > math.hypot(p_curr[0]+tx - prev_edge['mid'][0], p_curr[1]+ty - prev_edge['mid'][1]):
                    tx, ty = -tx, -ty
                u = self._normalize(tx, ty)
            else:
                u = self._normalize(p_curr[0] - prev_edge['start'][0], p_curr[1] - prev_edge['start'][1])
                
            if curr_edge.get('is_arc_group') and curr_edge.get('arc_params'):
                cx, cy, r = curr_edge['arc_params']
                tx = -(p_curr[1] - cy)
                ty = (p_curr[0] - cx)
                if math.hypot(p_curr[0]+tx - curr_edge['mid'][0], p_curr[1]+ty - curr_edge['mid'][1]) > math.hypot(p_curr[0]-tx - curr_edge['mid'][0], p_curr[1]-ty - curr_edge['mid'][1]):
                    tx, ty = -tx, -ty
                v = self._normalize(tx, ty)
            else:
                v = self._normalize(curr_edge['end'][0] - p_curr[0], curr_edge['end'][1] - p_curr[1])
                
            dir_x = v[0] - u[0]
            dir_y = v[1] - u[1]
            dir_norm = self._normalize(dir_x, dir_y)
            bend_magnitude = math.hypot(dir_x, dir_y)
            wall_up = get_wall_property(p_curr[0], p_curr[1])
            
            if bend_magnitude > 0.05:
                if dir_norm == (0.0, 0.0):
                    dir_norm = (-u[1], u[0])
                # The bisector dir_norm at a convex corner points INTO the mold body (outward from pocket).
                # We want cand1 = pocket_corner + dir_norm*offset (into mold wall)
                # Verify: cand1 should be OUTSIDE the polygon (outside pocket = inside mold body)
                cand1 = Point(p_curr[0] + dir_norm[0] * self.bisector_offset, p_curr[1] + dir_norm[1] * self.bisector_offset)
                cand2 = Point(p_curr[0] - dir_norm[0] * self.bisector_offset, p_curr[1] - dir_norm[1] * self.bisector_offset)
                
                # Determine which candidate is OUTSIDE the polygon (= into mold wall)
                if not clean_poly.contains(cand1):
                    selected_cand = (cand1, dir_norm)
                elif not clean_poly.contains(cand2):
                    selected_cand = (cand2, (-dir_norm[0], -dir_norm[1]))
                else:
                    # Both inside — pick the one farther from face_center (more toward the wall)
                    fc_x, fc_y = face_center[0], face_center[1]
                    d1 = math.hypot(cand1.x - fc_x, cand1.y - fc_y)
                    d2 = math.hypot(cand2.x - fc_x, cand2.y - fc_y)
                    if d1 >= d2:
                        selected_cand = (cand1, dir_norm)
                    else:
                        selected_cand = (cand2, (-dir_norm[0], -dir_norm[1]))
                    
                if selected_cand:
                    pt, norm = selected_cand
                    dist = clean_poly.exterior.distance(pt)
                    holes_2d.append((pt.x, pt.y, face_z, 'corner', wall_up, norm, dist))
                    
            if curr_edge.get('is_arc_group') and curr_edge.get('arc_params'):
                cx, cy, r = curr_edge['arc_params']
                mid = curr_edge['mid']
                
                def offset_arc_point(pt, cx, cy):
                    # Radial vector from arc center to boundary point
                    vx, vy = self._normalize(pt[0] - cx, pt[1] - cy)
                    # cand_out = point + radial (going AWAY from arc center = out of pocket)
                    # cand_in  = point - radial (going TOWARD arc center = into pocket)
                    cand_out = Point(pt[0] + vx * self.bisector_offset, pt[1] + vy * self.bisector_offset)
                    cand_in  = Point(pt[0] - vx * self.bisector_offset, pt[1] - vy * self.bisector_offset)
                    # cand_out is typically OUTSIDE the pocket polygon for convex arcs
                    if not clean_poly.contains(cand_out): 
                        return cand_out, (vx, vy)
                    elif not clean_poly.contains(cand_in):
                        return cand_in, (-vx, -vy)
                    else:
                        # Both inside: pick the one farther from face_center
                        fc_x, fc_y = face_center[0], face_center[1]
                        d1 = math.hypot(cand_out.x - fc_x, cand_out.y - fc_y)
                        d2 = math.hypot(cand_in.x - fc_x, cand_in.y - fc_y)
                        return (cand_out, (vx, vy)) if d1 >= d2 else (cand_in, (-vx, -vy))
                        
                # Thêm lỗ ở đỉnh cung (chỉ arc_peak, không thêm transition riêng)
                res = offset_arc_point(mid, cx, cy)
                if res:
                    pt, norm = res
                    holes_2d.append((pt.x, pt.y, face_z, 'arc_peak', curr_edge.get('has_wall_up', True), norm, clean_poly.exterior.distance(pt)))
            else:
                start = curr_edge['start']
                end = curr_edge['end']
                vx, vy = end[0] - start[0], end[1] - start[1]
                length = math.hypot(vx, vy)
                v_norm = self._normalize(vx, vy)
                
                adjusted_gap = self.max_edge_gap / density_multiplier
                if length >= adjusted_gap:
                    segments = int(math.ceil(length / adjusted_gap))
                    for j in range(1, segments):
                        ratio = j / segments
                        mx = start[0] + vx * ratio
                        my = start[1] + vy * ratio
                        
                        norm_in = (-v_norm[1], v_norm[0])
                        cand1 = Point(mx + norm_in[0] * self.bisector_offset, my + norm_in[1] * self.bisector_offset)
                        cand2 = Point(mx - norm_in[0] * self.bisector_offset, my - norm_in[1] * self.bisector_offset)
                        
                        # Determine which candidate is OUTSIDE the polygon (= into mold wall)
                        if not clean_poly.contains(cand1):
                            selected_cand = (cand1, norm_in)
                        elif not clean_poly.contains(cand2):
                            selected_cand = (cand2, (-norm_in[0], -norm_in[1]))
                        else:
                            fc_x, fc_y = face_center[0], face_center[1]
                            d1 = math.hypot(cand1.x - fc_x, cand1.y - fc_y)
                            d2 = math.hypot(cand2.x - fc_x, cand2.y - fc_y)
                            if d1 >= d2:
                                selected_cand = (cand1, norm_in)
                            else:
                                selected_cand = (cand2, (-norm_in[0], -norm_in[1]))
                            
                        if selected_cand:
                            pt, norm = selected_cand
                            dist = clean_poly.exterior.distance(pt)
                            holes_2d.append((pt.x, pt.y, face_z, 'line', curr_edge.get('has_wall_up', True), norm, dist))
                            
        return self._deduplicate_holes(holes_2d, 5.0)
