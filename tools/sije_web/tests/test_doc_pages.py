"""웹 서류 5종 화면 시험 (2단계) — 시험 프로젝트의 docs 에 가짜 서류를 넣거나 화면으로 만들고, 끝나면 지운다.
PC 창(1280px)과 휴대폰 창(390px)을 같이 띄워 같은 서류를 고친다. 손님 정보는 전부 가짜."""
import datetime
import re
import threading
import time
import urllib.parse
import uuid

import pytest
from google.cloud import firestore

ALLOWED = 'docs-allowed@example.com'
DENIED = 'docs-denied@example.com'
VIEWER = 'docs-viewer@example.com'   # 보기 명단(직원) — 일일 일정표만 읽는다

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
    # 일일 일정표 — 새 일정표의 구분값은 내일 날짜(요일)
    pytest.param('daily-schedule', 'daily-schedule.html', '일정표', '일일 일정표', '직원에게 보내기',
                 'TOMORROW', '[data-k="memo"]', id='daily-schedule'),
]
PAGE_ARGS = 'kind,file,noun,title,send,label,edit_sel'


def today_kr():
    d = datetime.date.today()
    return f'{d.year}년 {d.month}월 {d.day}일'


WEEK = '월화수목금토일'


def day_label(d):
    """'2026년 10월 21일 (수)' — 일정표의 날짜(요일)."""
    return f'{d.year}년 {d.month}월 {d.day}일 ({WEEK[d.weekday()]})'


def expected_label(label):
    if label == 'TOMORROW':
        return day_label(datetime.date.today() + datetime.timedelta(days=1))
    return label or today_kr()


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
    """목록에서 '새 서류' → 열린 서류의 id. 일일 일정표가 '같은 날짜 일정표가 이미 있습니다'를 물으면 '그래도 새로 만들기'(확인) —
    시험 프로젝트에 같은 날짜 일정표가 남아 있어도 늘 새 서류를 만든다 (그 물음 자체는 test_daily_new_asks_when_same_date_exists)."""
    def make_anyway(d):
        d.accept()
    page.on('dialog', make_anyway)
    try:
        page.click('#doc-new')
        page.wait_for_url('**?id=*', timeout=20_000)
        wait_view(page, 'doc')
    finally:
        page.remove_listener('dialog', make_anyway)
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


def unfold_if_folded(page, selector):
    """일정표의 장례 칸이 접혀 있으면(10-24 검토 반영) 사람이 하듯 '장례 칸 펼치기'를 먼저 누른다. 다른 서류에는 해당 없음."""
    # Playwright 선택자(:text-is 등)도 받아야 하므로 브라우저 querySelector 가 아니라 locator 로 찾는다
    page.locator(selector).first.evaluate("""(e) => { const td = e.closest('td.meet.folded'); if (td) td.querySelector('.btn-open').click(); }""")


def set_text(page, selector, text):
    """편집 중인 칸 하나의 글자를 통째로 바꾼다 (사람이 누르고 지우고 치는 것처럼)."""
    unfold_if_folded(page, selector)
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
    if kind == 'daily-schedule':                                # 일정표 줄 = 날짜(요일) · 건수 (금액 없음)
        assert '가짜동 새 문중' in row and '2명' in row and '10월 16일 고침' in row
        return
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
    assert doc['label'] == expected_label(label)
    if kind == 'daily-schedule':
        assert doc['issue'] == doc['label']                     # 일정표는 일정 날짜가 곧 발행일 칸
    else:
        assert doc['issue'] == ('' if kind == 'sije-worksheet' else today_kr())   # 작업지시서는 발행일 칸이 없다 → 봉행 일시(빈 칸)
    assert len(doc['html']) > 1000 and doc['createdAt'] is not None
    assert pc.locator('.sheet').is_visible()


@pytest.mark.parametrize(PAGE_ARGS, PAGES)
def test_untouched_new_doc_is_removed_on_list(pc, repo_url, custom_token, test_db, made, kind, file, noun, title, send,
                                              label, edit_sel):
    """'새 서류' 만 누르고 한 글자도 안 고친 채 목록으로 가면 그 빈 서류는 지운다
    (사장님 10-26: 열었다 닫기만 해도 빈 알바비 지급내역서가 목록에 남음)."""
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    ref = test_db.collection('docs').document(new_doc(pc, made))
    wait_db(ref, lambda s: s.exists)
    pc.click('#btn-list')
    wait_view(pc, 'list')
    wait_db(ref, lambda s: not s.exists)


def test_edited_new_doc_is_kept_on_list(pc, repo_url, custom_token, test_db, made):
    """한 글자라도 고쳤으면 목록으로 가도 남는다."""
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    ref = test_db.collection('docs').document(new_doc(pc, made))
    pc.click('#btn-edit')
    set_text(pc, '[data-k="memo"]', '가짜 전달 메모')
    pc.click('#btn-list')
    wait_view(pc, 'list')
    wait_db(ref, lambda s: s.exists and '가짜 전달 메모' in s.get('html'))
    time.sleep(2)
    assert ref.get().exists


def test_untouched_new_doc_is_removed_when_page_closes(pc, repo_url, custom_token, test_db, made):
    """창을 닫아도(목록 단추 없이 떠남) 빈 새 서류는 지운다 — 지우기가 기기에 남았다가 다음에 열 때 올라가도 된다."""
    token = custom_token(ALLOWED, allowed=True)
    open_list(pc, repo_url, 'staff-pay.html', token)
    ref = test_db.collection('docs').document(new_doc(pc, made))
    wait_db(ref, lambda s: s.exists)
    pc.goto('about:blank')                                   # 떠남 (pagehide)
    open_list(pc, repo_url, 'staff-pay.html', token)         # 다음에 목록을 연다
    wait_db(ref, lambda s: not s.exists)


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
def test_row_delete_asks_first(pc, repo_url, custom_token, made, kind, file, noun, title, send, label, edit_sel):
    """줄 ✕ · '줄 삭제' 는 묻고 지운다 — 묻지 않을 때 첫 줄 ✕ 를 두 번 누르면 올라온 아랫줄까지 지워졌다
    (사장님 10-24, 시제견적서 과실 · 조과와 포 · 혜 · 나물이 함께 사라짐). 일일 일정표도 같다 — 처음 고칠 때 빠졌었다(10-24 저녁)."""
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    pc.click('#btn-edit')
    tested = []
    for sel, msg in (('tr.item', '이 항목을 삭제할까요?'), ('.jrow', '이 줄을 삭제할까요?')):
        x = pc.locator(f'{sel} .btn-del')
        if x.count() == 0:
            continue
        rows = pc.locator(sel).count()
        asked = []

        def answer(d, ok):
            asked.append(d.message)
            d.accept() if ok else d.dismiss()

        pc.once('dialog', lambda d: answer(d, False))
        x.first.click()
        assert asked == [msg] and pc.locator(sel).count() == rows          # 아니오 → 그대로
        pc.once('dialog', lambda d: answer(d, True))
        x.first.click()
        assert pc.locator(sel).count() == rows - 1                         # 예 → 한 줄만
        tested.append(sel)
    assert tested[:1] == ['tr.item']      # 음식 구성 줄(.jrow)은 옛 행사견적서 · 작업지시서에만 있어 새 서류에서는 건너뛴다


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


def test_staff_pay_paydate_is_first_and_big(pc, repo_url, custom_token, made):
    """지급일은 서류 맨 위 첫 줄에 크게 — 새 지급내역서는 오늘 날짜(요일)로 채워 둔다 (사장님 2026-10-25)."""
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    assert pc.evaluate("document.querySelector('article.sheet').firstElementChild.className") == 'pay-date'
    assert pc.text_content('[data-k="paydate"]').strip() == day_label(datetime.date.today())
    size = pc.evaluate("""parseFloat(getComputedStyle(document.querySelector('[data-k="paydate"]')).fontSize)""")
    title = pc.evaluate("parseFloat(getComputedStyle(document.querySelector('.doc-title')).fontSize)")
    assert size > title                                    # 제목 '알바비 지급내역서' 보다 크게


def test_staff_pay_add_row_puts_cursor_in_name(phone, repo_url, custom_token, made):
    """'줄 추가' 를 누르면 새 줄의 이름 칸에 커서 — 휴대폰은 이름 칸이 맨 위라, 날짜 칸으로 가면 밑으로 내려갔다 (사장님 2026-10-26)."""
    open_list(phone, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    new_doc(phone, made)
    phone.click('#btn-edit')
    phone.click('tr.addrow button')
    assert phone.evaluate("""(() => { const a = document.activeElement, rows = document.querySelectorAll('tr.item');
        return [a.dataset.f || a.tagName, a.closest('tr.item') === rows[rows.length - 1]]; })()""") == ['name', True]


def pay_fill(page, n):
    """알바비 편집 중: 줄을 n 개로 늘려 가짜 사람으로 채운다 — 일당은 150,000, 마지막 사람만 110,000."""
    while page.evaluate("document.querySelectorAll('tr.item').length") < n:
        page.click('tr.addrow button')
    page.evaluate("""(n) => document.querySelectorAll('tr.item').forEach((tr, i) => {
        const k = String(i + 1).padStart(4, '0');
        const v = { name: '가짜' + (i + 1), tel: '010-0000-' + k, date: '10/31 (금)', event: '가짜시 시제 출장',
                    acct: '가짜은행 000-0000-' + k, pay: i === n - 1 ? '110000' : '150000' };
        for (const [f, t] of Object.entries(v)) {
            const e = tr.querySelector(f === 'pay' ? '[data-k="pay"]' : `[data-f="${f}"]`);
            e.textContent = t;
            e.dispatchEvent(new Event('input', { bubbles: true }));
            e.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
        }
    })""", n)


def test_staff_pay_photo_is_phone_cards(pc, repo_url, custom_token, made, tmp_path):
    """사진은 일일 일정표처럼 휴대폰 카드 묶음 — 폭 1080 · 9:16 안, 첫 장에 제목 · 지급일, 사람마다 카드, 끝에 인원 · 총 지급액.
    상호 · 도장 · 문서번호 · 작성일자는 넣지 않는다 (사장님 2026-10-26 — 휴대폰 폭 그대로 찍은 한 장이 카톡에서 길쭉했다)."""
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    pc.click('#btn-edit')
    pay_fill(pc, 3)
    pc.click('#btn-edit')
    watch_shots(pc, 'root.innerText')
    names, shots, sizes = save_pages(pc, tmp_path)
    assert names == [f'알바비지급내역서_{datetime.date.today():%Y-%m-%d}.png'], names
    assert shots == [[1, 2, 3]], shots
    assert sizes[0][0] == 1080 and sizes[0][1] / sizes[0][0] <= 16 / 9 * 1.03, sizes
    text = pc.evaluate('window.__shots[0]')
    for s in ('푸드벨 알바비 지급내역서', day_label(datetime.date.today()), '1번 · 가짜1 · 150,000원', '010-0000-0001',
              '10/31 (금) 가짜시 시제 출장', '가짜은행 000-0000-0001', '3번 · 가짜3 · 110,000원', '인원 3명', '410,000원', '모두 계좌이체'):
        assert s in text, s
    for s in ('010-5353-3477', '전통 제례', '문서번호', '작성일자'):
        assert s not in text, s


def test_staff_pay_many_people_split_into_pages(phone, repo_url, custom_token, made, tmp_path):
    """열 명이면 사진이 장마다 나뉜다 — 어느 장도 9:16 보다 길지 않고, 한 사람이 두 장에 갈리지 않는다.
    제목은 첫 장에만, 인원 · 총 지급액은 마지막 장에만. 휴대폰에서 보내도 폭 1080 (전에는 휴대폰 폭 그대로 한 장)."""
    open_list(phone, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    new_doc(phone, made)
    phone.click('#btn-edit')
    pay_fill(phone, 10)
    phone.click('#btn-edit')
    watch_shots(phone, 'root.innerText')
    names, shots, sizes = save_pages(phone, tmp_path)
    assert len(names) >= 2 and names[0].endswith('_1.png') and names[1].endswith('_2.png'), names
    assert sum(shots, []) == list(range(1, 11)), shots
    for w, h in sizes:
        assert w == 1080 and h / w <= 16 / 9 * 1.03, sizes
    texts = phone.evaluate('window.__shots')
    assert '푸드벨 알바비 지급내역서' in texts[0] and all('푸드벨 알바비 지급내역서' not in t for t in texts[1:]), texts
    assert '총 지급액 1,460,000원' in texts[-1] and all('총 지급액' not in t for t in texts[:-1]), texts
    assert all(f'{i + 1}/{len(names)}' in t for i, t in enumerate(texts)), texts


# ---------- 시제 견적서 ----------

QUOTE = dict(file='sije-quote.html', sel='.brief-row dd span[data-edit]')


def test_supply_updates_total_summary(pc, repo_url, custom_token, test_db, made):
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '[data-k="supply"]', '1000000')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('total') == '1,100,000')


def quote_photo_size(page, repo_url, token, made, tmp_path, where):
    """새 시제 견적서(양식 그대로)를 열어 '파일로 저장' 사진의 (가로, 세로)."""
    from PIL import Image
    open_list(page, repo_url, QUOTE['file'], token)
    new_doc(page, made)
    page.wait_for_function("typeof html2canvas === 'function'", timeout=20_000)
    page.once('dialog', lambda d: d.accept())                  # 공급가액이 비어 있어도 저장
    with page.expect_download(timeout=60_000) as d:
        page.click('#btn-save-file')
    path = tmp_path / f'{where}.png'
    d.value.save_as(path)
    with Image.open(path) as im:
        return im.size


def test_sije_quote_photo_on_phone_is_paper_like_pc(pc, phone, repo_url, custom_token, made, tmp_path):
    """휴대폰에서 만든 견적서 사진도 PC 와 같은 종이(A4) 모양 한 장 — 전에는 휴대폰 폭 그대로 찍혀
    세로가 가로의 5.6배로 길쭉했다 (사장님 2026-10-26, 안 1 '종이 모양')."""
    w_pc, h_pc = quote_photo_size(pc, repo_url, custom_token(ALLOWED, allowed=True), made, tmp_path, 'pc')
    w_ph, h_ph = quote_photo_size(phone, repo_url, custom_token(ALLOWED, allowed=True), made, tmp_path, 'phone')
    assert h_pc / w_pc < 1.5, (w_pc, h_pc)                     # PC 사진은 원래 종이 모양 (대조)
    assert w_ph == w_pc and abs(h_ph - h_pc) <= 4, ((w_ph, h_ph), (w_pc, h_pc))


def test_tier_fills_rows_by_name_even_after_a_row_is_deleted(pc, repo_url, custom_token, made):
    """수량 단추는 줄 이름으로 채운다 — 윗줄부터 차례로 채우면 지운 줄이 있을 때 한 칸씩 밀렸다
    (사장님 10-24: 탕 3종에 '3개', 적 · 전에 '500g'). 없는 줄은 알림에 적는다."""
    open_list(pc, repo_url, QUOTE['file'], custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    pc.click('#btn-edit')
    pc.once('dialog', lambda d: d.accept())
    pc.locator('tbody[data-group] tr.item .btn-del').first.click()              # 과실 · 조과 지움
    pc.click('.tier-btn[data-tier="basic"]')
    qty = pc.evaluate("""() => Object.fromEntries([...document.querySelector('tbody[data-group]').querySelectorAll('tr.item')]
        .map(r => [r.querySelector('.item-name').textContent.trim(),
                   r.querySelector('td[data-label="수량"] span[data-edit]').textContent.trim()]))""")
    assert qty == {'포 · 혜 · 나물': '500g', '탕 3종': '1식', '적 · 전': '6개', '반 · 갱 · 면': '1'}
    assert '과실 · 조과' in pc.text_content('#toast')


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


# ---------- 보기 명단(직원) — 일일 일정표 계획 Task 2 ----------

def test_viewer_sees_denied_on_other_kinds(pc, repo_url, custom_token):
    pc.goto(f'{repo_url}staff-pay.html?testToken={custom_token(VIEWER, allowed=False, viewer=True)}')
    pc.get_by_text('권한이 없습니다').wait_for(timeout=20_000)
    assert pc.locator('#doc-rows .doc-row').count() == 0


def test_body_role_marks_owner_and_viewer(pc, browser, repo_url, custom_token):
    """화면이 로그인한 사람의 자리를 안다 — 주인(allow)이면 owner, 보기 명단이면 viewer."""
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    pc.wait_for_function("document.body.dataset.role === 'owner'", timeout=10_000)
    ctx, other = new_ctx(browser)
    try:
        other.goto(f'{repo_url}staff-pay.html?testToken={custom_token(VIEWER, allowed=False, viewer=True)}')
        other.wait_for_function("document.body.dataset.role === 'viewer'", timeout=20_000)
    finally:
        ctx.close()


# ---------- 일일 일정표 전용 (계획 Task 3) ----------

DAILY = 'daily-schedule.html'
DEFAULT_MEMO = ('추모공원(협력업체)은 회사에서 출발 전에 전화 · 화장은 시작 5분 후 전화 · 매장은 발인 5분 전에 팀장에게 전화'
                ' · 상주(직접주문)에게는 가게 출발 전에 전화')


def text_of(page, selector):
    return page.locator(selector).first.inner_text().strip()


def daily_new(page, repo_url, token, made):
    open_list(page, repo_url, DAILY, token)
    return new_doc(page, made)


def edit_cell(page, selector, text):
    """편집 중에 칸 하나를 바꾸고 칸을 떠난다 (빈 글자면 지운다)."""
    if text:
        set_text(page, selector, text)
    else:
        unfold_if_folded(page, selector)
        page.click(selector)
        page.keyboard.press('Control+A')
        page.keyboard.press('Backspace')
    page.keyboard.press('Tab')


@pytest.fixture
def no_daily(test_db):
    """시험 프로젝트에 일정표가 하나도 없게 (이어받을 것이 없는 '맨 처음')."""
    for d in test_db.collection('docs').where('kind', '==', 'daily-schedule').stream():
        d.reference.delete()


def test_daily_weekday_follows_date(pc, repo_url, custom_token, test_db, made):
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', '2026년 10월 21일')
    assert text_of(pc, '[data-k="dow"]') == '(수)'
    edit_cell(pc, '[data-k="date"]', '2026년 2월 30일')            # 없는 날
    assert text_of(pc, '[data-k="dow"]') == ''
    edit_cell(pc, '[data-k="date"]', '10월 21일')                  # 연도 없음
    assert text_of(pc, '[data-k="dow"]') == ''
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('label') == '10월 21일')   # 목록 이름은 적힌 그대로


def test_daily_lunar_follows_date(pc, repo_url, custom_token, made):
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', '2026년 10월 21일')
    assert text_of(pc, '[data-k="lunar"]') == '음력 9월 11일'
    edit_cell(pc, '[data-k="date"]', '2026년 2월 30일')
    assert text_of(pc, '[data-k="lunar"]') == ''


def test_daily_fresh_date_rolls_over_year(pc, repo_url, custom_token, made):
    pc.clock.set_fixed_time(datetime.datetime(2026, 12, 31, 20, 0))
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert text_of(pc, '[data-k="date"]') == '2027년 1월 1일'
    assert text_of(pc, '[data-k="dow"]') == '(금)'


def test_daily_first_doc_gets_default_memo(pc, repo_url, custom_token, made, no_daily):
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert text_of(pc, '[data-k="memo"]') == DEFAULT_MEMO
    assert text_of(pc, '[data-k="order"]') == ''


def test_daily_new_doc_inherits_order_and_memo(pc, repo_url, custom_token, test_db, made, no_daily):
    token = custom_token(ALLOWED, allowed=True)
    first = daily_new(pc, repo_url, token, made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="order"]', '가짜일 · 가짜이')
    edit_cell(pc, '[data-k="memo"]', '가짜 메모')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(first), lambda s: '가짜 메모' in s.get('html'))
    pc.click('#btn-list')
    wait_view(pc, 'list')
    pc.locator(f'#doc-rows .doc-row[data-id="{first}"]').wait_for(timeout=15_000)
    new_doc(pc, made)
    assert text_of(pc, '[data-k="order"]') == '가짜일 · 가짜이'
    assert text_of(pc, '[data-k="memo"]') == '가짜 메모'
    assert text_of(pc, '[data-k="date"]') + ' ' + text_of(pc, '[data-k="dow"]') == expected_label('TOMORROW')


def test_daily_amount_from_typed_numbers(pc, repo_url, custom_token, made):
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="people"]', '60명')
    edit_cell(pc, 'tr.item [data-f="price"]', '15,000원')
    assert text_of(pc, 'tr.item [data-k="amt"]') == '60명 × 15,000원 = 900,000원'
    edit_cell(pc, 'tr.item [data-f="price"]', '')
    assert pc.locator('tr.item [data-k="amt"]').first.inner_text().strip() == ''
    assert pc.locator('tr.item [data-k="amt"]').first.is_hidden()


def test_daily_amount_reads_man_and_skips_ranges(pc, repo_url, custom_token, made):
    """설계서: 실제 주문은 단가를 ○만 으로 쓴다. 범위 · 숫자 둘은 금액을 만들지 않는다 (검토 I2)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="people"]', '60명')
    edit_cell(pc, 'tr.item [data-f="price"]', '2만')
    assert text_of(pc, 'tr.item [data-k="amt"]') == '60명 × 20,000원 = 1,200,000원'
    edit_cell(pc, 'tr.item [data-f="people"]', '60~70명')
    assert text_of(pc, 'tr.item [data-k="amt"]') == '20,000원'   # 인원이 애매하면 곱하지 않고 단가만 (사장님 결정 2026-10-20)


def test_daily_bare_number_price_asks_for_unit(pc, repo_url, custom_token, test_db, made):
    """단가 칸에 단위(만 · 천 · 원) 없이 숫자만 적으면 금액을 짐작하지 않는다. 사장님이 '250' · '300' 을 25만 · 30만 뜻으로
    손으로 쳤는데 250원 · 300원으로 읽혀 직원 단톡방 사진에 나갔다(2026-10-21, 실제 값). 화면에는 빨간 글씨로 단위를 적으라고
    알리고, 사진 · 요약 글(옵시디언 사본)에는 넣지 않는다 — 사장님 결정 2026-10-21."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '삼우제')
    amt = pc.locator('tr.item [data-k="amt"]').first
    for bare in ('250', '300', '15000'):
        edit_cell(pc, 'tr.item [data-f="price"]', bare)
        assert amt.inner_text().strip() == '단위를 적어 주세요(예: 25만)', bare
        assert 'warn' in (amt.get_attribute('class') or ''), bare
    edit_cell(pc, 'tr.item [data-f="people"]', '60명')              # 인원이 있어도 곱하지 않는다
    assert amt.inner_text().strip() == '단위를 적어 주세요(예: 25만)'
    # 직원 사진(카드) · 게시판은 rowsData() 의 글자로 만든다 — 거기에는 알림이 없다 (10-24 검토 반영: 사진은 카드, html.shot 없음)
    assert pc.evaluate("window.FoodbellDoc.rowsData().map((r) => r.amt)") == ['']
    pc.click('#btn-edit')
    ref = test_db.collection('docs').document(doc_id)
    wait_db(ref, lambda s: '삼우제' in (s.to_dict() or {}).get('text', ''))
    text = ref.get().to_dict()['text']
    assert '15,000원' not in text and '단위' not in text, text
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="people"]', '')
    edit_cell(pc, 'tr.item [data-f="price"]', '25만')                # 단위를 적으면 전처럼
    assert amt.inner_text().strip() == '250,000원'
    assert 'warn' not in (amt.get_attribute('class') or '')


def test_daily_comma_number_price_is_won(pc, repo_url, custom_token, made):
    """천 단위 쉼표를 찍은 숫자('350,000')는 원이 분명하다 — 사장님이 단가에 '350,000' 을 쳤는데 '단위를 적어 주세요' 가 되어
    사진 · 인쇄에 금액이 빠졌다(2026-10-21 실제 일정표). 쉼표 없는 숫자('250' · '15000')는 전처럼 단위를 묻는다 (대조)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '49재')
    amt = pc.locator('tr.item [data-k="amt"]').first
    for typed, want in (('350,000', '350,000원'), ('1,200,000', '1,200,000원')):
        edit_cell(pc, 'tr.item [data-f="price"]', typed)
        assert amt.inner_text().strip() == want, typed
        assert 'warn' not in (amt.get_attribute('class') or ''), typed
    for typed in ('250', '15000', '35,0000'):                     # 쉼표 없거나 쉼표 자리가 틀리면 단위를 묻는다
        edit_cell(pc, 'tr.item [data-f="price"]', typed)
        assert amt.inner_text().strip() == '단위를 적어 주세요(예: 25만)', typed
    edit_cell(pc, 'tr.item [data-f="people"]', '60명')
    edit_cell(pc, 'tr.item [data-f="price"]', '15,000')
    assert amt.inner_text().strip() == '60명 × 15,000원 = 900,000원'


def test_daily_paste_order_fills_empty_cells_only(pc, repo_url, custom_token, made):
    """'문자 붙여넣기' — 비어 있는 시간 · 단가만 채우고 이미 적힌 연락처는 그대로, 인원은 안 뽑고, 원문은 메모 끝에.
    단가만 있으면 사진의 금액 자리에 단가가 보인다 (사장님 결정 2026-10-20 · 표본 tools/sije_web/js-tests/fixtures/order-samples.json)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="tel"]', '010-0000-9999')
    edit_cell(pc, 'tr.item [data-f="memo"]', '먼저 쓴 메모')
    order = '가짜상조\n가짜팔팀장 입니다 제사상 부탁드립니다\n08시20분 화장\n선산 도착시간\n약 11시\n가격은 35만\n상주 010-0000-0005'
    pc.click('tr.item .btn-paste')
    pc.fill('#paste-text', order)
    pc.click('#paste-ok')
    assert text_of(pc, 'tr.item [data-f="tel"]') == '010-0000-9999'
    assert text_of(pc, 'tr.item [data-f="time"]') == '11시'
    assert text_of(pc, 'tr.item [data-f="price"]') == '350,000원'
    assert text_of(pc, 'tr.item [data-f="people"]') == ''
    memo = pc.locator('tr.item [data-f="memo"]').first.text_content()
    assert memo == '먼저 쓴 메모\n' + order, memo
    pc.click('#btn-edit')
    assert text_of(pc, 'tr.item [data-k="amt"]') == '350,000원'
    assert pc.locator('#paste-dlg').is_hidden()


def test_daily_two_phone_numbers_stay_in_their_cell(pc, repo_url, custom_token, made):
    """연락처 칸은 상주 · 담당자 전화 — 번호 둘이 흔하다. 칸 밖으로 넘치지 않고, 번호 하나가 두 줄로 갈리지 않는다 (검토 I4)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    for f in ('tel', 'lead-tel', 'guide-tel'):
        edit_cell(pc, f'tr.item [data-f="{f}"]', '010-0000-0000, 010-0000-0001')
    pc.click('#btn-edit')
    bad = pc.evaluate(r"""() => [...document.querySelectorAll('tr.item [data-f$="tel"]')].flatMap((e) => {
        const out = [];
        const td = e.closest('td').getBoundingClientRect();
        const all = document.createRange();
        all.selectNodeContents(e);
        if (all.getBoundingClientRect().right > td.right + 0.5) out.push(e.dataset.f + ' 칸 넘침');
        const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
        for (let t; (t = w.nextNode());) {
            for (const m of t.textContent.matchAll(/\d{2,3}-\d{3,4}-\d{4}/g)) {
                const r = document.createRange();
                r.setStart(t, m.index);
                r.setEnd(t, m.index + m[0].length);
                if (new Set([...r.getClientRects()].map((q) => Math.round(q.top))).size > 1) out.push(e.dataset.f + ' 번호 갈림');
            }
        }
        return out;
    })""")
    assert bad == []
    assert text_of(pc, 'tr.item [data-f="lead-tel"]') == '010-0000-0000, 010-0000-0001'   # 글자는 그대로
    saved = pc.evaluate('window.FoodbellDoc.serialize()')
    assert '010-0000-0000, 010-0000-0001' in saved and 'tel1' not in saved                 # 저장은 묶음 표시 없이


def test_daily_phone_numbers_get_dashes(pc, repo_url, custom_token, made):
    """전화번호 칸에 숫자만 치면 칸을 떠날 때 작대기가 들어간다 — 01000001234 → 010-0000-1234 (사장님 2026-10-21).
    지역번호 · 070 · 대표번호도. 전화번호 모양이 아닌 숫자 · 이미 작대기가 있는 번호 · 번호 앞뒤 글자는 그대로."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    cases = [
        ('01000001234', '010-0000-1234'),
        ('0110001234', '011-000-1234'),
        ('0200001234', '02-0000-1234'),
        ('020001234', '02-000-1234'),
        ('03100001234', '031-0000-1234'),
        ('0310001234', '031-000-1234'),
        ('07000001234', '070-0000-1234'),
        ('15880000', '1588-0000'),
        ('상주 01000001234, 01000005678', '상주 010-0000-1234, 010-0000-5678'),
        ('010-0000-1234', '010-0000-1234'),        # 이미 작대기
        ('1234567', '1234567'),                    # 너무 짧다
        ('010000012345', '010000012345'),          # 너무 길다
        ('20261022', '20261022'),                  # 날짜 같은 숫자
    ]
    for typed, want in cases:
        edit_cell(pc, 'tr.item [data-f="tel"]', typed)
        assert text_of(pc, 'tr.item [data-f="tel"]') == want, typed
    for f in ('lead-tel', 'guide-tel'):
        edit_cell(pc, f'tr.item [data-f="{f}"]', '01000002000')
        assert text_of(pc, f'tr.item [data-f="{f}"]') == '010-0000-2000', f
    edit_cell(pc, 'tr.item [data-f="place"]', '01000003000')      # 전화번호 칸이 아니면 그대로
    assert text_of(pc, 'tr.item [data-f="place"]') == '01000003000'
    set_text(pc, 'tr.item [data-f="tel"]', '01000009999')        # 칸을 안 떠나고 바로 '편집 완료'
    pc.click('#btn-edit')
    assert text_of(pc, 'tr.item [data-f="tel"]') == '010-0000-9999'


def stub_share(page, cancel=False):
    """휴대폰 공유창 대신 넘긴 것(사진 수 · 글)을 모은다 — 시험 브라우저에는 카톡 공유창이 없다. cancel 이면 사장님이 공유창을 닫은 것."""
    page.evaluate("""(cancel) => {
        window.__shared = [];
        Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
        Object.defineProperty(navigator, 'share', { configurable: true, value: (d) => {
            window.__shared.push({ files: (d.files || []).length, text: d.text });
            return cancel ? Promise.reject(new DOMException('닫음', 'AbortError')) : Promise.resolve();
        } });
    }""", cancel)


def shared(page, n):
    page.wait_for_function(f'window.__shared.length >= {n}', timeout=60_000)
    return page.evaluate(f'window.__shared[{n - 1}]')


PHOTO_TEXT = '푸드벨 일일 일정표 (2026년 10월 22일 (목))\nhttps://foodbell.kr/daily-schedule.html'


def fill_phone_numbers(page):
    """세 줄 일정 — 1번 줄은 연락처 · 팀장, 2번 줄은 번호 없음, 3번 줄은 연락처 둘 · 안내 (편집 중에 부른다)."""
    page.click('tr.addrow button')
    page.click('tr.addrow button')
    edit_cell(page, 'tr.item:nth-child(1) [data-f="tel"]', '01000001234')     # 작대기 없이 친 번호도
    edit_cell(page, 'tr.item:nth-child(1) [data-f="lead-tel"]', '010-0000-2000')
    edit_cell(page, 'tr.item:nth-child(3) [data-f="tel"]', '010-0000-3000, 010-0000-3001')
    edit_cell(page, 'tr.item:nth-child(3) [data-f="guide-tel"]', '02-000-4000')


def test_daily_send_has_no_second_window(phone, repo_url, custom_token, made):
    """사진만 보낸다 — 전화 · 지도는 단톡방 공지의 고정 링크(today.html)가 맡아서 사진 뒤 두 번째 창은 없다
    (사장님 2026-10-21: 매일 두 번 보내기가 불편). 번호가 있는 일정이어도 공유는 한 번."""
    daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    stub_share(phone)
    phone.click('#btn-edit')
    edit_cell(phone, '[data-k="date"]', '2026년 10월 22일')
    fill_phone_numbers(phone)
    phone.click('#btn-send')
    photos = shared(phone, 1)
    assert photos['files'] >= 1 and photos['text'] == PHOTO_TEXT
    phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=10_000)
    phone.wait_for_timeout(800)
    assert phone.evaluate('window.__shared.length') == 1
    assert phone.locator('#call-dlg').count() == 0


def test_daily_pc_send_has_no_second_window(pc, repo_url, custom_token, made):
    """PC: 사진을 클립보드에 넣고 끝 — 링크를 복사하라는 두 번째 창은 없다."""
    pc.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', '2026년 10월 22일')
    fill_phone_numbers(pc)
    # 시험 브라우저의 사진 복사는 될 때도 안 될 때도 있다 — '사진 복사됨' 으로 정해 둔다
    pc.evaluate("() => Object.defineProperty(navigator.clipboard, 'write', { configurable: true, value: () => Promise.resolve() })")
    pc.click('#btn-send')
    pc.get_by_text('일정표 사진을 복사했습니다').wait_for(timeout=60_000)
    assert pc.locator('#call-dlg').count() == 0


def test_daily_cancelled_send_resets_button(phone, repo_url, custom_token, made):
    """사장님이 사진 공유창을 닫으면(안 보냄) 버튼이 원래대로 돌아온다."""
    daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    stub_share(phone, cancel=True)
    phone.click('#btn-edit')
    fill_phone_numbers(phone)
    phone.click('#btn-send')
    shared(phone, 1)
    phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=10_000)


def test_daily_files_are_named_by_date(pc, repo_url, custom_token, made):
    """파일 이름은 일정표 날짜만 — 2026-10-22.png, 인쇄 · PDF 저장 창도 2026-10-22 (사장님 2026-10-21 '일일 일정표는 없어도 돼')."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', '2026년 10월 22일')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜동 상차림')
    pc.click('#btn-edit')
    pc.wait_for_function("typeof html2canvas === 'function'", timeout=20_000)
    with pc.expect_download(timeout=60_000) as d:
        pc.click('#btn-save-file')
    assert d.value.suggested_filename == '2026-10-22.png'
    pc.evaluate("() => { window.__titles = []; window.print = () => window.__titles.push(document.title); }")
    pc.click('#btn-print')
    assert pc.evaluate('window.__titles') == ['2026-10-22']


def test_daily_funeral_hall_and_times(pc, phone, repo_url, custom_token, test_db, made):
    """팀장 칸에 장례식장(화장장) · 발인 시간 · 화장 시간 (사장님 2026-10-21). 빈 것은 보기 · 사진에서 '발인' 글자까지 숨기고,
    요약 글(옵시디언 사본)에도 들어간다. 휴대폰 카드는 팀장 · 안내인이 비어도 장례식장 · 화장이 있으면 칸을 보여 준다."""
    token = custom_token(ALLOWED, allowed=True)
    doc_id = daily_new(pc, repo_url, token, made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜동 평토상')
    pc.click('tr.item td.meet button.btn-open')                    # 장례 칸은 접혀 있다 — 사람도 먼저 편다 (10-24 검토 반영)
    edit_cell(pc, 'tr.item [data-f="hall"]', '가짜병원장례식장')
    edit_cell(pc, 'tr.item [data-f="cremate"]', '08시20분')
    pc.click('#btn-edit')
    assert text_of(pc, 'tr.item [data-f="hall"]') == '가짜병원장례식장'
    assert pc.locator('tr.item .rite:has([data-f="depart"])').first.is_hidden()       # 비면 '발인' 글자도 숨김
    assert text_of(pc, 'tr.item .rite:has([data-f="cremate"])') == '화장 08시20분'
    ref = test_db.collection('docs').document(doc_id)
    wait_db(ref, lambda s: '화장 08시20분' in (s.to_dict() or {}).get('text', ''))
    assert '가짜병원장례식장 · 화장 08시20분' in ref.get().to_dict()['text']
    open_doc(phone, repo_url, DAILY, doc_id, token)
    phone.locator('tr.item [data-f="hall"]', has_text='가짜병원').wait_for(timeout=15_000)
    assert phone.locator('tr.item td.meet').first.is_visible()
    pc.click('#btn-edit')                                          # 다 비우면 발인 · 화장 줄도 숨김 (대조)
    edit_cell(pc, 'tr.item [data-f="hall"]', '')
    edit_cell(pc, 'tr.item [data-f="cremate"]', '')
    pc.click('#btn-edit')
    assert pc.locator('tr.item .rites').first.is_hidden()


def test_daily_paste_fills_funeral_times(pc, repo_url, custom_token, made):
    """문자 붙여넣기 — 주문 글의 발인 · 화장 시간도 빈 칸에 (실제 표본 '장례식장 — 발인 · 화장 시간뿐', 이름은 가짜)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    order = ('■ 장례식장: 가짜병원장례식장\n■고인: 가짜십\n■ 내일발인: 10월 12일 05시30분\n■ 1차장지: 가짜추모공원 07시20분 화장\n'
             '■ 2차장지: 가짜추모의집\n■  식사100인분  평토상 35만원 부탁드립니다 (한분)')
    pc.click('tr.item .btn-paste')
    pc.fill('#paste-text', order)
    pc.click('#paste-ok')
    assert text_of(pc, 'tr.item [data-f="depart"]') == '05시30분'
    assert text_of(pc, 'tr.item [data-f="cremate"]') == '07시20분'
    assert text_of(pc, 'tr.item [data-f="time"]') == ''            # 발인 · 화장은 상차림 시간이 아니다
    assert text_of(pc, 'tr.item [data-f="hall"]') == ''            # 장례식장 이름은 읽지 않는다 (손으로)


def test_call_page_shows_nothing_for_a_bad_link(phone, repo_url):
    """'전화 · 지도' 화면 — 링크가 잘렸거나 이상하면 버튼을 만들지 않는다 (엉뚱한 번호로 걸지 않게)."""
    for tail in ('', '#', '#abc', '#20261022-9x01000001234-1c123-1c010000012345', '#1p', '#1p%E0%A4%A'):
        phone.goto('about:blank')
        phone.goto(f'{repo_url}call.html{tail}')
        assert phone.locator('a.call').count() == 0, tail
        assert text_of(phone, '#hint') == '번호 · 장소가 없습니다. 일정표 사진을 확인해 주세요.', tail
    phone.goto('about:blank')
    phone.goto(f'{repo_url}call.html#1c01000001234')               # 날짜가 없어도 번호는 보인다 (대조)
    assert phone.locator('a.call').count() == 1
    assert text_of(phone, 'h1') == '전화 · 지도'


def test_daily_table_headers_fit_their_columns(pc, repo_url, custom_token, made):
    """표 머리줄이 칸을 넘치면 사진에서는 잘린다('상조팀장 · 현지 안'). 최종 검토 I1 을 고친 뒤 사진을 보다 찾음."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    over = pc.evaluate("""() => [...document.querySelectorAll('table.day-table thead th')]
        .filter((th) => th.scrollWidth > th.clientWidth + 1).map((th) => th.textContent.trim())""")
    assert over == []


def test_daily_counts_filled_rows_only(pc, repo_url, custom_token, test_db, made):
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    pc.click('tr.addrow button')
    pc.click('tr.addrow button')
    rows = pc.locator('tr.item')
    assert rows.count() == 3
    edit_cell(pc, 'tr.item:nth-child(1) [data-f="work"]', '가짜동 상차림')
    edit_cell(pc, 'tr.item:nth-child(3) [data-f="time"]', '오전 9:00')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.get('count') == '2건')


def test_daily_long_text_fits_phone(pc, phone, repo_url, custom_token, made):
    token = custom_token(ALLOWED, allowed=True)
    doc_id = daily_new(pc, repo_url, token, made)
    pc.click('#btn-edit')
    long = '가짜동가짜리산00번지가짜공원묘지가짜관리사무소옆주차장'
    edit_cell(pc, 'tr.item [data-f="place"]', long)
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜씨종중시사상차림' * 3)
    edit_cell(pc, 'tr.item [data-f="tel"]', '010-0000-0000, 010-0000-0001')
    pc.click('#btn-edit')
    open_doc(phone, repo_url, DAILY, doc_id, token)
    phone.locator('tr.item [data-f="place"]', has_text=long[:6]).wait_for(timeout=15_000)
    assert phone.evaluate('document.documentElement.clientWidth') == 390
    assert phone.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')


def save_pages(page, out_dir):
    """'파일로 저장' → (사진 이름들, 장마다 보인 줄 번호, 사진 크기들). 줄 번호는 사진을 찍는 사본(html2canvas)에서 읽는다 —
    줄이 두 장에 갈리거나 빠지면 번호가 겹치거나 빈다."""
    from PIL import Image
    page.wait_for_function("typeof html2canvas === 'function'", timeout=20_000)
    page.evaluate("""() => {
        const orig = window.html2canvas;
        window.__shotRows = [];
        window.html2canvas = (el, o) => orig(el, { ...o, onclone: async (doc, ref) => {
            if (o && o.onclone) await o.onclone(doc, ref);
            const root = ref || doc.querySelector('.shot-cards');   // 사진 = 휴대폰 카드 묶음 (10-24 검토 반영)
            window.__shotRows.push([...root.querySelectorAll('article.card:not([data-shot-hide])')].map((c) => +c.dataset.no));
        } });
    }""")
    files = []
    page.on('download', lambda d: files.append(d))
    page.click('#btn-save-file')
    deadline, last = time.time() + 90, None
    while time.time() < deadline:                                  # 장 수를 모르니 사진 · 기록이 같아지고 멈출 때까지
        page.wait_for_timeout(1500)
        now = (page.evaluate('window.__shotRows.length'), len(files))
        if now[0] and now[0] == now[1] and now == last:
            break
        last = now
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = []
    files.sort(key=lambda d: int((re.search(r'_(\d+)[.]png$', d.suggested_filename) or [0, 0])[1]))   # _2 가 _10 보다 앞
    for d in files:
        d.save_as(out_dir / d.suggested_filename)
        sizes.append(Image.open(out_dir / d.suggested_filename).size)
    return [d.suggested_filename for d in files], page.evaluate('window.__shotRows'), sizes


def test_daily_fifteen_rows_split_into_pages(pc, browser, repo_url, custom_token, made, tmp_path):
    """하루 15건(밴드에 실제로 있었던 최대) — 사진이 장마다 나뉘고, 어느 장도 A4 비율보다 길지 않다(줄이 잘리지 않음).
    휴대폰에서 보내도 PC 와 같은 종이(표) 모양 · 같은 장 나눔 (최종 검토 I1 — 휴대폰은 일 하나마다 사진 한 장이었다)."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    for _ in range(14):
        pc.click('tr.addrow button')
    # 밴드 일정처럼 줄마다 칸을 다 채운다 (두 칸만 채우면 15줄이 PC 폭 A4 한 장에 들어가 나눌 일이 없다)
    pc.evaluate("""() => {
        const v = { staff: '가짜일 · 가짜이', car: '1톤 탑차', time: '오전 11:00', place: '가짜군 가짜면 가짜리 산 00',
                    tel: '010-0000-0000', work: '가짜씨 종중 시사 상차림', people: '60명', price: '15,000원',
                    lead: '가짜팀장', 'lead-tel': '010-0000-1000', 'guide-tel': '010-0000-2000', memo: '가짜 메모' };
        document.querySelectorAll('tr.item').forEach((tr, i) => {
            for (const [f, t] of Object.entries(v)) {
                tr.querySelector(`[data-f="${f}"]`).textContent = f === 'work' ? `${t} ${i + 1}` : t;
            }
        });
        document.querySelector('tr.item [data-f="work"]').dispatchEvent(new Event('input', { bubbles: true }));
    }""")
    pc.click('#btn-edit')
    results = {'PC': save_pages(pc, tmp_path / 'pc')}
    ctx, ph = new_ctx(browser, phone=True)
    try:
        open_list(ph, repo_url, DAILY, custom_token(ALLOWED, allowed=True))
        ph.click(f'#doc-rows .doc-row[data-id="{doc_id}"]')
        wait_view(ph, 'doc')
        results['휴대폰'] = save_pages(ph, tmp_path / 'phone')
    finally:
        ctx.close()
    for where, (names, shots, sizes) in results.items():
        assert len(names) >= 2 and names[0].endswith('_1.png') and names[1].endswith('_2.png'), (where, names)
        assert len(shots) == len(names) and sum(shots, []) == list(range(1, 16)), (where, shots)
        for w, h in sizes:
            assert h / w <= 16 / 9 * 1.03, (where, w, h)                 # 한 장 = 휴대폰 화면 비율 (10-24 검토 반영)
    assert results['휴대폰'][1] == results['PC'][1], results     # 휴대폰도 PC 와 같은 장 나눔


def test_daily_viewer_sees_list_and_doc_without_edit(pc, browser, repo_url, custom_token, made):
    owner = custom_token(ALLOWED, allowed=True)
    doc_id = daily_new(pc, repo_url, owner, made)
    ctx, staff = new_ctx(browser, phone=True)
    try:
        open_list(staff, repo_url, DAILY, custom_token(VIEWER, allowed=False, viewer=True))
        staff.wait_for_function("document.body.dataset.role === 'viewer'", timeout=10_000)
        staff.locator(f'#doc-rows .doc-row[data-id="{doc_id}"]').wait_for(timeout=15_000)
        assert staff.locator('#doc-new').is_hidden()
        staff.click(f'#doc-rows .doc-row[data-id="{doc_id}"]')
        wait_view(staff, 'doc')
        assert staff.locator('#btn-edit').is_hidden() and staff.locator('#doc-del').is_hidden()
        assert staff.locator('#btn-send').is_visible() and staff.locator('#btn-print').is_visible()
        assert staff.errors == [], staff.errors
    finally:
        ctx.close()


def test_daily_copy_text_ends_with_site_url(pc, repo_url, custom_token, made):
    pc.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜동 상차림')
    pc.click('#btn-edit')
    pc.click('#btn-copy')
    pc.locator('#btn-copy', has_text='복사됨').wait_for(timeout=5_000)
    text = pc.evaluate('navigator.clipboard.readText()')
    lines = text.strip().splitlines()                         # 윈도우 클립보드는 줄바꿈을 \r\n 으로 바꾼다
    assert lines[0] == '[푸드벨 일일 일정표]' and '가짜동 상차림' in text
    assert lines[-1] == 'https://foodbell.kr/'


# ---------- 직원 게시판 — 일정표가 저장될 때 today.html 로 가는 칸 (계획 2026-10-21-staff-today-link Task 3) ----------

def kr_date(d):
    """'2026년 10월 21일' — 일정표 날짜 칸에 치는 글자."""
    return f'{d.year}년 {d.month}월 {d.day}일'


@pytest.fixture
def share_key(test_db):
    """시험 프로젝트의 직원 게시판 암호 — 없으면 만들고, 시험마다 칸을 비우고 시작한다."""
    from tools.sije_web import share_link
    key = share_link.current_key(test_db)
    if not key or not test_db.collection('share').document(key).get().exists:
        key = share_link.new_key(test_db)
    test_db.collection('share').document(key).set({'entries': {}})
    return key


def board(test_db, key):
    return (test_db.collection('share').document(key).get().to_dict() or {}).get('entries', {})


def wait_board(test_db, key, check, timeout=20):
    """게시판의 entries 가 check 를 만족할 때까지 — 만족한 entries 를 돌려준다."""
    ref = test_db.collection('share').document(key)
    snap = wait_db(ref, lambda s: check((s.to_dict() or {}).get('entries', {})), timeout)
    return snap.to_dict()['entries']


def test_daily_board_gets_filled_rows(pc, repo_url, custom_token, test_db, made, share_key):
    """채운 줄만, 줄 번호는 일정표 그대로(빈 2번을 건너도 3번), 금액은 화면 글자 — '단위를 적어 주세요' 는 안 간다."""
    today = datetime.date.today()
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', kr_date(today))
    edit_cell(pc, '[data-k="order"]', '가짜1 · 가짜2')
    edit_cell(pc, '[data-k="memo"]', '가짜 전달 메모')
    pc.click('tr.addrow button')
    pc.click('tr.addrow button')
    one = 'tr.item:nth-child(1)'
    for f, v in [('staff', '가짜직원'), ('car', '1톤'), ('time', '06:30'), ('place', '가짜추모공원'), ('tel', '01000001234'),
                 ('work', '가짜동 상차림'), ('people', '60'), ('price', '15,000원'), ('lead', '가짜팀장'),
                 ('lead-tel', '010-0000-2000'), ('memo', '가짜 메모')]:
        edit_cell(pc, f'{one} [data-f="{f}"]', v)
    edit_cell(pc, 'tr.item:nth-child(3) [data-f="work"]', '가짜동 제사상')
    edit_cell(pc, 'tr.item:nth-child(3) [data-f="price"]', '250')                 # 단위 없음 → 화면에만 알림
    pc.click('#btn-edit')
    entries = wait_board(test_db, share_key, lambda e: [r['no'] for r in e.get(doc_id, {}).get('rows', [])] == [1, 3])
    e = entries[doc_id]
    assert (e['date'], e['label']) == (today.isoformat(), day_label(today))
    assert e['lunar'].startswith('음력 ') and (e['order'], e['memo']) == ('가짜1 · 가짜2', '가짜 전달 메모')
    r1, r3 = e['rows']
    assert r1 == {'no': 1, 'staff': '가짜직원', 'car': '1톤', 'leave': '', 'time': '06:30', 'place': '가짜추모공원', 'map': '',
                  'tel': '010-0000-1234', 'work': '가짜동 상차림', 'amt': '60명 × 15,000원 = 900,000원', 'lead': '가짜팀장',
                  'leadTel': '010-0000-2000', 'guideTel': '', 'hall': '', 'depart': '', 'cremate': '', 'memo': '가짜 메모',
                  'state': ''}   # leave · map: 10-24 검토 반영, state(연기 · 취소): 10-24 저녁
    assert (r3['work'], r3['amt']) == ('가짜동 제사상', '')


def fill_work(page, text='가짜동 상차림'):
    """일 하나를 적고 편집을 끝낸다 — 일이 적힌 일정표만 직원 게시판에 올라간다."""
    page.click('#btn-edit')
    edit_cell(page, 'tr.item [data-f="work"]', text)
    page.click('#btn-edit')


def test_daily_filled_schedule_publishes_and_delete_removes(pc, repo_url, custom_token, test_db, made, share_key):
    """일을 적으면 올라가고(날짜 = 내일), 지우면 게시판에서도 빠진다."""
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    entries = wait_board(test_db, share_key, lambda e: doc_id in e)
    assert entries[doc_id]['date'] == tomorrow.isoformat() and len(entries[doc_id]['rows']) == 1
    pc.once('dialog', lambda d: d.accept())
    pc.click('#doc-del')
    wait_board(test_db, share_key, lambda e: doc_id not in e)


def test_daily_empty_schedule_not_on_board(pc, repo_url, custom_token, test_db, made, share_key):
    """일이 하나도 없는 일정표는 올리지 않는다 — 빈 일정표가 먼저 골라져 직원 화면에 [전화] · [지도]가 안 보였다(사장님 10-21 저녁)."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    wait_board(test_db, share_key, lambda e: doc_id in e)                         # 일을 적으면 올라간다 (대조)
    fill_work(pc, '')                                                             # 다 지우면
    wait_board(test_db, share_key, lambda e: doc_id not in e)                     # 빠진다


def test_daily_has_no_hint(pc, repo_url, custom_token, made):
    """일정표 맨 위 안내문은 없앴다 (사장님 10-21 저녁)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert pc.locator('.hint').count() == 0


def test_daily_unreadable_date_not_on_board(pc, repo_url, custom_token, test_db, made, share_key):
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    wait_board(test_db, share_key, lambda e: doc_id in e)                         # 날짜를 읽으면 올라간다 (대조)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', '10월 21일')                                  # 연도 없음 — 못 읽는 날짜
    pc.click('#btn-edit')
    wait_board(test_db, share_key, lambda e: doc_id not in e)


def test_daily_board_prunes_old_days(pc, repo_url, custom_token, test_db, made, share_key):
    """어제보다 지난 날짜의 칸은 올릴 때 지운다 — 어제 것은 남긴다(자정 무렵 폰 시계 차이)."""
    today = datetime.date.today()
    test_db.collection('share').document(share_key).update({
        'entries.old3': {'date': (today - datetime.timedelta(days=3)).isoformat(), 'rows': []},
        'entries.yday': {'date': (today - datetime.timedelta(days=1)).isoformat(), 'rows': []},
    })
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    entries = wait_board(test_db, share_key, lambda e: doc_id in e and 'old3' not in e)
    assert 'yday' in entries


def test_daily_board_keeps_other_entries(pc, repo_url, custom_token, test_db, made, share_key):
    """다른 기기가 올린 다른 일정표 칸은 그대로 — 게시판을 통째로 덮지 않고 칸 하나씩 고친다."""
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    test_db.collection('share').document(share_key).update({'entries.otherdoc': {'date': tomorrow, 'rows': []}})
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜동 상차림')
    pc.click('#btn-edit')
    entries = wait_board(test_db, share_key, lambda e: e.get(doc_id, {}).get('rows'))
    assert entries['otherdoc'] == {'date': tomorrow, 'rows': []}


def test_daily_board_follows_date_change(pc, repo_url, custom_token, test_db, made, share_key):
    """날짜를 내일 → 모레로 고치면 같은 칸의 날짜만 바뀐다 — 내일 카드가 따로 남지 않는다."""
    after = datetime.date.today() + datetime.timedelta(days=2)
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    wait_board(test_db, share_key, lambda e: doc_id in e)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', kr_date(after))
    pc.click('#btn-edit')
    entries = wait_board(test_db, share_key, lambda e: e.get(doc_id, {}).get('date') == after.isoformat())
    assert list(entries) == [doc_id]


def test_today_updates_live(pc, browser, repo_url, custom_token, test_db, made, share_key):
    """직원 화면(today.html, 로그인 없음)을 열어 둔 채 사장님이 일정표를 고치면 새로고침 없이 바뀐다 (계획 Task 4 —
    사장님 화면 도구가 이 파일에 있어서 여기 둔다)."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', kr_date(datetime.date.today()))
    edit_cell(pc, 'tr.item [data-f="place"]', '가짜동 처음 장소')
    pc.click('#btn-edit')
    ctx, staff = new_ctx(browser, phone=True)
    try:
        staff.goto(f'{repo_url}today.html#{share_key}')
        staff.locator('#cards', has_text='가짜동 처음 장소').wait_for(timeout=20_000)
        pc.click('#btn-edit')
        edit_cell(pc, 'tr.item [data-f="place"]', '가짜동 바뀐 장소')
        pc.click('#btn-edit')
        staff.locator('#cards', has_text='가짜동 바뀐 장소').wait_for(timeout=20_000)
        assert staff.errors == []
    finally:
        ctx.close()


def test_daily_view_place_opens_map_and_numbers_call(phone, repo_url, custom_token, made):
    """사장님 일정표 화면(편집 완료 상태)에서도 장소를 누르면 지도(새 창), 번호를 누르면 전화 — 사장님 10-21 저녁
    ('지도는 안되고있어' 캡처가 일정표 화면이었다). 편집 중 · 저장 · 직원 사진에는 링크가 없다."""
    place = '가짜추모공원 #3 & 제례실'
    daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    phone.click('#btn-edit')
    edit_cell(phone, 'tr.item [data-f="place"]', place)
    edit_cell(phone, 'tr.item [data-f="tel"]', '010-0000-1234, 010-0000-1235')
    edit_cell(phone, 'tr.item [data-f="lead-tel"]', '010-0000-2000')
    edit_cell(phone, 'tr.item [data-f="guide-tel"]', '02-000-4000')
    phone.click('#btn-edit')
    maps = phone.eval_on_selector_all('tr.item a.map1', 'as => as.map((a) => [a.getAttribute("href"), a.target, a.textContent])')
    assert maps == [['https://m.map.naver.com/search2/search.naver?query=' + urllib.parse.quote(place, safe=''), '_blank', place]]
    calls = phone.eval_on_selector_all('tr.item a.tel1', 'as => as.map((a) => a.getAttribute("href"))')
    assert calls == ['tel:01000001234', 'tel:01000001235', 'tel:01000002000', 'tel:020004000']
    saved = phone.evaluate('window.FoodbellDoc.serialize()')
    assert 'map1' not in saved and 'tel1' not in saved and place.replace('&', '&amp;') in saved   # 저장은 글자만
    # 직원 사진은 글자로 새로 그린 카드라 링크가 없다(10-24 검토 반영) — 화면에서만 밑줄 (대조)
    assert phone.evaluate("getComputedStyle(document.querySelector('tr.item a.map1')).textDecorationLine") == 'underline'
    phone.click('#btn-edit')                                                              # 편집 중에는 글자만
    assert phone.locator('tr.item a.map1, tr.item a.tel1').count() == 0
    assert text_of(phone, 'tr.item [data-f="place"]') == place


STAFF_NOTE = "전화 · 지도는 홈 화면의 '푸드벨 일정' 아이콘을 누르세요"      # 10-24 검토 반영 — 공지 링크는 사라진 적이 있다
STAFF_LIKE = '확인했으면 사진을 길게 눌러 👍 해 주세요'
STAFF_HINT = "직원이시면 단톡방 공지의 '푸드벨 일정' 링크를 누르세요"


def test_daily_photo_ends_with_staff_note(pc, repo_url, custom_token, made):
    """직원에게 가는 사진 맨 아래에 '전화 · 지도는 공지 링크' 한 줄 — 사진 속 글자는 눌리지 않아서 (사장님 10-21 밤).
    그 아래에 '👍 해 주세요' 한 줄이 더 붙는다 (사장님 10-23). 화면 · 인쇄에는 없다."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    fill_work(pc)
    assert pc.get_by_text(STAFF_NOTE).count() == 0 or pc.get_by_text(STAFF_NOTE).is_hidden()   # 화면에는 없음
    pc.wait_for_function("typeof html2canvas === 'function'", timeout=20_000)
    pc.evaluate("""() => {
        const orig = window.html2canvas;
        window.__notes = [];
        window.html2canvas = (el, o) => orig(el, { ...o, onclone: async (doc, ref) => {
            if (o && o.onclone) await o.onclone(doc, ref);
            const root = ref || doc.querySelector('.shot-cards');   // 사진 = 휴대폰 카드 묶음 (10-24 검토 반영)
            window.__notes.push([...root.querySelector('.shot-foot').children].map((e) => e.textContent.trim()));
        } });
    }""")
    pc.click('#btn-save-file')
    pc.wait_for_function('window.__notes.length >= 1', timeout=60_000)
    assert pc.evaluate('window.__notes[0]') == [STAFF_NOTE, STAFF_LIKE]           # 사진에는 보이고, 맨 아래 두 줄 (차례대로)
    pc.locator('#btn-save-file', has_text='파일로 저장').wait_for(timeout=60_000)   # 다 찍혀 카드 묶음이 치워진 뒤에 본다
    pc.emulate_media(media='print')
    assert pc.get_by_text(STAFF_NOTE).count() == 0 or pc.get_by_text(STAFF_NOTE).is_hidden()   # 인쇄에도 없음
    pc.emulate_media(media='screen')


def test_daily_login_and_denied_point_staff_to_notice(pc, repo_url, custom_token):
    """일정표 주소를 직원이 열었을 때 — 로그인 화면 · 권한 없음 화면 모두 공지의 '푸드벨 일정' 링크로 안내한다.
    다른 서류에는 없다 (대조)."""
    pc.goto(f'{repo_url}{DAILY}')
    wait_view(pc, 'login')
    pc.locator('[data-show="login"]', has_text=STAFF_HINT).wait_for(timeout=5_000)
    pc.goto(f'{repo_url}{DAILY}?testToken={custom_token(DENIED, allowed=False)}')
    pc.get_by_text('권한이 없습니다').wait_for(timeout=20_000)
    pc.locator('[data-show="denied"]', has_text=STAFF_HINT).wait_for(timeout=5_000)
    pc.goto(f'{repo_url}staff-pay.html?testToken={custom_token(DENIED, allowed=False)}')
    pc.get_by_text('권한이 없습니다').wait_for(timeout=20_000)
    assert pc.get_by_text(STAFF_HINT).count() == 0


# ---------- 10-24 검토 반영 (설계 docs/superpowers/specs/2026-10-24-daily-schedule-review-fixes-design.md) ----------

def test_daily_leave_and_map_fields(pc, repo_url, custom_token, test_db, made, share_key):
    """출발 · 지도 링크 칸 — 보기에서 출발이 보이고, 게시판 한 장에 leave · map 이 들어가며, 지도 링크가 있으면 장소 글자가 그 주소를 연다.
    http 없는 지도 링크는 무시(검색). 전화 칸은 숫자 자판."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert pc.get_attribute('tr.item [data-f="tel"]', 'inputmode') == 'tel'
    assert pc.get_attribute('tr.item [data-f="lead-tel"]', 'inputmode') == 'tel'
    assert pc.get_attribute('tr.item [data-f="guide-tel"]', 'inputmode') == 'tel'
    assert '상주 010' in pc.get_attribute('tr.item [data-f="tel"]', 'data-ph')
    pc.click('#btn-edit')
    assert pc.locator('tr.item [data-f="map"]').is_visible()
    for f, t in [('staff', '가짜직원'), ('leave', '06:30 가게'), ('place', '가짜추모공원'), ('map', 'https://naver.me/abc'), ('work', '가짜 상차림')]:
        edit_cell(pc, f'tr.item [data-f="{f}"]', t)
    pc.click('tr.addrow button')
    for f, t in [('place', '가짜공원'), ('map', 'naver.me/abc'), ('work', '둘째')]:
        edit_cell(pc, f'tr.item:nth-child(2) [data-f="{f}"]', t)
    pc.click('#btn-edit')
    assert pc.locator('tr.item [data-f="map"]').first.is_hidden()
    assert pc.get_attribute('tr.item:nth-child(1) [data-f="place"] a', 'href') == 'https://naver.me/abc'
    assert pc.get_attribute('tr.item:nth-child(2) [data-f="place"] a', 'href').startswith('https://m.map.naver.com/search2/search.naver?query=')
    assert '06:30 가게' in pc.locator('tr.item:nth-child(1)').inner_text()
    snap = wait_db(test_db.collection('share').document(share_key), lambda s: doc_id in (s.to_dict() or {}).get('entries', {}))
    rows = snap.to_dict()['entries'][doc_id]['rows']
    assert (rows[0]['leave'], rows[0]['map'], rows[1]['leave'], rows[1]['map']) == ('06:30 가게', 'https://naver.me/abc', '', 'naver.me/abc')


def test_daily_copy_text_keeps_memo_lines(pc, repo_url, custom_token, made):
    """복사 글 — 출발은 '/ 출발 …', 여러 줄 메모는 다음 줄부터 세 칸 들여 한 줄씩."""
    pc.context.grant_permissions(['clipboard-read', 'clipboard-write'])
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜 상차림')
    edit_cell(pc, 'tr.item [data-f="leave"]', '06:30 가게')
    pc.evaluate("""() => { const m = document.querySelector('tr.item [data-f="memo"]'); m.textContent = '첫 줄\\n둘째 줄';
                           m.dispatchEvent(new Event('input', { bubbles: true })); }""")
    pc.click('#btn-edit')
    pc.click('#btn-copy')
    pc.locator('#btn-copy', has_text='복사됨').wait_for(timeout=5_000)
    lines = pc.evaluate('navigator.clipboard.readText()').strip().splitlines()
    i = next(n for n, l in enumerate(lines) if l.startswith('1. '))
    assert lines[i] == '1. 가짜 상차림 / 출발 06:30 가게' and lines[i + 1] == '   첫 줄' and lines[i + 2] == '   둘째 줄'


def test_daily_funeral_cells_fold_until_opened(pc, repo_url, custom_token, test_db, made):
    """편집 중 장례 여섯 칸이 모두 비면 '장례 칸 펼치기' 단추만, 누르면 펼쳐지고 첫 칸에 커서. 하나라도 적혀 있으면 늘 펼쳐짐.
    저장 HTML 에는 접힘 표시가 없다."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    meet = pc.locator('tr.item td.meet')
    assert meet.locator('button.btn-open').is_visible() and meet.locator('[data-f="lead"]').is_hidden()
    meet.locator('button.btn-open').click()
    assert meet.locator('[data-f="lead"]').is_visible() and pc.evaluate('document.activeElement?.dataset.f') == 'lead'
    assert meet.locator('button.btn-open').count() == 0
    edit_cell(pc, 'tr.item [data-f="hall"]', '가짜장례식장')
    pc.click('#btn-edit')
    pc.click('#btn-edit')                                               # 다시 편집: 적힌 줄은 펼쳐져 있다
    assert meet.locator('button.btn-open').count() == 0 and meet.locator('[data-f="lead"]').is_visible()
    pc.click('tr.addrow button')                                        # 새 줄은 접혀 있다
    assert pc.locator('tr.item:nth-child(2) td.meet button.btn-open').is_visible()
    pc.click('#btn-edit')
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: '가짜장례식장' in (s.to_dict() or {}).get('html', '')).to_dict()['html']
    assert 'folded' not in html and 'btn-open' not in html


def test_daily_time_without_ampm_gets_hint(pc, repo_url, custom_token, test_db, made):
    """'11시20분' 은 편집 중 '오전? 오후?' 가 붙고, '오후 1시' · '13:30' 은 안 붙는다. 보기 · 저장 HTML 에는 없다."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    t = pc.locator('tr.item [data-f="time"]')
    edit_cell(pc, 'tr.item [data-f="time"]', '11시20분')
    assert t.get_attribute('data-ampm') is not None
    assert '오전? 오후?' in pc.evaluate("""getComputedStyle(document.querySelector('tr.item [data-f="time"]'), '::after').content""")
    for v in ('오후 1시', '13:30'):
        edit_cell(pc, 'tr.item [data-f="time"]', v)
        assert t.get_attribute('data-ampm') is None, v
    edit_cell(pc, 'tr.item [data-f="time"]', '12시')
    pc.click('#btn-edit')
    assert '오전? 오후?' not in pc.locator('.sheet').inner_text()
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: '12시' in (s.to_dict() or {}).get('html', '')).to_dict()['html']
    assert 'data-ampm' not in html


def test_daily_send_asks_when_amount_missing(pc, repo_url, custom_token, made):
    """단위 없는 단가('250')가 있으면 '직원에게 보내기'가 한 번 묻고, 아니오면 사진을 만들지 않고 단추가 돌아온다."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, 'tr.item [data-f="work"]', '가짜 상차림')
    edit_cell(pc, 'tr.item [data-f="price"]', '250')
    pc.click('#btn-edit')
    asked = []
    pc.once('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    pc.click('#btn-send')
    pc.wait_for_timeout(800)
    assert asked == ['1번 줄 금액이 비어 있습니다(단위 없음). 그래도 보낼까요?']
    assert pc.locator('#btn-send').inner_text() == '직원에게 보내기' and pc.locator('#btn-send').is_enabled()


def test_daily_stats_line(pc, repo_url, custom_token, made):
    """곱셈 줄 + 단가만 줄 + 단위 없는 줄 → '3건 · 금액 합계 1,250,000원 · 금액 빠진 줄 1'. 0건이면 숨김. 인쇄엔 없음."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    assert pc.locator('.day-stats').is_hidden()
    pc.click('#btn-edit')
    for _ in range(2):
        pc.click('tr.addrow button')
    pc.evaluate("""() => {
        const v = [{ work: '시제', people: '60명', price: '15,000원' }, { work: '평토상', price: '35만' }, { work: '배달', price: '250' }];
        document.querySelectorAll('tr.item').forEach((tr, i) => { for (const [f, t] of Object.entries(v[i])) tr.querySelector(`[data-f="${f}"]`).textContent = t; });
        document.querySelector('tr.item [data-f="work"]').dispatchEvent(new Event('input', { bubbles: true }));
    }""")
    pc.click('#btn-edit')
    assert pc.locator('.day-stats').inner_text() == '3건 · 금액 합계 1,250,000원 · 금액 빠진 줄 1'
    pc.emulate_media(media='print')
    assert pc.locator('.day-stats').is_hidden()
    pc.emulate_media(media='screen')
    assert '금액 합계' not in pc.evaluate('window.FoodbellDoc.serialize()')          # 저장 HTML 에는 없다 (설계 5절)


def watch_shots(page, expr):
    """사진을 찍는 순간의 카드 묶음(사본)에서 expr 로 값을 뽑아 window.__shots 에 모은다."""
    page.wait_for_function("typeof html2canvas === 'function'", timeout=20_000)
    page.evaluate("""(expr) => { window.__shots = []; const o = window.html2canvas;
        window.html2canvas = (el, opt) => o(el, { ...opt, onclone: async (d, ref) => { if (opt.onclone) await opt.onclone(d, ref);
            const root = ref || d.querySelector('.shot-cards'); window.__shots.push(new Function('root', 'return ' + expr)(root)); } }); }""", expr)


def test_daily_photo_is_phone_cards(pc, repo_url, custom_token, made, tmp_path):
    """사진은 카드 묶음 — 폭 1080, 상호 · QR · 인장 없음, 첫 장에 날짜 · 순번 · 전달 메모 · '만듦' 표시, 카드 줄 순서는 cards.js."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="order"]', '가짜1 · 가짜2')
    for f, t in [('staff', '가짜직원'), ('leave', '06:30 가게'), ('time', '오전 10:30'), ('place', '가짜추모공원'), ('tel', '010-0000-0001'),
                 ('work', '가짜 상차림'), ('people', '60명'), ('price', '15,000원')]:
        edit_cell(pc, f'tr.item [data-f="{f}"]', t)
    pc.click('#btn-edit')
    watch_shots(pc, 'root.innerText')
    names, shots, sizes = save_pages(pc, tmp_path)
    assert len(names) == 1 and re.fullmatch(r'\d{4}-\d{2}-\d{2}\.png', names[0]), names   # 날짜는 내일 — 이름 형식만 본다
    assert sizes[0][0] == 1080 and sizes[0][1] / sizes[0][0] <= 16 / 9 * 1.03, sizes
    text = pc.evaluate('window.__shots[0]')
    for s in ('푸드벨 일일 일정표', '순번: 가짜1 · 가짜2', '1번 · 오전 10:30 · 가짜직원', '출발', '06:30 가게', '60명 × 15,000원 = 900,000원',
              '만듦', STAFF_NOTE, STAFF_LIKE):
        assert s in text, s
    for s in ('foodbell.kr', '전통 제례', '010-5353-3477', '단위를 적어 주세요', '건 · 금액 합계'):
        assert s not in text, s


def test_daily_tall_card_gets_own_page(pc, repo_url, custom_token, made, tmp_path):
    """메모 40줄짜리 카드는 혼자 한 장(그 장만 9:16 보다 길어도 된다), 앞뒤 카드는 잘리지 않는다."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    for _ in range(2):
        pc.click('tr.addrow button')
    pc.evaluate("""() => { const trs = document.querySelectorAll('tr.item');
        trs.forEach((tr, i) => { tr.querySelector('[data-f="work"]').textContent = '일 ' + (i + 1); });
        trs[1].querySelector('[data-f="memo"]').textContent = Array.from({ length: 40 }, (_, i) => '주문 글 ' + (i + 1)).join('\\n');
        trs[0].querySelector('[data-f="work"]').dispatchEvent(new Event('input', { bubbles: true })); }""")
    pc.click('#btn-edit')
    names, shots, sizes = save_pages(pc, tmp_path)
    assert shots == [[1], [2], [3]] and sizes[1][1] > sizes[0][1], (shots, sizes)


def test_daily_send_count_and_stamp(phone, repo_url, custom_token, test_db, made):
    """보내기(공유창)마다 차수가 오르고 사진에 '보냄 · N차'. 취소(AbortError)는 안 오른다."""
    doc_id = daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    phone.click('#btn-edit')
    edit_cell(phone, 'tr.item [data-f="work"]', '가짜 상차림')
    phone.click('#btn-edit')
    watch_shots(phone, "root.querySelector('.shot-stamp').textContent")
    phone.evaluate("""() => { navigator.canShare = () => true; window.__shares = 0;
        navigator.share = () => { window.__shares++; return window.__shares === 1 ? Promise.reject(Object.assign(new Error('x'), { name: 'AbortError' })) : Promise.resolve(); }; }""")
    for _ in range(3):
        phone.click('#btn-send')
        phone.locator('#btn-send', has_text='준비 중').wait_for(timeout=10_000)
        phone.locator('#btn-send', has_text='직원에게 보내기').wait_for(timeout=60_000)
    stamps = phone.evaluate('window.__shots')
    assert [s.split(' ', 2)[2] for s in stamps] == ['보냄 · 1차', '보냄 · 1차', '보냄 · 2차'], stamps
    sent = re.compile(r'data-k="sent"[^>]*>2<')
    html = wait_db(test_db.collection('docs').document(doc_id), lambda s: sent.search((s.to_dict() or {}).get('html', ''))).to_dict()['html']
    assert sent.search(html)


# ---------- 10-24 저녁 사장님 요청: 연기 · 취소 표시, 같은 날짜 일정표 물음 ----------

def mark(page, row, state):
    """편집 중 그 줄의 [연기] · [취소] 단추를 누른다."""
    page.click(f'tr.item:nth-child({row}) .btn-state[data-set="{state}"]')


def badges(page):
    """줄마다 번호 칸 옆의 표시 글자 — 표시가 없으면 ''."""
    return page.eval_on_selector_all('tr.item', "trs => trs.map((tr) => tr.querySelector('td.c .state')?.textContent || '')")


def test_daily_row_state_marks_row_and_leaves_total(pc, repo_url, custom_token, test_db, made, share_key):
    """줄마다 [연기] · [취소] — 누르면 켜지고 다시 누르면 풀리며, 둘 중 하나만. 표시한 줄은 번호 옆 · 복사 글 · 직원 게시판에 붙고
    사장님 한 줄의 건수 · 합계 · 금액 빠진 줄에서는 빠진다. 다시 열어도 남는다 (사장님 10-24 저녁 — 메모에 '연기'만 적으면 사진에서 똑같아 보였다)."""
    doc_id = daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    for _ in range(2):
        pc.click('tr.addrow button')
    pc.evaluate("""() => {
        const v = [{ work: '가짜 시제', price: '120만' }, { work: '가짜 평토상', price: '35만' }, { work: '가짜 제사', price: '250' }];
        document.querySelectorAll('tr.item').forEach((tr, i) => { for (const [f, t] of Object.entries(v[i])) tr.querySelector(`[data-f="${f}"]`).textContent = t; });
        document.querySelector('tr.item [data-f="work"]').dispatchEvent(new Event('input', { bubbles: true }));
    }""")
    mark(pc, 1, '연기')
    mark(pc, 1, '연기')                                   # 다시 누르면 풀린다
    mark(pc, 2, '연기')
    mark(pc, 3, '연기')
    mark(pc, 3, '취소')                                   # 둘 중 하나만 — 연기에서 취소로
    assert badges(pc) == ['', '연기', '취소']
    pressed = pc.eval_on_selector_all('tr.item .btn-state', "bs => bs.map((b) => b.dataset.set + ':' + b.getAttribute('aria-pressed'))")
    assert pressed == ['연기:false', '취소:false', '연기:true', '취소:false', '연기:false', '취소:true']
    pc.click('#btn-edit')
    assert pc.locator('.day-stats').inner_text() == '1건 · 금액 합계 1,200,000원 · 연기 1 · 취소 1'   # 단위 없는 3번(취소)은 '금액 빠진 줄'에도 안 든다
    text = pc.evaluate('window.FoodbellDoc.summary().text').splitlines()
    assert '1. 가짜 시제 1,200,000원' in text and '2. [연기] 가짜 평토상 350,000원' in text and '3. [취소] 가짜 제사' in text, text
    entries = wait_board(test_db, share_key, lambda e: [r.get('state') for r in e.get(doc_id, {}).get('rows', [])] == ['', '연기', '취소'])
    assert [r['no'] for r in entries[doc_id]['rows']] == [1, 2, 3]
    wait_db(test_db.collection('docs').document(doc_id), lambda s: '취소' in s.get('html'))
    open_doc(pc, repo_url, DAILY, doc_id)                 # 다시 열어도 남는다(저장된 화면)
    pc.locator('tr.item td.c .state').first.wait_for(timeout=15_000)
    assert badges(pc) == ['', '연기', '취소']


def test_daily_send_skips_state_rows_in_amount_check(phone, repo_url, custom_token, made):
    """취소 · 연기한 줄의 단위 없는 단가는 '금액이 비어 있습니다' 물음에 안 든다 — 묻지 않고 사진을 넘긴다."""
    daily_new(phone, repo_url, custom_token(ALLOWED, allowed=True), made)
    stub_share(phone)
    phone.click('#btn-edit')
    edit_cell(phone, 'tr.item [data-f="work"]', '가짜 상차림')
    edit_cell(phone, 'tr.item [data-f="price"]', '250')
    mark(phone, 1, '취소')
    phone.click('#btn-edit')
    asked = []
    phone.on('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    phone.click('#btn-send')
    assert shared(phone, 1)['files'] >= 1
    assert asked == []


def test_daily_photo_marks_state(pc, repo_url, custom_token, made, tmp_path):
    """직원 사진 카드에도 연기 · 취소 표시가 머리 맨 앞에 — 표시 없는 카드에는 없다."""
    daily_new(pc, repo_url, custom_token(ALLOWED, allowed=True), made)
    pc.click('#btn-edit')
    pc.click('tr.addrow button')
    edit_cell(pc, 'tr.item:nth-child(1) [data-f="work"]', '가짜 시제')
    edit_cell(pc, 'tr.item:nth-child(2) [data-f="work"]', '가짜 제사')
    mark(pc, 2, '연기')
    pc.click('#btn-edit')
    watch_shots(pc, "[...root.querySelectorAll('article.card:not([data-shot-hide]) .head')].map((h) => h.innerText)")
    save_pages(pc, tmp_path)
    heads = pc.evaluate('window.__shots')[0]
    assert len(heads) == 2 and not heads[0].startswith('연기') and heads[1].startswith('연기'), heads


def test_daily_new_asks_when_same_date_exists(pc, repo_url, custom_token, test_db, made, no_daily):
    """'새 일정표'를 누를 때 같은 날짜(내일) 일정표가 이미 있으면 묻는다 — 취소 = 있는 일정표를 연다(새로 안 만듦),
    확인 = 그래도 새로 만든다. 날짜가 다르면 묻지 않는다 (10-21 같은 날 일정표가 넷 생겨 직원 화면에 빈 일정이 먼저 떴다)."""
    token = custom_token(ALLOWED, allowed=True)
    first = daily_new(pc, repo_url, token, made)

    def touch(memo):
        """한 글자라도 적어야 남는다 — 안 고친 새 일정표는 떠날 때 지운다 (10-26). 새 일정표는 앞 것의 메모를 물려받으니 장마다 다른 글자로."""
        pc.click('#btn-edit')
        edit_cell(pc, '[data-k="memo"]', memo)
        pc.click('#btn-edit')

    touch('가짜 메모 1')

    def daily_ids():
        return sorted(d.id for d in test_db.collection('docs').where('kind', '==', 'daily-schedule').stream())

    def to_list():
        pc.click('#btn-list')
        wait_view(pc, 'list')
        pc.locator(f'#doc-rows .doc-row[data-id="{first}"]').wait_for(timeout=15_000)

    def press_new():
        pc.click('#doc-new')
        pc.wait_for_url(re.compile(r'\?id='), timeout=20_000)
        wait_view(pc, 'doc')
        return pc.evaluate("new URLSearchParams(location.search).get('id')")

    asked = []
    to_list()
    pc.once('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    assert press_new() == first                                    # 취소 → 있는 일정표가 열린다
    assert len(asked) == 1 and asked[0].startswith(f'{expected_label("TOMORROW")} 일정표가 이미 있습니다'), asked
    assert daily_ids() == [first]                                  # 새로 만들지 않았다

    pc.click('#btn-edit')
    edit_cell(pc, '[data-k="date"]', kr_date(datetime.date.today()))   # 있는 것을 오늘 날짜로 → 내일 일정표는 없다
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(first), lambda s: s.get('label') == day_label(datetime.date.today()))
    to_list()
    asked.clear()

    def record(d):
        asked.append(d.message)
        d.dismiss()

    pc.on('dialog', record)
    second = press_new()
    pc.remove_listener('dialog', record)
    made.append(second)
    assert second != first and asked == []                         # 날짜가 다르면 묻지 않는다

    touch('가짜 메모 2')
    pc.click('#btn-list')
    wait_view(pc, 'list')
    pc.locator(f'#doc-rows .doc-row[data-id="{second}"]').wait_for(timeout=15_000)
    pc.once('dialog', lambda d: (asked.append(d.message), d.accept()))
    third = press_new()
    made.append(third)
    assert third not in (first, second) and len(asked) == 1        # 확인 → 그래도 새로 만든다
    wait_db(test_db.collection('docs').document(third), lambda s: s.exists)
