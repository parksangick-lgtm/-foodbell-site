"""사무실 PC 프로그램 시험 — 저장소 · 크롬 없이 한 차례를 흉내 낸다."""
import json
import logging

import pytest

from conftest import FakeCalendar, fake_event
from tools.sije_web import calendar_sync, office_agent


class BrokenSource:
    """바뀐 행사 묻기가 실패하는 저장소 (인터넷이 잠깐 끊긴 것처럼). 전체 목록은 준다."""

    def changed_since(self, since):
        raise ConnectionError('흉내: 끊김')

    def images(self, id):
        return []

    def all_events(self):
        return [('a', fake_event())]

    def all_docs(self):
        return [('d1', {'kind': 'statement', 'html': '<p>가짜</p>', 'label': '○○ 문중 종친회'})]


def test_backup_runs_even_when_pdf_sync_fails(tmp_path):
    log = logging.getLogger('test-agent')
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 'state.json', 'http://unused/', log)
    assert list((tmp_path / '백업').glob('*시제행사 백업.xlsx'))


def test_backup_includes_docs_from_source(tmp_path):
    """하루 한 번 백업에 서류 5종도 함께 (2단계)."""
    import openpyxl
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 'state.json', 'http://unused/',
                           logging.getLogger('test-agent'))
    [backup] = (tmp_path / '백업').glob('*시제행사 백업.xlsx')
    ws = openpyxl.load_workbook(backup)['서류']
    assert [c.value for c in ws[2]][:3] == ['d1', '거래명세서', '○○ 문중 종친회']


def test_calendar_synced_even_when_pdf_fails(tmp_path):
    cal = FakeCalendar()
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                           calendar_sync.CalendarJob([('사장님', cal, False)]))
    assert set(cal.list_tagged()) == {'a'}


def test_staff_calendar_synced_and_logged_with_label(tmp_path, caplog):
    owner, staff = FakeCalendar(), FakeCalendar()
    with caplog.at_level(logging.INFO, logger='t'):
        office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                               calendar_sync.CalendarJob([('사장님', owner, False), ('직원', staff, True)]))
    assert set(owner.list_tagged()) == {'a'} and set(staff.list_tagged()) == {'a'}
    msgs = [r.getMessage() for r in caplog.records]
    assert any(m.startswith('캘린더 만듦:') for m in msgs) and any(m.startswith('캘린더(직원) 만듦:') for m in msgs)


def test_one_calendar_failing_does_not_stop_the_other(tmp_path):
    class Revoked(FakeCalendar):
        def list_tagged(self):
            raise calendar_sync.CalendarError(403, '캘린더 권한 없음 — 흉내')
    owner = FakeCalendar()
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                           calendar_sync.CalendarJob([('직원', Revoked(), True), ('사장님', owner, False)]))
    assert set(owner.list_tagged()) == {'a'}


def test_calendar_failure_does_not_stop_backup(tmp_path):
    class Broken(FakeCalendar):
        def list_tagged(self):
            raise ConnectionError('흉내: 끊김')
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                           calendar_sync.CalendarJob([('사장님', Broken(), False)]))
    assert list((tmp_path / '백업').glob('*시제행사 백업.xlsx'))


def test_calendar_permission_error_is_a_short_warning(tmp_path, caplog):
    """공유가 풀리면 5분마다 긴 오류 기록(traceback) 대신 한 줄 경고 — 기록 파일에서 PDF 기록이 밀려나지 않게."""
    class Revoked(FakeCalendar):
        def list_tagged(self):
            raise calendar_sync.CalendarError(403, '캘린더 권한 없음 — 흉내')
    with caplog.at_level(logging.INFO, logger='t'):
        office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                               calendar_sync.CalendarJob([('사장님', Revoked(), False)]))
    recs = [r for r in caplog.records if '캘린더' in r.getMessage()]
    assert recs and all(r.levelno == logging.WARNING and not r.exc_info for r in recs)


def test_staff_sheets_failure_does_not_stop_pdf_and_backup(tmp_path):
    class BrokenDb:
        def collection(self, name):
            raise ConnectionError('흉내: 끊김')
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                           sheets=BrokenDb())
    assert list((tmp_path / '백업').glob('*시제행사 백업.xlsx'))


NUL = b'\x00' * 66   # 2026-11-13 정전 뒤 사무실 PC 의 담당자 기록 파일이 실제로 이 모양이었다


class CalmSource(BrokenSource):
    """바뀐 것 묻기에 준 목록을 그대로 돌려주는 저장소."""

    def __init__(self, docs=()):
        self.docs = list(docs)

    def changed_since(self, since, kind='events'):
        return self.docs if kind == 'docs' else []


@pytest.mark.parametrize('name', ['s.json', 's-staff.json'])
def test_broken_state_file_is_put_aside_and_step_starts_fresh(tmp_path, monkeypatch, caplog, name):
    """0 으로 찬 기록 파일 — 그 차례가 5분마다 실패만 되풀이하지 않고(11-13 ~ 11-14, 387번) 옆으로 치운 뒤
    빈 기록으로 처음부터 한 번 다시 본다(PDF 는 같은 이름에 다시 만들고, 담당자 내역서는 전체를 다시 본다)."""
    seen = {}

    def recorder(file, i, out):
        def run(*a):
            seen[file] = dict(a[i])
            a[i]['since'] = 'x'
            return out
        return run
    monkeypatch.setattr(office_agent, 'sync_once', recorder('s.json', 2, {'made': [], 'removed': [], 'failed': [], 'skipped': []}))
    monkeypatch.setattr(office_agent.staff_sheets, 'sync_staff_sheets', recorder('s-staff.json', 1, {'written': [], 'removed': []}))
    broken = tmp_path / name
    broken.write_bytes(NUL)
    with caplog.at_level(logging.WARNING, logger='t'):
        office_agent.one_cycle(CalmSource(), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                               sheets=object())
    assert seen == {'s.json': {}, 's-staff.json': {}}
    assert json.loads(broken.read_text(encoding='utf-8')) == {'since': 'x'}
    [aside] = tmp_path.glob(f'{name}.broken-*')
    assert aside.read_bytes() == NUL
    assert any(name in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)


def test_broken_obsidian_state_does_not_copy_every_note_again(tmp_path, caplog):
    """옵시디언 기록이 망가지면 '지금부터' 바뀐 일정표만 옮긴다 — 빈 기록으로 처음부터 보면 어느 노트가 프로그램 것인지 몰라
    있는 노트마다 '… (2).md' 를 한 벌 더 만든다(사무실 볼트에 57개)."""
    note = tmp_path / '푸드벨-업무' / '일일 일정표' / '2026-11-22 (일).md'
    note.parent.mkdir(parents=True)
    note.write_text('먼저 옮긴 것', encoding='utf-8')
    old = ('d1', {'kind': 'daily-schedule', 'label': '2026년 11월 22일 (일)', 'text': '옛 판',
                  'updatedAt': '2026-11-21T12:11:08.437000+00:00'})
    broken = tmp_path / 's-obsidian.json'
    broken.write_bytes(NUL)
    with caplog.at_level(logging.WARNING, logger='t'):
        office_agent.one_cycle(CalmSource([old]), tmp_path, tmp_path / 's.json', 'http://unused/', logging.getLogger('t'),
                               vault=tmp_path)
    assert sorted(p.name for p in note.parent.iterdir()) == ['2026-11-22 (일).md']
    assert note.read_text(encoding='utf-8') == '먼저 옮긴 것'
    assert json.loads(broken.read_text(encoding='utf-8'))['since'] > old[1]['updatedAt']
    [aside] = tmp_path.glob('s-obsidian.json.broken-*')
    assert aside.read_bytes() == NUL
    assert any('s-obsidian.json' in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)


def test_agent_refuses_missing_work_root(tmp_path):
    """원드라이브 폴더가 없으면(경로가 다른 PC) 동기화 안 되는 곳에 PDF 를 쌓지 않고 멈춘다."""
    assert office_agent.main(['--once', '--work-root', str(tmp_path / '없는 폴더')]) == 2
