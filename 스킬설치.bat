@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ================================
echo  푸드벨 작업 스킬 설치
echo ================================
echo.
echo 이 저장소 안의 스킬을 내 컴퓨터 전체에 복사합니다.
echo 그러면 어느 폴더에서 작업하든 같은 규칙이 적용됩니다.
echo.

set "SRC=.claude\skills"
set "DEST=%USERPROFILE%\.claude\skills"

if not exist "%SRC%" (
  echo [오류] 이 폴더에 .claude\skills 가 없습니다.
  echo        저장소 폴더에서 실행했는지 확인하세요.
  pause
  exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"

xcopy /E /I /Y "%SRC%" "%DEST%" >nul
if errorlevel 1 (
  echo [오류] 스킬 복사에 실패했습니다.
  pause
  exit /b 1
)

rem 복사됐다는 말만 믿지 않는다 - 실제로 자리에 있는지 확인한다.
rem 대표 파일 하나가 없으면 xcopy 가 0 을 내고도 아무것도 안 옮긴 것이다.
if not exist "%DEST%\foodbell-site-dev\SKILL.md" (
  echo [오류] 복사는 끝났다는데 파일이 없습니다. 권한이나 경로를 확인하세요.
  pause
  exit /b 1
)

echo 설치 완료: %DEST%
echo.
echo 설치된 스킬:
for /d %%D in ("%SRC%\*") do echo   - %%~nxD
echo.
echo 클로드 코드를 새로 켜면 반영됩니다.
pause
