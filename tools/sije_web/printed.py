r"""인쇄한 내역서 합치기 — '확정 (인쇄 전)' 폴더에 있는 PDF 의 행사에 인쇄 표시(printedAt)를 단다.

10-24 에 확정 63건을 3장씩 인쇄해 묶어 두었다. 그 뒤에 확정한(또는 인쇄 뒤에 고친) 행사 PDF 는 '확정 (인쇄 전)' 에
따로 생긴다(pdf_sync.target_path). 그것들을 인쇄한 뒤 이 명령을 돌리면, 사무실 PC 프로그램이 다음 차례(5분 안)에
'확정' 폴더로 옮긴다. 어느 PDF 가 어느 행사인지는 그 프로그램의 상태 기록에 있으므로 사무실 PC 에서 돌린다.

    python -m tools.sije_web.printed --key C:\foodbell-keys\sije-admin.json --dry-run   # 무엇을 합칠지만
    python -m tools.sije_web.printed --key C:\foodbell-keys\sije-admin.json             # 합치기
"""
import argparse
from pathlib import Path

from tools.sije_web import fsdb
from tools.sije_web.pdf_sync import PENDING, STATE_FILE, load_state


def waiting(state: dict) -> list[tuple[str, Path]]:
    """'확정 (인쇄 전)' 에 PDF 가 있는 행사 (id, PDF 경로)."""
    rows = ((id, Path(p)) for id, p in state.get('paths', {}).items())
    return sorted((r for r in rows if r[1].parent.name == PENDING), key=lambda r: r[1].name)


def merge(db, state: dict) -> list[str]:
    """인쇄 표시와 고친 시각을 같은 값으로 — 고친 시각이 바뀌니 다음 차례에 다시 그려 '확정' 으로 간다."""
    rows = waiting(state)
    if rows:
        batch = db.batch()
        for id, _ in rows:
            now = fsdb.firestore.SERVER_TIMESTAMP
            batch.update(db.collection('events').document(id), {'printedAt': now, 'updatedAt': now})
        batch.commit()
    return [p.name for _, p in rows]


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.printed', description="인쇄한 '확정 (인쇄 전)' 내역서를 '확정' 으로 합치기")
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    p.add_argument('--dry-run', action='store_true', help='표시하지 않고 무엇을 합칠지만 보여 준다')
    a = p.parse_args(argv)
    state = load_state(STATE_FILE.with_name(f'state-{a.key.stem}.json'))     # office_agent 와 같은 상태 기록
    names = [p.name for _, p in waiting(state)] if a.dry_run else merge(fsdb.open_db(a.key), state)
    for n in names:
        print(n)
    print(f"{'합칠 것' if a.dry_run else '합침'}: {len(names)}건")   # 윈도우 한글 창(cp949)이 못 찍는 글자(—)는 쓰지 않는다


if __name__ == '__main__':
    main()
