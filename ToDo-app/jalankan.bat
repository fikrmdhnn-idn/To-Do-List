@echo off
title Aplikasi Tugas Kuliah
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan Server Aplikasi Tugas Kuliah
echo   URL: http://127.0.0.1:5000
echo ============================================================
echo.
echo Membuka browser otomatis...
start http://127.0.0.1:5000
"C:\Users\acer\AppData\Local\Programs\Python\Python314\python.exe" app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Mencoba dengan launcher python...
    py app.py
)
pause

