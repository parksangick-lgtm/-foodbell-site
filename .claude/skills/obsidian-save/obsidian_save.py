"""옵시디언(Obsidian) 볼트에 마크다운 노트를 저장한다.

옵시디언 볼트는 특별한 데이터베이스가 아니라 그냥 `.md` 파일이 들어 있는 폴더다.
그래서 저장은 "정해진 폴더에 마크다운 파일을 쓰는 것"이 전부다.

이 파일은 일부러 표준 라이브러리만 쓴다. pip 설치 없이 단독 실행할 수 있어야
요약 기능과 상관없이 어디서든 노트를 저장할 수 있기 때문이다.

볼트 경로는 옵시디언 설정 파일(obsidian.json)에서 자동으로 찾는다. 그래서 보통은
사용자가 경로를 직접 찾아 입력하지 않아도 된다.

사용 예:
    python src/obsidian_save.py --list-vaults          # 볼트 찾기
    python src/obsidian_save.py --title "제목" --folder "유튜브 요약" \
        --tags 유튜브,요약 --source "https://youtu.be/..." < 본문.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 옵시디언과 윈도우에서 파일 이름에 쓸 수 없는 글자.
# #, ^, [, ] 는 파일 이름에는 들어가지만 [[내부링크]]를 깨뜨려서 같이 지운다.
FORBIDDEN_FILENAME_CHARS = r'[\\/:*?"<>|#^\[\]]'

# 파일 이름 최대 길이(바이트). 대부분의 파일 시스템 한계가 255바이트라서
# 날짜 접두사와 ".md" 를 붙일 여유를 두고 잡았다.
MAX_FILENAME_BYTES = 150

# 볼트 경로를 기억해 두는 파일. 이게 있으면 어느 폴더에서 실행하든 볼트를 찾는다.
# (.env 는 프로젝트마다 따로 있어서, 홈페이지 작업 폴더 같은 다른 곳에서는 못 읽는다.)
VAULT_CONFIG = Path.home() / ".claude" / "obsidian_vault.txt"


def obsidian_config_candidates() -> list[Path]:
    """옵시디언이 볼트 목록을 적어 두는 파일 위치 후보(윈도우/맥/리눅스)."""
    home = Path.home()
    appdata = os.environ.get("APPDATA", "")
    candidates = [
        Path(appdata) / "obsidian" / "obsidian.json" if appdata else None,
        home / "AppData" / "Roaming" / "obsidian" / "obsidian.json",
        home / "Library" / "Application Support" / "obsidian" / "obsidian.json",
        home / ".config" / "obsidian" / "obsidian.json",
    ]
    return [c for c in candidates if c is not None]


def detect_vaults() -> list[Path]:
    """옵시디언 설정에서 볼트 목록을 읽는다. 최근에 연 것이 앞으로 온다.

    옵시디언은 열어 본 볼트 목록을 obsidian.json 에 적어 둔다. 그래서 사용자가
    경로를 직접 찾아 입력하지 않아도 볼트를 알아낼 수 있다.
    설정 파일 모양이 다르거나 없으면 빈 목록을 돌려주고 조용히 넘어간다.
    """
    for config in obsidian_config_candidates():
        try:
            if not config.is_file():
                continue
            data = json.loads(config.read_text(encoding="utf-8"))
            vaults = data.get("vaults")
            if not isinstance(vaults, dict):
                continue
        except (OSError, ValueError):
            continue

        found = []
        for info in vaults.values():
            if not isinstance(info, dict) or not info.get("path"):
                continue
            path = Path(str(info["path"])).expanduser()
            if path.is_dir():
                # 지금 열려 있는 볼트를 맨 앞으로, 그다음은 최근에 연 순서로.
                found.append((0 if info.get("open") else 1, -int(info.get("ts") or 0), path))

        if found:
            return [path for _, _, path in sorted(found)]
    return []


def load_env_file(path: Path = Path(".env")) -> None:
    """.env 파일이 있으면 KEY=VALUE 를 환경변수로 읽어들인다."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def save_vault_config(path: str) -> Path:
    """볼트 경로를 홈 폴더에 기억해 둔다(어느 폴더에서 실행해도 찾을 수 있게)."""
    if path == "auto":
        detected = detect_vaults()
        if not detected:
            raise RuntimeError(
                "옵시디언 설정에서 볼트를 찾지 못했습니다. 경로를 직접 알려주세요."
            )
        path = str(detected[0])
    # 윈도우에서 "경로 복사"로 붙여넣으면 따옴표가 같이 들어온다.
    vault = Path(path.strip().strip("'\"")).expanduser()
    if not vault.is_dir():
        raise RuntimeError(f"볼트 폴더가 없습니다: {vault}")
    VAULT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    VAULT_CONFIG.write_text(str(vault.resolve()), encoding="utf-8")
    return VAULT_CONFIG


def resolve_vault(explicit: str | None = None) -> Path:
    """볼트 폴더를 찾는다.

    --vault > OBSIDIAN_VAULT > 기억해 둔 설정 파일 > 옵시디언 설정에서 자동 찾기.
    마지막 단계 덕분에 보통은 사용자가 경로를 직접 찾을 필요가 없다.
    """
    raw = (explicit or os.environ.get("OBSIDIAN_VAULT", "")).strip().strip("'\"")
    if not raw and VAULT_CONFIG.is_file():
        raw = VAULT_CONFIG.read_text(encoding="utf-8").strip().strip("'\"")
    if not raw:
        detected = detect_vaults()
        if detected:
            return detected[0]
        raise RuntimeError(
            "옵시디언 볼트를 찾지 못했습니다.\n"
            "  옵시디언을 한 번도 실행하지 않았거나, 설치 위치가 다를 수 있습니다.\n"
            "  --list-vaults 로 찾은 볼트를 확인하거나, 아래처럼 직접 알려주세요.\n"
            "     python obsidian_save.py --set-vault \"볼트폴더경로\"\n"
            "  (볼트 폴더 = 옵시디언에서 열어 둔 그 폴더. 안에 .obsidian 폴더가 있습니다.)"
        )

    vault = Path(raw).expanduser()
    if not vault.is_dir():
        raise RuntimeError(f"볼트 폴더가 없습니다: {vault}")
    return vault.resolve()


def _truncate_bytes(text: str, limit: int) -> str:
    """UTF-8 기준 limit 바이트를 넘지 않게 자른다(글자 중간에서 끊기지 않게)."""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="ignore").rstrip()


def sanitize_filename(name: str) -> str:
    """제목을 파일 이름으로 쓸 수 있게 다듬는다."""
    cleaned = re.sub(FORBIDDEN_FILENAME_CHARS, " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = _truncate_bytes(cleaned, MAX_FILENAME_BYTES)
    if not cleaned:
        raise ValueError(f"파일 이름으로 쓸 수 있는 글자가 없습니다: {name!r}")
    return cleaned


def normalize_tag(tag: str) -> str:
    """옵시디언 태그 규칙에 맞게 다듬는다(공백 불가, 앞의 # 제거)."""
    tag = tag.strip().lstrip("#").strip()
    tag = re.sub(r"\s+", "-", tag)
    return re.sub(r"[^\w/\-가-힣]", "", tag)


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def strip_existing_frontmatter(body: str) -> tuple[str, bool]:
    """본문이 이미 --- 속성 블록으로 시작하면 떼어낸다(속성 블록 중복 방지)."""
    if not body.startswith("---\n"):
        return body, False
    end = body.find("\n---", 4)
    if end == -1:
        return body, False
    return body[end + 4 :].lstrip("\n"), True


def build_frontmatter(
    title: str,
    tags: list[str],
    source: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    """옵시디언 속성(프로퍼티) 블록을 만든다."""
    lines = ["---", f"title: {_yaml_quote(title)}"]
    lines.append(f"created: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    if tags:
        lines.append("tags:")
        lines.extend(f"  - {tag}" for tag in tags)
    if source:
        lines.append(f"source: {_yaml_quote(source)}")
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {_yaml_quote(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def next_number(directory: Path, width: int = 2) -> str:
    """폴더 안의 `01-`, `02-` 형태 파일을 보고 다음 번호를 계산한다.

    기존 노트가 `01-웹개발-학습로드맵` 처럼 번호로 정리돼 있을 때, 그 순서를
    이어서 붙이기 위한 것이다. 폴더가 없으면 01 부터 시작한다.
    """
    highest = 0
    if directory.is_dir():
        for item in directory.glob("*.md"):
            match = re.match(r"(\d+)-", item.stem)
            if match:
                highest = max(highest, int(match.group(1)))
                width = max(width, len(match.group(1)))
    return str(highest + 1).zfill(width)


def _unique_path(path: Path) -> Path:
    """같은 이름이 있으면 뒤에 2, 3... 을 붙인다."""
    if not path.exists():
        return path
    for number in range(2, 1000):
        candidate = path.with_name(f"{path.stem} {number}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"이름이 겹치는 파일이 너무 많습니다: {path}")


def target_path(
    vault: Path,
    title: str,
    folder: str = "",
    filename: str | None = None,
    date_prefix: bool = False,
    auto_number: bool = False,
) -> Path:
    """볼트 안의 저장 위치를 계산한다(볼트 밖으로 나가지 못하게 막는다)."""
    if date_prefix and auto_number:
        raise ValueError("--date-prefix 와 --auto-number 는 같이 쓸 수 없습니다.")

    stem = sanitize_filename(filename or title)

    directory = vault
    for part in Path(folder.replace("\\", "/")).parts if folder else ():
        if part in ("..", "/", "."):
            raise ValueError(f"폴더 이름에 쓸 수 없는 값입니다: {folder!r}")
        directory = directory / sanitize_filename(part)

    if date_prefix:
        stem = f"{datetime.now().strftime('%Y-%m-%d')} {stem}"
    elif auto_number:
        stem = f"{next_number(directory)}-{stem.lstrip('-')}"

    path = directory / f"{stem}.md"
    if not path.resolve().parent.is_relative_to(vault):
        raise ValueError(f"볼트 바깥에는 저장할 수 없습니다: {path}")
    return path


def save_note(
    body: str,
    title: str,
    vault: Path | str | None = None,
    folder: str = "",
    tags: list[str] | None = None,
    source: str | None = None,
    filename: str | None = None,
    mode: str = "new",
    date_prefix: bool = False,
    auto_number: bool = False,
    frontmatter: bool = True,
    extra: dict[str, str] | None = None,
    dry_run: bool = False,
) -> Path:
    """볼트에 노트 하나를 저장하고 저장된 경로를 돌려준다.

    mode: new(겹치면 새 이름) / overwrite(덮어쓰기) / append(기존 파일 뒤에 붙이기)
    """
    if mode not in ("new", "overwrite", "append"):
        raise ValueError(f"mode 는 new, overwrite, append 중 하나여야 합니다: {mode}")

    vault_path = vault if isinstance(vault, Path) else resolve_vault(vault)
    path = target_path(vault_path, title, folder, filename, date_prefix, auto_number)

    body = body.strip()
    if not body:
        raise ValueError("저장할 본문이 비어 있습니다.")

    stripped, had_frontmatter = strip_existing_frontmatter(body)
    if had_frontmatter and frontmatter:
        print("본문 앞에 있던 속성(---) 블록은 새로 만든 것으로 바꿨습니다.", file=sys.stderr)
        body = stripped

    if mode == "append" and path.exists():
        content = path.read_text(encoding="utf-8").rstrip() + "\n\n---\n\n" + body + "\n"
    else:
        if mode == "new":
            path = _unique_path(path)
        head = ""
        if frontmatter:
            head = build_frontmatter(
                title, [normalize_tag(t) for t in (tags or []) if normalize_tag(t)],
                source, extra,
            )
        content = head + body + "\n"

    if dry_run:
        print(f"[미리보기] 저장할 위치: {path}", file=sys.stderr)
        print(content)
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="옵시디언 볼트에 마크다운 노트 저장")
    parser.add_argument("--title", help="노트 제목(파일 이름이 된다)")
    parser.add_argument(
        "--set-vault",
        metavar="경로",
        help="볼트 경로를 기억해 두고 끝낸다(한 번만 하면 어느 폴더에서든 저장 가능)",
    )
    parser.add_argument("--folder", default="", help="볼트 안의 하위 폴더 (예: '유튜브 요약')")
    parser.add_argument("--tags", default="", help="태그 (쉼표 구분, 예: 유튜브,요약)")
    parser.add_argument("--source", default="", help="출처 링크")
    parser.add_argument("--vault", default="", help="볼트 폴더 경로 (기본: OBSIDIAN_VAULT)")
    parser.add_argument("--file", type=Path, help="본문이 들어 있는 파일 (기본: 표준입력)")
    parser.add_argument("--filename", help="파일 이름을 제목과 다르게 쓰고 싶을 때")
    parser.add_argument(
        "--mode",
        default="new",
        choices=["new", "overwrite", "append"],
        help="이름이 겹칠 때: new=새 이름, overwrite=덮어쓰기, append=뒤에 붙이기",
    )
    parser.add_argument("--date-prefix", action="store_true", help="파일 이름 앞에 날짜 붙이기")
    parser.add_argument(
        "--auto-number",
        action="store_true",
        help="폴더의 기존 번호를 이어서 `17-` 처럼 앞에 붙이기",
    )
    parser.add_argument(
        "--list-vaults", action="store_true", help="옵시디언에 등록된 볼트를 찾아서 보여주기"
    )
    parser.add_argument("--no-frontmatter", action="store_true", help="속성(---) 블록 없이 저장")
    parser.add_argument("--dry-run", action="store_true", help="저장하지 않고 결과만 보여주기")
    args = parser.parse_args()

    load_env_file()

    if args.list_vaults:
        detected = detect_vaults()
        if not detected:
            print(
                "옵시디언 설정에서 볼트를 찾지 못했습니다.\n"
                "옵시디언을 한 번 실행한 뒤 다시 시도하거나, 경로를 직접 알려주세요.",
                file=sys.stderr,
            )
            return 1
        print("찾은 볼트 (맨 위가 지금 열려 있거나 가장 최근에 연 볼트):")
        for index, vault in enumerate(detected, 1):
            print(f"  {index}. {vault}")
        print("\n이 중 맨 위 볼트를 계속 쓰려면:")
        print("  python obsidian_save.py --set-vault auto")
        return 0

    if args.set_vault:
        try:
            config = save_vault_config(args.set_vault)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"볼트 경로를 기억했습니다: {config.read_text(encoding='utf-8')}")
        print(f"(설정 파일: {config})")
        return 0

    if not args.title:
        print("--title 이 필요합니다. (예: --title \"노트 제목\")", file=sys.stderr)
        return 1

    body = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()

    try:
        path = save_note(
            body=body,
            title=args.title,
            vault=args.vault or None,
            folder=args.folder,
            tags=[t for t in args.tags.split(",") if t.strip()],
            source=args.source or None,
            filename=args.filename,
            mode=args.mode,
            date_prefix=args.date_prefix,
            auto_number=args.auto_number,
            frontmatter=not args.no_frontmatter,
            dry_run=args.dry_run,
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not args.dry_run:
        print(f"저장 완료: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
