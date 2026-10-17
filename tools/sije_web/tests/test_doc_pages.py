"""웹 서류 5종 화면 시험 (2단계) — 시험 프로젝트의 docs 에 가짜 서류를 넣거나 화면으로 만들고, 끝나면 지운다.
PC 창(1280px)과 휴대폰 창(390px)을 같이 띄워 같은 서류를 고친다. 손님 정보는 전부 가짜."""
import datetime
import threading
import time
import uuid

import pytest
from google.cloud import firestore

ALLOWED = 'docs-allowed@example.com'
DENIED = 'docs-denied@example.com'

# (종류, 파일, 이름, 목록 제목, 보내기 버튼 글자, 새 서류의 구분값(None = 오늘 작성일), 휴대폰에서 고칠 글자 칸)
PAGES = [
    pytest.param('sije-quote', 'sije-quote.html', '견적서', '시제 견적서', '고객에게 보내기',
                 '○○ 김씨 문중 종친회', '.brief-row dd span[data-edit]', id='sije-quote'),
    pytest.param('event-quote', 'event-quote.html', '견적서', '행사 견적서', '고객에게 보내기',
                 '○○ 단체', '.brief-row dd span[data-edit]', id='event-quote'),
    pytest.param('sije-worksheet', 'sije-worksheet.html', '작업지시서', '시제 작업지시서', '보내기',
                 '무제', '.brief-row:has(dt:text-is("봉행 장소")) dd', id='sije-worksheet'),
    pytest.param('statement', 'statement.html', '거래명세서', '거래명세서', '고객에게 보내기',
                 '○○ 문중 종친회', '[data-k="cust"]', id='statement'),
    pytest.param('staff-pay', 'staff-pay.html', '지급내역서', '알바비 지급내역서', '직원에게 보내기',
                 None, '[data-k="memo"]', id='staff-pay'),
]
PAGE_ARGS = 'kind,file,noun,title,send,label,edit_sel'


def today_kr():
    d = datetime.date.today()
    return f'{d.year}년 {d.month}월 {d.day}일'


@pytest.fixture
def made(test_db):
    """시험이 만든 서류 id 를 모았다가 끝나면 지운다."""
    ids = []
    yield ids
    for i in ids:
        test_db.collection('docs').document(i).delete()


def new_ctx(browser, phone=False):
    opts = dict(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True) if phone \
        else dict(viewport={'width': 1280, 'height': 900})
    ctx = browser.new_context(**opts)
    pg = ctx.new_page()
    pg.errors = []
    pg.on('pageerror', lambda e: pg.errors.append(str(e)))
    return ctx, pg


@pytest.fixture
def pc(browser):
    ctx, pg = new_ctx(browser)
    yield pg
    errors = pg.errors
    ctx.close()
    assert errors == [], errors


@pytest.fixture
def phone(browser):
    ctx, pg = new_ctx(browser, phone=True)
    yield pg
    errors = pg.errors
    ctx.close()
    assert errors == [], errors


def wait_view(page, name, timeout=20_000):
    page.wait_for_function(f'document.body.dataset.docView === {name!r}', timeout=timeout)


def open_list(page, repo_url, file, token):
    page.goto(f'{repo_url}{file}?testToken={token}')
    wait_view(page, 'list')


def open_doc(page, repo_url, file, doc_id, token=None):
    page.goto(f'{repo_url}{file}?id={doc_id}' + (f'&testToken={token}' if token else ''))
    wait_view(page, 'doc')


def new_doc(page, made):
    """목록에서 '새 서류' → 열린 서류의 id."""
    page.click('#doc-new')
    page.wait_for_url('**?id=*', timeout=20_000)
    wait_view(page, 'doc')
    doc_id = page.evaluate("new URLSearchParams(location.search).get('id')")
    made.append(doc_id)
    return doc_id


def wait_db(ref, check, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snap = ref.get()
        if check(snap):
            return snap
        time.sleep(0.5)
    raise AssertionError('저장소에 기대한 값이 안 들어왔다')


def set_text(page, selector, text):
    """편집 중인 칸 하나의 글자를 통째로 바꾼다 (사람이 누르고 지우고 치는 것처럼)."""
    page.click(selector)
    page.keyboard.press('Control+A')
    page.keyboard.type(text)


# ---------- 다섯 종류 공통 ----------

@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_denied_account_sees_no_permission_message(pc, repo_url, custom_token, kind, file, noun, title, send, label,
                                                   edit_sel):
    pc.goto(f'{repo_url}{file}?testToken={custom_token(DENIED, allowed=False)}')
    pc.get_by_text('권한이 없습니다').wait_for(timeout=20_000)
    assert pc.locator('#doc-rows .doc-row').count() == 0
    assert pc.locator('.sheet').is_hidden()


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_icon_opens_list_sorted_by_updated(pc, repo_url, custom_token, test_db, made, kind, file, noun, title, send,
                                           label, edit_sel):
    utc = datetime.timezone.utc
    other = 'statement' if kind != 'statement' else 'sije-quote'
    seeds = {
        'old': dict(kind=kind, html='<p>가짜</p>', label='가짜동 옛 문중', issue='2026년 10월 15일', total='1,000',
                    count='1명', updatedAt=datetime.datetime(2026, 10, 15, 5, tzinfo=utc)),
        'new': dict(kind=kind, html='<p>가짜</p>', label='가짜동 새 문중', issue='2026년 10월 16일', total='2,000',
                    count='2명', updatedAt=datetime.datetime(2026, 10, 16, 5, tzinfo=utc)),
        'other': dict(kind=other, html='<p>가짜</p>', label='다른 종류', issue='', total='',
                      updatedAt=datetime.datetime(2026, 10, 17, 5, tzinfo=utc)),
    }
    ids = {}
    for name, data in seeds.items():
        ids[name] = 'docs-' + uuid.uuid4().hex[:8]
        test_db.collection('docs').document(ids[name]).set(data)
        made.append(ids[name])
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    pc.locator(f'#doc-rows .doc-row[data-id="{ids["old"]}"]').wait_for(timeout=20_000)
    assert pc.inner_text('#doc-list h1') == f'{title} 목록'
    assert pc.inner_text('#doc-new') == f'새 {noun}'
    shown = [i for i in pc.eval_on_selector_all('#doc-rows .doc-row', 'els => els.map(e => e.dataset.id)')
             if i in ids.values()]
    assert shown == [ids['new'], ids['old']]                    # 최근 고친 것이 위, 다른 종류는 없음
    row = pc.inner_text(f'#doc-rows .doc-row[data-id="{ids["new"]}"]')
    assert '2026년 10월 16일' in row and '2,000원' in row and '10월 16일 고침' in row
    assert ('2명' if kind == 'staff-pay' else '가짜동 새 문중') in row


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_new_doc_creates_one_and_opens_it(pc, repo_url, custom_token, test_db, made, kind, file, noun, title, send,
                                          label, edit_sel):
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    snap = wait_db(test_db.collection('docs').document(doc_id), lambda s: s.exists)
    doc = snap.to_dict()
    assert doc['kind'] == kind
    assert doc['label'] == (label or today_kr())
    assert doc['issue'] == ('' if kind == 'sije-worksheet' else today_kr())   # 작업지시서는 발행일 칸이 없다 → 봉행 일시(빈 칸)
    assert len(doc['html']) > 1000 and doc['createdAt'] is not None
    assert pc.locator('.sheet').is_visible()


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_edit_on_phone_appears_on_pc_without_reload(pc, phone, repo_url, custom_token, test_db, made, kind, file, noun,
                                                    title, send, label, edit_sel):
    token = custom_token(ALLOWED, allowed=True)
    open_list(pc, repo_url, file, token)
    doc_id = new_doc(pc, made)
    open_doc(phone, repo_url, file, doc_id, token)
    phone.click('#btn-edit')
    set_text(phone, edit_sel, '가짜동 고친 문중')
    phone.click('#btn-edit')                                    # 편집 완료
    pc.locator(edit_sel, has_text='가짜동 고친 문중').wait_for(timeout=15_000)
    wait_db(test_db.collection('docs').document(doc_id), lambda s: '가짜동 고친 문중' in s.get('html'))


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_toolbar_has_list_instead_of_reset(pc, repo_url, custom_token, made, kind, file, noun, title, send, label,
                                           edit_sel):
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    labels = [t.strip() for t in pc.locator('.toolbar button:visible').all_inner_texts()]
    assert labels == ['편집', '파일로 저장', send, '복사', '인쇄 · PDF', '목록']
    pc.click('#btn-list')
    wait_view(pc, 'list')
    assert 'id=' not in pc.url


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_delete_asks_then_removes_and_returns_to_list(pc, repo_url, custom_token, test_db, made, kind, file, noun,
                                                      title, send, label, edit_sel):
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    ref = test_db.collection('docs').document(doc_id)
    wait_db(ref, lambda s: s.exists)
    asked = []

    def answer(d, ok):
        asked.append(d.message)
        d.accept() if ok else d.dismiss()

    pc.once('dialog', lambda d: answer(d, False))
    pc.click('#doc-del')
    assert asked == [f'정말 지울까요? 지운 {noun}는 되살릴 수 없습니다.']
    assert pc.evaluate('document.body.dataset.docView') == 'doc' and ref.get().exists
    pc.once('dialog', lambda d: answer(d, True))
    pc.click('#doc-del')
    wait_view(pc, 'list')
    wait_db(ref, lambda s: not s.exists)


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_missing_doc_shows_not_found_with_list_button(pc, repo_url, custom_token, kind, file, noun, title, send, label,
                                                      edit_sel):
    pc.goto(f'{repo_url}{file}?id=docs-none-{uuid.uuid4().hex[:6]}&testToken={custom_token(ALLOWED, allowed=True)}')
    wait_view(pc, 'missing')
    assert pc.get_by_text('서류를 찾을 수 없습니다').is_visible()
    pc.click('#doc-back')
    wait_view(pc, 'list')


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_page_works_when_font_and_cdn_servers_never_answer(pc, kind, file, noun, title, send, label, edit_sel,
                                                           repo_url):
    """신호가 약해 글꼴(구글 · jsdelivr) · 사진 만들기 부품(cdnjs)이 안 와도 화면은 떠야 한다 (검토 I1, 1단계 I4 와 같은 종류)."""
    for host in ('**/fonts.googleapis.com/**', '**/fonts.gstatic.com/**', '**/cdn.jsdelivr.net/**',
                 '**/cdnjs.cloudflare.com/**'):
        pc.route(host, lambda route: None)                      # 답을 영영 안 준다
    pc.goto(f'{repo_url}{file}', wait_until='commit')
    pc.get_by_role('button', name='구글로 로그인').wait_for(timeout=8_000)


# ---------- 종류별 합계 ----------

def test_statement_qty_price_updates_total_summary(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, 'statement.html', custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '[data-k="qty"]', '2')
    set_text(pc, '[data-k="price"]', '50000')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('total') == '110,000')   # 100,000 + 세액 10%


def test_worksheet_list_date_is_bonghaeng_ilsi(pc, repo_url, custom_token, test_db, made):
    """작업지시서에는 발행일이 없다 — 목록 날짜 자리에 봉행 일시를 쓴다."""
    open_list(pc, repo_url, 'sije-worksheet.html', custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '.brief-row:has(dt:text-is("봉행 일시")) dd', '2026년 11월 21일 (토) 오전 10시')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('issue') == '2026년 11월 21일 (토) 오전 10시')


def test_staff_pay_row_updates_count_and_total_summary(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '[data-k="pay"]', '150000')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id),
            lambda s: s.get('count') == '1명' and s.get('total') == '150,000')


# ---------- 시제 견적서 ----------

QUOTE = dict(file='sije-quote.html', sel='.brief-row dd span[data-edit]')


def test_supply_updates_total_summary(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '[data-k="supply"]', '1000000')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('total') == '1,100,000')


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_remote_change_shows_at_once_while_editing(pc, repo_url, custom_token, test_db, made, kind, file, noun, title,
                                                   send, label, edit_sel):
    """편집을 켜 둔 채라도 이 기기에 안 올린 글자가 없으면 다른 기기 고침이 바로 보이고, 편집을 이어 할 수 있다
    (사장님 결정 2026-10-17 — 전에는 편집을 끝낼 때까지 기다려서, 켜 둔 채 치면 다른 기기 고침을 덮었다)."""
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    ref = test_db.collection('docs').document(doc_id)
    pc.click('#btn-edit')
    set_text(pc, edit_sel, 'PC 첫 글자')
    html = wait_db(ref, lambda s: 'PC 첫 글자' in s.get('html')).get('html')       # 다 올라갔다
    ref.update({'html': html.replace('PC 첫 글자', '다른기기 고침'), 'updatedAt': firestore.SERVER_TIMESTAMP})
    pc.locator(edit_sel, has_text='다른기기 고침').wait_for(timeout=10_000)
    assert pc.evaluate("document.body.classList.contains('editing')")            # 편집은 켜진 그대로
    set_text(pc, edit_sel, '이어서 고침')                                          # 칸이 다시 고칠 수 있어야 들어간다
    pc.click('#btn-edit')
    wait_db(ref, lambda s: '이어서 고침' in s.get('html') and '다른기기 고침' not in s.get('html'))


def test_remote_change_does_not_erase_text_being_typed(pc, repo_url, custom_token, test_db, made):
    """Review Focus 1 — 한창 치는 중(아직 안 올라간 글자가 있음)에 다른 기기 고침이 와도 치던 글자는 안 지워지고 이 기기 것이 남는다."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    ref = test_db.collection('docs').document(doc_id)
    sel = QUOTE['sel']
    pc.click('#btn-edit')
    set_text(pc, sel, '시작')
    html = wait_db(ref, lambda s: '시작' in s.get('html')).get('html')

    def other_device():
        time.sleep(1.0)
        ref.update({'html': html.replace('시작', '다른기기 고침'), 'updatedAt': firestore.SERVER_TIMESTAMP})

    t = threading.Thread(target=other_device)
    t.start()
    pc.keyboard.type(' 가나다라마바사아자차카타파하', delay=150)   # 0.8초보다 촘촘히 치는 동안 다른 기기 고침이 온다
    t.join()
    pc.click('#btn-edit')
    assert pc.inner_text(sel) == '시작 가나다라마바사아자차카타파하'
    wait_db(ref, lambda s: '시작 가나다라마바사아자차카타파하' in s.get('html') and '다른기기 고침' not in s.get('html'))


def test_edit_done_saves_at_once(pc, repo_url, custom_token, test_db, made):
    """편집 완료를 누르면 모으지 않고 바로 올린다 — 그 0.8초 사이에 다른 기기 고침이 오면 마지막 글자가 사라졌다 (검토 M1)."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    ref = test_db.collection('docs').document(doc_id)
    pc.click('#btn-edit')
    set_text(pc, QUOTE['sel'], '바로 올라갈 글자')
    start = time.time()
    pc.click('#btn-edit')
    wait_db(ref, lambda s: '바로 올라갈 글자' in s.get('html'), timeout=5)
    assert time.time() - start < 0.75, f'{time.time() - start:.2f}초 — 모아 올리기(0.8초)를 기다렸다'


def test_delete_does_not_flash_missing(pc, repo_url, custom_token, test_db, made):
    """지우기를 확인하면 바로 목록으로 — '서류를 찾을 수 없습니다' 가 잠깐도 뜨지 않는다 (검토 M2)."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.exists)
    pc.evaluate("""() => new MutationObserver(() => sessionStorage.setItem('views',
        (sessionStorage.getItem('views') || '') + ' ' + document.body.dataset.docView))
        .observe(document.body, { attributes: true, attributeFilter: ['data-doc-view'] })""")
    pc.once('dialog', lambda d: d.accept())
    pc.click('#doc-del')
    wait_view(pc, 'list')
    assert 'missing' not in (pc.evaluate("sessionStorage.getItem('views')") or '')


def test_typing_then_leaving_page_saves(pc, repo_url, custom_token, test_db, made):
    """Review Focus 2 — 치자마자(모아 올리기 전) 화면을 끄거나 앱을 바꿔도 저장된다.
    화면은 살아 있고 '숨김' 신호만 온다 — 1단계 내역서 시험(test_leaving_the_page_saves_the_field_being_typed)과 같은 방법."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, QUOTE['sel'], '떠나기 직전 글자')
    pc.evaluate("window.dispatchEvent(new Event('pagehide'))")
    wait_db(test_db.collection('docs').document(doc_id), lambda s: '떠나기 직전 글자' in s.get('html'), timeout=5)


def test_typing_then_list_button_saves(pc, repo_url, custom_token, test_db, made):
    """치자마자 '목록' 을 누르면 화면이 바뀌기 전에 올라가야 한다 (페이지가 넘어가면 보내던 것이 끊긴다)."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, QUOTE['sel'], '목록 누르기 직전')
    pc.click('#btn-list')
    wait_view(pc, 'list')
    pc.goto('about:blank')                                      # 목록 화면도 바로 닫는다
    wait_db(test_db.collection('docs').document(doc_id), lambda s: '목록 누르기 직전' in s.get('html'))


def test_old_local_draft_ignored_and_kept(pc, repo_url, custom_token, test_db, made):
    """Review Focus 3 — 기기에 남은 옛 '쓰던 한 장'은 안 섞이고, 지워지지도 않는다."""
    token = custom_token(ALLOWED, allowed=True)
    pc.goto(f'{repo_url}{QUOTE["file"]}')
    pc.evaluate("localStorage.setItem('foodbell-sije-quote-v4', '<p>옛초안글자</p>')")
    open_list(pc, repo_url, QUOTE['file'], token)
    doc_id = new_doc(pc, made)
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: s.exists).get('html')
    assert '옛초안글자' not in html
    assert pc.evaluate("localStorage.getItem('foodbell-sije-quote-v4')") == '<p>옛초안글자</p>'


def test_deleted_elsewhere_shows_missing_and_does_not_recreate(pc, repo_url, custom_token, test_db, made):
    """Review Focus 5 — 열어 둔 서류를 다른 기기에서 지우면 '찾을 수 없습니다', 이 기기 저장이 다시 만들지 않는다."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    ref = test_db.collection('docs').document(doc_id)
    pc.click('#btn-edit')
    set_text(pc, QUOTE['sel'], '지워질 서류')
    wait_db(ref, lambda s: s.exists and '지워질 서류' in s.get('html'))
    pc.keyboard.type(' 마지막')                                 # 올리기 전에 지워진다
    ref.delete()
    wait_view(pc, 'missing', timeout=10_000)
    pc.goto('about:blank')
    time.sleep(5)
    assert not ref.get().exists
