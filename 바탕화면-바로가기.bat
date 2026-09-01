@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 바탕화면 바로가기 만들기

echo ============================================
echo    바탕화면에 "푸드벨 시작 / 저장" 아이콘 만들기
echo ============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0바탕화면-바로가기.ps1"

echo.
pause
