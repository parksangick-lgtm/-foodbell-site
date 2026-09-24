@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 푸드벨 사이트 - 작업 시작

echo ============================================
echo    푸드벨 사이트 - 작업 시작
echo ============================================
echo.
echo [1/3] 지난번 저장이 잘 올라갔는지 확인 중...
echo.
call :check_not_pushed

echo.
echo [2/3] GitHub 에서 최신 내용을 받는 중...
echo.
git pull
if errorlevel 1 (
  echo.
  echo  !! 받기에 실패했습니다. 위 메시지를 확인하세요.
  echo     충돌이면 Claude Code 에 "충돌 해결해줘" 라고 하세요.
  echo.
  pause
  exit /b 1
)q666

echo.
echo [3/3] 미리보기 서버를 켭니다.
echo.
echo    브라우저에서 이 주소를 여세요 :  http://localhost:8000
echo.
echo    ( 미리보기를 끝내려면 이 창을 닫으세요 )
echo ============================================
echo.

start "" http://localhost:8000
python -m http.server 8000 || py -m http.server 8000

pause
exit /b 0


rem ============================================================
rem  지난번 저장이 GitHub 까지 갔는지 확인
rem  ("저장" 창이 업로드 전에 닫히면 커밋만 되고 안 올라간다.
rem   그러면 저장된 줄 알고 있다가, 사이트가 안 바뀌어서야 알게 된다.)
rem
rem  묻는 것까지 저장전점검.py 가 한다 — 한글 프롬프트를 배치에 두면
rem  cmd 가 UTF-8 배치 파일에서 그 다음 줄을 갉아먹는 일이 있다.
rem ============================================================
:check_not_pushed
set "PY=python"
python --version >nul 2>&1
if errorlevel 1 set "PY=py"
%PY% 저장전점검.py --notpushed
exit /b 0
