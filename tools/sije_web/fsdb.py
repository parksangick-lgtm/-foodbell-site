"""firebase-admin 감싸기 — 관리자 열쇠로 저장소를 연다(보안 규칙을 건너뛴다).

열쇠 파일은 원드라이브 · 저장소 밖(C:\\foodbell-keys)에만 둔다. GitHub 에 올리지 않는다.
"""
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

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
