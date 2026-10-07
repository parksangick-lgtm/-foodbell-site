#!/usr/bin/env bash
# index.html 을 고친 뒤 지켜야 할 것이 남아 있는지 본다 (PostToolUse 훅).
#   1) 마지막 저장본(HEAD)에 있던 검색 확인 태그(구글·네이버)와 사업자 정보가 그대로 있는가
#      — 확인 태그를 지우면 검색 등록이 풀린다
#   2) 가격("30만원", "300,000원")이 들어가지 않았는가 — 가격은 사이트에 올리지 않는다
# 걸리면 클로드에게 되돌려 보낸다. index.html 이 저장본과 같으면 아무것도 안 한다.
# 기준이 HEAD 라서, 사업자 정보를 정말 바꾼 경우에는 저장(커밋)되고 나면 경고가 멈춘다.
# 한계: 고친 "뒤"에 알린다. 그 답 안에서 안 고치면 자동 저장이 그대로 올린다.

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
f=index.html
git diff --quiet HEAD -- "$f" 2>/dev/null && exit 0
old=$(git show HEAD:"$f" 2>/dev/null) || exit 0

problems=()
if [ ! -f "$f" ]; then
  problems+=("index.html 이 없어졌습니다")
else
  # 1) 확인 태그 — 이름과 값만 뽑아 비교한다 (줄바꿈·들여쓰기가 달라도 같게 본다)
  while IFS= read -r tag; do
    grep -qF -- "$tag" "$f" || problems+=("검색 확인 태그가 사라짐 또는 바뀜: ${tag%% content=*}")
  done < <(printf '%s\n' "$old" | grep -oE 'name="(google|naver)-site-verification" content="[^"]*"')

  for s in "208-09-69358" "010-5353-3477" "올림픽로34길 31" "박상익"; do
    printf '%s\n' "$old" | grep -qF -- "$s" && ! grep -qF -- "$s" "$f" && problems+=("사업자 정보가 사라짐: $s")
  done

  # 2) 가격 — 숫자 바로 뒤의 (만·천) 원
  price=$(grep -noE '[0-9][0-9,]*[[:space:]]*(만|천)?[[:space:]]*원' "$f" | head -3 | tr '\n' ' ')
  [ -n "$price" ] && problems+=("가격으로 보이는 글자 (줄:내용) ${price}— 가격은 사이트에 올리지 않고 상담 후 안내")
fi

[ ${#problems[@]} -eq 0 ] && exit 0
msg="[index.html 지킴이] $(printf '%s / ' "${problems[@]}")실수면 이 답 안에서 되돌리세요. 일부러 바꾼 것이면 사용자에게 확인받으세요 — 저장되면 경고가 멈춥니다."
msg=${msg//\\/\/}; msg=${msg//\"/\'}
printf '{"decision":"block","reason":"%s"}\n' "$msg"
exit 0
