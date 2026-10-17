"""firebase-admin 감싸기 — 관리자 열쇠로 저장소를 연다(보안 규칙을 건너뛴다).

열쇠 파일은 원드라이브 · 저장소 밖(C:\\foodbell-keys)에만 둔다. GitHub 에 올리지 않는다.
"""
import os
import ssl
import tempfile
from pathlib import Path

import certifi


def _trust_windows_certs():
    """백신(Avast 등)이 보안 연결을 중간에서 검사하면 그 백신의 인증서는 윈도우 목록에만 있다.
    파이썬(requests)과 gRPC 는 윈도우 목록을 보지 않아 연결이 실패하므로(2026-10-16 노트북에서 겪음),
    원래 목록(certifi) + 윈도우 ROOT 목록을 합친 파일을 쓰게 한다. 저장소에 붙기 전에 불러야 한다."""
    if not hasattr(ssl, 'enum_certificates'):
        return
    pems = [Path(certifi.where()).read_text(encoding='utf-8')]
    for der, encoding, trust in ssl.enum_certificates('ROOT'):
        if encoding == 'x509_asn' and (trust is True or '1.3.6.1.5.5.7.3.1' in trust):
            pems.append(ssl.DER_cert_to_PEM_cert(der))
    out = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'foodbell-sije' / 'ca-bundle.pem'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(''.join(pems), encoding='utf-8')
    os.environ.setdefault('REQUESTS_CA_BUNDLE', str(out))
    os.environ.setdefault('GRPC_DEFAULT_SSL_ROOTS_FILE_PATH', str(out))


_trust_windows_certs()

import firebase_admin  # noqa: E402 — 위에서 인증서를 먼저 정한 뒤 불러온다
from firebase_admin import credentials, firestore  # noqa: E402

KEY_PROD = Path(r"C:\foodbell-keys\sije-admin.json")
KEY_TEST = Path(r"C:\foodbell-keys\sije-test-admin.json")


def app_for(key: Path) -> firebase_admin.App:
    """열쇠 하나에 앱 하나 — 실제와 시험을 한 프로그램에서 같이 열 수 있게."""
    name = str(Path(key).resolve())
    try:
        return firebase_admin.get_app(name)
    except ValueError:
        return firebase_admin.initialize_app(credentials.Certificate(str(key)), name=name)


def open_db(key: Path):
    return firestore.client(app_for(key))


def write_event(db, id: str, ev: dict, images: list[bytes]):
    """행사 문서 + 그림(images/0, 1, …). 같은 id 로 다시 쓰면 덮어쓴다 (옮기기를 두 번 해도 하나)."""
    from PIL import Image
    import io
    ref = db.collection('events').document(id)
    ref.set({**ev, 'updatedAt': firestore.SERVER_TIMESTAMP})
    for old in ref.collection('images').stream():
        old.reference.delete()
    for n, data in enumerate(images):
        w, h = Image.open(io.BytesIO(data)).size
        ref.collection('images').document(str(n)).set({'order': n, 'bytes': data, 'width': w, 'height': h})


class FirestoreSource:
    """사무실 PC 프로그램이 읽는 저장소 — 바뀐 행사(updatedAt 기준) · 그림 · 전체."""

    def __init__(self, db):
        self.db = db

    def changed_since(self, since: str | None) -> list[tuple[str, dict]]:
        from datetime import datetime
        from google.cloud.firestore_v1.base_query import FieldFilter
        q = self.db.collection('events')
        if since:
            q = q.where(filter=FieldFilter('updatedAt', '>', datetime.fromisoformat(since)))
        rows = [(d.id, d.to_dict()) for d in q.stream()]
        return sorted(rows, key=lambda x: str(x[1].get('updatedAt') or ''))

    def images(self, id: str) -> list[bytes]:
        docs = self.db.collection('events').document(id).collection('images').order_by('order').stream()
        return [d.get('bytes') for d in docs]

    def all_events(self) -> list[tuple[str, dict]]:
        return [(d.id, d.to_dict()) for d in self.db.collection('events').stream()]

    def all_docs(self) -> list[tuple[str, dict]]:
        """2단계 서류 5종 전체 (하루 한 번 백업용)."""
        return [(d.id, d.to_dict()) for d in self.db.collection('docs').stream()]


def write_template(db, name: str, tpl: dict):
    db.collection('templates').document(name).set({'name': name, 'items': tpl['items'], 'itemRows': tpl.get('itemRows', 0)})
