---
name: flutter-windows-setup
description: 윈도우 PC 에 Flutter 개발 환경을 처음 세팅하고 안드로이드 에뮬레이터에서 my_app 을 처음 실행(flutter run)하기까지의 절차. 사무실·집·노트북 세 PC 가 같은 앱을 쓰므로 PC 마다 반복된다. "이 PC 에 플러터 세팅해줘", "새 PC 에 플러터", "노트북에 my_app 실행", "에뮬레이터 만들어줘", "flutter run 이 안 된다", "NDK 설치 실패", "JAVA_HOME is not set", "sdkmanager 패키지를 못 찾는다" 같은 말이 나올 때 쓴다. Windows Flutter + Android toolchain first-run setup.
---

# 윈도우 Flutter 첫 세팅 — 내부용 스킬

사용자는 개발자가 아니다. 한국어로, 쉬운 말로 설명한다. 단계마다 **실제로 명령을 돌려 확인한 뒤** 다음으로 간다.
집 PC(2026-09-29)·사무실 PC(2026-09-29)에서 성공한 절차이고, 아래 "막힌 곳"은 그때 실제로 한 번씩 실패한 자리다.

## 목표 (성공 기준)

- Flutter SDK `C:\flutter`(stable), 사용자 PATH 에 `C:\flutter\bin`
- 프로젝트 `https://github.com/parksangick-lgtm/my_app.git`(비공개) → `C:\dev\my_app`
- 에뮬레이터 `Pixel_Flutter`(`system-images;android-36;google_apis;x86_64`, `pixel_7`)에서 `flutter run` 성공 —
  **`adb -s emulator-5554 exec-out screencap -p` 로 찍은 화면에 카운터 앱이 보이면** 성공이다.

## 순서

1. **점검표부터.** flutter · git · Android Studio(`C:\Program Files\Android\Android Studio`) · Android SDK(`%LOCALAPPDATA%\Android\Sdk`) ·
   `cmdline-tools\latest` · 이 PC 의 `$env:COMPUTERNAME` 을 확인해 표로 보여준다(깃배시 `hostname` 은 한글이 깨진다).
2. **Flutter SDK** 가 없으면 `git clone https://github.com/flutter/flutter.git -b stable --depth 1 C:\flutter`
   → PATH 추가는 **`scripts/add-user-path.ps1`** 로(아래 막힌 곳 8) → `flutter config --no-analytics`.
3. **Android Studio** 가 없으면 `https://developer.android.com/studio` 를 열어 주고 설치를 기다린다.
   **cmdline-tools** 가 없으면 직접 설치한다: `https://dl.google.com/android/repository/repository2-3.xml` 에서
   `cmdline-tools;latest` 의 windows zip 이름과 sha1 을 읽어 → 받고 → **sha1 을 대조**하고 → 풀어서 zip 안의
   `cmdline-tools` 폴더를 `%LOCALAPPDATA%\Android\Sdk\cmdline-tools\latest` 로 둔다(사무실 PC 에서 성공).
   이게 실패할 때만 Studio → SDK Manager → SDK Tools → "Android SDK Command-line Tools (latest)" 를 안내하고 "완료"를 기다린다.
4. **라이선스**: `flutter doctor` 의 Android toolchain 이 √ 면 이미 동의된 것 — 건너뛴다. `Sdk\licenses` 가 없으면
   사용자에게 새 터미널에서 `flutter doctor --android-licenses` 를 직접 돌려 y 로 답하게 한다(대화형이라 대신 못 한다).
5. **프로젝트**: `C:\dev\my_app` 이 없으면 clone, 있으면 pull.
6. **버전 확인 → 패키지 설치 → 에뮬레이터 만들기**: 아래 "버전 읽기"로 숫자를 확인해 `scripts/sdk-tools.bat` 위쪽
   `API`·`NDK` 값과 맞춘 뒤(다르면 스크래치패드에 사본을 만들어 고친다) `sdk-tools.bat check` → `install` → `avd`.
7. **실행**: 에뮬레이터를 켜고 부팅 완료를 **기기를 지정해** 확인 → `flutter run -d emulator-5554` → screencap 으로 눈 확인.
8. **마무리**: `flutter doctor` 결과와 함께 "끝난 것 / 사용자가 직접 할 것"을 정리하고,
   `C:\dev\my_app\docs\new-pc-setup-prompt.md` 의 "세팅 완료한 PC" 줄에 이 PC 를 체크한다.
   그리고 이 PC 의 `~/.claude/settings.json` 에 `git-auto-sync` 훅이 있는지 본다 — 없으면
   `C:\dev\vibe-study\tools\자동저장-설치.ps1` 실행을 제안한다(my_app 변경이 세 PC 사이를 오가는 길이다).

### 버전 읽기 — 짐작하지 말고 Flutter 가 쓰는 값을 읽는다

```bash
grep -n "val compileSdkVersion\|val ndkVersion" /c/flutter/packages/flutter_tools/gradle/src/main/kotlin/FlutterExtension.kt
```
Flutter 3.47.5 에서는 `36` / `"28.2.13676358"` 이었다(2026-10-09 집 PC 에서 이 명령으로 확인).
Flutter 를 올렸으면 숫자가 바뀔 수 있다. 첫 빌드가 다른 버전을 요구하면 **에러에 나온 버전**을 설치한다.

## 막힌 곳 — 모두 실제로 한 번씩 실패했다

1. **`;` 가 든 인자를 셸로 넘기지 않는다.** `system-images;android-36;...` 를 PowerShell 에서 넘기면 `;` 에서 쪼개지고
   (`Package android-36 not found`), `cmd /c --%` 도 따옴표가 깨졌다. → 패키지 이름을 **배치 파일 안에 적어 둔**
   `scripts/sdk-tools.bat` 으로만 부른다. 이름을 명령줄 인자로 받게 고치지 말 것 — 같은 문제로 되돌아간다.
2. **`avdmanager` 는 `JAVA_HOME is not set` 으로 실패한다**(같은 창의 sdkmanager 는 됐다).
   → `sdk-tools.bat` 첫 부분이 `JAVA_HOME=C:\Program Files\Android\Android Studio\jbr` 로 맞춘다.
3. **첫 `flutter run` 이 `sdkmanager did not install NDK 28.2.13676358` 로 실패했다** — Gradle 자동 설치가 조용히 실패.
   → NDK 를 미리 설치한다(`sdk-tools.bat install`).
4. **USB 폰과 에뮬레이터가 같이 붙으면 adb 가 엉뚱한 기기에 답한다.** 부팅 확인이 "0초 만에 완료"로 나왔는데
   폰이 대답한 것이었다. → **adb 는 항상 `-s <serial>`, flutter 는 항상 `-d <id>`**. 기기를 안 정한 확인 명령은 확인이 아니다.
5. **첫 Gradle 빌드는 2~4분 걸린다**(사무실 i7-7700K 에서 약 4분). 로그에서 `Flutter run key commands` / `FAILURE:` /
   `Error launching` 을 기다린다. PowerShell 이 붙이는 `RemoteException` 경고 줄을 실패로 읽지 않는다.
6. **PATH 를 바꾼 직후의 터미널·VS Code 는 flutter 를 못 찾는다.** → 그 자리에서는 `C:\flutter\bin\flutter.bat`
   전체 경로로 부르고, 끝나면 VS Code 를 다시 열라고 안내한다.
7. **SDK 에 더 새 플랫폼(android-37)만 있고 Flutter 가 쓰는 compileSdk(36) 가 없었다**(사무실 PC).
   → NDK 처럼 플랫폼도 미리 설치한다(`install` 에 들어 있다).
8. **사용자 PATH 를 `[Environment]::SetEnvironmentVariable` 로 쓰지 않는다.** 값이 REG_SZ 로 바뀌고
   `%USERPROFILE%` 가 모두 펼쳐진다 — 집 PC 가 실제로 그렇게 됐다(`kind: String`, 2026-10-09 확인. 지금 동작에는 문제없다).
   → `scripts/add-user-path.ps1` 은 `DoNotExpandEnvironmentNames` 로 읽고, 이미 있으면 아무것도 안 하고,
   기본이 **미리보기(dry run)** 이며, `-Apply` 일 때만 옛 값을 `%TEMP%` 에 백업한 뒤 ExpandString 으로 쓴다.
9. **`sdkmanager is deprecated … Android CLI will be used instead` 경고는 실패가 아니다**(2026-10-09 처음 봄).
   목록·설치는 정상으로 끝났다. 끝 줄의 결과와 종료 코드로 판단한다.

## 실행은 사용자 터미널에서

`flutter run` 을 클로드가 백그라운드로 띄우면 **핫 리로드(r 키)를 사용자가 누를 수 없다.** 첫 성공 확인이 끝나면
"앞으로는 VS Code 터미널에서 `flutter run -d emulator-5554` 를 직접 실행하세요"라고 안내한다.
폰으로 실행하려면: 개발자 옵션 → USB 디버깅 켜기 → 설치 허용 팝업 허용.

## 스크립트

| 파일 | 하는 일 | 부르는 법 |
|---|---|---|
| `scripts/sdk-tools.bat` | sdkmanager·avdmanager 를 JAVA_HOME 맞춰 부른다. 패키지 이름은 파일 안에 있다 | `check`(읽기만) · `install` · `avd`. 다른 인자는 사용법을 찍고 종료 코드 2 |
| `scripts/add-user-path.ps1` | 사용자 PATH 에 한 폴더를 안전하게 덧붙인다 | `powershell -NoProfile -ExecutionPolicy Bypass -File add-user-path.ps1 -Add 'C:\flutter\bin'` → 미리보기. 확인 후 `-Apply` |

- `sdk-tools.bat` 은 **CRLF 줄바꿈**이어야 한다(LF 면 cmd 가 줄을 못 나눈다). 두 스크립트 모두 한글을 넣지 않았다 —
  윈도우 PowerShell 5.1 은 BOM 없는 UTF-8 의 한글을 깨뜨린다. 고칠 때도 영문만 쓴다.
- 이 PC 에서 이미 다 된 단계는 **건너뛰되, 건너뛴 이유(확인한 결과)를 표에 적는다.**

## 끝내기 전 점검

- [ ] screencap 사진에 카운터 앱이 보였다(명령 성공 메시지만으로 "됐다"고 하지 않는다)
- [ ] 모든 adb·flutter 명령에 기기를 지정했다
- [ ] PATH 를 바꿨다면 `add-user-path.ps1` 로, 백업 경로를 사용자에게 알렸다
- [ ] `new-pc-setup-prompt.md` 의 완료 표에 이 PC 를 적었다
- [ ] 새로 막힌 곳이 있었으면 위 "막힌 곳"에 추가할 관찰로 기록했다
