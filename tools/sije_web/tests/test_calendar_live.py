"""구글 캘린더 부품 시험 — 시험 프로젝트 서버용 계정 + "푸드벨 행사(시험)" 캘린더에 실제로 쓴다.
시험 열쇠나 시험 캘린더 파일(C:\\foodbell-keys\\sije-test-calendar.txt)이 없는 PC 에서는 건너뛴다."""
import uuid
from pathlib import Path

import pytest

from conftest import fake_event
from tools.sije_web import fsdb
from tools.sije_web.calendar_sync import calendar_file, open_calendar, sync_calendar, to_calendar_event


@pytest.fixture(scope='module')
def live_cal():
    cal = open_calendar(fsdb.KEY_TEST) if fsdb.KEY_TEST.exists() else None
    if cal is None:
        pytest.skip('시험 열쇠 또는 시험 캘린더 파일이 없습니다')
    return cal


def test_calendar_file_name():
    assert calendar_file(Path(r'C:\k\sije-admin.json')) == Path(r'C:\k\sije-calendar.txt')
    assert calendar_file(Path(r'C:\k\sije-test-admin.json')) == Path(r'C:\k\sije-test-calendar.txt')


def test_open_calendar_without_file_is_none(tmp_path):
    assert open_calendar(tmp_path / 'sije-admin.json') is None


def test_live_sync_twice_is_stable(live_cal):
    """구글이 돌려주는 모양('+09:00' 등)과도 '같음'으로 봐야 5분마다 다시 고치지 않는다.
    (시험 캘린더의 다른 꼬리표 일정은 지운다 — 시험 캘린더에는 시험 일정만 있다)"""
    doc = 'livetest-' + uuid.uuid4().hex[:8]
    first = sync_calendar(live_cal, [(doc, fake_event())])
    second = sync_calendar(live_cal, [(doc, fake_event())])
    assert len(first['made']) == 1 and not second['updated'] and not second['made'] and not second['failed']
    sync_calendar(live_cal, [(doc, fake_event(status='주문없음'))])
    assert doc not in live_cal.list_tagged()


def test_live_revive_after_delete(live_cal):
    """캘린더에서 지운 일정의 번호는 구글이 다시 못 쓰게 한다(409) — 되살려야 한다."""
    doc = 'livetest-' + uuid.uuid4().hex[:8]
    body = to_calendar_event(doc, fake_event())
    live_cal.insert(body)
    live_cal.delete(body['id'])
    live_cal.insert(body)
    try:
        assert doc in live_cal.list_tagged()
    finally:
        live_cal.delete(body['id'])
