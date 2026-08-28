# v1.0.0-2
"""
Module HoleClustering - Tầng Application
Sử dụng Machine Learning (DBSCAN) để phân cụm các lỗ D4.2 nằm sát nhau, giảm thiểu số lượng lỗ mồi mặt sau.
"""
import numpy as np
from typing import List, Tuple

try:
    from sklearn.cluster import DBSCAN
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class HoleClusteringService:
    def __init__(self, merge_threshold_mm: float = 1.5):
        self.merge_threshold_mm = merge_threshold_mm

    def cluster_holes(self, coordinates: List[tuple], cad_reader=None, top_z_val: float = 36.0) -> List[tuple]:
        if not coordinates:
            return []
            
        if not HAS_SKLEARN:
            print("[CẢNH BÁO] Chưa cài đặt scikit-learn. Bỏ qua bước phân cụm (Trả về nguyên gốc).")
            return coordinates
        
        # Chuyển đổi sang mảng numpy (chỉ lấy phần tọa độ và thông số số học)
        numeric_coords = [list(pt[:6]) for pt in coordinates]
        X = np.array(numeric_coords, dtype=float)
        
        db = DBSCAN(eps=self.merge_threshold_mm, min_samples=1).fit(X)
        labels = db.labels_
        
        clustered_centers = []
        n_clusters = len(set(labels))
        
        for k in range(n_clusters):
            # Lấy các index gốc thuộc cụm k
            cluster_indices = np.where(labels == k)[0]
            cluster_points = X[cluster_indices]
            
            # Tính trung bình XY
            mean_x = cluster_points[:, 0].mean()
            mean_y = cluster_points[:, 1].mean()
            
            if cluster_points.shape[1] >= 4:
                # Nếu có thuộc tính depth (index 3)
                deepest_local_idx = np.argmax(cluster_points[:, 3])
                orig_idx = cluster_indices[deepest_local_idx]
                orig_pt = list(coordinates[orig_idx])
                
                max_depth = np.max(cluster_points[:, 3])
                min_depth = np.min(cluster_points[:, 3])
                
                # COLLISION CHECK: Kiểm tra va chạm nếu có sự khác biệt bậc đáng kể
                is_safe = True
                if max_depth - min_depth > 0.5:
                    if cad_reader and getattr(cad_reader, '_is_loaded', False):
                        r_test = 2.1 # Bán kính mũi khoan D4.2
                        test_pts = [
                            (mean_x + r_test, mean_y),
                            (mean_x - r_test, mean_y),
                            (mean_x, mean_y + r_test),
                            (mean_x, mean_y - r_test)
                        ]
                        for tx, ty in test_pts:
                            hit_z = cad_reader.raycast_z(tx, ty, top_z_val + 10.0)
                            if hit_z > 0:
                                hit_depth = top_z_val - hit_z - 2.0
                                # Nếu mép mũi khoan chạm vào vùng nông hơn độ sâu mũi khoan dự định (max_depth) quá 1mm
                                if hit_depth < max_depth - 1.0:
                                    is_safe = False
                                    break
                    else:
                        print(f"[THÔNG BÁO] Chế độ DXF: Đã gộp lỗ ở ({mean_x:.1f}, {mean_y:.1f}) và lấy theo vị trí lỗ sâu nhất (chênh lệch bậc {max_depth - min_depth:.1f}mm).")
                        is_safe = True
                                
                if is_safe:
                    orig_pt[0] = mean_x
                    orig_pt[1] = mean_y
                    clustered_centers.append(tuple(orig_pt))
                else:
                    # Cancel merge, giữ nguyên lỗ gốc
                    for idx in cluster_indices:
                        clustered_centers.append(coordinates[idx])
            else:
                # Nếu chỉ có xyz, lấy z sâu nhất (z nhỏ nhất)
                deepest_local_idx = np.argmin(cluster_points[:, 2])
                orig_idx = cluster_indices[deepest_local_idx]
                orig_pt = list(coordinates[orig_idx])
                
                orig_pt[0] = mean_x
                orig_pt[1] = mean_y
                clustered_centers.append(tuple(orig_pt))
            
        return clustered_centers
