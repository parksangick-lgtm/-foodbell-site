"""이 PC 점검(PC점검.py) 의 작은 판정 함수 시험 — 이 저장소의 시험이 모두 여기 있어 같이 둔다 (2026-11-05).
실제 저장소 · 파일은 건드리지 않는다. 함수에 git 이 내는 글을 그대로 넣어 본다.
- 저장소 줄(기록장 #103): vibe-study 의 안 올린 변경이 대화가 쓴 기록뿐이면 '정상', 다른 파일이 하나라도 섞이면 '확인'.
- MCP 이름(기록장 #81 · #82): 이름 안의 ':'(plugin:…)를 첫 ':' 에서 자르지 않는다."""
import datetime
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('pc_check', REPO / 'PC점검.py')
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

# 2026-11-05 사무실 PC, 이 대화 중 vibe-study 에서 실제로 나온 git status --porcelain (core.quotepath=false)
NOW = (' M handoff/진행중.md\n'
       ' M skill-observations/activation-tiers.txt\n'
       ' M skill-updates/PENDING.md\n'
       '?? handoff/2026-11-05-기록장정리.md\n'
       '?? skill-updates/2026-11-05/\n')
# 기록장 #103 의 노트북 경우 (2026-10-31): 시작 점검이 쓴 한 줄뿐
LAPTOP = ' M skill-observations/checkpoints.log\n'


def own(out):
    return pc.session_writes_only(pc.porcelain_paths(out))


def test_paths_from_porcelain():
    assert pc.porcelain_paths(NOW) == ['handoff/진행중.md', 'skill-observations/activation-tiers.txt', 'skill-updates/PENDING.md',
                                       'handoff/2026-11-05-기록장정리.md', 'skill-updates/2026-11-05/']
    assert pc.porcelain_paths('?? "handoff/a b.md"\n') == ['handoff/a b.md']
    assert pc.porcelain_paths('R  tools/x.sh -> handoff/x.sh\n') == ['tools/x.sh', 'handoff/x.sh']


def test_session_writes_only_is_ok():   # 양성 — 이 대화가 쓴 것만
    assert own(NOW)
    assert own(LAPTOP)
    assert own(' M skill-observations/observation-log/0110-x.md\n')


def test_other_tracked_file_stays_check():   # 음성 — 다른 파일이 하나라도 섞이면 '확인'
    assert not own(NOW + ' M tools/pc-sync.sh\n')
    assert not own(LAPTOP + ' M 작업원칙.md\n')
    assert not own(' M tools/claude-global/CLAUDE.md\n')
    assert not own(' M tools/handoff/x.md\n')                    # handoff/ 가 맨 앞이 아니면 아님
    assert not own('?? skill-observations-old/x.md\n')           # 이름만 비슷한 폴더
    assert not own('R  skill-updates/a.md -> tools/a.md\n')      # 이름 바꿈의 뒤쪽이 밖이면 아님
    assert not own('')                                           # 변경 없음은 이 함수가 판정하지 않는다


# 2026-11-05 사무실 PC 에서 실제로 나온 claude mcp list 줄 (확장 2.1.314)
MCP_LINES = [
    'claude.ai Google Drive: https://drivemcp.googleapis.com/mcp/v1 - √ Connected',
    'plugin:episodic-memory:episodic-memory: node C:/Users/USER/.claude/plugins/cache/superpowers-marketplace/episodic-memory/1.6.0/cli/mcp-server-wrapper.js - √ Connected',
    'context7: https://mcp.context7.com/mcp (HTTP) - √ Connected',
    r'excel: C:\Users\USER\AppData\Local\mcp-servers\excel\Scripts\python.exe -m excel_mcp stdio - √ Connected',
]


def test_mcp_name_keeps_colons_in_name():
    assert [pc.mcp_name(l) for l in MCP_LINES] == ['claude.ai Google Drive', 'plugin:episodic-memory:episodic-memory', 'context7', 'excel']
    assert MCP_LINES[1].split(':')[0] == 'plugin'   # 대조 — 옛 자르기는 'plugin' 만 남겼다


# 기록장 #131 (2026-11-22): agent.log 오류는 줄 앞 시각으로 최근 24시간만 본다 — '마지막 500줄' 은 하루 몇 줄 쌓이는 기록이라
# 일주일 지난 11-14 오류를 계속 '확인' 으로 띄웠다. 한 차례가 1시간에 3번 넘게 실패하면 '문제'(11-13 은 5분마다 실패했다).
NOW_T = datetime.datetime(2026, 11, 22, 4, 22)
LOG = [   # 2026-11-22 사무실 PC agent.log 에서 실제로 있던 줄 모양
    '2026-11-14 19:43:57,228 ERROR 담당자 내역서 차례 실패 (다음 차례에 다시)',
    'Traceback (most recent call last):',
    '2026-11-18 05:02:06,496 ERROR 시제행사 내역서 폴더가 없습니다: C:\\Users\\USER\\AppData\\Local\\Temp\\pytest-of-USER\\pytest-177\\x — --work-root 로 알려 주세요',
    '2026-11-21 21:25:26,884 INFO 시작 (열쇠 sije-admin.json, 300초마다)',
]


def test_old_agent_error_is_not_flagged():
    assert pc.agent_log_row(LOG, NOW_T)[0] == '정상'


def test_recent_agent_error_is_check():
    state, detail = pc.agent_log_row(LOG + ['2026-11-22 01:00:00,000 ERROR 옵시디언 차례 실패 (다음 차례에 다시)'], NOW_T)
    assert state == '확인' and '옵시디언 차례 실패' in detail


def test_recent_pytest_noise_is_not_flagged():
    assert pc.agent_log_row(LOG + [LOG[2].replace('2026-11-18 05:02', '2026-11-22 04:02')], NOW_T)[0] == '정상'


def test_step_failing_every_cycle_is_problem():
    burst = [f'2026-11-22 {h:02d}:{m:02d}:00,000 ERROR 담당자 내역서 차례 실패 (다음 차례에 다시)'
             for h in (3, 4) for m in range(0, 60, 5) if (3, 25) <= (h, m) <= (4, 20)]
    state, detail = pc.agent_log_row(LOG + burst, NOW_T)
    assert state == '문제' and '담당자 내역서 차례 실패' in detail and '12번' in detail


def test_put_aside_warning_is_check():
    line = '2026-11-22 04:00:00,000 WARNING 기록 파일이 망가져 옆으로 치우고 다시 시작합니다: a.json → a.json.broken-20261122-040000'
    state, detail = pc.agent_log_row(LOG + [line], NOW_T)
    assert state == '확인' and '망가져' in detail


# 기록장 #131 (2026-11-22): 강제 종료(정전 · 전원 단추) 뒤에는 기록 파일이 0 으로 찰 수 있다(11-13) — 7일 안의 것을 한 줄로.
def test_no_shutdown_is_ok():
    assert pc.shutdown_row({'ev': []}, [])[0] == '정상'


def test_shutdown_with_button_is_check_and_names_time():
    got = {'ev': [{'t': '2026-11-21T21:24:39.1234567+09:00', 'button': True}]}
    state, detail = pc.shutdown_row(got, [('state-sije-admin-staff.json', True)])
    assert state == '확인' and '11-21 21:24' in detail and '전원 단추' in detail and '모두 읽힘' in detail


def test_broken_state_file_is_problem():
    state, detail = pc.shutdown_row({'ev': []}, [('state-sije-admin-staff.json', False), ('state-sije-admin.json', True)])
    assert state == '문제' and 'state-sije-admin-staff.json' in detail


def test_shutdown_measure_failure_is_not_ok():   # 측정 실패는 '정상' 이 아니다
    assert pc.shutdown_row({'err': '읽기 거부'}, [])[0] == '확인'
    assert pc.shutdown_row(None, [])[0] == '확인'


# 기록장 #120: 규칙이 다르면 어느 쪽이 움직였는지 — 저장본이 앞선 것(올리기 기다림)과 바깥(콘솔)에서 고친 것은 반대 상황이다.
OLD_RULES = 'rules_version = "2";\nservice cloud.firestore {\n  match /a { allow read: if true; }\n}\n'
NEW_RULES = OLD_RULES.replace('}\n}', '}\n  match /b { allow read: if true; }\n}')
HIST = [('bbbbbbb', '2026-11-04', NEW_RULES), ('aaaaaaa', '2026-10-27', OLD_RULES)]


def test_rules_same_is_ok():
    assert pc.rules_verdict(NEW_RULES.replace('\n', '\r\n'), NEW_RULES, HIST)[0] == '정상'


def test_rules_live_is_older_revision_is_check():
    state, detail = pc.rules_verdict(OLD_RULES, NEW_RULES, HIST)
    assert state == '확인' and 'aaaaaaa' in detail and '+1' in detail and '올리기 기다림' in detail


def test_rules_edited_outside_repo():
    edited = OLD_RULES + '// 콘솔에서 고침\n'
    assert pc.rules_verdict(edited, NEW_RULES, HIST)[0] == '문제'
    assert pc.rules_verdict(edited, NEW_RULES, HIST, outside='확인')[0] == '확인'   # 시험 프로젝트는 '확인'(예전 그대로)
