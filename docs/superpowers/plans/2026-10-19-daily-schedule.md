# 직원용 일일 일정표 서류 — 작업 계획 (10-20 새 설계로 다시 씀)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 함께 적용: `superpowers-extras` 스킬(이 사용자 환경의 보조 규칙).

**Goal:** 서류 웹의 여섯 번째 서류 "일일 일정표"(`daily-schedule.html`)를 만든다. 사장님이 저녁에 다음 날 일정을 채워 카톡 단톡방에 사진으로 보내고, 직원 10명은 구글로 로그인해 일정표만 **보기**로 연다(밴드 대신). 사무실 PC 가 옵시디언에 사본을 남긴다.

**Architecture:** 알바비 지급내역서(`staff-pay.html`)를 본떠 화면 파일 하나를 만들고, 공통 부품(`js/docs/doc-page.js`)에 "보기 전용"과 "이어받기" 고리 두 개만 더한다. 보안 규칙에 보기 명단(`viewers`)을 더하고, 사무실 PC 상주 프로그램(`office_agent.py`)에 옵시디언 사본 차례를 붙인다. 장 나누기 계산은 따로 시험할 수 있게 작은 모듈(`js/docs/paging.js`)로 뺀다.

**Tech Stack:** 정적 HTML/CSS/JS(빌드 없음), 파이어베이스(Firestore · 구글 로그인), html2canvas, node --test, pytest + Playwright, Pillow(아이콘).

**Spec:** `docs/superpowers/specs/2026-10-19-daily-schedule-design.md` — 특히 "10-20 추가 결정" 1 · 2 절. 견본 화면은 사장님이 확인함(10-20).

## Global Constraints

- 종류 `daily-schedule` · 목록 제목 `일일 일정표` · 버튼 글자 `일정표` · 화면 `daily-schedule.html`.
- 사진 · PDF 이름 `일일일정표_YYYY-MM-DD`(일정 날짜, 못 읽으면 오늘). 사진이 여러 장이면 `_1` · `_2` …
- 새로 만들 때: 날짜 = **내일**, 요일 계산(`(월)`…`(일)`, 못 읽는 날짜면 빈칸). 순번 · 전달 메모 = **가장 최근에 고친 일정표**에서 이어받음, 하나도 없으면 전달 메모만 아래 글:
  `추모공원(협력업체)은 회사에서 출발 전에 전화 · 화장은 시작 5분 후 전화 · 매장은 발인 5분 전에 팀장에게 전화 · 상주(직접주문)에게는 가게 출발 전에 전화`
- 표 칸 여섯(이 순서): 번호 / **담당 직원 · 차량** / 시간 · 장소 · 연락처 / 행사 내용 · 인원 · 금액 / 상조팀장 · 현지 안내인 / 메모. **집합 칸 없음.** 휴대폰 카드도 번호 옆 첫 줄이 담당 직원(10-20 사장님).
  칸 폭(PC) 6% / 15% / 23% / 24% / 15% / 나머지.
- 금액 = 인원 × 단가(저절로), 표시 `60명 × 15,000원 = 900,000원`. 하루 합계 없음.
- 표제 "푸드벨" 옆 `foodbell.kr` 링크(`https://foodbell.kr/`) + QR(`images/qr-foodbell.png`, `design/qr/qr-화면.png` 사본). 복사 글 맨 끝에 `https://foodbell.kr/` 한 줄. 보내기 공유 글에 `https://foodbell.kr/daily-schedule.html` 한 줄.
- 직원(보기 명단)은 일정표만 읽는다 — 다른 종류 서류 · 쓰기 · 지우기는 규칙이 막고, 화면은 편집 · 새 일정표 · 지우기 버튼을 숨긴다. 알림은 카톡(보내기)뿐 — 푸시 없음.
- 손님 이름 · 연락처 · 직원 실명을 예시 · 시험 자료에 넣지 않는다(시험 글자는 `가짜동` · `가짜일` · `010-0000-0000`).
- **이 집 PC 에는 관리자 열쇠(`C:\foodbell-keys`)가 없다** → 파이썬 시험(`test_rules_live.py` · `test_doc_pages.py` · `test_backup.py` 등 시험 서버에 붙는 것)과 보기 명단 넣기는 **노트북 · 사무실 PC 에서**. 집 PC 에서는 `node --test` 와 코드 작성까지.
- 저장(커밋 · 푸시)은 자동 저장 훅이 한다(어느 폴더에서 연 대화든 galleypark 도 저장됨, 10-20). 과제마다 직접 커밋하지 않고 **바꾼 파일 목록**을 기록장에 남긴다. 시작 커밋을 적어 둔다. 시작 전에 `git check-ignore -q .superpowers/x` 로 계획 폴더가 무시되는지 보고, 아니면 `.git/info/exclude` 에 `.superpowers/` 를 넣는다(집 PC 는 무시 안 됨 — 10-20 확인).
- 자동 저장은 답이 끝날 때마다 GitHub → 버셀에 게시한다. 그래서 **규칙(Task 1)을 실제 프로젝트에 올린 뒤에 화면(Task 3)을 만든다** — 반대면 게시된 화면의 "새 일정표"가 권한 없음으로 실패한다. 실제 프로젝트 올리기는 **직전에 사장님께 묻는다**.
- `doc-page.js` · `docs.css` 를 고치면 그 둘을 부르는 다섯 화면(`sije-quote` · `event-quote` · `sije-worksheet` · `statement` · `staff-pay`)의 `?v=2` 를 `?v=3` 으로 올린다(`캐시버전올리기.py` 는 이 둘을 안 올린다).
- 실행: 저장소 맨 위(`c:\galleypark`). JS `node --test "tools/sije_web/js-tests/*.test.mjs"`, 파이썬 `python -m pytest tools/sije_web/tests/<파일> -q`.
- 앞 단계 기록장(`.superpowers/…` 의 `Final:` · `Ruling:`)은 노트북에만 있어 이 PC 에서 못 읽었다 — 노트북에서 실행하면 시작 전에 읽고 해당되는 것을 여기에 더한다. 알려진 것: 외부 글꼴은 `media=print onload` 로(막히면 화면이 멈춤), 대기는 `navigator.onLine` 에 기대지 않고 `atMost` 로 묶는다.

## Review Focus

1. 날짜를 연도 없이 · 없는 날(2월 30일)로 고침 → 요일 빈칸, 목록 이름은 적힌 그대로, 파일 이름은 오늘 — Task 3 `test_daily_weekday_follows_date`.
2. 연말에 "새 일정표" → 다음 해 1월 1일 (금) — Task 3 `test_daily_fresh_date_rolls_over_year`.
3. 하루 15건(밴드에 실제로 있었던 최대) → 인쇄 · 사진이 줄을 자르지 않고 장을 나눔 — Task 3 `test_page_groups_*`(node) · `test_daily_fifteen_rows_split_into_pages`.
4. 보기 명단 직원이 화면을 거치지 않고 저장소에 직접 쓰기 · 다른 종류 읽기 → 거부 — Task 1 `test_viewer_*`.
5. 단가 · 인원을 `15,000원` · `60명` 처럼 손으로 침 → 숫자만 읽어 금액이 맞음, 비우면 아래 줄 숨김 — Task 3 `test_daily_amount_from_typed_numbers`.

---

### Task 1: 종류 등록 · 보기 명단 규칙

**Files:**
- Modify: `js/docs/doc-model.js` (`KINDS`, `rowCells`), `tools/sije_web/backup.py` (`DOC_KINDS`), `firestore.rules`, `tools/sije_web/allow.py`, `tools/sije_web/tests/conftest.py` (`custom_token` · `id_token`)
- Test: `tools/sije_web/js-tests/doc-model.test.mjs`, `tools/sije_web/tests/test_backup.py`, `tools/sije_web/tests/test_rules_live.py`

**Interfaces:**
- Produces: `KINDS['daily-schedule'] = { title: '일일 일정표', noun: '일정표' }`; `rowCells('daily-schedule', doc) → [doc.label || '(날짜 없음)', doc.count || '0건', '']`; `DOC_KINDS['daily-schedule'] = '일일 일정표'`.
- `allow.py`: `add_viewer(db, email)`, `remove_viewer(db, email)`, `list_viewers(db) -> list[str]` + 명령 `viewer-add` · `viewer-remove` · `viewer-list`(`viewers/{메일 소문자}` 문서).
- 규칙: `viewer()` = 로그인 · 메일 확인 · `viewers/{메일}` 있음. `docs` 읽기 = `allowed() || (viewer() && resource.data.kind == 'daily-schedule')`; 쓰기 · 지우기 = `allowed()` 만(kind 목록에 `daily-schedule` 추가). `allow/{메일}` · `viewers/{메일}` 은 **그 메일로 로그인한 사람만** `get`.
- conftest: `custom_token(email, allowed, viewer=False)` · `id_token(email, allowed, viewer=False)` — viewer 면 보기 명단에 넣고 끝나면 뺀다.

- [ ] **Step 1: 실패하는 시험** — doc-model: 여섯 종류 제목 + `rowCells('daily-schedule', {label:'2026년 10월 21일 (수)', count:'3건'})` → `['2026년 10월 21일 (수)','3건','']`, 빈 것 → `['(날짜 없음)','0건','']`. backup: `FAKE_DOCS` 에 `daily-schedule` 한 장 → 종류 칸 `일일 일정표`. 규칙(`test_rules_live.py`):
  - `test_docs_daily_schedule_kind_allowed` — 허락된 사람이 만들기 200.
  - `test_viewer_reads_daily_schedule_only` — 보기 명단 사람: daily-schedule 읽기 200, `staff-pay` 읽기 403.
  - `test_viewer_cannot_write_or_delete` — 보기 명단 사람: daily-schedule 고치기 · 만들기 · 지우기 403.
  - `test_own_allow_and_viewer_doc_readable_others_not` — 자기 `allow`/`viewers` 문서 get 200, 남의 것 403(기존 `test_allow_collection_unreadable` 는 "남의 것"으로 바꾼다).
- [ ] **Step 2: 실패 확인** — node(집 PC 가능) FAIL, 파이썬(열쇠 있는 PC) FAIL.
- [ ] **Step 3: 구현** — 위 Interfaces 대로.
- [ ] **Step 4: 시험 프로젝트에 규칙** — `npx firebase-tools@15.34.0 deploy --only firestore:rules --project test` → `Deploy complete!`, **1분 기다린 뒤** Step 2 시험 → PASS, `node --test` 전체 PASS.
- [ ] **Step 5: 실제 프로젝트 — 사장님께 묻고 나서.** 물을 말: "보안 규칙에 '일일 일정표'와 직원 보기 명단을 더해 실제 서버에 올려도 될까요? 시험 서버에서 시험 N개 통과했고, 다른 서류에는 영향이 없습니다." 허락하면 `--project default`. 없으면 Task 2 까지만 하고 멈춘다(Task 3 은 규칙 뒤).
- [ ] **Step 6: 기록장** — 바꾼 파일 목록.

---

### Task 2: 공통 부품 — 보기 전용 · 이어받기

**Files:**
- Modify: `js/sije/store.js` (`myRole`), `js/docs/doc-page.js`, `css/docs.css`, 다섯 서류 화면의 `doc-page.js?v=` · `docs.css?v=`
- Test: `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Consumes: Task 1 규칙(자기 `allow`/`viewers` get).
- Produces: `myRole(email: string) → Promise<'owner'|'viewer'|'none'>` (allow 문서 있으면 owner, 아니면 viewers 문서 있으면 viewer). doc-page: 로그인 뒤 `document.body.dataset.role` 에 그 값; `viewer` 면 `#doc-new` · `#doc-del` · `#btn-edit` 숨김(`docs.css`), `D.editing()` 이 참이 되지 않게 편집 진입을 막고 저장(`saveDoc`)을 부르지 않는다. 이어받기: 받은 목록을 `lastRows` 에 두고, `makeNew` 에서 `D.fresh()` 다음에 `D.inherit` 가 있으면 `D.inherit(sortDocs(lastRows)[0]?.doc ?? null)`.

- [ ] **Step 1: 실패하는 시험** — `test_viewer_sees_denied_on_other_kinds`(보기 명단 사람이 `staff-pay.html` → 권한 없음 화면). 기존 `test_new_doc_creates_one_and_opens_it` 다섯 종류는 그대로 PASS 여야 함(이어받기가 없는 종류에 영향 없음).
- [ ] **Step 2: 실패 확인 · Step 3: 구현 · Step 4: 통과**(`test_doc_pages.py -q` 전체 — 열쇠 있는 PC).
- [ ] **Step 5: `?v=` 올림 확인** — `git grep -n "doc-page.js?v=\|docs.css?v=" -- "*.html"` 에 `v=2` 가 남지 않음.

---

### Task 3: 화면 `daily-schedule.html` (+ 장 나누기 `js/docs/paging.js`)

**Files:**
- Create: `daily-schedule.html`(`staff-pay.html` 복사해 고침), `js/docs/paging.js`, `images/qr-foodbell.png`(= `design/qr/qr-화면.png`)
- Test: `tools/sije_web/js-tests/paging.test.mjs`, `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Consumes: Task 1 `KINDS`, Task 2 `D.inherit` 고리 · `data-role`.
- Produces: `pageGroups(rowHeights: number[], firstCap: number, nextCap: number) → number[][]` — 줄 번호를 장마다 묶는다(첫 장은 표제 · 순번 · 메모 때문에 자리가 적다). 한 줄이 cap 보다 커도 그 줄 혼자 한 장. `window.FoodbellDoc = { kind:'daily-schedule', serialize, load, fresh, inherit, summary, editing, onSave }`; `summary() → { label, issue: label, total: '', count: '<채운 줄 수>건', text: buildText() }`(`text` 는 Task 4 가 쓴다). 칸 표지: `[data-k="date|dow|order|memo|no"]`, 줄 `tr.item` 안 `[data-f="time|place|tel|work|people|price|staff|car|lead|lead-tel|guide-tel|memo"]`, 금액 표시 `[data-k="amt"]`.
- 화면 모양은 사장님이 본 견본(설계서 "종이 모양" + 추가 결정 1 · 2)을 따른다: 큰 날짜 → 순번 띠 → 섹션 제목 `일정 日程` → 전달 메모 → 표. 휴대폰(620px 이하)은 줄마다 카드, 빈 메모 · 빈 상조팀장 칸은 보기에서 숨김.

- [ ] **Step 1: node 시험** `paging.test.mjs` — `pageGroups([10,10,10],100,100)` → `[[0,1,2]]`; `pageGroups(Array(15).fill(30),200,300)` → 첫 장 6줄 · 다음 장 9줄(`[[0..5],[6..14]]`); 아주 큰 한 줄 `[500]` → `[[0]]`; `[]` → `[]`.
- [ ] **Step 2: 화면 시험**(`test_doc_pages.py`, `PAGES` 에 `daily-schedule` 추가 — 공통 9개에 들어감) + 일정표 전용:
  - `test_daily_weekday_follows_date`, `test_daily_fresh_date_rolls_over_year`(옛 계획과 같음)
  - `test_daily_first_doc_gets_default_memo` — 일정표가 하나도 없을 때 새 일정표의 전달 메모 = Global Constraints 의 글.
  - `test_daily_new_doc_inherits_order_and_memo` — 순번 `가짜일 · 가짜이`, 메모 `가짜 메모` 인 일정표가 있으면 새 일정표가 둘 다 같고 날짜는 내일.
  - `test_daily_amount_from_typed_numbers` — 인원 `60명`, 단가 `15,000원` → `[data-k="amt"]` 에 `60명 × 15,000원 = 900,000원`; 둘 중 하나 비우면 그 줄 숨김.
  - `test_daily_counts_filled_rows_only` · `test_daily_long_text_fits_phone`(옛 계획과 같음, 칸 이름만 새것)
  - `test_daily_fifteen_rows_split_into_pages` — 15줄 채우고 사진 만들기 → 사진 2장 이상, 어느 줄도 두 장에 갈리지 않음(장마다 `tr.item` 번호 이어짐).
  - `test_daily_viewer_sees_list_and_doc_without_edit` — 보기 명단 사람: 목록 보임, `#doc-new` 안 보임, 서류 열면 `#btn-edit` · `#doc-del` 안 보임, `#btn-send` · `#btn-print` 보임.
  - `test_daily_copy_text_ends_with_site_url` — 복사 글 마지막 줄 `https://foodbell.kr/`.
- [ ] **Step 3: 실패 확인 → 구현** — 보내기는 알바비와 같되 사진을 `pageGroups` 로 나눠 여러 장(휴대폰 공유창에 파일 여러 개; PC 는 모두 내려받고 첫 장을 클립보드에, 안내 "N장"). 인쇄는 `@page{size:A4}` + `tr{break-inside:avoid}` + `thead{display:table-header-group}`. 외부 글꼴은 `media=print onload`.
- [ ] **Step 4: 통과** — node 전체, `test_doc_pages.py -q` 전체(열쇠 있는 PC).

---

### Task 4: 옵시디언 사본 (사무실 PC 상주 프로그램)

**Files:**
- Create: `tools/sije_web/obsidian_copy.py`
- Modify: `tools/sije_web/office_agent.py` (`one_cycle` 에 한 차례)
- Test: `tools/sije_web/tests/test_obsidian_copy.py`

**Interfaces:**
- Consumes: Task 3 `summary().text`(저장된 서류의 `text` 칸), `source.all_docs()`.
- Produces: `find_vault(obsidian_json: Path) -> Path | None` — 옵시디언 볼트 목록 중 `푸드벨-업무` 폴더가 있는 볼트; `note_path(vault, label) -> Path` = `vault/푸드벨-업무/일일 일정표/<label>.md`(파일 이름에 못 쓰는 글자는 뺀다); `sync_notes(docs, vault, state: dict) -> list[str]` — `kind=='daily-schedule'` 이고 `updatedAt` 이 state 보다 새것만 쓰고(덮어씀), 쓴 이름을 돌려준다. 지운 일정표의 노트는 그대로 둔다. 볼트를 못 찾으면 `one_cycle` 은 기록에 한 줄 남기고 건너뛴다.

- [ ] **Step 1: 실패하는 시험** — 임시 볼트(`tmp_path/볼트/푸드벨-업무`)와 가짜 서류 둘(일정표 1, staff-pay 1): 일정표만 노트가 생기고 내용이 `text` 와 같음; 같은 `updatedAt` 으로 다시 → 안 씀; 새 `updatedAt` → 덮어씀; `find_vault` 는 그 폴더가 없는 볼트를 고르지 않음.
- [ ] **Step 2: 실패 확인 · Step 3: 구현 · Step 4: 통과**(`test_obsidian_copy.py` 는 시험 서버를 안 써서 집 PC 에서도 됨).
- [ ] **Step 5: 사무실 PC 에서 다시 켜기** — 예약 작업 "푸드벨 시제 PDF" 껐다 켜기 → `office_agent` 프로세스 시작 시각이 바꾼 시각보다 나중인지 확인(`foodbell-site-dev` 8절 명령) → 일정표 하나 고치고 5분 안에 볼트에 노트가 생기는지 본다. (사장님이 사무실 PC 에 있을 때.)

---

### Task 5: 오프라인 사본 · 휴대폰 앱 · 아이콘 · 바탕화면

옛 계획 Task 3 그대로(`sw.js` CACHE v34→v35 · `OFFLINE_PAGES` 에 `daily-schedule.html` 과 `js/docs/paging.js` · `images/qr-foodbell.png`, `manifest-daily.webmanifest`, 주홍 `#C4502A` 아이콘 180 · 192 · 512 · maskable-512 · `아이콘-일정표.ico` — **알바비 아이콘을 다시 그려 원본과 비교한 뒤** 만들고 사장님께 512 를 보여 드린다, `바탕화면-바로가기.ps1`(BOM 확인) · `휴대폰캡처.py` `PAGES`). 시험: `sw.test.mjs` 두 목록에 `daily-schedule.html`.

---

### Task 6: 문서 · 휴대폰 폭 · 게시 확인 · 직원 명단

- [ ] `CLAUDE.md` 파일 목록에 `daily-schedule.html` · `js/docs/paging.js` · `tools/sije_web/obsidian_copy.py` 줄, 아이콘 색 목록에 `일일 일정표=주홍`, 보기 명단 명령(`allow.py viewer-add`).
- [ ] `python 휴대폰캡처.py` → 일정표 폭 390 · 넘침 0, 사진을 눈으로 보고 사장님께 보여 드림.
- [ ] 전체 시험(node + 파이썬 — 열쇠 있는 PC) PASS.
- [ ] **(자동 저장으로 올라간 뒤)** `curl -s -o /dev/null -w "%{http_code}" https://foodbell.kr/daily-schedule.html` → `200`.
- [ ] **직원 명단** — 사장님께 직원 10명의 구글 메일을 받아 `python -m tools.sije_web.allow viewer-add <메일> --key C:\foodbell-keys\sije-admin.json`(열쇠 있는 PC, **넣기 직전에 명단을 보여 드리고 묻는다**) → `viewer-list` 로 10개 확인.
- [ ] 사장님께 남길 것: ① 휴대폰에서 단톡방에 실제로 보내 보기 ② 직원에게 안내할 글(주소 `https://foodbell.kr/daily-schedule.html` · 구글로 로그인 · 홈 화면에 추가) ③ 바탕화면 아이콘은 PC 마다 `바탕화면-바로가기.bat` 한 번(pc-sync 는 바로가기를 만들지 않는다).
