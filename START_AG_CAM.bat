@echo off
title AG-CAM Enterprise Launcher
echo ===================================================
echo       Khoi dong he thong AG-CAM Enterprise
echo ===================================================
echo.

echo [1/3] Khoi dong Backend Server (Python/FastAPI)...
start "AG-CAM Backend" cmd /k "call D:\Miniconda3\condabin\conda.bat activate ysdcam_env && python -m uvicorn src.presentation.api:app --host 0.0.0.0 --port 8888 --reload"

echo [2/3] Khoi dong Frontend Server (React/Vite)...
start "AG-CAM Frontend" cmd /k "cd frontend && npm run dev"

echo [3/3] Dang doi Server khoi dong de mo trinh duyet...
timeout /t 5 /nobreak >nul

echo Mo trinh duyet...
start http://localhost:5173

echo.
echo Hoan tat! 
echo (Luu y: De tat phan mem, hay tat 2 cua so den CMD vuaga duoc mo ra)
pause
