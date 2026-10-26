"""담당자 화면 sije-view.html 시험 - 시험 프로젝트의 staffSheets/{암호} 에 가짜 한 장을 관리자 열쇠로 넣고,
로그인 없는 휴대폰 창으로 sije-view.html#암호 를 연다. 손님 정보는 전부 가짜."""
import time
import urllib.parse
import uuid

import pytest

from tools.sije_web.staff_sheets import staff_view
from conftest import fake_event

MISSING = '지금은 볼 수 없는 내역서예요. 행사 전날부터 당일까지 열려요. 링크가 맞는지 사장님께 여쭤 주세요.'
KAKAO_UA = ('Mozilla/5.0 (Linux; Android 14; SM-S921N Build/UP1A.231005.007; wv) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Version/4.0 Chrome/130.0.0.0 Mobile Safari/537.36;KAKAOTALK 2410550')


def naver(place):
    return 'https://m.map.naver.com/search2/search.naver?query=' + urllib.parse.quote(place, safe='')


@pytest.fixture
def sheets(test_db):
    """put(**fields) -> 새 암호 - 가짜 한 장을 넣고, 끝나면 지운다."""
    made = []

    def put(key=None, **over):
        k = key or 'view-' + uuid.uuid4().hex
        test_db.collection('staffSheets').document(k).set(staff_view(fake_event(**over)))
        made.append(k)
        return k

    yield put
    for k in made:
        test_db.collection('staffSheets').document(k).delete()


@pytest.fixture
def ctx(browser):
    c = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    yield c
    c.close()


@pytest.fixture
def phone(ctx):
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    yield pg
    assert errors == [], errors


def open_view(page, repo_url, key):
    page.goto('about:blank')
    page.goto(f'{repo_url}sije-view.html#{key}')
    page.locator('#sheet').wait_for(state='visible', timeout=20_000)


def hrefs(page, sel):
    return page.eval_on_selector_all(sel, 'els => els.map((a) => a.getAttribute("href"))')


def test_view_shows_sheet(phone, repo_url, sheets):
    key = sheets(extraItems='가짜 추가 기입')
    open_view(phone, repo_url, key)
    text = phone.locator('#sheet').inner_text()
    for s in ('11월 13일 (금)', '10시', '가짜동 1-1 놀이터 위', '7치 1상', '가짜 문중', '010-0000-0000', '600,000원',
              '상차림 60만', '산신제 상은 따로 차린다', '도착하면 먼저 전화', '준비 품목 — 60만원상', '배 5개', '주차는 가짜 마을회관 앞',
              '가짜 추가 기입'):
        assert s in text, s
    assert hrefs(phone, 'a.btn-map') == [naver('가짜동 1-1 놀이터 위')]
    assert phone.locator('img, canvas').count() == 0
    assert '예상' not in text
    assert phone.locator('#status').is_hidden()
    assert phone.locator('table').count() == 0


@pytest.mark.parametrize('kind, heading', [('(60만원상)', '준비 품목 (60만원상)'), ('', '준비 품목')])
def test_view_template_type_heading_rule(phone, repo_url, sheets, kind, heading):
    key = sheets(templateType=kind)
    open_view(phone, repo_url, key)
    assert phone.locator('#sheet h2', has_text='준비 품목').inner_text() == heading


def test_view_contacts_get_call_buttons(phone, repo_url, sheets):
    key = sheets(contacts=['총무 010-0000-0001, 010-0000-0002', '가짜 1234'])
    open_view(phone, repo_url, key)
    assert hrefs(phone, 'a.btn-call') == ['tel:01000000001', 'tel:01000000002']
    assert '총무' in phone.locator('#sheet').inner_text()
    assert '가짜 1234' in phone.locator('#sheet').inner_text()


def test_view_hides_items_heading_when_no_rows(phone, repo_url, sheets, test_db):
    ev = fake_event()
    for it in ev['items'].values():
        it['qty'] = ''
        it['note'] = ''
    key = 'view-' + uuid.uuid4().hex
    test_db.collection('staffSheets').document(key).set(staff_view(ev))
    try:
        open_view(phone, repo_url, key)
        assert '준비 품목' not in phone.locator('#sheet').inner_text()
        assert '가짜 문중' in phone.locator('#sheet').inner_text()
    finally:
        test_db.collection('staffSheets').document(key).delete()


def test_view_missing_key_message(phone, repo_url):
    phone.goto('about:blank')
    phone.goto(f'{repo_url}sije-view.html#' + 'x' * 32)
    phone.locator('#status', has_text=MISSING).wait_for(timeout=20_000)
    assert phone.locator('#sheet').is_hidden()
    phone.goto('about:blank')
    phone.goto(f'{repo_url}sije-view.html')
    phone.locator('#status', has_text=MISSING).wait_for(timeout=20_000)


def test_view_keeps_line_breaks(phone, repo_url, sheets):
    key = sheets(mustDo='가짜 첫째\n가짜 둘째')
    open_view(phone, repo_url, key)
    must = phone.locator('.must')
    assert must.inner_text() == '가짜 첫째\n가짜 둘째'
    a = must.evaluate("""el => { const r = document.createRange(); r.selectNodeContents(el);
        return [...r.getClientRects()].map((x) => Math.round(x.top)); }""")
    assert len(set(a)) >= 2


def test_view_updates_live(phone, repo_url, sheets, test_db):
    key = sheets(memo='가짜 처음 메모')
    open_view(phone, repo_url, key)
    assert '가짜 처음 메모' in phone.locator('#sheet').inner_text()
    test_db.collection('staffSheets').document(key).update({'memo': '가짜 바뀐 메모'})
    phone.locator('#sheet', has_text='가짜 바뀐 메모').wait_for(timeout=20_000)
    assert '가짜 처음 메모' not in phone.locator('#sheet').inner_text()


def test_view_follows_hash_change(phone, repo_url, sheets):
    """카톡 안 브라우저는 두 번째 링크를 같은 탭에서 # 만 바꿔 열기도 한다 - 그때 두 번째 행사가 보여야 한다."""
    a = sheets(memo='가짜 A행사 메모')
    b = sheets(memo='가짜 B행사 메모')
    open_view(phone, repo_url, a)
    assert '가짜 A행사 메모' in phone.locator('#sheet').inner_text()
    phone.evaluate(f"location.hash = '{b}'")
    phone.locator('#sheet', has_text='가짜 B행사 메모').wait_for(timeout=20_000)
    assert '가짜 A행사 메모' not in phone.locator('#sheet').inner_text()


def long_sheet():
    long = '가짜동가짜리산00번지가짜공원묘지가짜관리사무소옆주차장가짜'
    items = {f'L{i:02d}': {'group': f'구분{i // 8}', 'no': str(i), 'name': f'가짜품목{i}번', 'qty': f'{i}개',
                           'note': '가짜비고' * 10 if i == 3 else ''} for i in range(1, 31)}
    return dict(place=long * 2, titlePlace=long, mustDo='\n'.join(f'가짜 지킬 것 {i} ' + long for i in range(1, 6)),
                contacts=[f'가짜담당{i} 010-0000-000{i}' for i in range(5)], memo='가짜메모' * 10, items=items,
                amountDetail='가짜금액' + '1234567890' * 5)


OVERFLOW = """() => [...document.querySelectorAll('body *')]
    .filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 0.5)
    .map((e) => e.tagName + '.' + e.className)"""


@pytest.mark.parametrize('width, zoom', [(360, None), (390, None), (390, '1.3')])
def test_view_fits_phone(browser, repo_url, sheets, width, zoom):
    c = browser.new_context(viewport={'width': width, 'height': 800}, is_mobile=True, has_touch=True)
    try:
        pg = c.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        key = sheets(**long_sheet())
        open_view(pg, repo_url, key)
        if zoom:
            pg.evaluate(f"document.documentElement.style.zoom='{zoom}'")
        cw = pg.evaluate('document.documentElement.clientWidth')
        assert cw == width
        assert pg.evaluate(OVERFLOW) == []
        assert pg.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
        # 대조: 폭 600px 상자를 넣으면 같은 검사가 그 상자를 잡는다
        pg.evaluate("""() => { const d = document.createElement('div'); d.style.width = '600px'; d.textContent = 'x';
            d.id = 'wide'; document.body.append(d); }""")
        assert any('DIV' in o for o in pg.evaluate(OVERFLOW))
        assert pg.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        assert errors == [], errors
    finally:
        c.close()


def test_view_opens_in_kakao_browser(browser, repo_url, sheets):
    c = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, user_agent=KAKAO_UA)
    try:
        pg = c.new_page()
        key = sheets()
        open_view(pg, repo_url, key)
        assert '가짜 문중' in pg.locator('#sheet').inner_text()
    finally:
        c.close()


def _old_share_store():
    """담당자 링크를 만들기 전(BASE c6458ea)의 share-store.js - today.html 을 써 온 직원 폰의 서비스 워커 저장본."""
    import subprocess
    from conftest import ROOT
    return subprocess.run(['git', 'show', 'c6458ea:js/sije/share-store.js'], cwd=ROOT, capture_output=True,
                          check=True).stdout.decode('utf-8')


@pytest.mark.parametrize('cached_copy', ['old', 'new'])
def test_view_opens_on_weak_signal_with_cached_share_store(browser, repo_url, cached_copy):
    """I1: 서비스 워커 저장본에 share-store.js 가 '판 번호 없이' 남아 있고 신호가 약해(3초 넘게 안 옴) 저장본이 대신 나가도,
    담당자 화면이 '불러오는 중…' 에서 멈추지 않는다. old = 옛 사본(watchSheet 없음, 걸려야 하는 경우), new = 대조."""
    from conftest import ROOT
    from test_offline import wait_controlled
    src = _old_share_store() if cached_copy == 'old' else (ROOT / 'js/sije/share-store.js').read_text(encoding='utf-8')
    c = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    try:
        pg = c.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(f'{repo_url}today.html')
        wait_controlled(pg)
        pg.evaluate("""async ([url, src]) => {
            const name = (await caches.keys()).find((k) => k.startsWith('foodbell-'));
            await (await caches.open(name)).put(url, new Response(src, { headers: { 'Content-Type': 'text/javascript' } }));
        }""", [f'{repo_url}js/sije/share-store.js', src])
        slow = {'on': True}

        def delay(route):
            if slow['on']:
                time.sleep(4.5)
            route.continue_()

        c.route('**/js/sije/share-store.js*', delay)
        pg.goto('about:blank')
        pg.goto(f'{repo_url}sije-view.html#' + 'x' * 32)
        pg.locator('#status', has_text=MISSING).wait_for(timeout=30_000)
        slow['on'] = False
        assert errors == [], errors
    finally:
        c.close()
