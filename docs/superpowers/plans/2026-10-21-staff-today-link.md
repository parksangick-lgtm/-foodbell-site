# 직원용 고정 링크 "오늘 일정" 작업 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 이번 실행: 사장님이 "여기서 직접 차례로" 를 고름(10-21) → superpowers:executing-plans.

**Goal:** 단톡방 공지에 한 번 올린 고정 링크(`today.html#암호`)가 열 때마다 지금의 일정표를 카드 · [전화] · [지도]로 보여 주고, 사진 뒤 두 번째 보내기를 없앤다.

**Architecture:** 사장님 화면이 저장할 때마다 일정표 글자를 `share/{암호}` 게시판 한 장(일정표 id 마다 한 칸)에 칸 단위로 올린다. 직원 화면은 로그인 없이 그 한 장만 지켜본다(`get: if true`, 목록 · 쓰기는 막힘). 암호는 `config/share` 에 두고 관리 도구가 만들고 바꾼다.

**Tech Stack:** 정적 HTML + ES 모듈, Firebase JS SDK(`firebase-config.js` 의 `SDK`), Firestore 보안 규칙, 파이썬 `firebase_admin`, pytest + Playwright, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-21-staff-today-link-design.md`

## Global Constraints

- 실행: 저장소 맨 위(`c:\galleypark`). 파이썬 `python -m pytest tools/sije_web/tests/<파일> -q`, JS `node --test "tools/sije_web/js-tests/*.test.mjs"`. 관리자 열쇠는 이 사무실 PC 에 있다(`C:\foodbell-keys\sije-admin.json` · `sije-test-admin.json`).
- 저장(커밋 · 푸시)은 자동 저장 훅이 답이 끝날 때 한다 — 과제마다 직접 커밋하지 않고 **바꾼 파일 목록**을 남긴다. 시작 커밋을 적어 둔다. `.superpowers/` 는 무시됨(확인함).
- **규칙을 실제 저장소에 먼저**(Task 2) — 그 전에 게시판에 올리는 화면 코드(Task 3~)가 답 끝에 게시되면 안 된다. 실제 저장소 규칙 올리기 · 실제 게시판 만들기는 **직전에 사장님께 묻는다**(시험 결과를 함께).
- 규칙 올리기: `npx firebase-tools@15.34.0 deploy --only firestore:rules --project test` (실제는 `--project default`).
- 링크 꼴 `https://foodbell.kr/today.html#<암호>`, 암호 = `secrets.token_urlsafe(24)`. **실제 암호를 규칙 · 코드 · 문서 · 기록장 · 진행중.md 에 적지 않는다**(사장님께는 대화창으로만).
- 게시판 한 장 = `{date:'YYYY-MM-DD', label, lunar, order, memo, rows:[{no, staff, car, time, place, tel, work, amt, lead, leadTel, guideTel, hall, depart, cremate, memo}], at}` — 채운 줄만, `no` 는 일정표 줄 번호, `amt` 에 "단위를 적어 주세요" 는 안 넣음, 날짜를 못 읽으면 올리지 않음(칸을 뺌).
- 지울 때: 날짜가 **어제보다 이전**인 칸(어제 것은 남김).
- 화면 글자(그대로): "직원 링크 화면에 올리지 못했습니다 (오류)" · "링크가 바뀌었습니다. 단톡방 공지의 새 링크를 눌러 주세요." · "올라온 일정이 없습니다. 단톡방의 일정표 사진을 확인해 주세요." · "연결 안 됨 — 마지막으로 받은 내용입니다" · 제목 `푸드벨 일정` · 날짜 버튼 `오늘 10월 22일 (목)` / `내일 10월 23일 (금)` / `10월 24일 (토)`.
- [전화] = `tel:` + 숫자만, 전화번호 모양만(`telShape` 와 같은 식). [지도] = `https://map.naver.com/p/search/` + `encodeURIComponent(장소)`.
- `doc-page.js` 를 고치면 부르는 여섯 화면(`sije-quote` · `event-quote` · `sije-worksheet` · `statement` · `staff-pay` · `daily-schedule`)의 `doc-page.js?v=4` → `?v=5`. `sw.js` 를 고치면 `CACHE = 'foodbell-v35'` → `'foodbell-v36'`. css 는 안 고친다.
- 외부 글꼴은 `media="print" onload="this.media='all'"`(막히면 화면이 멈춤). 화면 글자는 `textContent` 로만 넣는다(`innerHTML` 에 저장소 글자를 넣지 않음).
- 시험 자료는 가짜만(`가짜동` · `010-0000-0000` 꼴). **날짜는 시험 날 기준으로 계산**한다(고정 날짜 금지 — 다음 주에 깨진다).
- 시험 쓰는 법(1단계 기록장): 규칙 시험의 403 은 같은 사람의 200 과 함께 본다 · `wait_for_function` 에 약속(promise)을 돌려주는 식을 넣지 않는다 · `set_offline(True)` 뒤 새로 연 화면의 `navigator.onLine` 은 믿지 않는다.

## Review Focus

1. 두 기기가 서로 다른 일정표를 고침 → 상대 칸이 지워지지 않는다(칸 단위 고침). — Task 3 `test_daily_board_keeps_other_entries`
2. 일정표 날짜를 내일 → 모레로 바꿈 → 같은 칸의 날짜만 바뀌고 옛 날짜 카드가 남지 않는다. — Task 3 `test_daily_board_follows_date_change`
3. 칸에 전화번호가 아닌 숫자(`10/22`, `350,000`, `1234`)와 번호 둘 → [전화]는 전화번호 모양마다 하나씩만. — Task 4 `test_today_cards_match_board`
4. 장소 · 메모에 `#` `&` `%` `-` `<b>` → 지도 주소가 안 깨지고 글자는 그대로 보인다. — Task 4 `test_today_odd_characters`
5. 링크를 바꾼 뒤 옛 링크를 연다 → "링크가 바뀌었습니다". — Task 1 `test_new_moves_entries_and_removes_old` + Task 4 `test_today_bad_or_old_link`

---

### Task 1: 보안 규칙 · 관리 도구 (시험용 저장소)

**Files:**
- Modify: `firestore.rules` (`docs` 규칙 아래에 두 자리)
- Create: `tools/sije_web/share_link.py`
- Modify: `tools/sije_web/tests/test_rules_live.py`
- Create: `tools/sije_web/tests/test_share_link.py`

**Interfaces:**
- Produces (`share_link.py`): `LINK = 'https://foodbell.kr/today.html#'` · `current_key(db) -> str | None` · `new_key(db) -> str`(새 게시판, 옛 `entries` 옮김, `config/share` 바꿈, 옛 게시판 지움) · `link(key: str) -> str` · `main(argv)`(`show` · `new`, `--key` 필수 — `allow.py` 와 같은 꼴).
- Produces (규칙): `config/share` — `get: if allowed()`. `share/{key}` — `get: if true`; `update: if allowed() && request.resource.data.keys().hasOnly(['entries']) && request.resource.data.entries is map && request.resource.data.entries.size() <= 40`. create · delete · list 규칙 없음.

- [ ] **Step 1: 규칙 시험을 쓴다** (`test_rules_live.py`, 게시판은 관리자 열쇠로 `share/rules-<8글자>` 를 만들고 끝나면 지우는 fixture)
  - `test_share_board_readable_without_login_not_writable`: 로그인 없이 GET → 200, 같은 사람 PATCH(`entries`) → 403, 허락된 사람 PATCH(`entries`) → 200.
  - `test_share_board_list_denied`: 로그인 없이 GET 그 문서 → 200 이면서 GET `share`(목록) → 403, 허락된 사람도 목록 → 403.
  - `test_share_config_only_for_owner`: 시험 fixture 로 `config/share` 를 둔 상태에서 로그인 없이 → 403, 허락 안 된 사람 → 403, 허락된 사람 → 200.
  - `test_share_update_only_entries`: 허락된 사람이 `entries` 아닌 칸(`x`) PATCH → 403, `entries` → 200.
  - (PATCH 몸통은 `{'fields': {'entries': {'mapValue': {'fields': {...}}}}}`, `updateMask.fieldPaths=entries` 또는 `x`.)
  - `config/share` 를 바꾸는 시험은 끝나면 원래 값으로 되돌린다(다른 시험이 그 암호를 쓴다).
- [ ] **Step 2: 관리 도구 시험을 쓴다** (`test_share_link.py`, `test_db`)
  - `test_new_moves_entries_and_removes_old`: `new_key` → 첫 암호 게시판에 칸 하나 넣기 → `new_key` 다시 → 옛 게시판 없음 · 새 게시판에 그 칸 있음 · `current_key` == 새 암호 · 두 암호 길이 32 · 서로 다름.
  - `test_show_prints_link`: `main(['show', '--key', 시험 열쇠])` 출력 == `LINK + current_key`.
- [ ] **Step 3: 시험이 실패하는지 본다** — `python -m pytest tools/sije_web/tests/test_rules_live.py tools/sije_web/tests/test_share_link.py -q` → 규칙 시험은 403/404 로, 관리 도구는 `ModuleNotFoundError` 로 실패.
- [ ] **Step 4: 규칙 두 자리와 `share_link.py` 를 쓴다.** 규칙 파일 머리 주석처럼 "암호를 여기 쓰지 않는다" 를 적는다. `share_link.py` 머리에 사용법(`show` · `new`, 실제 · 시험 열쇠) 문서 문자열.
- [ ] **Step 5: 시험용 저장소에 규칙을 올린다** — `npx firebase-tools@15.34.0 deploy --only firestore:rules --project test` → `Deploy complete!`. (로그인 문제면 `firebase-setup-from-cli` 스킬.)
- [ ] **Step 6: 시험이 통과하는지 본다** — Step 3 명령 → 전부 통과, 기존 규칙 시험도 통과.

### Task 2: 실제 저장소 — 사장님께 묻고 규칙 · 게시판 (코드 없음)

**Interfaces:**
- Consumes: Task 1 의 규칙 · `share_link.new_key`.
- Produces: 실제 `config/share` · `share/<암호>`(빈 `entries`). 암호는 이 대화에만.

- [ ] **Step 1: 사장님께 묻는다** — Task 1 시험 결과(통과 수, 막힌 것 · 열린 것)를 적고 "실제 저장소에 올릴까요?". 아니면 멈춘다.
- [ ] **Step 2:** `npx firebase-tools@15.34.0 deploy --only firestore:rules --project default` → `Deploy complete!`.
- [ ] **Step 3:** `python -m tools.sije_web.share_link new --key C:\foodbell-keys\sije-admin.json` → 링크 한 줄.
- [ ] **Step 4: 실제에서 확인** — 로그인 없이 REST GET `share/<암호>` → 200, GET `config/share` → 403, GET 아무 암호 → 404. (결과에 암호를 적지 않는다.)

### Task 3: 사장님 화면이 게시판에 올리기

**Files:**
- Modify: `js/sije/store.js` (끝에 게시판 부분)
- Modify: `js/docs/doc-page.js` (`onDoc` 처음 그린 뒤 · `flush` 의 `saveDoc` 옆 · 지우기)
- Modify: `daily-schedule.html` (`window.FoodbellDoc.share`), 여섯 화면 `doc-page.js?v=5`
- Test: `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Produces (`store.js`): `publishShare(id: string, entry: object | null) -> Promise<boolean>` — `config/share` 가 없으면 `false`(아무것도 안 함). 있으면 `share/{key}` 에 `new fs.FieldPath('entries', id)` 로 `{...entry, at: serverTimestamp()}` 또는 `deleteField()`, 같은 호출에서 처음 읽은 게시판 기준 어제보다 이전 날짜 칸도 `deleteField()`. 암호 · 게시판은 화면이 열려 있는 동안 들고 있는다.
- Produces (`daily-schedule.html`): `FoodbellDoc.share() -> entry | null`(Global Constraints 의 꼴, 날짜를 못 읽으면 `null`).
- `doc-page.js`: `D.share` 가 있고 `role === 'owner'` 일 때만 `publishShare(docId, D.share())`; 지울 때 `publishShare(docId, null)`. 실패하면 토스트 한 번(화면당).

- [ ] **Step 1: 시험을 쓴다** (fixture `share_key(test_db)`: `share_link.current_key` 가 없으면 `new_key`, 시작할 때 `entries` 를 비운다 → 암호를 돌려줌)
  - `test_daily_board_gets_filled_rows`: 오늘 날짜, 줄 셋 중 1 · 3번만 채움(3번 단가 `250` → 단위 알림) → 관리자로 읽은 칸: `date` == 오늘, `rows` 의 `no` == `[1, 3]`, 칸 글자 맞음, 3번 `amt` == `''`.
  - `test_daily_open_publishes_and_delete_removes`: 새 일정표를 열기만 함 → 칸 생김(날짜 = 내일) → 지우기 → 칸 없음.
  - `test_daily_unreadable_date_not_on_board`: 날짜 `10월 21일` → 칸 없음(먼저 오늘 날짜로 생긴 것을 본 뒤 — 대조).
  - `test_daily_board_prunes_old_days`: 관리자로 3일 전 칸 · 어제 칸을 넣고 사장님이 고침 → 3일 전 없음, 어제 있음.
  - `test_daily_board_keeps_other_entries`: 관리자로 다른 id 칸을 넣고 사장님이 고침 → 그 칸 그대로.
  - `test_daily_board_follows_date_change`: 내일 → 모레로 고침 → 같은 id 칸의 `date` 가 모레, 칸은 하나.
- [ ] **Step 2: 실패를 본다** — 위 시험 `-k board or publishes or unreadable` → 칸이 안 생겨 실패.
- [ ] **Step 3: `publishShare` · `share()` · `doc-page.js` 를 쓴다.** `share()` 는 `buildText` 처럼 `field(tr, …)` 로 읽고 `filled(tr)` 인 줄만, 금액은 `[data-k="amt"]:not(.warn)`.
- [ ] **Step 4: `?v=4` → `?v=5`** 여섯 화면.
- [ ] **Step 5: 통과를 본다** — 같은 명령 → 통과. 그다음 `python -m pytest tools/sije_web/tests/test_doc_pages.py -q` 전부 통과(다섯 서류가 그대로인지).

### Task 4: 직원 화면 `today.html`

**Files:**
- Create: `today.html`, `js/sije/share-store.js`
- Modify: `sw.js` (`OFFLINE_PAGES` 에 `'today.html'`, `CACHE` v36)
- Create: `tools/sije_web/tests/test_today_page.py`

**Interfaces:**
- Consumes: Task 3 의 게시판 꼴, Task 1 의 `share_link`.
- Produces (`share-store.js`): `watchShare(key: string, cb: (entries: object | null, meta: {fromCache: boolean}) => void, onError) -> unsubscribe` — 앱 · 저장소만 받는다(로그인 부품 없음), `projectConfig(location.hostname)`, `persistentLocalCache({ tabManager: persistentMultipleTabManager() })`, 문서가 없으면 `cb(null, meta)`.

- [ ] **Step 1: 시험을 쓴다** (게시판은 관리자로 직접 넣는다 — 날짜는 시험 날 기준, 휴대폰 창 390px)
  - `test_today_cards_match_board`: 오늘 칸 하나(줄 1 · 3번; 1번 연락처 `010-0000-1234, 010-0000-1235`, 메모 `10/22 연기\n350,000 1234`, 장소 `가짜추모공원 제례실`, 팀장 · 안내 번호, 장례식장 · 발인 · 화장, 금액) → 카드 머리 `['1번', '3번']`, `tel:` 주소 = 번호 셋(연락처 둘 · 팀장 하나) + 안내, 메모 숫자로는 버튼 없음, 지도 주소 = 네이버 + quote, 메모 줄바꿈 그대로, 빈 칸 이름표 없음(3번 카드에 '안내' 없음).
  - `test_today_day_buttons`: 어제 · 오늘 · 내일 · 모레 칸 → 버튼 글자 `오늘 …`, `내일 …`, `M월 D일 (요일)`(어제 없음), 처음은 오늘 것이 보임, [내일] 누르면 내일 줄이 보임. 오늘 칸이 없으면 내일 것이 처음.
  - `test_today_bad_or_old_link`: `#` 없음 · `#없는암호` · `share_link.new_key` 로 바꾸기 전 암호 → "링크가 바뀌었습니다. …"; 빈 게시판 → "올라온 일정이 없습니다. …".
  - `test_today_odd_characters`: 장소 `가짜동 #3 & 5%-1`, 메모 `<b>굵게</b>` → 지도 주소 == 네이버 + `urllib.parse.quote(장소, safe='')`, 메모 글자가 그대로(굵은 글씨 요소 없음).
  - `test_today_updates_live`: 직원 창(로그인 없음)에서 오늘 일정이 보이는 중에 사장님 창(1280px)에서 같은 일정표 장소를 고침 → 직원 창이 새로고침 없이 새 장소.
  - `test_today_fits_phone`: 긴 장소 · 메모 → `clientWidth == 390`, 오른쪽 끝을 넘는 요소 없음(`test_daily_long_text_fits_phone` 과 같은 재기).
  - `test_today_offline_shows_last`: 한 번 연 뒤 끊고 다시 열기(`test_offline.py` 의 방식) → 지난 카드 + "연결 안 됨 — 마지막으로 받은 내용입니다".
- [ ] **Step 2: 실패를 본다** — `python -m pytest tools/sije_web/tests/test_today_page.py -q` → 404 로 실패.
- [ ] **Step 3: `share-store.js` · `today.html` · `sw.js` 를 쓴다.** 색 · 글꼴은 `call.html` 과 같게, 날짜 버튼 · 카드 · 상태 글은 Global Constraints 의 글자 그대로.
- [ ] **Step 4: 통과를 본다** — 같은 명령 → 통과. `python -m pytest tools/sije_web/tests/test_offline.py -q` 도 통과.

### Task 5: 일정표에서 두 번째 창 빼기

**Files:**
- Modify: `daily-schedule.html` (`#call-dlg`, `callLink` · `offerCallLink` · `CALL_KIND`, 부르던 두 곳; `telShape` · `dashTels` 는 남김)
- Modify: `call.html` (머리 주석: "만드는 쪽은 … callLink" → "더는 만들지 않음 — 10-21 오전에 보낸 링크용")
- Modify: `tools/sije_web/tests/test_doc_pages.py`

- [ ] **Step 1: 시험을 고친다** — `test_daily_phone_send_then_call_link` · `test_daily_pc_send_then_copy_call_link` · `test_daily_call_link_shows_map_for_places` 를 지우고, `test_daily_cancelled_send_shows_no_call_window` 를 `test_daily_send_has_no_second_window` 로 바꾼다: 휴대폰 공유 성공 뒤 공유는 한 번(`__shared.length == 1`) · `#call-dlg` 요소가 없음, PC 복사 뒤에도 없음. `test_call_page_shows_nothing_for_a_bad_link` 는 남긴다. 안 쓰게 된 `CALL_HEAD` 를 지운다.
- [ ] **Step 2: 실패를 본다** — 그 시험 → `#call-dlg` 가 있어 실패.
- [ ] **Step 3: 화면에서 뺀다.**
- [ ] **Step 4: 통과를 본다** — `python -m pytest tools/sije_web/tests/test_doc_pages.py -q -k daily or call` → 통과.

### Task 6: 마무리 확인

- [ ] **Step 1:** 전체 시험 — `python -m pytest tools/sije_web/tests -q` 와 `node --test "tools/sije_web/js-tests/*.test.mjs"` → 전부 통과(수를 적는다).
- [ ] **Step 2:** 휴대폰 폭 사진 — 시험용 게시판에 가짜 일정을 넣고 `today.html` 을 390px 로 찍어 본다(`%TEMP%` 에 저장, 되읽은 폭을 적는다).
- [ ] **Step 3:** `git status --porcelain` 에 시험이 남긴 파일 없음.
- [ ] **Step 4 (자동 저장으로 올라간 뒤):** `https://foodbell.kr/today.html` → 200, 서버의 `daily-schedule.html` 에 `call-dlg` 없음 · `doc-page.js?v=5`.
- [ ] **Step 5:** 사장님께 실제 링크를 대화창으로 드리고 확인 순서(공지 올리기 → 내일 일정표 한 번 열기 → 직원 폰에서 [전화] · [지도] → 일정표를 고친 뒤 링크 화면이 바뀌는지)를 알린다. 진행중.md 를 고친다(암호는 적지 않음).
