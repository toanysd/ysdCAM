import ezdxf
import math
from typing import List, Dict

class DxfReader:
    """Đọc file DXF và trích xuất thành các wire_data dùng cho PolygonHoleStrategy."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.doc = ezdxf.readfile(filepath)
        self.msp = self.doc.modelspace()

    def parse_z_from_layer(self, layer_name: str) -> float:
        """Trích xuất depth từ tên layer, ví dụ 'Z_18' hoặc 'DEPTH_18'."""
        try:
            import re
            match = re.search(r'(?:Z_|DEPTH_)(\d+(?:\.\d+)?)', layer_name, re.IGNORECASE)
            if match:
                return float(match.group(1))
        except Exception as e:
            print(f"[DXF] Error parsing layer name: {e}")
        return 0.0

    def extract_faces(self) -> List[Dict]:
        """Trích xuất danh sách các mặt (face_records) từ DXF."""
        layer_entities = {}
        for entity in self.msp:
            layer = entity.dxf.layer
            if layer not in layer_entities:
                layer_entities[layer] = []
            layer_entities[layer].append(entity)
            
        faces = []
        for layer, entities in layer_entities.items():
            z_depth = self.parse_z_from_layer(layer)
            wire_edges = []
            
            for entity in entities:
                dxftype = entity.dxftype()
                
                # Hàm hỗ trợ thêm wire
                def add_line(p1, p2):
                    wire_edges.append({
                        'start': (p1.x, p1.y, 0.0),
                        'end': (p2.x, p2.y, 0.0),
                        'mid': ((p1.x+p2.x)/2, (p1.y+p2.y)/2, 0.0),
                        'type': 'LINE',
                        'sampled_pts': [(p1.x, p1.y, 0.0), (p2.x, p2.y, 0.0)],
                        'has_wall_up': True
                    })
                    
                def add_arc(center, radius, start_angle, end_angle):
                    sa = math.radians(start_angle)
                    ea = math.radians(end_angle)
                    if ea < sa: ea += 2 * math.pi
                    pts = []
                    for i in range(11):
                        ang = sa + (ea - sa) * (i / 10.0)
                        pts.append((center.x + radius * math.cos(ang), center.y + radius * math.sin(ang), 0.0))
                    wire_edges.append({
                        'start': pts[0],
                        'end': pts[-1],
                        'mid': pts[5],
                        'type': 'ARC',
                        'sampled_pts': pts,
                        'has_wall_up': True
                    })

                if dxftype == 'LINE':
                    add_line(entity.dxf.start, entity.dxf.end)
                elif dxftype == 'ARC':
                    add_arc(entity.dxf.center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle)
                elif dxftype in ('LWPOLYLINE', 'POLYLINE'):
                    # Dùng virtual_entities để lấy các thành phần cơ bản (đã tính toán bulge thành ARC)
                    for v_entity in entity.virtual_entities():
                        if v_entity.dxftype() == 'LINE':
                            add_line(v_entity.dxf.start, v_entity.dxf.end)
                        elif v_entity.dxftype() == 'ARC':
                            add_arc(v_entity.dxf.center, v_entity.dxf.radius, v_entity.dxf.start_angle, v_entity.dxf.end_angle)
            
            if wire_edges:
                all_pts = [pt for edge in wire_edges for pt in edge['sampled_pts']]
                if not all_pts:
                    continue
                    
                min_x = min(p[0] for p in all_pts)
                max_x = max(p[0] for p in all_pts)
                min_y = min(p[1] for p in all_pts)
                max_y = max(p[1] for p in all_pts)
                
                center = ((min_x+max_x)/2, (min_y+max_y)/2, 0.0)
                
                faces.append({
                    'layer': layer,
                    'center': center,
                    'calculated_depth': z_depth if z_depth > 0 else 5.0,
                    'actual_z': z_depth,
                    'wire_data': wire_edges,
                    'type': 'DXF_FACE',
                    # Thêm bbox object giả để tương thích
                    'face_obj': type('FakeBbox', (object,), {
                        'BoundingBox': lambda self: type('BBox', (object,), {
                            'xlen': max_x - min_x,
                            'ylen': max_y - min_y,
                            'zmax': 0.0
                        })()
                    })()
                })
                
        return faces
