r"""인쇄한 내역서 합치기 — '확정 (인쇄 전)' 폴더에 있는 PDF 의 행사에 인쇄 표시(printedAt)를 단다.

10-24 에 확정 63건을 3장씩 인쇄해 묶어 두었다. 그 뒤에 확정한(또는 인쇄 뒤에 고친) 행사 PDF 는 '확정 (인쇄 전)' 에
따로 생긴다(pdf_sync.target_path). 그것들을 인쇄한 뒤 이 명령을 돌리면, 사무실 PC 프로그램이 다음 차례(5분 안)에
'확정' 폴더로 옮긴다. 어느 PDF 가 어느 행사인지는 그 프로그램의 상태 기록에 있으므로 사무실 PC 에서 돌린다.
상태 기록이 없는 PC(노트북 · 집)에서는 멈춘다 — 그냥 두면 '0건' 이 '이미 다 합쳤다' 로 읽힌다(기록장 #96).
그런 PC 에서는 --from-store: 저장소에서 '확정' 이고 인쇄 표시가 없는(인쇄 뒤에 고친 것 포함) 행사를 직접 찾는다 —
PDF 폴더를 정하는 규칙(pdf_sync.printed)과 같은 판단이라 사무실 PC 의 '확정 (인쇄 전)' 폴더와 같은 목록이 나온다.
--expect N: 인쇄한 장 수를 알면 붙인다 — 기다리는 수가 N 과 다르면 아무것도 표시하지 않고 멈춘다.

    python -m tools.sije_web.printed --key C:\foodbell-keys\sije-admin.json --dry-run              # 무엇을 합칠지만
    python -m tools.sije_web.printed --key C:\foodbell-keys\sije-admin.json --expect 23            # 합치기
    python -m tools.sije_web.printed --key C:\foodbell-keys\sije-admin.json --from-store --dry-run # 사무실 밖 PC
"""
import argparse
import sys
from pathlib import Path

from tools.sije_web import fsdb
from tools.sije_web.pdf_sync import PENDING, STATE_FILE, load_state, printed, targets


def waiting(state: dict) -> list[tuple[str, Path]]:
    """'확정 (인쇄 전)' 에 PDF 가 있는 행사 (id, PDF 경로)."""
    rows = ((id, Path(p)) for id, p in state.get('paths', {}).items())
    return sorted((r for r in rows if r[1].parent.name == PENDING), key=lambda r: r[1].name)


def waiting_in_store(db) -> list[tuple[str, str]]:
    """저장소에서 '확정' 이고 인쇄 표시가 없는(또는 인쇄 뒤에 고친) 행사 (id, PDF 이름). 날짜 없는 행사는 PDF 가 없어 뺀다."""
    events = [(d.id, d.to_dict()) for d in db.collection('events').stream()]
    where = targets(Path(), events)
    rows = [(id, where[id].name) for id, ev in events if ev.get('status') == '확정' and not printed(ev) and id in where]
    return sorted(rows, key=lambda r: r[1])


def mark(db, ids: list[str]):
    """인쇄 표시와 고친 시각을 같은 값으로 — 고친 시각이 바뀌니 다음 차례에 다시 그려 '확정' 으로 간다."""
    if ids:
        batch = db.batch()
        for id in ids:
            now = fsdb.firestore.SERVER_TIMESTAMP
            batch.update(db.collection('events').document(id), {'printedAt': now, 'updatedAt': now})
        batch.commit()


def merge(db, state: dict) -> list[str]:
    rows = waiting(state)
    mark(db, [id for id, _ in rows])
    return [p.name for _, p in rows]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.printed', description="인쇄한 '확정 (인쇄 전)' 내역서를 '확정' 으로 합치기")
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    p.add_argument('--dry-run', action='store_true', help='표시하지 않고 무엇을 합칠지만 보여 준다')
    p.add_argument('--from-store', action='store_true', help='PDF 프로그램 상태 기록 대신 저장소에서 찾는다 (어느 PC 에서나)')
    p.add_argument('--expect', type=int, help='기다리는 수가 이 수와 다르면 아무것도 표시하지 않고 멈춘다')
    a = p.parse_args(argv)
    db = None
    if a.from_store:
        db = fsdb.open_db(a.key)
        rows = waiting_in_store(db)
    else:
        state_file = STATE_FILE.with_name(f'state-{a.key.stem}.json')     # office_agent 와 같은 상태 기록
        if not state_file.exists():
            print(f'이 PC 에는 PDF 프로그램 상태 기록이 없습니다 ({state_file}).')
            print('사무실 PC 에서 돌리거나, --from-store 를 붙여 저장소에서 직접 찾습니다. 아무것도 표시하지 않았습니다.')
            return 2
        rows = [(id, path.name) for id, path in waiting(load_state(state_file))]
    for _, name in rows:
        print(name)
    if a.expect is not None and len(rows) != a.expect:
        print(f'기다리는 것이 {len(rows)}건이라 --expect {a.expect} 와 다릅니다. 아무것도 표시하지 않았습니다.')
        return 3
    if not a.dry_run:
        mark(db or fsdb.open_db(a.key), [id for id, _ in rows])
    print(f"{'합칠 것' if a.dry_run else '합침'}: {len(rows)}건")   # 윈도우 한글 창(cp949)이 못 찍는 글자(—)는 쓰지 않는다
    return 0


if __name__ == '__main__':
    sys.exit(main())
