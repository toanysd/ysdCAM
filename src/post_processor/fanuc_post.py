# v2.0.0
"""
Module fanuc_post.py - Tầng Post Processor
Trình xuất G-code chuyên biệt cho hệ điều hành Fanuc, tham chiếu từ MPFAN_Y0_OK.pst.
"""
from typing import List, Tuple, Dict
from datetime import datetime
import os

class FanucPostProcessor:
    def __init__(self, output_filepath: str):
        self.output_filepath = output_filepath
        # Default Fanuc parameters
        self.metric_mode = "G21"
        self.abs_mode = "G90"
        self.cancel_cycles = "G40 G49 G80"
        self.home_z = "G91 G28 Z0."
        self.home_xy = "G91 G28 X0. Y0." # Hoặc G28 X0. Y0.

    def _generate_header(self, program_name: str = "YSD_FANUC_PROGRAM") -> List[str]:
        """Tạo đoạn mã Header tiêu chuẩn của Fanuc (Tham khảo pheader$ / psof$)."""
        date_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        return [
            "%",
            f"O1000 ({program_name})",
            f"(DATE - {date_str})",
            f"{self.metric_mode} {self.abs_mode} {self.cancel_cycles}",
            self.home_z
        ]

    def _generate_tool_change(self, tool_no: int, tool_dia: float, spindle_speed: int = 3000, z_safe: float = 36.0) -> List[str]:
        """Tạo đoạn mã thay dao và kích hoạt trục chính/Dung dịch làm mát (Tham khảo ptlchg$)."""
        return [
            f"(--- TOOL T{tool_no} - D{tool_dia:.1f} ---)",
            f"T{tool_no} M06",
            f"S{spindle_speed} M03",
            "G90 G54",
            "G00 X0. Y0.",
            f"G43 H{tool_no} Z{z_safe:.3f} M08"
        ]

    def _generate_peck_drill_cycle(self, holes: List[Dict], peck_depth: float = 2.0, feed_rate: int = 150) -> List[str]:
        """Tạo vòng lặp khoan mổ G83 (Tham khảo ppeck$)."""
        gcode = []
        if not holes:
            return gcode
            
        first_hole = True
        for h in holes:
            x, y, z_bot = h['x'], h['y'], h['z']  # Note: z is target depth
            
            sx = f"{x:.3f}"
            sy = f"{y:.3f}"
            sz = f"{z_bot:.3f}"
            
            if first_hole:
                # Dòng nội suy đầu tiên: G83 X Y Z R Q F
                # R (Retract plane) thường đặt cách mặt phôi 2mm
                gcode.append(f"G83 X{sx} Y{sy} Z{sz} R2.0 Q{peck_depth:.3f} F{feed_rate}")
                first_hole = False
            else:
                # Các tọa độ tiếp theo chỉ cần X, Y
                gcode.append(f"X{sx} Y{sy}")
                
        # Hủy chu trình khoan
        gcode.append("G80")
        return gcode

    def _generate_footer(self) -> List[str]:
        """Tạo đoạn mã Footer kết thúc chương trình (Tham khảo peof$)."""
        return [
            "M09",              # Tắt dung dịch trơn nguội
            self.home_z,        # Rút dao về gốc Z an toàn
            self.home_xy,       # Rút trục X, Y về gốc
            "M30",              # Kết thúc chương trình
            "%"
        ]

    def generate_program(self, grouped_by_tool: dict, program_name: str = "YSD_FANUC", z_safe: float = 36.0, spindle_speed: int = 3000, feed_rate: int = 150, peck_depth: float = 2.0) -> bool:
        """
        Sinh toàn bộ chương trình G-Code cho Fanuc.
        grouped_by_tool format: { tool_dia_float: [{'x': x, 'y': y, 'z': z}, ...], ... }
        """
        if not grouped_by_tool:
            return False
            
        gcode = self._generate_header(program_name)
        
        tool_no = 1
        for tool_dia, holes in grouped_by_tool.items():
            if not holes:
                continue
                
            # Block thay dao
            gcode.extend(self._generate_tool_change(tool_no, tool_dia, spindle_speed, z_safe))
            
            # Block gia công
            gcode.extend(self._generate_peck_drill_cycle(holes, peck_depth, feed_rate))
            
            tool_no += 1

        # Block kết thúc
        gcode.extend(self._generate_footer())

        try:
            with open(self.output_filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(gcode))
            print(f"[FANUC POST] Đã xuất thành công: {self.output_filepath}")
            return True
        except Exception as e:
            print(f"[FANUC POST LỖI] {e}")
            return False

    def write(self, coordinates: List[Tuple], **kwargs) -> bool:
        """
        Giao diện tương thích (Drop-in replacement) với GCodeWriter cũ.
        Nhóm các toạ độ theo đường kính lỗ (dao) và gọi `generate_program`.
        - coordinates format: list of tuples (x, y, z_target, depth, actual_z, diameter, hole_type, dir)
        """
        grouped = {}
        for coord in coordinates:
            x, y = coord[0], coord[1]
            z_target = coord[2]
            dia = coord[5] if len(coord) > 5 else 4.2
            
            if dia not in grouped:
                grouped[dia] = []
                
            grouped[dia].append({
                'x': x,
                'y': y,
                'z': z_target
            })
            
        return self.generate_program(grouped, **kwargs)
