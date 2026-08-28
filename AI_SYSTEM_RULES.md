# HƯỚNG DẪN VÀ QUY TẮC HỆ THỐNG DÀNH CHO AI (AI SYSTEM RULES)
*File này cung cấp ngữ cảnh bắt buộc cho bất kỳ AI Agent nào khi làm việc trong môi trường này.*

## KIẾN TRÚC ANTIGRAVITY USB PORTABLE (STANDALONE V3.0)

Hệ thống này được thiết lập theo cơ chế **"USB Portable Standalone"**: code trực tiếp trên USB, mỗi dự án hoàn toàn độc lập.

### 1. Kiến trúc lưu trữ (Storage Architecture)
- **Mã nguồn + node_modules:** Nằm trực tiếp trên USB (ổ G: hoặc tùy máy).
- **Mỗi dự án là STANDALONE:** Có `package.json`, `node_modules`, các file config riêng.
- **KHÔNG dùng Monorepo:** Không dùng `pnpm-workspace.yaml`, `npm workspaces`, hay bất kỳ cơ chế nào tạo Symlink.
- **QUY TẮC AI:** Code trực tiếp trên USB. Không cần copy sang ổ cứng nội bộ.

### 2. Quản lý Dependencies
- **DÙNG `npm`:** Tuyệt đối KHÔNG dùng `pnpm` (pnpm tạo Symlink -> Windows chặn trên USB).
- **`node_modules`:** Nằm trong từng thư mục dự án, KHÔNG chia sẻ giữa các app.
- **Khi đổi máy:**
  - Xóa `.next` (cache Next.js chứa native binaries cũ)
  - Chạy `npx prisma generate` (nếu dự án dùng Prisma)
  - `node_modules` giữ nguyên, KHÔNG cần cài lại

### 3. Quy trình làm việc
1. Cắm USB vào máy tính
2. Chạy `USB_START.bat` ở root (hoặc file `start_*.bat` trong từng dự án)
3. Script tự động: xóa cache → kiểm tra thư viện → mở trình duyệt → khởi động server
4. Khi xong: Ctrl+C để dừng, rút USB an toàn

### 4. Quy định khi Coding
- **No Hardcoding Drives:** Tuyệt đối không hardcode đường dẫn ổ đĩa như `C:\` hay `G:\` trong mã nguồn.
- **Port Caching:** Chú ý giải phóng cổng (port) vì đôi khi server bị treo.
- **Cấu hình Next.js:**
  - `"dev": "next dev -p PORT"`: Dùng Turbopack mặc định.
  - `"build": "next build"`: KHÔNG dùng `--turbo` khi build production.

### 5. Quy tắc viết file .bat
- Chỉ dùng cú pháp batch cơ bản (`if exist`, `if errorlevel`, `call`)
- KHÔNG dùng `setlocal enabledelayedexpansion` hay `!variable!` (dễ gây lỗi cú pháp)
- KHÔNG dùng tiếng Việt có dấu trong file .bat
- Luôn có `cd /d "%~dp0"` ở đầu file
- Luôn có `start "" "http://localhost:PORT"` để tự động mở trình duyệt
- Luôn kiểm tra `if not exist "node_modules"` trước khi chạy `npm install`
- Xem file mẫu: `apps/_template_run.bat`

### 6. Quản lý File Rác & Debug (Cleanup Rules)
- Nếu AI cần tạo file script nháp để test/debug, BẮT BUỘC phải tạo trong `temp_ai/` của dự án đó.
- Tuyệt đối không xả rác file test bừa bãi ra thư mục gốc dự án.
