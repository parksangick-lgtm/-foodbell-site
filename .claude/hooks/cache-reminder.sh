#!/usr/bin/env bash
# css/js 를 고쳤는데 index.html 의 캐시 번호(?v=)를 아직 안 올렸으면 클로드에게 알린다 (PostToolUse 훅).
# 자동 저장(auto-save.sh)은 이 점검을 안 하고 "클로드가 같은 답 안에서 올린다"에 맡겨 왔다.
# 반복해서 빠지는 단계는 기억에 맡기지 않는다 — 그래서 고칠 때마다 여기서 본다.
# 마지막 저장본(HEAD)과 비교한다. 번호를 이미 올렸으면 조용하다(여러 번 올려 번호가 튀지 않게).

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

changed=$(git -c core.quotepath=false diff --name-only HEAD -- css js 2>/dev/null)
[ -z "$changed" ] && exit 0
git diff HEAD -- index.html 2>/dev/null | grep -Eq '^\+.*(css/style\.css|js/main\.js)\?v=' && exit 0

files=$(echo $changed)
printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' \
  "[캐시 번호] ${files} 를 고쳤는데 index.html 의 ?v= 를 아직 안 올렸습니다. css·js 를 다 고친 뒤, 이 답을 끝내기 전에 python 캐시버전올리기.py 를 한 번만 실행하세요."
exit 0
