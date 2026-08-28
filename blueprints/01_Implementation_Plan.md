# KẾ HOẠCH TRIỂN KHAI DỰ ÁN CAM-PROCESSING (AG-EA STANDARD)

**Triết lý cốt lõi:** Tuân thủ AG-EA Standard (Clean Architecture & Domain-Driven Design).
**Ngôn ngữ lập trình:** Python (phù hợp nhất với các thư viện hình học tính toán và AI/Data).

---

## GIAI ĐOẠN 0: KHỞI TẠO NỀN MÓNG (FOUNDATION SETUP)
**Mục tiêu:** Xây dựng khung xương dự án vững chắc như một doanh nghiệp.
1. Khởi tạo môi trường ảo Python (Virtual Environment).
2. Thiết lập cấu trúc thư mục 4 phòng ban (Layers):
   - `src/domain/` (Hình học)
   - `src/application/` (Luồng xử lý)
   - `src/infrastructure/` (Đọc STEP / Ghi G-Code)
   - `src/presentation/` (Giao diện dòng lệnh - CLI)
3. Cài đặt các thư viện lõi: `cadquery` (hoặc `pythonocc-core` / `Ocp`) để đọc B-Rep CAD, `numpy` (toán học ma trận), `scikit-learn` (phân cụm).

---

## GIAI ĐOẠN 1: XÂY DỰNG PHÒNG HẠ TẦNG (INFRASTRUCTURE LAYER)
**Mục tiêu:** Hệ thống có khả năng "nhìn" thấy vật thể vật lý và "viết" được ngôn ngữ của máy CNC.
1. **Module Đọc CAD (`STEPReader`):**
   - Nhiệm vụ: Tải file STEP/IGES vào bộ nhớ. Trả về cấu trúc dữ liệu lưới (Mesh) hoặc Boundary Representation (B-Rep).
2. **Module Ghi NC (`GCodeWriter`):**
   - Nhiệm vụ: Nhận một danh sách tọa độ (X, Y, Z, Layer), tự động format thành cú pháp `G83` an toàn cho máy phay mặt sau (có phần đầu dao, bù dao chuẩn).

*Kiểm thử Giai đoạn 1:* Viết Unit Test nạp một file CAD bất kỳ và đếm số mặt phẳng. Xuất file `.nc` nháp.

---

## GIAI ĐOẠN 2: XÂY DỰNG PHÒNG NGHIỆP VỤ (DOMAIN LAYER)
**Mục tiêu:** Dạy cho máy tính "Know-how" khoan cầm tay của con người.
*(Lưu ý: Tuyệt đối không import `cadquery` hay thư viện ngoài vào đây, chỉ dùng cấu trúc dữ liệu thuần túy và Toán học).*
1. **Module Nhận diện Mặt Đáy (`FaceAnalyzer`):**
   - Thuật toán phân tích pháp tuyến (Normal Vectors) để bóc tách toàn bộ "mặt hướng lên" (Mặt đáy pocket).
2. **Thuật toán Vét Mép & Đặt Lỗ (`EdgeTraversal`):**
   - Trích xuất đường viền mép đáy. Xác định đỉnh, góc bo, và trung điểm các đoạn thẳng dài. Đặt điểm neo 0.6mm (Front Hole).
3. **Thuật toán Tránh Vách Thủ Công (`KinematicClearance`):**
   - Input: Chiều sâu pocket, bán kính cán dao (3mm), tọa độ mép khoan.
   - Xử lý: Tính góc nghiêng $\theta$ an toàn, tính lượng tịnh tiến vector ngang $\Delta$.
   - Output: Tọa độ D4.2 lý tưởng nằm dưới vách (Back Ana Target).

*Kiểm thử Giai đoạn 2:* Đưa input tọa độ giả lập, kiểm tra xem máy có nội suy góc nghiêng và vector dịch chuyển đúng toán học không.

---

## GIAI ĐOẠN 3: XÂY DỰNG PHÒNG ĐIỀU HÀNH (APPLICATION LAYER)
**Mục tiêu:** Ráp nối luồng làm việc tự động (Pipeline).
1. **Nhân bản Hình học (Pattern Propagation):**
   - Phân tích các mặt đáy giống hệt nhau. Chỉ chạy thuật toán Giai đoạn 2 cho 1 Pocket Master, sau đó nhân bản ma trận sang các pocket khác.
2. **Giải quyết Xung đột & Phân Cụm (Clustering & Collision):**
   - Chạy thuật toán DBSCAN để gom cụm các lỗ 0.6 gần nhau vào chung 1 lỗ D4.2.
   - Kiểm tra khoảng cách tối thiểu $\ge 0.8mm$.
3. **Use Case (`GenerateMoldCAMUseCase`):**
   - Người dùng gọi Use Case -> Gọi Giai đoạn 1 đọc file -> Gọi Giai đoạn 2 để tính toán -> Phân layer theo độ sâu Z -> Gọi Giai đoạn 1 xuất file DXF hoặc G-Code.

---

## GIAI ĐOẠN 3.5: HỆ THỐNG KIỂM ĐỊNH AN TOÀN (VERIFICATION MODULE)
**Mục tiêu:** Xóa bỏ rủi ro "Black-box", đảm bảo an toàn tuyệt đối trước khi chạy máy CNC.
1. **Module `ThicknessChecker` (Tầng Domain):**
   - Quét tia (Ray-cast) từ tâm lỗ D4.2 lên mặt pocket để đo chính xác bề dày lớp thịt nhôm còn lại. Đảm bảo đúng 2mm (hoặc $\pm 0.1mm$).
   - Báo lỗi ĐỎ nếu phát hiện lỗ đâm thủng mặt khuôn.
2. **Module `CollisionDetector` (Tầng Domain):**
   - Quét toàn bộ tọa độ lỗ, phát hiện các điểm giao nhau, đè lên nhau hoặc nằm quá sát vách thẳng đứng.
3. **Module `DXFWriter` (Tầng Infrastructure):**
   - Xuất bản vẽ 2D (`.dxf`) của các lỗ Back Ana (phân layer theo độ sâu) để người dùng mở lên bằng AutoCAD/MasterCAM kiểm tra chéo.

---

## GIAI ĐOẠN 4: GIAO DIỆN ĐỒ HỌA & MÔ PHỎNG 3D (PRESENTATION LAYER)
**Mục tiêu:** Xây dựng phần mềm trực quan ngang tầm MasterCAM/Fusion360.
1. **Kiến trúc Hệ thống:** Thay vì CLI, chúng ta sẽ xây dựng cấu trúc Client-Server hiện đại:
   - **Backend API (FastAPI - Python):** Xử lý hình học nặng, chạy thuật toán và xuất file.
   - **Frontend UI (React/Vite + Three.js):** Giao diện tương tác người dùng trên trình duyệt.
2. **Tính năng Giao diện:**
   - **Màn hình View 3D:** Hiển thị phôi khuôn, vẽ đường sinh (cylinder) của mũi khoan D4.2 và mũi 0.6mm xiên góc để người dùng nhìn tận mắt không gian 3D.
   - **Bảng Cảnh Báo (Dashboard):** Thống kê số lỗ, highlight màu đỏ các lỗ "Cảnh báo thủng", "Sai độ dày".
   - **Tương tác Chỉnh sửa:** Cho phép người dùng click vào lỗ trên màn hình 3D để xóa, dịch chuyển hoặc đổi thông số trước khi bấm "Xuất G-Code".
   - **Xuất File Theo Bước:** 
     - Nút [Xuất DXF Kiểm tra].
     - Nút [Xuất G-Code Layer 1], [Xuất G-Code Layer 2]...
