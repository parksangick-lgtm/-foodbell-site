@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 푸드벨 견적서

echo ============================================
echo    푸드벨 견적서
echo ============================================
echo.

rem 이미 켜져 있는 미리보기 서버가 있으면 그대로 쓴다.
rem (파일을 그냥 두 번 눌러 여는 방식은 입력 자동저장이 안 되므로 쓰지 않는다)

curl -s -o nul -m 2 http://127.0.0.1:5500/sije-quote.html
if not errorlevel 1 (
  echo 켜져 있는 미리보기 5500 번으로 견적서를 엽니다.
  start "" http://127.0.0.1:5500/sije-quote.html
  exit /b 0
)

curl -s -o nul -m 2 http://127.0.0.1:8000/sije-quote.html
if not errorlevel 1 (
  echo 켜져 있는 미리보기 8000 번으로 견적서를 엽니다.
  start "" http://127.0.0.1:8000/sije-quote.html
  exit /b 0
)

echo 미리보기 서버를 켜고 견적서를 엽니다.
echo.
echo    ( 견적서를 다 쓰셨으면 이 창을 닫으세요 )
echo ============================================
echo.

start "" http://127.0.0.1:8000/sije-quote.html
python -m http.server 8000 || py -m http.server 8000

pause
