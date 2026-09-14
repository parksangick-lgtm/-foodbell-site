@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 푸드벨 사이트 - 저장 (GitHub 업로드)

rem 더블클릭이 겹쳐 두 번 실행되면 커밋이 꼬일 수 있어, 창 하나만 돌게 막는다.
set "LOCK=%TEMP%\foodbell-save.lock"
mkdir "%LOCK%" 2>nul
if errorlevel 1 (
  echo ============================================
  echo    푸드벨 사이트 - 저장 (GitHub 업로드)
  echo ============================================
  echo.
  echo  ※ 이미 "저장" 창이 하나 더 열려 진행 중입니다.
  echo     (두 번 누르신 것 같습니다 - 이 창만 닫으시고, 먼저 연 창에서 계속하세요)
  echo.
  pause
  exit /b 1
)

call :run
set "RC=%ERRORLEVEL%"
rmdir "%LOCK%" 2>nul
exit /b %RC%

:run
echo ============================================
echo    푸드벨 사이트 - 저장 (GitHub 업로드)
echo ============================================
echo.
rem 파이썬 명령 이름을 한 번만 정한다 (PC 에 따라 python 또는 py).
set "PY=python"
python --version >nul 2>&1
if errorlevel 1 set "PY=py"

echo [1/5] 먼저 최신 내용을 받는 중...
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
echo [2/5] 올릴 파일 점검 중...
call :check_big_files
if errorlevel 1 (
  echo.
  echo  저장을 취소했습니다. 올리고 싶지 않은 파일은 지우거나,
  echo  .gitignore 에 넣은 뒤 다시 "저장"을 눌러 주세요.
  echo.
  pause
  exit /b 1
)
call :check_cache_version

echo.
echo [3/5] 바뀐 파일 목록 :
echo.
git status --short
echo.

set "MSG="
set /p "MSG=[4/5] 무엇을 바꿨나요? (한 줄 설명 / 그냥 엔터치면 날짜로 저장) : "
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
echo [5/5] GitHub 에 올리는 중...
echo.
git push
if errorlevel 1 (
  echo.
  echo  !! 업로드 실패. 위 메시지를 확인하세요.
  echo     ( 방금 만든 내용은 이 컴퓨터에 그대로 남아 있습니다. 다시 "저장"을 눌러 재시도하세요 )
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
exit /b 0


rem ============================================================
rem  올리기 전 점검
rem ============================================================

rem  점검 내용은 저장전점검.py 안에 있다. 배치 파일이 아니라 파이썬인 이유:
rem  git 이 한글 파일 이름을 "\354\213\234..." 로 바꿔 내보내서, 배치로 짠
rem  첫 판은 6MB 짜리 시험 파일을 그냥 통과시켰다 (경고가 없는 것과 점검이
rem  망가진 것이 화면상 똑같았다).

rem --- 무거운 새 파일이 통째로 올라가는 것 막기 -----------------
rem  git add -A 는 작업 폴더의 새 파일을 전부 올린다. 예전에 26MB 짜리
rem  디자인 zip 이 그렇게 올라갔고, 나중에 지워도 저장소 기록에는 남는다.
rem  묻는 것까지 파이썬이 한다. 저장.bat 에 한글 프롬프트를 두면 cmd 가 UTF-8
rem  배치 파일에서 그 다음 줄을 갉아먹는 일이 있다 (echo 가 ho 로 읽혔다).
:check_big_files
%PY% 저장전점검.py --big
rem  2 = 점검 자체가 고장난 것. 저장을 막지는 않되, 통과와 헷갈리지 않게 말해 준다.
if errorlevel 2 goto :check_big_broken
if errorlevel 1 exit /b 1
exit /b 0
:check_big_broken
echo    점검을 못 했습니다 - 올릴 파일 목록을 직접 확인해 주세요.
exit /b 0

rem --- 캐시 번호를 안 올리고 저장하는 것 막기 --------------------
rem  css/js 를 고쳐도 ?v= 를 안 올리면 손님 휴대폰은 옛 파일을 계속 본다.
rem  "기억해서 하기"로는 계속 빠져서(같은 교훈이 노트에 세 번 적혔다)
rem  반드시 지나가는 이 자리에 붙였다.
:check_cache_version
%PY% 저장전점검.py --cache
if errorlevel 2 goto :check_cache_broken
exit /b 0
:check_cache_broken
echo    점검을 못 했습니다 - 캐시 번호는 직접 확인해 주세요.
exit /b 0
