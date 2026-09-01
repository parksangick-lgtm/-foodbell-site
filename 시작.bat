@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 푸드벨 사이트 - 작업 시작

echo ============================================
echo    푸드벨 사이트 - 작업 시작
echo ============================================
echo.
echo [1/2] GitHub 에서 최신 내용을 받는 중...
echo.
git pull
if errorlevel 1 (
  echo.
  echo  !! 받기에 실패했습니다. 위 메시지를 확인하세요.
  echo     충돌이면 Claude Code 에 "충돌 해결해줘" 라고 하세요.
  echo.
  pause
  exit /b 1
)

echo.
echo [2/2] 미리보기 서버를 켭니다.
echo.
echo    브라우저에서 이 주소를 여세요 :  http://localhost:8000
echo.
echo    ( 미리보기를 끝내려면 이 창을 닫으세요 )
echo ============================================
echo.

start "" http://localhost:8000
python -m http.server 8000 || py -m http.server 8000

pause
