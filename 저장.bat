@echo off
chcp 65001 >nul
title 푸드벨 사이트 - 저장 (깃허브에 올리기)
cd /d "%~dp0"

echo.
echo ========================================
echo   [1/4]  올리기 전에 최신부터 받기
echo ========================================
git pull
if errorlevel 1 (
  echo.
  echo  [!] 받기 실패. 충돌이면 Claude Code 에 "충돌 해결해줘" 라고 하세요.
  echo.
  pause
  exit /b 1
)

echo.
echo ========================================
echo   [2/4]  이번에 바뀐 파일
echo ========================================
git status --short
echo.

set "msg="
set /p "msg=[3/4] 무엇을 바꿨나요?  (그냥 엔터치면 날짜로 저장): "
if "%msg%"=="" set "msg=작업 %date% %time%"

echo.
echo ========================================
echo   [4/4]  깃허브에 올리는 중...
echo ========================================
git add -A
git commit -m "%msg%"
git push

echo.
echo ==============  완료!  ==============
echo.
pause
