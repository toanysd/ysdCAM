# AntiGravity - USB Portable Workspace Guide

## Phuong an: Code truc tiep tren USB (Standalone)

Moi du an trong `apps/` la mot project doc lap, KHONG phu thuoc monorepo.

## Quy tac chung

### 1. Khong dung pnpm, chi dung npm
- `pnpm` tao Symlink -> Windows chan khi khong co quyen Admin -> LOI
- `npm` copy file vat ly -> Luon thanh cong tren USB

### 2. Moi du an tu quan ly node_modules cua minh
- Khong dung `pnpm-workspace.yaml` hay `npm workspaces`
- Moi du an co `package.json` rieng, `node_modules` rieng
- Chay `npm install` truc tiep trong thu muc du an

### 3. Quy tac viet file .bat
- Chi dung cu phap batch co ban (`if exist`, `if errorlevel`, `call`)
- KHONG dung `setlocal enabledelayedexpansion` hay `!variable!` (de gay loi)
- KHONG dung tieng Viet co dau
- Luon co `cd /d "%~dp0"` o dau file
- Luon co `start "" "http://localhost:PORT"` de tu dong mo trinh duyet
- Luon kiem tra `if not exist "node_modules"` truoc khi chay `npm install`
- Voi du an Next.js: xoa `.next` truoc khi chay (tranh loi khi doi may)

### 4. Khi doi may tinh
- Chi can cam USB va chay file `.bat` cua du an
- Lan dau: `npm install` tu dong chay (~1-2 phut)
- Lan sau: `node_modules` da co, khoi dong ngay (~1 giay)
- Voi du an dung Prisma: `npx prisma generate` tu dong chay lai

## Cau truc thu muc

```
G:\AntiGravity\
├── USB_START.bat          <- Launcher tong hop (chon du an)
├── apps\
│   ├── _template_run.bat  <- Mau file bat cho du an moi
│   ├── nenkin\            <- Du an doc lap
│   │   ├── start_nenkin.bat
│   │   ├── package.json
│   │   ├── node_modules\  <- Thu vien rieng
│   │   ├── src\
│   │   └── prisma\
│   ├── ipc\               <- Du an doc lap
│   │   ├── start_ipc.bat
│   │   └── ...
│   └── [du_an_khac]\
├── packages\              <- Thu vien dung chung (khong bat buoc)
└── infrastructure\
```

## Cach tao du an moi
1. Copy file `apps/_template_run.bat` vao thu muc du an moi
2. Doi ten thanh `start_[ten_du_an].bat`
3. Sua port va ten du an trong file bat
4. Chay `npm init` va `npm install` cac thu vien can thiet
