"""이 PC 점검(PC점검.py) 의 작은 판정 함수 시험 — 이 저장소의 시험이 모두 여기 있어 같이 둔다 (2026-11-05).
실제 저장소 · 파일은 건드리지 않는다. 함수에 git 이 내는 글을 그대로 넣어 본다.
- 저장소 줄(기록장 #103): vibe-study 의 안 올린 변경이 대화가 쓴 기록뿐이면 '정상', 다른 파일이 하나라도 섞이면 '확인'.
- MCP 이름(기록장 #81 · #82): 이름 안의 ':'(plugin:…)를 첫 ':' 에서 자르지 않는다."""
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
