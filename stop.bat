@echo off
echo Ting Zhi HHU RAG Fu Wu...
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
echo [OK] Yi Ting Zhi
echo Ni Ke Yi Guan Bi Xiang Ying De Chuang Kou Le
timeout /t 3 /nobreak >nul
