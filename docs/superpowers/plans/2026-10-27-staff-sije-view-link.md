# 담당자용 시제 내역서 보기 링크 — 실행 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 이 저장소에서는 `superpowers-extras` 스킬도 함께 적용한다(자동 저장 · 다시 켜기 · 직전에 묻기).

**Goal:** 확정 내역서마다 보기 전용 링크(`sije-view.html#암호`)를 만들어, 그 행사 담당자가 행사 전날 · 당일에 휴대폰으로 내역서를 본다.

**Architecture:** 사장님 내역서 화면의 [담당자 링크] 가 행사에 `viewKey` 를 만들고(고친 시각은 그대로) 링크 글을 카톡으로 넘긴다.
사무실 PC 프로그램이 5분마다 오늘 · 내일 확정 + `viewKey` 있는 행사를 `staffSheets/{viewKey}` 한 장으로 올리고 범위 밖은 지운다.
`sije-view.html` 은 로그인 없이 그 한 장을 실시간으로 읽어 휴대폰 모양(표 없이 쌓는 줄)으로 그린다.

**Tech Stack:** 정적 HTML/JS(Firebase JS SDK, `js/sije/firebase-config.js` 의 SDK 판) · Python 3(firebase-admin, pytest, Playwright) · Firestore 보안 규칙 · node --test

**Spec:** `docs/superpowers/specs/2026-10-27-staff-sije-view-link-design.md` — 실행하는 쪽은 설계서와 이 계획서를 같이 읽는다.

## Global Constraints

- 보이는 기간: 행사 날짜가 **오늘 또는 내일**(사무실 PC 시계 = 한국 시각)인 것만 올린다. 그 밖은 지운다.
- 올리는 행사: `status == '확정'` **그리고** `viewKey` 가 있는 것만.
- 한 장에 넣는 칸(설계서 그대로): `date, time, place, titlePlace, setting, templateType, sijeil, sansinje, meal, staffCar, departTime, arriveTime, customer, contacts, amount, amountDetail, mustDo, extraItems, memo, items, at`.
  넣지 않는 것: 그림, `expectedDate · basis · confirmedText`, `fileLabel · sourceFile`, `status`, `printedAt`, `updatedAt`, `itemRows`, `viewKey`.
- `items` = 왼쪽 `L01…` 다음 오른쪽 `R01…` 순서의 `{group, name, qty, note}` 목록, 수량 · 비고가 **둘 다 빈** 줄은 뺀다.
- `viewKey` 를 쓸 때 `updatedAt` 을 바꾸지 않는다(바꾸면 PDF 를 다시 그리고 인쇄한 확정이 `확정 (인쇄 전)` 으로 간다).
- 암호: 24바이트 난수 → base64url 32글자(`[A-Za-z0-9_-]{32}`). 규칙 · 코드 · 문서에 실제 암호를 적지 않는다.
- 화면 글(그대로 쓴다):
  - 없을 때: `지금은 볼 수 없는 내역서예요. 행사 전날부터 당일까지 열려요. 링크가 맞는지 사장님께 여쭤 주세요.`
  - 공유 글: `[푸드벨] 10월 31일 (토) 10시 ○○ 시제 내역서 (보기만)` · 링크 · `행사 전날부터 당일까지 열려요.` (세 줄, ○○ = `titlePlace` 없으면 `place`, 날짜가 비면 날짜 · 시간 부분을 뺀다)
  - PC 복사 알림: `링크를 복사했어요 — 카톡 대화창에 붙여 넣으세요`
  - 확정이 아닐 때 더하는 알림: `확정이 되어야 담당자에게 보여요`
- 사무실 프로그램 기록 줄: `담당자 내역서 올림: <날짜>` · `담당자 내역서 지움: <날짜>` — 장소 · 손님은 기록에 안 쓴다.
- 휴대폰: 표 없음, 고정 폭 · 최소 폭 없음, 긴 글은 줄바꿈(`overflow-wrap:anywhere`, 한글 `word-break:keep-all`), 글자 14px 이상, [전화] · [지도] 44px 이상.
- 앞 작업(직원 링크, `.superpowers/sdd/2026-10-21-staff-today-link/progress.md`)에서 옮겨 오는 규칙:
  - 이 사무실 PC 에는 firebase CLI 로그인이 없다 → 보안 규칙은 **관리자 열쇠 + Firebase Rules REST API** 로 올린다(그때 쓴 방법, `firebase-setup-from-cli` 스킬의 '열쇠만 있는 PC'). `npx firebase-tools … deploy` 는 로그인이 있는 PC 에서만.
  - 화면이 "없음"(null) 답을 **기기 저장본에서** 받으면 안내 글을 띄우지 않고 서버 답을 기다린다 — 처음 여는 폰은 늘 "없음" 이 먼저 온다.
  - 메모 · 꼭 지킬 것은 줄바꿈을 살려 보인다(`white-space: pre-line`).
  - 글꼴 · 외부 스크립트가 답이 없어도 화면이 뜨게 `today.html` 의 `<head>` 방식을 그대로 쓴다(약한 신호에서 멈췄던 일).
- 파이썬이 창에 찍는 글에 `—` 를 쓰지 않는다(윈도우 cp949 창에서 죽는다, 기록장 #42). 내용에 `\` 가 있으면 heredoc 대신 편집 도구로 쓴다(#25).
- 이 저장소는 **답이 끝날 때 자동 저장**(commit · push)된다 — 아래 "Commit" 단계는 직접 커밋하지 말고 바꾼 파일 목록만 기록장에 적는다. 시작 커밋을 먼저 적어 둔다.
  `.superpowers/` 가 무시되는지 먼저 본다(`git check-ignore -q .superpowers/x`). 공유 코드(`js/sije/store.js` · `share-store.js`)를 바꾼 차례는 **전체 시험이 끝나기 전에 답을 끝내지 않는다**(기록장 #71).

## Review Focus

1. 사장님이 날짜를 범위 밖으로 바꿈(내일 → 다음 주) → 다음 차례에 한 장이 지워지고 링크는 "지금은 볼 수 없는" 글. (Task 1 시험)
2. 연락처가 `총무 010-0000-0001` 처럼 이름이 붙은 글 · 쉼표로 여러 번호 → 번호마다 [전화], 이름 글자는 남음. 번호 모양이 아닌 숫자에는 단추 없음. (Task 3 시험)
3. 빈 양식으로 만든 행사(수량 · 비고가 빈 품목) → 그 줄은 안 보이고, 남은 줄이 없으면 "준비 품목" 제목도 안 보임. (Task 1 · 3 시험)
4. 오래된 휴대폰 브라우저처럼 `navigator.share` 가 없는 휴대폰 → PC 처럼 복사로 넘어간다. (Task 4 시험)
5. 같은 행사에서 [담당자 링크] 를 여러 번 · 두 기기에서 → 같은 링크(이미 있으면 새로 만들지 않음). (Task 4 시험)

---

### Task 1: 사무실 PC 프로그램 — 담당자 한 장 만들기 · 올리기 · 지우기

**Files:**
- Create: `tools/sije_web/staff_sheets.py`
- Modify: `tools/sije_web/office_agent.py` (`one_cycle` 에 단계 하나, `main` 에서 넘김)
- Test: `tools/sije_web/tests/test_staff_sheets.py`(새), `tools/sije_web/tests/test_office_agent.py`

**Interfaces:**
- Produces: `staff_view(ev: dict) -> dict` — Global Constraints 의 칸만(`at` 제외, `at` 은 쓸 때 서버 시각).
- Produces: `sync_staff_sheets(db, today: datetime.date) -> dict` → `{'written': [날짜 글자, …], 'removed': [날짜 글자, …]}`.
  `db.collection('events').where(filter=FieldFilter('date', 'in', [오늘, 내일]))` 로 읽고, `db.collection('staffSheets').stream()` 으로 지금 올라간 것을 본다.
  쓸 때 `staffSheets/{viewKey}.set({**staff_view(ev), 'at': SERVER_TIMESTAMP})`, 같은 내용(`at` 뺀 비교)이면 안 쓴다.
- Produces: `one_cycle(source, work_root, state_file, base_url, log, calendar=None, vault=None, sheets=None)` — `sheets` 는 Firestore db(없으면 건너뜀). `main` 은 `sheets=source.db` 를 넘긴다.

- [ ] **Step 1: 실패하는 시험 쓰기** — `test_staff_sheets.py`. 가짜 저장소(`FakeDb`: `collection(name)` → 문서 사전, `where(filter=...)` 는 `filter.field_path == 'date'`, `filter.op_string == 'in'`, `filter.value` 로 거름, `document(k).get/set/delete`, `stream()`)를 이 파일 안에 둔다. 시험:
  - `test_staff_view_keeps_listed_fields_only` — `fake_event(viewKey='k'*32, printedAt='x', expectedDate='y')` → 결과 칸 집합이 Global Constraints 목록에서 `at` 을 뺀 것과 같다. `amount == '600,000원'`.
  - `test_staff_view_items_left_then_right_and_drops_empty_rows` — L02 의 qty · note 를 비우면 그 품목이 빠지고, 첫 항목은 L01, 마지막은 오른쪽 마지막 키.
  - `test_sync_publishes_only_confirmed_with_key_today_or_tomorrow` — 오늘 · 내일 확정+키(올림), 내일 미확정+키 · 내일 확정 키 없음 · 모레 확정+키 · 어제 확정+키(안 올림) → `staffSheets` 키 집합 = 앞의 둘.
  - `test_sync_does_not_rewrite_unchanged` — 두 번 돌리면 두 번째 `written == []`.
  - `test_sync_removes_out_of_window` — 올라가 있던 한 장의 행사 날짜를 다음 주로 바꾸면 지워지고 `removed == ['<새 날짜 아님, 지운 한 장의 date>']`.
  - `test_office_agent.py::test_staff_sheets_failure_does_not_stop_pdf_and_backup` — `sheets` 로 `collection()` 이 예외를 던지는 가짜 → 백업 엑셀은 생긴다.
- [ ] **Step 2: 실패 확인** — `python -X utf8 -m pytest tools/sije_web/tests/test_staff_sheets.py tools/sije_web/tests/test_office_agent.py -q` → `ModuleNotFoundError: tools.sije_web.staff_sheets` · 새 시험 실패.
- [ ] **Step 3: 구현** — `staff_sheets.py` 에 두 함수(맨 위 설명은 다른 `tools/sije_web/*.py` 처럼 한국어 r-문자열). `office_agent.one_cycle` 에 옵시디언 단계와 같은 모양의 `try/except` 단계(`log.info('담당자 내역서 올림: %s', d)` · `'… 지움: %s'`), `main` 에서 `sheets=source.db`.
- [ ] **Step 4: 통과 확인** — 같은 명령 + `test_pdf_sync.py test_obsidian_copy.py` → 전부 통과.
- [ ] **Step 5: 기록** — 바꾼 파일 목록을 기록장에. (커밋은 자동 저장)

### Task 2: 보안 규칙 — `staffSheets/{암호}` 는 이름을 알면 읽기만

**Files:**
- Modify: `firestore.rules` (`/share/{key}` 블록 아래) — **CRLF 파일**: 편집 도구로만 고치고, 고친 뒤 파이썬으로 `\r\n` · 맨 `\n` 개수를 센다.
- Test: `tools/sije_web/tests/test_rules_live.py`

**Interfaces:**
- Consumes: Task 1 의 `staff_view` (시험 자료 만들기).
- Produces: 규칙 `match /staffSheets/{key} { allow get: if true; }` (주석 한 줄: 담당자 보기, 쓰기는 관리 도구만).

- [ ] **Step 1: 실패하는 시험 쓰기** — `test_staff_sheet_readable_without_login_not_listable_not_writable`: 관리자 열쇠로 `staffSheets/rules-<uuid>` 에 `staff_view(fake_event())` 를 넣고, 로그인 없이 `GET …/staffSheets/<id>` == 200, `GET …/staffSheets`(목록) != 200, 사장님 토큰(`id_token(ALLOWED, allowed=True)`)으로 `PATCH` == 403. 끝나면 지운다.
- [ ] **Step 2: 실패 확인** — 지금 규칙(시험 프로젝트)에서는 첫 GET 이 403 → 실패.
- [ ] **Step 3: 규칙 더하기 · 시험 프로젝트에 올리기** — 시험 관리자 열쇠(`C:\foodbell-keys\sije-test-admin.json`) + Rules REST API(새 ruleset 만들기 → `cloud.firestore` release 바꾸기, 200 확인). (실제는 Task 5 에서 사장님께 물은 뒤 같은 방법으로 실제 열쇠)
- [ ] **Step 4: 통과 확인** — `python -X utf8 -m pytest tools/sije_web/tests/test_rules_live.py -q` → 전부 통과(옛 `share` 시험 포함).
- [ ] **Step 5: 기록** — 줄바꿈 개수 · 바꾼 파일.

### Task 3: 담당자 화면 `sije-view.html`

**Files:**
- Create: `sije-view.html`
- Modify: `js/sije/share-store.js` (`watchSheet` 더함), `sw.js` (`OFFLINE_PAGES` 에 `'sije-view.html'`, `CACHE` `foodbell-v37` → `foodbell-v38`), `tools/sije_web/js-tests/sw.test.mjs`(목록을 확인하면 거기도)
- Test: `tools/sije_web/tests/test_sije_view_page.py`(새)

**Interfaces:**
- Consumes: Task 1 `staff_view` (시험 자료), Task 2 규칙.
- Produces: `watchSheet(key: string, cb: (sheet: object|null, meta: {fromCache: boolean}) => void, onError) => unsubscribe` — `watchShare` 와 같은 db 초기화를 함께 쓴다.

- [ ] **Step 1: 실패하는 시험 쓰기** — 시험 프로젝트 `staffSheets/view-<uuid>` 에 관리자 열쇠로 `staff_view(fake_event(...))` 를 넣고 휴대폰 창으로 `sije-view.html#<그 id>` 를 연다(`test_today_page.py` 의 `ctx` · `phone` 모양, 오류 없는지 `pageerror` 도 본다):
  - `test_view_shows_sheet` — 날짜 · 시간 · 장소 · 상차림 · 손님 · 금액 · 꼭 지킬 것 · 품목(`배 5개`) · 메모가 보이고, `[지도]` href = 네이버 휴대폰 검색(장소), 그림 · `예상` 같은 미확정 글은 없다.
  - `test_view_contacts_get_call_buttons` — `contacts=['총무 010-0000-0001, 010-0000-0002', '가짜 1234']` → `tel:01000000001` · `tel:01000000002` 두 개, `총무` 글자는 남음.
  - `test_view_hides_items_heading_when_no_rows` — 모든 품목 수량 · 비고를 비운 한 장 → "준비 품목" 이 안 보인다.
  - `test_view_missing_key_message` — 없는 암호 → Global Constraints 의 없을 때 글.
  - `test_view_keeps_line_breaks` — `mustDo='가짜 첫째\n가짜 둘째'` 가 두 줄로 보인다.
  - `test_view_updates_live` — 연 뒤 관리자 열쇠로 `memo` 를 바꾸면 화면 글이 바뀐다.
  - `test_view_fits_phone` — 긴 자료(장소 60글자, `mustDo` 5줄, 연락처 5개, 비고 40글자, 품목 30줄)로 폭 **360 · 390**, 그리고 390 에서 `document.documentElement.style.zoom='1.3'` → 각각 `clientWidth` 를 되읽어 확인하고 오른쪽 끝을 넘는 요소 0(`test_today_fits_phone` 의 검사), `scrollWidth <= clientWidth`. **대조:** 같은 화면에 폭 600px 상자를 넣으면 검사가 그 상자를 잡는다.
  - `test_view_opens_in_kakao_browser` — 안드로이드 카톡 브라우저 이름표(user agent: `… KAKAOTALK …`)로 열어도 내역서가 보인다.
- [ ] **Step 2: 실패 확인** — `python -X utf8 -m pytest tools/sije_web/tests/test_sije_view_page.py -q` → 페이지 없음으로 실패.
- [ ] **Step 3: 구현** — `today.html` 을 본뜬 한 장(로그인 없음, `noindex`, 같은 색 · 글꼴 변수, `#` 암호, 기기 저장 · 연결 안 됨 알림, 서비스워커 등록). 그리기 차례는 설계서 "담당자 화면" 절. 연락처 줄은 `today.html` 의 `telShape` · `phoneLines` 와 같은 규칙.
- [ ] **Step 4: 통과 확인** — 새 시험 + `test_today_page.py test_offline.py` + `node --test tools/sije_web/js-tests/*.test.mjs` 전부 통과.
- [ ] **Step 5: 사진 두 장(360 · 390, 긴 자료)을 `%TEMP%` 에 찍어 둔다** — Task 5 에서 사장님께 보여 드림. 작업 폴더에 png 를 두지 않는다.

### Task 4: 내역서 화면 [담당자 링크]

**Files:**
- Modify: `js/sije/model.js` (`newViewKey`, `viewLinkText`), `js/sije/store.js` (`setViewKey`), `js/sije/sheet-page.js` (단추), `sije-sheet.html` (단추 · `sheet-page.js?v=3` → `?v=4`)
- Test: `tools/sije_web/js-tests/model.test.mjs`, `tools/sije_web/tests/test_sheet_page.py`

**Interfaces:**
- Produces: `newViewKey(): string` — `crypto.getRandomValues(new Uint8Array(24))` → base64url 32글자.
- Produces: `viewLinkText(ev: object, link: string): string` — Global Constraints 의 세 줄(줄바꿈 `\n`).
- Produces: `setViewKey(id: string, key: string): Promise` — `updateDoc(doc(db,'events',id), { viewKey: key })` 만.

- [ ] **Step 1: 실패하는 시험 쓰기**
  - node: `newViewKey()` 가 `/^[A-Za-z0-9_-]{32}$/` 이고 두 번 부르면 다름. `viewLinkText({date:'2026-10-31', time:'10시', titlePlace:'가짜동 1-1', place:'가짜동 1-1 뒷산'}, 'https://foodbell.kr/sije-view.html#' + 'a'.repeat(32))` ==
    `'[푸드벨] 10월 31일 (토) 10시 가짜동 1-1 시제 내역서 (보기만)\nhttps://foodbell.kr/sije-view.html#aaaa…\n행사 전날부터 당일까지 열려요.'`. `titlePlace` 가 비면 `place`, `date` 가 비면 `'[푸드벨] 가짜동 1-1 시제 내역서 (보기만)'`.
  - pytest(`test_sheet_page.py`, PC 창, `grant_permissions(['clipboard-read','clipboard-write'])`):
    `test_view_link_copies_same_link_and_keeps_updated_at` — 누르기 전 `updatedAt` 을 읽고, `#view-link` 두 번 → 클립보드 글 두 번 같음, 둘째 줄이 `sije-view.html#` + 문서의 `viewKey`, `updatedAt` 그대로, 알림에 `링크를 복사했어요`.
    `test_view_link_warns_when_not_confirmed` — 상태 미확정 행사 → 알림에 `확정이 되어야 담당자에게 보여요`.
    `test_view_link_phone_shares_text_only` — 휴대폰 창에서 `navigator.share` 를 받은 인자를 적어 두는 가짜로 바꾸고 누르면 인자 키가 `['text']` 뿐.
    `test_view_link_phone_without_share_copies` — 휴대폰 창에서 `navigator.share` 를 지우면 복사로 넘어간다.
- [ ] **Step 2: 실패 확인** — `node --test tools/sije_web/js-tests/model.test.mjs` · `python -X utf8 -m pytest tools/sije_web/tests/test_sheet_page.py -q -k view_link` → 실패.
- [ ] **Step 3: 구현** — 단추는 그림 붙이기 · 인쇄 · 목록 단추줄에(인쇄 · PDF 에 안 나오게). 누르면: `viewKey` 가 없으면 `newViewKey()` → `setViewKey` (화면의 `ev` 에도 넣어 두 번째 누를 때 같은 값). 휴대폰(`matchMedia('(pointer: coarse)')` + `navigator.share` 있음)은 `share({ text })`, 아니면 `clipboard.writeText` + 알림. 확정이 아니면 알림 끝에 Global Constraints 의 글을 더한다.
- [ ] **Step 4: 통과 확인** — `test_sheet_page.py` · `test_list_page.py` 전체, **`store.js` 를 바꿨으니 `test_doc_pages.py` 전체**(약 12분, 앞에서 기다린다 — #71), node 전체.
- [ ] **Step 5: 기록** — 바꾼 파일 · `?v=` 올린 곳.

### Task 5: 내보내기 · 확인 (사장님과 함께 — 되돌리기 어려운 것은 직전에 묻는다)

- [ ] **Step 1:** 시험 전체(파이썬 `tools/sije_web/tests` 전부 · node 전부)를 한 번 더 — 결과 숫자를 적는다.
- [ ] **Step 2: 사장님께 사진 보여 드리기** — Task 3 Step 5 의 360 · 390 사진. 고칠 곳이 나오면 Task 3 으로.
- [ ] **Step 3: 실제 규칙 올리기 — 직전에 묻는다.** 먼저 실제 프로젝트의 지금 규칙을 받아(서비스 계정으로 Firebase Rules API `projects/<id>/releases/cloud.firestore` → 그 ruleset 의 원문) 저장소의 마지막 `firestore.rules`(이번 변경 전 커밋)와 비교한다(기록장 #46). 같을 때만, 사장님 "예" 를 받고 실제 관리자 열쇠(`C:\foodbell-keys\sije-admin.json`) + Rules REST API 로 올린다(Task 2 와 같은 방법).
- [ ] **Step 4: 사무실 PC 프로그램 다시 켜기** — 예약 작업 "푸드벨 시제 PDF" 끄고 켜기, 프로세스 시작 시각 > `staff_sheets.py` 바꾼 시각인지 확인.
- [ ] **Step 5: (자동 저장으로 올라간 뒤) 배포 확인** — `curl -s -o /dev/null -w "%{http_code}" https://foodbell.kr/sije-view.html` == 200, 서버의 `sije-sheet.html` 에 `sheet-page.js?v=4`.
- [ ] **Step 6: 실제 한 번** — 사장님이 내일 날짜 확정 행사 하나에서 [담당자 링크] → 자기 휴대폰에서 연다. **링크를 만든 시각부터 담당자 화면에 뜨기까지 걸린 시간을 재서 설계서의 "5분 안에" 와 나란히 보고한다**(기록장 #59).
- [ ] **Step 7: 끝내기 전 점검(superpowers-extras)** — 실제 파일로 구조 확인 · 앞 단계 수정 옮기기 · 도는 프로그램 다시 켜기 · 커밋 범위와 배포 확인 · 직전에 묻기 — 각각 한 줄씩 결과(해당 없으면 "해당 없음").
