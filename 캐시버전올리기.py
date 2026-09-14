"""index.html 의 css/js 캐시 번호(?v=)를 1씩 올린다.

왜 필요한가
-----------
CSS 나 JS 를 고쳐도 방문자의 브라우저·서비스워커는 이미 받아 둔 옛 파일을
계속 보여준다. 주소 뒤 `?v=21` 숫자를 올려야 "다른 파일"로 보고 새로 받는다.
이 단계를 손으로 기억해서 하면 계속 빠진다 — 실제로 여러 날 옛 화면이
그대로 보인 적이 있다. 그래서 저장.bat 이 이 파일을 대신 불러 준다.

쓰는 법
-------
    python 캐시버전올리기.py           # 올린다
    python 캐시버전올리기.py --check   # 올리지 않고, 올릴 필요가 있는지만 알려준다
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"
SW = HERE / "sw.js"

# 올릴 대상: 사이트 전체가 쓰는 스타일·스크립트. 사진의 ?v= 는 건드리지 않는다
# (사진은 바뀐 것만 따로 올리면 되고, 전부 올리면 손님이 사진을 다 다시 받는다).
TARGETS = ("css/style.css", "js/main.js")


def bump_index(text: str):
    """`css/style.css?v=21` -> `css/style.css?v=22`. 바뀐 내용과 기록을 돌려준다."""
    changes = []

    def repl(match):
        path, number = match.group(1), int(match.group(2))
        changes.append((path, number, number + 1))
        return f"{path}?v={number + 1}"

    pattern = re.compile(r"(" + "|".join(re.escape(t) for t in TARGETS) + r")\?v=(\d+)")
    return pattern.sub(repl, text), changes


def main(argv) -> int:
    check_only = "--check" in argv

    if not INDEX.exists():
        print(f"index.html 을 찾지 못했습니다: {INDEX}")
        return 1

    text = INDEX.read_text(encoding="utf-8")
    new_text, changes = bump_index(text)

    if not changes:
        print("index.html 에서 올릴 ?v= 번호를 찾지 못했습니다.")
        print(f"(찾는 대상: {', '.join(TARGETS)})")
        return 1

    for path, old, new in changes:
        arrow = "올릴 수 있음" if check_only else "올림"
        print(f"  {path}  ?v={old} -> ?v={new}   ({arrow})")

    if check_only:
        return 0

    INDEX.write_text(new_text, encoding="utf-8")

    # 서비스워커 캐시 이름도 함께 올린다. 크게 바뀐 경우 ?v= 만으로는 안 풀리고
    # CACHE 이름까지 올려야 옛 화면이 사라진다.
    if SW.exists():
        sw_text = SW.read_text(encoding="utf-8")
        match = re.search(r"const CACHE = 'foodbell-v(\d+)'", sw_text)
        if match:
            old_v = int(match.group(1))
            sw_text = sw_text.replace(
                f"const CACHE = 'foodbell-v{old_v}'",
                f"const CACHE = 'foodbell-v{old_v + 1}'",
                1,
            )
            SW.write_text(sw_text, encoding="utf-8")
            print(f"  sw.js  CACHE foodbell-v{old_v} -> foodbell-v{old_v + 1}   (올림)")

    print()
    print("캐시 번호를 올렸습니다. 이대로 저장하면 손님 화면에 새 내용이 바로 보입니다.")
    return 0


if __name__ == "__main__":
    # 윈도우 기본 콘솔(cp949)에서도 한글 안내문이 깨지지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    raise SystemExit(main(sys.argv[1:]))
