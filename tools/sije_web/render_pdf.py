r"""행사 → A4 PDF.

저장소 폴더를 이 컴퓨터 안에서만 여는 서버를 띄우고, sije-print.html 을 헤드리스 크롬(Playwright)으로 열어 PDF 로 저장한다.
웹 화면의 `인쇄` 와 같은 그리기(js/sije/sheet-render.js)를 쓰므로 둘이 똑같이 나온다.
"""
import base64
import contextlib
import datetime
import functools
import http.server
import json
import threading
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

MARGIN = {'top': '0.3in', 'bottom': '0.3in', 'left': '0.25in', 'right': '0.25in'}   # css/sije-sheet.css 의 @page 와 같게


class TooLong(Exception):
    """가장 작게 줄여도 A4 한 장에 들어가지 않는다."""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def serve_repo(root: Path):
    """root 폴더를 http://127.0.0.1:빈포트/ 로 연다 (이 컴퓨터 안에서만)."""
    handler = functools.partial(_QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}/'
    finally:
        server.shutdown()
        server.server_close()


def _plain(v):
    """저장소의 시각 값은 ISO 글자로 넘긴다."""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    raise TypeError(f'JSON 으로 못 바꾸는 값: {type(v).__name__}')


def render_pdf(ev: dict, images: list[bytes], out: Path, base_url: str) -> int:
    """PDF 를 out 에 만들고 쪽수를 돌려준다. 한 장에 안 들어가면 TooLong."""
    data = {'event': ev, 'images': ['data:image/jpeg;base64,' + base64.b64encode(b).decode() for b in images]}
    script = 'window.__SIJE__ = ' + json.dumps(data, ensure_ascii=False, default=_plain) + ';'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.add_init_script(script)
            page.goto(base_url + 'sije-print.html')
            page.wait_for_selector('body[data-ready="1"]', state='attached', timeout=30_000)
            if page.evaluate('document.body.dataset.overflow') == '1':
                raise TooLong(f'A4 한 장에 안 들어갑니다: {ev.get("titlePlace", "")} {ev.get("date", "")}')
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            page.pdf(path=str(out), format='A4', print_background=True, margin=MARGIN)
        finally:
            browser.close()
    with pymupdf.open(out) as doc:
        return doc.page_count


def clipped_words(pdf: Path) -> list[str]:
    r"""가로 테두리선이 글자 한가운데를 지나가는 글자 = 잘린 글자 (`_만들기 프로그램\find_clip.py` 와 같은 방법, 첫 쪽)."""
    with pymupdf.open(pdf) as doc:
        page = doc[0]
        lines = []   # (y, x0, x1)
        for d in page.get_drawings():
            for it in d['items']:
                if it[0] == 'l' and abs(it[1].y - it[2].y) < 0.5:
                    lines.append((it[1].y, min(it[1].x, it[2].x), max(it[1].x, it[2].x)))
                elif it[0] == 're' and it[1].height < 2 and it[1].width > 5:
                    r = it[1]
                    lines.append(((r.y0 + r.y1) / 2, r.x0, r.x1))
        bad = set()
        for x0, y0, x1, y1, word, *_ in page.get_text('words'):
            for y, a, b in lines:
                if y0 + 2.5 < y < y1 - 2.5 and a < (x0 + x1) / 2 < b:
                    bad.add(word)
    return sorted(bad)
