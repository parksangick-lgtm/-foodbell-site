# 일일 일정표 사진으로 채우기 — 작업 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 이 저장소에서는 **관리자(foodbell-manager)** 가 과제 2~5 를 일꾼(고치기 · 시험 · 휴대폰 화면 · 코드 규칙)에게 나눠 맡긴다. 과제 1 · 6 은 메인이 한다(배포 확인 · 사장님과 함께).

**Goal:** 일일 일정표 편집 화면에서 손글씨 노트 사진을 찍으면 클로드(오퍼스 5.5)가 읽어 빈 줄부터 칸을 채우고, 자신 없는 칸은 노란색으로 보인다.

**Architecture:** 버셀 서버 기능 `api/read-note.js` 가 사장님 로그인 표(파이어베이스 ID 토큰)로 허락 목록을 읽어 주인인지 보고, 클로드에 사진 + 지시 + 이름 목록을 보내 구조화 JSON 을 받아 돌려준다. 화면(`daily-schedule.html`)은 사진을 줄여 보내고, 받은 줄을 기존 "줄 추가" · 칸 정리 함수로 채운다. 공통 부품(`js/docs/doc-page.js`)이 토큰과 최근 일정표를 화면에 건넨다.

**Tech Stack:** 정적 HTML/JS(빌드 없음) · 버셀 Node 서버 기능(웹 표준 `GET`/`POST` 내보내기) · `@anthropic-ai/sdk` 1.4.0 · 파이어베이스 Auth/Firestore(REST) · 시험 node --test + pytest/Playwright

**Spec:** `docs/superpowers/specs/2026-11-03-daily-schedule-photo-fill-design.md`

## Global Constraints

- 모델 `claude-opus-5-5` · `max_tokens: 16000` · `output_config.effort: 'medium'` · `betas: ['server-side-fallback-2026-07-01']` + `fallbacks: 'default'` · 구조화 출력 `output_config.format: { type: 'json_schema', schema: NOTE_SCHEMA }`.
- 클로드 호출은 `client.beta.messages.create(...)`, 요청 옵션 `{ timeout: 55_000, maxRetries: 0 }`. 응답은 `stop_reason === 'refusal'` 을 먼저 보고, 첫 `text` 블록을 `JSON.parse`.
- `@anthropic-ai/sdk` 는 **실제 호출할 때만** `await import(...)` — 시험은 SDK 없이 돈다.
- 주인 확인 = `GET https://firestore.googleapis.com/v1/projects/foodbell-sije/databases/(default)/documents/allow/<encodeURIComponent(메일)>` 에 `Authorization: Bearer <토큰>`. 200 만 통과.
- 몸통 글자 수 4,000,000 넘으면 413. 사진은 화면에서 긴 변 2000점 · JPEG 품질 0.85(4,000,000 가까우면 0.7 → 0.5).
- 이름 목록(hints): 최근 일정표 20장의 `staff` · `place` 칸 글자, 각 60개 · 한 개 40자까지, 숫자 3자리 이상 이어진 것(전화 등)은 뺀다.
- 서버 기록(console)에는 `{status, ms, in, out}`(숫자)만. 사진 · 결과 · 메일 · 토큰 글자를 찍지 않는다.
- 비밀값은 버셀 `ANTHROPIC_API_KEY` 하나. 코드 · 저장소 · 문서 · 시험에 실제 값 없음.
- 시험 데이터는 가짜만(이름 '가짜○○', 전화 `010-0000-xxxx`). 사장님 노트 사진은 저장소에 넣지 않는다.
- `vercel.json` · `.vercelignore` 는 고치지 않는다(과제 1 결과 시간 한도가 모자라면 메인이 사장님께 묻는다).
- css/js 를 고치면 부르는 곳의 `?v=` 를 올리고(`python 캐시버전올리기.py --check` 로 확인), `sw.js` 의 `CACHE` 번호도 올린다.
- 화면 글 · 주석은 한국어, 그 파일의 기존 말투. 누르는 자리 44px 이상, 글자 14px 이상, 390px 에서 넘침 0.
- JS 시험 명령은 `node --test "tools/sije_web/js-tests/*.test.mjs"`(폴더 이름만 주면 0개가 돈다).

## Review Focus

1. 사진이 아닌 파일 · 열 수 없는 사진(HEIC 등) — 서버로 보내지 않고 "사진을 열지 못했습니다". → 과제 4 `test_daily_photo_bad_file_not_sent`
2. 읽는 동안 단추를 또 누름 — 요청은 한 번만. → 과제 4 `test_daily_photo_single_request_while_reading`
3. 글자 있는 줄 사이에 빈 줄이 끼어 있음 · 연기/취소 표시만 있는 줄 — 빈 줄(표시 없음)만 위에서부터 채운다. → 과제 4 `test_daily_photo_fills_empty_rows_then_adds`
4. 인터넷 끊김 · 서버가 JSON 이 아닌 답 — 일정표 그대로 + "사진을 읽지 못했습니다 (연결)" / "(번호)". → 과제 4 `test_daily_photo_errors_show_reason`
5. 클로드가 지시와 다른 칸 이름 · 숫자 아닌 값을 보냄 — 모르는 칸은 버리고, 단가가 숫자로 안 읽히면 글자 그대로. → 과제 2 `rejects_unknown_fields`(서버가 스키마 밖 칸 제거) + 과제 4 `fills_empty_rows_then_adds` 의 단가 '협의'

---

### Task 1: 버셀이 서버 기능을 돌리는지 확인 (메인)

**Files:**
- Create: `api/ping.js`, `package.json`, `package-lock.json`
- Modify: `.gitignore`(맨 끝에 `node_modules/`)

- [ ] **Step 1:** `npm install @anthropic-ai/sdk@1.4.0 --save-exact` 로 `package.json`(`"private": true, "type": "module"`)과 잠금 파일을 만든다. `node_modules/` 를 `.gitignore` 에.
- [ ] **Step 2:** `api/ping.js` — `export const maxDuration = 60;` · `export async function GET(request)` : `?wait=N`(0~55초)만큼 기다린 뒤 `Response.json({ ok: true, sdk: typeof (await import('@anthropic-ai/sdk')).default === 'function', waited: N })` · `export async function POST(request)` : `Response.json({ bytes: (await request.text()).length })`.
- [ ] **Step 3:** 기존 시험이 그대로인지: `node --test "tools/sije_web/js-tests/*.test.mjs"` → 실패 0 (`"type": "module"` 영향 확인).
- [ ] **Step 4:** 차례를 끝낸다(자동 저장으로 올라감). **다음 차례 첫 일**로:
  - `curl -s https://foodbell.kr/api/ping` → `{"ok":true,"sdk":true,"waited":0}`
  - `curl -s -m 70 "https://foodbell.kr/api/ping?wait=50"` → 50초쯤 뒤 200 (504 면 시간 한도 부족 → 사장님께 `vercel.json` 여쭘)
  - 3,000,000자 몸통 POST → `{"bytes":3000000}` (413 이면 사진 품질을 낮추는 기준을 그 값 아래로)
  - `https://foodbell.kr/` · `daily-schedule.html` · `sije-list.html` 200 그대로
  - 결과(시간 · 몸통 한도)를 이 계획서 끝 "확인 기록"에 적는다.

### Task 2: 서버 기능 `api/read-note.js`

**Files:**
- Create: `api/read-note.js`
- Test: `tools/sije_web/js-tests/read-note.test.mjs`

**Interfaces:**
- Produces: `makeHandlers({ env, fetch, anthropic, log }) → { GET(request): Promise<Response>, POST(request): Promise<Response> }` (이름 붙인 내보내기). 같은 파일에서 `export const maxDuration = 60;` 과 실제 의존으로 만든 `export const { GET, POST } = makeHandlers({ env: process.env, fetch: globalThis.fetch, anthropic: <lazy SDK 클라이언트 만드는 함수>, log: console.log })`.
- `anthropic` 인자 = `async (apiKey) => ({ beta: { messages: { create(params, options) } } })` 모양(실제는 `new (await import('@anthropic-ai/sdk')).default({ apiKey })`).
- 응답 몸통(200): `{ day: string, rows: Row[], note: string }`, `Row` 칸 = `staff car leave time place tel work people price lead lead_tel hall depart cremate memo` (모두 문자열) + `unsure: string[]`. 오류: `{ error: 'login'|'denied'|'too-big'|'bad-request'|'not-ready'|'limit'|'timeout'|'busy'|'refusal'|'failed' }` + 상태 번호 401·403·413·400·503·402·504·429·502·502.

- [ ] **Step 1: 실패하는 시험을 쓴다** — 가짜 `fetch`(Firestore 답 200/403/404) · 가짜 `anthropic`(받은 요청을 적어 두고 정해 둔 답을 줌) · 가짜 `log`(찍은 것 모음):
  - `get_ready_follows_key` — env 에 키 없음 → `{ready:false}`, 있음 → `{ready:true}`
  - `post_without_token_is_401` — Authorization 없음 → 401 `login`, Firestore · 클로드 안 부름
  - `post_non_owner_is_403` — Firestore 404 · 403 → 403 `denied`
  - `post_too_big_is_413` — 4,000,001자 몸통 → 413, Firestore 안 부름
  - `post_without_key_is_503` — 주인이지만 키 없음 → 503 `not-ready`
  - `post_owner_returns_rows` — 토큰 `가짜헤더.<base64url({"email":"fake@example.com"})>.서명` → Firestore 주소가 `.../projects/foodbell-sije/databases/(default)/documents/allow/fake%40example.com` · 머리 `Bearer <토큰>`; 클로드 요청에 `model 'claude-opus-5-5'` · `betas ['server-side-fallback-2026-07-01']` · `fallbacks 'default'` · `output_config.effort 'medium'` · `output_config.format.type 'json_schema'` · 첫 내용 블록 `{type:'image', source:{type:'base64', media_type:'image/jpeg'}}` · 지시 글에 hints 이름(`가짜담당`)이 들어감 · 옵션 `{timeout:55000, maxRetries:0}`; 200 몸통 = 가짜 답 JSON
  - `rejects_unknown_fields` — 가짜 답 줄에 `secret:'x'` · 문자열 아닌 값 → 몸통에서 빠지거나 `''`
  - `refusal_is_502` — `stop_reason:'refusal'` → 502 `refusal`
  - `anthropic_errors_map` — 시간 초과(이름 `APIConnectionTimeoutError`) → 504 `timeout`; status 429 → 429 `busy`; status 400 + 메시지 `credit balance` → 402 `limit`; status 401 → 503 `not-ready`; 그 밖 → 502 `failed`
  - `logs_hold_no_content` — 모든 경우의 `log` 글에 사진 글자 · 메일 · 토큰이 없고 `status` 숫자가 있음
- [ ] **Step 2:** `node --test tools/sije_web/js-tests/read-note.test.mjs` → 실패(파일 없음)
- [ ] **Step 3: 만든다** — 상수 `NOTE_SCHEMA`(설계서 3-2 그대로, 모든 칸 required · `additionalProperties:false`) · `SYSTEM`(설계서 3-2 칸 규칙 + "읽기 애매하면 unsure, 지어내지 않는다" + 이름 목록 규칙) · `readEmail(token)`(가운데 조각 base64url → JSON → email, 실패면 '') · `cleanRows(rows)`(Row 칸만, 문자열만) · `mapError(e)`. 사진은 `body.image`(base64 글자), 사용자 글에 `day` · hints 를 붙인다.
- [ ] **Step 4:** 같은 명령 → 통과. 전체 `node --test "tools/sije_web/js-tests/*.test.mjs"` → 실패 0.

### Task 3: 공통 부품이 토큰 · 최근 일정표를 건넨다

**Files:**
- Modify: `js/sije/store.js`(내보내기 둘 추가), `js/docs/doc-page.js`(`D.idToken` · `D.recentDocs` 붙이기), doc-page.js 를 부르는 모든 html 의 `doc-page.js?v=12` → `13`

**Interfaces:**
- Produces: `store.js` — `export function idToken(): Promise<string>`(로그인 없으면 Error) · `export async function recentDocs(kind: string, n: number): Promise<Array<{id, doc}>>`(`watchDocs` 와 같은 조건 한 번 읽기, `updatedAt` 최근 순 n장)
- Produces: 화면에서 `window.FoodbellDoc.idToken()` · `window.FoodbellDoc.recentDocs(n)` (doc-page 가 `D.onSave` 처럼 붙인다). 주인 여부는 지금처럼 `document.body.dataset.role === 'owner'`.

- [ ] **Step 1:** 실패하는 시험 `test_daily_doc_hooks_give_token_and_recent`(test_doc_pages.py) — 일정표 두 장(담당 '가짜담당1' · '가짜담당2')을 `made` 로 만든 뒤 새 일정표를 열어 `await FoodbellDoc.idToken()` 이 빈 글자가 아니고, `(await FoodbellDoc.recentDocs(20)).length >= 2`, 최근 고친 것이 먼저.
- [ ] **Step 2:** `python -X utf8 -m pytest tools/sije_web/tests/test_doc_pages.py -k doc_hooks -q` → 실패
- [ ] **Step 3:** 두 함수 + doc-page 연결 + `?v=` 올림
- [ ] **Step 4:** 같은 명령 통과 · `python -X utf8 -m pytest tools/sije_web/tests/test_doc_pages.py -q` 전체 통과

### Task 4: 화면 — "사진으로 채우기"

**Files:**
- Modify: `daily-schedule.html`(css · 줄 추가 행 · 입력 처리 · serialize · 인쇄), `sw.js`(`/api/` 통과 + `CACHE` 올림)
- Test: `tools/sije_web/tests/test_doc_pages.py`, `tools/sije_web/js-tests/sw.test.mjs`

**Interfaces:**
- Consumes: Task 2 응답 모양 · Task 3 `FoodbellDoc.idToken()` / `recentDocs(n)`
- 화면 안 이름(시험이 쓴다): 단추 `.btn-photo`(글 "사진으로 채우기", "줄 추가 (일 하나)" 와 같은 `tr.addrow` 안), 숨은 입력 `#photo-input`(`type=file accept="image/*"`), 표시 클래스 `ai-unsure`, 줄 더하기를 click 처리에서 꺼낸 `addRow(): HTMLTableRowElement`(기존 "줄 추가" 도 이것을 씀)
- 칸 이름 바꿈: 응답 `lead_tel` → 화면 `lead-tel`. 채울 칸 = `staff car leave time place tel work people price lead lead-tel hall depart cremate memo`.

- [ ] **Step 1: 실패하는 시험을 쓴다** (모두 `page.route('**/api/read-note', …)` 가짜 답, `daily_new` · `edit_cell` · `text_of` · `fake_jpeg` 그대로)
  - `test_daily_photo_button_only_when_ready_and_editing` — GET `{ready:false}` 또는 404 → 편집 중에도 `.btn-photo` 0개; `{ready:true}` → 편집 전 안 보임, 편집 중 1개, 높이 ≥ 44px
  - `test_daily_photo_fills_empty_rows_then_adds` — 1번 줄에 '가짜 먼저', 2번 줄은 '줄 추가'만 하고 비움, 3번 줄 연기 표시만 → 가짜 답 두 줄(`tel '01000001234'`, `price '35만'`, `cremate '08:00'`, 둘째 줄 `price '협의'`) → 1번 그대로, 2번 줄에 첫째, 맨 끝 새 줄에 둘째, 3번(연기) 그대로; 첫째 줄 연락처 `010-0000-1234` · 단가 `350,000원` · 장례 칸 펼쳐짐; 둘째 줄 단가 `협의`
  - `test_daily_photo_marks_unsure_until_edited` — `unsure ['tel','place']` → 두 칸 `ai-unsure`; 연락처를 고치면 그 칸만 사라짐; `FoodbellDoc.serialize()` 에 `ai-unsure` 없음; 인쇄 모양(`emulate_media(media='print')`)에서 그 칸 배경이 투명
  - `test_daily_photo_request_carries_token_hints_and_resized_jpeg` — 3000×2250 `fake_jpeg` 를 `#photo-input` 에 → 잡은 요청: `Authorization` 이 `Bearer ` + 글자, 몸통 `image` 를 풀면 JPEG 이고 긴 변 ≤ 2000, `hints.staff` 에 앞서 저장한 일정표의 '가짜담당1', `hints` 어디에도 `010-` 없음, `day` = 일정표 날짜(`YYYY-MM-DD`)
  - `test_daily_photo_errors_show_reason` — 401 · 403 · 413 · 402 · 504 · 500 · 연결 끊김(`route.abort()`) · JSON 아닌 200 → 알림이 차례로 "로그인이 풀렸습니다 — 다시 로그인해 주세요" · "이 계정은 쓸 수 없습니다" · "사진이 너무 큽니다" · "이번 달 사용 한도에 닿았습니다(앤트로픽 설정 확인)" · "시간이 너무 걸렸습니다 — 다시 눌러 주세요" · "사진을 읽지 못했습니다 (500)" · "사진을 읽지 못했습니다 (연결)" · "사진을 읽지 못했습니다 (응답)"; 그때마다 일정표 HTML 은 그대로
  - `test_daily_photo_day_mismatch_and_note` — 답 `day` 가 일정표 날짜와 다름 + `note '가짜 메모'` → 알림에 "노트 날짜 M/D · 일정표 날짜 M/D — 확인하세요" 와 "가짜 메모" 가 함께, 일정표 날짜는 그대로
  - `test_daily_photo_single_request_while_reading` — 답을 3초 늦게 → 단추 두 번 → 요청 1번, 읽는 동안 단추 막힘 · "읽는 중…" 글
  - `test_daily_photo_bad_file_not_sent` — 글자 파일(.txt)을 넣음 → 요청 0번, 알림 "사진을 열지 못했습니다"
  - sw.test.mjs `api_requests_pass_through` — GET `https://foodbell.kr/api/read-note` 를 sw 가 가로채지 않음(저장 안 함)
- [ ] **Step 2:** `python -X utf8 -m pytest tools/sije_web/tests/test_doc_pages.py -k daily_photo -q` → 실패 · sw 시험 실패
- [ ] **Step 3: 만든다**
  - 페이지 열 때 한 번 `fetch('/api/read-note', {cache:'no-store'})` → `ready` 기억, 늦게 오면 편집 중일 때 단추를 그때 넣음(넣기는 같은 함수, 두 번 넣지 않음). 단추는 주인일 때만.
  - 사진 줄이기: `createImageBitmap` → canvas 긴 변 2000 → `toBlob('image/jpeg', 0.85)`; base64 가 3,900,000자 넘으면 0.7 → 0.5. 실패하면 "사진을 열지 못했습니다".
  - 요청: `POST /api/read-note`, 머리 `Authorization: Bearer ${await FoodbellDoc.idToken()}`, 몸통 `{image, hints, day}`; 70초 넘으면 끊고 "시간이 너무 걸렸습니다 — 다시 눌러 주세요".
  - 빈 줄 = 15칸 모두 비고 `data-state` 없음. 위에서부터 빈 줄, 모자라면 `addRow()`. 넣는 값: 연락처 · 팀장 전화는 `dashTels(v)`, 단가는 `readNumber(v)` 가 숫자면 `${fmt(n)}원` 아니면 글자 그대로, 나머지 그대로. `unsure` 칸에 `ai-unsure`. 줄마다 `foldMeet(tr)` 로 장례 칸 펼침 판단, 끝에 `recalc(); save();`.
  - 알림 하나에 줄바꿈으로: "N줄을 채웠습니다 — 노란 칸을 확인해 주세요"(0줄이면 "읽을 줄을 찾지 못했습니다") + 날짜 다름 + `note`.
  - `ai-unsure` 배경 `rgba(176,141,87,.35)`(이 파일이 쓰는 금색 값), `input` 에서 그 칸 클래스 지움, `serialize()` 복사본에서 지움, `@media print` 에서 배경 없음.
  - `sw.js`: `/_vercel/` 줄 옆에 `/api/` 는 return(통과) + `CACHE` 번호 올림.
- [ ] **Step 4:** 같은 명령 통과 · 일정표 시험 전체 `-k daily` 통과 · JS 시험 전체 실패 0
- [ ] **Step 5:** 휴대폰 확인: `python 휴대폰캡처.py` 로 390px 넘침 0 · `.btn-photo` 44px · 글자 14px 이상(ready 를 가짜로 켠 상태는 시험이 본다)

### Task 5: 마무리

**Files:**
- Delete: `api/ping.js`
- Modify: `CLAUDE.md`(파일 목록: `api/read-note.js` · `package.json` 한 줄, `daily-schedule.html` 줄에 "사진으로 채우기" 한 줄 — 설계서 경로 포함)

- [ ] **Step 1:** `api/ping.js` 지움 · CLAUDE.md 두 곳 · `python 캐시버전올리기.py --check` 깨끗
- [ ] **Step 2:** 전체 시험 — `node --test "tools/sije_web/js-tests/*.test.mjs"` 실패 0 · `python -X utf8 -m pytest tools/sije_web/tests -q` 실패 0(일시 실패는 혼자 다시 돌려 확인)
- [ ] **Step 3:** 코드 규칙 검토(바뀐 곳 전체 — 비밀값 · 손님 정보 · 캐시 번호 · 옛 저장 키) · 문구 검토(새 알림 글)
- [ ] **Step 4 (자동 저장으로 올라간 뒤 · 메인):** `curl -s https://foodbell.kr/api/read-note` → `{"ready":false}` · `curl -s -o /dev/null -w "%{http_code}" https://foodbell.kr/api/ping` → 404 · 서버 `daily-schedule.html` 의 `doc-page.js?v=13` · `sw.js` CACHE = 저장본

### Task 6: 열쇠 넣고 실제로 (메인 + 사장님)

- [ ] **Step 1:** 사장님 안내(한 단계씩, 캡처로 확인): console.anthropic.com 가입 → 카드 → 월 한도 약 $7 → API 열쇠 만들기(대화창에 붙이지 않음) → 버셀 Settings → Environment Variables → `ANTHROPIC_API_KEY`(Production) → Deployments 에서 Redeploy. **월 한도 설정 화면이 없으면** 멈추고 여쭘(미리 충전 1만 원어치 등).
- [ ] **Step 2:** `curl -s https://foodbell.kr/api/read-note` → `{"ready":true}`
- [ ] **Step 3:** 사장님 휴대폰: 일정표 → 편집 → "사진으로 채우기" → 오늘 노트 사진. 잴 것: 걸린 시간(초) · 사장님이 고친 칸 수 / 채운 칸 수 · 앤트로픽 Usage 화면의 비용(원) — **설계 추정(1분 안 · 한 장 100~150원)과 나란히** 보고. 1분을 넘거나 고친 칸이 많으면 `effort` 를 `high` 로 바꿀지 사장님께 여쭘.

## 확인 기록

(과제 1 · 5 · 6 의 실제 숫자를 여기에 적는다.)

- **과제 1 (2026-11-03 19:5x 사무실, 자동 저장 81bf370 뒤)**: `GET /api/ping` → `{"ok":true,"sdk":true,"waited":0}` (버셀이 `package.json` 의존을 깔고 웹 표준 `GET`/`POST` 내보내기를 돌림) · `?wait=50` → 200, 50.26초 (`export const maxDuration = 60` 로 충분 — `vercel.json` 손대지 않음) · POST 3,000,000자 · 4,400,000자 → 둘 다 200 · `/` · `daily-schedule.html` · `sije-list.html` 200 · `/package.json` 404(공개 안 됨).
- **과제 2~5 (관리자, 21:3x)**: JS 97/97 · pytest 전체 통과 · 390px 넘침 0 · `.btn-photo` 44px. **과제 5 배포 확인(f241494)**: `/api/read-note` → `{"ready":false}` · `/api/ping` 404 · `doc-page.js?v=13` · `foodbell-v42`.
- **최종 검토(fable)**: Critical 0. Important 1(doc-page.js 가 store.js 를 `?v=` 없이 불러 옛 저장본과 섞이면 서류 6종이 안 뜸) 고침 — `store.js?v=1` · `doc-page.js?v=14`, 시험 `doc_page_imports_store_with_version`. 나머지는 작은 것으로 미룸(작업 기록장).
- 부품 1.4.0 타입으로 확인: `output_config.format` = `{ type: 'json_schema', schema }`(`BetaJSONOutputFormat`) · `fallbacks?: Array<…> | 'default'` · 베타 이름 `'server-side-fallback-2026-07-01'` 있음 · `effort` 에 `'medium'`.
