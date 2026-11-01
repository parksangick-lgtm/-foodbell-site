"""거래명세서(statement.html) 보완 시험 — 서류 7종 보완 2차 (사장님 2026-11-01).
새 거래명세서의 첫 줄 월/일은 빈 칸, 아래에 입금 계좌 · 인수일 빈 칸이 있다. 손님 정보 · 계좌는 전부 가짜."""
from test_doc_pages import ALLOWED, made, new_doc, open_doc, open_list, pc, set_text, wait_db, wait_view  # noqa: F401 (준비물)

FILE = 'statement.html'


def test_new_statement_first_row_date_is_empty(pc, repo_url, custom_token, made):
    """새 거래명세서의 첫 줄 월/일은 비어 있다 — 전에는 오늘 날짜(예: 11/1)가 들어갔다. 문서번호 · 작성일자는 그대로 오늘."""
    open_list(pc, repo_url, FILE, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    assert pc.locator('tr.item [data-k="md"]').first.inner_text().strip() == ''
    assert pc.locator('[data-k="issue"]').inner_text().strip() != ''
    assert pc.locator('[data-k="dno"]').inner_text().strip().startswith('FB-')


def test_editing_shows_empty_account_and_receive_date_cells(pc, repo_url, custom_token, made):
    """편집 모드에서 입금 계좌 · 인수일 칸이 보이고 비어 있다. 보기 모드에서는 비어 있으면 라벨까지 숨긴다."""
    open_list(pc, repo_url, FILE, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    acct = pc.locator('.sheet [data-edit][data-k="acct"]')
    recv = pc.locator('.sheet [data-edit][data-k="recvDate"]')
    assert not acct.is_visible() and not recv.is_visible()          # 보기 모드: 빈 칸이면 라벨만 덩그러니 남지 않게
    pc.click('#btn-edit')
    assert acct.is_visible() and recv.is_visible()
    assert acct.inner_text().strip() == '' and recv.inner_text().strip() == ''
    assert pc.locator('.closing-row', has_text='입금 계좌').is_visible()
    assert pc.locator('.closing-row', has_text='인수일').is_visible()


def test_account_and_receive_date_survive_save_and_reopen(pc, repo_url, custom_token, test_db, made):
    """적은 입금 계좌 · 인수일이 저장돼 다시 열어도 남는다(serialize 가 저장하는 문서면 안에 있다). 값은 가짜."""
    token = custom_token(ALLOWED, allowed=True)
    open_list(pc, repo_url, FILE, token)
    doc_id = new_doc(pc, made)
    pc.click('#btn-edit')
    set_text(pc, '.sheet [data-k="acct"]', '시험은행 000-0000-0000')
    set_text(pc, '.sheet [data-k="recvDate"]', '2026년 11월 2일')
    pc.click('#btn-edit')
    wait_db(test_db.collection('docs').document(doc_id), lambda s: s.exists and '시험은행 000-0000-0000' in s.get('html'))
    open_doc(pc, repo_url, FILE, doc_id, token)
    assert pc.locator('.sheet [data-k="acct"]').inner_text().strip() == '시험은행 000-0000-0000'
    assert pc.locator('.sheet [data-k="recvDate"]').inner_text().strip() == '2026년 11월 2일'
    assert pc.locator('.closing-row', has_text='입금 계좌').is_visible()   # 보기 모드에서도 값이 있으면 보인다
