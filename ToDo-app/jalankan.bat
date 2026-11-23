@echo off
title Aplikasi Tugas Kuliah (HTTPS Secure)
cd /d "%~dp0"
echo ============================================================
echo   Menjalankan Server Aplikasi Tugas Kuliah (HTTPS)
echo   URL: https://127.0.0.1:5000
echo   Status: SSL/TLS Encryption Aktif
echo ============================================================
echo.
echo Membuka browser aman via HTTPS...
start https://127.0.0.1:5000
"C:\Users\acer\AppData\Local\Programs\Python\Python314\python.exe" app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Mencoba dengan launcher python...
    py app.py
)
pause
