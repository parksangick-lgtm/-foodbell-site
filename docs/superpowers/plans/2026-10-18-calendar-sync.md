# 시제행사 → 구글 캘린더 자동 맞추기 작업 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사무실 PC 상주 프로그램이 5분마다 시제행사(파이어베이스 `events`)를 "푸드벨 행사" 구글 캘린더에 맞춘다.

**Architecture:** 새 모듈 `tools/sije_web/calendar_sync.py` 하나에 ① 행사 → 일정 바꾸기(순수 함수) ② 맞추기(캘린더 부품을 받아 비교 · 만들기 · 고치기 · 지우기) ③ 구글 캘린더 부품(서비스 계정)을 둔다. `office_agent.one_cycle` 이 PDF · 백업 다음 세 번째 덩어리로 부른다.

**Tech Stack:** Python 3.14, firebase-admin 7.7.0 에 딸린 google-auth(`service_account`, `AuthorizedSession`), requests, pytest 9.1.1, gws 0.22.5(준비 단계만).

**Spec:** `docs/superpowers/specs/2026-10-18-calendar-sync-design.md`

## Global Constraints

- 새 꾸러미 설치 없음 — `requirements.txt` 를 바꾸지 않는다.
- 캘린더 ID 는 `C:\foodbell-keys\sije-calendar.txt`(실제) · `C:\foodbell-keys\sije-test-calendar.txt`(시험)에만. 저장소 · 코드 · 시험 파일에 적지 않는다.
- 시험은 시험 프로젝트(`KEY_TEST`) · 시험 캘린더만. 행사 자료는 `conftest.fake_event()`(가짜) — 손님 정보 금지.
- 시간대 `Asia/Seoul`. 시간 있는 일정 끝 = 시작 + 2시간. 종일 일정 끝 = 다음 날(구글 규칙).
- 미확정 `colorId` = `'8'`, 제목 앞 `[미확정] `. 확정은 `colorId` 없음.
- 범위(scope) `https://www.googleapis.com/auth/calendar.events`.
- 내역서 링크 `https://foodbell.kr/sije-sheet.html?id=<행사 번호>`.
- 숨은 꼬리표 `extendedProperties.private.foodbellId` = 행사 번호. 꼬리표 없는 일정은 읽지도 고치지도 않는다.
- `calendar_sync.py` 는 맨 위에서 `from tools.sije_web import fsdb` 를 먼저 불러 윈도우 인증서 설정이 requests 에 걸리게 한다.
- **커밋은 직접 하지 않는다** — 답이 끝날 때 자동 저장(훅)이 한다. 그래서 답을 끝낼 때마다 시험이 통과하는 상태여야 한다(반쯤 고친 채 끝내지 않기).
- 시험 실행: 파이썬 `python -m pytest tools/sije_web/tests/<파일> -q` (저장소 맨 위에서).

## Review Focus

1. **23시 이후 시작** — 끝(2시간 뒤)이 다음 날로 넘어가야 한다 → Task 2 `test_late_start_rolls_to_next_day`.
2. **행사 번호에 한글 · 기호** — 일정 ID 가 구글 규칙(소문자 a–v · 숫자)을 지켜야 한다 → Task 2 `test_event_id_is_base32hex_safe`.
3. **구글이 돌려주는 시간 모양이 우리 것과 다름**(`+09:00` 붙은 `dateTime`, `colorId` 없음 등) — 같은 일정을 "달라짐"으로 보면 5분마다 85개를 다시 고친다 → Task 3 `test_google_shaped_existing_counts_as_same`, Task 4 실제 구글로 두 번 맞추기.
4. **사장님이 캘린더에서 일정을 지움** — 다음 차례에 같은 번호로 만들다 409 → 되살려야 한다 → Task 4 `test_live_revive_after_delete`.
5. **저장소 읽기가 통째로 실패 · 0개** — 캘린더를 비우면 안 된다 → Task 3 `test_empty_source_deletes_nothing`, Task 5 `test_calendar_failure_does_not_stop_backup`.

---

### Task 1: 준비 — 캘린더 만들기 · 공유 · 캘린더 서비스 켜기 · 쓰기 시험 (코드 없음)

**Files:** 저장소 밖만. Create `C:\foodbell-keys\sije-calendar.txt`, `C:\foodbell-keys\sije-test-calendar.txt` (캘린더 ID 한 줄).

- [ ] **Step 1: 사장님 계정에 캘린더 두 개 만들기 (gws, 사장님 로그인)**

```bash
gws calendar calendars insert --json '{"summary": "푸드벨 행사", "timeZone": "Asia/Seoul"}'
gws calendar calendars insert --json '{"summary": "푸드벨 행사(시험)", "timeZone": "Asia/Seoul"}'
```
Expected: 각각 `"id": "…@group.calendar.google.com"`. 두 ID 를 위 두 txt 파일에 한 줄씩 저장(실제 → `sije-calendar.txt`, 시험 → `sije-test-calendar.txt`).
gws 로그인이 풀렸으면(7일) 사장님이 메모리의 `--scopes` 로그인 명령을 다시 실행.

- [ ] **Step 2: 서버용 계정에 "일정 변경"으로 공유**

```bash
gws calendar acl insert --params '{"calendarId": "<실제 캘린더 ID>"}' --json '{"role": "writer", "scope": {"type": "user", "value": "firebase-adminsdk-fbsvc@foodbell-sije.iam.gserviceaccount.com"}}'
gws calendar acl insert --params '{"calendarId": "<시험 캘린더 ID>"}' --json '{"role": "writer", "scope": {"type": "user", "value": "firebase-adminsdk-fbsvc@foodbell-sije-test.iam.gserviceaccount.com"}}'
```
Expected: `"role": "writer"`. 안전 장치가 막으면 사장님이 구글 캘린더 웹 → 캘린더 설정 → "특정 사용자 또는 그룹과 공유" → 위 메일 · "일정 변경" 으로 직접.

- [ ] **Step 3: 사장님이 두 프로젝트에서 Google Calendar API 사용 설정**

`https://console.cloud.google.com/apis/library/calendar-json.googleapis.com?project=foodbell-sije` 와 `…?project=foodbell-sije-test` → **사용 설정**.

- [ ] **Step 4: 시험 서버용 계정으로 일정 하나 쓰고 지우기 (설계의 "추정" 확인)**

scratchpad 의 한 번 쓰는 스크립트: `KEY_TEST` 로 `service_account.Credentials`(범위 위) → `AuthorizedSession` →
`POST https://www.googleapis.com/calendar/v3/calendars/<시험 ID>/events` 본문 `{"summary": "쓰기 시험", "start": {"date": "2026-12-31"}, "end": {"date": "2027-01-01"}}` → 받은 `id` 로 `DELETE`.
Expected: 200 · 204. **403/404 면 멈추고 사장님께 보고** (설계 전제가 깨짐 — 이후 Task 진행 안 함).

---

### Task 2: 행사 → 일정 바꾸기 (순수 함수)

**Files:**
- Create: `tools/sije_web/calendar_sync.py`
- Test: `tools/sije_web/tests/test_calendar_sync.py`

**Interfaces:**
- Produces:
  - `parse_time(text: str | None) -> tuple[int, int] | None` — (시, 분). 못 읽으면 `None`.
  - `event_id(doc_id: str) -> str` — `'fb' + doc_id.encode('utf-8').hex()`.
  - `to_calendar_event(doc_id: str, ev: dict) -> dict | None` — 구글 일정 본문(`id`, `summary`, `location`, `description`, `start`, `end`, 미확정이면 `colorId`, `extendedProperties`). 넣지 않을 행사면 `None`.
  - 상수 `SITE = 'https://foodbell.kr/sije-sheet.html?id='`, `TZ = 'Asia/Seoul'`.

- [ ] **Step 1: 실패하는 시험 쓰기** — 아래 시험들 (값은 설계서 그대로)

```python
@pytest.mark.parametrize('text, want', [
    ('10시', (10, 0)), ('11시', (11, 0)), ('8시', (8, 0)), ('9시', (9, 0)), ('12시', (12, 0)), ('13시', (13, 0)),
    ('14시', (14, 0)), ('7시', (7, 0)), ('9시 30분', (9, 30)), ('5시', (5, 0)), ('07시', (7, 0)),   # 실제 자료 모양
    ('오전 10시', (10, 0)), ('오후 2시', (14, 0)), ('오후 12시', (12, 0)), ('오전 12시', (0, 0)),
    ('', None), (None, None), ('10시경', None), ('25시', None), ('오후', None),
])
def test_parse_time(text, want): assert parse_time(text) == want

def test_confirmed_timed_event():
    b = to_calendar_event('abc', fake_event())   # 확정 · 2026-11-13 · 10시
    assert b['summary'] == '가짜동 1-1 놀이터 위 · 7치 1상'
    assert b['location'] == '가짜동 1-1 놀이터 위'
    assert b['start'] == {'dateTime': '2026-11-13T10:00:00', 'timeZone': 'Asia/Seoul'}
    assert b['end'] == {'dateTime': '2026-11-13T12:00:00', 'timeZone': 'Asia/Seoul'}
    assert b['description'] == ('고객: 가짜 문중\n연락처: 010-0000-0000\n금액: 600,000원\n'
                                '내역서: https://foodbell.kr/sije-sheet.html?id=abc')
    assert 'colorId' not in b
    assert b['extendedProperties'] == {'private': {'foodbellId': 'abc'}} and b['id'] == event_id('abc')

def test_unconfirmed_is_marked_gray():
    b = to_calendar_event('x', fake_event(status='미확정'))
    assert b['summary'].startswith('[미확정] ') and b['colorId'] == '8'

def test_blank_time_is_all_day():
    b = to_calendar_event('x', fake_event(time=''))
    assert b['start'] == {'date': '2026-11-13'} and b['end'] == {'date': '2026-11-14'}

def test_late_start_rolls_to_next_day():
    b = to_calendar_event('x', fake_event(time='23시'))
    assert b['end'] == {'dateTime': '2026-11-14T01:00:00', 'timeZone': 'Asia/Seoul'}

@pytest.mark.parametrize('over', [{'status': '주문없음'}, {'date': ''}, {'status': ''}])
def test_not_put_on_calendar(over): assert to_calendar_event('x', fake_event(**over)) is None

def test_title_fallbacks():
    assert to_calendar_event('x', fake_event(place=''))['summary'] == '가짜동 1-1 · 7치 1상'
    assert to_calendar_event('x', fake_event(setting=''))['summary'] == '가짜동 1-1 놀이터 위'
    assert to_calendar_event('x', fake_event(place='', titlePlace='', setting=''))['summary'] == '시제행사'

def test_description_skips_blank_lines():
    b = to_calendar_event('x', fake_event(customer='', contacts=['010-1', '', '010-2'], amount=''))
    assert b['description'] == '연락처: 010-1, 010-2\n내역서: https://foodbell.kr/sije-sheet.html?id=x'

def test_event_id_is_base32hex_safe():
    i = event_id('가짜-1_A.b')
    assert re.fullmatch(r'[0-9a-v]{5,1024}', i) and i != event_id('가짜-1_A.c')
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_calendar_sync.py -q` → `ModuleNotFoundError` / ImportError.

- [ ] **Step 3: `calendar_sync.py` 에 위 세 함수 구현**

`parse_time`: 정규식 `^\s*(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?\s*$`. 오후이고 시<12 면 +12, 오전 12시 → 0. 시>23 · 분>59 면 `None`. 문자열이 아니면 `None`.
시간 있는 일정의 끝은 `datetime` 으로 +2시간 해서 날짜 넘김을 처리. 모듈 머리 docstring 은 기존 모듈처럼 한국어로 "무엇 · 왜".

- [ ] **Step 4: 통과 확인** — 같은 명령 → 모두 PASS.

---

### Task 3: 맞추기 (가짜 캘린더 상대)

**Files:**
- Modify: `tools/sije_web/calendar_sync.py`
- Modify: `tools/sije_web/tests/conftest.py` (끝에 `FakeCalendar` 추가 — Task 5 도 씀)
- Test: `tools/sije_web/tests/test_calendar_sync.py`

**Interfaces:**
- Consumes: `to_calendar_event`, `event_id` (Task 2).
- Produces:
  - 캘린더 부품 약속(가짜 · 진짜 공통): `list_tagged() -> dict[str, dict]` (foodbellId → 구글 일정 자료, 지워진 것 제외) · `insert(body: dict) -> None` · `update(event_id: str, body: dict) -> None` · `delete(event_id: str) -> None`.
  - `sync_calendar(cal, events: list[tuple[str, dict]]) -> dict` — 키 `made`, `updated`, `removed`(제목 목록), `failed`(`(행사 번호, 이유)` 목록), `guarded`(bool: 0개라 지우기를 건너뜀).
  - `same_event(existing: dict, desired: dict) -> bool` — 비교 대상: `summary`, `location`, `description`(없으면 `''`), `colorId`(없으면 `None`), `start` · `end`(종일은 `date` 글자, 시간은 `dateTime` 을 시간대 붙은 시각으로 바꿔 비교 — `'2026-11-13T10:00:00'`+`Asia/Seoul` 과 `'2026-11-13T10:00:00+09:00'` 은 같음).
  - `conftest.FakeCalendar(fail_ids: set[str] = frozenset())` — 위 약속을 메모리 dict 로. `calls` 목록에 `('insert'|'update'|'delete', event_id)` 를 쌓는다. `fail_ids` 에 든 일정 번호는 insert/update 때 `RuntimeError`.
    `untagged: dict[str, dict]` — 꼬리표 없는(손으로 만든) 일정 자리. `list_tagged` 에 나오지 않고, 맞추기가 건드리면 안 된다.

- [ ] **Step 1: 실패하는 시험 쓰기**

```python
def test_creates_updates_removes():
    cal = FakeCalendar()
    r = sync_calendar(cal, [('a', fake_event()), ('b', fake_event(status='미확정'))])
    assert len(r['made']) == 2 and set(cal.list_tagged()) == {'a', 'b'}
    r = sync_calendar(cal, [('a', fake_event(time='11시')), ('b', fake_event(status='주문없음'))])
    assert len(r['updated']) == 1 and len(r['removed']) == 1 and set(cal.list_tagged()) == {'a'}

def test_second_run_does_nothing():
    cal = FakeCalendar(); evs = [('a', fake_event())]
    sync_calendar(cal, evs); cal.calls.clear()
    sync_calendar(cal, evs)
    assert cal.calls == []

def test_google_shaped_existing_counts_as_same():
    desired = to_calendar_event('a', fake_event())
    google = {**desired, 'start': {'dateTime': '2026-11-13T10:00:00+09:00', 'timeZone': 'Asia/Seoul'},
              'end': {'dateTime': '2026-11-13T12:00:00+09:00', 'timeZone': 'Asia/Seoul'}, 'etag': '"1"', 'status': 'confirmed'}
    assert same_event(google, desired)
    assert not same_event({**google, 'summary': '사장님이 고친 제목'}, desired)   # 캘린더에서 고친 것은 되돌린다

def test_empty_source_deletes_nothing():
    cal = FakeCalendar(); sync_calendar(cal, [('a', fake_event())])
    r = sync_calendar(cal, [])
    assert r['guarded'] and set(cal.list_tagged()) == {'a'}

def test_untagged_events_untouched():
    cal = FakeCalendar(); cal.untagged['manual'] = {'id': 'manual', 'summary': '사장님 개인 일정'}
    sync_calendar(cal, [('a', fake_event())])
    assert 'manual' in cal.untagged and all(i != 'manual' for _, i in cal.calls)

def test_one_failure_does_not_stop_others():
    cal = FakeCalendar(fail_ids={event_id('a')})
    r = sync_calendar(cal, [('a', fake_event()), ('b', fake_event())])
    assert [i for i, _ in r['failed']] == ['a'] and 'b' in cal.list_tagged()
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_calendar_sync.py -q` → 새 시험 FAIL(ImportError `sync_calendar`/`FakeCalendar`).

- [ ] **Step 3: `same_event`, `sync_calendar` 구현 + `FakeCalendar`**

`sync_calendar`: `desired = {id: body}`(None 제외) · `have = cal.list_tagged()`. 없으면 insert, `same_event` 가 아니면 update, `have` 에만 있으면 delete — 단 `events` 가 비면 delete 를 모두 건너뛰고 `guarded=True`. 일정 하나마다 `try`, 실패는 `failed` 에 담고 계속.

- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS. 그리고 `python -m pytest tools/sije_web/tests/test_office_agent.py -q` 도 PASS(conftest 를 건드렸으므로).

---

### Task 4: 구글 캘린더 부품 (서비스 계정) + 실제 시험 캘린더 시험

**Files:**
- Modify: `tools/sije_web/calendar_sync.py`
- Test: `tools/sije_web/tests/test_calendar_live.py`

**Interfaces:**
- Consumes: 캘린더 부품 약속 · `sync_calendar` · `to_calendar_event` (Task 2 · 3).
- Produces:
  - `class GoogleCalendar(key: Path, calendar_id: str)` — 위 약속을 구글 REST(`https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events`)로. `list_tagged` 는 `maxResults=2500` · `nextPageToken` 끝까지 · `showDeleted=false` 로 받아 꼬리표 있는 것만. `insert` 가 409 면 같은 번호를 `PUT` 하면서 `status: 'confirmed'` 로 되살린다. 2xx 가 아니면 `CalendarError(status: int, message: str)`; 403 · 404 는 메시지 `'캘린더 권한 없음'`.
  - `calendar_file(key: Path) -> Path` — `key.with_name(key.stem.replace('-admin', '-calendar') + '.txt')` (`sije-admin.json` → `sije-calendar.txt`).
  - `open_calendar(key: Path) -> GoogleCalendar | None` — 위 파일이 없으면 `None`.

- [ ] **Step 1: 실패하는 시험 쓰기** (시험 열쇠나 시험 캘린더 파일이 없으면 `pytest.skip`, 끝나면 만든 일정 지움)

```python
def test_calendar_file_name():
    assert calendar_file(Path(r'C:\k\sije-admin.json')) == Path(r'C:\k\sije-calendar.txt')
    assert calendar_file(Path(r'C:\k\sije-test-admin.json')) == Path(r'C:\k\sije-test-calendar.txt')

def test_open_calendar_without_file_is_none(tmp_path):
    assert open_calendar(tmp_path / 'sije-admin.json') is None

def test_live_sync_twice_is_stable(live_cal):            # live_cal = open_calendar(fsdb.KEY_TEST), 없으면 skip
    doc = 'livetest-' + uuid.uuid4().hex[:8]
    first = sync_calendar(live_cal, [(doc, fake_event())])
    second = sync_calendar(live_cal, [(doc, fake_event())])
    assert len(first['made']) == 1 and not second['updated'] and not second['made']   # 구글 모양과도 '같음'
    sync_calendar(live_cal, [(doc, fake_event(status='주문없음'))])
    assert doc not in live_cal.list_tagged()

def test_live_revive_after_delete(live_cal):
    doc = 'livetest-' + uuid.uuid4().hex[:8]
    body = to_calendar_event(doc, fake_event())
    live_cal.insert(body); live_cal.delete(body['id'])
    live_cal.insert(body)                                  # 409 → 되살림
    assert doc in live_cal.list_tagged()
    live_cal.delete(body['id'])
```

주의: `test_live_sync_twice_is_stable` 의 `sync_calendar` 는 시험 캘린더의 다른 꼬리표 일정을 지운다 — 시험 캘린더에는 시험 일정만 있으므로 괜찮다.

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_calendar_live.py -q` → ImportError.

- [ ] **Step 3: `GoogleCalendar`, `CalendarError`, `calendar_file`, `open_calendar` 구현** — `service_account.Credentials.from_service_account_file(str(key), scopes=[범위])` + `AuthorizedSession`. 캘린더 ID 는 `urllib.parse.quote(…, safe='')`.

- [ ] **Step 4: 통과 확인** — 같은 명령 → 4개 PASS (skip 이면 실패로 본다 — Task 1 준비가 빠진 것).

---

### Task 5: 사무실 PC 프로그램에 붙이기

**Files:**
- Modify: `tools/sije_web/office_agent.py` (`one_cycle`, `main`)
- Test: `tools/sije_web/tests/test_office_agent.py`

**Interfaces:**
- Consumes: `sync_calendar`, `open_calendar` (Task 3 · 4), `conftest.FakeCalendar`.
- Produces: `one_cycle(source, work_root, state_file, base_url, log, calendar=None)` — 기존 인자 그대로, 맨 끝에 `calendar` 추가.

- [ ] **Step 1: 실패하는 시험 쓰기** (기존 `BrokenSource` 재사용 — PDF 는 실패, 전체 목록은 `[('a', fake_event())]`)

```python
def test_calendar_synced_even_when_pdf_fails(tmp_path):
    cal = FakeCalendar()
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'), cal)
    assert set(cal.list_tagged()) == {'a'}

def test_calendar_failure_does_not_stop_backup(tmp_path):
    class Broken(FakeCalendar):
        def list_tagged(self): raise ConnectionError('흉내: 끊김')
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'), Broken())
    assert list((tmp_path / '백업').glob('*시제행사 백업.xlsx'))
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tools/sije_web/tests/test_office_agent.py -q` → 새 시험 FAIL(`one_cycle` 인자 개수).

- [ ] **Step 3: 구현**

`one_cycle`: 백업 다음에 `if calendar is not None:` 세 번째 `try` — `sync_calendar(calendar, source.all_events())`. 기록: `캘린더 만듦/고침/지움: <제목>`(info), 실패는 `캘린더 실패 (다음 차례에 다시): <번호> — <이유>`(warning), `guarded` 면 `캘린더: 행사 목록이 0개로 읽혀 지우기를 건너뜀`(warning). 예외는 `log.exception('캘린더 차례 실패 (다음 차례에 다시)')`.
`main`: `calendar = calendar_sync.open_calendar(a.key)` 를 만들어 `one_cycle` 에 넘기고, 시작 기록에 `캘린더 켬/끔` 을 덧붙인다. 모듈 docstring 첫 줄에 "· 캘린더 맞추기" 추가.

- [ ] **Step 4: 통과 확인** — `python -m pytest tools/sije_web/tests/test_office_agent.py tools/sije_web/tests/test_calendar_sync.py -q` → PASS. 이어서 `python -m pytest tools/sije_web/tests -q -x` 전체가 이전과 같이 통과(브라우저 시험의 일시적 실패는 그 시험만 다시 돌려 확인).

---

### Task 6: 실제로 켜기 · 확인

**Files:** Modify: `CLAUDE.md` (파일 목록의 `tools/sije_web/` 줄에 한 줄 — "5분마다 '푸드벨 행사' 캘린더도 맞춤, 캘린더 ID 는 `C:\foodbell-keys\sije-calendar.txt`").

- [ ] **Step 1: 예약 작업 다시 시작** — PowerShell `Stop-ScheduledTask -TaskName '푸드벨 시제 PDF'; Start-ScheduledTask -TaskName '푸드벨 시제 PDF'`.
  Expected: `Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'"` 의 `CreationDate` 가 방금 시각.

- [ ] **Step 2: 기록 확인** — `%LOCALAPPDATA%\foodbell-sije\agent.log` 끝에 `시작 (… 캘린더 켬)` 과 `캘린더 만듦:` 줄이 (확정 + 날짜 있는 미확정 수)만큼. 경고 · 실패 줄 없음.

- [ ] **Step 3: 캘린더 숫자 대조** — `gws calendar events list --params '{"calendarId": "<실제 ID>", "maxResults": 2500}'` 의 일정 수 = 저장소에서 `to_calendar_event` 가 `None` 아닌 행사 수. 5분 뒤 기록에 `캘린더 고침` 이 다시 나오지 않음(Review Focus 3).

- [ ] **Step 4: 사장님 확인** — 휴대폰 구글 캘린더에서 "푸드벨 행사" 를 켜고 3월 1일 행사 · 미확정 하나(회색, `[미확정]`)를 본다. 목록에서 시험 삼아 행사 하나의 시간을 바꾸면 5분 안에 캘린더도 바뀌는지.

- [ ] **Step 5: `CLAUDE.md` 한 줄 추가.**
