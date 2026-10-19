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
    """남의 허락 문서는 못 읽는다 (자기 것은 읽힌다 — 아래 test_own_allow_and_viewer_doc_readable_others_not)."""
    id_token(DENIED, allowed=False)
    token = id_token(ALLOWED, allowed=True)
    assert call('GET', f'{base}/allow/{ALLOWED}', token).status_code == 200      # 자기 것은 되고
    assert call('GET', f'{base}/allow/{DENIED}', token).status_code in (403,)     # 남의 것은 막힘


# ---------- 2단계: 서류 5종 (docs) ----------

@pytest.fixture
def doc_id(test_db):
    """시험이 만들 서류 id — 끝나면 관리자 열쇠로 지운다."""
    doc_id = 'rules-doc-' + uuid.uuid4().hex[:8]
    yield doc_id
    test_db.collection('docs').document(doc_id).delete()


def put_doc(base, doc_id, token, kind='sije-quote', html='<p>○○ 김씨 문중 종친회</p>'):
    """서류 한 장을 통째로 쓴다 (없으면 만들기, 있으면 고치기) — 화면의 createDoc 과 같은 칸."""
    return call('PATCH', f'{base}/docs/{doc_id}', token, json={'fields': {
        'kind': {'stringValue': kind}, 'html': {'stringValue': html},
        'label': {'stringValue': '○○ 김씨 문중 종친회'}, 'issue': {'stringValue': '2026년 10월 17일'},
        'total': {'stringValue': ''}}})


def test_docs_allowed_can_create_read_update_delete(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token).status_code == 200
    assert call('GET', f'{base}/docs/{doc_id}', token).status_code == 200
    assert patch(base, f'docs/{doc_id}', token, 'html', '<p>고친 견적서</p>').status_code == 200
    assert call('DELETE', f'{base}/docs/{doc_id}', token).status_code == 200
    assert call('GET', f'{base}/docs/{doc_id}', token).status_code == 404


def test_docs_denied_cannot_read_or_create(base, doc_id, id_token):
    allowed = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, allowed).status_code == 200            # 서류는 있고
    assert call('GET', f'{base}/docs/{doc_id}', allowed).status_code == 200  # 허락된 사람은 읽는다
    denied = id_token(DENIED, allowed=False)
    assert call('GET', f'{base}/docs/{doc_id}', denied).status_code == 403
    assert put_doc(base, doc_id + '-x', denied).status_code == 403
    assert call('DELETE', f'{base}/docs/{doc_id}', denied).status_code == 403
    assert call('GET', f'{base}/docs/{doc_id}').status_code == 403        # 로그인 안 함


def test_docs_unknown_kind_rejected(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token, kind='other').status_code == 403
    assert put_doc(base, doc_id, token, kind='staff-pay').status_code == 200  # 다섯 가지 중 하나는 된다


def test_docs_html_too_long_rejected(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token, html='a' * 300_000).status_code == 403
    assert put_doc(base, doc_id, token, html='a' * 299_999).status_code == 200


def test_docs_update_to_unknown_kind_rejected(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token).status_code == 200
    assert patch(base, f'docs/{doc_id}', token, 'kind', 'other').status_code == 403


# ---------- 일일 일정표 · 직원 보기 명단 (viewers) ----------

VIEWER = 'rules-viewer@example.com'


def test_docs_daily_schedule_kind_allowed(base, doc_id, id_token):
    token = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, token, kind='daily-schedule').status_code == 200


def test_viewer_reads_daily_schedule_only(base, doc_id, id_token):
    owner = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, owner, kind='daily-schedule').status_code == 200
    assert put_doc(base, doc_id + '-pay', owner, kind='staff-pay').status_code == 200
    viewer = id_token(VIEWER, allowed=False, viewer=True)
    try:
        assert call('GET', f'{base}/docs/{doc_id}', viewer).status_code == 200          # 일정표는 읽고
        assert call('GET', f'{base}/docs/{doc_id}-pay', viewer).status_code == 403      # 다른 서류는 막힘
    finally:
        call('DELETE', f'{base}/docs/{doc_id}-pay', owner)


def test_viewer_cannot_write_or_delete(base, doc_id, id_token):
    owner = id_token(ALLOWED, allowed=True)
    assert put_doc(base, doc_id, owner, kind='daily-schedule').status_code == 200
    viewer = id_token(VIEWER, allowed=False, viewer=True)
    assert call('GET', f'{base}/docs/{doc_id}', viewer).status_code == 200              # 읽기는 되는 사람인데
    assert patch(base, f'docs/{doc_id}', viewer, 'html', '<p>몰래 고침</p>').status_code == 403
    assert put_doc(base, doc_id + '-new', viewer, kind='daily-schedule').status_code == 403
    assert call('DELETE', f'{base}/docs/{doc_id}', viewer).status_code == 403
    assert patch(base, f'docs/{doc_id}', owner, 'html', '<p>사장님 고침</p>').status_code == 200   # 주인은 된다


def test_own_allow_and_viewer_doc_readable_others_not(base, id_token):
    """화면이 '나는 보기 전용인가'를 알도록 자기 allow · viewers 문서만 읽힌다."""
    owner = id_token(ALLOWED, allowed=True)
    viewer = id_token(VIEWER, allowed=False, viewer=True)
    assert call('GET', f'{base}/viewers/{VIEWER}', viewer).status_code == 200
    assert call('GET', f'{base}/allow/{ALLOWED}', owner).status_code == 200
    assert call('GET', f'{base}/allow/{ALLOWED}', viewer).status_code == 403
    assert call('GET', f'{base}/viewers/{VIEWER}', owner).status_code == 403
