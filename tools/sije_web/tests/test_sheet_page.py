"""내역서 화면(sije-sheet.html) 시험 — PC 창(1280px)과 휴대폰 창(390px)을 같이 띄우고 같은 가짜 행사를 고친다."""
import io
import time
import uuid

import pymupdf
import pytest

from conftest import fake_event

EMAIL = 'sheet-allowed@example.com'


@pytest.fixture
def event_id(test_db):
    doc_id = 'sheet-' + uuid.uuid4().hex[:8]
    ref = test_db.collection('events').document(doc_id)
    ref.set(fake_event())
    yield doc_id
    for img in ref.collection('images').stream():
        img.reference.delete()
    ref.delete()


def _open(browser, repo_url, token, event_id, **ctx_opts):
    ctx = browser.new_context(**ctx_opts)
    pg = ctx.new_page()
    pg.goto(f'{repo_url}sije-sheet.html?id={event_id}&testToken={token}', wait_until='domcontentloaded')   # 'load' 는 바깥 글꼴까지 기다린다 (기록장 #61)
    pg.locator('#sheet td[data-path="items.L01.qty"]').wait_for(timeout=20_000)
    return ctx, pg


@pytest.fixture
def pc(browser, repo_url, custom_token, event_id):
    ctx, pg = _open(browser, repo_url, custom_token(EMAIL, allowed=True), event_id, viewport={'width': 1280, 'height': 900})
    yield pg
    ctx.close()


@pytest.fixture
def phone(browser, repo_url, custom_token, event_id):
    ctx, pg = _open(browser, repo_url, custom_token(EMAIL, allowed=True), event_id,
                    viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    yield pg
    ctx.close()


def wait_db(ref, check, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        snap = ref.get()
        if check(snap):
            return snap
        time.sleep(0.5)
    raise AssertionError('저장소에 기대한 값이 안 들어왔다')


def wait_text(page, selector, text, ref=None, timeout=5):
    """selector 에 text 가 timeout 초 안에 보여야 한다. 못 보면 15초 더 기다려 '늦게 옴 / 안 옴'과 저장소 값을 알린다
    (2026-10-16: 날짜 시험이 약 35번에 2번 실패, 다시 일으키지 못함 — 다음 실패 때 원인을 가르려고)."""
    loc = page.locator(selector)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if text in loc.inner_text():
            return
        time.sleep(0.1)
    while time.time() - t0 < timeout + 15 and text not in loc.inner_text():
        time.sleep(0.5)
    late = f'{time.time() - t0:.1f}초 뒤에 옴' if text in loc.inner_text() else '20초 안에 안 옴'
    stored = ref.get().to_dict() if ref else None
    raise AssertionError(f'{selector} 에 {text!r} 가 {timeout}초 안에 안 보임 ({late}); 지금 화면 {loc.inner_text()!r}; '
                         f'저장소 {stored and {k: stored.get(k) for k in ("date", "items")} }')


def test_phone_qty_edit_appears_on_pc_without_reload(pc, phone, test_db, event_id):
    box = phone.locator('#quick input[data-path="items.L01.qty"]')
    assert box.input_value() == '5개'
    box.fill('7개')
    box.press('Tab')
    wait_text(pc, '#sheet td[data-path="items.L01.qty"]', '7개', test_db.collection('events').document(event_id))   # 성공 기준 2


def test_phone_date_edit_updates_title_line_on_pc(pc, phone, test_db, event_id):
    box = phone.locator('#quick input[data-path="date"]')
    box.fill('2026-11-14')
    box.press('Tab')
    wait_text(pc, '#sheet .title-date', '2026년 11월 14일 (토) 10시', test_db.collection('events').document(event_id))


def test_title_place_stays_readable_while_editing(pc):
    # 제목 줄은 남색 바탕 · 흰 글씨 — 누르면 공통 편집 규칙이 바탕을 희게 해서 흰 글씨가 사라졌다(2026-10-29 사장님 캡처)
    place = pc.locator('#sheet .title-place')
    place.click()
    color, bg = place.evaluate('e => { const s = getComputedStyle(e); return [s.color, s.backgroundColor]; }')
    assert color != bg, f'글자색 {color} 이 바탕색 {bg} 과 같아 안 보인다'


def test_focused_cells_keep_their_background(pc):
    # 누르면 바탕색이 바뀌지 않고 테두리만 — 제목 줄(남색)도 보통 칸(흰색)도 (사장님 2026-10-29 "어느 칸이든")
    for sel in ['#sheet .title-place', '#sheet td[data-path="setting"]']:
        before = pc.locator(sel).evaluate('e => getComputedStyle(e).backgroundColor')
        pc.click(sel)
        after = pc.locator(sel).evaluate('e => getComputedStyle(e).backgroundColor')
        assert after == before, f'{sel}: 누르니 바탕색이 {before} → {after}'


def test_event_info_has_no_date_row_place_or_sijeil(pc, phone):
    # 행사일 줄 · 장소 · 시제일 칸을 뺐다 (사장님 2026-10-29 — 맨 위 큰 줄의 주소 · 행사일과 겹침, 시제일은 메모로)
    for page in (pc, phone):
        assert page.locator('#sheet td[data-path="place"]').count() == 0
        assert page.locator('#sheet td[data-path="sijeil"]').count() == 0
    labels = pc.locator('#sheet td.lab').all_inner_texts()
    for gone in ('행사일', '장소', '시제일'):
        assert gone not in labels, labels
    for kept in ('상차림', '고객', '담당·차량'):
        assert kept in labels, labels
    assert '행사일' not in phone.locator('#sheet td.lab').all_inner_texts()


def test_title_place_edit_also_saves_place(pc, test_db, event_id):
    # 장소 칸이 없어져도 PDF 이름 · 목록 · 캘린더 · 담당자 지도 링크는 place 를 쓴다 — 맨 위 주소를 고치면 place 도 같은 값
    place = pc.locator('#sheet .title-place')
    place.click()
    pc.keyboard.press('Control+A')
    pc.keyboard.type('가짜동 5-5 새 주소')
    pc.evaluate('document.activeElement.blur()')
    wait_db(test_db.collection('events').document(event_id),
            lambda s: s.get('place') == '가짜동 5-5 새 주소' and s.get('titlePlace') == '가짜동 5-5 새 주소')


def test_digits_only_contact_gets_dashes_on_leave(pc):
    cell = pc.locator('#sheet td[data-path="contacts.0"]')
    cell.click()
    pc.keyboard.press('Control+A')
    pc.keyboard.type('총무 01087455865')
    pc.keyboard.press('Tab')
    wait_text(pc, '#sheet td[data-path="contacts.0"]', '총무 010-8745-5865')


def test_phone_date_edit_updates_own_title_while_next_field_focused(phone):
    box = phone.locator('#quick input[data-path="date"]')
    box.fill('2026-11-14')
    box.press('Tab')   # 시간 칸으로 넘어가 있는 동안에도 휴대폰 자기 화면 맨 위 줄이 바뀌어야 한다
    wait_text(phone, '#sheet .title-date', '2026년 11월 14일 (토) 10시')


def test_offline_phone_edit_and_pc_memo_edit_both_survive(pc, phone, test_db, event_id):
    phone.context.set_offline(True)
    box = phone.locator('#quick input[data-path="items.L02.qty"]')
    box.fill('9개')
    box.press('Tab')
    phone.locator('#save-state', has_text='연결 안 됨').wait_for(timeout=5_000)
    memo = pc.locator('#sheet [data-path="memo"]')
    memo.click()
    pc.keyboard.press('End')
    pc.keyboard.type(' · PC에서 고침')
    pc.evaluate('document.activeElement.blur()')
    ref = test_db.collection('events').document(event_id)
    wait_db(ref, lambda s: 'PC에서 고침' in s.get('memo'))
    phone.context.set_offline(False)
    snap = wait_db(ref, lambda s: s.get('items')['L02']['qty'] == '9개')
    assert 'PC에서 고침' in snap.get('memo')


def test_status_button_moves_event(pc, test_db, event_id):
    pc.click('button[data-set-status="주문없음"]')
    wait_db(test_db.collection('events').document(event_id), lambda s: s.get('status') == '주문없음')
    assert pc.get_attribute('button[data-set-status="주문없음"]', 'aria-pressed') == 'true'


def test_attach_image_shrinks_below_limit(pc, test_db, event_id):
    from PIL import Image
    import random
    random.seed(1)
    img = Image.frombytes('RGB', (2400, 1800), bytes(random.getrandbits(8) for _ in range(2400 * 1800 * 3)))
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=95)
    assert buf.tell() > 3_000_000
    pc.set_input_files('#image-file', files=[{'name': 'big.jpg', 'mimeType': 'image/jpeg', 'buffer': buf.getvalue()}])
    images = test_db.collection('events').document(event_id).collection('images')
    deadline = time.time() + 30
    docs = []
    while not docs and time.time() < deadline:
        docs = list(images.stream())
        time.sleep(0.5)
    assert len(docs) == 1
    assert len(docs[0].get('bytes')) <= 900_000
    pc.locator('#sheet .memo-imgs img').wait_for(timeout=10_000)


def test_leaving_the_page_saves_the_field_being_typed(phone, test_db, event_id):
    """칸에 쓰다가 화면을 끄거나 앱을 바꾸면(칸을 안 떠남) 쓴 글이 사라지면 안 된다 (검토 I7)."""
    box = phone.locator('#quick input[data-path="items.L03.qty"]')
    box.fill('8개')                                       # Tab 없이 — 아직 칸 안에 있음
    phone.evaluate("window.dispatchEvent(new Event('pagehide'))")
    wait_db(test_db.collection('events').document(event_id), lambda s: s.get('items')['L03']['qty'] == '8개')


def test_sheet_too_long_for_a4_shows_a_notice(browser, repo_url, custom_token, test_db):
    """A4 한 장을 넘으면 화면에서 바로 알려 준다 — PDF 실패는 사무실 PC 기록에만 남으므로 (검토 I8)."""
    import uuid
    doc_id = 'sheet-long-' + uuid.uuid4().hex[:6]
    ref = test_db.collection('events').document(doc_id)
    ref.set(fake_event(memo='\n'.join(f'메모 {i}번째 줄' for i in range(1, 81))))
    try:
        ctx, pg = _open(browser, repo_url, custom_token(EMAIL, allowed=True), doc_id, viewport={'width': 1280, 'height': 900})
        pg.locator('#overflow-note', has_text='A4 한 장을 넘습니다').wait_for(timeout=10_000)
        ctx.close()
    finally:
        ref.delete()


def test_print_is_one_page(pc, tmp_path):
    out = tmp_path / 'print.pdf'
    pc.pdf(path=str(out), format='A4', print_background=True)
    with pymupdf.open(out) as doc:
        assert doc.page_count == 1


# ---- 담당자 링크 단추 ----

def _toast_text(page, text, timeout=10_000):
    page.wait_for_function("(t) => { const e = document.getElementById('toast'); return !e.hidden && e.textContent.includes(t); }",
                           arg=text, timeout=timeout)


def test_view_link_copies_same_link_and_keeps_updated_at(pc, test_db, event_id):
    ref = test_db.collection('events').document(event_id)
    before = ref.get().to_dict().get('updatedAt')
    pc.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    pc.locator('#view-link').click()
    _toast_text(pc, '링크를 복사했어요')
    first = pc.evaluate('navigator.clipboard.readText()')
    pc.locator('#view-link').click()
    time.sleep(1)
    second = pc.evaluate('navigator.clipboard.readText()')
    assert first == second
    key = wait_db(ref, lambda s: s.to_dict().get('viewKey')).to_dict()['viewKey']
    assert len(key) == 32
    assert first.splitlines()[1].endswith('sije-view.html#' + key)
    assert ref.get().to_dict().get('updatedAt') == before


def test_view_link_warns_when_not_confirmed(browser, repo_url, custom_token, test_db):
    doc_id = 'sheet-' + uuid.uuid4().hex[:8]
    ref = test_db.collection('events').document(doc_id)
    ref.set(fake_event(status='미확정'))
    ctx = None
    try:
        ctx, pg = _open(browser, repo_url, custom_token(EMAIL, allowed=True), doc_id, viewport={'width': 1280, 'height': 900})
        ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
        pg.locator('#view-link').click()
        _toast_text(pg, '확정이 되어야 담당자에게 보여요')
    finally:
        if ctx:
            ctx.close()
        ref.delete()


def test_view_link_phone_shares_text_only(phone):
    phone.evaluate("() => { window.__shared = []; navigator.share = (d) => { window.__shared.push(Object.keys(d)); return Promise.resolve(); }; }")
    phone.locator('#view-link').click()
    phone.wait_for_function('window.__shared.length > 0', timeout=10_000)
    assert phone.evaluate('window.__shared') == [['text']]


def test_view_link_phone_without_share_copies(phone):
    phone.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    phone.evaluate("() => Object.defineProperty(navigator, 'share', { configurable: true, value: undefined })")
    phone.locator('#view-link').click()
    _toast_text(phone, '링크를 복사했어요')
    assert 'sije-view.html#' in phone.evaluate('navigator.clipboard.readText()')


def test_ensure_view_key_never_overwrites_existing_key(pc, test_db, event_id):
    ref = test_db.collection('events').document(event_id)
    ref.update({'viewKey': 'k' * 32})
    got = pc.evaluate("(id) => import('./js/sije/store.js').then((m) => m.ensureViewKey(id, () => 'x'.repeat(32)))", event_id)
    assert got == 'k' * 32
    assert ref.get().to_dict()['viewKey'] == 'k' * 32


# ---- 휴대폰 단추줄이 내용을 가리지 않는다 (마지막 전체 검토 I2) ----

TOOLBAR_CHECK = """() => {
  window.scrollTo(0, document.documentElement.scrollHeight);
  const tb = document.querySelector('.toolbar').getBoundingClientRect();
  const mk = document.getElementById('make-statement').getBoundingClientRect();
  const t = document.getElementById('toast');
  t.hidden = false; t.textContent = '시험용 알림 글입니다';
  const to = t.getBoundingClientRect();
  const hit = document.elementFromPoint(mk.left + mk.width / 2, mk.bottom - 3);
  const mq = document.getElementById('make-quote').getBoundingClientRect();
  const hitQuote = document.elementFromPoint(mq.left + mq.width / 2, mq.bottom - 3);
  const btns = [...document.querySelectorAll('.toolbar button')].map((b) => {
    const r = document.createRange(); r.selectNodeContents(b);
    return { label: b.textContent, h: Math.round(b.getBoundingClientRect().height), lines: new Set([...r.getClientRects()].map((x) => Math.round(x.top))).size };
  });
  const rows = new Set([...document.querySelectorAll('.toolbar button')].map((b) => Math.round(b.getBoundingClientRect().top))).size;
  return { mkBottom: mk.bottom, tbTop: tb.top, toastBottom: to.bottom, hitId: hit && hit.id, hitQuoteId: hitQuote && hitQuote.id, btns, rows };
}"""


@pytest.mark.parametrize('width', [360, 390])
def test_phone_toolbar_does_not_cover_make_statement_or_toast(browser, repo_url, custom_token, event_id, width):
    ctx, pg = _open(browser, repo_url, custom_token(EMAIL, allowed=True), event_id,
                    viewport={'width': width, 'height': 800}, is_mobile=True, has_touch=True)
    try:
        r = pg.evaluate(TOOLBAR_CHECK)
        assert r['mkBottom'] <= r['tbTop'], r                 # '거래명세서 만들기' 아래 끝이 단추줄 위
        assert r['hitId'] == 'make-statement', r              # 그 단추 아래쪽을 눌러도 다른 단추가 눌리지 않는다
        assert r['hitQuoteId'] == 'make-quote', r             # 옆 '견적서 만들기'도 (알림이 떠 있어도, 2026-10-28)
        assert r['toastBottom'] <= r['tbTop'], r              # 알림이 단추줄을 덮지 않는다
        assert all(b['h'] >= 44 and b['lines'] == 1 for b in r['btns']), r   # 44px 이상, 글자가 두 줄로 접히지 않는다
    finally:
        ctx.close()


def test_view_link_phone_not_allowed_error_asks_to_press_again(phone):
    """m3: 링크를 저장하느라 기다린 사이 크롬의 누름 허락(약 5초)이 지나 share 가 NotAllowedError 로 거절되면, 실패가 아니라 '한 번 더' 안내."""
    phone.evaluate("() => { navigator.share = () => Promise.reject(new DOMException('expired', 'NotAllowedError')); }")
    phone.locator('#view-link').click()
    _toast_text(phone, '링크를 만들었어요 — 한 번 더 눌러 주세요')
    assert '공유하지 못했습니다' not in phone.locator('#toast').inner_text()
