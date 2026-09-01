@echo off
chcp 65001 >nul
title 푸드벨 사이트 - 시작 (받기 + 미리보기)
cd /d "%~dp0"

echo.
echo ========================================
echo   [1/2]  깃허브에서 최신 내용 받기
echo ========================================
git pull
if errorlevel 1 (
  echo.
  echo  [!] 받기 실패. 위 메시지를 확인하세요.
  echo      충돌이면 Claude Code 에 "충돌 해결해줘" 라고 하세요.
  echo.
  pause
  exit /b 1
)

echo.
echo ========================================
echo   [2/2]  미리보기 열기
echo ========================================
where python >nul 2>nul
if errorlevel 1 (
  echo  python 이 없어 index.html 을 바로 엽니다.
  start "" "index.html"
  echo  이 창은 닫으셔도 됩니다.
  echo.
  pause
) else (
  start "" "http://localhost:8000"
  echo  브라우저에서 http://localhost:8000 이 열립니다.
  echo.
  echo  ★ 작업이 끝나면 이 검은 창을 닫으면 미리보기가 종료됩니다.
  echo.
  python -m http.server 8000
)
