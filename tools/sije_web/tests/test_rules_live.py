"""보안 규칙 시험 — 시험 프로젝트에 실제 요청(Firestore REST + ID 토큰)을 보내 허락 · 거부를 본다."""
import uuid

import pytest
import requests

ALLOWED = 'rules-allowed@example.com'
DENIED = 'rules-denied@example.com'


@pytest.fixture
def base(test_db):
    return f'https://firestore.googleapis.com/v1/projects/{test_db.project}/databases/(default)/documents'


def _fake(test_db, collection, data):
    doc_id = 'rules-' + uuid.uuid4().hex[:8]
    ref = test_db.collection(collection).document(doc_id)
    ref.set(data)
    return doc_id, ref


@pytest.fixture
def fake_event(test_db):
    doc_id, ref = _fake(test_db, 'events', {'status': '확정', 'place': '가짜동 1-1', 'memo': ''})
    yield doc_id
    ref.delete()


@pytest.fixture
def fake_template(test_db):
    doc_id, ref = _fake(test_db, 'templates', {'name': '가짜상', 'items': {}})
    yield doc_id
    ref.delete()


def call(method, url, token=None, **kw):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    return requests.request(method, url, headers=headers, timeout=30, **kw)


def patch(base, path, token, field, value):
    """칸 하나만 고친다 (updateMask) — 화면이 하는 칸 단위 저장과 같다."""
    return call('PATCH', f'{base}/{path}', token, params={'updateMask.fieldPaths': field},
                json={'fields': {field: {'stringValue': value}}})


def test_allowed_can_read_and_update_event(base, fake_event, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert call('GET', f'{base}/events/{fake_event}', token).status_code == 200
    assert patch(base, f'events/{fake_event}', token, 'memo', '고친 메모').status_code == 200


def test_denied_user_gets_403_on_read(base, fake_event, id_token):
    token = id_token(DENIED, allowed=False)
    assert call('GET', f'{base}/events/{fake_event}', token).status_code == 403
    assert patch(base, f'events/{fake_event}', token, 'memo', '몰래').status_code == 403


def test_signed_out_gets_403(base, fake_event):
    assert call('GET', f'{base}/events/{fake_event}').status_code == 403


def test_allowed_cannot_delete_event(base, fake_event, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert call('GET', f'{base}/events/{fake_event}', token).status_code == 200  # 읽기는 되는 사람인데
    assert call('DELETE', f'{base}/events/{fake_event}', token).status_code == 403


def test_status_must_be_one_of_three(base, fake_event, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert patch(base, f'events/{fake_event}', token, 'status', '미확정').status_code == 200  # 세 가지 중 하나는 되고
    assert patch(base, f'events/{fake_event}', token, 'status', '취소').status_code == 403


def test_templates_read_only_for_allowed(base, fake_template, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert call('GET', f'{base}/templates/{fake_template}', token).status_code == 200
    assert patch(base, f'templates/{fake_template}', token, 'name', '바꿈').status_code == 403


def test_allow_collection_unreadable(base, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert call('GET', f'{base}/allow/{ALLOWED}', token).status_code == 403
