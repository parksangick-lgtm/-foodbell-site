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
