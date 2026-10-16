"""사무실 PC 프로그램 시험 — 저장소 · 크롬 없이 한 차례를 흉내 낸다."""
import logging

from conftest import fake_event
from tools.sije_web import office_agent


class BrokenSource:
    """바뀐 행사 묻기가 실패하는 저장소 (인터넷이 잠깐 끊긴 것처럼). 전체 목록은 준다."""

    def changed_since(self, since):
        raise ConnectionError('흉내: 끊김')

    def images(self, id):
        return []

    def all_events(self):
        return [('a', fake_event())]


def test_backup_runs_even_when_pdf_sync_fails(tmp_path):
    log = logging.getLogger('test-agent')
    office_agent.one_cycle(BrokenSource(), tmp_path, tmp_path / 'state.json', 'http://unused/', log)
    assert list((tmp_path / '백업').glob('*시제행사 백업.xlsx'))


def test_agent_refuses_missing_work_root(tmp_path):
    """원드라이브 폴더가 없으면(경로가 다른 PC) 동기화 안 되는 곳에 PDF 를 쌓지 않고 멈춘다."""
    assert office_agent.main(['--once', '--work-root', str(tmp_path / '없는 폴더')]) == 2
