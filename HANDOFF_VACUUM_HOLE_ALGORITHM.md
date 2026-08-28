# HANDOFF: Thuật toán Đặt Lỗ Khoan Mồi (Back Ana / Vacuum Hole)

> **Ngày tạo:** 2026-06-10  
> **Mục đích:** Tài liệu bàn giao cho phiên chat mới. Đọc file này để hiểu toàn bộ bối cảnh.

---

## 1. BÀI TOÁN

Phần mềm ysdCAM nhận đầu vào là file STEP 3D của khuôn hút chân không (vacuum mold).  
Nhiệm vụ: **Tự động tính toán vị trí đặt các lỗ khoan mồi (Back Ana holes)** ở mặt sau khuôn.

### Quy trình thực tế:
1. Thợ khoan sẽ khoan lỗ hút chân không d0.6mm **từ mặt trước** khuôn, xiên vào các góc pocket
2. Lỗ d0.6mm cần "thông" xuống mặt sau → cần **lỗ mồi (back ana)** ở mặt sau
3. Phần mềm chỉ cần tính toán và vẽ **lỗ mồi mặt sau** (d2.2 ~ d8.0mm)
4. Lỗ d0.6mm do thợ tự xác định khi khoan thực tế

---

## 2. QUY TẮC NGHIỆP VỤ (Domain Rules)

**File tham chiếu chính:** `blueprints/02_Domain_Rules_Hole_Calculation.md`

### 2.1 Vị trí đặt lỗ (Wire-Walk Algorithm)
- Đi dọc đường bao khép kín (Wire) của pocket
- **Góc lõm (Concave):** 1 lỗ tại đỉnh cung (vị trí sâu nhất)
- **Góc lồi (Convex):** 1 lỗ tại đỉnh + 2 lỗ ở 2 đầu tiếp tuyến
- **Cạnh thẳng dài > 20mm:** Chia đều rải lỗ (⌈L/20⌉ phân đoạn)
- **Slot (rãnh hẹp):** 2 lỗ ở 2 đầu rãnh
- **Bisector offset:** Tâm lỗ mồi lùi vào 1.5mm so với vách khuôn

### 2.2 Chọn mũi khoan
| Mũi | Đường kính | Chiều sâu max |
|-----|-----------|--------------|
| D2.2 | 2.2mm | 20mm |
| D3.3 | 3.3mm | 50mm |
| **D4.2** | **4.2mm** | **60mm** (ưu tiên #1) |
| D6.0 | 6.0mm | 75mm |
| D8.0 | 8.0mm | 90mm |

- Ưu tiên D4.2 (tốc độ nhanh, lỗ đủ rộng cho d0.6 xiên vào)
- Hạ cấp D3.3/D2.2 nếu thành hẹp
- Thăng cấp D6.0/D8.0 nếu pocket sâu hơn 60mm

### 2.3 Ràng buộc an toàn
- **Thịt Z (Z-flesh):** Luôn chừa 2mm từ đáy pocket đến đỉnh mũi khoan
- **Thịt ngang (Wall clearance):** ≥ 1.0mm từ vai mũi khoan (tính góc vát 118°) đến thành
- **Thịt giữa 2 lỗ:** ≥ 0.8mm
- **Gom cụm:** Chỉ khi BẤT KHẢ KHÁNG. Ưu tiên đẩy lỗ ra xa trước

### 2.4 Quyết định của user (đã phê duyệt)
- `has_wall_up`: **Tạm bỏ qua**, đặt lỗ tại tất cả góc/bậc trước
- Polygon Z=0: **Giữ nguyên 1 polygon lớn**, Wire-Walk chạy quanh toàn bộ

---

## 3. PHÂN TÍCH LỖI CODE HIỆN TẠI

### 3.1 Code hiện tại: `vacuum_hole_generator.py` (309 dòng)
**Vấn đề nghiêm trọng:**
1. **Mất cấu trúc topo:** Chỉ lọc vertex trùng `original_endpoints`, không biết đâu là nối LINE↔ARC
2. **Không rải lỗ trên cạnh dài:** Cạnh 50mm không sinh lỗ nào ở giữa
3. **Không phân biệt đỉnh cung vs điểm nối:** Chỉ dùng `poly.contains(midpoint)` 
4. **`global_merge` sai:** Lấy trung bình XY → lỗ trôi ra giữa 2 pocket
5. **Không tính góc vát 118°:** Chỉ buffer polygon đơn giản

### 3.2 Code tốt đã bị bỏ quên: `polygon_hole_strategy.py` (391 dòng)
**Đã triển khai đúng Wire-Walk:**
- `_sort_and_orient_edges()` — sắp xếp nối mạch
- `_merge_collinear_lines()` — gộp đường thẳng cùng hướng
- `_merge_contiguous_arcs()` — gộp cung tròn cùng tâm/bán kính
- `calculate_holes()` — tính bisector, phân biệt corner/arc_peak/line
- `_deduplicate_holes()` — loại trùng

---

## 4. KẾ HOẠCH SỬA (ĐÃ PHÊ DUYỆT)

### Bước 1: Kết nối `PolygonHoleStrategy` vào pipeline
Sửa `generate_cam_use_case.py`:
- Thay `VacuumHoleGenerator.generate_holes()` → `PolygonHoleStrategy.calculate_holes()`
- Truyền `layer_wires` (đã có sẵn) vào `PolygonHoleStrategy`

### Bước 2: Viết lại `VacuumHoleGenerator` thành module chọn dao
- Input: danh sách `(x, y, z, hole_type, is_valid_wall)` từ `PolygonHoleStrategy`
- Chọn mũi khoan theo depth + khoảng cách thành
- Đẩy tâm lỗ theo bisector = `D/2 + 1.0mm`
- Kiểm tra khoảng cách thịt ≥ 1.0mm

### Bước 3: Sửa `global_merge`
- KHÔNG lấy trung bình XY khi gộp
- Giữ lỗ ở vị trí sâu hơn
- Ưu tiên đẩy ra xa trước khi gộp

### Bước 4: Tạm bỏ qua `has_wall_up`
- Đặt lỗ tại tất cả góc/bậc, user sẽ kiểm tra kết quả trước

---

## 5. CẤU TRÚC FILE QUAN TRỌNG

```
D:\AntiGravity_Workspace\apps\ysdCAM\
├── blueprints\
│   ├── 01_Implementation_Plan.md          # Kế hoạch gốc 4 giai đoạn
│   └── 02_Domain_Rules_Hole_Calculation.md # QUY TẮC NGHIỆP VỤ CHÍNH
├── src\plugins\ysd_flow\
│   ├── generate_cam_use_case.py           # Pipeline chính (252 dòng)
│   ├── vacuum_hole_generator.py           # Module lỗi cần sửa (309 dòng)
│   └── polygon_hole_strategy.py           # Module tốt cần tái sử dụng (391 dòng)
├── frontend\                              # React/Vite + Three.js UI
├── temp_workspace\
│   └── IRI-002D(Q)_3D.step               # File STEP test
└── HANDOFF_VACUUM_HOLE_ALGORITHM.md       # File này
```

---

## 6. CÁCH CHẠY THỬ

```powershell
cd D:\AntiGravity_Workspace\apps\ysdCAM

# Test backend
$env:PYTHONIOENCODING="utf8"
python -c "
from src.plugins.ysd_flow.generate_cam_use_case import GenerateMoldCAMUseCase
uc = GenerateMoldCAMUseCase('temp_workspace/IRI-002D(Q)_3D.step')
res = uc.execute()
holes = [h for h in res['holes'] if 'back' in h.get('hole_type', '')]
print('Back drill holes:', len(holes))
"

# Chạy UI (backend + frontend)
# Backend: uvicorn src.api.main:app --host 0.0.0.0 --port 8888 --reload
# Frontend: cd frontend && npm run dev
```

---

## 7. HÌNH ẢNH THAM KHẢO
- Ví dụ tính toán thủ công của user: `C:\Users\遠藤 健一\.gemini\antigravity\brain\tempmediaStorage\media__1780973011689.png`

---

## 8. TÓM TẮT CHO AI MỚI

**Bạn cần làm:**
1. Đọc file `blueprints/02_Domain_Rules_Hole_Calculation.md` để hiểu domain rules
2. Đọc file `src/plugins/ysd_flow/polygon_hole_strategy.py` — đây là code TỐT cần tái sử dụng
3. Sửa `generate_cam_use_case.py` để gọi `PolygonHoleStrategy` thay vì `VacuumHoleGenerator`
4. Viết lại `VacuumHoleGenerator` thành module chọn dao + kiểm tra va chạm
5. Sửa `global_merge` không lấy trung bình XY
6. Test với file `temp_workspace/IRI-002D(Q)_3D.step`
7. Kiểm tra kết quả trên UI (localhost:5173)
