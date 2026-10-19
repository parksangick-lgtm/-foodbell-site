r"""허락 목록 — 로그인해서 내역서를 볼 수 있는 구글 메일.

규칙 파일(firestore.rules)은 공개 저장소에 올라가므로 메일 주소를 거기 쓰지 않고,
저장소 안 `allow` 묶음에 둔다. 화면에서는 로그인한 사람이 자기 메일 문서 하나만 읽을 수 있고(내가 주인인지 확인),
남의 것 · 목록은 못 읽는다. 고치기는 관리자 열쇠로만.

    python -m tools.sije_web.allow list --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow add 메일주소 --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow remove 메일주소 --key C:\foodbell-keys\sije-admin.json

보기 명단(viewers) — 직원: 일일 일정표만 읽는다(쓰기 · 지우기 · 다른 서류 없음). 그만두면 뺀다.

    python -m tools.sije_web.allow viewer-list --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow viewer-add 메일주소 --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow viewer-remove 메일주소 --key C:\foodbell-keys\sije-admin.json
"""
import argparse
from pathlib import Path

from google.cloud.firestore import SERVER_TIMESTAMP

from tools.sije_web import fsdb


def _doc(db, email: str):
    return db.collection('allow').document(email.strip().lower())


def add(db, email: str):
    _doc(db, email).set({'addedAt': SERVER_TIMESTAMP})


def remove(db, email: str):
    _doc(db, email).delete()


def list_all(db) -> list[str]:
    return sorted(doc.id for doc in db.collection('allow').stream())


def _viewer(db, email: str):
    return db.collection('viewers').document(email.strip().lower())


def add_viewer(db, email: str):
    _viewer(db, email).set({'addedAt': SERVER_TIMESTAMP})


def remove_viewer(db, email: str):
    _viewer(db, email).delete()


def list_viewers(db) -> list[str]:
    return sorted(doc.id for doc in db.collection('viewers').stream())


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.allow', description='허락 목록 · 보기 명단 보기 · 넣기 · 빼기')
    p.add_argument('action', choices=['add', 'remove', 'list', 'viewer-add', 'viewer-remove', 'viewer-list'])
    p.add_argument('email', nargs='?')
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    a = p.parse_args(argv)
    if not a.action.endswith('list') and not a.email:
        p.error('메일 주소를 적어 주세요')
    db = fsdb.open_db(a.key)
    if a.action == 'add':
        add(db, a.email)
    elif a.action == 'remove':
        remove(db, a.email)
    elif a.action == 'viewer-add':
        add_viewer(db, a.email)
    elif a.action == 'viewer-remove':
        remove_viewer(db, a.email)
    for email in (list_viewers if a.action.startswith('viewer') else list_all)(db):
        print(email)


if __name__ == '__main__':
    main()
