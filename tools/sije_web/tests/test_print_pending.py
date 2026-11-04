"""print_pending.py 시험 (기록장 #94) — 순서 · 합치기 · 저장소와 PDF 폴더 대조 · 인쇄 대기열 보기. 프린터 · Acrobat · 파이어베이스 없이."""
import itertools

import pymupdf
import pytest

from conftest import fake_event
from test_printed import FakeDb
from tools.sije_web import fsdb, print_pending
from tools.sije_web.pdf_sync import save_state

KEY = 'x/sije-admin.json'
T1 = '2026-10-29T07:00:00+00:00'


def one_page(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 100), text, fontsize=20)
        doc.save(path)
    return path


def test_time_key_orders_like_a_clock():
    times = ['10시', '9시', '10시30분', '오전 10시', '11', '', '오후 2시', '9시 30분']
    assert sorted(times, key=print_pending.time_key) == ['9시', '9시 30분', '10시', '오전 10시', '10시30분', '11', '오후 2시', '']


@pytest.fixture
def office(tmp_path, monkeypatch):
    """사무실 PC 흉내: 저장소에 인쇄 전 행사 셋 + 인쇄해 합친 것 하나, 상태 기록 · PDF 폴더도 같게."""
    pend = tmp_path / '확정 (인쇄 전)'
    evs = {'b': fake_event(date='2026-11-15', time='9시', updatedAt=T1), 'a': fake_event(date='2026-11-15', time='11시', updatedAt=T1),
           'c': fake_event(date='2026-11-14', time='', updatedAt=T1), 'old': fake_event(updatedAt=T1, printedAt=T1)}
    paths = {i: str(one_page(pend / f'{i}.pdf', f'sheet-{i}')) for i in ('a', 'b', 'c')}
    paths['old'] = str(one_page(tmp_path / '확정' / 'old.pdf', 'sheet-old'))
    save_state(tmp_path / 'state-sije-admin.json', {'paths': paths})
    db = FakeDb(evs)
    monkeypatch.setattr(print_pending, 'STATE_FILE', tmp_path / 'state.json')
    monkeypatch.setattr(fsdb, 'open_db', lambda key: db)
    monkeypatch.setattr(print_pending.tempfile, 'gettempdir', lambda: str(tmp_path / 'temp'))
    (tmp_path / 'temp').mkdir()
    monkeypatch.setattr(print_pending, 'printer_exists', lambda name: True)     # 파워셸을 부르지 않게
    monkeypatch.setattr(print_pending.subprocess, 'Popen', lambda *a, **k: pytest.fail('인쇄를 띄우면 안 된다'))
    return tmp_path, db


def test_pending_sorted_by_date_then_time(office):
    tmp_path, db = office
    from tools.sije_web.pdf_sync import load_state
    rows, why = print_pending.pending(db, load_state(tmp_path / 'state-sije-admin.json'))
    assert why == '' and [i for i, _, _ in rows] == ['c', 'b', 'a']      # 11-14 먼저, 11-15 는 9시 → 11시


def test_pending_stops_when_store_and_folder_differ(office):
    """방금 확정해서 PDF 가 아직 없으면 멈춘다 — 그대로 인쇄하고 '합쳐줘' 하면 안 뽑은 장이 인쇄한 것으로 표시된다."""
    tmp_path, db = office
    from tools.sije_web.pdf_sync import load_state
    db.events['new'] = fake_event(updatedAt=T1)
    rows, why = print_pending.pending(db, load_state(tmp_path / 'state-sije-admin.json'))
    assert rows == [] and '저장소에만 1' in why


def test_merge_pdf_repeats_each_sheet(tmp_path):
    a, b = one_page(tmp_path / 'a.pdf', 'sheet-a'), one_page(tmp_path / 'b.pdf', 'sheet-b')
    out = tmp_path / 'out.pdf'
    assert print_pending.merge_pdf([a, b], 3, out) == 6
    with pymupdf.open(out) as doc:
        assert [p.get_text().strip() for p in doc] == ['sheet-a'] * 3 + ['sheet-b'] * 3


def test_dry_run_counts_pages_prints_nothing_and_removes_temp(office, capsys):
    tmp_path, _ = office
    assert print_pending.main(['--key', KEY, '--dry-run']) == 0
    out = capsys.readouterr().out
    assert '행사 3건 x 3부 = 9쪽' in out and 'dry-run' in out
    assert list((tmp_path / 'temp').iterdir()) == []                      # 손님 정보가 든 합친 파일은 지운다


def test_test_and_rest_split_the_run(office, capsys):
    assert print_pending.main(['--key', KEY, '--dry-run', '--test', '--copies', '2']) == 0
    assert '행사 1건 x 2부 = 2쪽' in capsys.readouterr().out
    assert print_pending.main(['--key', KEY, '--dry-run', '--rest']) == 0
    assert '행사 2건 x 3부 = 6쪽' in capsys.readouterr().out


def test_missing_state_file_stops(office, monkeypatch, capsys):
    tmp_path, _ = office
    monkeypatch.setattr(print_pending, 'STATE_FILE', tmp_path / 'none' / 'state.json')
    assert print_pending.main(['--key', KEY, '--dry-run']) == 2
    assert '상태 기록이 없습니다' in capsys.readouterr().out


def test_refuses_when_acrobat_already_open(office, monkeypatch, capsys):
    """떠 있는 Acrobat 은 새 /t 를 삼킨다 (10-29) — 이 도구가 띄운 것이 아니면 닫지 않고 멈춘다."""
    tmp_path, _ = office
    acrobat = tmp_path / 'Acrobat.exe'
    acrobat.write_bytes(b'')
    monkeypatch.setattr(print_pending, 'acrobat_pids', lambda: {4242})
    assert print_pending.main(['--key', KEY, '--acrobat', str(acrobat)]) == 5
    assert '이미 열려 있습니다' in capsys.readouterr().out
    assert list((tmp_path / 'temp').iterdir()) == []


class FakeProc:
    pid = 777


def fake_queue(monkeypatch, snapshots):
    """jobs() 가 차례로 내놓을 대기열. 첫 번째는 인쇄 전(시작 전에 있던 작업)."""
    feed = iter(snapshots)
    last = []

    def jobs(printer):
        nonlocal last
        last = next(feed, last)
        return last

    closed = []
    monkeypatch.setattr(print_pending, 'jobs', jobs)
    monkeypatch.setattr(print_pending, 'acrobat_pids', lambda: set())
    monkeypatch.setattr(print_pending, 'close_acrobat', lambda pids: closed.append((sorted(pids), last)))
    monkeypatch.setattr(print_pending.subprocess, 'Popen', lambda *a, **k: FakeProc())
    monkeypatch.setattr(print_pending.time, 'sleep', lambda s: None)
    return closed


def test_print_file_waits_for_queue_and_closes_acrobat_after_spooling(monkeypatch, tmp_path):
    other = {'Id': 1, 'TotalPages': 2, 'PagesPrinted': 0, 'Status': 'Printing'}      # 남이 먼저 넣어 둔 작업 — 세지 않는다
    spool = {'Id': 9, 'TotalPages': 4, 'PagesPrinted': 0, 'Status': 'Spooling'}
    run = {'Id': 9, 'TotalPages': 9, 'PagesPrinted': 3, 'Status': 'Printing'}
    closed = fake_queue(monkeypatch, [[other], [other], [other, spool], [other, run], [other]])
    assert print_pending.print_file(tmp_path / 'x.pdf', 'P', tmp_path / 'A.exe', 9) == (True, 9)
    assert closed == [([777], [other, run])]               # 대기열에 다 들어간 뒤(Spooling 이 끝난 뒤) 한 번 닫는다


def test_print_file_reports_a_swallowed_batch(monkeypatch, tmp_path, capsys):
    """10-29: 두 번째 /t 가 떠 있던 Acrobat 에 삼켜져 대기열에 작업이 안 생겼다 — 오류 없이. 이제는 그렇다고 말한다."""
    closed = fake_queue(monkeypatch, [[]])
    clock = itertools.count(0, 10)
    monkeypatch.setattr(print_pending.time, 'time', lambda: next(clock))
    assert print_pending.print_file(tmp_path / 'x.pdf', 'P', tmp_path / 'A.exe', 9) == (False, 0)
    assert '작업을 못 봤습니다' in capsys.readouterr().out and len(closed) == 1     # 그래도 띄운 Acrobat 은 닫는다
