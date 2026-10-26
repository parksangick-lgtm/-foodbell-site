"""사무실 PC 의 PDF 자동 만들기 시험 — 가짜 저장소 · 가짜 그리기로 (파이어베이스 · 크롬 없이)."""
import pymupdf

from conftest import fake_event
from tools.sije_web.pdf_sync import load_state, pdf_name, save_state, sync_once, target_path


class FakeSource:
    def __init__(self, events):
        self.events = events          # {id: ev} — ev['updatedAt'] 는 ISO 글자

    def changed_since(self, since):
        return sorted(((i, ev) for i, ev in self.events.items() if since is None or ev['updatedAt'] > since),
                      key=lambda x: x[1]['updatedAt'])

    def images(self, id):
        return []


def make_render(fail=(), clip=()):
    """가짜 그리기: 한 쪽 PDF 를 만든다. fail 에 든 장소는 처음 한 번 실패, clip 에 든 장소는 가로줄이 글자를 가른다."""
    calls = []

    def render(ev, images, out):
        calls.append(ev['place'])
        if ev['place'] in fail and calls.count(ev['place']) == 1:
            raise RuntimeError('그리기 실패 흉내')
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 100), 'gajja-' + ev['date'], fontsize=20)
        if ev['place'] in clip:
            page.draw_line((60, 94), (400, 94), width=1)      # 글자 한가운데를 지나는 선
        doc.save(out)
        return doc.page_count

    render.calls = calls
    return render


def ev_at(t, **kw):
    return fake_event(updatedAt=f'2026-10-16T0{t}:00:00+00:00', **kw)


def test_pdf_name_uses_file_label_exactly():
    assert pdf_name(fake_event(date='2026-11-01', fileLabel='  가짜면')) == '2026년11월1일  가짜면 시제행사 내역서.pdf'


def test_pdf_name_new_event_uses_place():
    assert pdf_name(fake_event(date='2026-11-13', fileLabel='', place='가짜동 1-1')) == '2026년11월13일 가짜동 1-1 시제행사 내역서.pdf'


def test_target_path_uses_season_folder_and_status(tmp_path):
    # 미확정 행사는 작년 날짜를 들고 있어도 2026년 PDF 폴더에 (지금 PDF 자리 그대로)
    p = target_path(tmp_path, fake_event(date='2025-11-16', status='미확정', fileLabel=' 가짜동'))
    assert p == tmp_path / '2026년 PDF (휴대폰용)' / '미확정' / '2025년11월16일 가짜동 시제행사 내역서.pdf'


def test_confirmed_not_yet_printed_goes_to_pending_folder(tmp_path):
    # 사장님 2026-10-26: 10-24 에 인쇄해 묶은 확정과 섞이지 않게, 그 뒤 확정한 것은 따로
    p = target_path(tmp_path, fake_event(updatedAt='2026-10-26T10:00:00+00:00'))
    assert p.parent.name == '확정 (인쇄 전)'


def test_printed_confirmed_stays_in_confirmed_folder(tmp_path):
    ev = fake_event(updatedAt='2026-10-24T03:03:00+00:00', printedAt='2026-10-24T03:03:00+00:00')
    assert target_path(tmp_path, ev).parent.name == '확정'


def test_confirmed_edited_after_printing_goes_back_to_pending(tmp_path):
    ev = fake_event(updatedAt='2026-10-24T04:27:00+00:00', printedAt='2026-10-24T03:03:00+00:00')
    assert target_path(tmp_path, ev).parent.name == '확정 (인쇄 전)'


def test_printed_mark_compares_store_datetimes(tmp_path):
    """저장소에서는 시각이 글자가 아니라 datetime 으로 온다."""
    import datetime
    t = datetime.datetime(2026, 10, 24, 3, 3, tzinfo=datetime.timezone.utc)
    assert target_path(tmp_path, fake_event(updatedAt=t, printedAt=t)).parent.name == '확정'
    later = t + datetime.timedelta(seconds=1)
    assert target_path(tmp_path, fake_event(updatedAt=later, printedAt=t)).parent.name == '확정 (인쇄 전)'


def test_only_changed_events_are_rendered(tmp_path):
    src = FakeSource({'a': ev_at(1, place='가'), 'b': ev_at(2, place='나')})
    render, state = make_render(), {}
    assert len(sync_once(src, tmp_path, state, render)['made']) == 2      # 처음엔 전부
    src.events['b'] = ev_at(3, place='나', memo='고침')
    result = sync_once(src, tmp_path, state, render)
    assert [p.name for p in result['made']] == [pdf_name(src.events['b'])]
    assert render.calls == ['가', '나', '나']


def test_date_change_removes_old_pdf(tmp_path):
    src = FakeSource({'a': ev_at(1, place='가', fileLabel=' 가')})
    render, state = make_render(), {}
    sync_once(src, tmp_path, state, render)
    src.events['a'] = ev_at(2, place='가', fileLabel=' 가', date='2026-11-14')
    result = sync_once(src, tmp_path, state, render)
    pdfs = list(tmp_path.rglob('*.pdf'))
    assert [p.name for p in pdfs] == ['2026년11월14일 가 시제행사 내역서.pdf']      # Review Focus 5
    assert [p.name for p in result['removed']] == ['2026년11월13일 가 시제행사 내역서.pdf']


def test_status_change_moves_pdf_to_new_folder(tmp_path):
    src = FakeSource({'a': ev_at(1, place='가', status='미확정')})
    render, state = make_render(), {}
    sync_once(src, tmp_path, state, render)
    src.events['a'] = ev_at(2, place='가', status='확정')
    sync_once(src, tmp_path, state, render)
    pdfs = list(tmp_path.rglob('*.pdf'))
    assert len(pdfs) == 1 and pdfs[0].parent.name == '확정 (인쇄 전)'     # 새로 확정 = 아직 인쇄 전


def test_render_failure_is_retried_next_run(tmp_path):
    src = FakeSource({'a': ev_at(1, place='가'), 'b': ev_at(2, place='나')})
    render, state = make_render(fail={'가'}), {}
    first = sync_once(src, tmp_path, state, render)
    assert [i for i, _ in first['failed']] == ['a'] and len(first['made']) == 1
    second = sync_once(src, tmp_path, state, render)
    assert [p.name for p in second['made']] == [pdf_name(src.events['a'])] and second['failed'] == []
    assert render.calls.count('나') == 1        # 이미 만든 것은 다시 안 그린다


def test_clipped_pdf_counts_as_failure(tmp_path):
    src = FakeSource({'a': ev_at(1, place='가')})
    result = sync_once(src, tmp_path, {}, make_render(clip={'가'}))
    assert [i for i, _ in result['failed']] == ['a'] and not list(tmp_path.rglob('*.pdf'))


def test_event_without_date_does_not_block_others(tmp_path):
    """새 행사는 날짜 없이 시작한다 — 그런 행사 하나가 다른 행사 PDF · 다음 차례를 막으면 안 된다 (검토 C1)."""
    src = FakeSource({'new': ev_at(1, place='새', date=''), 'b': ev_at(2, place='나')})
    render, state = make_render(), {}
    result = sync_once(src, tmp_path, state, render)
    assert [p.name for p in result['made']] == [pdf_name(src.events['b'])]
    assert [i for i, _ in result['skipped']] == ['new'] and result['failed'] == []
    assert state['since'] == src.events['b']['updatedAt']          # 다음 차례가 막히지 않는다
    assert sync_once(src, tmp_path, state, render)['made'] == []    # 다시 그리지 않는다


def test_locked_old_pdf_is_removed_on_a_later_run(tmp_path, monkeypatch):
    """옛 PDF 를 누가 열어 두어 못 지우면 그 행사만 미루고, 다음 차례에 지운다 — PDF 가 둘로 남지 않게 (검토 I5)."""
    from pathlib import Path
    src = FakeSource({'a': ev_at(1, place='가', fileLabel=' 가'), 'b': ev_at(2, place='나')})
    render, state = make_render(), {}
    sync_once(src, tmp_path, state, render)
    old = Path(state['paths']['a'])
    src.events['a'] = ev_at(3, place='가', fileLabel=' 가', date='2026-11-14')
    real_unlink = Path.unlink
    def locked(self, *a, **k):
        if self == old:
            raise PermissionError('다른 프로그램이 열어 둠')
        return real_unlink(self, *a, **k)
    monkeypatch.setattr(Path, 'unlink', locked)
    first = sync_once(src, tmp_path, state, render)               # 예외로 끝나지 않는다
    assert old.exists() and len(first['made']) == 1
    monkeypatch.setattr(Path, 'unlink', real_unlink)
    sync_once(src, tmp_path, state, render)
    names = sorted(p.name for p in tmp_path.rglob('*.pdf'))
    assert names == sorted([pdf_name(src.events['a']), pdf_name(src.events['b'])])


def test_locked_target_fails_only_that_event(tmp_path, monkeypatch):
    from pathlib import Path
    src = FakeSource({'a': ev_at(1, place='가'), 'b': ev_at(2, place='나')})
    target_a = str(target_path(tmp_path, src.events['a']))
    real_replace = Path.replace
    def locked(self, target):
        if str(target) == target_a:
            raise PermissionError('열려 있음')
        return real_replace(self, target)
    monkeypatch.setattr(Path, 'replace', locked)
    result = sync_once(src, tmp_path, {}, make_render())
    assert [i for i, _ in result['failed']] == ['a'] and len(result['made']) == 1


class FakeDb:
    """관리자 저장소 흉내 — 묶음(batch)의 update 를 commit 때 FakeSource 행사에 넣는다.
    SERVER_TIMESTAMP 는 저장소처럼 한 번에 같은 새 시각이 된다."""

    def __init__(self, src, now='2026-10-16T09:00:00+00:00'):
        self.src, self.now, self.queued = src, now, []

    def collection(self, name):
        assert name == 'events'
        return self

    def document(self, id):
        return id

    def batch(self):
        return self

    def update(self, id, data):
        self.queued.append((id, data))

    def commit(self):
        for id, data in self.queued:
            self.src.events[id].update({k: self.now for k in data})


def test_merge_moves_printed_pdfs_to_confirmed_on_next_run(tmp_path):
    from tools.sije_web.printed import merge
    src = FakeSource({'a': ev_at(1, place='가'), 'b': ev_at(2, place='나', status='미확정')})
    render, state = make_render(), {}
    sync_once(src, tmp_path, state, render)
    assert sorted(p.parent.name for p in tmp_path.rglob('*.pdf')) == ['미확정', '확정 (인쇄 전)']
    db = FakeDb(src)
    assert merge(db, state) == [pdf_name(src.events['a'])]        # 인쇄 전 폴더에 있던 것만
    assert [id for id, _ in db.queued] == ['a']
    sync_once(src, tmp_path, state, render)
    assert sorted(p.parent.name for p in tmp_path.rglob('*.pdf')) == ['미확정', '확정']


def test_merge_with_nothing_waiting_writes_nothing(tmp_path):
    from tools.sije_web.printed import merge
    db = FakeDb(FakeSource({}))
    assert merge(db, {'paths': {'a': str(tmp_path / '확정' / 'x.pdf')}}) == [] and db.queued == []


def test_state_round_trip(tmp_path):
    state = {'since': '2026-10-16T01:00:00+00:00', 'paths': {'a': 'x.pdf'}, 'done': {'a': '2026-10-16T01:00:00+00:00'}}
    save_state(tmp_path / 's' / 'state.json', state)
    assert load_state(tmp_path / 's' / 'state.json') == state
    assert load_state(tmp_path / 'none.json') == {}
