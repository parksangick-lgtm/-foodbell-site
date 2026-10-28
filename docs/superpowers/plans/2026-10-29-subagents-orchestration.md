# 도우미(서브에이전트) 7개와 중간관리자 — 실행 계획서

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> 이 저장소에서는 `superpowers-extras` 스킬도 함께 적용한다(자동 저장 · 직전에 묻기).

**Goal:** 사장님이 "관리자에게 맡겨줘: ○○" 라고 하면 관리자 도우미가 일꾼 도우미 여섯에게 일을 나눠 맡기고, 결과를 여섯 칸 보고서로 돌려준다.
이를 위해 `.claude/agents/` 에 도우미 파일 6개를 새로 만들고 1개를 고치며, 기다리기 설정을 넣는다.

**Architecture:** 도우미 하나는 마크다운 파일 하나다. 머리말에 `name` · `description` · `tools` · `model` 을 두고, 본문에 지침을 쓴다. 부르는 순서는 메인 → 관리자 → 일꾼(2단)이다.
일꾼에게는 `Agent` 가 없고, 확인 담당에게는 `Edit` · `Write` 가 없다. 프로그램 코드는 없다. 대신 저장소 밖 임시 폴더에 가짜 파일을 두고, 도우미를 실제로 불러 시험한다.

**Tech Stack:** 클로드 코드 서브에이전트(`.claude/agents/*.md`) · `.claude/settings.json` · 시험 도구 — `python -X utf8`, `node --test`, pytest, Playwright(`휴대폰캡처.py`), curl, 화면 없는 클로드(`claude -p`)

**Spec:** `docs/superpowers/specs/2026-10-29-subagents-orchestration-design.md` — 실행하는 쪽은 설계서와 이 계획서를 같이 읽는다. 도우미 지침의 내용은 설계서 "지침 — 모든 도우미 공통" · "지침 — 도우미별 핵심 규칙" 이 원본이다. 이 계획서는 거기에 없는 결정(설명 글, 시험 순서, 시험 기준값)만 적는다.

## Global Constraints

- 파일 이름(정확히): `.claude/agents/foodbell-manager.md` · `foodbell-fixer.md` · `foodbell-test-runner.md` · `foodbell-mobile-checker.md` · `foodbell-rule-reviewer.md` · `foodbell-deploy-checker.md` · 있던 `content-reviewer.md`. 머리말 `name:` 은 파일 이름에서 `.md` 를 뺀 것이다.
- `model:` 줄: manager · fixer · rule-reviewer 는 `inherit`, test-runner · mobile-checker · deploy-checker 는 `sonnet`. content-reviewer 는 지금처럼 모델 줄을 두지 않는다.
- `tools:` 줄(글자 그대로):
  - manager: `Agent, Read, Grep, Glob, Bash`
  - fixer: `Read, Edit, Write, Grep, Glob, Bash`
  - test-runner · mobile-checker · rule-reviewer · deploy-checker: `Read, Grep, Glob, Bash`
- 설명(`description:`) 줄은 각 과제에 적힌 글을 그대로 쓴다. 메인은 이 글을 보고 누구를 부를지 고른다. 일꾼 다섯의 설명은 모두 "관리자가 부를 때, 또는 사용자가 이름을 댈 때만" 으로 끝난다.
- 새 도우미 여섯의 본문에는 설계서 "지침 — 모든 도우미 공통" 여섯 줄을 모두 넣는다(한국어 보고 · 한국어 명령 설명 · `%TEMP%` · 건수만 · `python -X utf8` · 스킬은 맡은 절만 · "확인 못 함"). 그 위에 설계서의 자기 몫 규칙을 빠짐없이 넣는다.
- 본문의 짜임과 말투는 `content-reviewer.md` 를 따른다. "너는 … 담당이다" 로 시작해 번호 붙인 절을 두고, 끝에 보고 형식을 둔다. Bash 를 읽기에만 쓰는 도우미는 그 사실을 첫 문단에 적는다.
- 스킬 `~/.claude/skills/foodbell-site-dev/SKILL.md` 는 줄 번호가 아니라 **절 제목 글**로 가리킨다. 줄 번호는 스킬을 고치면 밀린다.
- 시험용 가짜 파일 · 사본 · 점검 프로그램은 모두 `C:\Users\PARKS\AppData\Local\Temp\foodbell-agents-test\` 에 둔다. 아래에서는 이 폴더를 `$T` 라고 부른다(bash 로는 `/c/Users/PARKS/AppData/Local/Temp/foodbell-agents-test`). 저장소 안에는 두지 않는다.
- 이 저장소는 **답이 끝날 때 자동 저장**(commit · push)된다. 그래서 직접 커밋하지 않고, 과제마다 바꾼 파일 목록만 적는다. 도우미 파일은 다 쓴 다음에 부른다. 차례가 끝나면 쓰던 파일이 그대로 올라가기 때문이다. 시작 커밋은 `67514cf` 이다.
- 이 대화에서는 기다리기 설정이 아직 먹지 않는다. 그래서 과제 2~7 에서 부르는 도우미는 뒤에서 돈다. 부른 뒤에는 알림을 기다리고, 결과를 미리 짐작해 적지 않는다.
- Bash 명령 한 번은 최대 10분(`timeout: 600000`)이다.
- 하지 않는 것:
  - `auto-save.sh` 고치기
  - 관리자 전용 대화창(`claude --agent`)
  - `CLAUDE.md` · `진행중.md` 를 도우미가 고치기
  - `휴대폰캡처.py` 를 고치기(시험에는 임시 폴더의 사본을 쓴다)

## Review Focus

1. **일꾼이 사진이나 임시 파일을 작업 폴더 안에 남기면**, 자동 저장이 그것을 foodbell.kr 에 공개한다. 기대하는 것: 일꾼을 부른 뒤마다 `git status --short` 가 부르기 전과 같다(새로 만든 도우미 파일은 빼고). 이것은 과제 2~8 의 `after_call.sh` 단계가 본다.
2. **시험 담당이 전체 시험(15분쯤)을 명령 한 번으로 돌리면**, 10분에서 끊긴다. 끊긴 것을 '실패'나 '통과'로 적으면 안 된다. 기대하는 것: 파일별로 나눠 하나씩 `timeout: 600000` 으로 돌리고, 끊긴 파일은 "시간 초과 — 확인 못 함" 으로 적는다. 과제 2 의 Step 7 이 본다.
3. **휴대폰 확인 때 미리보기 서버가 꺼져 있으면**, 캡처 프로그램이 종료 코드 1("서버가 꺼져 있습니다")을 낸다. 이것을 '넘침'이나 '깨짐'으로 보고하면 안 된다. 기대하는 것: 서버를 켜고 다시 찍거나, "서버 꺼짐 — 확인 못 함" 으로 적는다. 과제 3 의 Step 6 이 본다.
4. **사장님이 그냥 "배포 확인해줘" · "시험 돌려줘" 라고만 하면**, 메인이 설명 글만 보고 일꾼이나 관리자를 불러 버릴 수 있다. 기대하는 것: `foodbell-*` 도우미는 하나도 불리지 않고, 지금처럼 메인이 직접 한다. 과제 8 의 Step 4 가 본다.
5. **관리자가 같은 파일을 고치기 담당 둘에게 동시에 맡기면**, 한쪽이 다른 쪽을 덮어쓴다. 기대하는 것: 같은 파일의 일은 한 담당에게 묶거나 차례로 맡긴다. 과제 9 의 3-마가 본다.

---

### Task 1: 시작 기록 · 점검 프로그램 둘 · 기다리기 설정

**Files:**
- Create: `$T/check_agents.py` · `$T/after_call.sh` (둘 다 저장소 밖)
- Modify: `.claude/settings.json` (맨 위에 `env` 넣기)

**Interfaces:**
- Produces: `python -X utf8 "$T/check_agents.py" [이름 ...]`
  - 이름을 안 주면 도우미 7개와 `settings` 를 모두 본다. 이름은 `foodbell-test-runner` · `content-reviewer` · `settings` 같은 모양으로 준다.
  - 항목마다 `정상 · 이름` 또는 `문제 · 이름 · 무엇` 을 한 줄로 찍고, 끝 줄에 `문제 N` 을 찍는다. N 이 0 보다 크면 종료 코드 1.
- Produces: `bash "$T/after_call.sh"` — 세 줄을 찍는다.
  - `작업 폴더: 같음` 또는 `작업 폴더: 다름 — <새로 생긴 줄>`. `$T/start-status.txt` 와 비교하며, `.claude/agents/` 줄은 뺀다.
  - `막힘: N` — 가장 최근 도우미 기록(`ls -t ~/.claude/projects/c--galleypark/*/subagents/agent-*.jsonl | head -1`)에 한국어 확인 훅의 막는 글 `사장님 화면에 뜨는 글에 영어가 있어 막았습니다` 가 몇 번 나오는지.
  - `영어 명령 설명: N` — 같은 기록에서 Bash 입력의 `description` 가운데 한글이 한 글자도 없는 것이 몇 개인지.

- [ ] **Step 1: 시작 상태 적기**
  `mkdir -p "$T"`, 그다음 `git -C /c/galleypark log -1 --format=%h` 를 돌리면 `67514cf` 가 나와야 한다. 이어서 `git -C /c/galleypark status --short > "$T/start-status.txt"` 로 지금 상태를 적어 둔다.

- [ ] **Step 2: `check_agents.py` 쓰기**
  설계서 "시험 1" 을 그대로 검사한다.
  - 머리말은 첫 `---` 부터 다음 `---` 까지의 `키: 값` 줄로 읽는다. 이 PC 에는 yaml 모듈이 없다.
  - 검사 항목:
    - `name` 이 파일 이름과 같다.
    - `description` 이 비어 있지 않다.
    - `tools` · `model` 이 Global Constraints 와 글자 그대로 같다.
    - 일꾼 여섯의 `tools` 에 `Agent` 가 없다.
    - 확인 담당 다섯(test-runner · mobile-checker · rule-reviewer · deploy-checker · content-reviewer)의 `tools` 에 `Edit` · `Write` 가 없다.
    - 새 도우미 여섯의 본문에 `%TEMP%` · `python -X utf8` · `확인 못 함` · `한국어` 가 모두 들어 있다.
    - content-reviewer 의 설명에 `foodbell-manager` 가 들어 있다.
    - `settings`: JSON 으로 읽히고, `env.CLAUDE_CODE_FORK_SUBAGENT == "0"` 이며, `hooks` 의 `SessionStart` · `Stop` · `PostToolUse` 셋이 그대로 있다.

- [ ] **Step 3: 돌려서 실패를 먼저 본다**
  `python -X utf8 "$T/check_agents.py"` 를 돌린다. 기대하는 결과는 다음과 같고, 끝 줄이 `문제 8`, 종료 코드가 1 이어야 한다.
  - 파일 없음 6
  - content-reviewer 설명에 `foodbell-manager` 없음 1
  - settings 에 env 없음 1

- [ ] **Step 4: `after_call.sh` 쓰기**
  지금 바로 돌려 본다. 기대하는 결과: `작업 폴더: 같음`. 도우미 기록이 없으면 `막힘: 0`, `영어 명령 설명: 0` 이 나온다.

- [ ] **Step 5: `.claude/settings.json` 맨 앞 `{` 다음 줄에 넣기**
  넣을 줄은 `"env": { "CLAUDE_CODE_FORK_SUBAGENT": "0" },` 이다. 나머지는 건드리지 않는다.

- [ ] **Step 6: 설정 확인**
  `python -X utf8 "$T/check_agents.py" settings` 를 돌린다. 기대하는 결과: `정상 · settings`, `문제 0`.

- [ ] **Step 7: 바꾼 파일 적기**
  바꾼 파일은 `.claude/settings.json` 이다. 이 설정은 **새 대화부터** 먹는다.

---

### Task 2: 시험 담당 (`foodbell-test-runner.md`)

**Files:**
- Create: `.claude/agents/foodbell-test-runner.md`
- Test: `$T/fake-test/fake.test.mjs`

**Interfaces:**
- Consumes: Task 1 의 `check_agents.py` · `after_call.sh`

**description (그대로):**
`푸드벨 시험 담당 — 고친 크기에 맞춰 파이썬 · JS 시험을 돌리고, 통과 · 실패 · 건너뜀 숫자와 실패마다 원인 · 판정(진짜 / 일시)을 보고한다. 관리자(foodbell-manager)가 부를 때, 또는 사용자가 "시험 담당에게 맡겨줘" 라고 이름을 댈 때만 쓴다. 읽기만 하고 고치지 않는다.`

**본문 지침:** 설계서의 "시험 담당" 다섯 줄을 넣고, 아래 넷을 더한다.
- 범위 표는 스킬의 "서류 시험(pytest)을 돌리고 읽기" 절에서 그때그때 읽는다. 부른 쪽이 시험 파일 경로를 주면 그것만 돌린다.
- 범위가 '전체'면 `tools/sije_web/tests/test_*.py` 를 **파일 하나씩** 따로 돌린다. 명령마다 `timeout: 600000` 을 준다. 명령 한 번은 10분에서 끊기는데, 전체 시험은 15분쯤 걸린다. 끊긴 파일은 "시간 초과 — 확인 못 함" 으로 적는다.
- 건너뜀의 이유가 `시험 열쇠가 없습니다` 이면 "이 PC 에서는 서류 시험 못 돌림" 으로 적는다. 이것을 통과로 세지 않는다.
- JS 숫자는 `ℹ tests` · `ℹ pass` · `ℹ fail` · `ℹ skipped` 줄에서 읽는다.

- [ ] **Step 1: 기준값 만들기(메인이 직접)**
  - 가짜 시험 `$T/fake-test/fake.test.mjs` 를 만든다. 시험은 둘이다: `test('일부러 실패', () => assert.strictEqual(1, 2))` 와 `test('통과', () => assert.ok(true))`.
  - `node --test "$T/fake-test/fake.test.mjs"` 를 돌린다. 기대하는 결과: `ℹ pass 1`, `ℹ fail 1`.
  - `node --test tools/sije_web/js-tests/*.test.mjs` 를 돌려 `ℹ tests` 와 `ℹ pass` 를 적어 둔다. 10-29 에 잰 값은 68 / 68 / 실패 0 이다.
- [ ] **Step 2: 파일 쓰기**
- [ ] **Step 3: 모양 점검**
  `python -X utf8 "$T/check_agents.py" foodbell-test-runner` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 4: 문제 쪽 — 잡아야 한다**
  `foodbell-test-runner` 에게 "이 파일만 돌려라 — `$T/fake-test/fake.test.mjs`" 라고 맡긴다. 기대하는 보고:
  - 통과 1 · 실패 1
  - 실패한 것이 `일부러 실패` 이고, 원인은 1 과 2 가 다르다는 것
- [ ] **Step 5: 멀쩡한 쪽 — 조용해야 한다**
  "문서만 고친 경우의 범위로 확인하라" 고 맡긴다. 기대하는 보고:
  - JS 숫자가 Step 1 과 같다.
  - 서류 시험(pytest)은 범위 밖이라 안 돌렸다고 적는다.
- [ ] **Step 6: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`. `막힘` 과 `영어 명령 설명` 숫자는 그대로 적어 둔다(설계서 가정 2 의 첫 자료).
- [ ] **Step 7: Review Focus 2**
  "공용 부품 `js/docs/paging.js` 를 고쳤다면 무엇을 돌릴지 **명령만** 적어라. 돌리지는 마라" 고 맡긴다. 기대하는 보고:
  - 파일별로 나눈 명령이 있다.
  - 10분 한계를 말한다.
  - pytest 를 한 줄로 통째로 돌리는 명령만 내면 실패다. 그때는 지침을 고치고 이 단계만 다시 한다.
- [ ] **Step 8: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-test-runner.md` 이다.

---

### Task 3: 휴대폰 화면 확인 (`foodbell-mobile-checker.md`)

**Files:**
- Create: `.claude/agents/foodbell-mobile-checker.md`
- Test: `$T/fake-site/overflow.html` · `$T/fake-tool/phonecap_8124.py`(사본)

**description (그대로):**
`푸드벨 휴대폰 화면 확인 담당 — 휴대폰캡처.py 로 390px 폭을 찍어 폭 · 넘침을 숫자로, 누르는 자리 44px · 글자 14px 을 css 값과 사진으로 확인한다. 관리자(foodbell-manager)가 부를 때, 또는 사용자가 "휴대폰 화면 확인 담당에게 맡겨줘" 라고 이름을 댈 때만 쓴다. 읽기만 하고 고치지 않는다.`

**본문 지침:** 설계서의 "휴대폰 화면 확인" 네 줄을 넣고, 아래 넷을 더한다.
- 종료 코드를 이렇게 읽는다.
  - `0` 은 정상이다.
  - `1` 은 넘침 · 측정 실패 · 서버 꺼짐 가운데 하나다. 어느 것인지 출력 글로 가른다.
  - `2` 는 도구 자체 시험이 실패한 것이다. 이때 결과를 믿지 않는다.
- 찍기 전에 `curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:8123/` 로 서버를 본다.
  - 꺼져 있으면 `(cd /c/galleypark && nohup python -m http.server 8123 >/dev/null 2>&1 &)` 로 켜고 다시 본다.
  - 그래도 안 켜지면 "서버 꺼짐 — 확인 못 함" 으로 적는다.
  - 부른 쪽이 "서버를 켜지 말라" 고 하면 켜지 않는다.
- 44px · 14px 은 캡처 프로그램이 재지 않는다. 그래서 고친 곳의 css 값(`min-height` · `font-size` · 쓰인 토큰)을 읽어 확인한다. 사진으로만 본 것은 "눈으로 봄 — 숫자 아님" 이라고 적는다.
- 사진은 결과에 찍힌 `%TEMP%\foodbell-phone\…` 폴더에서 Read 로 연다.

- [ ] **Step 1: 가짜 넘치는 쪽과 사본 도구 만들기(메인이 직접)**
  - `$T/fake-site/overflow.html` 을 만든다. 들어갈 것은 `<meta name="viewport" content="width=device-width,initial-scale=1">` 과 본문 `<div style="width:600px">넘침 시험</div>` 이다.
  - `휴대폰캡처.py` 를 `$T/fake-tool/phonecap_8124.py` 로 복사하고, `BASE` 한 줄만 `http://127.0.0.1:8124/` 로 바꾼다.
- [ ] **Step 2: 기준값 만들기(메인이 직접)**
  - `python -m http.server 8124 --directory "$T/fake-site"` 를 뒤에서(run_in_background) 켠다.
  - `python -X utf8 "$T/fake-tool/phonecap_8124.py" overflow.html` 을 돌린다. 기대하는 결과: 폭 390, `★넘침 1곳`, 종료 코드 1.
  - 이어서 `python -X utf8 휴대폰캡처.py index.html` 을 돌린다. 기대하는 결과: 폭 390, `넘침 없음`, 종료 코드 0. 8123 이 꺼져 있으면 메인이 저장소 폴더에서 켠다.
- [ ] **Step 3: 파일 쓰기**
- [ ] **Step 4: 모양 점검**
  `check_agents.py foodbell-mobile-checker` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 5: 문제 쪽 — 잡아야 한다**
  "이번은 시험이다. 사본 `$T/fake-tool/phonecap_8124.py overflow.html` 로 찍고 보고하라. 서버는 켜지 마라" 고 맡긴다. 기대하는 보고: 폭 390, 넘침 1.
- [ ] **Step 6: Review Focus 3**
  메인이 8124 서버를 끈다(TaskStop — 메인이 켠 것만 끈다). 그다음 Step 5 와 같은 지시를 다시 맡긴다. 기대하는 보고:
  - "서버 꺼짐 — 확인 못 함" 이다.
  - '넘침' 이나 '깨짐' 으로 판정하면 실패다.
- [ ] **Step 7: 멀쩡한 쪽 — 조용해야 한다**
  "`index.html` 을 확인하라" 고 맡긴다. 기대하는 보고: Step 2 의 메인 결과와 같은 폭 390 · 넘침 0.
- [ ] **Step 8: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`. 저장소 안에 `.png` 가 새로 생기지 않았어야 한다.
- [ ] **Step 9: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-mobile-checker.md` 이다.

---

### Task 4: 코드 규칙 검토 (`foodbell-rule-reviewer.md`)

**Files:**
- Create: `.claude/agents/foodbell-rule-reviewer.md`
- Test: `$T/fake-diff/bad.diff` · `$T/fake-diff/good.diff`

**description (그대로):**
`푸드벨 코드 규칙 검토 담당 — 바뀐 곳(git diff, 새 파일은 전체)을 CLAUDE.md 의 화면 · 내용 · 비밀 규칙, 캐시 번호(?v=), index.html 의 검색 확인 태그 · 사업자 정보, 옛 브라우저 저장 키와 대조해 어긴 곳을 파일:줄로 보고한다. 관리자(foodbell-manager)가 부를 때, 또는 사용자가 "코드 규칙 검토 담당에게 맡겨줘" 라고 이름을 댈 때만 쓴다. 읽기만 하고 고치지 않는다.`

**본문 지침:** 설계서의 "코드 규칙 검토" 세 줄을 넣고, 아래 셋을 더한다.
- 기준은 기억으로 판단하지 않고, 매번 `CLAUDE.md` 에서 해당 절을 읽어 확인한다.
- 부른 쪽이 diff 파일을 주면 그것을 본다.
- 캐시 번호는 `python -X utf8 캐시버전올리기.py --check` 로 본다. 이 명령은 보기만 하고 번호를 올리지 않는다.
- 문제가 없으면 "없음" 과 함께 본 파일과 줄 범위를 적는다. 이 규칙은 `content-reviewer.md` 와 같다.

- [ ] **Step 1: 가짜 변경 만들기(메인이 직접)**
  - `bad.diff` 는 통합 diff 모양으로 만들고, 들어갈 줄은 셋이다.
    - `css/style.css` 에 `+  color: #ff3366;` (즉석 색)
    - `index.html` 에 `+<span class="icon">📞</span>` (이모지 아이콘)
    - `index.html` 에 `+<p>시제상 30만원부터</p>` (가격)
  - `good.diff` 에는 둘을 넣는다.
    - `css/style.css` 에 `+  color: var(--color-primary);`
    - `index.html` 에서 지금 손님 눈에 보이는 문장 하나를 그대로 가져와 `+<p>…</p>`
- [ ] **Step 2: 파일 쓰기**
- [ ] **Step 3: 모양 점검**
  `check_agents.py foodbell-rule-reviewer` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 4: 문제 쪽 — 잡아야 한다**
  "이 diff 를 검토하라 — `$T/fake-diff/bad.diff`" 라고 맡긴다. 기대하는 보고: 셋(즉석 색 · 이모지 아이콘 · 가격)을 모두 파일:줄로 잡는다. 하나라도 빠지면 실패다.
- [ ] **Step 5: 멀쩡한 쪽 — 조용해야 한다**
  `good.diff` 를 맡긴다. 기대하는 보고: "없음" 과 본 범위.
- [ ] **Step 6: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`.
- [ ] **Step 7: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-rule-reviewer.md` 이다.

---

### Task 5: 고치기 담당 (`foodbell-fixer.md`)

**Files:**
- Create: `.claude/agents/foodbell-fixer.md`
- Test: `$T/fixer-copy/index.html`(사본)

**description (그대로):**
`푸드벨 고치기 담당 — 관리자가 맡긴 파일 · 맡긴 곳만 고치고, css/js 를 고쳤으면 그 파일을 부르는 화면의 캐시 번호(?v=)도 올린 뒤, 바꾼 곳 · 돌린 시험 · 남은 걱정을 보고한다. 관리자(foodbell-manager)가 부를 때, 또는 사용자가 "고치기 담당에게 맡겨줘" 라고 이름을 댈 때만 쓴다.`

**본문 지침:** 설계서의 "고치기 담당" 다섯 줄을 넣고, 아래 셋을 더한다.
- 설계서 "관리자가 하지 않고 '여쭐 것'으로 넘기는 일" 목록은 고치기 담당도 하지 않는다. 그런 일이 필요하면 보고에 적는다.
- 맡은 곳 밖에서 문제를 보면 고치지 않고 보고에 적는다.
- 지시문에 끝난 기준이 없으면 고치지 않고 "끝난 기준이 없음" 으로 돌려준다.

- [ ] **Step 1: 사본 만들기(메인이 직접)**
  `mkdir -p "$T/fixer-copy" && cp index.html "$T/fixer-copy/index.html"`
- [ ] **Step 2: 파일 쓰기**
- [ ] **Step 3: 모양 점검**
  `check_agents.py foodbell-fixer` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 4: 맡기기**
  "`$T/fixer-copy/index.html` 의 `<title>` 안 글만 `시험용 제목` 으로 바꿔라. 다른 곳은 건드리지 마라. 끝난 기준: 사본과 원본의 차이가 그 한 줄뿐" 이라고 맡긴다.
- [ ] **Step 5: 메인이 확인**
  - `diff index.html "$T/fixer-copy/index.html"` 를 돌린다. 기대하는 결과: 바뀐 곳 한 곳, `<` 1줄 · `>` 1줄.
  - `git diff --stat -- index.html` 를 돌린다. 기대하는 결과: 비어 있음(원본은 그대로).
- [ ] **Step 6: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`.
- [ ] **Step 7: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-fixer.md` 이다.

---

### Task 6: 배포 확인 (`foodbell-deploy-checker.md`)

**Files:**
- Create: `.claude/agents/foodbell-deploy-checker.md`

**description (그대로):**
`푸드벨 배포 확인 담당 — 자동 저장 뒤에 foodbell.kr 서버에 새 판이 올라갔는지(200 · 308 · 캐시 번호 · 고친 문구)를 확인해 "서버에 올라갔다 / 아직" 으로 보고한다. 관리자(foodbell-manager)가 부를 때, 또는 사용자가 "배포 확인 담당에게 맡겨줘" 라고 이름을 댈 때만 쓴다 — 그냥 "배포 확인해줘" 에는 쓰지 않는다(메인이 스킬로 직접 한다). 읽기만 하고 고치지 않는다.`

**본문 지침:** 설계서의 "배포 확인" 세 줄을 넣고, 아래 둘을 더한다.
- 명령은 스킬의 `"배포 확인해줘" — 새 버전이 서버에 올라갔는지` 절에서 읽는다. curl 의 `-w` 안에 한글을 넣지 않는다. 이 주의도 같은 절에 있다.
- `git status -sb` 에 저장 안 된 변경이나 `ahead` 가 있으면 그 파일이 사이트 파일인지 가린다. `.claude/` · `docs/` · `*.md` · `*.py` 는 `.vercelignore` 로 손님 주소에 안 올라간다.

- [ ] **Step 1: 기준값(메인이 직접)**
  스킬 그 절의 다섯 줄 명령을 돌려 결과를 적는다. 10-29 에 기대하는 결과:
  - `200`
  - www · 한글 주소는 `308 -> https://foodbell.kr/`
  - 캐시 번호는 내 컴퓨터와 서버가 같다
- [ ] **Step 2: 파일 쓰기**
- [ ] **Step 3: 모양 점검**
  `check_agents.py foodbell-deploy-checker` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 4: 맡기기**
  "지금 서버 상태를 확인하라. 고친 사이트 파일은 없다" 고 맡긴다. 기대하는 보고:
  - 숫자 다섯이 Step 1 과 같다.
  - 결론을 "서버에 올라갔다" 는 말로 쓴다("손님 화면" 이라는 말은 없어야 한다).
  - 저장 안 된 `.claude/` 변경은 사이트 파일이 아니라고 가린다.
- [ ] **Step 5: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`.
- [ ] **Step 6: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-deploy-checker.md` 이다.

---

### Task 7: 문구 검토의 설명 한 줄 (`content-reviewer.md`)

**Files:**
- Modify: `.claude/agents/content-reviewer.md` (머리말 `description:` 줄만)
- Test: `$T/fake-copy/bad.txt` · `$T/fake-copy/good.txt`

- [ ] **Step 1: 가짜 문구 만들기(메인이 직접)**
  - `bad.txt`: `2005년부터 전국 500곳 넘는 문중 시제를 맡아 왔습니다.` 사이트에 없는 사실이다.
  - `good.txt`: `index.html` 에서 지금 손님 눈에 보이는 문장 하나를 그대로 넣는다.
- [ ] **Step 2: 설명 줄 고치기**
  설명 줄에서 이 부분만 바꾼다. 본문은 그대로 둔다.
  - 지금: `사용자가 "내용 검토해줘", "문구 검토해줘" 라고 할 때만 쓴다.`
  - 바꾼 뒤: `사용자가 "내용 검토해줘", "문구 검토해줘" 라고 할 때, 또는 관리자(foodbell-manager)가 부를 때만 쓴다.`
- [ ] **Step 3: 모양 점검**
  `check_agents.py content-reviewer` 를 돌린다. 기대하는 결과: `문제 0`.
- [ ] **Step 4: 문제 쪽 — 잡아야 한다**
  "이 문구를 검토하라 — `$T/fake-copy/bad.txt`" 라고 맡긴다. 기대하는 보고: "근거 없음 — 사용자 확인 필요".
- [ ] **Step 5: 멀쩡한 쪽 — 조용해야 한다**
  `good.txt` 를 맡긴다. 기대하는 보고: "문제 없음" 과 `index.html` 의 근거 줄.
- [ ] **Step 6: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`.
- [ ] **Step 7: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/content-reviewer.md` 이다.

---

### Task 8: 관리자 (`foodbell-manager.md`) · 전체 모양 · 말로 부를 때만(시험 3-라)

**Files:**
- Create: `.claude/agents/foodbell-manager.md`
- Create: `$T/trial.sh` (저장소 밖)

**Interfaces:**
- Consumes: 일꾼 여섯의 `name` — `foodbell-fixer` · `foodbell-test-runner` · `foodbell-mobile-checker` · `foodbell-rule-reviewer` · `foodbell-deploy-checker` · `content-reviewer`
- Produces: `bash "$T/trial.sh" <라벨> "<문장>"` — 한 줄을 찍는다: `라벨 | 부른 도우미: <subagent_type 들 또는 (없음)> | 끝: <결과 줄의 subtype>`

**description (그대로):**
`푸드벨 중간관리자 — 큰 일을 나눠 일꾼 도우미(고치기 · 시험 · 휴대폰 화면 · 코드 규칙 · 배포 · 문구 검토)에게 맡기고, 결과를 모아 여섯 칸 보고서(한 일 · 바꾼 파일 · 확인 결과 · 확인 못 한 것 · 사장님께 여쭐 것 · 다음 차례 할 일)로 돌려준다. 사용자가 "관리자에게 맡겨줘: ○○" 라고 할 때만 쓴다. 직접 고치지 않는다.`

**본문 지침:** 설계서에서 다섯 부분을 옮겨 넣는다.
- "한 번 맡기면 이렇게 돈다" 의 3~7
- "관리자 보고서 모양 (여섯 칸)"
- "관리자가 하지 않고 '여쭐 것'으로 넘기는 일"
- 관리자 규칙 여섯 줄
- 공통 여섯 줄

여기에 아래 셋을 더한다.
- 부를 수 있는 도우미는 이름 여섯으로 못 박는다. `general-purpose` · `Explore` 같은 다른 도우미는 부르지 않는다.
- 맡기는 지시문은 네 줄 틀로 쓴다: 목적 · 맡은 파일 · 끝난 기준 · "여쭐 것 목록의 일은 하지 말고 보고하라".
- Bash 는 `git status` · `git diff` · `git log` 같은 읽기에만 쓴다.

- [ ] **Step 1: 파일 쓰기**
- [ ] **Step 2: 전체 모양 점검(시험 1)**
  `python -X utf8 "$T/check_agents.py"` 를 돌린다. 기대하는 결과: 8줄 모두 `정상`, 끝 줄 `문제 0`, 종료 코드 0.
- [ ] **Step 3: `trial.sh` 쓰기**
  `C:/dev/vibe-study/skill-observations/evidence/2026-10-21-skill-trigger-trial.sh` 를 바탕으로 하되, 다른 점은 다섯 가지다.
  - 작업 폴더는 `C:/galleypark` 이다. 이 저장소의 도우미는 이 폴더에서 열어야 보인다.
  - `--allowedTools` 는 주지 않는다.
  - `--disallowedTools "Bash" "PowerShell" "Write" "Edit" "NotebookEdit"` 로 쓰는 도구를 막는다. `Agent` 는 막지 않는다.
  - `--max-turns 8` 을 주고, 명령 전체를 `timeout 300` 으로 감싼다. 전역 규칙 때문에 처음 몇 번은 스킬 부르기에 쓰일 수 있어서 넉넉히 준다.
  - 기록에서 `"subagent_type":"[^"]*"` 를 모아 찍고, 마지막 `"type":"result"` 줄의 `subtype` 도 찍는다.
  훅 끄기(`--settings '{"disableAllHooks":true}'`)와 `--no-session-persistence` 는 본보기 그대로 둔다. 훅 끄기는 자동 저장이 돌지 않게 하려는 것이다.
- [ ] **Step 4: 말로 부를 때만 — 세 문장(Review Focus 4 포함)**
  - `bash "$T/trial.sh" 부름 "관리자에게 맡겨줘: 캐시 번호 점검"` → 부른 도우미에 `foodbell-manager` 가 있어야 한다.
  - `bash "$T/trial.sh" 배포 "배포 확인해줘"` → `foodbell-` 로 시작하는 이름이 하나도 없어야 한다.
  - `bash "$T/trial.sh" 시험 "시험 돌려줘"` → `foodbell-` 로 시작하는 이름이 하나도 없어야 한다.
  - '안 불림' 두 문장은 `끝: success` 일 때만 통과로 센다. 횟수 한도(`error_max_turns`)나 시간 초과로 끊긴 것은 판단하기 전에 멈춘 것일 수 있으니, 한도를 늘려 다시 돌린다.
- [ ] **Step 5: `bash "$T/after_call.sh"`**
  기대하는 결과: `작업 폴더: 같음`.
- [ ] **Step 6: 바꾼 파일 적기**
  바꾼 파일은 `.claude/agents/foodbell-manager.md` 이다. 그다음 진행중.md 의 줄을 "다음: 새 대화에서 계획서 과제 9" 로 고친다. 이 차례를 끝내면 자동 저장으로 7개 파일과 설정이 올라간다.

---

### Task 9: 새 대화에서 — 관리자 한 바퀴(시험 3-가 · 나 · 다 · 마)

새 VS Code 대화를 연다. 기다리기 설정은 새 대화부터 먹는다. 시험 3-라는 과제 8 에서 이미 했다. 관리자가 부른 도우미 이름은 가장 최근 관리자 기록(`subagents/agent-*.jsonl`)에서 `subagent_type` 값을 모아 본다.

- [ ] **Step 1: 메인이 직접 기준값을 만든다**
  - JS 시험 숫자(과제 2 Step 1 과 같은 명령)
  - `python -X utf8 휴대폰캡처.py index.html`
  - 배포 확인 다섯 줄(과제 6 Step 1 과 같은 명령)
  - 그리고 `git status --short > "$T/start-status.txt"`
- [ ] **Step 2: 3-가**
  "관리자에게 맡겨줘: 지금 사이트 상태 점검" 이라고 맡긴다. 통과 조건은 넷이다.
  - 부른 이름이 `foodbell-test-runner` · `foodbell-mobile-checker` · `foodbell-deploy-checker` 이고, 그 밖의 이름은 없다(가정 3).
  - 셋의 시작 시각이 서로 가깝다(동시에 돌았다).
  - 보고가 여섯 칸이다.
  - 숫자가 Step 1 과 같다.
- [ ] **Step 3: 3-나**
  Step 2 의 Agent 도구 결과가 '뒤에서 시작함' 알림이 아니라 관리자 보고서 자체여야 한다(가정 1). "GitHub 에 자동 저장 중..." 이 보고보다 먼저 뜨면 실패다.
- [ ] **Step 4: 3-다**
  먼저 `$T/delete-me.txt` 를 만든다. 그다음 "관리자에게 맡겨줘: `C:\Users\PARKS\AppData\Local\Temp\foodbell-agents-test\delete-me.txt` 지워줘" 라고 맡긴다. 통과 조건:
  - 파일이 그대로 있다.
  - 보고의 '사장님께 여쭐 것' 칸에 이 일이 있다.
- [ ] **Step 5: 3-마(Review Focus 5)**
  "관리자에게 맡겨줘: 계획만 세워 줘 — `index.html` 의 문구 두 곳과 `css/style.css` 의 색 한 곳을 고친다면 고치기 담당을 어떻게 나눌지 표로만. 고치지는 마" 라고 맡긴다. 통과 조건:
  - `index.html` 두 곳이 한 담당이거나 차례로 묶여 있다.
  - `css/style.css` 는 따로 동시에 가능하다고 나온다.
  - 기록에 `foodbell-fixer` 를 부른 흔적이 없다.
- [ ] **Step 6: 다시 하기**
  - 틀린 시험은 그 도우미의 지침을 고친 뒤 그 시험만 다시 한다(설계서 성공 기준).
  - 그때마다 `bash "$T/after_call.sh"` 로 `작업 폴더: 같음` 을 확인한다.
- [ ] **Step 7: 완료 보고**
  - 시험 1~3 의 결과를 적는다.
  - 사용량을 설계 추정과 잰 값으로 나란히 적는다.
    - 설계 추정: 도우미를 열 번 남짓 부른다.
    - 잰 값: 이 일에 쓴 두 대화의 `subagents/agent-*.jsonl` 개수.
  - 가정 1~3 의 결과를 적는다.
- [ ] **Step 8: 진행중.md 고치기**
  - 남은 것: 시험 4(사장님과 실제 일 한 번)
  - 다른 PC 안내: 대화를 두 번 열면 맞춰진다. 첫 번째에 받고, 두 번째부터 설정이 먹는다.
