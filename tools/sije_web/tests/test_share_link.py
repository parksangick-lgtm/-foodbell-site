"""직원 게시판 관리 도구 시험 — 시험 프로젝트에서 암호를 새로 만들고 바꾼다. 끝나면 쓸 수 있는 게시판 하나를 남긴다
(다른 시험 · 화면이 config/share 의 암호를 쓴다)."""
from tools.sije_web import fsdb, share_link


def test_new_moves_entries_and_removes_old(test_db):
    first = share_link.new_key(test_db)
    board = test_db.collection('share')
    # 통째로 덮어 칸 하나만 — 다른 일정표 시험이 시험 게시판에 남긴 칸이 섞이지 않게 (전체 시험에서 실제로 섞였다)
    board.document(first).set({'entries': {'docmove': {'date': '2026-10-22', 'label': '가짜일'}}})
    second = share_link.new_key(test_db)
    assert len(first) == 32 and len(second) == 32 and first != second
    assert share_link.current_key(test_db) == second
    assert not board.document(first).get().exists                      # 옛 링크는 더 안 열린다
    assert board.document(second).get().get('entries') == {'docmove': {'date': '2026-10-22', 'label': '가짜일'}}
    board.document(second).update({'entries': {}})                      # 다음 시험을 위해 비워 둔다


def test_show_without_board_prints_on_korean_console(monkeypatch):
    """게시판이 아직 없을 때의 안내 — 윈도우 한글 창(cp949)에서 못 찍는 글자(—)가 있으면 도구가 멈췄다 (10-21 실제)."""
    import io
    import sys
    monkeypatch.setattr(share_link.fsdb, 'open_db', lambda key: None)
    monkeypatch.setattr(share_link, 'current_key', lambda db: None)
    raw = io.BytesIO()
    monkeypatch.setattr(sys, 'stdout', io.TextIOWrapper(raw, encoding='cp949'))
    share_link.main(['show', '--key', 'x'])
    sys.stdout.flush()
    assert raw.getvalue().decode('cp949').strip() == '아직 없음 - new 로 만드세요'


def test_show_prints_link(test_db, capsys):
    key = share_link.current_key(test_db) or share_link.new_key(test_db)
    share_link.main(['show', '--key', str(fsdb.KEY_TEST)])
    assert capsys.readouterr().out.strip() == 'https://foodbell.kr/today.html#' + key
