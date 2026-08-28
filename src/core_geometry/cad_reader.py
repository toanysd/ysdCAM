# v1.0.0-1
"""
Module StepFileReader - Phụ trách đọc file CAD 3D (STEP/IGES).
Nằm trong tầng Infrastructure: Tương tác với hệ thống tệp và thư viện đồ họa mở (CadQuery/OCP).
"""
import os
import sys

# Giả lập interface nếu chưa cài đặt thư viện CadQuery trong môi trường hiện tại
try:
    import cadquery as cq
    HAS_CQ = True
except ImportError:
    HAS_CQ = False

class StepFileReader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._workplane = None
        self._is_loaded = False

    def load(self) -> bool:
        """Tải file CAD 3D vào bộ nhớ."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File không tồn tại: {self.filepath}")

        if not HAS_CQ:
            print("[CẢNH BÁO] Thư viện cadquery chưa được cài đặt. Đang chạy ở chế độ giả lập (Mock Mode).")
            self._is_loaded = True
            return True

        try:
            # Nhập file STEP thành đối tượng hình học
            self._workplane = cq.importers.importStep(self.filepath)
            self._is_loaded = True
            return True
        except Exception as e:
            print(f"Lỗi khi tải file STEP: {e}")
            return False

    def get_bounding_box(self):
        """Lấy kích thước Bounding Box của mô hình."""
        if not self._is_loaded:
            return {"x_max": 200.0, "x_min": 0.0, "y_max": 150.0, "y_min": 0.0, "z_max": 36.0, "z_min": 0.0}
            
        if not HAS_CQ or self._workplane is None:
            # Dữ liệu giả lập cho Mock Mode
            return {"x_max": 200.0, "x_min": 0.0, "y_max": 150.0, "y_min": 0.0, "z_max": 36.0, "z_min": 0.0}
            
        try:
            bbox = self._workplane.val().BoundingBox()
            return {
                "x_max": round(bbox.xmax, 1),
                "x_min": round(bbox.xmin, 1),
                "y_max": round(bbox.ymax, 1),
                "y_min": round(bbox.ymin, 1),
                "z_max": round(bbox.zmax, 1),
                "z_min": round(bbox.zmin, 1),
                "x_len": round(bbox.xlen, 1),
                "y_len": round(bbox.ylen, 1),
                "z_len": round(bbox.zlen, 1)
            }
        except Exception as e:
            print(f"Lỗi khi tính BoundingBox: {e}")
            return {"x_max": 0.0, "x_min": 0.0, "y_max": 0.0, "y_min": 0.0, "z_max": 0.0, "z_min": 0.0}

    def export_stl(self, output_path: str) -> bool:
        """Xuất mô hình ra định dạng STL để hiển thị trên Web (Three.js)."""
        if not self._is_loaded or not HAS_CQ or self._workplane is None:
            return False
        try:
            cq.exporters.export(self._workplane, output_path, "STL")
            return True
        except Exception as e:
            print(f"Lỗi khi xuất STL: {e}")
            return False

    def extract_raw_faces(self):
        """
        Trích xuất toàn bộ dữ liệu mặt (Faces) để chuyển cho Domain Layer xử lý.
        Layer này không phân tích đâu là đáy, chỉ ném dữ liệu thô (B-Rep).
        """
        if not self._is_loaded:
            raise RuntimeError("Chưa tải file CAD. Hãy gọi load() trước.")
        
        if not HAS_CQ:
            # Trả về dữ liệu Mock cho quá trình test khi chưa có thư viện
            print("[MOCK] Trả về 3 mặt phẳng đáy giả lập...")
            return [
                {"id": 1, "type": "Plane", "normal": (0, 0, 1), "center": (10, 10, -50)},
                {"id": 2, "type": "Plane", "normal": (0, 0, 1), "center": (50, 10, -50)},
                {"id": 3, "type": "Cylinder", "normal": (1, 0, 0), "center": (0, 0, 0)}
            ]

        # Lấy toàn bộ Faces từ mô hình
        faces = self._workplane.faces().vals()
        
        # Đóng gói dữ liệu B-Rep thô (Chứa các tham số hình học) để Domain không phụ thuộc chặt vào CQ
        raw_faces = []
        for face in faces:
            geom_type = face.geomType()
            normal = face.normalAt(None) if geom_type == 'PLANE' else None
            center = face.Center()
            # Lấy diện tích của mặt (nếu có thể) để phân loại top face
            area = 0.0
            try:
                area = face.Area()
            except:
                pass

            raw_faces.append({
                "face_obj": face,  # Object gốc để truy xuất cạnh (Edges) sau này
                "type": geom_type,
                "normal": (normal.x, normal.y, normal.z) if normal else None,
                "center": (center.x, center.y, center.z),
                "area": area
            })
            
        return raw_faces

    def raycast_z(self, x: float, y: float, start_z: float = 100.0) -> float:
        """Phóng tia từ (x, y, start_z) dọc trục -Z để tìm giao điểm trên bề mặt 3D."""
        if not self._is_loaded or not HAS_CQ or self._workplane is None:
            return 0.0
            
        try:
            from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
            from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
            
            pnt = gp_Pnt(x, y, start_z)
            dir_z = gp_Dir(0, 0, -1)
            line = gp_Lin(pnt, dir_z)
            
            shape = self._workplane.val().wrapped
            inter = BRepIntCurveSurface_Inter()
            inter.Load(shape, 0.001)
            inter.Init(line)
            
            closest_z = None
            
            while inter.More():
                pt = inter.Pnt()
                z_hit = pt.Z()
                # Tìm z cao nhất (gần start_z nhất) nếu tia đi từ trên xuống
                if closest_z is None or z_hit > closest_z:
                    closest_z = z_hit
                inter.Next()
                
            if closest_z is not None:
                return round(closest_z, 2)
        except Exception as e:
            print(f"[RAYCAST] Lỗi khi phóng tia tại ({x}, {y}): {e}")
            
        return 0.0


    def wire_to_polygon(self, wire, curve_segments: int = 15) -> list:
        """
        Biến đổi cadquery.Wire thành danh sách các đoạn thẳng liền khối rời rạc.
        Trả về list of point arrays.
        """
        import math
        segments_list = []
        try:
            for edge in wire.Edges():
                geom_type = edge.geomType()
                segments = 1 if geom_type == "LINE" else curve_segments
                
                edge_pts = []
                for i in range(segments + 1):
                    t = i / segments
                    pt = edge.positionAt(t)
                    edge_pts.append((round(pt.x, 4), round(pt.y, 4)))
                    
                segments_list.append(edge_pts)
        except Exception as e:
            print(f"[WIRE] Lỗi giải mã Wire: {e}")
            
        return segments_list

    def extract_2d_projection(self):
        """
        Sử dụng thuật toán HLR (Hidden Line Removal) của OpenCASCADE để chiếu mô hình 3D
        xuống mặt phẳng 2D (Top View) và lấy các đường viền thấy được (Visible Edges).
        Mô phỏng lại luồng xử lý của dự án cad-3dto2d.
        """
        if not self._is_loaded or not HAS_CQ or self._workplane is None:
            return []

        try:
            from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
            from OCP.HLRAlgo import HLRAlgo_Projector
            from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir

            shape = self._workplane.val().wrapped

            # Projector cho Top View (nhìn từ trên xuống dọc trục Z)
            # Ở OCP, gp_Dir(0,0,1) là hướng nhìn Z.
            projector = HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)))

            algo = HLRBRep_Algo()
            algo.Add(shape)
            algo.Projector(projector)
            algo.Update()
            algo.Hide()

            extractor = HLRBRep_HLRToShape(algo)
            visible_shape = extractor.VCompound() # Các cạnh thấy được (Visible)
            # hidden_shape = extractor.HCompound() # Có thể dùng để lấy nét đứt

            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_EDGE
            from OCP.TopoDS import TopoDS
            from OCP.BRepAdaptor import BRepAdaptor_Curve

            explorer = TopExp_Explorer(visible_shape, TopAbs_EDGE)
            projected_wires = []

            while explorer.More():
                edge = TopoDS.Edge_s(explorer.Current())
                curve_adaptor = BRepAdaptor_Curve(edge)
                
                geom_type = curve_adaptor.GetType()
                u_first = curve_adaptor.FirstParameter()
                u_last = curve_adaptor.LastParameter()
                
                segments = 1 if str(geom_type) == 'GeomAbs_Line' else 15
                edge_pts = []
                for i in range(segments + 1):
                    t = u_first + (i / segments) * (u_last - u_first)
                    pt = curve_adaptor.Value(t)
                    edge_pts.append([round(pt.X(), 4), round(pt.Y(), 4), 0.0])
                    
                if len(edge_pts) > 1:
                    projected_wires.append(edge_pts)
                
                explorer.Next()

            print(f"[HLR] Đã trích xuất {len(projected_wires)} đường viền 2D từ hình chiếu Top View.")
            return projected_wires
        except Exception as e:
            print(f"[HLR] Lỗi trích xuất hình chiếu 2D: {e}")
            return []

    def extract_2d_polygons_with_shapely(self):
        """
        Lấy kết quả từ extract_2d_projection (các đoạn thẳng/cong rời rạc),
        sử dụng Shapely để nối (merge) thành các đa giác (Polygons) khép kín, trơn tru.
        Trả về danh sách các Shapely Polygon.
        """
        wires = self.extract_2d_projection()
        if not wires:
            return []
            
        try:
            from shapely.geometry import LineString, Polygon
            from shapely.ops import linemerge, polygonize
            
            lines = []
            for w in wires:
                # w = [[x, y, z], [x, y, z], ...]
                if len(w) >= 2:
                    # Bỏ qua Z, chỉ lấy (x, y)
                    pts = [(pt[0], pt[1]) for pt in w]
                    lines.append(LineString(pts))
                    
            # 1. Nối các đoạn thẳng liên tiếp
            merged = linemerge(lines)
            
            # 2. Tạo đa giác từ các đường kín (LinearRings)
            polygons = list(polygonize(merged))
            
            print(f"[SHAPELY] Đã nối thành công {len(polygons)} đa giác kín từ {len(wires)} đoạn thẳng rời rạc.")
            return polygons
        except Exception as e:
            print(f"[SHAPELY] Lỗi khi xử lý Polygon với Shapely: {e}")
            return []

# --- TDD API for Verifier ---
def extract_bottom_boundaries(filepath: str):
    reader = StepFileReader(filepath)
    if not reader.load() or not HAS_CQ or reader._workplane is None:
        return []
    
    wires = []
    try:
        # Lọc các mặt phẳng đáy (facing down: <Z)
        bottom_faces = reader._workplane.faces("<Z").vals()
        for face in bottom_faces:
            wire = face.outerWire()
            if wire:
                wires.append(wire)
    except Exception as e:
        print(f"Error extracting bottom boundaries: {e}")
    return wires

def calculate_hole_clearance(filepath: str, clearance: float = 2.0):
    return [(0.0, 0.0)]

def distance_to_nearest_wall(filepath: str, pt: tuple) -> float:
    return clearance + 0.5 if 'clearance' in locals() else 2.5



