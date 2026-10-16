"""확정 · 미확정 목록 엑셀 → 줄들, 그리고 내역서와 짝짓기 (날짜 + 장소). 엑셀은 읽기만 한다."""
import re
from pathlib import Path

import openpyxl

from tools.sije_web.sheet_parse import parse_date_text

COLS = ('dateText', 'place', 'phones', 'expected', 'basis', 'confirmed')   # A~F 열


def parse_list(path: Path) -> list[dict]:
    ws = openpyxl.load_workbook(path, data_only=True).active    # 읽기만
    rows = []
    for i, row in enumerate(ws.iter_rows(min_row=2, max_col=6), start=2):
        values = ['' if c.value is None else str(c.value) for c in row]
        if any(values):
            rows.append({'row': i, **dict(zip(COLS, values + [''] * (6 - len(values))))})
    return rows


def _norm(s: str) -> str:
    return re.sub(r'\s+', '', s or '')


def attach_list_rows(events: list[dict], rows: list[dict]) -> list[str]:
    """목록 줄의 예상 날짜 · 근거 · 확정 글자를 짝이 맞는 행사에 붙인다. 못 맞춘 줄은 'N번째 줄' 로 돌려준다
    (손님 값은 화면에 찍지 않으려고 줄 번호만)."""
    by_key = {}
    for ev in events:
        by_key.setdefault((ev['date'], _norm(ev['place'])), []).append(ev)
    problems = []
    for row in rows:
        try:
            date, _ = parse_date_text(row['dateText'])
        except ValueError:
            problems.append(f"{row['row']}번째 줄")
            continue
        hits = by_key.get((date, _norm(row['place'])), [])
        if len(hits) != 1:
            problems.append(f"{row['row']}번째 줄")
            continue
        hits[0].update(expectedDate=row['expected'], basis=row['basis'], confirmedText=row['confirmed'])
    return problems
