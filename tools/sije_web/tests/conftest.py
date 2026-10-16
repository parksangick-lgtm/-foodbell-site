"""시험 공용 준비물 — 시험 프로젝트(foodbell-sije-test)만 쓴다. 손님 정보는 넣지 않는다(전부 가짜)."""
import io
import re
from pathlib import Path

import pytest
import requests
from firebase_admin import auth

from tools.sije_web import allow, fsdb

ROOT = Path(__file__).resolve().parents[3]
CONFIG_JS = ROOT / 'js' / 'sije' / 'firebase-config.js'

# 60만원상 빈 양식의 품목 (손님 정보 아님)
_LEFT = [('과일', '배', '5개', ''), ('과일', '사과', '5개', ''), ('과일', '감', '5개', ''), ('과일', '밤', '5치', ''),
         ('과일', '대추', '5치', ''), ('한과', '약과', '10개', ''), ('한과', '산자', '5장', ''), ('떡', '조청', '1개', ''),
         ('떡', '웃기', '없음', ''), ('떡', '편떡', '3쪽', ''), ('적·생선', '산적', '3쪽', ''), ('적·생선', '계적', '1마리', ''),
         ('적·생선', '조기', '1마리', '큰걸로'), ('적·생선', '두부(소적)', '5쪽', ''), ('전·부침', '녹두부침', '5쪽', ''),
         ('전·부침', '동태전', '10개', ''), ('전·부침', '육원전', '25개', '')]
_RIGHT = [('탕', '북어탕', '1개', '북어,무'), ('탕', '소탕', '1개', '두부,무'), ('탕', '육탕', '1개', '쇠고기,무'),
          ('나물', '도라지', '1개', ''), ('나물', '숙주', '1개', ''), ('나물', '고사리', '1개', ''),
          ('메·갱', '국수', '1그릇', ''), ('메·갱', '밥·국', '', ''), ('기타', '북어포', '1개', ''),
          ('기타', '식혜', '1개', ''), ('기타', '간장·고명', '1개', ''), ('기타', '물김치', '1개', ''), ('기타', '술', '', '')]


def fake_event(**over) -> dict:
    """가짜 행사 한 건 (저장소에 들어가는 모양 그대로). 손님 정보는 전부 가짜."""
    items, no = {}, 1
    for side, rows in (('L', _LEFT), ('R', _RIGHT)):
        for i, (group, name, qty, note) in enumerate(rows, 1):
            items[f'{side}{i:02d}'] = {'group': group, 'no': str(no), 'name': name, 'qty': qty, 'note': note}
            no += 1
    ev = {
        'status': '확정', 'date': '2026-11-13', 'time': '10시', 'sijeil': '음력 10월 3일',
        'expectedDate': '', 'basis': '', 'confirmedText': '',
        'place': '가짜동 1-1 놀이터 위', 'titlePlace': '가짜동 1-1',
        'setting': '7치 1상', 'sansinje': '없음', 'customer': '가짜 문중', 'contacts': ['010-0000-0000'],
        'staffCar': '가짜 담당 · 1호차', 'meal': '20인분', 'amount': '600,000원', 'amountDetail': '상차림 60만',
        'departTime': '07시', 'arriveTime': '09시 30분',
        'mustDo': '산신제 상은 따로 차린다\n도착하면 먼저 전화',
        'templateType': '60만원상', 'items': items, 'fileLabel': '', 'extraItems': '',
        'memo': '주차는 가짜 마을회관 앞', 'sourceFile': '',
    }
    ev.update(over)
    return ev


def fake_jpeg(w=1200, h=900, color=(176, 141, 87)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (w, h), color).save(buf, 'JPEG', quality=90)
    return buf.getvalue()


@pytest.fixture(scope='session')
def repo_url():
    """저장소 폴더를 이 컴퓨터 안에서만 여는 임시 서버 주소."""
    from tools.sije_web.render_pdf import serve_repo
    with serve_repo(ROOT) as url:
        yield url


def _test_project_config() -> dict:
    """firebase-config.js 의 TEST 묶음 값(apiKey · projectId …) — 설정값은 그 파일 한 곳에만 둔다."""
    block = re.search(r'const TEST = \{(.*?)\};', CONFIG_JS.read_text(encoding='utf-8'), re.S).group(1)
    return dict(re.findall(r"(\w+): '([^']*)'", block))


@pytest.fixture(scope='session')
def test_db():
    if not fsdb.KEY_TEST.exists():
        pytest.skip(f'시험 열쇠가 없습니다: {fsdb.KEY_TEST}')
    return fsdb.open_db(fsdb.KEY_TEST)


@pytest.fixture(scope='session')
def custom_token(test_db):
    """custom_token(email, allowed) → 화면의 signInWithCustomToken 에 넣을 토큰. allowed 면 허락 목록에 넣는다."""
    app = fsdb.app_for(fsdb.KEY_TEST)
    used = []

    def make(email: str, allowed: bool) -> str:
        try:
            user = auth.get_user_by_email(email, app=app)
        except auth.UserNotFoundError:
            user = auth.create_user(email=email, email_verified=True, app=app)
        (allow.add if allowed else allow.remove)(test_db, email)
        used.append(email)
        return auth.create_custom_token(user.uid, app=app).decode()

    yield make
    for email in used:
        allow.remove(test_db, email)


@pytest.fixture(scope='session')
def id_token(custom_token):
    """id_token(email, allowed) → 그 메일로 로그인한 사람의 ID 토큰 (REST 로 저장소를 직접 부를 때)."""
    api_key = _test_project_config()['apiKey']

    def make(email: str, allowed: bool) -> str:
        r = requests.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken',
                          params={'key': api_key}, json={'token': custom_token(email, allowed), 'returnSecureToken': True},
                          timeout=30)
        r.raise_for_status()
        return r.json()['idToken']

    return make


@pytest.fixture(scope='module')
def browser():
    """헤드리스 크롬 — 시험 파일(모듈)마다 하나. render_pdf 가 따로 여는 것과 겹치지 않게 모듈 단위로 닫는다."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    """PC 창(1280px) 하나 — 시험마다 새 창이라 로그인 · 저장소 사본이 섞이지 않는다."""
    ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
    pg = ctx.new_page()
    yield pg
    ctx.close()
