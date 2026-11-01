"""알바비 지급내역서(staff-pay.html) 전용 화면 시험 — 서류 7종 보완 2차 (사장님 2026-11-01).
새 서류 여는 방법 · 준비물은 test_doc_pages 를 그대로 따른다. 손님 정보는 전부 가짜."""
import datetime

from test_doc_pages import ALLOWED, day_label, made, new_doc, open_list, pay_fill, pc  # noqa: F401 (준비물)


def test_send_confirm_shows_paydate_once(pc, repo_url, custom_token, made):
    """'직원에게 보내기' 확인창 하나에 지급일 한 줄 + 전화번호 · 계좌 안내 — 지급일을 못 보고 보내는 일이 없게 (보완 알바비 1).
    새 지급내역서의 지급일은 오늘(요일)이라 확인창에 그 글자가 그대로 들어 있어야 한다. 확인창은 둘로 나누지 않는다."""
    open_list(pc, repo_url, 'staff-pay.html', custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    pc.click('#btn-edit')
    pay_fill(pc, 1)                                                                       # 일당이 있으니 일당 물음은 안 뜬다
    pc.click('#btn-edit')
    asked = []
    pc.on('dialog', lambda d: (asked.append(d.message), d.dismiss()))
    pc.click('#btn-send')
    pc.wait_for_timeout(800)
    assert len(asked) == 1, asked                                                         # 확인창 하나
    assert '지급일' in asked[0] and day_label(datetime.date.today()) in asked[0], asked
    assert '전화번호·계좌가 담깁니다' in asked[0], asked
    assert pc.locator('#btn-send').inner_text() == '직원에게 보내기' and pc.locator('#btn-send').is_enabled()
