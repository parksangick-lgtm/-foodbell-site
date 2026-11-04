"""printed.py 시험 (기록장 #96) — 상태 기록이 없는 PC 에서 멈추기 · 저장소에서 찾기(--from-store) · 기대 수(--expect). 가짜 저장소로."""
import pytest

from conftest import fake_event
from test_pdf_sync import FakeSource, make_render
from tools.sije_web import fsdb, printed
from tools.sije_web.pdf_sync import save_state, sync_once

KEY = 'x/sije-admin.json'     # 상태 기록 이름이 열쇠 이름(sije-admin)에서 나온다
T0, T1 = '2026-10-24T03:03:00+00:00', '2026-10-29T07:00:00+00:00'


class Doc:
    def __init__(self, id, data):
        self.id, self._data = id, data

    def to_dict(self):
        return dict(self._data)


class FakeDb:
    """관리자 저장소 흉내 — 행사 읽기(stream) · 묶음 쓰기(batch → update → commit)."""

    def __init__(self, events):
        self.events, self.queued, self.committed = events, [], []

    def collection(self, name):
        assert name == 'events'
        return self

    def stream(self):
        return [Doc(i, e) for i, e in self.events.items()]

    def document(self, id):
        return id

    def batch(self):
        return self

    def update(self, id, data):
        self.queued.append((id, data))

    def commit(self):
        self.committed, self.queued = self.committed + self.queued, []


def events():
    return {
        'new': fake_event(updatedAt=T1),                       # 확정 · 인쇄 표시 없음 → 기다림
        'done': fake_event(updatedAt=T0, printedAt=T0),        # 인쇄해 합친 것
        'edited': fake_event(updatedAt=T1, printedAt=T0),      # 인쇄 뒤에 고침 → 기다림
        'maybe': fake_event(status='미확정', updatedAt=T1),
        'nodate': fake_event(date='', updatedAt=T1),           # 날짜 없음 → PDF 가 없어 뺀다
    }


@pytest.fixture
def db(monkeypatch):
    d = FakeDb(events())
    monkeypatch.setattr(fsdb, 'open_db', lambda key: d)
    return d


@pytest.fixture
def state_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(printed, 'STATE_FILE', tmp_path / 'state.json')    # 이 PC 의 상태 기록 자리 (처음엔 비어 있음)
    return tmp_path


def test_missing_state_file_stops_loudly(db, state_dir, capsys):
    """노트북에서 '합칠 것: 0건' 이 '이미 다 합쳤다' 로 읽혔다 (기록장 #96) — 0 대신 멈추고 까닭을 말한다."""
    assert printed.main(['--key', KEY, '--dry-run']) == 2
    out = capsys.readouterr().out
    assert '상태 기록이 없습니다' in out and '--from-store' in out and '0건' not in out
    assert printed.main(['--key', KEY]) == 2 and db.committed == []


def test_from_store_lists_confirmed_not_printed(db, state_dir, capsys):
    assert printed.main(['--key', KEY, '--from-store', '--dry-run']) == 0
    assert capsys.readouterr().out.strip().endswith('합칠 것: 2건') and db.committed == []
    assert sorted(i for i, _ in printed.waiting_in_store(db)) == ['edited', 'new']


def test_from_store_merge_marks_only_waiting(db, state_dir):
    assert printed.main(['--key', KEY, '--from-store', '--expect', '2']) == 0
    assert sorted(i for i, _ in db.committed) == ['edited', 'new']
    assert all(set(data) == {'printedAt', 'updatedAt'} for _, data in db.committed)


def test_expect_mismatch_writes_nothing(db, state_dir, capsys):
    assert printed.main(['--key', KEY, '--from-store', '--expect', '23']) == 3
    assert '--expect 23' in capsys.readouterr().out and db.committed == []


def test_state_mode_with_expect(db, state_dir):
    pend, done = state_dir / '확정 (인쇄 전)' / 'a.pdf', state_dir / '확정' / 'b.pdf'
    save_state(state_dir / 'state-sije-admin.json', {'paths': {'new': str(pend), 'done': str(done)}})
    assert printed.main(['--key', KEY, '--expect', '2']) == 3 and db.committed == []
    assert printed.main(['--key', KEY, '--expect', '1']) == 0
    assert [i for i, _ in db.committed] == ['new']


def test_store_list_matches_office_pdf_folder(tmp_path):
    """--from-store 는 사무실 PC 상태 기록(PDF 가 '확정 (인쇄 전)' 에 있는 행사)과 같은 목록 · 같은 PDF 이름을 낸다."""
    evs = events()
    evs['twin'] = fake_event(updatedAt=T1, place='', time='')          # 이름이 겹쳐 (2) 가 붙는 행사도 같은 이름으로
    evs['twin2'] = fake_event(updatedAt=T1, place='', time='')
    state = {}
    sync_once(FakeSource(evs), tmp_path, state, make_render())
    office = {(i, p.name) for i, p in printed.waiting(state)}
    assert office == set(printed.waiting_in_store(FakeDb(evs)))
    assert len(office) == 4
