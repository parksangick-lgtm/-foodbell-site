# 일일 일정표 검토 반영 — 작업 계획 (2026-10-24)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. `superpowers-extras` 스킬을 같이 적용한다.

**Goal:** 직원 사진을 휴대폰 카드 모양으로 바꾸고, 출발 · 지도 링크 칸과 홈 화면 아이콘을 더해, 10-24 검토의 부족한 점 15개 중 사장님이 고르지 않은 1개(금액 · 링크)를 뺀 14개를 전부 반영한다.

**Architecture:** 카드 줄을 만드는 순수 함수(`js/docs/cards.js`)와 오전 · 오후 판정(`js/docs/time-hint.js`)을 작은 모듈로 떼어 Node 시험을 붙이고, `daily-schedule.html` 은 그 함수로 화면 밖 카드 묶음을 그려 html2canvas 로 장마다 찍는다. 직원 화면(`today.html`)은 게시판 칸 두 개(`leave` · `map`)를 더 읽고, 링크 속 암호를 브라우저 저장소에 기억해 홈 화면 아이콘으로 열린다. 보안 규칙 · 공통 부품(`doc-page.js`)은 건드리지 않는다.

**Tech Stack:** 정적 HTML/CSS/JS(빌드 없음), 파이어베이스(시험 프로젝트), html2canvas 1.4.1, node --test, pytest + Playwright, Pillow(아이콘).

**Spec:** `docs/superpowers/specs/2026-10-24-daily-schedule-review-fixes-design.md` — 절 번호는 아래에서 "설계 2절" 식으로 가리킨다.

## Global Constraints

- 모든 글 · 안내 · 주석은 한국어, 쉬운 말. 이 저장소는 **답이 끝날 때 자동 저장**(commit + push)된다 — 과제마다 커밋하지 않고 **바꾼 파일 목록**을 기록장(`.superpowers/sdd/2026-10-24-daily-schedule-review-fixes/progress.md`)에 남긴다. 답을 끝낼 때 파일이 반쯤 고친 상태면 그대로 올라간다.
- 사진에 찍히는 카드에는 `font-variant-numeric: tabular-nums` 와 `::before` · `::after` 이름표를 쓰지 않는다(설계 12절 — 숫자 틈 · 사본에 박힘).
- 카드 묶음: 폭 540 CSS px, `html2canvas(..., { windowWidth: 540, scale: 2 })`, 한 장 = 540 × 960(9:16). 글자 17px, 이름표 14px. 카드 하나는 두 장에 안 갈린다(`pageGroups`).
- 사진 아래 두 줄(장마다): `전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요` · `확인했으면 사진을 길게 눌러 👍 해 주세요`.
- 보냄 표시: `MM-DD HH:mm 보냄 · N차`, 한 번도 안 보냈으면 `MM-DD HH:mm 만듦`. 차수는 문서면 안 숨은 칸 `[data-k="sent"]`(저장 HTML 에 포함). 공유창 취소(`AbortError`)는 안 센다.
- 새 칸 이름: 출발 `data-f="leave"`(담당 직원 · 차량 칸 맨 아래), 지도 링크 `data-f="map"`(장소 아래, 편집 중에만 보임). 게시판 한 장 `rows[]` 칸 이름 `leave` · `map`.
- 지도 링크는 `^https?://` 로 시작할 때만 쓴다. 아니면 검색(`https://m.map.naver.com/search2/search.naver?query=`).
- 전화 칸(`tel` · `lead-tel` · `guide-tel`)은 `inputmode="tel"`. 연락처 흐린 글자 `연락처 (예: 상주 010-… / 자녀 010-…)`.
- 서류 화면 시험(pytest)은 시험 열쇠(`C:\foodbell-keys\sije-test-admin.json`)가 있는 **노트북 · 사무실 PC** 에서만 돈다. Node 시험은 어디서나.
- 보기 · 사진 · 인쇄 · 직원 화면 · 복사 글에 나가면 안 되는 것: "단위를 적어 주세요", "오전? 오후?", 사장님 한 줄(`.day-stats`), 지도 링크 글자.
- css/js 를 고치면 그 파일을 부르는 화면의 `?v=` 를 올린다(새 `cards.js?v=1` · `time-hint.js?v=1`). `sw.js` 는 `CACHE = 'foodbell-v37'`.
- 시험 자료는 전부 가짜(`가짜동` · `010-0000-0000` 꼴). 손님 정보 없음.
- 시험 명령: Node `node --test tools/sije_web/js-tests/` · 파이썬 `python -m pytest tools/sije_web/tests/test_doc_pages.py -k daily -q` 와 `python -m pytest tools/sije_web/tests/test_today_page.py -q`(둘 다 `c:\galleypark` 에서). 사진 시험은 PC 폭과 휴대폰 폭 둘 다(기존 `test_daily_fifteen_rows_split_into_pages` 방식).

## Review Focus

1. 메모가 아주 길어(붙여넣은 주문 글 40줄) 카드 하나가 한 장(960)보다 클 때 — 그 카드 혼자 한 장, 잘리지 않고 그 장만 길어진다 → Task 6 `test_daily_tall_card_gets_own_page`.
2. 지도 링크 칸에 `naver.me/abc` 처럼 `http` 없이 적거나 공백이 들어갈 때 — 무시하고 검색으로 → Task 2 · 3 의 `map` 시험에 `'naver.me/abc'` 사례.
3. 시간이 `13:30` · `오후 1시` · `정오` 이면 안 묻고 `12시` · `11시20분` 이면 묻는다 → Task 1 `needsAmPm` 시험.
4. 공유창을 취소했을 때 차수가 안 오르고, 다시 보내면 같은 차수로 찍힌다 → Task 6 `test_daily_cancelled_send_keeps_count`.
5. 아이콘으로 열었는데(`#` 없음) 그 브라우저에 암호가 없을 때(처음 · 저장소 지워짐) — "링크가 바뀌었습니다" 글 → Task 7 `test_today_no_hash_without_saved_key`.
6. 금액 합계에 곱셈 줄 · 단가만 줄 · 빠진 줄이 섞였을 때 — 합계는 앞 둘만, 빠진 줄 수는 따로 → Task 5 `test_daily_stats_line`.

---

### Task 1: 순수 함수 — 카드 줄 · 보냄 표시 · 오전/오후 판정

**Files:**
- Create: `js/docs/cards.js`, `js/docs/time-hint.js`
- Test: `tools/sije_web/js-tests/cards.test.mjs`, `tools/sije_web/js-tests/time-hint.test.mjs`

**Interfaces:**
- Produces (`cards.js`):
  - `export const STAFF_NOTE = "전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요"`, `export const STAFF_LIKE = '확인했으면 사진을 길게 눌러 👍 해 주세요'`, `export const SHOT_W = 540`, `export const SHOT_H = 960`.
  - `export function cardLines(row)` — `row` 는 게시판 한 장의 줄(`{ no, staff, car, leave, time, place, tel, work, amt, lead, leadTel, guideTel, hall, depart, cremate, memo }`, 빈 칸은 `''`). 돌려주는 것: `[{ lab, text }]`. 첫 줄은 머리(`lab: ''`, `text: '1번 · 오전 10:30 도착 · 김○○ · 1톤'` — 번호, 시간, 담당 · 차량을 ` · ` 로, 빈 것은 뺌). 그다음 순서대로 `출발` · `장소` · `연락처` · `행사` · `금액` · `팀장`(이름 + 전화를 공백으로) · `안내` · `장례`(장례식장 · `발인 …` · `화장 …` 을 ` · ` 로) · `메모`(줄바꿈 그대로). 값이 빈 줄은 넣지 않는다.
  - `export function stampText(sent, when)` — `sent`(정수) · `when`(Date). `sent > 0` → `'10-24 19:32 보냄 · 2차'`, 아니면 `'10-24 19:32 만듦'`. 월 · 일 · 시 · 분은 두 자리.
- Produces (`time-hint.js`): `export function needsAmPm(text)` — `text` 에 `1~12` 뒤에 `시` 또는 `:분` 이 오는 시각이 있고, `오전 · 오후 · 새벽 · 아침 · 낮 · 저녁 · 밤 · 정오 · AM · PM`(대소문자 무관)이 없으면 `true`. `13` 이상만 있으면 `false`. 빈 글자 `false`.

- [ ] **Step 1: 실패하는 시험 쓰기** — `cards.test.mjs`(`paging.test.mjs` 와 같은 꼴, `node:test` + `assert/strict`):

```js
test('카드 줄 — 머리 · 출발 · 장소 · 연락처 · 행사 · 금액 · 팀장 · 안내 · 장례 · 메모 순, 빈 칸은 뺌', () => {
  const lines = cardLines({ no: 2, staff: '박○○', car: '스타렉스', leave: '06:30 가게', time: '11시20분', place: '가짜추모공원',
    tel: '상주 010-0000-0003', work: '평토상', amt: '350,000원', lead: '가짜팀장', leadTel: '010-0000-0005', guideTel: '',
    hall: '가짜장례식장 3호실', depart: '오전 7시', cremate: '9시 30분', memo: '첫 줄\n둘째 줄', map: 'https://naver.me/x' });
  assert.deepEqual(lines, [
    { lab: '', text: '2번 · 11시20분 · 박○○ · 스타렉스' }, { lab: '출발', text: '06:30 가게' }, { lab: '장소', text: '가짜추모공원' },
    { lab: '연락처', text: '상주 010-0000-0003' }, { lab: '행사', text: '평토상' }, { lab: '금액', text: '350,000원' },
    { lab: '팀장', text: '가짜팀장 010-0000-0005' }, { lab: '장례', text: '가짜장례식장 3호실 · 발인 오전 7시 · 화장 9시 30분' },
    { lab: '메모', text: '첫 줄\n둘째 줄' }]);
});
test('빈 줄은 머리(번호)만', () => { assert.deepEqual(cardLines({ no: 4 }), [{ lab: '', text: '4번' }]); });
test('보냄 표시', () => {
  const d = new Date(2026, 9, 24, 19, 32);
  assert.equal(stampText(0, d), '10-24 19:32 만듦');
  assert.equal(stampText(2, d), '10-24 19:32 보냄 · 2차');
  assert.equal(stampText(1, new Date(2026, 0, 3, 7, 5)), '01-03 07:05 보냄 · 1차');
});
```

`time-hint.test.mjs`:

```js
for (const t of ['11시20분', '12시', '3시 도착', '11:20']) test(`묻는다: ${t}`, () => assert.equal(needsAmPm(t), true));
for (const t of ['13:30', '오후 1시', '정오', '새벽 5시', '11시 am', '오전 11시', '', '15시 도착', '2026년 10월 25일']) test(`안 묻는다: ${t}`, () => assert.equal(needsAmPm(t), false));
```

- [ ] **Step 2: 실패 확인** — `node --test tools/sije_web/js-tests/cards.test.mjs tools/sije_web/js-tests/time-hint.test.mjs` → 모듈 없음으로 실패.
- [ ] **Step 3: 구현** — `cards.js` 의 `cardLines` · `stampText` · 상수, `time-hint.js` 의 `needsAmPm`. 머리 주석에 "일일 일정표 사진(카드) · 직원 화면과 같은 줄 순서 (설계 2026-10-24)".
- [ ] **Step 4: 통과 확인** — 같은 명령, 전부 통과. `node --test tools/sije_web/js-tests/` 도 전부 통과.
- [ ] **Step 5: 기록** — 기록장에 바꾼 파일 4개.

### Task 2: 일정표 칸 — 출발 · 지도 링크 · 숫자 자판 · 연락처 예시 · 게시판 · 복사 글

**Files:**
- Modify: `daily-schedule.html` (표 머리줄 · `tr.item` 칸 · `FIELDS` · `placesLinked` · `buildText` · `share()` · 보기 CSS)
- Test: `tools/sije_web/tests/test_doc_pages.py` (일정표 절)

**Interfaces:**
- Consumes: 없음(Task 1 과 무관).
- Produces: 게시판 한 장 `rows[i].leave` · `rows[i].map`(글자 그대로, 빈 칸 `''`). 복사 글 한 일: `1. 시간 장소 연락처 — 행사 금액 / 담당 · 차량 / 출발 06:30 가게 / 팀장 … / 메모한줄`; 메모가 여러 줄이면 `/ 메모` 대신 다음 줄부터 세 칸 들여 한 줄씩. `window.FoodbellDoc.rowsData()` — `share()` 가 쓰는 줄 목록을 그대로 돌려주는 함수(채운 줄만, 번호 포함) — Task 6 의 카드가 쓴다.

- [ ] **Step 1: 실패하는 시험** — `test_daily_leave_and_map_fields`:

```python
def test_daily_leave_and_map_fields(pc, repo_url, custom_token, test_db, made, share_key):
    """출발 · 지도 링크 칸 — 보기에서 출발이 보이고, 게시판 한 장에 leave · map 이 들어가며, 지도 링크가 있으면 장소 글자가 그 주소를 연다.
    http 없는 지도 링크는 무시(검색). 전화 칸은 숫자 자판."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert pc.get_attribute('tr.item [data-f="tel"]', 'inputmode') == 'tel'
    assert pc.get_attribute('tr.item [data-f="lead-tel"]', 'inputmode') == 'tel'
    assert '상주 010' in pc.get_attribute('tr.item [data-f="tel"]', 'data-ph')
    pc.click('#btn-edit')
    assert pc.locator('tr.item [data-f="map"]').is_visible()
    for f, t in [('staff', '가짜직원'), ('leave', '06:30 가게'), ('place', '가짜추모공원'), ('map', 'https://naver.me/abc'), ('work', '가짜 상차림')]:
        edit_cell(pc, f'tr.item [data-f="{f}"]', t)
    pc.click('tr.addrow button')
    for f, t in [('place', '가짜공원'), ('map', 'naver.me/abc'), ('work', '둘째')]:
        edit_cell(pc, f'tr.item:nth-child(2) [data-f="{f}"]', t)
    pc.click('#btn-edit')
    assert pc.locator('tr.item [data-f="map"]').first.is_hidden()
    assert pc.get_attribute('tr.item:nth-child(1) [data-f="place"] a', 'href') == 'https://naver.me/abc'
    assert pc.get_attribute('tr.item:nth-child(2) [data-f="place"] a', 'href').startswith('https://m.map.naver.com/search2/search.naver?query=')
    assert '06:30 가게' in pc.locator('tr.item:nth-child(1)').inner_text()
    snap = wait_db(test_db.collection('share').document(share_key), lambda s: doc_id in (s.to_dict() or {}).get('entries', {}))
    rows = snap.to_dict()['entries'][doc_id]['rows']
    assert (rows[0]['leave'], rows[0]['map'], rows[1]['leave'], rows[1]['map']) == ('06:30 가게', 'https://naver.me/abc', '', 'naver.me/abc')
```

`test_daily_copy_text_keeps_memo_lines`:

```python
def test_daily_copy_text_keeps_memo_lines(pc, repo_url, custom_token, made):
    pc.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜 상차림')
    edit_cell(pc, 'tr.item [data-f="leave"]', '06:30 가게')
    pc.evaluate("""() => { const m = document.querySelector('tr.item [data-f="memo"]'); m.textContent = '첫 줄\\n둘째 줄'; m.dispatchEvent(new Event('input', { bubbles: true })); }""")
    pc.click('#btn-edit'); pc.click('#btn-copy')
    pc.locator('#btn-copy', has_text='복사됨').wait_for(timeout=5_000)
    lines = pc.evaluate('navigator.clipboard.readText()').strip().splitlines()
    i = next(n for n, l in enumerate(lines) if l.startswith('1. '))
    assert lines[i] == '1. 가짜 상차림 / 출발 06:30 가게' and lines[i + 1] == '   첫 줄' and lines[i + 2] == '   둘째 줄'
```

(`share_key` 픽스처는 기존 `test_daily_board_gets_filled_rows` 가 쓰는 것을 그대로 쓴다.)

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_doc_pages.py -k "leave_and_map or keeps_memo_lines" -q` → 실패(속성 없음 · 칸 없음).
- [ ] **Step 3: 구현** — (a) 표 머리줄 `담당 직원 · 차량 · 출발`; `td.crew` 에 `<span class="sub" data-edit data-t="text" data-f="leave" data-ph="출발 (예: 06:30 가게)">`; `td.when` 의 장소 아래 `<span class="sub maplink" data-edit data-t="text" data-f="map" data-ph="지도 링크 (선택 — 네이버 지도 공유)">` + CSS `body:not(.editing) .maplink{display:none}` · `@media print{.maplink{display:none}}`; 전화 칸 셋에 `inputmode="tel"`; 연락처 `data-ph` 교체. (b) `FIELDS` 에 `'leave'` · `'map'`. (c) `placesLinked()`: 같은 줄 `[data-f="map"]` 글자가 `/^https?:\/\//` 이면 그 주소, 아니면 검색. (d) `rowsData()` 를 `share()` 에서 떼어 내 `window.FoodbellDoc.rowsData` 로 내주고 줄 객체에 `leave` · `map` 추가; `share()` 는 `rowsData()` 를 쓴다. (e) `buildText()`: `crew` 다음에 `field(tr,'leave') ? '출발 ' + …` 조각; 메모가 줄바꿈을 품으면 `/ 메모` 대신 다음 줄들에 `'   ' + 줄`. 휴대폰 카드(620px 이하)에서 `leave` 는 `td.crew` 안이라 저절로 보인다.
- [ ] **Step 4: 통과 확인** — 위 두 시험 통과 + `python -m pytest tools/sije_web/tests/test_doc_pages.py -k daily -q` 전부 통과(`test_daily_copy_text_ends_with_site_url` · `test_daily_board_gets_filled_rows` 가 그대로 통과하는지 특히).
- [ ] **Step 5: 기록** — 바꾼 파일 2개.

### Task 3: 직원 화면 — 출발 줄 · 지도 링크

**Files:**
- Modify: `today.html` (`card()`)
- Test: `tools/sije_web/tests/test_today_page.py`

**Interfaces:**
- Consumes: 게시판 줄의 `leave` · `map`(Task 2).

- [ ] **Step 1: 실패하는 시험** — `FIELDS` 에 `'leave', 'map'` 추가하고:

```python
def test_today_leave_line_and_map_link(phone, repo_url, test_db, key):
    """출발 줄은 머리 다음에, [지도]는 지도 링크가 http(s) 면 그 주소 · 아니면 검색."""
    put(test_db, key, docA=entry(day(0), [
        row(1, time='06:30', place='가짜추모공원', leave='05:30 가게', map='https://naver.me/abc', work='가짜 상차림'),
        row(2, place='가짜공원', map='naver.me/abc', work='둘째'),
        row(3, place='가짜납골당', work='셋째')]))
    open_today(phone, repo_url, f'#{key}')
    c = cards(phone)
    lines = [l.strip() for l in c.nth(0).locator('p.line').all_inner_texts()]
    assert lines[0].startswith('출발') and '05:30 가게' in lines[0]
    assert hrefs(phone, 'a.btn-map') == ['https://naver.me/abc', naver('가짜공원'), naver('가짜납골당')]
    assert '출발' not in c.nth(1).inner_text()
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_today_page.py -k leave_line -q` → 실패.
- [ ] **Step 3: 구현** — `card()`: 머리 다음 `if (r.leave) line(c, '출발', r.leave);`; 지도 주소 `const mapHref = /^https?:\/\//.test(r.map || '') ? r.map : NAVER + encodeURIComponent(r.place)` (`NAVER` 상수로 뽑음). 머리 주석에 두 칸 한 줄.
- [ ] **Step 4: 통과 확인** — `python -m pytest tools/sije_web/tests/test_today_page.py -q` 전부 통과.
- [ ] **Step 5: 기록** — 바꾼 파일 2개.

### Task 4: 편집 — 장례 칸 접기 · 오전/오후 물음

**Files:**
- Modify: `daily-schedule.html` (`addControls` · `removeControls` · `serialize` · `focusout`/`input` 처리 · CSS), `<script type="module">` import 줄에 `time-hint.js?v=1`
- Test: `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Consumes: `needsAmPm(text)`(Task 1).
- Produces: 편집 중 `td.meet.folded` + 그 안 `button.btn-mini.btn-open`(글자 `장례 칸 펼치기`); 시간 칸 `[data-f="time"][data-ampm]` 에 CSS `::after` 로 ` 오전? 오후?` — 이 `::after` 는 **편집 화면에만**(사진은 Task 6 부터 별도 카드라 안 찍힘, 인쇄 `content:none`).

- [ ] **Step 1: 실패하는 시험**

```python
def test_daily_funeral_cells_fold_until_opened(pc, repo_url, custom_token, test_db, made):
    """편집 중 장례 여섯 칸이 모두 비면 '장례 칸 펼치기' 단추만, 누르면 펼쳐지고 첫 칸에 커서. 하나라도 적혀 있으면 늘 펼쳐짐. 저장 HTML 에는 접힘 표시가 없다."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    meet = pc.locator('tr.item td.meet')
    assert meet.locator('button.btn-open').is_visible() and meet.locator('[data-f="lead"]').is_hidden()
    meet.locator('button.btn-open').click()
    assert meet.locator('[data-f="lead"]').is_visible() and pc.evaluate("document.activeElement?.dataset.f") == 'lead'
    assert meet.locator('button.btn-open').count() == 0
    edit_cell(pc, 'tr.item [data-f="hall"]', '가짜장례식장')
    pc.click('#btn-edit'); pc.click('#btn-edit')                       # 다시 편집: 적힌 줄은 펼쳐져 있다
    assert meet.locator('button.btn-open').count() == 0 and meet.locator('[data-f="lead"]').is_visible()
    pc.click('tr.addrow button')                                        # 새 줄은 접혀 있다
    assert pc.locator('tr.item:nth-child(2) td.meet button.btn-open').is_visible()
    pc.click('#btn-edit')
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: '가짜장례식장' in (s.to_dict() or {}).get('html', '')).to_dict()['html']
    assert 'folded' not in html and 'btn-open' not in html

def test_daily_time_without_ampm_gets_hint(pc, repo_url, custom_token, test_db, made):
    """'11시20분' 은 편집 중 '오전? 오후?' 가 붙고, '오후 1시' · '13:30' 은 안 붙는다. 보기 · 저장 HTML 에는 없다."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    t = pc.locator('tr.item [data-f="time"]')
    edit_cell(pc, 'tr.item [data-f="time"]', '11시20분')
    assert t.get_attribute('data-ampm') is not None
    assert '오전? 오후?' in pc.evaluate("getComputedStyle(document.querySelector('tr.item [data-f=\"time\"]'), '::after').content")
    for v in ('오후 1시', '13:30'):
        edit_cell(pc, 'tr.item [data-f="time"]', v)
        assert t.get_attribute('data-ampm') is None, v
    edit_cell(pc, 'tr.item [data-f="time"]', '12시')
    pc.click('#btn-edit')
    assert '오전? 오후?' not in pc.locator('.sheet').inner_text()
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: '12시' in (s.to_dict() or {}).get('html', '')).to_dict()['html']
    assert 'data-ampm' not in html
```

- [ ] **Step 2: 실패 확인** — `-k "fold_until or ampm"` → 실패.
- [ ] **Step 3: 구현** — (a) `addControls()`: `tr.item` 마다 `td.meet` 의 여섯 칸(`lead` · `lead-tel` · `guide-tel` · `hall` · `depart` · `cremate`)이 전부 비면 `td.meet.classList.add('folded')` + `button.btn-mini.btn-open` 추가(이미 있으면 생략). 클릭(기존 `sheet` click 위임에 가지 추가): `folded` 떼고 단추 지우고 `[data-f="lead"]` 에 `focus()`. CSS `body.editing td.meet.folded > :not(.btn-open){display:none}`. `removeControls()` 가 `.btn-open` 도 지우고 `folded` 도 뗀다. `serialize()` 도 `folded` · `.btn-open` 을 뗀다. (b) 시간 칸: `input` · `focusout` 처리에서 `[data-f="time"]` 이면 `needsAmPm(text) ? t.setAttribute('data-ampm','') : t.removeAttribute('data-ampm')`; `setEditing(true)` 때 모든 시간 칸에 한 번 적용, `setEditing(false)` · `serialize()` 때 속성 제거. CSS `body.editing [data-f="time"][data-ampm]::after{content:" 오전? 오후?"; color:var(--ink-mute); font-size:.85em; font-weight:var(--w-normal)}` + `@media print{…{content:none}}`.
- [ ] **Step 4: 통과 확인** — 두 시험 + `-k daily` 전부 통과(`test_daily_funeral_hall_and_times` · `test_daily_paste_fills_funeral_times` 가 접힌 칸 때문에 깨지면, 그 시험들이 `edit_cell` 전에 단추를 누르도록 고친다 — 사람도 그렇게 한다).
- [ ] **Step 5: 기록**.

### Task 5: 보내기 전 확인 · 사장님 한 줄

**Files:**
- Modify: `daily-schedule.html` (`recalc` · `btn-send` 처리 · `.day` 아래 `.day-stats` · CSS)
- Test: `tools/sije_web/tests/test_doc_pages.py`

**Interfaces:**
- Produces: `recalc()` 가 `{ count, sum, missing }` 을 계산해 `.day-stats` 에 `N건 · 금액 합계 X원` (+ ` · 금액 빠진 줄 M`), 0건이면 빈 글자(숨김). `.day-stats` 는 `data-k` 없음(저장 HTML 에는 들어가지만 그릴 때마다 덮어씀), `html.shot` · 인쇄 · 카드에 없음. 보내기 확인 글: `${nos.join(' · ')}번 줄 금액이 비어 있습니다(단위 없음). 그래도 보낼까요?`

- [ ] **Step 1: 실패하는 시험**

```python
def test_daily_send_asks_when_amount_missing(pc, repo_url, custom_token, made):
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜 상차림'); edit_cell(pc, 'tr.item [data-f="price"]', '250')
    pc.click('#btn-edit')
    asked = []
    pc.once('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    pc.click('#btn-send')
    pc.wait_for_timeout(800)
    assert asked == ['1번 줄 금액이 비어 있습니다(단위 없음). 그래도 보낼까요?']
    assert pc.locator('#btn-send').inner_text() == '직원에게 보내기' and pc.locator('#btn-send').is_enabled()

def test_daily_stats_line(pc, repo_url, custom_token, made):
    """곱셈 줄 + 단가만 줄 + 단위 없는 줄 → '3건 · 금액 합계 1,250,000원 · 금액 빠진 줄 1'. 0건이면 숨김. 사진 · 인쇄엔 없음."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert pc.locator('.day-stats').is_hidden()
    pc.click('#btn-edit')
    for _ in range(2): pc.click('tr.addrow button')
    pc.evaluate("""() => {
        const v = [{ work: '시제', people: '60명', price: '15,000원' }, { work: '평토상', price: '35만' }, { work: '배달', price: '250' }];
        document.querySelectorAll('tr.item').forEach((tr, i) => { for (const [f, t] of Object.entries(v[i])) tr.querySelector(`[data-f="${f}"]`).textContent = t; });
        document.querySelector('tr.item [data-f="work"]').dispatchEvent(new Event('input', { bubbles: true }));
    }""")
    pc.click('#btn-edit')
    assert pc.locator('.day-stats').inner_text() == '3건 · 금액 합계 1,250,000원 · 금액 빠진 줄 1'
    pc.emulate_media(media='print')
    assert pc.locator('.day-stats').is_hidden()
```

- [ ] **Step 2: 실패 확인** — `-k "send_asks or stats_line"` → 실패.
- [ ] **Step 3: 구현** — `recalc()` 가 줄마다 금액 숫자(`people*price` 또는 `price`)를 더하고 `bare` 줄을 센다; `<p class="day-stats" aria-live="polite"></p>` 를 `.day` 바로 아래에; CSS `.day-stats{font-size:14.5px;color:var(--ink-mute);margin:-.3rem 0 .6rem} .day-stats:empty{display:none} @media print{.day-stats{display:none}}` (사진은 Task 6 부터 별도 카드라 들어가지 않는다). `btn-send` 처리 맨 앞(기존 "일정을 아직 안 넣으셨습니다" 다음)에 `warn` 줄 번호를 모아 `window.confirm`, 아니오면 `return`.
- [ ] **Step 4: 통과 확인** — `-k daily` 전부.
- [ ] **Step 5: 기록**.

### Task 6: 직원 사진 = 휴대폰 카드 · 보냄 N차 · 아래 문구

**Files:**
- Modify: `daily-schedule.html` (`renderImage` · `renderPages` · `btn-send` · `btn-save-file` · `.day` 아래 `[data-k="sent"]` · 카드 CSS), import `cards.js?v=1` · `paging.js` 그대로
- Modify: `tools/sije_web/tests/test_doc_pages.py` (`save_pages` · `STAFF_NOTE` · `test_daily_fifteen_rows_split_into_pages` · `test_daily_photo_ends_with_staff_note` · `test_daily_files_are_named_by_date` 는 그대로)

**Interfaces:**
- Consumes: `cardLines` · `stampText` · `STAFF_NOTE` · `STAFF_LIKE` · `SHOT_W` · `SHOT_H`(Task 1), `rowsData()`(Task 2), `pageGroups`.
- Produces: 화면 밖 `<div class="shot-cards" aria-hidden="true">`(`position:absolute; left:-9999px; top:0; width:540px; background:#F7F2E9; padding:16px`): `.shot-head`(`.shot-title` "푸드벨 일일 일정표", `.shot-day` 큰 날짜 + `.lunar` + `.pageno`, `.shot-order`, `.shot-memo`, `.shot-stamp`), `article.card[data-no="N"]`(줄마다 `p.line > span.lab + span.txt`, 머리는 `p.head`), `.shot-foot`(`p` 두 개 = `STAFF_NOTE` · `STAFF_LIKE`). 첫 장만 `.shot-order` · `.shot-memo` · `.shot-stamp` · `.shot-title`; 다음 장은 `.shot-day`(+ `pageno`)만. `renderPages()` 는 지금처럼 `[{ blob, name }]`. 사진 폭 1080px.
- `save_pages`(시험 도우미)는 줄 번호를 `root.querySelectorAll('article.card:not([data-shot-hide])')` 의 `data-no` 에서 읽는다(`root = ref || doc.querySelector('.shot-cards')`).

- [ ] **Step 1: 시험 고치기 · 새 시험** — `STAFF_NOTE = "전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요"`. `test_daily_fifteen_rows_split_into_pages`: 단정을 `h / w <= 16 / 9 * 1.03` 로, 나머지(이름 `_1` `_2`, 번호 1~15 연속, 휴대폰 = PC 장 나눔) 그대로. `test_daily_photo_ends_with_staff_note`: 사본의 `.shot-cards` 마지막 두 자식 글자가 `[STAFF_NOTE, STAFF_LIKE]`. 새 시험:

```python
def test_daily_photo_is_phone_cards(pc, repo_url, custom_token, made, tmp_path):
    """사진은 카드 묶음 — 폭 1080, 상호 · QR · 인장 없음, 첫 장에 날짜 · 순번 · 전달 메모 · '만듦' 표시, 카드 줄 순서는 cards.js."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="order"]', '가짜1 · 가짜2')
    for f, t in [('staff', '가짜직원'), ('leave', '06:30 가게'), ('time', '오전 10:30'), ('place', '가짜추모공원'), ('tel', '010-0000-0001'), ('work', '가짜 상차림'), ('people', '60명'), ('price', '15,000원')]:
        edit_cell(pc, f'tr.item [data-f="{f}"]', t)
    pc.click('#btn-edit')
    pc.evaluate("""() => { window.__shotText = []; const o = window.html2canvas; window.html2canvas = (el, opt) => o(el, { ...opt, onclone: async (d, ref) => { if (opt.onclone) await opt.onclone(d, ref); window.__shotText.push((ref || d.querySelector('.shot-cards')).innerText); } }); }""")
    names, shots, sizes = save_pages(pc, tmp_path)
    assert len(names) == 1 and re.fullmatch(r'\d{4}-\d{2}-\d{2}\.png', names[0]), names   # 날짜는 내일 — 이름 형식만 본다
    assert sizes[0][0] == 1080 and sizes[0][1] / sizes[0][0] <= 16 / 9 * 1.03
    text = pc.evaluate('window.__shotText[0]')
    for s in ('푸드벨 일일 일정표', '순번: 가짜1 · 가짜2', '1번 · 오전 10:30 · 가짜직원', '출발', '06:30 가게', '60명 × 15,000원 = 900,000원', '만듦', STAFF_NOTE, STAFF_LIKE):
        assert s in text, s
    for s in ('foodbell.kr', '전통 제례', '010-5353-3477', '단위를 적어 주세요', '건 · 금액 합계'):
        assert s not in text, s

def test_daily_tall_card_gets_own_page(pc, repo_url, custom_token, made, tmp_path):
    """메모 40줄짜리 카드는 혼자 한 장(그 장만 9:16 보다 길어도 된다), 앞뒤 카드는 잘리지 않는다."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    for _ in range(2): pc.click('tr.addrow button')
    pc.evaluate("""() => { const trs = document.querySelectorAll('tr.item'); trs.forEach((tr, i) => { tr.querySelector('[data-f="work"]').textContent = '일 ' + (i + 1); });
        trs[1].querySelector('[data-f="memo"]').textContent = Array.from({ length: 40 }, (_, i) => '주문 글 ' + (i + 1)).join('\\n');
        trs[0].querySelector('[data-f="work"]').dispatchEvent(new Event('input', { bubbles: true })); }""")
    pc.click('#btn-edit')
    names, shots, sizes = save_pages(pc, tmp_path)
    assert shots == [[1], [2], [3]] and sizes[1][1] > sizes[0][1]

def test_daily_send_count_and_stamp(phone, repo_url, custom_token, test_db, made):
    """보내기(공유창)마다 차수가 오르고 사진에 '보냄 · N차'. 취소(AbortError)는 안 오른다."""
    doc_id = daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    phone.click('#btn-edit'); edit_cell(phone, 'tr.item [data-f="work"]', '가짜 상차림'); phone.click('#btn-edit')
    phone.evaluate("""() => { window.__stamps = []; const o = window.html2canvas; window.html2canvas = (el, opt) => o(el, { ...opt, onclone: async (d, ref) => { if (opt.onclone) await opt.onclone(d, ref); window.__stamps.push((ref || d.querySelector('.shot-cards')).querySelector('.shot-stamp')?.textContent); } });
        navigator.canShare = () => true; window.__shares = 0; navigator.share = () => { window.__shares++; return window.__shares === 1 ? Promise.reject(Object.assign(new Error('x'), { name: 'AbortError' })) : Promise.resolve(); }; }""")
    phone.click('#btn-send'); phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=30_000)
    phone.click('#btn-send'); phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=30_000)
    phone.click('#btn-send'); phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=30_000)
    stamps = phone.evaluate('window.__stamps')
    assert [s.split(' ', 1)[1] for s in stamps] == ['보냄 · 1차', '보냄 · 1차', '보냄 · 2차']
    sent = re.compile(r'data-k="sent"[^>]*>2<')
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: sent.search((s.to_dict() or {}).get('html', ''))).to_dict()['html']
    assert sent.search(html)
```

- [ ] **Step 2: 실패 확인** — `-k "fifteen_rows or ends_with_staff_note or phone_cards or tall_card or send_count"` → 실패.
- [ ] **Step 3: 구현** — (a) `.day` 아래 `<span data-k="sent" hidden>0</span>`; `sentCount()` = 숫자(없으면 0). (b) `buildCards(stamp)`: `rowsData()` 로 `.shot-cards` 를 새로 그려 `body` 끝에 붙인다(있으면 비우고 다시). 카드 CSS 는 `today.html` 의 `.card` · `.line` · `.lab` · `.txt` 값을 가져오되 `tabular-nums` · `::before` 없이. (c) `renderPages()`: `buildCards` → 카드 높이 재기(`article.card` `offsetHeight`), 첫 장 머리 높이 · 다음 장 머리 높이 · 바닥 높이를 재서 `pageGroups(heights, SHOT_H - head1 - foot, SHOT_H - headN - foot)` → 장마다 다른 장 카드와 첫 장 전용 부분에 `data-shot-hide` → `html2canvas(shotCards, { backgroundColor:'#F7F2E9', scale:2, windowWidth:SHOT_W, width:SHOT_W, useCORS:true, logging:false, onclone })`. 끝나면 `.shot-cards` 제거. `html.shot` 추가 · `::before` 끄기 줄은 뗀다(표를 안 찍으니). 파일 이름 규칙 그대로. (d) `btn-send`: 찍기 전 `stamp = stampText(sentCount() + 1, new Date())`; 공유 성공(`then`) · PC 복사 경로 성공에서 `setText('sent', String(sentCount() + 1)); save();` — `AbortError` 는 안 올림. `btn-save-file`: `stampText(sentCount(), new Date())`. (e) 표 사진용 코드(`pageOf` 의 표 줄 숨기기, `.staff-note` 붙이기, `firstOnly` 목록)는 지운다 — 더는 안 쓴다. `.staff-note` CSS 도 지운다.
- [ ] **Step 4: 통과 확인** — `-k daily` 전부(PC · 휴대폰 둘 다 도는 15줄 시험 포함). 사진 한 장을 `tmp_path` 에서 열어 **눈으로** 본다(카드가 잘리지 않았는지, 글자 틈 없는지) — 결과를 기록장에 적는다.
- [ ] **Step 5: 기록**.

### Task 7: 직원 화면 홈 화면 아이콘 — 앱 정보 · 아이콘 · 암호 기억 · 설치 안내

**Files:**
- Create: `manifest-today.webmanifest`, `icons/app-today-180.png` · `-192.png` · `-512.png` · `-maskable-512.png`
- Modify: `today.html` (`<head>` · 암호 읽기 · 맨 아래 `<details id="install">`), `sw.js` (`CACHE` v37)
- Test: `tools/sije_web/tests/test_today_page.py`

**Interfaces:**
- Produces: `localStorage['foodbell-today-key']`. `manifest-today.webmanifest` 는 `manifest-daily.webmanifest` 와 같은 꼴(`name` "푸드벨 일정", `short_name` "일정", `id` · `start_url` · `scope` `./today.html`, 아이콘 `icons/app-today-*`).

- [ ] **Step 1: 실패하는 시험**

```python
def test_today_remembers_key_for_home_icon(ctx, phone, repo_url, test_db, key):
    """링크(#암호)로 한 번 열면 같은 브라우저에서 # 없이 열어도(홈 화면 아이콘) 일정이 보인다. 다른 브라우저(새 문맥)는 안 보인다."""
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜 상차림')]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    open_today(phone, repo_url, '')
    assert cards(phone).count() == 1
    assert phone.evaluate("localStorage.getItem('foodbell-today-key')") == key

def test_today_no_hash_without_saved_key(phone, repo_url, test_db, key):
    open_today(phone, repo_url, '')
    phone.locator('#status', has_text=CHANGED).wait_for(timeout=10_000)

def test_today_has_manifest_icons_and_install_guide(phone, repo_url, test_db, key):
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜 상차림')]))
    open_today(phone, repo_url, f'#{key}'); cards(phone)
    assert phone.get_attribute('link[rel="manifest"]', 'href') == 'manifest-today.webmanifest'
    m = phone.request.get(f'{repo_url}manifest-today.webmanifest'); assert m.status == 200 and m.json()['name'] == '푸드벨 일정'
    for icon in m.json()['icons']:
        assert phone.request.get(f'{repo_url}{icon["src"]}').status == 200, icon
    guide = phone.locator('#install')
    assert guide.is_visible() and '홈 화면' in guide.inner_text() and '다른 브라우저로 열기' in guide.inner_text()
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_today_page.py -k "home_icon or without_saved_key or install_guide" -q` → 실패.
- [ ] **Step 3: 아이콘 만들기** — 임시 폴더의 파이썬(`python -X utf8`, Pillow): `icons/app-daily-512.png` 와 `app-daily-maskable-512.png` 를 열어 바탕색 `(196, 80, 42)` 와 거리 40 안의 픽셀을 `(46, 107, 79)`(`#2E6B4F`, 추정 — 사장님께 보여 드린 뒤 바꿀 수 있음)로 바꾼 뒤 저장; 512 에서 192 · 180 을 LANCZOS 로 줄인다. 확인: 새 파일 네 개의 가장 많은 색이 `(46,107,79,255)`, 크기 맞음. 512 를 사장님께 보여 드린다(Read 로 화면에).
- [ ] **Step 4: 구현** — `manifest-today.webmanifest`; `today.html` `<head>` 에 `<link rel="manifest" href="manifest-today.webmanifest">` · `<link rel="apple-touch-icon" href="icons/app-today-180.png">`; 암호: `const KEY_STORE = 'foodbell-today-key'; let key = location.hash.slice(1); if (/^[\w-]{8,64}$/.test(key)) { try { localStorage.setItem(KEY_STORE, key); } catch {} } else { try { key = localStorage.getItem(KEY_STORE) || ''; } catch { key = ''; } }` 뒤에 기존 `if (!/^[\w-]{8,64}$/.test(key)) gone(); else …`; `main` 끝에 `<details id="install"><summary>홈 화면에 아이콘으로 두기</summary><ol><li>카톡 안에서 열렸으면 오른쪽 위 ⋮ → <b>다른 브라우저로 열기</b>(크롬)</li><li>크롬 오른쪽 위 ⋮ → <b>홈 화면에 추가</b>(또는 앱 설치). 삼성 인터넷은 아래 ≡ → 현재 페이지 추가 → 홈 화면</li><li>다음부터는 홈 화면의 <b>푸드벨 일정</b>을 누르면 됩니다. "링크가 바뀌었습니다"가 뜨면 단톡방 공지 링크를 한 번 더 누르세요</li></ol></details>` + CSS(`summary` 44px, 글자 15px). `sw.js` `CACHE = 'foodbell-v37'`.
- [ ] **Step 5: 통과 확인** — `test_today_page.py` 전부 + `node --test tools/sije_web/js-tests/`(sw 시험) + `python -m pytest tools/sije_web/tests/test_offline.py -q`.
- [ ] **Step 6: 기록**.

### Task 8: 문서 · 안내문 · 올라갔는지 확인

**Files:**
- Modify: `CLAUDE.md`(파일 목록 `daily-schedule.html` · `today.html` 줄에 한 줄씩), `docs/superpowers/specs/2026-10-19-daily-schedule-design.md`(맨 위에 "10-24 검토 반영 설계서로 사진 모양 · 칸이 바뀜" 한 줄), `docs/superpowers/specs/2026-10-21-staff-today-link-design.md`(같은 한 줄)
- Create: `C:\dev\vibe-study\handoff\직원-홈화면-아이콘-안내문.md`(사장님이 단톡방에 올릴 글 — 저장소 밖 · 비공개)
- Modify: `C:\dev\vibe-study\handoff\진행중.md`(이 일의 줄: 남은 것 = 사장님 폰 보내기 · 직원 폰 아이콘 확인 · 안내문 올리기)

- [ ] **Step 1: 문서 고치기** — 위 파일들. 안내문(설계 3절): 세 줄 + "링크가 바뀌었습니다가 뜨면 이 글의 링크를 다시 누르세요" + 링크 자리(`[여기에 직원 링크 — python -m tools.sije_web.share_link show --key C:\foodbell-keys\sije-admin.json 으로 봄]`, 링크 자체는 적지 않는다).
- [ ] **Step 2: 전체 시험** — `node --test tools/sije_web/js-tests/` · `python -m pytest tools/sije_web/tests/test_doc_pages.py -q`(전부) · `python -m pytest tools/sije_web/tests/test_today_page.py tools/sije_web/tests/test_offline.py -q` → 전부 통과. `python 휴대폰캡처.py daily-schedule.html` → 폭 390 · 넘침 0.
- [ ] **Step 3: 기록 · 답 끝내기** — 기록장에 전체 바꾼 파일 목록과 시험 결과. (자동 저장으로 올라간 뒤) 다음 차례 첫 일로:
  `curl -s -o /dev/null -w "%{http_code}" https://foodbell.kr/today.html` · `…/manifest-today.webmanifest` · `…/icons/app-today-192.png` · `…/daily-schedule.html` → 전부 `200`, `curl -s https://foodbell.kr/today.html | grep -c manifest-today` → `1`, `curl -s https://foodbell.kr/sw.js | grep -o "foodbell-v[0-9]*"` → `foodbell-v37`.
- [ ] **Step 4: 사장님 몫(멈추는 자리)** — ① 사장님 폰에서 실제 일정표 하나로 "직원에게 보내기" → 단톡방 사진이 카드 모양 · "보냄 · N차" ② 직원 폰 한 대에서 설치 안내대로 아이콘 → 아이콘으로 열어 일정이 보이는지(설계 3절 가정) ③ 안내문 올리기. 결과를 들으면 기록장 · 진행중.md 에 적는다.
