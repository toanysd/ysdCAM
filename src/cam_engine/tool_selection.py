# v1.0.0
"""
Module ToolSelection - Tầng Domain
Phụ trách logic chọn dao mồi mặt sau (Back Ana) dựa trên giới hạn vật lý 
và thuật toán lượng dư 118 độ của mũi khoan.
Tuyệt đối không phụ thuộc vào CAD.
"""
import math
from typing import Optional, Dict

class DrillBitLibrary:
    """Từ điển cấu hình giới hạn các loại dao khoan."""
    def __init__(self):
        self.bits = {
            # "ID": {"diameter": D, "max_depth": L}
            "D4.2": {"diameter": 4.2, "max_depth": 60.0},
            "D6.0": {"diameter": 6.0, "max_depth": 75.0},
            "D8.0": {"diameter": 8.0, "max_depth": 90.0},
            "D3.3": {"diameter": 3.3, "max_depth": 50.0},
            "D2.0": {"diameter": 2.0, "max_depth": 20.0},
        }

    def get_bit(self, name: str) -> Optional[Dict]:
        return self.bits.get(name)


class TipClearanceMath:
    """Toán học tính toán lượng dư đâm thủng của chóp mũi khoan 118 độ."""
    
    def __init__(self, tip_angle_deg: float = 118.0):
        self.tip_angle_deg = tip_angle_deg
        # Góc nửa chóp (Half-angle) = 59 độ
        self.half_angle_rad = math.radians(self.tip_angle_deg / 2.0)

    def calculate_tip_height(self, diameter: float) -> float:
        """
        Tính chiều cao của phần chóp mũi khoan (từ đỉnh nhọn đến vai).
        h = (D/2) / tan(59)
        """
        return (diameter / 2.0) / math.tan(self.half_angle_rad)

    def check_safe_clearance(self, diameter: float, target_depth: float, wall_distance: float) -> bool:
        """
        Kiểm tra xem với mũi khoan D, ở độ sâu target_depth, phần vai của mũi khoan
        có chọc thủng vách (lượng dư < 1.0mm) hay không.
        - diameter: Đường kính mũi khoan.
        - target_depth: Độ sâu trục Z (chưa dùng trong logic cơ bản, có thể dùng nếu có profile độ dốc).
        - wall_distance: Khoảng cách từ trục (tâm) mũi khoan đến thành vách khuôn (tại cao độ Z của vai dao).
        """
        # Lượng dư vật liệu (Material thickness left) = khoảng cách tâm đến vách - bán kính mũi khoan.
        # Vai mũi khoan là nơi to nhất của dao (đường kính D).
        # Nếu wall_distance - D/2 < 1.0mm -> Cảnh báo đâm thủng (Không an toàn).
        safe_margin = 1.0
        remaining_thickness = wall_distance - (diameter / 2.0)
        
        return remaining_thickness >= safe_margin


class ToolSelector:
    """Engine quyết định loại dao nào được dùng."""
    def __init__(self):
        self.library = DrillBitLibrary()
        self.math_engine = TipClearanceMath()
        
    def select_optimal_drill(self, required_depth: float, wall_distance: float) -> Optional[str]:
        """
        Thuật toán chọn dao ưu tiên theo 9 quy tắc từ Kỹ sư.
        - Ưu tiên 1: D4.2. Nếu an toàn (bề dày >= 1mm) và depth <= 60 -> D4.2.
        - Nếu không đủ bề dày an toàn cho D4.2:
          - Kiểm tra D3.3 (depth <= 50, an toàn).
          - Kiểm tra D2.0 (depth <= 20, an toàn).
        - Nếu lượng dư dư dả nhưng hốc sâu (depth > 60):
          - Kiểm tra D6.0 (depth <= 75).
          - Kiểm tra D8.0 (depth <= 90).
        """
        # Các mốc đánh giá
        bit_42 = self.library.get_bit("D4.2")
        bit_33 = self.library.get_bit("D3.3")
        bit_20 = self.library.get_bit("D2.0")
        bit_60 = self.library.get_bit("D6.0")
        bit_80 = self.library.get_bit("D8.0")
        
        # Hàm nội bộ kiểm tra 1 loại dao
        def is_suitable(bit: dict) -> bool:
            if required_depth > bit["max_depth"]:
                return False
            if not self.math_engine.check_safe_clearance(bit["diameter"], required_depth, wall_distance):
                return False
            return True

        # Nhánh 1: Ưu tiên D4.2 (L <= 60)
        if required_depth <= bit_42["max_depth"]:
            if is_suitable(bit_42):
                return "D4.2"
            else:
                # Thiếu bề dày (hẹp) -> Hạ cấp
                if is_suitable(bit_33):
                    return "D3.3"
                if is_suitable(bit_20):
                    return "D2.0"
                # Không dao nào chui lọt -> Trả về None để kích hoạt logic "Khoan ra ngoài vách"
                return None
                
        # Nhánh 2: Hốc sâu (L > 60)
        else:
            if is_suitable(bit_60):
                return "D6.0"
            if is_suitable(bit_80):
                return "D8.0"
            return None
