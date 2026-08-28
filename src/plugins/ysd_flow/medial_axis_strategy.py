"""
Module MedialAxisStrategy - Tầng Domain
Mô phỏng vật lý "hút chân không":
1. Trải đa giác 2D lên một Grid Raster.
2. Tính Distance Transform (khoảng cách tới vách).
3. Lấy Medial Axis (bộ xương) làm nơi đặt lỗ.
"""
import math
import numpy as np
from typing import List, Tuple
from shapely.geometry import Polygon, LineString, Point

# Sẽ import skimage và scipy khi chạy thực tế
class MedialAxisStrategy:
    def __init__(self, pixel_size: float = 0.5, bisector_offset: float = 1.5):
        self.pixel_size = pixel_size # 1 pixel = 0.5 mm
        self.bisector_offset = bisector_offset

    def extract_polygon_from_wire(self, wire_edges_data: list) -> Polygon:
        if not wire_edges_data or len(wire_edges_data) < 3:
            return None
        coords = []
        for edge in wire_edges_data:
            pt = (edge['start'][0], edge['start'][1])
            if not coords or math.hypot(coords[-1][0]-pt[0], coords[-1][1]-pt[1]) > 0.001:
                coords.append(pt)
        if len(coords) < 3:
            return None
        if math.hypot(coords[-1][0]-coords[0][0], coords[-1][1]-coords[0][1]) > 0.001:
            coords.append(coords[0])
        poly = Polygon(coords)
        if poly.is_valid: return poly
        clean_poly = poly.buffer(0)
        if isinstance(clean_poly, Polygon) and clean_poly.is_valid:
            return clean_poly
        return None

    def calculate_holes(self, wire_edges_data: list, face_center: tuple) -> List[tuple]:
        """Tính lỗ dựa trên Grid Distance Transform và Skeletonization."""
        try:
            from skimage.draw import polygon2mask
            from skimage.morphology import skeletonize
            from scipy.ndimage import distance_transform_edt
        except ImportError:
            print("[MEDIAL AXIS] Thiếu thư viện skimage hoặc scipy.")
            return []

        poly = self.extract_polygon_from_wire(wire_edges_data)
        if not poly or not poly.is_valid:
            return []

        # 1. Tạo Grid 2D bao trọn Polygon
        minx, miny, maxx, maxy = poly.bounds
        
        # Thêm padding
        pad = 2.0
        minx -= pad; miny -= pad; maxx += pad; maxy += pad
        
        width = int(math.ceil((maxx - minx) / self.pixel_size))
        height = int(math.ceil((maxy - miny) / self.pixel_size))
        
        if width <= 0 or height <= 0 or width > 2000 or height > 2000:
            return [] # Quá to hoặc lỗi
            
        # Tọa độ pixel (row, col) = (y, x)
        # origin (0,0) ở góc trên trái
        coords = list(poly.exterior.coords)
        poly_pixels = []
        for x, y in coords:
            col = (x - minx) / self.pixel_size
            row = (y - miny) / self.pixel_size
            poly_pixels.append((row, col))
            
        # 2. Rasterize Polygon thành Mask 2D (1=Inside, 0=Outside)
        image_shape = (height, width)
        mask = polygon2mask(image_shape, np.array(poly_pixels))
        
        # 3. Tính Euclidean Distance Transform
        # Tính khoảng cách từ mỗi pixel bên trong tới biên gần nhất
        dt = distance_transform_edt(mask)
        
        # 4. Tìm Xương Sống (Skeleton)
        skeleton = skeletonize(mask)
        
        # Chỉ giữ lại các pixel xương có khoảng cách > bisector_offset (tránh khoan phạm vách)
        min_dist_pixels = self.bisector_offset / self.pixel_size
        valid_skeleton = skeleton & (dt >= min_dist_pixels)
        
        holes_2d = []
        face_z = face_center[2]
        
        # 5. Phân tích xương (Tìm điểm đầu, giao điểm)
        # Dùng một ma trận kernel 3x3 để đếm số hàng xóm
        import scipy.ndimage as ndimage
        kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
        neighbor_count = ndimage.convolve(valid_skeleton.astype(int), kernel, mode='constant', cval=0)
        
        # Điểm đầu tận cùng của nhánh (Endpoints): có 1 hàng xóm
        endpoints = valid_skeleton & (neighbor_count == 1)
        # Giao điểm của các nhánh (Junctions): có >= 3 hàng xóm
        junctions = valid_skeleton & (neighbor_count >= 3)
        
        # Gộp các điểm mấu chốt
        key_points = endpoints | junctions
        
        rows, cols = np.where(key_points)
        
        # Chuyển đổi tọa độ pixel về tọa độ thực
        for r, c in zip(rows, cols):
            real_x = minx + c * self.pixel_size
            real_y = miny + r * self.pixel_size
            holes_2d.append((real_x, real_y, face_z))
            
        # Để rải đều các đoạn dài không có junctions/endpoints, 
        # (Chưa implement, tạm thời rải Endpoint và Junction là đủ điểm hút chết)
        
        return holes_2d
