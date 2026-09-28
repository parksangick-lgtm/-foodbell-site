#!/usr/bin/env bash
# 클로드 코드가 답을 마칠 때마다(Stop 훅) 바뀐 파일을 커밋하고 GitHub 에 올린다.
# 세 컴퓨터가 같은 저장소를 쓰는데 "저장" 을 깜빡하면 다른 PC 에서 충돌이 나서 만들었다.
# 결과는 화면 한 줄(systemMessage)로만 알린다. 실패해도 클로드 작업은 막지 않는다.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

say() { printf '{"systemMessage": "%s"}\n' "$1"; exit 0; }

# 저장.bat 이 돌고 있으면 겹치지 않게 이번엔 건너뛴다.
# 단, 10분 넘은 잠금은 창이 비정상 종료돼 남은 것이라 무시한다 (안 그러면 자동 저장이 조용히 영영 멈춘다).
lock="${TEMP:-/tmp}/foodbell-save.lock"
[ -d "$lock" ] && [ -z "$(find "$lock" -maxdepth 0 -mmin +10 2>/dev/null)" ] && exit 0

# 병합·되돌리기가 진행 중이면 손대지 않는다.
g=$(git rev-parse --git-dir 2>/dev/null) || exit 0
if [ -e "$g/MERGE_HEAD" ] || [ -d "$g/rebase-merge" ] || [ -d "$g/rebase-apply" ]; then
  say "자동 저장 건너뜀: 충돌 정리 중입니다. 클로드에게 '충돌 해결해줘' 라고 하세요."
fi

n=$(git status --porcelain | wc -l | tr -d ' ')
if [ "$n" -gt 0 ]; then
  PY=python; command -v python >/dev/null 2>&1 || PY=py
  # 무거운 새 파일이 있으면 자동으로 올리지 않는다 (묻는 칸에는 '아니오' 가 들어간다).
  if ! "$PY" 저장전점검.py --big </dev/null >/dev/null 2>&1; then
    say "자동 저장 멈춤: 5MB 넘는 새 파일이 있습니다. '저장' 아이콘으로 직접 확인해 주세요."
  fi
  git add -A
  git commit -q -m "자동 저장: 파일 ${n}개 ($(date '+%Y-%m-%d %H:%M'))" || exit 0
fi

# 올릴 커밋이 없으면(바뀐 것도, 지난번 못 올린 것도 없으면) 조용히 끝낸다.
[ "$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)" -eq 0 ] && exit 0

# 다른 컴퓨터에서 올린 것을 먼저 받아 합친다. 부딪히면 합치기를 취소하고 알린다.
if ! git pull -q --no-edit >/dev/null 2>&1; then
  git merge --abort >/dev/null 2>&1
  say "자동 저장: 커밋은 했지만 다른 컴퓨터 작업과 부딪혀 못 올렸습니다. 클로드에게 '충돌 해결해줘' 라고 하세요."
fi

if git push -q >/dev/null 2>&1; then
  say "자동 저장 완료: GitHub 에 올렸습니다."
else
  say "자동 저장: 커밋은 했지만 업로드에 실패했습니다 (인터넷 확인). 다음 답이 끝날 때 다시 시도합니다."
fi
