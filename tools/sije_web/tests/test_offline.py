"""인터넷 없을 때 시험 — 한 번 열어 본 목록 · 내역서는 산속(오프라인)에서도 떠야 한다 (Review Focus 2)."""
import time
import uuid

import pytest

from conftest import fake_event

EMAIL = 'offline-allowed@example.com'


@pytest.fixture
def event_id(test_db):
    doc_id = 'offline-' + uuid.uuid4().hex[:8]
    ref = test_db.collection('events').document(doc_id)
    ref.set(fake_event(titlePlace='가짜동 9-9', place='가짜동 9-9 산속'))
    yield doc_id
    ref.delete()


@pytest.fixture
def ctx(browser):
    c = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
    yield c
    c.close()


def wait_controlled(page):
    """서비스 워커가 이 화면을 맡을 때까지 (처음 연 화면은 아직 안 맡는다 → 한 번 다시 연다)."""
    state = ("navigator.serviceWorker.getRegistration().then((r) => r ? [r.installing && r.installing.state, "
             "r.waiting && r.waiting.state, r.active && r.active.state, !!navigator.serviceWorker.controller] : 'none')")
    for _ in range(30):
        if page.evaluate(state)[2:] == ['activated', True]:
            return
        page.wait_for_timeout(500)
    page.reload()
    for _ in range(30):
        if page.evaluate(state)[2:] == ['activated', True]:
            return
        page.wait_for_timeout(500)
    raise AssertionError(f'서비스 워커가 화면을 맡지 않음: {page.evaluate(state)} ({page.url})')


def test_list_and_opened_sheet_load_offline(ctx, repo_url, custom_token, event_id):
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-list.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.locator(f'#rows .row[data-id="{event_id}"]').wait_for(timeout=20_000)
    wait_controlled(page)
    page.goto(f'{repo_url}sije-list.html')
    page.locator(f'#rows .row[data-id="{event_id}"]').wait_for(timeout=20_000)
    page.goto(f'{repo_url}sije-sheet.html?id={event_id}')
    page.locator('#sheet .title-place', has_text='가짜동 9-9').wait_for(timeout=20_000)

    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-list.html')
    page.locator(f'#rows .row[data-id="{event_id}"]', has_text='가짜동 9-9 산속').wait_for(timeout=20_000)
    page.get_by_text('연결 안 됨').first.wait_for(timeout=5_000)
    page.goto(f'{repo_url}sije-sheet.html?id={event_id}')
    page.locator('#sheet .title-place', has_text='가짜동 9-9').wait_for(timeout=20_000)
    page.locator('#save-state', has_text='연결 안 됨').wait_for(timeout=5_000)


QUOTE_SEL = '.brief-row dd span[data-edit]'   # 시제 견적서의 수신 칸


@pytest.fixture
def made(test_db):
    ids = []
    yield ids
    for i in ids:
        test_db.collection('docs').document(i).delete()


def _new_quote(page, made):
    page.click('#doc-new')
    page.wait_for_url('**?id=*', timeout=20_000)
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    doc_id = page.evaluate("new URLSearchParams(location.search).get('id')")
    made.append(doc_id)
    return doc_id


def test_doc_list_and_opened_doc_load_offline(ctx, repo_url, custom_token, made):
    """2단계 서류 — 한 번 연 목록 · 서류는 인터넷 없이도 열린다."""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    doc_id = _new_quote(page, made)
    page.click('#btn-edit')                     # 한 글자라도 적어야 남는다 — 안 고친 새 서류는 떠날 때 지운다 (10-26)
    page.click('.brief-row dd span[data-edit]')
    page.keyboard.press('End')
    page.keyboard.type(' 가짜')
    page.click('#btn-edit')                     # 편집 완료 = 바로 올림
    wait_controlled(page)
    page.goto(f'{repo_url}sije-quote.html')
    page.locator(f'#doc-rows .doc-row[data-id="{doc_id}"]').wait_for(timeout=20_000)
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)

    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-quote.html')
    page.locator(f'#doc-rows .doc-row[data-id="{doc_id}"]').wait_for(timeout=20_000)
    page.locator('#doc-net', has_text='연결 안 됨').wait_for(timeout=5_000)
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    page.locator('#doc-state', has_text='연결 안 됨').wait_for(timeout=5_000)


def test_doc_opens_fast_on_weak_signal(ctx, repo_url, custom_token, made):
    """신호가 약해 저장소가 답을 안 줄 때(끊긴 것은 아님) — 한 번 연 서류는 몇 초 안에 기기 사본으로 뜬다.
    '주인 · 직원' 확인(myRole)을 기다리느라 10초쯤 멈췄다 (일일 일정표 최종 검토 I3)."""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    doc_id = _new_quote(page, made)
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    page.route('https://firestore.googleapis.com/**', lambda route: None)   # 답이 안 온다
    start = time.time()
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    took = time.time() - start
    assert took < 6, f'{took:.1f}초 걸림'
    assert page.evaluate('document.body.dataset.role') == 'owner'   # 지난번 확인한 것으로


def test_new_doc_offline_then_syncs(ctx, repo_url, custom_token, test_db, made):
    """Review Focus 4 — 인터넷 없이 새 서류를 만들고 고쳐도 멈추지 않고, 연결되면 올라간다."""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    wait_controlled(page)
    page.goto(f'{repo_url}sije-quote.html')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)

    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-quote.html')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    doc_id = _new_quote(page, made)
    page.click('#btn-edit')
    page.click(QUOTE_SEL)
    page.keyboard.press('Control+A')
    page.keyboard.type('산속에서 쓴 견적')
    page.click('#btn-edit')
    page.wait_for_timeout(1500)
    ctx.set_offline(False)
    deadline = time.time() + 30
    while time.time() < deadline:
        snap = test_db.collection('docs').document(doc_id).get()
        if snap.exists and '산속에서 쓴 견적' in snap.get('html'):
            return
        time.sleep(1)
    raise AssertionError('연결된 뒤 30초 안에 저장소에 안 올라감')


def test_handoff_offline_then_syncs(ctx, repo_url, custom_token, test_db, made):
    """3단계 Review Focus 5 — 끊긴 곳에서 견적서 → 거래명세서를 만들어도 열리고, 연결되면 올라간다."""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    quote_id = _new_quote(page, made)
    wait_controlled(page)
    page.goto(f'{repo_url}statement.html')                       # 받는 화면도 한 번 열어 둔다 (오프라인 사본)
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    page.goto(f'{repo_url}sije-quote.html?id={quote_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)

    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-quote.html?id={quote_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    page.once('dialog', lambda d: d.accept())
    page.click('#doc-make-statement')
    page.wait_for_url('**/statement.html?id=*', timeout=20_000)
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    st_id = page.evaluate("new URLSearchParams(location.search).get('id')")
    made.append(st_id)
    ctx.set_offline(False)
    deadline = time.time() + 30
    while time.time() < deadline:
        snap = test_db.collection('docs').document(st_id).get()
        if snap.exists and snap.get('label') == '○○ 김씨 문중 종친회':
            return
        time.sleep(1)
    raise AssertionError('연결된 뒤 30초 안에 거래명세서가 저장소에 안 올라감')


def test_handoff_no_signal_then_syncs(ctx, repo_url, custom_token, test_db, made):
    """3단계 검토 I1 — 신호가 아예 없는 곳(navigator.onLine 거짓 — 비행기 모드 · 산속)에서 만든 거래명세서도
    기기에 남았다가 연결되면 올라간다. (set_offline 만으로는 끊긴 채 연 화면이 '연결됨' 이라 이 길을 안 탄다)"""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    quote_id = _new_quote(page, made)
    wait_controlled(page)
    page.goto(f'{repo_url}statement.html')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    page.goto(f'{repo_url}sije-quote.html?id={quote_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)

    page.add_init_script("Object.defineProperty(Navigator.prototype, 'onLine', {get: () => false, configurable: true})")
    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-quote.html?id={quote_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    page.once('dialog', lambda d: d.accept())
    page.click('#doc-make-statement')
    page.wait_for_url('**/statement.html?id=*', timeout=20_000)
    st_id = page.evaluate("new URLSearchParams(location.search).get('id')")
    made.append(st_id)
    # 기기 저장이 끝났는지 — 서류가 열려야 한다 (저장 전에 넘어가면 '찾을 수 없습니다')
    page.wait_for_function("['doc', 'missing'].includes(document.body.dataset.docView)", timeout=20_000)
    assert page.evaluate('document.body.dataset.docView') == 'doc', '신호 없는 곳에서 만든 거래명세서가 기기에 안 남음'
    ctx.set_offline(False)
    page.goto('about:blank')
    page.goto(f'{repo_url}statement.html?id={st_id}')                  # 연결된 화면이 들고 있던 쓰기를 올린다
    deadline = time.time() + 30
    while time.time() < deadline:
        snap = test_db.collection('docs').document(st_id).get()
        if snap.exists and snap.get('label') == '○○ 김씨 문중 종친회':
            return
        time.sleep(1)
    raise AssertionError('연결된 뒤 30초 안에 거래명세서가 저장소에 안 올라감')


def test_list_button_offline_does_not_hang(ctx, repo_url, custom_token, made):
    """끊긴 곳에서 고치고 '목록' 을 눌러도 멈추지 않는다 (끊긴 채 연 화면은 navigator.onLine 이 참으로 나온다)."""
    page = ctx.new_page()
    page.goto(f'{repo_url}sije-quote.html?testToken={custom_token(EMAIL, allowed=True)}')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=20_000)
    doc_id = _new_quote(page, made)
    wait_controlled(page)
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    ctx.set_offline(True)
    page.goto(f'{repo_url}sije-quote.html?id={doc_id}')
    page.wait_for_function("document.body.dataset.docView === 'doc'", timeout=20_000)
    page.click('#btn-edit')
    page.click(QUOTE_SEL)
    page.keyboard.type(' 산속')
    page.click('#btn-list')
    page.wait_for_function("document.body.dataset.docView === 'list'", timeout=10_000)


def test_home_page_offline_copy_unchanged(ctx, repo_url):
    page = ctx.new_page()
    page.goto(repo_url)
    wait_controlled(page)
    page.goto(repo_url)                              # 첫 화면 사본 저장
    page.goto(f'{repo_url}sije-list.html')           # 다른 화면을 열어도 첫 화면 사본 자리를 덮으면 안 된다
    page.locator('#login, #list, #denied').first.wait_for(state='attached', timeout=20_000)
    ctx.set_offline(True)
    page.goto(repo_url)
    assert 'sije-list' not in page.url
    assert page.locator('#rows').count() == 0       # 목록 화면이 아니라
    assert '푸드벨' in page.title()                  # 홈페이지 사본
