# 직원 확인 단추 — 만들기 계획 (관리자에게 맡김)

**설계서:** `docs/superpowers/specs/2026-11-04-staff-confirm-design.md` (사장님 확인 끝 11-05). 계획과 설계가 부딪히면 설계를 따르고 보고한다.
**목표:** 직원이 `today.html` 에서 자기 이름을 눌러 일정표 확인을 남기고, 사장님은 일정표 화면 확인 줄로 본다.
**맡김:** 사장님 "관리자를 불러서 작업해줘"(11-05 사무실). n8n 밤 9시 알림(설계 3-5)과 실제 규칙 올리기는 이 계획에 없다 — 메인 · 사장님 몫.

## 이미 한 것 (메인, 11-05)

- `firestore.rules` 에 `match /share/{key}/marks/{mark}` 를 설계 3-6 글자 그대로 넣었다.
- **시험 프로젝트(foodbell-sije-test)에만** 올렸다 — 관리자 열쇠로 Rules REST API. 올린 뒤 받은 규칙 = 파일(줄바꿈만 맞춰 비교). 실제 프로젝트에는 안 올렸다.

## 확인한 사실 — 메인이 이 세션에 파일을 열어 본 것 (다시 조사하지 않아도 된다)

- `today.html:80` 과 `sije-view.html:56` 이 `share-store.js?v=2` 로 부른다. 설계서 3-3 의 "판 번호 없이 부른다" 는 낡은 문장이다 → 둘 다 `?v=3`.
- `js/sije/store.js:182-206` `publishShare` — 게시판을 처음 한 번만 읽고(`shareSeen`), 올릴 때마다 `at` 을 새로 찍는다.
- `js/docs/doc-page.js:300` 서류를 **열기만 해도** `publish(false)`. `doc-page.js:428-457` 로그인 뒤 `watchDoc`(449줄).
- `store.js?v=2` 를 부르는 곳: `doc-page.js:10` · `js/sije/list-page.js:7` · `js/sije/sheet-page.js:9` · 시험 `test_sheet_page.py:329` → 모두 `?v=3`.
- `doc-page.js?v=15` 를 부르는 곳(6): `daily-schedule.html:1214` · `event-quote.html:850` · `sije-quote.html:957` · `sije-worksheet.html:906` · `staff-pay.html:800` · `statement.html:780` → `?v=16`.
- `sw.js:3` `CACHE = 'foodbell-v42'` → `v43`.
- `daily-schedule.html`: 모듈 import 474-478줄 · `clean()`(492)은 모든 빈칸(nbsp 포함)을 한 칸으로 · `recalc()` 끝 551-554 가 `.day-stats` 를 없으면 만든다 · `serialize()` 612 가 `.day-stats` 를 비운다 · CSS 277-279 · `share()` 1199-1204.
- `tools/sije_web/share_link.py:29-42` `new_key` — entries 만 옮기고 옛 게시판을 지운다.
- 시험 도구: `test_doc_pages.py` 의 `share_key`(1370) · `wait_board`(1385) · `daily_new` · `edit_cell` · `new_ctx` / `test_today_page.py` 의 `key`(42) · `put`(52) · `phone` / `test_rules_live.py` 의 `board`(194) · `call`(40) · `id_token`.

## 정한 모양 — 일꾼끼리 이름을 맞추려고 (메인이 정함)

### 1. 부품 `js/docs/confirm.js` (새 파일, 부르는 곳은 `?v=1`)

```js
export function staffNames(text)            // -> string[]
export function confirmState(entry, marks)  // entry {at: ms|null, names: string[]}, marks [{name, at: ms|null}]
                                            // -> { done: [{name, at}], waiting: [name], stale: [name], pending: [name] }
export function confirmLine(state, hhmm)    // hhmm(ms) -> 'HH:MM'. -> 사장님 한 줄 글자
```

- `staffNames`: 괄호 `( … )` · `（ … ）` 안은 뺀다(닫는 괄호가 없으면 끝까지). 나누는 글자는 `.` `,` `·` `/` `、` `+` 와 빈칸(`\s` — nbsp 포함). 빈 조각은 버리고, 같은 이름은 처음 하나만, 나온 순서대로.
- `confirmState`: `names` 순서대로. 기록 없음 → `waiting`. 기록의 `at` 이 null(눌렀는데 아직 서버에 안 감) → `pending`. `entry.at` 이 있고 기록 `at` < `entry.at` → `stale`(고친 뒤 안 봄). 그 밖 → `done`. `names` 에 없는 이름의 기록은 무시(사장님이 담당을 바꾼 경우).
- `confirmLine`: `직원 확인 2/4 · 박○○ 07:12 · 최○○ 07:30 · 아직: 김○○ · 이○○(고친 뒤 안 봄)` (설계 3-4). 분모 = `names` 수, 분자 = `done` 수. '아직:' 뒤에는 waiting · pending 이름, 그다음 stale 이름에 `(고친 뒤 안 봄)`. 아직인 사람이 없으면 '· 아직: …' 을 뺀다. `names` 가 비면 빈 글자.

### 2. `js/sije/store.js` (사장님 쪽)

- `publishShare(id, entry)`: 처음 한 번만 읽던 `shareSeen` 대신 **부를 때마다** 게시판을 읽는다(`fs.getDoc`, 실패면 빈 것). `entry` 가 있고 이미 올라간 `entries[id]` 와 **`at` 을 빼고 칸 순서와 상관없이** 같으며 지울 지난 날짜 칸도 없으면 쓰지 않고 `true`. 다르면 지금처럼 쓴다(오타 하나라도 다르면 씀 — 사장님 결정).
- 새 `export function watchConfirm(id, cb)` → 끊기 함수. `config/share` 의 암호로 `share/{암호}` 문서의 `entries[id]` 와 `share/{암호}/marks` 중 `sid == id` 를 바로 읽어 `cb({ at, names, marks: [{name, at}] })`, 그 칸이 없으면 `cb(null)`. 시각은 ms 숫자. 게시판 문서는 `data({ serverTimestamps: 'estimate' })` 로 읽는다 — 사장님이 방금 고친 것(서버 시각 대기)도 '지금' 으로 쳐야 '고친 뒤 안 봄' 이 바로 보인다. 암호가 없으면 cb 를 부르지 않는다.
- 맨 위 주석대로 `store.js?v=` 를 부르는 곳 전부 올린다.

### 3. `daily-schedule.html` (사장님 화면)

- `import { staffNames, confirmState, confirmLine } from './js/docs/confirm.js?v=1';`
- `share()` 에 `names` — `rowsData()` 의 모든 줄(연기 · 취소 포함)의 `staff` 를 `staffNames` 로 나눠 합친 목록(나온 순서, 겹침 없음).
- `D.showConfirm(info)` — 받은 것을 기억해 두고 `.day-stats` 바로 뒤 `<p class="day-confirm">` 에 `confirmLine(...)` 을 쓴다(없으면 만든다 — `.day-stats` 552줄처럼). `info` 가 null 이거나 `names` 가 비면 빈 글자. `load()` 가 `sheet.innerHTML` 을 바꾸므로 `recalc()` 끝에서도 다시 그린다.
- CSS 는 `.day-stats`(277-279)와 같게: `:empty` 숨김 · 인쇄 숨김. `serialize()` 는 `.day-confirm` 을 비운다(612줄처럼). 사진 카드 · 복사 글은 이 줄을 읽지 않으니 그대로.

### 4. `js/docs/doc-page.js`

- `watchConfirm` 을 import(그 줄의 `store.js?v=3`). 449줄 `watchDoc` 다음, `role === 'owner' && D.showConfirm` 이면 `watchConfirm(docId, D.showConfirm)` 도 켜고, 로그인이 바뀌면(`stop?.()`) 둘 다 끈다.

### 5. `js/sije/share-store.js` (직원 쪽, 로그인 없음)

```js
export function confirmMark(key, sid, name)        // setDoc share/{key}/marks/{sid~name} = {sid, name, at: serverTimestamp()}
export function watchMarks(key, cb, onError)       // cb([{sid, name, at: ms|null, pending: bool}]) — includeMetadataChanges
```

### 6. `today.html` (직원 화면)

- `#day-memo` 와 `#cards` 사이에 확인 칸. 상태 여섯 가지와 글자는 설계 3-3 표 그대로. 단 **'✓' 는 쓰지 않는다** — CLAUDE.md "아이콘에 이모지 · 특수문자 금지 → 인라인 SVG 선 아이콘".
- 눌렀는데 `pending` 이 2초 넘게 이어지면 "연결되면 올라갑니다"(그 전에는 조용히). 저장소가 기기에 들고 있다가 연결되면 올린다.
- 이름은 `localStorage` `foodbell-today-name` (try/catch — 못 읽으면 다시 고르게). 이름 단추를 누르는 것 = 확인 + 이름 기억.
- 오늘 · 내일 단추로 일정표를 바꾸면 그 일정표 것으로. `names` 가 없는 일정표면 칸을 숨긴다.
- 실패(끊김이 아닌 것)는 "확인을 올리지 못했습니다 (이유)" 를 한 번 보인다.
- 색 · 크기는 `today.html` 의 `:root` 값만. 단추 44px 이상, 글자 14px 이상.
- `confirmState` 는 `./js/docs/confirm.js?v=1` 에서. `share-store.js?v=3`.

### 7. `tools/sije_web/share_link.py`

- `new_key` 가 `share/{옛}/marks` 의 문서를 새 게시판 `marks` 로 옮기고 옛 것을 지운다(같은 batch). 그만둔 직원이 옛 링크로 이름 · 시각을 못 보게.

### 8. 캐시 번호

`share-store.js?v=3`(today · sije-view) · `store.js?v=3`(doc-page · list-page · sheet-page · test_sheet_page.py) · `doc-page.js?v=16`(html 6개) · `sw.js` `foodbell-v43` · 새 `confirm.js?v=1`.
`sw.js` 의 `PRECACHE` 에 `js/docs/` 의 다른 부품이 들어 있으면 `confirm.js` 도 넣는다. `js-tests/doc-page-imports.test.mjs` 가 통과해야 한다.

## 시험 (설계 5절)

- **JS** `tools/sije_web/js-tests/confirm.test.mjs`(새): `staffNames` — 점 · 빗금 · 빈칸 · nbsp · 괄호 · 같은 이름 두 번 · 빈 글자 · `·` `、` `+`. `confirmState` — done · waiting · stale · 목록에서 빠진 이름 · pending. `confirmLine` 글자 모양.
- **보안 규칙** `test_rules_live.py`(규칙은 이미 시험 프로젝트에 올라가 있다): 서버 시각은 REST `documents:commit` 의 `updateTransforms`(`setToServerValue: REQUEST_TIME`)로 쓴다. 로그인 없이 목록 이름 + 서버 시각 → 200. 막힘: 목록에 없는 이름 · 다른 칸 더 · 휴대폰 시각 · 문서 이름과 칸 다름 · 없는 게시판 · 다른 일정표 id. 지우기는 로그인 없으면 막히고 사장님은 된다. 게시판 문서 쓰기는 여전히 막힌다.
- **직원 화면** `test_today_page.py`(390px): 이름 단추가 담당대로 · 누르면 기록이 생기고 '확인함' · 다시 열면 기억한 이름 단추 하나 · 사장님이 고치면(게시판 `at` 이 기록보다 나중) '다시 확인' · `names` 없으면 숨음 · 끊긴 채 누르면 '연결되면 올라갑니다', 연결되면 올라감 · 넘침 0 · 44px · 14px.
- **사장님 화면** `test_doc_pages.py`: `share()` 에 `names` · 열기만 하면 `at` 이 안 바뀌고 고치면 바뀜 · 확인 줄이 바로 바뀜(관리자 열쇠로 marks 에 넣고 기다림) · 인쇄 · `serialize()` · 복사 글에 확인 줄 없음.
- **암호 바꾸기** `test_share_link.py`: 확인 기록이 새 게시판으로 옮겨지고 옛 것은 없다.
- 공용 파일(`store.js` · `doc-page.js`)을 고치므로 끝에 **시험 전체**(`python -X utf8 -m pytest tools/sije_web/tests -q` + `node --test tools/sije_web/js-tests/*.test.mjs`)를 한 번. 서류 시험과 서류 화면 캡처는 차례로.

## 하지 않는 것

- 실제 프로젝트 규칙 올리기 · n8n · 커밋 · 파일 지우기 → 보고서 5칸.
- `CLAUDE.md` · `docs/클로드-참고.md` 는 고치지 않는다(메인이 끝에 적는다).

## 보고에 꼭 넣을 것

시험마다 숫자와 명령 · 바꾼 캐시 번호 목록 · 설계 / 이 계획과 다르게 한 곳과 까닭.
