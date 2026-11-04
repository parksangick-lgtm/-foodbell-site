r"""바뀐 행사만 PDF 로 — 원드라이브 '…\2026년 PDF (휴대폰용)\{상태}\' 에, 지금 PDF 와 같은 이름으로.

- 날짜 · 장소 · 상태가 바뀌면 옛 이름의 PDF 를 지우고 새 이름 · 새 폴더로 (같은 행사 PDF 가 둘이 되지 않게).
- 확정인데 아직 인쇄해 묶지 않은 것(인쇄 표시 printedAt 이 없거나 그 뒤에 고친 것)은 '확정 (인쇄 전)' 폴더로.
  인쇄한 뒤 printed.py 로 표시하면 다음 차례에 '확정' 으로 옮긴다 (2026-10-26 사장님 — 인쇄해 둔 묶음과 섞이지 않게).
- 실패(그리기 오류 · 1쪽이 아님 · 잘린 글자)는 기록하고 다음 차례에 다시. 이미 만든 판은 다시 그리지 않는다.
- 이름이 겹치지 않게 (2026-11-05 사장님, 기록장 #95): fileLabel 도 장소도 비면 ' ' + 시간. 그래도 같은 폴더에 같은 이름이면
  id 순으로 뒤의 것에 ' (2)', ' (3)'. 겹침은 모든 행사를 보고 정한다 — 상태 기록의 이름 목록(names)에 행사마다 폴더 · 이름 앞부분을
  두고, 다른 행사 때문에 이름이 바뀌는 행사가 생기면 그 차례에 전체를 한 번 읽어 다시 그린다(평소에는 바뀐 것만 읽는다).
  옛 PDF 는 다른 행사가 그 자리를 쓰고 있으면 지우지 않는다 (예전에는 같은 이름을 나눠 쓴 행사끼리 5분마다 서로 지웠다).
"""
import collections
import datetime
import json
import os
import re
from pathlib import Path

from tools.sije_web.render_pdf import clipped_words

SEASON = 2026   # PDF 폴더 연도 = 시제철 — 미확정 · 주문없음 행사는 작년 날짜를 들고 있어서 날짜에서 뽑지 않는다
STATE_FILE = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'foodbell-sije' / 'state.json'
PENDING = '확정 (인쇄 전)'


def _iso(v) -> str:
    return v.isoformat() if isinstance(v, (datetime.datetime, datetime.date)) else str(v or '')


def _when(v):
    """저장소에서는 datetime, 시험에서는 ISO 글자로 온다."""
    return datetime.datetime.fromisoformat(v) if isinstance(v, str) and v else (v or None)


def printed(ev: dict) -> bool:
    """인쇄 표시가 있고, 그 뒤로 고치지 않았다."""
    at, up = _when(ev.get('printedAt')), _when(ev.get('updatedAt'))
    return at is not None and (up is None or up <= at)


def _head(ev: dict) -> str:
    """이름 앞부분 '{YYYY}년{M}월{D}일{fileLabel}' — fileLabel 이 비면(새 행사) ' ' + 장소, 장소도 비면 ' ' + 시간('11' 은 '11시')."""
    y, m, d = (int(x) for x in ev['date'].split('-'))
    label = ev.get('fileLabel') or ' ' + (ev.get('place') or '')
    t = (ev.get('time') or '').strip()
    if not label.strip() and t:
        label = ' ' + (t + '시' if t.isdigit() else t)
    return f'{y}년{m}월{d}일{label}'


def _name(head: str, n: int = 1) -> str:
    tail = f' ({n})' if n > 1 else ''
    return re.sub(r'[<>:"/\\|?*]', '_', f'{head}{tail} 시제행사 내역서.pdf')


def pdf_name(ev: dict) -> str:
    """'{YYYY}년{M}월{D}일{fileLabel} 시제행사 내역서.pdf' — 다른 행사와 겹칠 때 붙는 ' (n)' 은 targets 가 정한다."""
    return _name(_head(ev))


def folder(ev: dict) -> str:
    return PENDING if ev['status'] == '확정' and not printed(ev) else ev['status']


def target_path(work_root: Path, ev: dict) -> Path:
    """이 행사 하나만 보고 정한 자리 — 다른 행사와 겹치는지는 targets 가 본다."""
    return Path(work_root) / f'{SEASON}년 PDF (휴대폰용)' / folder(ev) / pdf_name(ev)


def _assign(keys: dict) -> dict:
    """{id: (폴더, 이름 앞부분)} → {id: (폴더, 파일 이름)}. 같은 폴더 · 같은 이름이면 id 순으로 첫 것은 그대로,
    뒤의 것은 다른 행사가 안 쓰는 가장 작은 ' (n)' (n ≥ 2). 같은 행사 목록이면 매번 같은 답."""
    taken = {(f, _name(h)) for f, h in keys.values()}      # 이름 그대로 쓰는 자리 — 사장님이 손으로 붙인 '(2)' 도 여기 든다
    out, first = {}, set()
    for id in sorted(keys):
        f, h = keys[id]
        if (f, _name(h)) not in first:
            first.add((f, _name(h)))
            out[id] = (f, _name(h))
            continue
        n = 2
        while (f, _name(h, n)) in taken:
            n += 1
        taken.add((f, _name(h, n)))
        out[id] = (f, _name(h, n))
    return out


def targets(work_root: Path, events) -> dict:
    """[(id, 행사)] → {id: PDF 자리}. 날짜 없는 행사는 PDF 가 없어서 뺀다. 겹치는 이름을 가른 뒤의 자리."""
    root = Path(work_root) / f'{SEASON}년 PDF (휴대폰용)'
    keys = {id: (folder(ev), _head(ev)) for id, ev in events if ev.get('date')}
    return {id: root / f / n for id, (f, n) in _assign(keys).items()}


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
    full = 'names' not in state               # 이름 목록이 없으면(처음 · 11-05 고침 전 기록) 전체를 한 번 읽는다
    names = state.setdefault('names', {})     # id → [폴더, 이름 앞부분] — 겹침을 모든 행사로 판단하려고
    made, removed, failed, skipped = [], [], [], []
    for old in list(stale):
        if old in paths.values():         # 그사이 다른 행사가 그 자리를 쓰게 됐다 — 지우지 않는다
            stale.remove(old)
            continue
        try:
            Path(old).unlink(missing_ok=True)
        except OSError:
            continue
        stale.remove(old)
        removed.append(Path(old))
    shared = {p for p, n in collections.Counter(paths.values()).items() if n > 1}   # 예전 규칙으로 이름을 나눠 쓰던 PDF

    def note(changed, everything):
        """이름 목록을 고치고 {id: 겹침을 가른 뒤의 PDF 자리} 를 돌려준다."""
        if everything:
            names.clear()                 # 전체를 읽었으면 목록을 새로 — 저장소에 없는 행사가 자리를 잡고 있지 않게
        for id, ev in changed:
            if ev.get('date'):
                names[id] = [folder(ev), _head(ev)]
            else:
                names.pop(id, None)
        root = Path(work_root) / f'{SEASON}년 PDF (휴대폰용)'
        return {id: str(root / f / n) for id, (f, n) in _assign({i: tuple(k) for i, k in names.items()}).items()}

    changed = source.changed_since(None if full else state.get('since'))
    want = note(changed, full)
    seen = {id for id, _ in changed}
    if not full and any(id not in seen and id in paths and (paths[id] != p or p in shared) for id, p in want.items()):
        # 다른 행사 때문에 이름이 바뀌는 행사가 있다 — 그 행사 내용으로 다시 그리려고 이번 차례에 전체를 읽는다
        changed = source.changed_since(None)
        want = note(changed, True)
    for id, ev in changed:
        version = _iso(ev.get('updatedAt'))
        if done.get(id) == version and (id not in want or (paths.get(id) == want[id] and want[id] not in shared)):
            continue
        if not ev.get('date'):            # 새 행사는 날짜 없이 시작한다 — 날짜가 생기면(판이 바뀌면) 그때 만든다
            skipped.append((id, '날짜 없음'))
            done[id] = version
            continue
        tmp = None
        try:
            target = Path(want[id])
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
        if old and Path(old) != target and old not in paths.values():   # 다른 행사가 그 자리를 쓰면 지우지 않는다
            try:
                Path(old).unlink(missing_ok=True)
                removed.append(Path(old))
            except OSError:
                stale.append(old)
    if changed and not failed:          # 실패가 있으면 since 를 그대로 둬서 다음 차례에 다시 받는다
        state['since'] = max(_iso(ev.get('updatedAt')) for _, ev in changed)
    return {'made': made, 'removed': removed, 'failed': failed, 'skipped': skipped}
