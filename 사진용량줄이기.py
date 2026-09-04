# 사진 용량 줄이기
#
# images 폴더의 사진을 웹에 맞는 크기로 줄이고 다시 저장한다.
# 실행:  python 사진용량줄이기.py
# 되돌리기:  git checkout -- images
#
# 처음 한 번만:  python -m pip install Pillow

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).parent / "images"

# 긴 변(px), JPEG 품질
HERO = (1600, 78)  # 첫 화면 배경 - 화면 전체를 덮으므로 크게 유지
ALBUM = (1100, 72)  # 앨범 - 작은 정사각 썸네일 + 클릭 시 확대
NORMAL = (1200, 74)  # 갤러리 / 메뉴 사진


def target_for(path: Path):
    if path.stem.startswith("hero-"):
        return HERO
    if path.parent.name == "album":
        return ALBUM
    return NORMAL


def shrink(path: Path) -> None:
    edge, quality = target_for(path)

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)  # 세로로 찍은 사진이 눕지 않게
        img = img.convert("RGB")

        if max(img.size) > edge:
            img.thumbnail((edge, edge), Image.LANCZOS)

        tmp = path.with_suffix(path.suffix + ".tmp")
        img.save(
            tmp,
            "JPEG",
            quality=quality,
            optimize=True,      # 허프만 테이블 최적화
            progressive=True,   # 느린 회선에서 흐릿한 상태로 먼저 보임
            subsampling=2,      # 4:2:0 - 사진에서는 눈에 띄지 않는다
        )

    # 줄인 쪽이 더 크면(이미 충분히 작은 사진) 원본을 그대로 둔다.
    if tmp.stat().st_size < path.stat().st_size:
        tmp.replace(path)
    else:
        tmp.unlink()


def main() -> None:
    files = sorted(p for p in ROOT.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg"})
    before = sum(p.stat().st_size for p in files)

    for path in files:
        shrink(path)

    after = sum(p.stat().st_size for p in files)
    mb = 1024 * 1024
    print(f"사진 {len(files)}장 처리 완료")
    print(
        f"이전: {before / mb:.2f} MB  ->  이후: {after / mb:.2f} MB "
        f"({(1 - after / before) * 100:.0f}% 절감)"
    )


if __name__ == "__main__":
    main()
