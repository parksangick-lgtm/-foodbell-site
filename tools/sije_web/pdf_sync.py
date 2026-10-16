r"""바뀐 행사만 PDF 로 — 원드라이브 '…\2026년 PDF (휴대폰용)\{상태}\' 에, 지금 PDF 와 같은 이름으로.

- 날짜 · 장소 · 상태가 바뀌면 옛 이름의 PDF 를 지우고 새 이름 · 새 폴더로 (같은 행사 PDF 가 둘이 되지 않게).
- 실패(그리기 오류 · 1쪽이 아님 · 잘린 글자)는 기록하고 다음 차례에 다시. 이미 만든 판은 다시 그리지 않는다.
"""
import datetime
import json
import os
import re
from pathlib import Path

from tools.sije_web.render_pdf import clipped_words

SEASON = 2026   # PDF 폴더 연도 = 시제철 — 미확정 · 주문없음 행사는 작년 날짜를 들고 있어서 날짜에서 뽑지 않는다
STATE_FILE = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'foodbell-sije' / 'state.json'


def _iso(v) -> str:
    return v.isoformat() if isinstance(v, (datetime.datetime, datetime.date)) else str(v or '')


def pdf_name(ev: dict) -> str:
    """'{YYYY}년{M}월{D}일{fileLabel} 시제행사 내역서.pdf' — fileLabel 이 비면(새 행사) ' ' + 장소."""
    y, m, d = (int(x) for x in ev['date'].split('-'))
    label = ev.get('fileLabel') or ' ' + ev.get('place', '')
    return re.sub(r'[<>:"/\\|?*]', '_', f'{y}년{m}월{d}일{label} 시제행사 내역서.pdf')


def target_path(work_root: Path, ev: dict) -> Path:
    return Path(work_root) / f'{SEASON}년 PDF (휴대폰용)' / ev['status'] / pdf_name(ev)


def load_state(p: Path) -> dict:
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def save_state(p: Path, state: dict):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(p)


def sync_once(source, work_root: Path, state: dict, render) -> dict:
    """render(ev, images, out) -> 쪽수. state 를 고쳐 놓고 {made, removed, failed, skipped} 를 돌려준다.
    행사 하나의 실패(그리기 · 잠긴 파일 등)가 다른 행사나 이번 차례 전체를 멈추지 않게, 행사마다 따로 감싼다."""
    paths = state.setdefault('paths', {})
    done = state.setdefault('done', {})       # id → 마지막으로 PDF 를 만든 판(updatedAt)
    stale = state.setdefault('stale', [])     # 열려 있어서 못 지운 옛 PDF — 차례마다 다시 지워 본다
    made, removed, failed, skipped = [], [], [], []
    for old in list(stale):
        try:
            Path(old).unlink(missing_ok=True)
        except OSError:
            continue
        stale.remove(old)
        removed.append(Path(old))
    changed = source.changed_since(state.get('since'))
    for id, ev in changed:
        version = _iso(ev.get('updatedAt'))
        if done.get(id) == version:
            continue
        if not ev.get('date'):            # 새 행사는 날짜 없이 시작한다 — 날짜가 생기면(판이 바뀌면) 그때 만든다
            skipped.append((id, '날짜 없음'))
            done[id] = version
            continue
        tmp = None
        try:
            target = target_path(work_root, ev)
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.stem + '.만드는중.pdf')
            pages = render(ev, source.images(id), tmp)
            if pages != 1:
                raise RuntimeError(f'{pages}쪽')
            if clipped_words(tmp):
                raise RuntimeError('잘린 글자')
            tmp.replace(target)
        except Exception as e:        # 다음 차례에 다시
            if tmp:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            failed.append((id, str(e) or type(e).__name__))
            continue
        old = paths.get(id)
        paths[id] = str(target)
        done[id] = version
        made.append(target)
        if old and Path(old) != target:
            try:
                Path(old).unlink(missing_ok=True)
                removed.append(Path(old))
            except OSError:
                stale.append(old)
    if changed and not failed:          # 실패가 있으면 since 를 그대로 둬서 다음 차례에 다시 받는다
        state['since'] = max(_iso(ev.get('updatedAt')) for _, ev in changed)
    return {'made': made, 'removed': removed, 'failed': failed, 'skipped': skipped}
