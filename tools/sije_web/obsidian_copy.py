"""옵시디언 사본 — 일일 일정표가 새로 생기거나 바뀌면 사장님 볼트의 푸드벨-업무/일일 일정표/2026-10-21 (수).md 에
복사 글(서류의 text 칸)을 쓴다. 사무실 PC 상주 프로그램(office_agent)이 차례마다 부른다. 바뀌면 덮어쓰고,
지운 일정표의 노트는 그대로 둔다. 직원은 못 보는 사장님 개인 기록.
"""
import datetime
import json
import os
import re
from pathlib import Path

OBSIDIAN_JSON = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'obsidian' / 'obsidian.json'
WORK = '푸드벨-업무'
FOLDER = '일일 일정표'
DATE = re.compile(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일')
BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')     # 윈도우 파일 이름에 못 쓰는 글자


def find_vault(obsidian_json: Path = OBSIDIAN_JSON) -> Path | None:
    """옵시디언이 적어 둔 볼트 목록(obsidian-save 와 같은 곳)에서 푸드벨-업무 폴더가 있는 볼트. 최근에 연 것 먼저, 없으면 None."""
    try:
        vaults = json.loads(Path(obsidian_json).read_text(encoding='utf-8-sig')).get('vaults')
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(vaults, dict):
        return None
    for v in sorted((v for v in vaults.values() if isinstance(v, dict) and v.get('path')),
                    key=lambda v: v.get('ts', 0), reverse=True):
        if (Path(v['path']) / WORK).is_dir():
            return Path(v['path'])
    return None


def note_path(vault: Path, label: str) -> Path:
    """'2026년 10월 21일 (수)' → 2026-10-21 (수).md (이름순 = 날짜순). 날짜 꼴이 아니면 못 쓰는 글자만 뺀다."""
    label = label or ''
    m = DATE.match(label)
    name = f'{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}{label[m.end():]}' if m else label
    name = BAD.sub('', name).strip().rstrip('.') or '(날짜 없음)'
    return Path(vault) / WORK / FOLDER / f'{name}.md'


def _stamp(v) -> str:
    if isinstance(v, datetime.datetime):
        return v.isoformat(timespec='microseconds')
    return str(v or '')


def sync_notes(docs, vault: Path, state: dict) -> list[str]:
    """state['since'] = 마지막으로 본 판(updatedAt). 그보다 새 일정표만 노트로 쓰고(덮어씀), 쓴 노트 이름들을 돌려준다."""
    since = state.get('since', '')
    written = []
    for _, doc in docs:
        at = _stamp(doc.get('updatedAt'))
        if at <= since:
            continue
        if doc.get('kind') == 'daily-schedule':
            p = note_path(vault, doc.get('label', ''))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(doc.get('text', ''), encoding='utf-8', newline='\n')
            written.append(p.stem)
        state['since'] = max(state.get('since', ''), at)
    return written
