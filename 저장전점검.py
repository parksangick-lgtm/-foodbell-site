"""저장(커밋·업로드) 전에 두 가지를 점검한다. 저장.bat 이 부른다.

    python 저장전점검.py --big        무거운 새 파일이 통째로 올라가려는지
    python 저장전점검.py --cache      css/js 를 고치고 캐시 번호(?v=)를 안 올렸는지
    python 저장전점검.py --notpushed  지난번 저장이 GitHub 까지 갔는지 (시작.bat 용)

종료 코드: 0 = 괜찮음 / 1 = 걸린 것이 있음(내용은 화면에 출력) / 2 = 점검 자체가 실패

왜 배치 파일이 아니라 파이썬인가 (두 번 데였다)
-----------------------------------------------
1. 처음에는 이 점검을 저장.bat 안에서 `git ls-files` + `for /f` 로 했는데, git 이
   한글 파일 이름을 `"\354\213\234..."` 처럼 바꿔 내보내는 바람에 `if exist` 가 늘
   실패해서 **6MB 짜리 시험 파일을 그냥 통과시켰다.** 경고가 안 뜨는 것과 점검이
   망가진 것이 화면상 똑같았다.
2. 그래서 점검만 파이썬으로 옮기고 Y/N 묻기는 배치에 두었더니, cmd 가 UTF-8 배치
   파일에서 한글·괄호가 섞인 줄 뒤의 **다음 줄을 갉아먹었다**(`echo` 가 `ho` 로
   읽혀 "명령이 아닙니다" 오류). 같은 구조인데 어떤 파일은 되고 어떤 파일은 깨져서,
   바이트 위치에 따라 불규칙하게 재발한다.

그래서 **묻는 것까지 여기서 한다.** 저장.bat 에는 한글 프롬프트를 두지 않는다.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ask_yes(question: str) -> bool:
    """Y/N 을 묻는다. 묻는 일까지 여기서 하는 이유는 아래 주석 참고."""
    try:
        answer = input(f"  {question} (Y=예 / N=아니오) : ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower().startswith("y")


BIG_BYTES = 5 * 1024 * 1024          # 5MB
HEAVY_SUFFIXES = {".zip", ".psd", ".ai", ".mp4", ".mov", ".pdf", ".tif", ".tiff"}


def run(cmd) -> int:
    """하위 프로그램을 돌린다. 돌리기 전에 내 출력을 먼저 내보낸다 —
    안 그러면 하위 프로그램 출력이 먼저 나와서 순서가 뒤엉켜 읽기 어렵다."""
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(cmd, cwd=HERE).returncode


def git(*args) -> str:
    """git 을 돌리고 표준출력을 돌려준다. 한글 파일 이름이 escape 되지 않게 한다."""
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=HERE, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return result.stdout


def check_big() -> int:
    """새로 올라갈 파일 중 무거운 것을 찾는다."""
    hits = []
    for line in git("ls-files", "--others", "--exclude-standard").splitlines():
        name = line.strip()
        if not name:
            continue
        path = HERE / name
        if not path.is_file():
            continue
        size = path.stat().st_size
        if path.suffix.lower() in HEAVY_SUFFIXES:
            hits.append((name, f"{path.suffix.lower()} 파일, {size / 1048576:.1f}MB"))
        elif size > BIG_BYTES:
            hits.append((name, f"{size / 1048576:.1f}MB"))

    if not hits:
        print("   무거운 새 파일 없음 (통과)")
        return 0

    print("   [확인] 이번에 새로 올라갈 파일 중 무거운 것이 있습니다:")
    for name, why in hits:
        print(f"       - {name}   ({why})")
    print()
    print("   한 번 올라간 큰 파일은 나중에 지워도 저장소 기록에는 남습니다.")
    print()
    if ask_yes("이 파일들도 함께 올릴까요?"):
        return 0
    print()
    print("   저장을 취소합니다. 올리고 싶지 않은 파일은 지우거나 .gitignore 에 넣은 뒤")
    print("   다시 '저장'을 눌러 주세요.")
    return 1


def check_cache() -> int:
    """css/js 를 고쳤는데 index.html 의 ?v= 를 안 올렸는지 본다."""
    changed = git("diff", "--name-only", "HEAD", "--", "css", "js").strip()
    if not changed:
        print("   css/js 변경 없음 (통과)")
        return 0

    # index.html 에서 '+' 로 시작하는(= 새로 넣은) 줄에 ?v= 가 있으면 이미 올린 것.
    diff = git("diff", "HEAD", "--", "index.html").splitlines()
    bumped = any(
        line.startswith("+") and not line.startswith("+++") and "?v=" in line
        for line in diff
    )
    if bumped:
        print("   캐시 번호 이미 올림 (통과)")
        return 0

    print("   [확인] css 나 js 를 고쳤는데 index.html 의 캐시 번호(?v=)가 그대로입니다.")
    print("          이대로 올리면 손님 휴대폰에는 한동안 옛 화면이 보입니다.")
    print()
    for name in changed.splitlines():
        print(f"       고친 파일: {name}")
    print()
    run([sys.executable, str(HERE / "캐시버전올리기.py"), "--check"])
    print()
    if ask_yes("지금 번호를 올려드릴까요?"):
        run([sys.executable, str(HERE / "캐시버전올리기.py")])
    # 번호를 안 올리기로 했어도 저장 자체를 막지는 않는다 (본인 판단).
    return 0


def check_not_pushed() -> int:
    """지난번 저장이 GitHub 까지 갔는지 본다. 시작.bat 이 부른다.

    "저장" 창이 업로드 전에 닫히면 커밋만 되고 안 올라간다. 그러면 저장된 줄 알고
    있다가 사이트가 안 바뀌어서야 알게 된다 — 다음 작업을 시작하는 이 자리가
    알려주기 가장 좋은 지점이다.
    """
    subprocess.run(["git", "fetch"], cwd=HERE, capture_output=True)
    status = git("status", "-sb").splitlines()
    head = status[0] if status else ""
    if "ahead" not in head:
        print("   올라가지 않은 저장은 없습니다.")
        return 0

    print("   [알림] 지난번 '저장'이 GitHub 에 올라가지 않았습니다.")
    print("          (커밋은 됐는데 업로드 전에 창이 닫힌 것 같습니다)")
    print()
    # @{u} = 지금 브랜치가 따라가는 원격 브랜치. 브랜치 이름을 적어두면 나중에 어긋난다.
    for line in git("log", "@{u}..HEAD", "--oneline").splitlines():
        print(f"       안 올라간 저장: {line}")
    print()
    if not ask_yes("지금 올릴까요?"):
        return 0

    if run(["git", "push"]) != 0:
        print("   !! 업로드 실패. 위 메시지를 확인하세요.")
        return 1
    print("   올렸습니다.")
    return 0


def main(argv) -> int:
    if "--big" in argv:
        return check_big()
    if "--cache" in argv:
        return check_cache()
    if "--notpushed" in argv:
        return check_not_pushed()
    print(__doc__)
    return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except BaseException as exc:                     # 점검이 깨진 것과
        print(f"   [점검 실패] {type(exc).__name__}: {exc}")   # 걸린 것이 없는 것을
        print("   (점검이 고장났습니다 - 올릴 파일을 직접 확인해 주세요)")
        raise SystemExit(2)                          # 구분되게 한다
