# v1.0.0
"""
Module HoleFeatureExtractor - Tầng Domain
Phân tích mô hình 3D (STEP) sử dụng CadQuery/OCP để tìm và trích xuất đặc trưng Lỗ khoan (Drill Holes).
"""
import math
from collections import defaultdict
from typing import List, Dict, Tuple

try:
    import cadquery as cq
    HAS_CQ = True
except ImportError:
    HAS_CQ = False

class HoleFeatureExtractor:
    def __init__(self, min_radius: float = 0.5, max_radius: float = 50.0):
        self.min_radius = min_radius
        self.max_radius = max_radius

    def extract_holes_from_step(self, step_filepath: str) -> List[Dict]:
        """
        Trích xuất danh sách các lỗ từ file STEP.
        Trả về danh sách các lỗ đã được gộp cụm (stepped holes).
        """
        if not HAS_CQ:
            raise RuntimeError("CadQuery is not installed.")
            
        workplane = cq.importers.importStep(step_filepath)
        faces = workplane.faces().vals()
        
        raw_cylinders = []
        
        for f in faces:
            if f.geomType() == 'CYLINDER':
                try:
                    surf = f._geomAdaptor()
                    if hasattr(surf, 'Cylinder'):
                        cyl = surf.Cylinder()
                        axis = cyl.Axis()
                        dir_z = axis.Direction().Z()
                        
                        # Chỉ lấy các mặt trụ thẳng đứng (song song trục Z)
                        if abs(dir_z) > 0.99:
                            center_x = round(axis.Location().X(), 3)
                            center_y = round(axis.Location().Y(), 3)
                            radius = round(cyl.Radius(), 3)
                            
                            # Bỏ qua các mặt trụ quá nhỏ (có thể là fillet/bo góc)
                            if self.min_radius <= radius <= self.max_radius:
                                bbox = f.BoundingBox()
                                zmax = round(bbox.zmax, 3)
                                zmin = round(bbox.zmin, 3)
                                
                                raw_cylinders.append({
                                    'x': center_x,
                                    'y': center_y,
                                    'r': radius,
                                    'z_top': zmax,
                                    'z_bot': zmin
                                })
                except Exception as e:
                    pass

        # Gộp các mặt trụ đồng trục (Coaxial Cylinders) thành một lỗ bậc/xuyên
        return self._group_coaxial_cylinders(raw_cylinders)

    def _group_coaxial_cylinders(self, cylinders: List[Dict]) -> List[Dict]:
        grouped = defaultdict(list)
        
        for c in cylinders:
            found_key = None
            for k in grouped.keys():
                # Gộp nếu tâm cách nhau dưới 0.1mm
                if math.hypot(k[0] - c['x'], k[1] - c['y']) < 0.1:
                    found_key = k
                    break
            
            if found_key:
                grouped[found_key].append(c)
            else:
                grouped[(c['x'], c['y'])] = [c]
                
        holes = []
        for (x, y), cyls in grouped.items():
            # Chiều sâu tổng quát của lỗ
            global_ztop = max(c['z_top'] for c in cyls)
            global_zbot = min(c['z_bot'] for c in cyls)
            
            # Lấy bán kính của đoạn trụ cắt sâu nhất (thường là mũi khoan chính)
            # Sắp xếp theo z_bot giảm dần để lấy đoạn dưới cùng (nếu xuyên thủng) hoặc đoạn dài nhất
            main_cyl = max(cyls, key=lambda c: (c['z_top'] - c['z_bot']))
            main_radius = main_cyl['r']
            
            holes.append({
                'x': x,
                'y': y,
                'r': main_radius,
                'diameter': main_radius * 2.0,
                'z_top': global_ztop,
                'z_bot': global_zbot,
                'depth': global_ztop - global_zbot,
                'segments': len(cyls)
            })
            
        return holes

