"""시험 공용 준비물 — 시험 프로젝트(foodbell-sije-test)만 쓴다. 손님 정보는 넣지 않는다(전부 가짜)."""
import re
from pathlib import Path

import pytest
import requests
from firebase_admin import auth

from tools.sije_web import allow, fsdb

ROOT = Path(__file__).resolve().parents[3]
CONFIG_JS = ROOT / 'js' / 'sije' / 'firebase-config.js'


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
def id_token(test_db):
    """id_token(email, allowed) → 그 메일로 로그인한 사람의 ID 토큰. allowed 면 허락 목록에 넣는다."""
    app = fsdb.app_for(fsdb.KEY_TEST)
    api_key = _test_project_config()['apiKey']
    used = []

    def make(email: str, allowed: bool) -> str:
        try:
            user = auth.get_user_by_email(email, app=app)
        except auth.UserNotFoundError:
            user = auth.create_user(email=email, email_verified=True, app=app)
        (allow.add if allowed else allow.remove)(test_db, email)
        used.append(email)
        custom = auth.create_custom_token(user.uid, app=app).decode()
        r = requests.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken',
                          params={'key': api_key}, json={'token': custom, 'returnSecureToken': True}, timeout=30)
        r.raise_for_status()
        return r.json()['idToken']

    yield make
    for email in used:
        allow.remove(test_db, email)
