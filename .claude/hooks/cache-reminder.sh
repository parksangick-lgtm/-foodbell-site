#!/usr/bin/env bash
# css/js 를 고쳤는데 그 파일을 ?v= 로 부르는 화면의 캐시 번호를 아직 안 올렸으면 클로드에게 알린다 (PostToolUse 훅).
# 자동 저장(auto-save.sh)은 이 점검을 안 하고 "클로드가 같은 답 안에서 올린다"에 맡겨 왔다.
# 반복해서 빠지는 단계는 기억에 맡기지 않는다 — 그래서 고칠 때마다 여기서 본다.
# 판단은 cache-reminder.py — 어느 화면이 부르는지 경로를 따져야 해서 파이썬으로 옮겼다 (2026-10-28, 기록장 #24).

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
git diff --quiet HEAD -- css js 2>/dev/null && exit 0   # css/js 가 안 바뀌었으면 파이썬을 띄우지 않는다

p=python; command -v python >/dev/null 2>&1 || p=py
exec "$p" -X utf8 "$(dirname "$0")/cache-reminder.py"
