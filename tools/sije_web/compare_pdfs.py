r"""옛 PDF(엑셀) ↔ 새 PDF(웹 그리기) 글자 비교 — 파일마다 같음 / 다름(빠진 글자 · 더 생긴 글자).

    python -m tools.sije_web.compare_pdfs "…\2026년 PDF (휴대폰용)" %TEMP%\foodbell-sije\dry1\pdf

공백 · ☐ · 맨 아래 '원본:' 줄은 무시하고, 글자 순서도 보지 않는다(두 PDF 가 표를 읽는 순서가 달라서).
화면에는 파일 이름과 글자 수만 찍고, 어떤 글자가 다른지는 NEW_DIR 안 compare-report.txt 에만 적는다(손님 값).
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf


def pdf_chars(path: Path) -> Counter:
    with pymupdf.open(path) as doc:
        text = '\n'.join(page.get_text() for page in doc)
    text = re.sub(r'^\s*원본:.*$', '', text, flags=re.M)
    return Counter(ch for ch in text if not ch.isspace() and ch != '☐')


def compare(old: Path, new: Path) -> tuple[Counter, Counter]:
    a, b = pdf_chars(old), pdf_chars(new)
    return a - b, b - a      # (빠진 글자, 더 생긴 글자)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print('사용: python -m tools.sije_web.compare_pdfs 옛PDF폴더 새PDF폴더')
        return 2
    old_dir, new_dir = Path(argv[0]), Path(argv[1])
    report, same, diff = [], 0, 0
    for old in sorted(old_dir.rglob('*.pdf')):
        rel = old.relative_to(old_dir)
        new = new_dir / rel
        if not new.exists():
            print(f'{rel}: 새 PDF 없음')
            diff += 1
            continue
        missing, extra = compare(old, new)
        if not missing and not extra:
            same += 1
            print(f'{rel}: 같음')
            continue
        diff += 1
        print(f'{rel}: 다름 (빠진 글자 {sum(missing.values())}개, 더 생긴 글자 {sum(extra.values())}개)')
        report.append(f'{rel}\n  빠진: {"".join(sorted(missing.elements()))}\n  더 생긴: {"".join(sorted(extra.elements()))}')
    (new_dir / 'compare-report.txt').write_text('\n'.join(report), encoding='utf-8')
    print(f'같음 {same} · 다름 {diff}  (자세한 글자: {new_dir / "compare-report.txt"})')
    return 0 if diff == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
