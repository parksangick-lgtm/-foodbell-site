r"""직원 게시판 링크 — 단톡방 공지에 올리는 고정 링크(today.html#암호)를 만들고 바꾼다.

직원은 로그인이 없어서, 링크 속 암호(= share 묶음의 문서 이름)를 아는 사람만 그 게시판 한 장을 읽는다(firestore.rules).
지금 암호는 config/share 에 있고 사장님 화면이 그것을 읽어 일정표를 올린다. 암호를 규칙 · 코드 · 문서에 쓰지 않는다.
직원이 그만두면 new 로 바꾼다 — 올라와 있던 일정은 새 게시판으로 옮기고, 옛 게시판은 지워 옛 링크가 안 열리게 한다.

    python -m tools.sije_web.share_link show --key C:\foodbell-keys\sije-admin.json   # 지금 링크
    python -m tools.sije_web.share_link new  --key C:\foodbell-keys\sije-admin.json   # 처음 만들기 · 바꾸기
    (시험 프로젝트는 --key C:\foodbell-keys\sije-test-admin.json)
"""
import argparse
import secrets
from pathlib import Path

from tools.sije_web import fsdb

LINK = 'https://foodbell.kr/today.html#'


def _config(db):
    return db.collection('config').document('share')


def current_key(db) -> str | None:
    snap = _config(db).get()
    return snap.get('key') if snap.exists else None


def new_key(db) -> str:
    """새 암호로 게시판을 만들고(옛 게시판의 일정을 옮겨서) config/share 를 바꾼 뒤 옛 게시판을 지운다."""
    old = current_key(db)
    old_ref = db.collection('share').document(old) if old else None
    old_snap = old_ref.get() if old_ref else None
    entries = (old_snap.to_dict() or {}).get('entries', {}) if old_snap and old_snap.exists else {}
    key = secrets.token_urlsafe(24)
    batch = db.batch()
    batch.set(db.collection('share').document(key), {'entries': entries})
    batch.set(_config(db), {'key': key})
    if old_ref:
        batch.delete(old_ref)
    batch.commit()
    return key


def link(key: str) -> str:
    return LINK + key


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.share_link', description='직원 게시판 링크 보기 · 새로 만들기')
    p.add_argument('action', choices=['show', 'new'])
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    a = p.parse_args(argv)
    db = fsdb.open_db(a.key)
    key = new_key(db) if a.action == 'new' else current_key(db)
    print(link(key) if key else '아직 없음 - new 로 만드세요')   # 윈도우 한글 창(cp949)이 못 찍는 글자(—)는 쓰지 않는다


if __name__ == '__main__':
    main()
