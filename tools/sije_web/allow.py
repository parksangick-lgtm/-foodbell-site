r"""허락 목록 — 로그인해서 내역서를 볼 수 있는 구글 메일.

규칙 파일(firestore.rules)은 공개 저장소에 올라가므로 메일 주소를 거기 쓰지 않고,
저장소 안 `allow` 묶음에 둔다. 이 묶음은 화면에서 아무도 못 읽고, 관리자 열쇠로만 고친다.

    python -m tools.sije_web.allow list --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow add 메일주소 --key C:\foodbell-keys\sije-admin.json
    python -m tools.sije_web.allow remove 메일주소 --key C:\foodbell-keys\sije-admin.json
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


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.allow', description='허락 목록 보기 · 넣기 · 빼기')
    p.add_argument('action', choices=['add', 'remove', 'list'])
    p.add_argument('email', nargs='?')
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    a = p.parse_args(argv)
    if a.action != 'list' and not a.email:
        p.error('메일 주소를 적어 주세요')
    db = fsdb.open_db(a.key)
    if a.action == 'add':
        add(db, a.email)
    elif a.action == 'remove':
        remove(db, a.email)
    for email in list_all(db):
        print(email)


if __name__ == '__main__':
    main()
