@echo off
rem Run Android sdkmanager / avdmanager with every package name written INSIDE this file.
rem PowerShell splits arguments at ';' (and drops the quotes), so names like
rem "system-images;android-36;google_apis;x86_64" must never be passed on the command line.
rem Usage:  sdk-tools.bat check | install | avd
rem   check   - read-only: list installed packages and AVDs
rem   install - platform-tools, emulator, platform, NDK, system image
rem   avd     - create the emulator
setlocal
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "SDK=%LOCALAPPDATA%\Android\Sdk"
set "BIN=%SDK%\cmdline-tools\latest\bin"

rem Versions: read them from
rem C:\flutter\packages\flutter_tools\gradle\src\main\kotlin\FlutterExtension.kt
rem (compileSdkVersion / ndkVersion). Flutter 3.47.5 = 36 / 28.2.13676358.
set "API=36"
set "NDK=28.2.13676358"
set "IMG=system-images;android-%API%;google_apis;x86_64"
set "AVD=Pixel_Flutter"

if not exist "%JAVA_HOME%\bin\java.exe" (
  echo JAVA_HOME not found: %JAVA_HOME%
  exit /b 3
)
if not exist "%BIN%\sdkmanager.bat" (
  echo cmdline-tools missing: %BIN%
  exit /b 3
)

if /i "%~1"=="check" goto check
if /i "%~1"=="install" goto install
if /i "%~1"=="avd" goto avd
echo usage: sdk-tools.bat check ^| install ^| avd
exit /b 2

:check
call "%BIN%\sdkmanager.bat" --list_installed
call "%BIN%\avdmanager.bat" list avd -c
exit /b %errorlevel%

:install
call "%BIN%\sdkmanager.bat" "platform-tools" "emulator" "platforms;android-%API%" "ndk;%NDK%" "%IMG%"
exit /b %errorlevel%

:avd
echo no| call "%BIN%\avdmanager.bat" create avd -n "%AVD%" -k "%IMG%" -d pixel_7
exit /b %errorlevel%
