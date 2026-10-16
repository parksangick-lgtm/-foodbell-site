"""인터넷 없을 때 시험 — 한 번 열어 본 목록 · 내역서는 산속(오프라인)에서도 떠야 한다 (Review Focus 2)."""
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
