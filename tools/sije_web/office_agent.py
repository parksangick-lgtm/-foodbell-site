r"""사무실 PC 상주 프로그램 — 5분마다 바뀐 행사 PDF · 캘린더 맞추기, 하루 한 번 백업 엑셀. 윈도우에 로그온하면 저절로 시작한다
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

from tools.sije_web import calendar_sync, fsdb, obsidian_copy, staff_sheets
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


def one_cycle(source, work_root: Path, state_file: Path, base_url: str, log: logging.Logger, calendar=None, vault=None, sheets=None):
    """PDF · 백업 · 캘린더 · 옵시디언 · 담당자 내역서는 따로 감싼다 — 하나가 실패해도 나머지는 돈다.
    sheets 는 Firestore db — None 이면 담당자 내역서 차례를 건너뛴다.
    calendar 는 calendar_sync.CalendarJob — None 이면(캘린더 ID 파일 없는 PC) 건너뛴다.
    vault 는 옵시디언 볼트 — None 이면(푸드벨-업무 볼트를 못 찾은 PC, 시작할 때 기록에 한 줄) 건너뛴다."""
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
            write_backup(source.all_events(), backup, source.all_docs())
            log.info('백업 만듦: %s', backup.name)
    except Exception:
        log.exception('백업 실패 (다음 차례에 다시)')
    if calendar is not None:
        try:
            for label, cal in (calendar.run(source, time.time()) or {}).items():
                name = '캘린더' if label == '사장님' else f'캘린더({label})'   # 사장님 캘린더는 예전 기록 모양 그대로
                err = cal.get('error')
                if isinstance(err, calendar_sync.CalendarError):   # 공유가 풀림 · 서비스 꺼짐 등 — 긴 오류 대신 한 줄
                    log.warning('%s 차례 실패 (다음 변경이나 1시간 뒤 다시): %s', name, err)
                    continue
                if err is not None:
                    log.error('%s 차례 실패 (다음 변경이나 1시간 뒤 다시)', name, exc_info=err)
                    continue
                for word, key in (('만듦', 'made'), ('고침', 'updated'), ('지움', 'removed')):
                    for title in cal[key]:
                        log.info('%s %s: %s', name, word, title)
                for id, why in cal['failed']:
                    log.warning('%s 실패 (다음 차례에 다시): %s — %s', name, id, why)
                if cal['guarded']:
                    log.warning('%s: 행사 목록이 0개로 읽혀 지우기를 건너뜀', name)
        except calendar_sync.CalendarError as e:
            log.warning('캘린더 차례 실패 (다음 차례에 다시): %s', e)
        except Exception:   # 행사 목록 읽기 실패 등
            log.exception('캘린더 차례 실패 (다음 차례에 다시)')
    if vault is not None:
        try:
            notes_file = state_file.with_name(f'{state_file.stem}-obsidian.json')
            notes = load_state(notes_file)
            for name in obsidian_copy.sync_notes(source.changed_since(notes.get('since'), 'docs'), vault, notes):
                log.info('옵시디언 일정표 노트 씀: %s', name)
            save_state(notes_file, notes)
        except Exception:
            log.exception('옵시디언 차례 실패 (다음 차례에 다시)')
    if sheets is not None:
        try:
            out = staff_sheets.sync_staff_sheets(sheets, datetime.date.today())
            for d in out['written']:
                log.info('담당자 내역서 올림: %s', d)
            for d in out['removed']:
                log.info('담당자 내역서 지움: %s', d)
        except Exception:
            log.exception('담당자 내역서 차례 실패 (다음 차례에 다시)')
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
    # 캘린더: 사장님용(확정 · 미확정, 금액 · 내역서 주소) + 직원용(확정만, 출발 · 도착 · 꼭 지킬 것). ID 파일이 있는 것만
    targets = [(label, cal, staff) for label, cal, staff in (
        ('사장님', calendar_sync.open_calendar(a.key), False),
        ('직원', calendar_sync.open_calendar(a.key, 'staff-calendar'), True)) if cal]
    calendar = calendar_sync.CalendarJob(targets) if targets else None
    vault = obsidian_copy.find_vault()
    log.info('시작 (열쇠 %s, 폴더 %s, %s초마다, 캘린더 %s)', a.key.name, a.work_root, a.interval,
             ' · '.join(label for label, _, _ in targets) or '끔')
    if vault is None:
        log.warning('옵시디언 볼트(푸드벨-업무 폴더가 있는 것)를 못 찾아 일정표 사본은 건너뜁니다')
    else:
        log.info('옵시디언 일정표 사본: %s', vault)
    source = fsdb.FirestoreSource(fsdb.open_db(a.key))
    with serve_repo(ROOT) as url:
        while True:
            try:
                one_cycle(source, a.work_root, state_file, url, log, calendar, vault, sheets=source.db)
            except Exception:       # 인터넷 끊김 등 — 기록하고 다음 차례에
                log.exception('이번 차례 실패')
                if a.once:
                    return 1
            if a.once:
                return 0
            time.sleep(a.interval)


if __name__ == '__main__':
    sys.exit(main())
