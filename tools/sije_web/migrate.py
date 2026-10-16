r"""옮기기 — 원드라이브 2026 내역서 엑셀 + 확정 · 미확정 목록 + 빈 양식 → 저장소 (갈아타는 날 아침 한 번).

    연습(쓰지 않음):  python -m tools.sije_web.migrate --excel-root "…\2026년" --lists 확정목록 미확정목록
                          --blanks 빈양식1 빈양식2 빈양식3 --dry-run %TEMP%\foodbell-sije\dry1
    쓰기:             … --write --key C:\foodbell-keys\sije-admin.json

- 엑셀은 읽기만 한다 (저장하면 붙인 그림이 사라진다).
- 엑셀이 열려 있으면(잠금 ~$ 파일) 반쯤 읽지 않고 "엑셀을 닫아 주세요" 로 멈춘다.
- --write 는 문제(읽기 오류 · 짝 안 맞음)가 하나라도 있으면 아무것도 쓰지 않는다.
- 화면에는 손님 값을 찍지 않는다 — 파일 이름 · 칸 이름 · 줄 번호만. 연습 결과는 --dry-run 폴더(%TEMP%)에만.
"""
import argparse
import json
import sys
from pathlib import Path

from tools.sije_web import fsdb
from tools.sije_web.lists_parse import attach_list_rows, parse_list
from tools.sije_web.pdf_sync import pdf_name
from tools.sije_web.sheet_parse import SheetError, event_id, extract_images, parse_sheet, parse_template, shrink_jpeg

ROOT = Path(__file__).resolve().parents[2]


def lock_files(paths: list[Path]) -> list[str]:
    """엑셀이 열려 있으면 같은 폴더에 ~$파일이름 이 생긴다."""
    dirs = {p if p.is_dir() else p.parent for p in paths}
    return sorted({f.name for d in dirs for f in d.rglob('~$*')})


def collect(excel_root: Path, lists: list[Path], blanks: list[Path]):
    """→ (events [(id, ev, images)], templates {name: tpl}, problems [글자])"""
    events, problems = [], []
    for path in sorted(p for p in excel_root.glob('*/*.xlsx') if not p.name.startswith('~$')):
        try:
            ev = parse_sheet(path)
            images = [shrink_jpeg(b) for b in extract_images(path)]
        except SheetError as e:
            problems.append(f'{e.file}: {e.reason}')
            continue
        # 사무실 PC 는 PDF 이름을 날짜 칸에서 새로 짓는다 — 지금 PDF 이름과 다르면 첫 차례에 PDF 가 둘이 된다
        if pdf_name(ev) != path.stem + '.pdf':
            problems.append(f'{path.name}: PDF 이름이 달라짐 (파일 이름의 날짜와 행사일 칸이 다름) → {pdf_name(ev)}')
        events.append((event_id(path.name), ev, images))
    seen = {}
    for i, ev, _ in events:   # id 는 파일 이름에서 나온다 — 같은 이름이 두 폴더에 있으면 하나가 조용히 덮인다
        if i in seen:
            problems.append(f"{ev['sourceFile']}: 같은 파일 이름이 '{seen[i]}' 와 '{ev['status']}' 폴더에 둘 다 있음")
        seen[i] = ev['status']
    by_status = {}
    for _, ev, _ in events:
        by_status.setdefault(ev['status'], []).append(ev)
    for lst in lists:
        status = '미확정' if '미확정' in lst.name else '확정'
        for p in attach_list_rows(by_status.get(status, []), parse_list(lst)):
            problems.append(f'{lst.name}: {p} — 짝이 맞는 내역서(날짜 + 장소)가 없음')
    templates = {}
    for b in blanks:
        try:
            tpl = parse_template(b)
            templates[tpl['name']] = tpl
        except SheetError as e:
            problems.append(f'{e.file}: {e.reason}')
    return events, templates, problems


def dry_run(events, templates, problems, out: Path):
    from tools.sije_web.render_pdf import TooLong, clipped_words, render_pdf, serve_repo
    out.mkdir(parents=True, exist_ok=True)
    (out / 'events.json').write_text(json.dumps(
        [{'id': i, 'event': ev, 'images': len(imgs)} for i, ev, imgs in events], ensure_ascii=False, indent=1),
        encoding='utf-8')
    (out / 'templates.json').write_text(json.dumps(templates, ensure_ascii=False, indent=1), encoding='utf-8')
    with serve_repo(ROOT) as url:
        for _, ev, imgs in events:
            pdf = out / 'pdf' / ev['status'] / pdf_name(ev)     # 사무실 PC 가 쓸 이름 그대로 → 비교가 이름까지 본다
            try:
                pages = render_pdf(ev, imgs, pdf, url)
            except TooLong:
                problems.append(f"{ev['sourceFile']}: A4 한 장에 안 들어감")
                continue
            if pages != 1:
                problems.append(f"{ev['sourceFile']}: PDF 가 {pages}쪽")
            if clipped_words(pdf):
                problems.append(f"{ev['sourceFile']}: 잘린 글자 있음")
    (out / 'problems.txt').write_text('\n'.join(problems), encoding='utf-8')


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):   # 윈도우 콘솔(cp949)에서도 한글이 안 깨지게
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.migrate', description='엑셀 내역서 → 저장소 옮기기')
    p.add_argument('--excel-root', type=Path, required=True, help='확정 · 미확정 · 주문없음 폴더가 있는 2026년 폴더')
    p.add_argument('--lists', type=Path, nargs='+', required=True, help='확정 날짜 목록 · 미확정 목록')
    p.add_argument('--blanks', type=Path, nargs='+', required=True, help='빈 양식 3종')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', type=Path, metavar='OUT', help='쓰지 않고 OUT 폴더에 결과 · PDF 만 만든다')
    mode.add_argument('--write', action='store_true', help='저장소에 쓴다 (--key 필요)')
    p.add_argument('--key', type=Path, help='관리자 열쇠 파일')
    p.add_argument('--force', action='store_true', help='이미 옮긴 행사가 있어도 덮어쓴다 (웹에서 고친 것이 지워진다)')
    a = p.parse_args(argv)
    if a.write and not a.key:
        p.error('--write 에는 --key 가 필요합니다')
    if a.dry_run and a.dry_run.resolve().is_relative_to(ROOT):
        print(f'연습 결과에는 손님 정보가 들어갑니다 — 저장소 밖(예: %TEMP%\\foodbell-sije\\…)에 두세요: {a.dry_run}')
        return 2

    locks = lock_files([a.excel_root, *a.lists, *a.blanks])
    if locks:
        print('엑셀을 닫아 주세요 — 열려 있는 파일:')
        for name in locks:
            print('  ' + name)
        return 1

    events, templates, problems = collect(a.excel_root, a.lists, a.blanks)
    with_images = sum(1 for _, _, imgs in events if imgs)
    print(f'내역서 {len(events)}건 (그림 있는 것 {with_images}건), 빈 양식 {len(templates)}종')

    if a.dry_run:
        dry_run(events, templates, problems, a.dry_run)
        print(f'연습 결과: {a.dry_run}')
    if problems:
        print(f'문제 {len(problems)}건:')
        for x in problems:
            print('  ' + x)
        if a.write:
            print('문제가 있어서 아무것도 쓰지 않았습니다.')
        return 1
    if a.write:
        db = fsdb.open_db(a.key)
        existing = {d.id for d in db.collection('events').select([]).stream()} & {i for i, _, _ in events}
        if existing and not a.force:   # 갈아탄 뒤 다시 돌리면 웹에서 고친 것을 옛 엑셀로 덮는다
            print(f'이미 옮긴 행사가 {len(existing)}건 있습니다 — 웹에서 고친 것이 지워지므로 쓰지 않았습니다.')
            print('정말 다시 옮기려면 --force 를 붙이세요 (갈아타는 날 아침, 웹을 아직 아무도 안 고쳤을 때만).')
            return 1
        for name, tpl in templates.items():
            fsdb.write_template(db, name, tpl)
        for i, ev, imgs in events:
            fsdb.write_event(db, i, ev, imgs)
        print(f'저장소에 썼습니다: 행사 {len(events)}건, 빈 양식 {len(templates)}종')
    return 0


if __name__ == '__main__':
    sys.exit(main())
