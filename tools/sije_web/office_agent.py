r"""사무실 PC 상주 프로그램 — 5분마다 바뀐 행사 PDF, 하루 한 번 백업 엑셀. 윈도우에 로그온하면 저절로 시작한다
(install-agent.ps1 이 작업 스케줄러 "푸드벨 시제 PDF" 로 등록).

    python -m tools.sije_web.office_agent              # 계속 돈다 (작업 스케줄러는 pythonw 로)
    python -m tools.sije_web.office_agent --once --key C:\foodbell-keys\sije-test-admin.json --work-root %TEMP%\foodbell-sije\work

기록: %LOCALAPPDATA%\foodbell-sije\agent.log · 상태: …\state.json. 꺼져 있던 동안 바뀐 것은 켤 때 한꺼번에 만든다.
"""
import argparse
import datetime
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

from tools.sije_web import fsdb
from tools.sije_web.backup import write_backup
from tools.sije_web.pdf_sync import STATE_FILE, load_state, save_state, sync_once
from tools.sije_web.render_pdf import render_pdf, serve_repo

ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = STATE_FILE.parent / 'agent.log'
WORK_ROOT = Path(os.environ.get('USERPROFILE', Path.home())) / 'OneDrive' / 'Desktop' / '작업장' / '시제상' / '시제행사 내역서'


def setup_log(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger('foodbell-sije')
    log.setLevel(logging.INFO)
    if not log.handlers:
        h = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log.addHandler(h)
    return log


def one_cycle(source, work_root: Path, state_file: Path, base_url: str, log: logging.Logger):
    """PDF 와 백업은 따로 감싼다 — 한쪽이 실패해도 다른 쪽은 돈다."""
    result = None
    try:
        state = load_state(state_file)
        result = sync_once(source, work_root, state, lambda ev, imgs, out: render_pdf(ev, imgs, out, base_url))
        save_state(state_file, state)
        for p in result['made']:
            log.info('PDF 만듦: %s', p.name)
        for p in result['removed']:
            log.info('옛 PDF 지움: %s', p.name)
        for id, why in result['failed']:
            log.warning('PDF 실패 (다음 차례에 다시): %s — %s', id, why)
        for id, why in result['skipped']:
            log.info('PDF 건너뜀: %s — %s', id, why)
    except Exception:
        log.exception('PDF 차례 실패 (다음 차례에 다시)')
    try:
        backup = work_root / '백업' / f'{datetime.date.today():%Y-%m-%d} 시제행사 백업.xlsx'
        if not backup.exists():
            write_backup(source.all_events(), backup)
            log.info('백업 만듦: %s', backup.name)
    except Exception:
        log.exception('백업 실패 (다음 차례에 다시)')
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.office_agent', description='시제행사 PDF 자동 · 백업')
    p.add_argument('--once', action='store_true', help='한 번만 돌고 끝낸다 (시험용)')
    p.add_argument('--key', type=Path, default=fsdb.KEY_PROD, help='관리자 열쇠 (기본: 실제 프로젝트)')
    p.add_argument('--work-root', type=Path, default=WORK_ROOT, help='시제행사 내역서 폴더 (PDF · 백업이 들어갈 곳)')
    p.add_argument('--interval', type=int, default=300, help='몇 초마다 (기본 300 = 5분, 사장님 확인 전 가정)')
    a = p.parse_args(argv)
    log = setup_log(LOG_FILE)
    if not a.work_root.is_dir():   # 원드라이브 경로가 다른 PC — 동기화 안 되는 곳에 PDF 를 쌓지 않는다
        log.error('시제행사 내역서 폴더가 없습니다: %s — --work-root 로 알려 주세요', a.work_root)
        print(f'시제행사 내역서 폴더가 없습니다: {a.work_root}  (--work-root 로 알려 주세요)')
        return 2
    # 상태 기록은 열쇠(프로젝트)마다 따로 — 시험 프로젝트로 돌려 본 기록이 실제와 섞이지 않게
    state_file = STATE_FILE.with_name(f'state-{a.key.stem}.json')
    log.info('시작 (열쇠 %s, 폴더 %s, %s초마다)', a.key.name, a.work_root, a.interval)
    source = fsdb.FirestoreSource(fsdb.open_db(a.key))
    with serve_repo(ROOT) as url:
        while True:
            try:
                one_cycle(source, a.work_root, state_file, url, log)
            except Exception:       # 인터넷 끊김 등 — 기록하고 다음 차례에
                log.exception('이번 차례 실패')
                if a.once:
                    return 1
            if a.once:
                return 0
            time.sleep(a.interval)


if __name__ == '__main__':
    sys.exit(main())
