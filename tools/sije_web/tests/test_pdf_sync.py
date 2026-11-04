"""사무실 PC 의 PDF 자동 만들기 시험 — 가짜 저장소 · 가짜 그리기로 (파이어베이스 · 크롬 없이)."""
from pathlib import Path

import pymupdf

from conftest import fake_event
from tools.sije_web.pdf_sync import load_state, pdf_name, save_state, sync_once, target_path, targets


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


def test_pdf_name_empty_place_uses_time():
    """사장님 2026-11-05 (기록장 #95): fileLabel 도 장소도 비면 시간을 붙인다 — 숫자만 있으면('11') '11시'."""
    def name(**kw):
        return pdf_name(fake_event(date='2026-11-15', fileLabel='', **kw))
    assert name(place='', time='11시') == '2026년11월15일 11시 시제행사 내역서.pdf'
    assert name(place='', time='11') == '2026년11월15일 11시 시제행사 내역서.pdf'
    assert name(place='', time='') == '2026년11월15일  시제행사 내역서.pdf'                 # 시간도 없으면 예전 그대로 (겹침은 targets 가)
    assert name(place='가짜동', time='11시') == '2026년11월15일 가짜동 시제행사 내역서.pdf'   # 장소가 있으면 시간을 안 붙인다


def empty(t, time='', **kw):
    """11-15 · fileLabel 도 장소도 빈 새 행사 (기록장 #95 의 모양)."""
    return ev_at(t, date='2026-11-15', fileLabel='', place='', time=time, **kw)


def test_same_date_empty_place_events_get_distinct_names_that_stay(tmp_path):
    """기록장 #95: 같은 날 · 빈 장소 행사가 한 이름을 나눠 써서 5분마다 서로 덮어쓰고 지웠다.
    이제 시간으로 가르고, 그래도 같으면 id 순으로 뒤의 것에 (2) — 고친 순서(updatedAt)가 아니라 id 순."""
    src = FakeSource({'c': empty(1), 'a': empty(2, '10시'), 'b': empty(3, '10시'), 'd': empty(4)})
    render, state = make_render(), {}
    first = sync_once(src, tmp_path, state, render)
    names = sorted(p.name for p in tmp_path.rglob('*.pdf'))
    assert names == sorted(['2026년11월15일 10시 시제행사 내역서.pdf', '2026년11월15일 10시 (2) 시제행사 내역서.pdf',
                            '2026년11월15일  시제행사 내역서.pdf', '2026년11월15일  (2) 시제행사 내역서.pdf'])
    assert {i: Path(p).name for i, p in state['paths'].items()} == {
        'a': '2026년11월15일 10시 시제행사 내역서.pdf', 'b': '2026년11월15일 10시 (2) 시제행사 내역서.pdf',
        'c': '2026년11월15일  시제행사 내역서.pdf', 'd': '2026년11월15일  (2) 시제행사 내역서.pdf'}
    assert first['removed'] == []
    again = sync_once(src, tmp_path, state, render)             # 두 번째 차례: 같은 이름, 다시 그리지도 지우지도 않는다
    assert again['made'] == [] and again['removed'] == []
    assert sorted(p.name for p in tmp_path.rglob('*.pdf')) == names


def test_name_freed_by_another_event_is_taken_over_in_the_same_run(tmp_path):
    """a 가 날짜를 바꾸면 (2) 였던 b 가 그 차례에 바로 제 이름으로 — b 는 안 바뀌었으니 전체를 읽어 b 내용으로 다시 그린다."""
    src = FakeSource({'a': empty(1), 'b': empty(2)})
    render, state = make_render(), {}
    sync_once(src, tmp_path, state, render)
    assert Path(state['paths']['b']).name == '2026년11월15일  (2) 시제행사 내역서.pdf'
    src.events['a'] = ev_at(3, date='2026-11-16', fileLabel='', place='', time='')
    sync_once(src, tmp_path, state, render)
    base = tmp_path / '2026년 PDF (휴대폰용)' / '확정 (인쇄 전)' / '2026년11월15일  시제행사 내역서.pdf'
    assert sorted(p.name for p in tmp_path.rglob('*.pdf')) == ['2026년11월15일  시제행사 내역서.pdf', '2026년11월16일  시제행사 내역서.pdf']
    assert state['paths']['b'] == str(base)
    with pymupdf.open(base) as doc:
        assert 'gajja-2026-11-15' in doc[0].get_text()           # a 의 옛 내용이 아니라 b 내용
    assert sync_once(src, tmp_path, state, render)['made'] == []


def _old_state(tmp_path, src):
    """11-05 고침 전 상태 기록 모양 — 두 행사가 한 PDF 자리를 나눠 쓰고, 이름 목록(names)이 없다."""
    shared = tmp_path / '2026년 PDF (휴대폰용)' / '확정 (인쇄 전)' / '2026년11월15일  시제행사 내역서.pdf'
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b'old')
    state = {'since': max(ev['updatedAt'] for ev in src.events.values()), 'paths': {i: str(shared) for i in src.events},
             'done': {i: ev['updatedAt'] for i, ev in src.events.items()}, 'stale': []}
    return shared, state


def test_old_state_with_shared_name_is_split_and_shared_pdf_removed(tmp_path):
    """옛 공유 자리를 아무도 안 쓰게 되면 프로그램이 스스로(상태 기록 paths 로) 지운다."""
    src = FakeSource({'a': empty(1, '10시'), 'b': empty(2, '11시')})
    shared, state = _old_state(tmp_path, src)
    render = make_render()
    result = sync_once(src, tmp_path, state, render)
    assert sorted(p.name for p in tmp_path.rglob('*.pdf')) == ['2026년11월15일 10시 시제행사 내역서.pdf', '2026년11월15일 11시 시제행사 내역서.pdf']
    assert shared in result['removed'] and len(render.calls) == 2


def test_old_shared_name_kept_by_first_event_is_redrawn(tmp_path):
    """시간도 없으면 id 가 앞선 a 가 옛 자리를 그대로 쓴다 — 거기 든 것이 누구 내용인지 모르니 a 내용으로 다시 그린다."""
    src = FakeSource({'a': empty(1), 'b': empty(2)})
    shared, state = _old_state(tmp_path, src)
    render = make_render()
    result = sync_once(src, tmp_path, state, render)
    assert sorted(p.name for p in tmp_path.rglob('*.pdf')) == ['2026년11월15일  (2) 시제행사 내역서.pdf', '2026년11월15일  시제행사 내역서.pdf']
    assert len(render.calls) == 2 and shared.read_bytes() != b'old' and result['removed'] == []


def test_same_name_in_different_folders_is_not_a_collision(tmp_path):
    t = targets(tmp_path, [('a', empty(1)), ('b', empty(2, status='미확정'))])
    assert t['a'].name == t['b'].name == '2026년11월15일  시제행사 내역서.pdf' and t['a'].parent != t['b'].parent


def test_suffix_skips_a_name_the_owner_already_uses(tmp_path):
    """사장님이 손으로 붙인 ' (2)' 를 다른 행사에 또 주지 않는다."""
    evs = [('a', fake_event(date='2026-11-15', fileLabel=' 가짜동')), ('b', fake_event(date='2026-11-15', fileLabel=' 가짜동')),
           ('c', fake_event(date='2026-11-15', fileLabel=' 가짜동 (2)'))]
    assert {i: p.name for i, p in targets(tmp_path, evs).items()} == {
        'a': '2026년11월15일 가짜동 시제행사 내역서.pdf', 'b': '2026년11월15일 가짜동 (3) 시제행사 내역서.pdf',
        'c': '2026년11월15일 가짜동 (2) 시제행사 내역서.pdf'}


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
