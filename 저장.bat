@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 푸드벨 사이트 - 저장 (GitHub 업로드)

echo ============================================
echo    푸드벨 사이트 - 저장 (GitHub 업로드)
echo ============================================
echo.
echo [1/4] 먼저 최신 내용을 받는 중...
echo.
git pull --no-edit
if errorlevel 1 (
  echo.
  echo  !! 받기 실패 또는 충돌. Claude Code 에 "충돌 해결해줘" 라고 하세요.
  echo.
  pause
  exit /b 1
)

echo.
echo [2/4] 바뀐 파일 목록 :
echo.
git status --short
echo.

set "MSG="
set /p "MSG=[3/4] 무엇을 바꿨나요? (한 줄 설명 / 그냥 엔터치면 날짜로 저장) : "
if "%MSG%"=="" set "MSG=작업 저장 %DATE% %TIME%"

git add -A
git commit -m "%MSG%"
if errorlevel 1 (
  echo.
  echo  (바뀐 내용이 없어서 올릴 것이 없습니다. 종료합니다.)
  echo.
  pause
  exit /b 0
)

echo.
echo [4/4] GitHub 에 올리는 중...
echo.
git push
if errorlevel 1 (
  echo.
  echo  !! 업로드 실패. 위 메시지를 확인하세요.
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================
echo    완료! GitHub 에 저장되었습니다.
echo ============================================
echo.
pause
