"""캘린더 맞추기 시험 — 인터넷 없이. 시간 칸 모양은 실제 행사 85개에서 본 그대로 (2026-10-18)."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from conftest import FakeCalendar, fake_event
from tools.sije_web.calendar_sync import (
    CalendarJob, event_id, parse_time, same_event, sync_calendar, to_calendar_event,
)


@pytest.mark.parametrize('text, want', [
    ('10시', (10, 0)), ('11시', (11, 0)), ('8시', (8, 0)), ('9시', (9, 0)), ('12시', (12, 0)), ('13시', (13, 0)),
    ('14시', (14, 0)), ('7시', (7, 0)), ('9시 30분', (9, 30)), ('5시', (5, 0)), ('07시', (7, 0)),   # 실제 자료 모양
    ('오전 10시', (10, 0)), ('오후 2시', (14, 0)), ('오후 12시', (12, 0)), ('오전 12시', (0, 0)),     # 견적서에서 온 모양
    ('', None), (None, None), ('10시경', None), ('25시', None), ('오후', None),
])
def test_parse_time(text, want):
    assert parse_time(text) == want


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


def test_unreadable_time_is_all_day():
    assert to_calendar_event('x', fake_event(time='10시경'))['start'] == {'date': '2026-11-13'}


def test_late_start_rolls_to_next_day():
    b = to_calendar_event('x', fake_event(time='23시'))
    assert b['end'] == {'dateTime': '2026-11-14T01:00:00', 'timeZone': 'Asia/Seoul'}


@pytest.mark.parametrize('over', [{'status': '주문없음'}, {'date': ''}, {'status': ''}])
def test_not_put_on_calendar(over):
    assert to_calendar_event('x', fake_event(**over)) is None


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


# ---------- 맞추기 (가짜 캘린더) ----------

def test_creates_updates_removes():
    cal = FakeCalendar()
    r = sync_calendar(cal, [('a', fake_event()), ('b', fake_event(status='미확정'))])
    assert len(r['made']) == 2 and set(cal.list_tagged()) == {'a', 'b'}
    r = sync_calendar(cal, [('a', fake_event(time='11시')), ('b', fake_event(status='주문없음'))])
    assert len(r['updated']) == 1 and len(r['removed']) == 1 and set(cal.list_tagged()) == {'a'}


def test_second_run_does_nothing():
    cal = FakeCalendar()
    evs = [('a', fake_event())]
    sync_calendar(cal, evs)
    cal.calls.clear()
    sync_calendar(cal, evs)
    assert cal.calls == []


def test_google_shaped_existing_counts_as_same():
    desired = to_calendar_event('a', fake_event())
    google = {**desired, 'start': {'dateTime': '2026-11-13T10:00:00+09:00', 'timeZone': 'Asia/Seoul'},
              'end': {'dateTime': '2026-11-13T12:00:00+09:00', 'timeZone': 'Asia/Seoul'}, 'etag': '"1"', 'status': 'confirmed'}
    assert same_event(google, desired)
    assert not same_event({**google, 'summary': '사장님이 고친 제목'}, desired)   # 캘린더에서 고친 것은 되돌린다


def test_empty_source_deletes_nothing():
    cal = FakeCalendar()
    sync_calendar(cal, [('a', fake_event())])
    r = sync_calendar(cal, [])
    assert r['guarded'] and set(cal.list_tagged()) == {'a'}


def test_untagged_events_untouched():
    cal = FakeCalendar()
    cal.untagged['manual'] = {'id': 'manual', 'summary': '사장님 개인 일정'}
    sync_calendar(cal, [('a', fake_event())])
    assert 'manual' in cal.untagged and all(i != 'manual' for _, i in cal.calls)


def test_one_failure_does_not_stop_others():
    cal = FakeCalendar(fail_ids={event_id('a')})
    r = sync_calendar(cal, [('a', fake_event()), ('b', fake_event())])
    assert [i for i, _ in r['failed']] == ['a'] and 'b' in cal.list_tagged()


def test_bad_event_is_skipped_not_deleted():
    """날짜가 틀린 행사(옛 엑셀 '2월 30일' 등) 하나 때문에 나머지가 멈추면 안 되고, 그 행사의 기존 일정은 지우지 않는다."""
    cal = FakeCalendar()
    sync_calendar(cal, [('good', fake_event()), ('bad', fake_event())])
    r = sync_calendar(cal, [('good', fake_event(time='11시')), ('bad', fake_event(date='2026-02-30'))])
    assert [i for i, _ in r['failed']] == ['bad'] and len(r['updated']) == 1
    assert set(cal.list_tagged()) == {'good', 'bad'}


# ---------- 차례 (파이어베이스 읽기 아끼기) ----------

T0 = datetime(2026, 10, 18, 0, 0, tzinfo=timezone.utc)


class CountingSource:
    """전체 읽기 횟수를 세는 가짜 저장소 — 바뀐 것 묻기는 updatedAt 으로."""

    def __init__(self, events):
        self.events = events
        self.full = 0

    def all_events(self):
        self.full += 1
        return self.events

    def changed_since(self, since):
        return [(i, e) for i, e in self.events if e['updatedAt'] > datetime.fromisoformat(since)]


def test_job_reads_everything_only_when_needed():
    src = CountingSource([('a', fake_event(updatedAt=T0))])
    job = CalendarJob(FakeCalendar())
    assert job.run(src, now=0)['made']                                   # 처음: 전체
    assert job.run(src, now=300) is None and src.full == 1                # 바뀐 것 없음: 전체를 안 읽는다
    src.events = [('a', fake_event(time='11시', updatedAt=T0 + timedelta(minutes=7)))]
    assert job.run(src, now=600)['updated'] and src.full == 2             # 바뀜: 5분 안에 반영
    assert job.run(src, now=600 + 3600) is not None and src.full == 3     # 한 시간마다: 전체 (캘린더에서 손댄 것 되돌리기)
