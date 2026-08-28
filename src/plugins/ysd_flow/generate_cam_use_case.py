import os
import json
import uuid
import cadquery as cq
import ezdxf
from typing import Dict
from shapely.geometry import Polygon

class GenerateMoldCAMUseCase:
    """
    Use Case: Tạo dữ liệu CAM (Hole + 2D Contour) từ file 3D CAD.
    Phiên bản sử dụng Native CadQuery Topology & ezdxf để bóc tách 2D chuẩn xác.
    """
    
    def __init__(self, cad_filepath: str = None, calc_mode: str = 'heuristic', **kwargs):
        self.cad_filepath = cad_filepath
        self.calc_mode = calc_mode
        self.kwargs = kwargs
        self.holes = []
        
    def execute(self) -> dict:
        """Thực thi luồng toàn trình (Pipeline)."""
        print(f"[USE CASE] Bắt đầu xử lý file: {self.cad_filepath}")
        
        if not (self.cad_filepath and os.path.exists(self.cad_filepath)):
            return {"status": "error", "message": "File CAD không tồn tại."}
            
        wp = cq.importers.importStep(self.cad_filepath)
        if wp is None:
            return {"status": "error", "message": "Lỗi đọc file STEP bằng CadQuery"}

        import math

        # 1. Trích xuất toàn bộ khối trụ (Cylinders) để làm từ điển lỗ
        cylinders_data = []
        for cyl in wp.faces("%Cylinder").vals():
            center = cyl.Center()
            bbox = cyl.BoundingBox()
            depth = bbox.zlen
            try:
                radius = cyl._geomAdaptor().Cylinder().Radius()
            except:
                radius = bbox.xlen / 2.0
            
            cylinders_data.append({
                "x": round(center.x, 3),
                "y": round(center.y, 3),
                "z": round(center.z, 3),
                "top_z": round(center.z + depth / 2.0, 3),
                "bottom_z": round(center.z - depth / 2.0, 3),
                "diameter": round(radius * 2.0, 3),
                "radius": round(radius, 3),
                "matched": False
            })

        # 2. Lấy tất cả mặt phẳng hướng lên (+Z) và nhóm theo Z
        up_faces = wp.faces("+Z").vals()
        if not up_faces:
            return {"status": "error", "message": "Không tìm thấy mặt phẳng gia công (Hướng Z)."}
            
        global_bbox = wp.val().BoundingBox()
        min_z = round(global_bbox.zmin, 3)
        max_z = max(f.Center().z for f in up_faces)
        
        layer_groups = {}
        for face in up_faces:
            z_val = round(face.Center().z, 3)
            if z_val not in layer_groups:
                layer_groups[z_val] = []
            layer_groups[z_val].append(face)

        # 3. Phân tích từng Layer (từ cao xuống thấp)
        def cq_wire_to_dict_edges(wire):
            edges_data = []
            for edge in wire.Edges():
                geom_type = edge.geomType()
                try:
                    p1 = edge.startPoint()
                    p2 = edge.endPoint()
                except:
                    continue
                start = [round(p1.x, 3), round(p1.y, 3)]
                end = [round(p2.x, 3), round(p2.y, 3)]
                if geom_type == "CIRCLE":
                    pmid = edge.positionAt(0.5)
                    mid = [round(pmid.x, 3), round(pmid.y, 3)]
                    if edge.IsClosed():
                        edges_data.append({'type': 'Circle', 'center': mid, 'radius': 0}) 
                    else:
                        edges_data.append({'type': 'ARC', 'start': start, 'end': end, 'mid': mid})
                elif geom_type == "LINE":
                    edges_data.append({'type': 'LINE', 'start': start, 'end': end})
                else:
                    pmid = edge.positionAt(0.5)
                    mid = [round(pmid.x, 3), round(pmid.y, 3)]
                    edges_data.append({'type': 'ARC', 'start': start, 'end': end, 'mid': mid})
            return edges_data

        edges_data = []
        holes_data = []
        
        sorted_z = sorted(layer_groups.keys(), reverse=True)
        temp_dir = os.path.dirname(self.cad_filepath)
        
        # Color palette cho từng độ sâu
        color_palette = ["#3498db", "#e74c3c", "#9b59b6", "#f1c40f", "#2ecc71", "#e67e22", "#1abc9c", "#34495e"]
        color_idx = 0

        for z_val in sorted_z:
            faces = layer_groups[z_val]
            calculated_depth = round(max_z - z_val, 3)
            
            # Pre-compute face areas to detect outer mold boundary face
            face_areas = [(face, face.Area()) for face in faces]
            face_areas_valid = [(f, a) for f, a in face_areas if a >= 3.0]
            if not face_areas_valid:
                continue
            max_area = max(a for _, a in face_areas_valid)
            
            # Pocket faces criterion: area < 30% of layer max area avoids the background mold floor
            # For layers where all faces are similar size (uniform pockets), keep all
            pocket_area_threshold = max_area * 0.30
            # But never skip faces smaller than 1000mm² (always real pockets)
            pocket_area_threshold = max(pocket_area_threshold, 1000.0)
            
            layer_wires_all = []
            layer_new_holes = []
            valid_faces_count = 0

            try:
                from src.plugins.ysd_flow.polygon_hole_strategy import PolygonHoleStrategy
                strategy = PolygonHoleStrategy(max_edge_gap=20.0, bisector_offset=1.5)
            except Exception as e:
                print(f"Error loading strategy: {e}")
                strategy = None

            for face_idx, face in enumerate(faces):
                face_area = face.Area()
                # Skip micro faces (noise) 
                if face_area < 3.0:
                    continue
                # Skip the outer mold floor face (much larger than actual pockets)
                if face_area > pocket_area_threshold and face_area == max_area:
                    continue
                valid_faces_count += 1
                
                # Export DXF cho face này
                face_dxf = os.path.join(temp_dir, f"face_{calculated_depth}_{face_idx}.dxf")
                try:
                    face_wp = cq.Workplane("XY").newObject([face])
                    cq.exporters.exportDXF(face_wp, face_dxf)
                except Exception as e:
                    print(f"[USE CASE] Lỗi xuất DXF face {face_idx}: {e}")
                    continue

                face_wires = []
                try:
                    doc = ezdxf.readfile(face_dxf)
                    msp = doc.modelspace()
                    for entity in msp:
                        if entity.dxftype() == 'LINE':
                            start = entity.dxf.start
                            end = entity.dxf.end
                            face_wires.append({
                                'type': 'LINE',
                                'start': [round(start.x, 3), round(start.y, 3)],
                                'end': [round(end.x, 3), round(end.y, 3)],
                            })
                        elif entity.dxftype() == 'ARC':
                            center = entity.dxf.center
                            radius = entity.dxf.radius
                            start_angle = entity.dxf.start_angle * math.pi / 180.0
                            end_angle = entity.dxf.end_angle * math.pi / 180.0
                            ea = end_angle if end_angle > start_angle else end_angle + 2 * math.pi
                            mid_angle = (start_angle + ea) / 2.0
                            start_pt = [round(center.x + radius * math.cos(start_angle), 3), round(center.y + radius * math.sin(start_angle), 3)]
                            end_pt = [round(center.x + radius * math.cos(end_angle), 3), round(center.y + radius * math.sin(end_angle), 3)]
                            mid_pt = [round(center.x + radius * math.cos(mid_angle), 3), round(center.y + radius * math.sin(mid_angle), 3)]
                            face_wires.append({
                                'type': 'ARC',
                                'start': start_pt,
                                'end': end_pt,
                                'mid': mid_pt,
                                'center': [round(center.x, 3), round(center.y, 3)],
                                'radius': round(radius, 3),
                                'startAngle': round(start_angle, 4),
                                'endAngle': round(end_angle, 4),
                                'isCCW': True
                            })
                        elif entity.dxftype() == 'CIRCLE':
                            center = entity.dxf.center
                            radius = round(entity.dxf.radius, 3)
                            cx, cy = round(center.x, 3), round(center.y, 3)
                            
                            matched_cyl = None
                            for cyl in cylinders_data:
                                if abs(cyl['x'] - cx) < 0.1 and abs(cyl['y'] - cy) < 0.1 and abs(cyl['radius'] - radius) < 0.1:
                                    if cyl['top_z'] <= z_val + 0.1 and cyl['bottom_z'] < z_val - 0.01:
                                        matched_cyl = cyl
                                        break
                                        
                            if matched_cyl:
                                hole_depth = round(z_val - matched_cyl['bottom_z'], 3)
                                matched_cyl['matched'] = True
                                holes_data.append({
                                    "id": str(uuid.uuid4()),
                                    "x": cx,
                                    "y": cy,
                                    "z": z_val,
                                    "depth": hole_depth,
                                    "actual_z": z_val,
                                    "diameter": min(matched_cyl['diameter'], 4.2),
                                    "color": color_palette[color_idx % len(color_palette)],
                                    "is_active": True
                                })
                            else:
                                # Convert circle to two arcs so strategy can process it
                                face_wires.append({
                                    'type': 'ARC',
                                    'start': [round(cx + radius, 3), cy],
                                    'end': [round(cx - radius, 3), cy],
                                    'mid': [cx, round(cy + radius, 3)],
                                    'center': [cx, cy],
                                    'radius': radius,
                                    'startAngle': 0.0,
                                    'endAngle': math.pi,
                                    'isCCW': True
                                })
                                face_wires.append({
                                    'type': 'ARC',
                                    'start': [round(cx - radius, 3), cy],
                                    'end': [round(cx + radius, 3), cy],
                                    'mid': [cx, round(cy - radius, 3)],
                                    'center': [cx, cy],
                                    'radius': radius,
                                    'startAngle': math.pi,
                                    'endAngle': 2 * math.pi,
                                    'isCCW': True
                                })
                except Exception as e:
                    pass

                try:
                    os.remove(face_dxf)
                except:
                    pass

                if face_wires:
                    layer_wires_all.extend(face_wires)
                    if strategy and z_val < max_z:
                        try:
                            fc = face.Center()
                            strategy_holes = strategy.calculate_holes(face_wires, face_center=(fc.x, fc.y, z_val), density_multiplier=1.0)
                            for (hx, hy, hz, htype, is_valid_wall, norm, dist) in strategy_holes:
                                flesh = 2.0
                                depth_val = round((hz - min_z) - flesh, 2)
                                if depth_val < 1.0:
                                    continue # không đủ thịt — bỏ lỗ này
                                layer_new_holes.append({
                                    'id': str(uuid.uuid4()),
                                    'x': round(hx, 3),
                                    'y': round(hy, 3),
                                    'z': round(hz, 3),
                                    'actual_z': round(hz, 3),
                                    'zmin': min_z,
                                    'diameter': 4.2,
                                    'depth': depth_val,
                                    'hole_type': f'back_drill_4.2_{htype}',
                                    'face_id': f"z{z_val}_f{face_idx}",
                                    'face_center_x': round(fc.x, 3),
                                    'face_center_y': round(fc.y, 3)
                                })
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
            
            if layer_wires_all:
                edges_data.append({
                    "depth": calculated_depth,
                    "actual_z": z_val,
                    "wires": layer_wires_all
                })
                
            if layer_new_holes:
                holes_data.extend(layer_new_holes)
            
            print(f"[USE CASE] Layer z={z_val}: {valid_faces_count} faces processed → {len(layer_new_holes)} lỗ back ana")
            color_idx += 1
                
        # Global deduplication across all layers using iterative merging
        back_holes = [h for h in holes_data if 'back' in h.get('hole_type', '')]
        other_holes = [h for h in holes_data if 'back' not in h.get('hole_type', '')]
        
        def apply_shared_hole_dedup(back_holes, xy_threshold=5.0):
            import math
            result = sorted(back_holes, key=lambda h: h['z'])  # sâu → nông
            active_map = {}  # key: (ax, ay) → z đã có lỗ active
            
            for h in result:
                found_close = False
                for (ax, ay), az in active_map.items():
                    if math.hypot(h['x'] - ax, h['y'] - ay) < xy_threshold:
                        h['is_active'] = False
                        found_close = True
                        break
                
                if not found_close:
                    h['is_active'] = True
                    active_map[(h['x'], h['y'])] = h['z']
            
            return result

        merged_back_holes = apply_shared_hole_dedup(back_holes)
        active_count = sum(1 for h in merged_back_holes if h['is_active'])
        holes_data = other_holes + merged_back_holes
        print(f"[USE CASE] shared_hole dedup: {len(back_holes)} -> {active_count} active.")


        # 4. Gom các lỗ chưa được khớp (fallback) vào layer gần nhất
        for cyl in cylinders_data:
            if not cyl['matched']:
                # Tìm layer gần đỉnh lỗ nhất
                closest_z = min(sorted_z, key=lambda z: abs(z - cyl['top_z']))
                calculated_depth = round(max_z - closest_z, 3)
                hole_depth = round(closest_z - cyl['bottom_z'], 3)
                if hole_depth <= 0: hole_depth = cyl['depth']
                
                holes_data.append({
                    "id": str(uuid.uuid4()),
                    "x": cyl['x'],
                    "y": cyl['y'],
                    "z": closest_z,
                    "depth": hole_depth,
                    "actual_z": closest_z,
                    "diameter": min(cyl['diameter'], 4.2),
                    "color": "#e74c3c", # Fallback color
                    "is_active": True
                })

        print(f"[USE CASE] Đã xử lý {len(sorted_z)} layers, {len(holes_data)} lỗ khoan.")

        self.holes = holes_data
        
        result = {
            "status": "success",
            "message": "Phân tích CAM theo Layer hoàn tất.",
            "holes": holes_data,
            "edges": edges_data,
            "boundingBox": {
                "minX": wp.val().BoundingBox().xmin,
                "maxX": wp.val().BoundingBox().xmax,
                "minY": wp.val().BoundingBox().ymin,
                "maxY": wp.val().BoundingBox().ymax,
                "minZ": wp.val().BoundingBox().zmin,
                "maxZ": wp.val().BoundingBox().zmax,
                "origW": wp.val().BoundingBox().xlen,
                "origH": wp.val().BoundingBox().ylen
            }
        }
        
        output_path = os.path.join(os.path.dirname(self.cad_filepath), "holes.json")
        try:
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[USE CASE] Lỗi ghi file JSON: {e}")
            
        return result
