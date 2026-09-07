#!/usr/bin/env python3
# sije-quote.html(완전한 HTML 문서) → sije-quote.artifact.html(아티팩트용, 래퍼 제거)
#
# 견적서를 claude.ai 아티팩트로도 발행할 때 쓴다.
#   1) 이 스크립트 실행 → 같은 폴더에 sije-quote.artifact.html 생성
#   2) 그 파일을 아티팩트 URL 로 재발행
#      (favicon 📜, capabilities {"downloads": true}, contract latest,
#       url: https://claude.ai/code/artifact/80925ce5-4415-4725-ac4d-6dbd69bb3dd6)
#
# 왜 필요: 아티팩트는 스켈레톤이 <head>를 감싸므로 doctype/html/head/body 를 빼야 하고,
#          아티팩트 CSP 가 jsdelivr 스타일시트를 막아 Pretendard 링크도 뺀다
#          (본문은 Noto Sans KR 폴백으로 렌더 — 구글폰트라 허용됨).

import re, os

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "sije-quote.html"), encoding="utf-8").read()

src = re.sub(r"^<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", src, flags=re.I)
src = src.replace('<meta charset="utf-8">\n', "")
src = re.sub(r'<meta name="viewport"[^>]*>\n', "", src)
src = src.replace("</head>\n<body>\n", "")
src = re.sub(r"\s*</body>\s*</html>\s*$", "\n", src, flags=re.I)
src = re.sub(
    r'<link rel="stylesheet" as="style" crossorigin '
    r'href="https://cdn\.jsdelivr\.net/gh/orioncactus/pretendard[^"]*"\s*/?>\n?',
    "", src,
)

out = os.path.join(HERE, "sije-quote.artifact.html")
open(out, "w", encoding="utf-8").write(src)
print(f"built {out} — {len(src)} bytes; jsdelivr link present: {'jsdelivr' in src}")
