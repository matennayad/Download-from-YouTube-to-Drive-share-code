@echo off
chcp 65001 >nul
title KAN Proxy - 3proxy
echo ============================================
echo   KAN Proxy - 3proxy
echo   HTTP proxy on port 3128
echo ============================================
echo.
echo הפרוקסי רץ. אל תסגור את החלון הזה.
echo כדי לעצור: סגור את החלון או לחץ Ctrl+C
echo.
3proxy.exe 3proxy.cfg
pause
