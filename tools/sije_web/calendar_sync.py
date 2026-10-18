"""시제행사 → 구글 캘린더 "푸드벨 행사" 맞추기 (사무실 PC 프로그램이 5분마다 부른다).

한쪽 방향: 목록(내역서)이 원본이고 캘린더는 보기용 — 캘린더에서 고친 것은 다음 차례에 목록 내용으로 되돌아간다.
설계: docs/superpowers/specs/2026-10-18-calendar-sync-design.md
"""
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from tools.sije_web import fsdb  # noqa: F401 — 윈도우 인증서 설정을 requests 보다 먼저 건다

SCOPE = 'https://www.googleapis.com/auth/calendar.events'
API = 'https://www.googleapis.com/calendar/v3/calendars/'
SITE = 'https://foodbell.kr/sije-sheet.html?id='
TZ = 'Asia/Seoul'
KST = timezone(timedelta(hours=9))   # 서울은 서머타임이 없다 — 시간대 꾸러미(tzdata) 없이 비교하려고
HOURS = 2            # 행사 길이 — 자료에 없어서 정한 값 (설계 · 사장님 확인 2026-10-18)
GRAY = '8'           # 미확정 일정 색
PUT_ON = ('확정', '미확정')

_TIME = re.compile(r'^\s*(오전|오후)?\s*(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?\s*$')


def parse_time(text) -> tuple[int, int] | None:
    """'10시' · '9시 30분' · '오후 2시' → (시, 분). 적힌 숫자 그대로('5시' = 새벽 5시). 못 읽으면 None."""
    if not isinstance(text, str):
        return None
    m = _TIME.match(text)
    if not m:
        return None
    ampm, h, mi = m.group(1), int(m.group(2)), int(m.group(3) or 0)
    if ampm == '오후' and h < 12:
        h += 12
    elif ampm == '오전' and h == 12:
        h = 0
    return (h, mi) if h <= 23 and mi <= 59 else None


def event_id(doc_id: str) -> str:
    """행사 번호 → 캘린더 일정 번호 (구글 규칙: 소문자 a–v · 숫자). 같은 행사는 늘 같은 번호."""
    return 'fb' + doc_id.encode('utf-8').hex()


def to_calendar_event(doc_id: str, ev: dict) -> dict | None:
    """행사 하나 → 구글 일정 본문. 캘린더에 넣지 않을 행사(주문없음 · 날짜 없음)면 None."""
    status, day = ev.get('status'), ev.get('date')
    if status not in PUT_ON or not day:
        return None
    place = ev.get('place') or ev.get('titlePlace') or ''
    title = ' · '.join(x for x in (place, ev.get('setting') or '') if x) or '시제행사'
    if status == '미확정':
        title = '[미확정] ' + title
    contacts = ', '.join(c for c in ev.get('contacts') or [] if c)
    lines = [f'고객: {ev["customer"]}' if ev.get('customer') else '',
             f'연락처: {contacts}' if contacts else '',
             f'금액: {ev["amount"]}' if ev.get('amount') else '',
             f'내역서: {SITE}{doc_id}']
    hm = parse_time(ev.get('time'))
    if hm:
        start = datetime.fromisoformat(day).replace(hour=hm[0], minute=hm[1])
        when = {'start': {'dateTime': start.isoformat(), 'timeZone': TZ},
                'end': {'dateTime': (start + timedelta(hours=HOURS)).isoformat(), 'timeZone': TZ}}
    else:   # 시간이 없거나 못 읽으면 종일 — 끝은 다음 날(구글 규칙)
        when = {'start': {'date': day}, 'end': {'date': (date.fromisoformat(day) + timedelta(days=1)).isoformat()}}
    body = {
        'id': event_id(doc_id), 'summary': title, 'location': place,
        'description': '\n'.join(x for x in lines if x), **when,
        'extendedProperties': {'private': {'foodbellId': doc_id}},
    }
    if status == '미확정':
        body['colorId'] = GRAY
    return body


def _when(x: dict):
    """일정의 시작/끝 → 비교할 값. 종일은 날짜 글자, 시간은 시간대 붙은 시각(구글은 '+09:00' 을 붙여 돌려준다)."""
    if 'date' in x:
        return x['date']
    t = datetime.fromisoformat(x['dateTime'])
    return t if t.tzinfo else t.replace(tzinfo=KST)


def same_event(existing: dict, desired: dict) -> bool:
    """캘린더에 있는 일정이 원하는 모양과 같은가 — 다르면 고친다(캘린더에서 손으로 고친 것도 되돌린다)."""
    def key(e):
        return (e.get('summary') or '', e.get('location') or '', e.get('description') or '', e.get('colorId'),
                _when(e['start']), _when(e['end']))
    return key(existing) == key(desired)


def sync_calendar(cal, events: list[tuple[str, dict]]) -> dict:
    """캘린더의 꼬리표 일정 ↔ 행사 전체를 비교해 만들기 · 고치기 · 지우기. 일정 하나가 실패해도 나머지는 계속.
    행사가 0개로 읽히면 '목록을 못 읽은 것'으로 보고 아무것도 지우지 않는다(guarded)."""
    result = {'made': [], 'updated': [], 'removed': [], 'failed': [], 'guarded': False}
    desired, broken = {}, set()
    for doc_id, ev in events:
        try:
            body = to_calendar_event(doc_id, ev)
        except Exception as e:   # 날짜가 틀린 행사 등 — 그 행사만 건너뛰고, 캘린더의 기존 일정도 지우지 않는다
            result['failed'].append((doc_id, f'일정 모양 실패: {e}'))
            broken.add(doc_id)
            continue
        if body:
            desired[doc_id] = body
    have = cal.list_tagged()
    for doc_id, body in desired.items():
        try:
            old = have.get(doc_id)
            if old is None:
                cal.insert(body)
                result['made'].append(body['summary'])
            elif not same_event(old, body):
                cal.update(body['id'], body)
                result['updated'].append(body['summary'])
        except Exception as e:
            result['failed'].append((doc_id, str(e)))
    if not events:
        result['guarded'] = True
        return result
    for doc_id, old in have.items():
        if doc_id in desired or doc_id in broken:
            continue
        try:
            cal.delete(old['id'])
            result['removed'].append(old.get('summary', ''))
        except Exception as e:
            result['failed'].append((doc_id, str(e)))
    return result


class CalendarJob:
    """5분마다 부르는 캘린더 차례. 파이어베이스 읽기를 아끼려고(무료 한도를 웹 서류와 같이 쓴다)
    평소에는 '바뀐 행사가 있나'만 묻고, 바뀐 것이 있을 때와 한 시간에 한 번만 전체를 읽어 맞춘다.
    → 목록에서 고친 것은 5분 안에, 캘린더에서 손으로 고친 것은 1시간 안에 목록 내용으로 되돌아간다."""

    FULL_EVERY = 3600   # 초

    def __init__(self, cal):
        self.cal = cal
        self.since = None     # 마지막으로 본 가장 늦은 updatedAt (isoformat)
        self.full_at = None   # 마지막 전체 맞추기 시각 (time.time())

    def run(self, source, now: float) -> dict | None:
        """맞추기 결과(sync_calendar 와 같은 모양). 바뀐 것이 없어 건너뛰면 None."""
        recent = self.full_at is not None and now - self.full_at < self.FULL_EVERY
        if recent and self.since and not source.changed_since(self.since):
            return None
        events = source.all_events()
        result = sync_calendar(self.cal, events)
        self.full_at = now
        stamps = [ev['updatedAt'] for _, ev in events if ev.get('updatedAt')]
        if stamps:
            self.since = max(stamps).isoformat()
        return result


class CalendarError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f'{status} {message}')
        self.status = status


class GoogleCalendar:
    """캘린더 부품 — 서버용 계정(관리자 열쇠)으로, 사장님이 공유해 준 캘린더 하나를 다룬다(7일 로그인 없음)."""

    def __init__(self, key: Path, calendar_id: str):
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(str(key), scopes=[SCOPE])
        self.s = AuthorizedSession(creds)
        self.base = API + quote(calendar_id, safe='') + '/events'

    @staticmethod
    def _check(r):
        if r.ok:
            return r
        try:
            msg = r.json()['error']['message']
        except Exception:
            msg = r.text[:200]
        if r.status_code in (403, 404):   # 공유가 풀렸거나 캘린더 서비스가 꺼졌을 때
            msg = f'캘린더 권한 없음 — {msg}'
        raise CalendarError(r.status_code, msg)

    def list_tagged(self) -> dict[str, dict]:
        """꼬리표(foodbellId) 있는 일정만 — 사장님이 손으로 만든 일정은 아예 보지 않는다."""
        out, token = {}, None
        while True:
            params = {'maxResults': 2500, 'showDeleted': 'false'}
            if token:
                params['pageToken'] = token
            d = self._check(self.s.get(self.base, params=params, timeout=30)).json()
            for e in d.get('items', []):
                fid = e.get('extendedProperties', {}).get('private', {}).get('foodbellId')
                if fid:
                    out[fid] = e
            token = d.get('nextPageToken')
            if not token:
                return out

    def insert(self, body: dict) -> None:
        r = self.s.post(self.base, json=body, timeout=30)
        if r.status_code == 409:   # 한 번 지운 일정의 번호는 새로 못 만든다 — 같은 번호를 되살린다
            r = self.s.put(f"{self.base}/{body['id']}", json={**body, 'status': 'confirmed'}, timeout=30)
        self._check(r)

    def update(self, event_id: str, body: dict) -> None:
        self._check(self.s.put(f'{self.base}/{event_id}', json=body, timeout=30))

    def delete(self, event_id: str) -> None:
        self._check(self.s.delete(f'{self.base}/{event_id}', timeout=30))


def calendar_file(key: Path) -> Path:
    """열쇠 옆의 캘린더 ID 파일 (sije-admin.json → sije-calendar.txt). 저장소에는 넣지 않는다."""
    return key.with_name(key.stem.replace('-admin', '-calendar') + '.txt')


def open_calendar(key: Path) -> GoogleCalendar | None:
    """캘린더 ID 파일이 없는 PC(집 · 노트북)면 None — 캘린더 단계를 건너뛴다."""
    f = calendar_file(Path(key))
    if not f.exists():
        return None
    return GoogleCalendar(Path(key), f.read_text(encoding='utf-8').strip())
