# v1.0.0
import math
import numpy as np

class DropCutterEngine:
    """
    Giả lập thuật toán Drop-Cutter của OpenCAMLib (OCL).
    Thay vì cài đặt thư viện C++ phức tạp, ta dùng phương pháp Z-Map (Heightmap)
    dựa trên ray-casting kết hợp với bù trừ bán kính dao (Tool Compensation).
    """
    def __init__(self, cad_reader, tool_radius=2.1, tool_type='FLAT'):
        self.cad_reader = cad_reader
        self.tool_radius = tool_radius
        self.tool_type = tool_type # FLAT, BALL
        
    def generate_waterline_toolpath(self, resolution=1.0, z_step=1.0):
        """
        Tạo đường chạy dao Waterline (Phay tinh bề mặt cong).
        Cách làm: Lấy mẫu lưới Grid, tạo Z-Map, sau đó bù trừ dao.
        """
        if not self.cad_reader._is_loaded:
            return []

        bbox = self.cad_reader.get_bounding_box()
        min_x, max_x = bbox.get("x_min", 0), bbox.get("x_max", 100)
        min_y, max_y = bbox.get("y_min", 0), bbox.get("y_max", 100)
        top_z = bbox.get("z_max", 36)
        min_z = bbox.get("z_min", 0)

        # Tạo lưới Grid XY
        x_coords = np.arange(min_x, max_x, resolution)
        y_coords = np.arange(min_y, max_y, resolution)
        
        toolpath_points = []
        
        # Mô phỏng quá trình Drop-Cutter (Raycast từ trên xuống)
        try:
            # Trong môi trường CQ, ta có thể raycast hoặc dùng hàm đánh giá bề mặt.
            # Ở đây ta dựng thuật toán mô phỏng thả dao:
            # - Flat Endmill: Chiều cao bằng max của các điểm nằm trong r <= tool_radius
            # - Ball Nose: Chiều cao bằng max(z_surface(x,y) + sqrt(R^2 - d^2))
            
            # Để demo logic kiến trúc, ta trả về lưới điểm nội suy làm điểm dao.
            # (Việc raycast thực tế sẽ dùng self.cad_reader.raycast(x, y, top_z))
            
            print(f"[OCL] Bắt đầu tính toán lưới Z-Map với {len(x_coords)*len(y_coords)} điểm...")
            
            for y in y_coords:
                row = []
                for x in x_coords:
                    # Giả định raycast đụng bề mặt ở z=10 (Mock)
                    # Thực tế: hit_z = self.cad_reader.raycast(x, y, top_z)
                    hit_z = min_z + 10.0 # Tạm thời lấy mặt phẳng 10mm
                    
                    # Tool compensation
                    comp_z = hit_z
                    if self.tool_type == 'BALL':
                        comp_z += self.tool_radius
                        
                    row.append({"x": float(x), "y": float(y), "z": float(comp_z)})
                toolpath_points.extend(row)
                
            print(f"[OCL] Đã sinh {len(toolpath_points)} điểm chạy dao 3D (Drop-Cutter).")
            return toolpath_points
            
        except Exception as e:
            print(f"[OCL] Lỗi khi chạy thuật toán Drop-Cutter: {e}")
            return []
