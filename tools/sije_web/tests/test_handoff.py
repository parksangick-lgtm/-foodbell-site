"""서류 잇기(3단계) 시험 — 버튼으로 한 번 옮겨 담기. 시험 프로젝트 · 가짜 자료만, 만든 서류는 끝나면 지운다.
도우미 · 준비물은 2단계 test_doc_pages.py 의 것을 그대로 쓴다."""
import time
from urllib.parse import quote

import pytest

from test_doc_pages import ALLOWED, made, new_doc, open_list, pc, set_text, wait_db, wait_view  # noqa: F401 (준비물)

STATEMENT_DONE = '**/statement.html?id=*'
SHEET_DONE = '**/sije-sheet.html?id=*'
FAKE_TPL_ITEMS = {'L01': {'group': '과일', 'no': '1', 'name': '배', 'qty': '5개', 'note': ''}}


@pytest.fixture
def templates(test_db):
    """빈 양식 '7치 고임상' · '60만원상'(가짜 품목). 원래 없던 것만 끝나고 지운다."""
    added = []
    for name in ('7치 고임상', '60만원상'):
        ref = test_db.collection('templates').document(name)
        if not ref.get().exists:
            ref.set({'name': name, 'items': FAKE_TPL_ITEMS, 'itemRows': 1})
            added.append(ref)
    yield
    for ref in added:
        ref.delete()


@pytest.fixture
def made_events(test_db):
    ids = []
    yield ids
    for i in ids:
        test_db.collection('events').document(i).delete()


def track_urls(page):
    urls = []
    page.on('framenavigated', lambda f: urls.append(f.url) if f == page.main_frame else None)
    return urls


def answer_next(page, ok=True):
    asked = []

    def handle(d):
        asked.append(d.message)
        d.accept() if ok else d.dismiss()

    page.once('dialog', handle)
    return asked


def opened_doc_id(page, made):
    doc_id = page.evaluate("new URLSearchParams(location.search).get('id')")
    made.append(doc_id)
    return doc_id


def statement_count(test_db):
    from google.cloud.firestore_v1.base_query import FieldFilter
    return sum(1 for _ in test_db.collection('docs').where(filter=FieldFilter('kind', '==', 'statement')).stream())


def quote_with_supply(pc, repo_url, custom_token, made, file, supply):
    open_list(pc, repo_url, file, custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    if supply:
        pc.click('#btn-edit')
        set_text(pc, '[data-k="supply"]', supply)
        pc.click('#btn-edit')
    return doc_id


def test_quote_to_statement_fills_one_row(pc, repo_url, custom_token, test_db, made):
    urls = track_urls(pc)
    quote_id = quote_with_supply(pc, repo_url, custom_token, made, 'sije-quote.html', '1000000')
    qref = test_db.collection('docs').document(quote_id)
    before = wait_db(qref, lambda s: s.get('total') == '1,100,000').get('html')
    asked = answer_next(pc)
    pc.click('#doc-make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    assert asked == ['이 견적서 내용으로 새 거래명세서를 만들까요?']
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['kind'] == 'statement' and doc['label'] == '○○ 김씨 문중 종친회'
    assert doc['total'] == '1,100,000'                                      # 견적서 합계와 같다
    assert '11/21' in doc['html'] and '5열 진설 제수상 1상 + 종친 음복 식사' in doc['html']
    time.sleep(1)
    assert qref.get().get('html') == before                                  # 원래 견적서 그대로 (Review Focus 4)
    for secret in ('문중', '1000000', '1,000,000'):                         # 주소에 손님 정보 없음 (Review Focus 3)
        assert not any(secret in u or quote(secret) in u for u in urls), (secret, urls)


def test_event_quote_to_statement_uses_event_kind(pc, repo_url, custom_token, test_db, made):
    quote_with_supply(pc, repo_url, custom_token, made, 'event-quote.html', '500000')
    answer_next(pc)
    pc.click('#doc-make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['label'] == '○○ 단체' and doc['total'] == '550,000'
    assert '단체 · 모임 행사 상차림' in doc['html'] and '11/21' in doc['html']


def test_cancel_creates_nothing(pc, repo_url, custom_token, test_db, made):
    quote_with_supply(pc, repo_url, custom_token, made, 'sije-quote.html', '')
    url = pc.url
    count = statement_count(test_db)
    answer_next(pc, ok=False)
    pc.click('#doc-make-statement')
    time.sleep(2)
    assert pc.url == url and statement_count(test_db) == count


def test_quote_without_supply_notes_amount(pc, repo_url, custom_token, test_db, made):
    quote_with_supply(pc, repo_url, custom_token, made, 'sije-quote.html', '')
    answer_next(pc)
    pc.click('#doc-make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    pc.locator('.doc-toast', has_text='금액을 읽지 못했습니다').wait_for(timeout=10_000)
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['total'] == ''                                                # 단가가 비어 합계도 빈 칸


# ---------- Task 3: 시제 견적서 → 내역서 ----------

def quote_for_event(pc, repo_url, custom_token, made, tier, supply='1000000', when=None):
    open_list(pc, repo_url, 'sije-quote.html', custom_token(ALLOWED, allowed=True))
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    pc.click(f'.tier-btn[data-tier="{tier}"]')
    set_text(pc, '[data-k="supply"]', supply)
    if when is not None:
        set_text(pc, '.brief-row:has(dt:text-is("봉행 일시")) dd', when)
    pc.click('#btn-edit')
    return doc_id


def opened_event(pc, test_db, made_events):
    pc.wait_for_url(SHEET_DONE, timeout=20_000)
    ev_id = pc.evaluate("new URLSearchParams(location.search).get('id')")
    made_events.append(ev_id)
    return wait_db(test_db.collection('events').document(ev_id), lambda s: s.exists).to_dict()


def test_quote_to_event_fills_fields_and_template(pc, repo_url, custom_token, test_db, made, made_events, templates):
    quote_id = quote_for_event(pc, repo_url, custom_token, made, '7chi')
    qref = test_db.collection('docs').document(quote_id)
    before = wait_db(qref, lambda s: s.get('total') == '1,100,000').get('html')
    asked = answer_next(pc)
    pc.click('#doc-make-event')
    ev = opened_event(pc, test_db, made_events)
    assert asked == ['이 견적서 내용으로 새 내역서를 만들까요?']
    assert ev['status'] == '미확정' and ev['templateType'] == '7치 고임상'
    assert ev['customer'] == '○○ 김씨 문중 종친회'
    assert (ev['date'], ev['time']) == ('2026-11-21', '오전 10시')
    assert ev['place'] == ev['titlePlace'] == '충남 ○○군 ○○면 선산 묘역 (야외)'
    assert ev['setting'] == '5열 진설 제수상 1상 + 종친 음복 식사'
    assert ev['amount'] == '1,000,000원'                                    # 공급가액 (답 42)
    assert ev['items'] == test_db.collection('templates').document('7치 고임상').get().get('items')   # 빈 양식의 품목으로 시작
    time.sleep(1)
    assert qref.get().get('html') == before                                  # 원래 견적서 그대로


def test_quote_40man_asks_template(pc, repo_url, custom_token, test_db, made, made_events, templates):
    quote_for_event(pc, repo_url, custom_token, made, '40man')
    answer_next(pc)
    pc.click('#doc-make-event')
    pc.locator('#toast', has_text='내역서를 만드는 중').wait_for(timeout=20_000)   # 받는 동안 표시 (검토 M1 — 안 된 줄 알고 또 누르지 않게)
    pc.locator('#tpl-dialog .tpl-choice', has_text='60만원상').click(timeout=20_000)   # 40만원상은 빈 양식이 없다 → 고르기
    ev = opened_event(pc, test_db, made_events)
    assert ev['templateType'] == '60만원상' and ev['customer'] == '○○ 김씨 문중 종친회'


def test_quote_bad_date_notes_date(pc, repo_url, custom_token, test_db, made, made_events, templates):
    quote_for_event(pc, repo_url, custom_token, made, '7chi', when='11월 말')
    answer_next(pc)
    pc.click('#doc-make-event')
    ev = opened_event(pc, test_db, made_events)
    assert ev['date'] == '' and ev['amount'] == '1,000,000원'
    pc.locator('#toast', has_text='날짜를 읽지 못했습니다').wait_for(timeout=15_000)


# ---------- Task 4: 내역서 → 거래명세서 ----------

@pytest.fixture
def event_id(test_db, made_events):
    """가짜 행사 (고객 '가짜 문중', 2026-11-13, 상차림 '7치 1상', 금액 '600,000원')."""
    from conftest import fake_event
    import uuid
    ev_id = 'handoff-' + uuid.uuid4().hex[:8]
    test_db.collection('events').document(ev_id).set(fake_event())
    made_events.append(ev_id)
    return ev_id


def open_sheet(pc, repo_url, custom_token, ev_id):
    pc.goto(f'{repo_url}sije-sheet.html?id={ev_id}&testToken={custom_token(ALLOWED, allowed=True)}',
            wait_until='domcontentloaded')                     # 'load' 는 바깥 글꼴까지 기다린다 (기록장 #61)
    pc.locator('#sheet td[data-path="items.L01.qty"]').wait_for(timeout=20_000)


def test_sheet_to_statement(pc, repo_url, custom_token, test_db, made, event_id):
    eref = test_db.collection('events').document(event_id)
    before = eref.get().to_dict()
    open_sheet(pc, repo_url, custom_token, event_id)
    asked = answer_next(pc)
    pc.click('#make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    assert asked == ['이 내역서 내용으로 새 거래명세서를 만들까요?']
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['label'] == '가짜 문중' and doc['total'] == '660,000'          # 600,000 + 세액 10%
    assert '11/13' in doc['html'] and '7치 1상' in doc['html']
    time.sleep(1)
    assert eref.get().to_dict() == before                                     # 내역서 그대로


def test_sheet_man_amount_to_statement(pc, repo_url, custom_token, test_db, made, event_id):
    test_db.collection('events').document(event_id).update({'amount': '360만 VAT별도 · 산신제15만  ·  제물추가20만'})   # 실제 내역서 꼴 — 단가가 비던 신고 (2026-10-18) · 금액 내역을 이어 붙인 꼴 (2026-10-29)
    open_sheet(pc, repo_url, custom_token, event_id)
    answer_next(pc)
    pc.click('#make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['total'] == '3,960,000'                                        # 3,600,000 + 세액 10%


def test_sheet_bad_amount_notes_amount(pc, repo_url, custom_token, test_db, made, event_id):
    test_db.collection('events').document(event_id).update({'amount': '육십만원'})   # 숫자가 아닌 꼴 (2.400,000원 은 이제 읽는다 — 2026-10-18)
    open_sheet(pc, repo_url, custom_token, event_id)
    answer_next(pc)
    pc.click('#make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    pc.locator('.doc-toast', has_text='금액을 읽지 못했습니다').wait_for(timeout=10_000)
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['total'] == ''


QUOTE_DONE = '**/sije-quote.html?id=*'
BRIEF = r"""ds => ds.map((d) => d.textContent.replace(/\s+/g, ' ').trim())"""


def test_sheet_to_quote(pc, repo_url, custom_token, test_db, made, event_id):
    """내역서 → 시제 견적서: 수신 · 봉행 일시 · 장소 · 상차림 · 공급가액이 채워진 새 견적서 (사장님 2026-10-28)."""
    eref = test_db.collection('events').document(event_id)
    before = eref.get().to_dict()
    open_sheet(pc, repo_url, custom_token, event_id)
    asked = answer_next(pc)
    pc.click('#make-quote')
    pc.wait_for_url(QUOTE_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    assert asked == ['이 내역서 내용으로 새 견적서를 만들까요?']
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['kind'] == 'sije-quote' and doc['label'] == '가짜 문중'
    dd = pc.eval_on_selector_all('.brief-row dd', BRIEF)
    assert dd[0] == '가짜 문중 귀중'
    assert dd[2:] == ['2026년 11월 13일 (금) 10시', '가짜동 1-1 놀이터 위', '7치 1상']
    assert pc.locator('[data-k="supply"]').inner_text() == '600,000'
    assert pc.locator('[data-k="total"]').inner_text() == '660,000'           # 600,000 + 부가세 10%
    time.sleep(1)
    assert eref.get().to_dict() == before                                     # 내역서 그대로


def test_sheet_to_quote_blank_fields_note(pc, repo_url, custom_token, test_db, made, event_id):
    """고객 · 날짜 · 금액을 못 읽으면 비워 두고 알린다 — 견적서 예시 글('○○ 김씨 문중…')이 손님에게 나가지 않게."""
    test_db.collection('events').document(event_id).update({'customer': '', 'date': '', 'amount': '육십만원'})
    open_sheet(pc, repo_url, custom_token, event_id)
    answer_next(pc)
    pc.click('#make-quote')
    pc.wait_for_url(QUOTE_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    pc.locator('.doc-toast', has_text='고객 이름을 읽지 못했습니다').wait_for(timeout=10_000)
    opened_doc_id(pc, made)
    dd = pc.eval_on_selector_all('.brief-row dd', BRIEF)
    assert dd[0] == '귀중' and dd[2] == ''
    assert pc.locator('[data-k="supply"]').inner_text() == ''


def test_print_hides_make_row(pc, repo_url, custom_token, made, event_id):
    open_sheet(pc, repo_url, custom_token, event_id)
    assert pc.locator('#make-statement').is_visible()
    pc.emulate_media(media='print')
    assert not pc.locator('#make-statement').is_visible()
    pc.emulate_media(media='screen')
    open_list(pc, repo_url, 'sije-quote.html', custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    assert pc.locator('#doc-make-event').is_visible()
    pc.emulate_media(media='print')
    assert not pc.locator('#doc-make-event').is_visible()


# ---------- Task 5: 보호 장치 ----------

def test_stale_bundle_creates_nothing(pc, repo_url, custom_token, test_db, made):
    """Review Focus 1 — 오래된(1분 넘은) 꾸러미로는 아무것도 안 만든다."""
    open_list(pc, repo_url, 'statement.html', custom_token(ALLOWED, allowed=True))
    count = statement_count(test_db)
    pc.evaluate("""sessionStorage.setItem('foodbell-handoff', JSON.stringify({to: 'statement', at: Date.now() - 120000,
        fields: {cust: '오래된 꾸러미', md: '', item: '가짜', price: 1000}, notes: []}))""")
    pc.goto(f'{repo_url}statement.html?make=1')
    wait_view(pc, 'list')
    time.sleep(2)
    assert statement_count(test_db) == count
    assert pc.evaluate("sessionStorage.getItem('foodbell-handoff')") is None     # 쓰지 않아도 지운다


def test_back_does_not_create_twice(pc, repo_url, custom_token, test_db, made):
    """Review Focus 2 — 만든 뒤 뒤로 가도 두 장이 생기지 않는다."""
    quote_with_supply(pc, repo_url, custom_token, made, 'sije-quote.html', '300000')
    answer_next(pc)
    pc.click('#doc-make-statement')
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    opened_doc_id(pc, made)
    count = statement_count(test_db)
    pc.go_back()                                                              # 견적서로 돌아간다 (만들기 화면은 기록에 안 남음)
    wait_view(pc, 'doc')
    assert 'sije-quote.html' in pc.url
    time.sleep(3)
    assert statement_count(test_db) == count



def test_sheet_just_edited_amount_goes_to_statement(pc, repo_url, custom_token, test_db, made, event_id):
    """3단계 검토 I2 — 금액 칸을 고치자마자(칸을 떠나기 전에) 버튼을 눌러도 고친 금액으로 거래명세서를 만든다.
    내역서에도 고친 금액이 남는다 — 저장을 기다리지 않고 넘어가서, 휴대폰이 바쁘면 내역서의 고친 금액이 사라졌다
    (2026-10-28 — 시험을 한꺼번에 돌릴 때만 가끔 실패해 헛실패로 보였다. 느린 휴대폰처럼 만들면 매번 실패)."""
    open_sheet(pc, repo_url, custom_token, event_id)
    pc.context.new_cdp_session(pc).send('Emulation.setCPUThrottlingRate', {'rate': 6})   # 느린 휴대폰처럼
    pc.once('dialog', lambda d: d.accept())
    pc.evaluate("""() => {
        const c = document.querySelector('#sheet [data-path="amount"]');
        c.focus();
        c.innerText = '700,000원';
        document.getElementById('make-statement').click();   // 포커스는 칸에 남은 채 — 빠르게 탭한 것과 같다
    }""")
    pc.wait_for_url(STATEMENT_DONE, timeout=20_000)
    wait_view(pc, 'doc')
    doc = wait_db(test_db.collection('docs').document(opened_doc_id(pc, made)), lambda s: s.exists).to_dict()
    assert doc['total'] == '770,000'                                           # 700,000 + 세액 10%
    wait_db(test_db.collection('events').document(event_id), lambda s: s.get('amount') == '700,000원')
