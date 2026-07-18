@echo off
title HHU AI Q&A Assistant
setlocal enabledelayedexpansion

:: Use short path (8.3 format) to avoid Chinese path issues
for %%i in ("%~dp0backend.") do set "BE_DIR=%%~fsi"
for %%i in ("%~dp0frontend.") do set "FE_DIR=%%~fsi"

echo.
echo ========================================
echo   HHU AI Wen Da Zhu Shou Zheng Zai Qi Dong
echo ========================================
echo.

echo [1/4] Qi Dong Hou Duan...
start "BE" /D "%BE_DIR%" python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws none

:wait_be
timeout /t 2 /nobreak >nul 2>&1
curl.exe -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 goto wait_be
echo [OK] Hou Duan Qi Dong Cheng Gong

echo [2/4] Qi Dong Qian Duan...
start "FE" /D "%FE_DIR%" cmd /c npx.cmd --yes vite --host 0.0.0.0 --port 5173

:wait_fe
timeout /t 3 /nobreak >nul 2>&1
curl.exe -s http://localhost:5173 >nul 2>&1
if errorlevel 1 goto wait_fe
echo [OK] Qian Duan Qi Dong Cheng Gong

echo [3/4] Da Kai Liu Lan Qi...
start http://localhost:5173

echo [4/4] Wan Cheng!
echo.
echo ========================================
echo   http://localhost:5173
echo   Zhang Hao: admin / admin123
echo.
echo   Liang Ge Du Li Chuang Kou Yi Da Kai
echo   Guan Bi Ta Men Ji Ke Ting Zhi Fu Wu
echo ========================================
echo.
echo An Ren Yi Jian Guan Bi Ci Chuang Kou
pause >nul
