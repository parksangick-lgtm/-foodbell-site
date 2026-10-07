"""사이트와 서류 5종을 휴대폰 폭(390px)으로 찍는다. 찍을 때마다 실제 폭을 되읽어 출력한다.

왜 필요한가
-----------
헤드리스 크롬에 --window-size=390 을 주면 실제로는 약 485px 로 잡혀서, 없는 버그를
세 번 쫓았다. 매번 클로드가 캡처 코드를 새로 짜다 보니 재는 방법이 틀렸다.
그래서 한 번 검증한 이 도구로 늘 같은 방법으로 찍는다.

- 폭은 Playwright 로 만들고, 찍기 전에 clientWidth 를 되읽어 390 이 아니면 "측정 실패".
- 사이트 css 가 html·body 에 overflow-x: hidden 을 걸어 두어서 "화면보다 넓은가"만 재면
  넘친 글자가 잘려도 "넘침 없음"으로 나온다. 그래서 오른쪽 끝을 넘어간 요소를 하나씩 찾는다.
- 매번 먼저 자체 시험을 한다 — 반드시 걸려야 하는 쪽과 반드시 조용해야 하는 쪽을
  같이 돌려, 둘 다 기대대로일 때만 결과를 믿는다.
- 사진은 작업 폴더 밖(임시 폴더)에 저장한다. 작업 폴더에 두면 자동 저장이 GitHub 에
  올리고 버셀이 foodbell.kr/사진이름.png 로 공개한다.
- 쪽마다 새 브라우저 프로필로 연다 — 서류에 저장된 옛 입력값이 찍히지 않는다.

쓰는 법
-------
    python -m http.server 8123          (미리보기 서버 — 다른 창에서)
    python 휴대폰캡처.py                 6쪽 모두
    python 휴대폰캡처.py index.html      고른 쪽만
    python 휴대폰캡처.py --tag before    고치기 전 기준 사진 (폴더 이름에 before 가 붙는다)

종료 코드: 0 = 모두 정상 / 1 = 넘침·측정 실패·서버 꺼짐 / 2 = 자체 시험 실패(도구 고장)
"""

import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8123/"
WIDTH = 390
PAGES = ["index.html", "sije-quote.html", "event-quote.html",
         "sije-worksheet.html", "statement.html", "staff-pay.html"]

# 오른쪽 끝(clientWidth)을 넘어간 요소를 찾는다. 빼는 것:
#  - 크기 0·숨김 요소, 통째로 화면 밖에 둔 것(접힌 메뉴 — 왼쪽 끝도 화면 밖)
#  - 화면 안에 있는 가로 스크롤 상자 속 내용(견적서 표처럼 일부러 밀어 보는 것)
# 넘친 것들 중 가장 바깥 요소만 남긴다.
OVERFLOW_JS = """() => {
  const cw = document.documentElement.clientWidth;
  const contained = (el) => {
    for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
      const ox = getComputedStyle(a).overflowX;
      if (ox !== 'visible' && a.getBoundingClientRect().right <= cw + 1) return true;
    }
    return false;
  };
  const hits = [];
  for (const el of document.body.querySelectorAll('*')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right <= cw + 1 || r.left >= cw) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
    if (contained(el)) continue;
    hits.push(el);
  }
  const outer = hits.filter(el => !hits.some(o => o !== el && o.contains(el)));
  const name = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\\s+/).join('.') : '');
  return { cw, items: outer.slice(0, 5).map(el => name(el) + ' (오른쪽 끝 ' + Math.round(el.getBoundingClientRect().right) + 'px)'),
           count: outer.length };
}"""

# 자체 시험용 쪽 — 사이트처럼 html 에 overflow-x: hidden 을 건다.
TEST_HEAD = ('<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<style>html,body{margin:0;overflow-x:hidden}</style>')
SELF_TESTS = [
    ("빈 쪽", "", 0),
    ("600px 상자 (잘려서 안 보이는 넘침)", '<div style="width:600px;height:20px"></div>', 1),
    ("가로 스크롤 상자 속 넓은 표", '<div style="width:300px;overflow-x:auto">'
                                 '<div style="width:600px;height:20px"></div></div>', 0),
]


def new_page(browser):
    ctx = browser.new_context(viewport={"width": WIDTH, "height": 844},
                              device_scale_factor=2, is_mobile=True, has_touch=True)
    return ctx, ctx.new_page()


def self_test(browser) -> bool:
    ok = True
    for label, body, want in SELF_TESTS:
        ctx, page = new_page(browser)
        page.set_content(f"<!doctype html><html><head>{TEST_HEAD}</head><body>{body}</body></html>")
        r = page.evaluate(OVERFLOW_JS)
        ctx.close()
        good = r["cw"] == WIDTH and r["count"] == want
        ok &= good
        print(f"  {'통과' if good else '★실패'}  {label}: 폭 {r['cw']}, 넘친 요소 {r['count']}개 (기대 {want}개)")
    return ok


def main(argv) -> int:
    tag = ""
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    pages = argv or PAGES

    try:
        urllib.request.urlopen(BASE, timeout=3)
    except OSError:
        print(f"미리보기 서버가 꺼져 있습니다: {BASE}")
        print("다른 창에서 이 폴더에 대고  python -m http.server 8123  을 먼저 실행하세요.")
        return 1

    out = Path(tempfile.gettempdir()) / "foodbell-phone" / (time.strftime("%Y%m%d-%H%M%S") + (f"-{tag}" if tag else ""))
    if HERE in out.resolve().parents:
        print(f"사진 폴더가 작업 폴더 안입니다 — 자동 저장으로 공개되므로 멈춥니다: {out}")
        return 1
    out.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright 가 없습니다. 이 컴퓨터에서 한 번만:")
        print("  python -m pip install playwright")
        print("  python -m playwright install chromium")
        return 1

    bad = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        print("자체 시험 (도구가 넘침을 제대로 잡는지):")
        if not self_test(browser):
            browser.close()
            print("\n자체 시험 실패 — 도구가 고장났습니다. 아래 결과를 믿지 마세요.")
            return 2

        print(f"\n{'쪽':<22}{'폭':>5}  결과")
        for name in pages:
            ctx, page = new_page(browser)
            try:
                page.goto(BASE + name, wait_until="networkidle", timeout=20000)
            except Exception:
                page.goto(BASE + name, wait_until="load", timeout=20000)
            page.evaluate("document.fonts.ready.then(() => 1)")
            r = page.evaluate(OVERFLOW_JS)
            shot = out / (Path(name).stem + ".png")
            page.screenshot(path=str(shot), full_page=True)
            ctx.close()

            if r["cw"] != WIDTH:
                bad += 1
                result = f"★측정 실패 — 폭이 {WIDTH} 이 아님. 이 사진으로 판단하지 말 것"
            elif r["count"]:
                bad += 1
                result = f"★넘침 {r['count']}곳: " + ", ".join(r["items"])
            else:
                result = "넘침 없음"
            print(f"{name:<22}{r['cw']:>5}  {result}")
        browser.close()

    print(f"\n사진 폴더 (작업 폴더 밖이라 GitHub 에 안 올라감): {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    # 윈도우 기본 콘솔(cp949)에서도 한글 안내문이 깨지지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    raise SystemExit(main(sys.argv[1:]))
