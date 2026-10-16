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
    pg.goto(f'{repo_url}sije-sheet.html?id={event_id}&testToken={token}')
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
