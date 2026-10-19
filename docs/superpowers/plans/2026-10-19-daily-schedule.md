# 직원용 일일 일정표 서류 — 작업 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 서류 웹의 여섯 번째 서류 "일일 일정표"(`daily-schedule.html`)를 만들어, 사장님이 저녁에 다음 날 직원 일정을 채워 카톡 단톡방에 사진으로 올리게 한다.

**Architecture:** 알바비 지급내역서(`staff-pay.html`)를 본떠 새 화면 파일 하나를 만들고, 공통 부품(`js/docs/doc-page.js`)에는
`window.FoodbellDoc` 연결 고리로만 붙는다. 종류 목록(`doc-model.js`) · 보안 규칙 · 백업 · 오프라인 사본 · 아이콘에 한 줄씩 더한다.

**Tech Stack:** 정적 HTML/CSS/JS(빌드 없음), 파이어베이스(Firestore · 구글 로그인), html2canvas, node --test, pytest + Playwright, Pillow(아이콘).

**Spec:** `docs/superpowers/specs/2026-10-19-daily-schedule-design.md`

## Global Constraints

- 종류 `daily-schedule` · 목록 제목 `일일 일정표` · 버튼 글자 `일정표` · 화면 파일 `daily-schedule.html`.
- 사진 · PDF 이름 `일일일정표_YYYY-MM-DD` — **일정 날짜**로(못 읽으면 오늘).
- 새로 만들 때 날짜 = **내일**, 요일은 날짜에서 계산(`(월)`…`(일)`), 못 읽는 날짜면 요일 빈칸.
- 손님 이름 · 연락처를 예시 · 시험 자료에 넣지 않는다(시험 글자는 `가짜동`, `○○`).
- 이 대화는 `c:\dev\vibe-study` 에서 열려 있어 galleypark 자동 저장 · 캐시 경고 훅이 돌지 않는다 → **과제마다 직접 `git pull` → commit → push**(사장님 결정). 캐시 번호도 손으로 확인.
- 보안 규칙의 **실제 프로젝트(`--project default`) 올리기 직전에 사장님께 다시 묻는다.**
- 실행: 저장소 맨 위(`c:\galleypark`)에서. JS 시험 `node --test "tools/sije_web/js-tests/*.test.mjs"`, 파이썬 시험 `python -m pytest tools/sije_web/tests/<파일> -q`.

## Review Focus

1. 날짜를 연도 없이 · 없는 날(2월 30일)로 고침 → 요일 빈칸, 목록 이름은 적힌 글자 그대로, 파일 이름은 오늘 날짜 — Task 2 `test_daily_schedule_weekday_follows_date`.
2. 연말에 "새 일정표" → 다음 해 1월 1일 · 요일이 맞아야 함 — Task 2 `test_daily_schedule_fresh_date_rolls_over_year`.
3. 줄만 추가하고 아무것도 안 친 빈 줄 → 건수 · 복사 글에 안 들어감 — Task 2 `test_daily_schedule_counts_filled_rows_only`.
4. 휴대폰(390px)에서 긴 장소 · 메모 → 카드 안에서 줄바꿈, 화면 밖으로 안 넘침 — Task 2 `test_daily_schedule_long_text_fits_phone`.
5. 다른 기기에서 날짜를 고쳐 화면에 들어옴 → 요일 · 목록 이름이 따라옴 — `load()` 가 `recalc()` 를 부르는 것으로 막음(알바비와 같음), 공통 시험 `test_remote_change_shows_at_once_while_editing` 이 그 경로를 지난다.

---

### Task 1: 종류 등록 — 목록 칸 · 백업 이름 · 보안 규칙

**Files:**
- Modify: `js/docs/doc-model.js` (`KINDS`, `rowCells`)
- Modify: `tools/sije_web/backup.py:25-26` (`DOC_KINDS`)
- Modify: `firestore.rules:34` (kind 목록)
- Test: `tools/sije_web/js-tests/doc-model.test.mjs`, `tools/sije_web/tests/test_backup.py`, `tools/sije_web/tests/test_rules_live.py`

**Interfaces:**
- Produces: `KINDS['daily-schedule'] = { title: '일일 일정표', noun: '일정표' }`;
  `rowCells('daily-schedule', doc) → [doc.label || '(날짜 없음)', doc.count || '0건', '']`;
  `DOC_KINDS['daily-schedule'] = '일일 일정표'`; 규칙이 `kind == 'daily-schedule'` 를 받는다.

- [ ] **Step 1: 실패하는 시험 쓰기**

`doc-model.test.mjs` — 첫 시험의 기대값에 `'daily-schedule': { title: '일일 일정표', noun: '일정표' }` 를 더하고 이름을 `'서류 여섯 종류의 목록 제목과 이름'` 으로. 새 시험:

```js
test('일정표 줄 = 날짜(요일) · 건수 · 빈 칸', () => {
  assert.deepEqual(rowCells('daily-schedule', { label: '2026년 10월 20일 (화)', count: '3건', total: '' }),
    ['2026년 10월 20일 (화)', '3건', '']);
  assert.deepEqual(rowCells('daily-schedule', { label: '', count: '' }), ['(날짜 없음)', '0건', '']);
});
```

`test_backup.py` — `FAKE_DOCS` 에 세 번째 서류를 더하고 기존 시험의 `ws.max_row == 3` 을 `4` 로:

```python
    ('d3', {'kind': 'daily-schedule', 'label': '2026년 10월 20일 (화)', 'issue': '2026년 10월 20일 (화)', 'total': '',
            'count': '2건', 'html': '<p>가짜</p>',
            'createdAt': datetime.datetime(2026, 10, 19, 11, tzinfo=UTC),
            'updatedAt': datetime.datetime(2026, 10, 19, 11, tzinfo=UTC)}),
```

```python
    third = [c.value for c in ws[4]]
    assert third[1] == '일일 일정표' and third[2] == '2026년 10월 20일 (화)' and third[5] == '2건'
```

`test_rules_live.py`:

```python
def test_docs_daily_schedule_kind_allowed(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token, kind='daily-schedule').status_code == 200
```

- [ ] **Step 2: 실패 확인**

Run: `node --test "tools/sije_web/js-tests/doc-model.test.mjs"` → FAIL (KINDS 다름, rowCells 가 `(이름 없음)` …).
Run: `python -m pytest tools/sije_web/tests/test_backup.py tools/sije_web/tests/test_rules_live.py -q -k "docs"` → 백업 FAIL(`daily-schedule` 영문), 규칙 FAIL(403).

- [ ] **Step 3: 구현** — `KINDS` 끝에 한 줄, `rowCells` 에 `if (kind === 'daily-schedule') return [doc.label || '(날짜 없음)', doc.count || '0건', ''];`,
  `DOC_KINDS` 에 한 쌍, `firestore.rules` 목록 끝에 `'daily-schedule'`.

- [ ] **Step 4: 규칙을 시험 프로젝트에 올리고 통과 확인**

Run: `npx firebase-tools@15.34.0 deploy --only firestore:rules --project test` → `Deploy complete!`
Run: Step 2 의 두 명령 → PASS. 이어서 `node --test "tools/sije_web/js-tests/*.test.mjs"` 전체 PASS(다른 시험 안 깨짐).

- [ ] **Step 5: 실제 프로젝트에 규칙 올리기 — 사장님께 묻고 나서**

물을 말: "보안 규칙에 '일일 일정표' 종류를 더해 실제 서버에 올려도 될까요? 다른 서류에는 영향이 없습니다."
허락하면 Run: `npx firebase-tools@15.34.0 deploy --only firestore:rules --project default` → `Deploy complete!`. 허락이 없으면 여기서 멈추고 Task 2 로 가되, 끝날 때 다시 묻는다.

- [ ] **Step 6: 저장** — `git pull --ff-only` → 위 파일들 `git add` → commit `일일 일정표 1: 종류 등록(목록 칸 · 백업 이름 · 보안 규칙)` → `git push`.

---

### Task 2: 화면 `daily-schedule.html`

**Files:**
- Create: `daily-schedule.html` (본보기 `staff-pay.html` 을 복사해 고친다)
- Test: `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Consumes: Task 1 의 `KINDS['daily-schedule']` (공통 부품이 목록 제목 · 버튼 글자로 씀).
- Produces: `window.FoodbellDoc = { kind: 'daily-schedule', serialize, load, fresh, summary, editing, onSave }`;
  `summary() → { label: dayText(), issue: dayText(), total: '', count: '<채운 줄 수>건' }`.
  화면 칸 표지: `[data-k="date"]`(고칠 수 있음) · `[data-k="dow"]`(계산) · `[data-k="memo"]` · 줄 `tr.item` 안
  `[data-f="time|place|work|staff|car|meet-time|meet-place|memo"]` · 번호 `[data-k="no"]`. Task 3 · 4 는 파일 이름만 쓴다.

- [ ] **Step 1: 실패하는 시험 쓰기** — `test_doc_pages.py`

`today_kr()` 아래에:

```python
DOW = '월화수목금토일'

def tomorrow_kr():
    d = datetime.date.today() + datetime.timedelta(days=1)
    return f'{d.year}년 {d.month}월 {d.day}일 ({DOW[d.weekday()]})'
```

`PAGES` 끝(이 함수 아래로 `PAGES` 를 옮긴다)에
`pytest.param('daily-schedule', 'daily-schedule.html', '일정표', '일일 일정표', '직원에게 보내기', tomorrow_kr(), '[data-k="memo"]', id='daily-schedule')`.

공통 시험 두 곳의 기대값을 종류에 맞춘다:
- `test_new_doc_creates_one_and_opens_it`: `assert doc['issue'] == {'sije-worksheet': '', 'daily-schedule': label}.get(kind, today_kr())`
- `test_icon_opens_list_sorted_by_updated` 마지막 두 줄을

```python
    expect = {'staff-pay': ['2026년 10월 16일', '2명', '2,000원'],
              'daily-schedule': ['가짜동 새 문중', '2명']}.get(kind, ['가짜동 새 문중', '2026년 10월 16일', '2,000원'])
    assert all(t in row for t in expect) and '10월 16일 고침' in row, row
```

일정표만의 시험 (파일 끝, `# ---------- 일일 일정표 ----------`):

```python
DAILY = 'daily-schedule.html'


def test_daily_schedule_weekday_follows_date(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, DAILY, custom_token(ALLOWED, allowed=True))
    ref = test_db.collection('docs').document(new_doc(pc, made))
    pc.click('#btn-edit')
    set_text(pc, '[data-k="date"]', '2026년 10월 21일')
    assert pc.inner_text('[data-k="dow"]') == '(수)'
    pc.click('#btn-edit')
    wait_db(ref, lambda s: s.get('label') == '2026년 10월 21일 (수)' and s.get('issue') == '2026년 10월 21일 (수)')
    pc.click('#btn-edit')
    set_text(pc, '[data-k="date"]', '2026년 2월 30일')            # 없는 날
    assert pc.inner_text('[data-k="dow"]') == ''
    pc.click('#btn-edit')
    wait_db(ref, lambda s: s.get('label') == '2026년 2월 30일')


def test_daily_schedule_fresh_date_rolls_over_year(pc, repo_url):
    """로그인 없이도 빈 서식은 그려진다 — 12월 31일 저녁에 열면 내일 = 2027년 1월 1일 (금)."""
    pc.clock.set_fixed_time(datetime.datetime(2026, 12, 31, 20, 0))
    pc.goto(f'{repo_url}{DAILY}')
    pc.wait_for_function("document.querySelector('[data-k=\"dow\"]').textContent !== ''")
    assert pc.eval_on_selector('[data-k="date"]', 'e => e.textContent') == '2027년 1월 1일'
    assert pc.eval_on_selector('[data-k="dow"]', 'e => e.textContent') == '(금)'


def test_daily_schedule_counts_filled_rows_only(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, DAILY, custom_token(ALLOWED, allowed=True))
    ref = test_db.collection('docs').document(new_doc(pc, made))
    pc.click('#btn-edit')
    set_text(pc, 'tr.item [data-f="work"]', '시제 상차림')
    pc.click('tr.addrow button')                                  # 빈 줄 하나 더 — 세지 않는다
    pc.click('#btn-edit')
    wait_db(ref, lambda s: s.get('count') == '1건')
    assert pc.locator('tr.item').count() == 2


def test_daily_schedule_long_text_fits_phone(phone, repo_url, custom_token, made):
    open_list(phone, repo_url, DAILY, custom_token(ALLOWED, allowed=True))
    new_doc(phone, made)
    phone.click('#btn-edit')
    set_text(phone, 'tr.item [data-f="place"]', '가짜동 ' * 15 + '선산 묘역 아래 주차장')
    set_text(phone, 'tr.item [data-f="memo"]', '가짜 메모 ' * 15)
    phone.click('#btn-edit')
    assert phone.evaluate('document.documentElement.clientWidth') == 390
    assert phone.evaluate('document.documentElement.scrollWidth') <= 390
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tools/sije_web/tests/test_doc_pages.py -q -k daily` → FAIL(화면 파일 없음 404 · 시간 초과).

- [ ] **Step 3: `daily-schedule.html` 만들기** — `staff-pay.html` 을 복사해 아래만 바꾼다(나머지 편집 · 저장 · 보내기 · 인쇄 코드는 그대로).

  머리(`<head>`): 제목 `푸드벨 일일 일정표`, 설명문 일정표용, `manifest-daily.webmanifest`, `icons/app-daily-180.png`,
  `apple-mobile-web-app-title` = `일정표`. `css/docs.css?v=2` · `js/docs/doc-page.js?v=2` 는 그대로.

  안내문(`.hint`) — 이 글 그대로:
  `<b>안내</b><strong>편집</strong>을 누르고 맨 위 날짜와 줄마다 시간·장소·행사 내용·담당 직원·차량·집합 시간·장소·메모를 채우세요. 요일은 날짜를 보고 저절로 바뀝니다. <strong>직원에게 보내기</strong>를 누르면 사진으로 카톡 단톡방에 올릴 수 있고, <strong>파일로 저장</strong>하면 일정 날짜로 이름이 붙습니다(예: 일일일정표_2026-10-20.png). 사진은 단톡방 모두가 봅니다. 고치는 대로 저절로 저장되고, 휴대폰·PC 어디서 열어도 같은 일정표가 보입니다. 새 일정은 <strong>목록</strong>에서 <strong>새 일정표</strong>를 누르세요.`

  종이(`.sheet`):
  - 표제 오른쪽: 제목 `일일 일정표` + 인장. 문서번호 · 작성일자(`.meta-list`) 지움.
  - 겹줄(`.rule-double`) 아래 큰 날짜 줄: `<p class="day"><span data-edit data-t="text" data-k="date"></span> <span data-k="dow"></span></p>`
    — 명조 · 굵게 · 30px(휴대폰 24px), 서류에서 가장 큰 글자. 빈 요일 칸은 자리를 차지하지 않음.
  - 섹션 제목 `일정` + 한자 `日程`, 그 아래 전달 메모(알바비와 같은 `.memo`, `data-ph="직원 모두에게 남길 말"`).
  - 표(`table.stmt.day-table`) 칸 여섯 — 번호 6% / 시간 · 장소 22% / 행사 내용 22% / 담당 직원 · 차량 16% / 집합 시간 · 장소 18% / 메모:
    `td.c[data-k="no"]` · `td.when` = `<b data-f="time" data-ph="시간">` + `<span class="sub" data-f="place" data-ph="장소">` ·
    `td.work[data-f="work"][data-ph="행사 내용"]` · `td.crew` = `<b data-f="staff" data-ph="담당 직원">` + `<span class="sub" data-f="car" data-ph="차량">` ·
    `td.meet` = `<b data-f="meet-time" data-ph="집합 시간">` + `<span class="sub" data-f="meet-place" data-ph="집합 장소">` ·
    `td.memo-cell` > `<span data-f="memo" data-ph="메모">` (모든 칸 `data-edit data-t="text"`). `ROW_HTML` 도 같은 모양.
    줄 추가 버튼 글자 `＋ 줄 추가 (일 하나)`. 새 줄을 넣은 뒤 커서는 그 줄의 `[data-f="time"]` 로(알바비의 `date` 는 이 서류에 없다).
  - 합계(`.totals`) 지움. 쓰지 않게 된 CSS(`.parties` · `.prow` · `.in` · `.stamp` · `.totals` · `.sum*` · `.receiver` · `.meta-list`, 알바비 전용 `table.stmt.pay` 블록)는 빼고 일정표 블록을 쓴다.
  - 휴대폰(699px 이하) 카드 차례: 번호(1칸) + 시간 · 장소(2칸) / 행사 내용 / 담당 · 차량 / 집합 / 메모(빈 메모는 보기에서 숨김) — 모두 전체 폭, `overflow-wrap:anywhere`.

  스크립트(알바비 IIFE 를 고침):
  - `NAME = "일일일정표"`, `DOW = ["일","월","화","수","목","금","토"]`.
  - `parseDate(text: string) → Date|null` — `(\d{4})\D+(\d{1,2})\D+(\d{1,2})` 을 읽어 `new Date(y, m-1, d)`, 월 · 일이 그대로가 아니면(2월 30일) `null`.
  - `dayText() → string` — `getText("date")` + (요일 있으면 `" " + 요일`).
  - `recalc()` — 줄 번호, 요일 칸(`parseDate` 결과로 `"(화)"` 또는 `""`), 돌려주는 값 = 칸이 하나라도 적힌 줄 수.
  - `ymd()` — `parseDate(getText("date"))`, 없으면 오늘. `fileBase() = NAME + "_" + ymd()`.
  - `fillFreshDefaults()` — 오늘 + 1일(`setDate(getDate()+1)`)을 `fmtDateKR` 로 날짜 칸에. 처음 그릴 때와 `fresh()` 에서 부른다.
  - `buildText()`: 첫 줄 `[푸드벨 일일 일정표]`, 둘째 줄 `dayText()`, 전달 메모 있으면 `전달 메모: …`, 빈 줄, 채운 줄마다
    `N. 시간 장소 — 행사 내용` 과 그 아래 `   담당 … · 차량 … / 집합 … … / 메모 …`(빈 조각은 뺌). 빈 줄은 건너뜀.
  - 보내기 · 파일로 저장: 채운 줄이 0 이면 `confirm("일정을 아직 안 넣으셨습니다. 그래도 보낼까요?")`(저장은 "저장할까요?").
    공유 제목 `"푸드벨 일일 일정표 (" + dayText() + ")"`, 안내 문구의 "알바비 지급내역서" → "일일 일정표", "직원과의" → "단톡방".
  - `FoodbellDoc.kind = "daily-schedule"`, `summary()` = Interfaces 의 모양.
  - `input` 처리에서 날짜 칸이 바뀌어도 `recalc()` 가 요일을 바로 고친다(지금 코드가 모든 입력에 `recalc()` 를 부름 — 그대로).

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tools/sije_web/tests/test_doc_pages.py -q -k daily` → PASS (공통 9개 + 일정표 4개).
Run: `python -m pytest tools/sije_web/tests/test_doc_pages.py -q` → 전체 PASS(다른 서류 안 깨짐).

- [ ] **Step 5: 저장** — `git pull --ff-only` → `daily-schedule.html` · 시험 파일 add → commit `일일 일정표 2: 화면` → push.

---

### Task 3: 오프라인 사본 · 휴대폰 앱 · 아이콘 · 바탕화면

**Files:**
- Modify: `sw.js:3` (`CACHE` v34 → v35), `sw.js:15-16` (`OFFLINE_PAGES` 끝에 `'daily-schedule.html'`)
- Create: `manifest-daily.webmanifest`, `icons/app-daily-{180,192,512,maskable-512}.png`, `아이콘-일정표.ico`
- Modify: `바탕화면-바로가기.ps1` (머리 주석 3 · 4줄, 알바비 아래 한 줄), `휴대폰캡처.py:39-40` (`PAGES`)
- Test: `tools/sije_web/js-tests/sw.test.mjs`

**Interfaces:**
- Consumes: Task 2 의 `daily-schedule.html`(manifest · 아이콘 경로를 이미 가리킴).

- [ ] **Step 1: 실패하는 시험** — `sw.test.mjs` 의 `'캐시 번호를 올려도 서류 화면 · js/docs · docs.css 사본은 남는다'` 두 목록에 `'daily-schedule.html'` 추가.
- [ ] **Step 2: 실패 확인** — `node --test "tools/sije_web/js-tests/sw.test.mjs"` → FAIL(`daily-schedule.html`).
- [ ] **Step 3: `sw.js` 고침** — `OFFLINE_PAGES` 에 더하고 `CACHE = 'foodbell-v35'`. `python 캐시버전올리기.py --check` 로 index 쪽 경고가 없는지 본다(index · css/js 는 안 바꿈).
- [ ] **Step 4: 통과 확인** — `node --test "tools/sije_web/js-tests/*.test.mjs"` → 전체 PASS.
- [ ] **Step 5: manifest** — `manifest-pay.webmanifest` 복사, 이름 `푸드벨 일일 일정표` · 짧은 이름 `일정표` · `id`/`start_url`/`scope` = `./daily-schedule.html` · 아이콘 `icons/app-daily-*`.
- [ ] **Step 6: 아이콘 그리기 (일회용 스크립트는 작업 폴더 밖 — 세션 scratchpad)**
  1. 글꼴: Gowun Batang Bold(OFL)를 scratchpad 의 빈 폴더에 받는다 — `https://github.com/google/fonts/raw/main/ofl/gowunbatang/GowunBatang-Bold.ttf`.
  2. `icons/app-pay-512.png` 를 픽셀로 재서(금색 테두리 위치 · 두께, 큰 글자 · 작은 글자 크기와 세로 위치, 가운데 금줄) 같은 값으로 그리는 Pillow 스크립트를 쓴다.
     **먼저 알바비 아이콘을 다시 그려 원본과 비교**한다(같은 크기에서 픽셀 평균 차이가 작아야 함 — 다르면 측정부터 고친다).
  3. 맞으면 바탕색만 주홍 `#C4502A`, 큰 글자 `일정표` · 작은 글자 `일일` 로 180 · 192 · 512 · maskable-512(알바비 maskable 처럼 안쪽 테두리)를 만들고,
     같은 그림으로 `아이콘-일정표.ico`(16 · 24 · 32 · 48 · 64 · 128 · 256).
  4. **사장님께 512 그림을 보여 드리고 색 · 글자 확인** — 바꾸라면 3 을 다시.
- [ ] **Step 7: 바탕화면 · 캡처 목록** — `바탕화면-바로가기.ps1`: 주석 목록에 `/ 푸드벨 일정표`, 색 목록에 `/ 일정표=주홍`, 알바비 아래에
  `New-UrlLink '푸드벨 일정표' "$site/daily-schedule.html" '일일 일정표 - 날짜별 직원 일정 · 직원에게 보내기 (내부용)' '아이콘-일정표.ico'`.
  파일 첫 3바이트가 `EF BB BF`(BOM)로 남았는지 `head -c3 바탕화면-바로가기.ps1 | od -An -tx1` 로 확인. `휴대폰캡처.py` `PAGES` 에 `"daily-schedule.html"`.
- [ ] **Step 8: 저장** — `git pull --ff-only` → add → commit `일일 일정표 3: 오프라인 · 휴대폰 앱 · 아이콘` → push.

---

### Task 4: 문서 · 휴대폰 폭 확인 · 실제 게시 확인

**Files:**
- Modify: `CLAUDE.md` (파일 목록 `staff-pay.html` 블록 아래 `daily-schedule.html` 줄, 아이콘 색 목록에 `일일 일정표=주홍(#C4502A)` — Task 3 에서 바뀐 색이 있으면 그 값)

- [ ] **Step 1: CLAUDE.md** — 파일 목록에 두 줄:
  `daily-schedule.html   직원용 일일 일정표 (2026-10-19). 사장님이 저녁에 다음 날 일정을 직접 채워 카톡 단톡방에 사진으로(직원에게 보내기).`
  `                      맨 위 날짜(요일 저절로) · 전달 메모 · 한 줄 = 일 하나(시간·장소 / 행사 내용 / 담당·차량 / 집합 / 메모). 설계 docs/superpowers/specs/2026-10-19-daily-schedule-design.md`
- [ ] **Step 2: 휴대폰 폭** — `python 휴대폰캡처.py` → 일정표 줄의 되읽은 폭 `390`, 넘침 `0`. 사진(임시 폴더)을 열어 눈으로 확인하고 사장님께 보여 드린다.
- [ ] **Step 3: 전체 시험** — `node --test "tools/sije_web/js-tests/*.test.mjs"` 와 `python -m pytest tools/sije_web/tests/test_doc_pages.py tools/sije_web/tests/test_backup.py tools/sije_web/tests/test_rules_live.py -q` → 모두 PASS.
- [ ] **Step 4: 실제 규칙 확인** — Task 1 Step 5 를 아직 못 했으면 지금 사장님께 묻고 올린다.
- [ ] **Step 5: 저장 · 게시 확인** — `git pull --ff-only` → add → commit `일일 일정표 4: 문서` → push.
  1~2분 뒤 `curl -s -o /dev/null -w "%{http_code}" https://foodbell.kr/daily-schedule.html` → `200`.
- [ ] **Step 6: 사장님께 남길 것** — ① 휴대폰에서 실제로 단톡방에 보내 보기(사장님 몫) ② 바탕화면 아이콘은 PC 마다 `바탕화면-바로가기.bat` 한 번
  ③ 사무실 PC 에서 예약 작업 "푸드벨 시제 PDF" 껐다 켜기(백업에 "일일 일정표" 이름 — 급하지 않음).
