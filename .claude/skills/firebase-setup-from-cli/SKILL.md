---
name: firebase-setup-from-cli
description: 새 파이어베이스 프로젝트(실제용 + 시험용)를 만들고 Firestore · 구글 로그인 · 관리자 열쇠 · 보안 규칙까지 준비하는 순서. 사장님이 콘솔에서 누를 것을 세 번 정도로 줄이고 나머지는 명령으로 한다. "파이어베이스 새로 만들어줘", "파이어베이스 프로젝트 설정", "Firestore 만들어줘", "이 PC 에서 보안 규칙 올리기", "firebase login 이 안 된다", "addFirebase 403", "API has not been used", "Failed to authenticate" 같은 말이 나올 때 쓴다. Firebase project setup from an agent shell with minimum console clicks.
---

# 파이어베이스 처음 설정 — 명령으로 하고, 사람 몫만 남긴다 (내부용)

사장님은 개발자가 아니다. 웹 콘솔을 같이 보며 하면 단계마다 한 번씩 오가야 한다. 그래서 **명령(API)으로 되는 것은
전부 클로드가 하고**, 사람만 할 수 있는 것(약관 동의 · 구글 로그인 동의 · OAuth 만들기)만 사장님께 남긴다.

**표시**: ✅ = 실제로 해 본 것(2026-10-16 시제 서류 웹, 2026-10-17 두 번째 PC). 🔸 = 해 보지 않은 것 — 쓰게 되면
실제 결과로 이 파일을 고쳐 적고 ✅ 로 바꾼다.

**첫 명령을 일찍 한 번 찔러 본다.** 아래 벽들(약관, API 켜기)은 **그 서비스를 한 번도 안 쓴 계정에서만** 나온다.
계획을 다 세운 뒤에 만나면 계획이 통째로 밀린다.

---

## 순서

| # | 할 일 | 누가 | 어떻게 |
|---|---|---|---|
| 1 | CLI 로그인 | 사장님(동의) + 클로드 | 아래 "벽 2" ✅ |
| 2 | 첫 프로젝트에 파이어베이스 붙이기(약관) | **사장님 — 콘솔** | 아래 "벽 4" ✅ |
| 3 | 나머지 프로젝트 만들기 | 클로드 | `projects:create` — 이름은 **영어로** (벽 3) ✅ |
| 4 | Firestore API 켜기 | 클로드 | Service Usage API (벽 5) ✅ |
| 5 | 데이터베이스 만들기 | 클로드 | `firestore:databases:create` (서울이면 `asia-northeast3`) ✅ |
| 6 | 웹 앱 등록 · 설정값 받기 | 클로드 | `apps:create` → `apps:sdkconfig` ✅ |
| 7 | 관리자 열쇠(서비스 계정 키) | 클로드 | IAM `serviceAccounts.keys.create` 로 **안전한 폴더에 바로 쓴다** — 사장님이 키 파일을 내려받지 않는다 ✅ |
| 8 | 구글 로그인 켜기 | **사장님 — 콘솔** | OAuth 클라이언트를 만들어야 해서 콘솔만 된다 ✅ |
| 9 | 허용 도메인 | 클로드 | Identity Toolkit 관리 API ✅ |
| 10 | 보안 규칙 올리기 → **1분 기다리고** 시험 | 클로드 | 아래 "규칙 올리기" ✅ |

관리자 열쇠는 저장소 **밖**에 둔다(푸드벨은 `C:\foodbell-keys\`, 원드라이브 · 저장소 밖). 저장소 안에 두면 자동 저장이 올린다.

---

## 벽 — 모두 한 번씩 실제로 막혔다

1. **새 PowerShell 창(`Start-Process`)에서 `npx` 가 아무것도 안 하고 프롬프트만 다시 뜬다.** 그 창의 실행 정책이
   `npx.ps1` 을 막은 것이다. → **`npx.cmd`** 로 부른다(또는 `-ExecutionPolicy Bypass`). ✅
2. **`firebase login` 을 파이프 등 터미널이 아닌 곳에서 부르면 조용히 "두 단계" 방식으로 바뀐다.** 세션 ID 와 주소를
   찍고, 설정 저장소(configstore)에 `tempLoginState` 를 남기고 끝난다. 사장님이 그 주소를 열어 동의하고 나온 코드를
   주면, 클로드 셸에서 `firebase login <코드>` 로 마무리된다. **클로드에게는 이쪽이 가장 낫다.** ✅
   `~/.config/configstore/firebase-tools.json` 에 `usage:false`·`gemini:false` 를 미리 넣어 두면 중간 질문이 안 나온다. ✅
   동의 화면은 사장님 몫이다 — 준비 방법은 `tool-recommender` 의 "동의를 눌러야 하는 도구" 절.
3. **`projects:create --display-name` 에 한글 → 400 "invalid characters".** 표시 이름도 영어로 쓴다. ✅
4. **`addFirebase` → 403 "caller does not have permission".** 파이어베이스 약관에 한 번도 동의하지 않은 계정이다.
   콘솔을 열어 보는 것으로는 안 되고, **"Google Cloud 프로젝트에 Firebase 추가"** 안에서만 약관 칸이 나온다.
   한 프로젝트를 콘솔로 붙이고 나면 나머지는 CLI 로 된다. ✅
5. **`firestore:databases:create` → 403 "API has not been used".** CLI 의 접근 토큰으로 Service Usage API 를 불러
   `firestore.googleapis.com` 을 켜면 된다. ✅
6. **규칙을 올린 직후 시험이 3/7 실패, 1분 뒤 같은 시험이 7/7 통과.** 규칙이 퍼지는 데 시간이 걸린다.
   올린 뒤 바로 시험하지 말고 1분 기다린다. ✅
7. **로그인한 적 없는 PC 에서 `deploy --only firestore:rules` → "Failed to authenticate".** ✅
   `GOOGLE_APPLICATION_CREDENTIALS` 에 관리자 열쇠를 가리키면 인증은 지나가지만, CLI 의 사전 점검
   (`serviceusage …/services/firestore.googleapis.com` 조회)에서 403 이 난다. ✅
   → 아래 "규칙 올리기 — 열쇠만 있는 PC". **CLI 로그인은 PC 마다 넘는 벽이지 프로젝트의 벽이 아니다.**
8. **백신(Avast 등)이 보안 연결을 검사하는 PC 에서는 파이썬 `requests`·gRPC 가 `CERTIFICATE_VERIFY_FAILED`.**
   브라우저·Node 는 된다. 진단과 해법은 `flutter-windows-setup` 10번. ✅

---

## 규칙 올리기

**로그인된 PC** ✅
```bash
npx firebase-tools@15.34.0 deploy --only firestore:rules --project test     # 시험용 먼저
npx firebase-tools@15.34.0 deploy --only firestore:rules --project default  # 실제 — 사장님께 묻고 나서
```
실제 프로젝트에 올리는 것은 되돌리기 어려운 행동이다. 계획서·인수인계에 허락이 적혀 있어도 **올리기 직전에 다시 묻는다**
(`superpowers-extras` 3절).

**관리자 열쇠만 있는 PC** ✅ — Firebase Rules REST API 를 열쇠로 직접 부른다(두 번 다 200 이었다).
1. `POST https://firebaserules.googleapis.com/v1/projects/{프로젝트}/rulesets` — 본문에 규칙 파일 내용
2. `PATCH https://firebaserules.googleapis.com/v1/projects/{프로젝트}/releases/cloud.firestore` — 새 `rulesetName` 으로

**로그인도 열쇠도 없는 PC** — 위 "벽 2" 로 로그인부터 한다(사장님 동의 한 번). ✅ 2026-10-20 집 PC:
1. `~/.config/configstore/firebase-tools.json` 을 읽은 뒤 `usage:false`·`gemini:false` 를 넣는다(중간 질문 없애기).
2. 사장님이 볼 창을 연다: `Start-Process powershell.exe -ArgumentList '-NoExit','-NoProfile','-ExecutionPolicy','Bypass','-Command','npx.cmd -y firebase-tools@15.34.0 login'`.
   이 창에서도 **두 단계 방식**(세션 ID + 주소)으로 나온다. 끝에 `Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)` 가 찍혀도
   무시한다 — 설정 저장소에 `tempLoginState` 가 남았는지만 본다.
3. 사장님: 주소 Ctrl+클릭 → "Yes, I just ran this command"(화면에는 `firebase login --no-localhost` 로 보여도 맞다) →
   세션 ID 확인 → 계정 고르고 허용 → 나온 코드를 대화에 붙여 넣는다.
4. 클로드: `npx.cmd -y firebase-tools@15.34.0 login <코드>` → `Success! Logged in as …`. 확인은 `login:list`·`projects:list`(읽기만).

---

## 끝내기 전 점검

- 관리자 열쇠가 저장소 밖에 있고 `git status` 에 안 보이는가
- 시험용 프로젝트에서 먼저 했는가, 실제는 직전에 물었는가
- 규칙을 올린 뒤 1분 기다리고 시험했는가
- 사장님이 한 일(콘솔 클릭)과 클로드가 한 일을 나눠서 보고했는가
