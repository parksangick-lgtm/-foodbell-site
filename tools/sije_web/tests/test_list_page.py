"""행사 목록 화면(sije-list.html) 시험 — 시험 프로젝트에 가짜 행사 4건 · 빈 양식 1개를 넣고, 끝나면 지운다."""
import re
import time
from datetime import date, timedelta

import pytest

from conftest import ROOT, fake_event

ALLOWED = 'list-allowed@example.com'
DENIED = 'list-denied@example.com'


def day(offset):
    """오늘 기준 며칠 뒤(음수면 전)의 'YYYY-MM-DD' — 목록은 오늘 이후를 먼저 · 지난 행사를 아래로 나누므로 고정 날짜를 쓰면 날이 지나며 깨진다."""
    return (date.today() + timedelta(days=offset)).isoformat()


SEEDED = {
    'list-a': fake_event(date=day(19), titlePlace='가짜동 2-2', place='가짜동 2-2 마을 뒷산'),
    'list-b': fake_event(date=day(12)),
    'list-c': fake_event(date=day(0), titlePlace='가짜동 3-3', place='가짜동 3-3 큰길 옆', status='미확정',
                         expectedDate='2026년 11월 2일 (월)', basis='작년 음력 날짜'),
    'list-d': fake_event(date=day(-31), titlePlace='가짜동 4-4', place='가짜동 4-4 옛 터'),   # 지난 행사 (확정)
}
TEMPLATE = {'name': '가짜상', 'items': {'L01': {'group': '과일', 'no': '1', 'name': '배', 'qty': '5개', 'note': ''}}}
BLANK = {'name': '가짜 빈 양식', 'type': '', 'items': {'L01': {'group': '과일', 'no': '1', 'name': '배', 'qty': '', 'note': ''}}}


@pytest.fixture(scope='module', autouse=True)
def seeded(test_db):
    for doc_id, ev in SEEDED.items():
        test_db.collection('events').document(doc_id).set(ev)
    for tpl in (TEMPLATE, BLANK):
        test_db.collection('templates').document(tpl['name']).set(tpl)
    yield
    for doc_id in SEEDED:
        test_db.collection('events').document(doc_id).delete()
    for tpl in (TEMPLATE, BLANK):
        test_db.collection('templates').document(tpl['name']).delete()


def open_list(page, repo_url, token=None):
    page.goto(repo_url + 'sije-list.html' + (f'?testToken={token}' if token else ''))


def seeded_rows(page):
    """화면에 보이는 줄 중 이 시험이 넣은 행사 id 만 (시험 프로젝트에 다른 시험 자료가 있어도 흔들리지 않게)."""
    return [i for i in page.eval_on_selector_all('#rows .row', 'els => els.map(e => e.dataset.id)') if i in SEEDED]


def test_denied_account_sees_no_permission_message(page, repo_url, custom_token):
    open_list(page, repo_url, custom_token(DENIED, allowed=False))
    page.get_by_text('권한이 없습니다').wait_for(timeout=20_000)
    assert page.locator('#rows .row').count() == 0


def seeded_order(page):
    """줄과 '지난 행사' 구분 줄의 순서 — 이 시험이 넣은 행사 id 와 구분 줄 글자만."""
    items = page.eval_on_selector_all('#rows > *', 'els => els.map(e => e.dataset.id || e.textContent)')
    return [i for i in items if i in SEEDED or i == '지난 행사']


def test_allowed_account_sees_confirmed_events_sorted_by_date(page, repo_url, custom_token):
    """오늘 이후는 가까운 순으로 먼저, 지난 행사는 '지난 행사' 구분 줄 아래 (목록 보완 1)."""
    open_list(page, repo_url, custom_token(ALLOWED, allowed=True))
    page.locator('#rows .row[data-id="list-a"]').wait_for(timeout=20_000)
    assert page.get_attribute('button[data-status="확정"]', 'aria-pressed') == 'true'
    assert seeded_rows(page) == ['list-b', 'list-a', 'list-d']
    assert seeded_order(page) == ['list-b', 'list-a', '지난 행사', 'list-d']
    assert page.locator('#rows .past-head').count() == 1
    assert page.eval_on_selector('#rows .past-head', 'e => e.tagName') == 'DIV'   # 구분 줄은 링크가 아니라 누를 수 없다


def test_status_buttons_filter(page, repo_url, custom_token):
    open_list(page, repo_url, custom_token(ALLOWED, allowed=True))
    page.locator('#rows .row[data-id="list-a"]').wait_for(timeout=20_000)
    page.click('button[data-status="미확정"]')
    assert seeded_rows(page) == ['list-c']   # 오늘 날짜는 '다가오는' 쪽
    assert page.locator('#rows .past-head').count() == 0, '지난 행사가 없으면 구분 줄도 없다'
    row = page.locator('#rows .row[data-id="list-c"]').inner_text()
    assert '2026년 11월 2일 (월)' in row and '작년 음력 날짜' in row


def test_search_box_filters_by_place(page, repo_url, custom_token):
    """검색 글상자 — 장소 글자를 치면 그 줄만, 비우면 전부 (목록 보완 2). 서버에 다시 묻지 않고 읽어 온 줄 안에서만."""
    open_list(page, repo_url, custom_token(ALLOWED, allowed=True))
    page.locator('#rows .row[data-id="list-a"]').wait_for(timeout=20_000)
    page.fill('#search', '4-4 옛 터')
    assert seeded_rows(page) == ['list-d']
    page.fill('#search', '마을 뒷산')
    assert seeded_rows(page) == ['list-a']
    page.fill('#search', '')
    assert seeded_rows(page) == ['list-b', 'list-a', 'list-d']
    box = page.locator('#search').bounding_box()
    assert box['height'] >= 44
    assert page.eval_on_selector('#search', 'e => parseFloat(getComputedStyle(e).fontSize)') >= 16


def test_new_event_from_template_opens_sheet(page, repo_url, custom_token, test_db):
    open_list(page, repo_url, custom_token(ALLOWED, allowed=True))
    page.locator('#rows .row[data-id="list-a"]').wait_for(timeout=20_000)
    page.click('#new-event')
    page.get_by_role('button', name=TEMPLATE['name']).click()
    page.wait_for_url(re.compile(r'sije-sheet\.html\?id='), timeout=20_000)
    new_id = page.url.split('id=', 1)[1]
    try:
        doc = test_db.collection('events').document(new_id).get()
        assert doc.exists and doc.get('status') == '미확정' and doc.get('templateType') == TEMPLATE['name']
    finally:
        test_db.collection('events').document(new_id).delete()


def test_blank_template_leaves_header_type_empty(page, repo_url, custom_token, test_db):
    """수량 없는 빈 양식(type '')으로 만들면 내역서 머리글에 양식 이름이 안 붙는다 (사장님 2026-10-26)."""
    open_list(page, repo_url, custom_token(ALLOWED, allowed=True))
    page.locator('#rows .row[data-id="list-a"]').wait_for(timeout=20_000)
    page.click('#new-event')
    page.get_by_role('button', name=BLANK['name']).click()
    page.wait_for_url(re.compile(r'sije-sheet\.html\?id='), timeout=20_000)
    new_id = page.url.split('id=', 1)[1]
    try:
        doc = test_db.collection('events').document(new_id).get()
        assert doc.exists and doc.get('templateType') == '' and doc.get('items')['L01']['qty'] == ''
        page.locator('text=■ 준비 품목').first.wait_for(timeout=20_000)
        assert page.locator('text=■ 준비 품목 —').count() == 0
    finally:
        test_db.collection('events').document(new_id).delete()


def test_page_has_noindex_and_no_home_link(page, repo_url):
    open_list(page, repo_url)
    assert 'noindex' in page.get_attribute('meta[name="robots"]', 'content')
    for f in ('index.html', 'sitemap.xml'):
        assert not re.search(r'sije-(list|sheet|print)', (ROOT / f).read_text(encoding='utf-8')), f


def test_page_works_when_font_server_never_answers(page, repo_url):
    """신호가 약해 글꼴 파일(jsdelivr)이 안 와도 화면은 떠야 한다 — 글꼴이 화면 그리기 · 스크립트를 막으면 안 된다 (검토 I4)."""
    page.route('**/cdn.jsdelivr.net/**', lambda route: None)     # 답을 영영 안 준다
    page.goto(repo_url + 'sije-list.html', wait_until='commit')   # 'load' 는 글꼴을 끝까지 기다리므로 화면만 본다
    page.get_by_role('button', name='구글로 로그인').wait_for(timeout=8_000)


def test_home_screen_app_signs_in_by_redirect_without_popup(page, repo_url):
    """홈 화면 앱(standalone)에서는 팝업이 떠도 결과가 안 돌아오는 일이 많다 — 처음부터 redirect (검토 I2)."""
    hits, opened = [], []
    page.expose_function('noteOpen', lambda: opened.append(1))   # 페이지가 넘어가도 파이썬 쪽에서 센다
    page.add_init_script("""
        window.open = (...a) => { window.noteOpen(); return null; };
        const mm = window.matchMedia.bind(window);
        window.matchMedia = (q) => q.includes('display-mode: standalone')
          ? { matches: true, media: q, addEventListener() {}, removeEventListener() {} } : mm(q);
    """)
    page.route('**/__/auth/handler**', lambda route: (hits.append(route.request.url), route.fulfill(status=200, body='')))
    open_list(page, repo_url)
    page.get_by_role('button', name='구글로 로그인').click()
    deadline = time.time() + 15
    while not hits and time.time() < deadline:
        page.wait_for_timeout(200)
    assert hits, '홈 화면 앱인데 redirect 로그인으로 가지 않았다'
    assert opened == [], '홈 화면 앱에서 팝업을 열려고 했다'


def test_sign_in_falls_back_to_redirect_when_popup_blocked(page, repo_url):
    hits = []
    page.add_init_script('window.open = () => null;')   # 팝업이 막힌 기기 흉내 (홈 화면 앱 등)
    page.route('**/__/auth/handler**', lambda route: (hits.append(route.request.url), route.fulfill(status=200, body='')))
    open_list(page, repo_url)
    page.get_by_role('button', name='구글로 로그인').click()
    deadline = time.time() + 15
    while not hits and time.time() < deadline:
        page.wait_for_timeout(200)
    assert hits, '팝업이 막혔는데 다른 방식(redirect) 로그인으로 넘어가지 않았다'
