"""서류 최종 점검 — 서류 여섯 가지를 휴대폰 폭(390px)에서 가짜 내용으로 채워
① 편집 화면 ② 보기 화면(넘침 재기) ③ '파일로 저장' 사진 ④ A4 인쇄(PDF)를 만들고, 서류마다 한 장짜리 모아보기를 만든다.

왜 필요한가
-----------
휴대폰캡처.py 는 '빈 서류가 옆으로 안 넘친다' 만 본다. 2026-10-26 하루 동안 고친 서류 고장은 전부 그 도구가 안 만드는
결과물(줄을 채운 화면 · 보낸 사진 · 인쇄)에 있었다(기록장 #75). 그날 한 번 짜서 쓴 점검을 그대로 옮겨 왔다.

- 시험 프로젝트에 가짜 계정으로 들어가 새 서류를 만들고(휴대폰캡처.py 의 DocLogin) 끝나면 지운다.
  시험 열쇠(C:\\foodbell-keys\\sije-test-admin.json)가 있어야 돈다. 손님 정보는 전부 가짜.
- 서류 시험(pytest)과 같이 돌리지 않는다 — 시험의 no_daily 가 시험 프로젝트의 일정표를 지운다.
- 결과는 작업 폴더 밖(임시 폴더)에 둔다. 작업 폴더에 두면 자동 저장으로 foodbell.kr 에 공개된다.
- 화면 폭을 되읽어 390 이 아니면 '측정 실패'. 숫자(넘침 · 사진 장수 · 쪽수)가 맞아도 모아보기 사진은 눈으로 본다.

쓰는 법
-------
    python -m http.server 8123                  (미리보기 서버 — 다른 창에서)
    python -X utf8 서류최종점검.py               여섯 가지 모두 (3분쯤)
    python -X utf8 서류최종점검.py staff-pay.html   고른 것만

종료 코드: 0 = 넘침 · 화면 오류 없음 / 1 = 넘침 · 화면 오류 · 측정 실패 · 서버 꺼짐 · 열쇠 없음
"""

import importlib.util
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGES = ["staff-pay.html", "daily-schedule.html", "sije-quote.html", "event-quote.html", "statement.html", "sije-worksheet.html"]

# 줄 채우기 — 칸 이름(data-f · data-k)만 넘기고 선택자는 JS 안에서 만든다 (선택자 글을 querySelector 에 넘기지 않는다, 기록장 #93)
SET_JS = """(rows) => { rows.forEach((v, i) => { const tr = document.querySelectorAll('tr.item')[i];
  for (const [k, t] of Object.entries(v)) {
    const e = tr.querySelector(`[data-f="${k}"]`) || tr.querySelector(`[data-k="${k}"]`);
    if (!e) continue;
    e.textContent = t;
    e.dispatchEvent(new Event('input', { bubbles: true }));
    e.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
  } }); }"""
ONE_JS = """(e, t) => { e.textContent = t;
  e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new FocusEvent('focusout', { bubbles: true })); }"""

STAFF = [{"name": f"가짜{i}", "tel": f"010-0000-000{i}", "date": "10/31 (금)", "event": "가짜시 시제 출장",
          "acct": f"가짜은행 000-0000-000{i}", "pay": "150000"} for i in (1, 2, 3)]
DAILY = [{"staff": "가짜일 · 가짜이", "car": "1톤 탑차", "time": "오전 9시", "place": "가짜시 가짜동 선산", "tel": "010-0000-0001",
          "work": "시제 상차림 2상", "people": "30명", "price": "35만"},
         {"staff": "가짜삼", "time": "오전 11시", "place": "가짜군 가짜면 묘소", "tel": "010-0000-0002", "work": "제사상 1상", "price": "40만"},
         {"staff": "가짜사 · 가짜오", "time": "오후 1시", "place": "가짜구 가짜동 회관", "tel": "010-0000-0003", "work": "출장음식",
          "people": "40명", "price": "5만", "memo": "가짜 메모"}]


def one(pg, sel, text):
    pg.locator(sel).first.evaluate(ONE_JS, text)


def fill(pg, name):
    if name in ("staff-pay.html", "daily-schedule.html"):
        rows = STAFF if name == "staff-pay.html" else DAILY
        while pg.evaluate("document.querySelectorAll('tr.item').length") < len(rows):
            pg.click("tr.addrow button")
        pg.evaluate(SET_JS, rows)
        one(pg, '[data-k="memo"]', "가짜 전달 메모입니다")
    elif name in ("sije-quote.html", "event-quote.html"):
        one(pg, '[data-k="supply"]', "1000000")
    elif name == "statement.html":
        pg.evaluate(SET_JS, [{"price": "500000"}])


def sheet(out, name, cols, font):
    """여러 그림을 높이 1400 으로 맞춰 가로로 붙인 모아보기."""
    from PIL import Image, ImageDraw
    H, gap, top = 1400, 30, 60
    ims = []
    for title, path in cols:
        im = Image.open(path).convert("RGB")
        ims.append((title, im.resize((round(im.width * H / im.height), H))))
    canvas = Image.new("RGB", (gap + sum(i.width + gap for _, i in ims), top + H + gap), "#EDE6DA")
    dr = ImageDraw.Draw(canvas)
    x = gap
    for title, im in ims:
        dr.text((x, 14), title, font=font, fill="#6E1E2B")
        canvas.paste(im, (x, top))
        x += im.width + gap
    path = out / f"모아보기-{name}.png"
    canvas.save(path)
    return path


def check(b, cap, login, out, name, font):
    import pymupdf
    stem = name.split(".")[0]
    ctx, pg = cap.new_page(b)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())          # 같은 날짜 일정표가 있으면 '그래도 새로 만들기' · 금액 빈 줄 확인
    try:
        login.open_new_doc(pg, name)
        cw = pg.evaluate("document.documentElement.clientWidth")
        pg.click("#btn-edit")
        fill(pg, name)
        pg.wait_for_timeout(400)
        pg.evaluate("window.scrollTo(0, 0)")
        ov_edit = pg.evaluate(cap.OVERFLOW_JS)
        pg.screenshot(path=str(out / f"{stem}-1-edit.png"), full_page=True)
        pg.click("#btn-edit")
        pg.wait_for_timeout(600)
        pg.evaluate("window.scrollTo(0, 0)")
        ov_view = pg.evaluate(cap.OVERFLOW_JS)
        pg.screenshot(path=str(out / f"{stem}-2-view.png"), full_page=True)
        # 사진 ('파일로 저장')
        pg.wait_for_function("typeof html2canvas === 'function'", timeout=20000)
        got = []
        pg.on("download", lambda d: got.append(d))
        pg.click("#btn-save-file")
        pg.locator("#btn-save-file", has_text="저장 중").wait_for(timeout=10000)
        pg.locator("#btn-save-file", has_text="파일로 저장").wait_for(timeout=90000)
        pg.wait_for_timeout(1500)
        photos = []
        from PIL import Image
        for i, d in enumerate(got):
            path = out / f"{stem}-3-photo-{i + 1}.png"
            d.save_as(str(path))
            with Image.open(path) as im:
                photos.append((path, im.size))
        # 인쇄 (A4 PDF)
        pdf = out / f"{stem}-4-print.pdf"
        pg.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
        doc = pymupdf.open(pdf)
        prints = []
        for i, page in enumerate(doc):
            path = out / f"{stem}-4-print-{i + 1}.png"
            page.get_pixmap(dpi=110).save(str(path))
            prints.append(path)
        npages = doc.page_count
        doc.close()
    finally:
        ctx.close()
    bad = cw != cap.WIDTH or ov_edit["count"] or ov_view["count"] or errors or not photos
    print(f"[{stem}] 화면 폭 {cw}{' ★측정 실패' if cw != cap.WIDTH else ''} | 넘침 편집 {ov_edit['count']} 보기 {ov_view['count']}"
          f" {ov_edit['items'] + ov_view['items']} | 사진 {len(photos)}장 " + ", ".join(f"{w}x{h}" for _, (w, h) in photos)
          + f" | 인쇄 {npages}쪽 | 화면 오류 {errors or '없음'}")
    cols = [("편집 화면", out / f"{stem}-1-edit.png"), ("보기 화면", out / f"{stem}-2-view.png")]
    cols += [(f"사진 {i + 1}", pth) for i, (pth, _) in enumerate(photos)]
    cols += [(f"인쇄 {i + 1}쪽", pth) for i, pth in enumerate(prints)]
    print("   모아보기:", sheet(out, stem, cols, font))
    return not bad


def main(argv) -> int:
    pages = argv or PAGES
    spec = importlib.util.spec_from_file_location("capture", HERE / "휴대폰캡처.py")
    cap = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(cap)
    try:
        urllib.request.urlopen(cap.BASE, timeout=3)
    except OSError:
        print(f"미리보기 서버가 꺼져 있습니다: {cap.BASE}")
        print("다른 창에서 이 폴더에 대고  python -m http.server 8123  을 먼저 실행하세요.")
        return 1
    out = Path(tempfile.gettempdir()) / "foodbell-final" / time.strftime("%Y%m%d-%H%M%S")
    if HERE in out.resolve().parents:
        print(f"결과 폴더가 작업 폴더 안입니다 — 자동 저장으로 공개되므로 멈춥니다: {out}")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
        import pymupdf  # noqa: F401 — 인쇄 쪽을 그림으로
        from PIL import ImageFont
    except ImportError as e:
        print(f"부품이 없습니다: {e} — python -m pip install playwright pymupdf pillow")
        return 1
    font = ImageFont.truetype(r"C:\Windows\Fonts\malgunbd.ttf", 28)
    try:
        login = cap.DocLogin()
    except Exception as e:
        print(f"시험 프로젝트에 못 들어갑니다 ({e.__class__.__name__}: {e})")
        return 1
    ok = True
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for name in pages:
                try:
                    ok &= check(b, cap, login, out, name, font)
                except Exception as e:   # 한 서류가 막혀도 나머지는 본다
                    ok = False
                    print(f"[{name.split('.')[0]}] ★점검 못 함 — {e.__class__.__name__}: {str(e).splitlines()[0]}")
            b.close()
    finally:
        login.close()
    print(f"\n결과 폴더 (작업 폴더 밖이라 GitHub 에 안 올라감): {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    raise SystemExit(main(sys.argv[1:]))
