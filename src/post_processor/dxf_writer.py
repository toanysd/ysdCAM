# v1.0.0-1
"""
Module DXFWriter - Tầng Infrastructure
Phụ trách xuất bản vẽ CAD 2D định dạng .dxf, tuân thủ tiêu chuẩn MasterCAM.
Hỗ trợ:
- Vẽ đường tròn kích thước thực (D4.2, D6.0, D8.0).
- Tạo layer theo "Độ sâu - Đường kính" với màu sắc riêng biệt.
- Vẽ đường tâm (Centerlines) để Auto-snap trên phần mềm CAM.
"""
import math
from typing import List, Dict

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

class DrillDXFWriter:
    def __init__(self, output_filepath: str):
        self.output_filepath = output_filepath
        # Danh sách màu chuẩn AutoCAD (ACI colors)
        self.color_palette = [1, 2, 3, 4, 5, 6, 20, 30, 40, 50, 140, 150] 

    def _get_color_for_layer(self, depth: float, index_seed: int) -> int:
        """Lấy một màu cố định từ Palette dựa vào độ sâu để các Layer dễ phân biệt."""
        return self.color_palette[index_seed % len(self.color_palette)]

    def export(self, holes: List[Dict], origin: tuple = (0, 0), edges: List[Dict] = None, base_dxf: str = None) -> bool:
        """
        Xuất file DXF.
        - holes: Danh sách dict [{'x': 10, 'y': 20, 'depth': 15.0, 'diameter': 4.2}, ...]
        - origin: Gốc tọa độ X, Y (để trừ tọa độ tương đối).
        - edges: Các đường viền Pocket [{'depth': 10.0, 'wires': [[{'x':.., 'y':..}, ...], ...]}]
        - base_dxf: Đường dẫn file DXF contour làm nền (nếu có).
        """
        if not HAS_EZDXF:
            print("[CẢNH BÁO] Thư viện ezdxf chưa cài đặt. Không thể xuất file DXF.")
            return False

        # Khởi tạo bản vẽ DXF
        try:
            if base_dxf and os.path.exists(base_dxf):
                doc = ezdxf.readfile(base_dxf)
                print(f"[DXF WRITER] Đã nạp file DXF nền: {base_dxf}")
            else:
                doc = ezdxf.new('R2010')
        except Exception as e:
            print(f"[DXF WRITER] Lỗi khi nạp file base_dxf, tạo mới hoàn toàn: {e}")
            doc = ezdxf.new('R2010')

        msp = doc.modelspace()

        # Tạo Layer chuẩn cho Đường tâm (Center)
        if 'Center' not in doc.layers:
            # Sửa lỗi AutoCAD: Bỏ linetype='CENTER' vì ezdxf mặc định có thể không nạp linetype này gây lỗi file corrupt
            doc.layers.add('Center', color=8) # Màu 8 (Xám)

        # Vẽ đường tâm tổng của toàn bộ gốc tọa độ (Global Crosshair)
        global_cross_size = 100.0
        msp.add_line((origin[0] - global_cross_size, origin[1]), 
                     (origin[0] + global_cross_size, origin[1]), 
                     dxfattribs={'layer': 'Center'})
        msp.add_line((origin[0], origin[1] - global_cross_size), 
                     (origin[0], origin[1] + global_cross_size), 
                     dxfattribs={'layer': 'Center'})

        # Group các lỗ theo Depth và Diameter để tạo Layer
        layers_created = {}
        layer_index = 0

        for hole in holes:
            hx = hole['x'] - origin[0]
            hy = hole['y'] - origin[1]
            depth = hole.get('depth', 0.0)
            diameter = hole.get('diameter', 4.2)
            
            abs_depth = abs(depth)
            layer_name = f"ANA {abs_depth:.1f} - D{diameter:.1f}"

            if layer_name not in layers_created:
                color = self._get_color_for_layer(abs_depth, layer_index)
                doc.layers.add(layer_name, color=color)
                layers_created[layer_name] = True
                layer_index += 1

            # 1. Vẽ đường tròn (Đúng kích thước thực) - KHÔNG vẽ đường tâm phụ
            msp.add_circle((hx, hy), radius=diameter/2.0, dxfattribs={'layer': layer_name})

        # Vẽ biên dạng túi (Pocket Edges) nếu có
        if edges:
            import math
            for edge_group in edges:
                depth = edge_group.get('depth', 0.0)
                abs_depth = abs(depth)
                layer_name = f"LINE {abs_depth:.1f}"
                
                if layer_name not in layers_created:
                    color = self._get_color_for_layer(abs_depth, layer_index)
                    doc.layers.add(layer_name, color=color)
                    layers_created[layer_name] = True
                    layer_index += 1
                    
                wires = edge_group.get('wires', [])
                for edge in wires:
                    if edge.get('type') == 'Line':
                        start = (edge['start'][0] - origin[0], edge['start'][1] - origin[1])
                        end = (edge['end'][0] - origin[0], edge['end'][1] - origin[1])
                        msp.add_line(start, end, dxfattribs={'layer': layer_name})
                    elif edge.get('type') == 'Arc':
                        center = (edge['center'][0] - origin[0], edge['center'][1] - origin[1])
                        # ezdxf arc angles are in degrees, CCW
                        start_ang = edge['startAngle']
                        end_ang = edge['endAngle']
                        if not edge.get('isCCW', True):
                            # if CW, swap start and end to draw CCW in dxf
                            start_ang, end_ang = end_ang, start_ang
                        msp.add_arc(center, edge['radius'], start_ang, end_ang, dxfattribs={'layer': layer_name})

        try:
            doc.saveas(self.output_filepath)
            print(f"[DXF] Đã xuất thành công bản vẽ: {self.output_filepath}")
            return True
        except Exception as e:
            print(f"[DXF LỖI] {e}")
            return False
