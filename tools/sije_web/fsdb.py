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
