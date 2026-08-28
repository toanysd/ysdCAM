# YSD-CAM: Domain Rules for Hole Calculation

Tài liệu này lưu trữ toàn bộ các Quy tắc Nghiệp Vụ (Domain Rules) và Ràng buộc Hình học (Geometric Constraints) để xác định vị trí lỗ hút chân không (0.6mm) và lỗ mồi mặt sau (Back Ana) cho quy trình gia công khuôn hút chân không.

## 1. Thuật toán Wire-Walk (Đi dọc đường bao pocket)

### Nguyên tắc cốt lõi
Thay vì xử lý từng cạnh (Edge) độc lập, thuật toán đi dọc toàn bộ **đường bao khép kín (Wire)** của pocket để hiểu cấu trúc topo.

### Trình tự ưu tiên đặt lỗ (Priority Order)
1. **Gom cụm và Dãn cách (Clearance)**: Lỗ được rải cách vách 1.5mm, nhưng sẽ tự động dời ra xa nhau hoặc gộp lại nếu khoảng cách không đủ an toàn.
2. **Đỉnh cung tròn (Arc Apex)**: Tùy thuộc vào góc lõm hay lồi. Góc lõm (vào trong) đặt 1 lỗ ở đỉnh. Góc lồi (ra ngoài) đặt lỗ ở đỉnh và 2 đầu cung.
3. **Trung điểm cạnh thẳng dài**: Nếu $L > 20mm$, chia đều rải lỗ ($\lceil L/20 \rceil$ phân đoạn).

### Quy tắc Ranh giới (Boundary Edge Filter)
- Mỗi cạnh trên đường bao được kiểm tra **Adjacent Face Z-max**.
- Nếu `adjacent_max_z ≤ face_z + 0.1mm` → Cạnh biên (thành đi xuống) → **KHÔNG sinh lỗ**.
- Chỉ các cạnh có thành đi LÊN (wall-up) mới được xử lý.

## 2. Phân tích Cạnh & Cung tròn (Edge & Arc Traversal)
- **Góc & Đỉnh:** Lỗ luôn được ưu tiên đặt tại các góc giao (Vertices). Khoảng cách lùi vào là 1.5mm nhưng sẽ linh hoạt dịch chuyển (đẩy ra xa) nếu va chạm với các lỗ khác.
- **Cung tròn (Arcs):** Do đặc thù phay Endmill, các góc luôn là cung R.
  - *Góc lõm (Concave - ăn vào lòng khuôn):* Chỉ đặt **1 lỗ duy nhất** tại đỉnh cung (vị trí sâu nhất).
  - *Góc lồi (Convex - bo ngoài):* Đặt lỗ tại đỉnh cung lồi, **VÀ** thường tạo thêm 2 lỗ ở 2 đầu tiếp tuyến của cung tròn đó.
- **Cạnh thẳng (Straight Edges):**
  - Đặt lỗ ở 2 góc trước.
  - Nếu chiều dài $L > 20mm$: Đặt thêm lỗ ở trung điểm. Nếu vẫn dài, chia đều rải lỗ.
  - *Đóng gióng (Alignment):* Thuật toán sẽ ưu tiên trượt vị trí lỗ (dọc theo cạnh) để gióng thẳng hàng (gióng X hoặc Y) với các lỗ của pocket lân cận.
- **Pocket hẹp & Đáy lõm R (D3.3 & L<25mm):**
  - Nếu pocket là rãnh dài hẹp (Slot): Đặt lỗ ở **hai đầu** rãnh.
  - Nếu pocket là đáy bị lõm xuống dạng cung R (vuông vức): Đặt **1 lỗ duy nhất** ở chính giữa đỉnh lõm (Centroid).
- **Ranh giới ngoài (Outer Boundary):** Chỉ sinh lỗ tại các giao tuyến mà ở đó vách đi **lên** (Positive Z). Nếu vách đi xuống (bậc lồi), tuyệt đối không sinh lỗ.

## 3. Chiến lược Chọn Dao & Bề dày an toàn (Tool Selection & Tip Clearance)
- **Danh sách Dao (Đường kính D - Chiều sâu tối đa L):**
  - **D4.2:** $L \le 60mm$ (Ưu tiên số 1 - Tốc độ khoan nhanh nhất).
  - **D6.0:** $L \le 75mm$ (Ưu tiên số 2 - Dành cho hốc sâu không thể dùng D4.2).
  - **D8.0:** $L \le 90mm$ (Chỉ dùng cho hốc cực kỳ sâu).
  - **D3.3:** $L \le 50mm$ (Hạn chế, dùng khi không đủ lượng dư an toàn cho D4.2 hoặc rãnh hẹp < 5mm).
  - **D2.0:** $L \le 20mm$ (Tối kỵ, chỉ dùng khi vách cực mỏng và rất nông).
- **Thuật toán Lượng dư Mũi khoan 118 độ (Drill Tip Clearance):**
  - Mũi khoan tiêu chuẩn có góc ở đỉnh là $118^\circ$ (góc vát chóp nón là $59^\circ$). Chiều cao phần chóp mũi khoan (từ đỉnh nhọn đến vai mũi khoan) là $h = \frac{D/2}{\tan(59^\circ)}$.
  - Do thành khuôn thường được vát nghiêng (draft angle), vị trí có lượng dư nhôm mỏng nhất chính là vị trí **vai mũi khoan** (nằm cách đáy pocket một khoảng là $h + 2mm$).
  - **Quy tắc An toàn:** Từ vị trí vai mũi khoan, phóng tia (Ray-cast) theo phương ngang ra thành khuôn. Khoảng cách (lượng dư thịt nhôm) bắt buộc phải $\ge 1.0mm$.
- **Luật chuyển đổi dao tự động (Tool Fallback):**
  - Nếu lượng dư $< 1.0mm$ khi dùng D4.2, hệ thống tự động **hạ cấp dao** xuống D3.3 hoặc D2.0 (nếu chiều sâu L cho phép).
  - Ngược lại, nếu lượng dư dồi dào nhưng chiều sâu $> 60mm$, hệ thống tự động **thăng cấp dao** lên D6.0 hoặc D8.0.
  - Nếu không có dao nào thỏa mãn (ví dụ vách quá mỏng cho cả D2.0 hoặc D2.0 không đủ dài), hệ thống chuyển sang quy tắc **Rib siêu mỏng** (mượn đáy bên cạnh).

## 4. Quy tắc Gom cụm (Clustering) & Khoan chung lỗ
- **Không bao giờ lấy trung bình chiều sâu (Z/Depth):** Khi gộp các lỗ từ các bậc có độ sâu khác nhau, tuyệt đối KHÔNG tính trung bình cộng chiều sâu. Tất cả các lỗ ở lớp/layer nào phải được bảo toàn đúng chiều sâu của lớp đó (chừa đúng 2mm thịt).
- **Khoan chung vào một lỗ (Shared Hole):** Thay vì khoan 2 lỗ D4.2 ở 2 bậc cao thấp khác nhau sát vách, ta chỉ khoan **MỘT lỗ D4.2 ở bậc SÂU HƠN**. Mũi khoan 0.6mm ở cả 2 bậc sẽ được khoan xiên chung vào khoảng không của lỗ D4.2 này.
- **Xê dịch XY (XY Shift):** Việc gom cụm chỉ gây ra xê dịch tọa độ của lỗ D4.2 trong mặt phẳng ngang (X, Y) để đảm bảo cả 2 lỗ chân không từ 2 bậc đều có thể đâm xiên vào một cách thoải mái, hoàn toàn không làm thay đổi trục Z.
- **Hạn chế dùng chung lỗ (Sharing Restriction):** 
  - Nếu 2 góc của 2 pocket kề nhau, **ưu tiên tách làm 2 lỗ Back Ana riêng biệt** để thợ dễ khoan thẳng đứng.
  - Chỉ gộp khi khoảng cách quá hẹp không đủ chừa $0.8mm$ thịt giữa 2 lỗ D4.2.

## 4.5 Không gian thao tác Khoan tay (Ergonomic Clearance)
- **Tối giản góc nghiêng:** Mặc dù mũi khoan phải nghiêng để né cán mài khi khoan vách đứng, nhưng thuật toán tính toán góc nghiêng động học (Kinematic Tilt) tạm thời bị vô hiệu hóa để tránh gây sai số vị trí rải lỗ. Tâm lỗ D4.2 sẽ mặc định được lùi vào 1.5mm so với vách.

## 5. Xử lý Thành/Rib siêu mỏng & Bậc dốc
- **Rib siêu mỏng:** Nếu thành vách giữa 2 pocket quá mỏng, **không được cố đặt lỗ bên dưới vách**. Giải pháp: Kéo lỗ xuống mặt phẳng đáy sâu nhất nằm kề bên.
- **Bậc góc hẹp (Narrow Corner Steps):** Nếu bậc nông rộng, đặt 2 lỗ riêng. Nếu bậc trên và dưới sát nhau, khoan chung 1 lỗ từ đáy bậc dưới xiên lên hút cho cả bậc trên.

## 6. Trình tự xử lý (Processing Order)
1. Xử lý pocket nhỏ trước, pocket lớn sau.
2. Trong mỗi pocket: Góc → Đỉnh cung → Trung điểm cạnh dài.
3. Nếu lỗ dày quá: Ưu tiên xê dịch lỗ về phía thành khuôn hoặc lòng pocket.
4. Chỉ khi không còn không gian xê dịch mới tính đến thêm lỗ D3.3.
