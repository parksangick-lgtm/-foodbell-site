r"""'인쇄해줘' — '확정 (인쇄 전)' 내역서를 행사 (날짜, 시간) 순으로 N부씩(기본 3) 한 파일로 합쳐 삼성 C48x 로 인쇄한다 (기록장 #94).

사무실 PC 에서 돈다: 어느 PDF 가 어느 행사인지는 PDF 프로그램(office_agent)의 상태 기록에 있다 — 없으면 멈춘다(printed.py 와 같이).
1. 저장소에서 인쇄 전 행사(확정 · 인쇄 표시 없음 · 날짜 있음)를 (날짜, 시간) 순으로. 상태 기록의 '확정 (인쇄 전)' PDF 와 다르면
   (방금 확정해서 PDF 가 아직 안 생김 등) 멈춘다 — 5분 뒤 다시.
2. pymupdf 로 행사마다 N부씩 한 파일(%TEMP%)로.
3. Acrobat /t 로 그 파일 하나를 인쇄 → 5초마다 인쇄 대기열(Get-PrintJob)을 보고 쪽수를 알린다 → 작업이 대기열에 다 들어가면
   이 도구가 띄운 Acrobat 을 닫는다 → 대기열이 비면 끝.
4. 임시 파일을 지운다(손님 정보가 들어 있다).

Acrobat 규칙 (2026-10-29 사무실에서 겪음): `Acrobat.exe /t` 는 인쇄한 뒤에도 Acrobat 을 띄워 둔다. 그 Acrobat 이 떠 있는 동안
두 번째 /t 를 보내면 떠 있는 Acrobat 이 받아 삼키고 아무것도 안 나온다(대기열에 작업이 안 생김, 오류도 없음).
그래서 묶음은 한 파일로 합쳐 한 번에 보내고, 묶음 사이에는 Acrobat 을 닫는다. Acrobat 이 이미 떠 있으면 이 도구는 시작하지 않는다.
이 PC 는 인쇄 기록(PrintService 이벤트 로그)이 꺼져 있어, 인쇄하는 동안 대기열을 5초마다 보는 것이 유일한 증거다.

    python -m tools.sije_web.print_pending --key C:\foodbell-keys\sije-admin.json --dry-run   # 합친 파일 쪽수까지만 (인쇄 안 함)
    python -m tools.sije_web.print_pending --key C:\foodbell-keys\sije-admin.json --test      # 첫 행사만 N부 (시험 장)
    python -m tools.sije_web.print_pending --key C:\foodbell-keys\sije-admin.json --rest      # 시험 장을 뺀 나머지
    python -m tools.sije_web.print_pending --key C:\foodbell-keys\sije-admin.json             # 전부
다 나오면 '합쳐줘' → python -m tools.sije_web.printed --key … --expect 행사수
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pymupdf

from tools.sije_web import fsdb
from tools.sije_web.pdf_sync import STATE_FILE, load_state, printed
from tools.sije_web.printed import waiting

ACROBAT = Path(r'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe')   # 사무실 PC (2026-11-05 확인)
PRINTER = 'Samsung C48x Series (USB001)'                                     # 사무실 PC Get-Printer 이름 (2026-11-05 확인)
POLL = 5            # 초 — 10초는 '안 들어온 작업' 과 '들어왔다 사라진 작업' 을 못 가렸다 (10-29)
APPEAR_WAIT = 180   # 초 — 이 안에 대기열에 작업이 안 생기면 Acrobat 이 삼킨 것으로 본다
DONE_WAIT = 3600    # 초 — 대기열이 이만큼 안 비면(종이 걸림 등) 기다리기를 그만두고 알린다
WINDOW = 3          # 초 — 파워셸 하나가 이 동안 0.1초마다 대기열을 본다(아래 jobs)


def time_key(t) -> tuple[int, int]:
    """'10시' · '10시30분' · '9시 30분' · '오전 10시' · '11' → (시, 분). 못 읽으면 (99, 0) — 그날 맨 뒤로."""
    t = t or ''
    m = re.search(r'(\d{1,2})(?:\s*[시:]\s*(\d{1,2})?)?', t)
    if not m:
        return (99, 0)
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if '오후' in t and h < 12:
        h += 12
    return (h, mi)


def pending(db, state: dict) -> tuple[list[tuple[str, dict, Path]], str]:
    """(인쇄할 [(id, 행사, PDF)] 를 (날짜, 시간) 순으로, 멈출 까닭). 저장소와 상태 기록이 다르면 목록은 비고 까닭이 찬다."""
    events = {d.id: d.to_dict() for d in db.collection('events').stream()}
    store = {id for id, ev in events.items() if ev.get('status') == '확정' and not printed(ev) and ev.get('date')}
    folder = dict(waiting(state))
    if store != set(folder):
        return [], (f"저장소의 인쇄 전 {len(store)}건과 '확정 (인쇄 전)' PDF {len(folder)}건이 다릅니다 "
                    f'(저장소에만 {len(store - set(folder))} · PDF 에만 {len(set(folder) - store)}). '
                    'PDF 프로그램이 5분마다 맞추니 5분 뒤 다시 돌립니다.')
    missing = [id for id in store if not folder[id].exists()]
    if missing:
        return [], f'상태 기록에는 있는데 폴더에 없는 PDF 가 {len(missing)}건입니다. 5분 뒤 다시 돌립니다.'
    rows = [(id, events[id], folder[id]) for id in store]
    return sorted(rows, key=lambda r: (r[1]['date'], time_key(r[1].get('time')), r[2].name)), ''


def merge_pdf(pdfs: list[Path], copies: int, out: Path) -> int:
    """PDF 마다 copies 부씩 이어 붙인 한 파일 → 쪽수."""
    with pymupdf.open() as doc:
        for p in pdfs:
            with pymupdf.open(p) as src:
                for _ in range(copies):
                    doc.insert_pdf(src)
        doc.save(out)
        return doc.page_count


def _ps(cmd: str) -> list[dict]:
    """파워셸 한 줄 → JSON 줄들 (읽기만 쓰는 명령: Get-PrintJob · Get-Printer · Get-Process)."""
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                        '[Console]::OutputEncoding = [Text.Encoding]::UTF8; ' + cmd],
                       capture_output=True, text=True, encoding='utf-8')
    out = r.stdout.strip()
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


def jobs(printer: str, window: float = WINDOW) -> list[dict]:
    """window 초 동안 대기열에 한 번이라도 보인 작업(마지막 상태로).

    파워셸 하나가 그동안 0.1초마다 본다. 한 번씩 새로 띄워 보면(1초 쉼 + 띄우는 데 1초쯤) 3장짜리는
    그 사이에 대기열을 지나가 버려, 종이는 나왔는데 '작업을 못 봤다' 로 끝났다(2026-11-05 시험 인쇄)."""
    return _ps(f"$p = '{printer}'; $end = (Get-Date).AddSeconds({window}); $seen = [ordered]@{{}}; "
               "while ((Get-Date) -lt $end) { foreach ($j in @(Get-PrintJob -PrinterName $p -ErrorAction SilentlyContinue)) { "
               "$seen[[string]$j.Id] = [pscustomobject]@{Id = $j.Id; TotalPages = $j.TotalPages; "
               "PagesPrinted = $j.PagesPrinted; Status = [string]$j.JobStatus} }; Start-Sleep -Milliseconds 100 }; "
               "@($seen.Values) | ConvertTo-Json -Compress")


def printer_exists(printer: str) -> bool:
    return bool(_ps(f"@(Get-Printer -Name '{printer}' -ErrorAction SilentlyContinue | Select-Object Name) | ConvertTo-Json -Compress"))


def acrobat_pids() -> set[int]:
    rows = _ps('@(Get-Process -Name Acrobat, AcroRd32 -ErrorAction SilentlyContinue | Select-Object Id) | ConvertTo-Json -Compress')
    return {r['Id'] for r in rows}


def close_acrobat(pids):
    """이 도구가 띄운 Acrobat 만 닫는다 (시작할 때 떠 있던 것은 없었다 — main 이 확인)."""
    for pid in pids:
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True)


def print_file(pdf: Path, printer: str, acrobat: Path, pages: int) -> tuple[bool, int]:
    """Acrobat /t 로 보내고 대기열이 빌 때까지 본다 → (다 나갔나, 대기열에서 본 쪽수)."""
    before = {j['Id'] for j in jobs(printer)}
    proc = subprocess.Popen([str(acrobat), '/t', str(pdf), printer])
    seen, closed, start = {}, False, time.time()
    try:
        while True:
            if seen:
                time.sleep(POLL)    # 처음 보일 때까지는 쉬지 않는다 — jobs() 가 그동안 내내 보고 있다
            now = [j for j in jobs(printer) if j['Id'] not in before]
            for j in now:
                seen[j['Id']] = max(seen.get(j['Id'], 0), j.get('TotalPages') or 0)
            if now:
                print(f"대기열: 작업 {len(now)} · 쪽 {sum(j.get('TotalPages') or 0 for j in now)}/{pages} · "
                      f"인쇄된 쪽 {sum(j.get('PagesPrinted') or 0 for j in now)} · {', '.join(j.get('Status') or '' for j in now)}")
                if not closed and not any('Spooling' in (j.get('Status') or '') for j in now):
                    close_acrobat({proc.pid} | acrobat_pids())     # 작업이 대기열에 다 들어갔다 — 다음 /t 가 삼켜지지 않게
                    closed = True
            elif seen:
                return True, sum(seen.values())
            elif time.time() - start > APPEAR_WAIT:
                print(f'{APPEAR_WAIT}초 동안 대기열에서 작업을 못 봤습니다. 프린터에서 종이가 나왔는지 봅니다 - '
                      '안 나왔으면 Acrobat 이 받아 삼킨 것입니다(떠 있는 Acrobat 을 닫고 다시).')
                return False, 0
            if time.time() - start > DONE_WAIT:
                print(f'{DONE_WAIT // 60}분이 지나도 대기열이 안 비었습니다. 프린터(종이 걸림 · 토너)를 봐 주세요.')
                return False, sum(seen.values())
    finally:
        if not closed:
            close_acrobat({proc.pid} | acrobat_pids())


def remove(p: Path):
    for _ in range(5):          # 닫은 Acrobat 이 파일을 막 놓는 중일 수 있다
        try:
            p.unlink(missing_ok=True)
            return
        except OSError:
            time.sleep(1)
    print(f'임시 파일을 못 지웠습니다. 손님 정보가 들어 있으니 직접 지웁니다: {p}')


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog='python -m tools.sije_web.print_pending', description="'확정 (인쇄 전)' 내역서를 날짜 · 시간 순으로 N부씩 인쇄")
    p.add_argument('--key', type=Path, required=True, help='관리자 열쇠 파일')
    p.add_argument('--copies', type=int, default=3, help='행사마다 몇 부 (기본 3)')
    which = p.add_mutually_exclusive_group()
    which.add_argument('--test', action='store_true', help='첫 행사만 (시험 장)')
    which.add_argument('--rest', action='store_true', help='첫 행사를 뺀 나머지 (시험 장을 뽑은 뒤)')
    p.add_argument('--dry-run', action='store_true', help='합친 파일 쪽수까지만 만들고 인쇄하지 않는다')
    p.add_argument('--printer', default=PRINTER, help=f'프린터 이름 (기본 {PRINTER})')
    p.add_argument('--acrobat', type=Path, default=ACROBAT, help='Acrobat.exe 위치')
    a = p.parse_args(argv)
    state_file = STATE_FILE.with_name(f'state-{a.key.stem}.json')     # office_agent 와 같은 상태 기록
    if not state_file.exists():
        print(f'이 PC 에는 PDF 프로그램 상태 기록이 없습니다 ({state_file}).')
        print('인쇄는 사무실 PC 에서 합니다. 아무것도 인쇄하지 않았습니다.')
        return 2
    rows, why = pending(fsdb.open_db(a.key), load_state(state_file))
    if why:
        print(why)
        return 4
    if not rows:
        print("인쇄할 것이 없습니다 ('확정 (인쇄 전)' 0건).")
        return 0
    pick = rows[:1] if a.test else rows[1:] if a.rest else rows
    if not pick:
        print('인쇄할 것이 없습니다 (첫 행사 하나뿐이라 나머지가 없음).')
        return 0
    for n, (_, ev, _) in enumerate(pick, 1):
        print(f"{n}. {ev['date']} {ev.get('time') or '(시간 없음)'}")
    out = Path(tempfile.gettempdir()) / f'foodbell-sije-print-{os.getpid()}.pdf'
    try:
        pages = merge_pdf([pdf for _, _, pdf in pick], a.copies, out)
        print(f'합친 파일: 행사 {len(pick)}건 x {a.copies}부 = {pages}쪽 (인쇄 전 전체 {len(rows)}건)')
        if a.dry_run:
            print(f"Acrobat {'있음' if a.acrobat.exists() else '없음'} · 프린터 {'있음' if printer_exists(a.printer) else '없음'} "
                  '(dry-run 이라 인쇄하지 않았습니다)')
            return 0
        if not a.acrobat.exists():
            print(f'Acrobat 이 없습니다: {a.acrobat} (--acrobat 로 알려 주세요). 인쇄하지 않았습니다.')
            return 5
        if not printer_exists(a.printer):
            print(f'프린터가 없습니다: {a.printer} (--printer 로 알려 주세요). 인쇄하지 않았습니다.')
            return 5
        if acrobat_pids():
            print('Acrobat 이 이미 열려 있습니다. 떠 있는 Acrobat 은 새 인쇄를 삼킵니다 - 닫고 다시 돌립니다. 인쇄하지 않았습니다.')
            return 5
        ok, sent = print_file(out, a.printer, a.acrobat, pages)
        print(f'대기열로 보낸 쪽: {sent} (합친 파일 {pages}쪽)' + ('' if sent == pages else ' - 쪽수가 다릅니다. 나온 종이를 세어 봅니다.'))
        if not ok:
            return 6
        if a.test:
            print('시험 장이 잘 나왔으면 나머지: --rest 를 붙여 다시 돌립니다.')
        else:
            print(f"다 나왔으면 '합쳐줘' → python -m tools.sije_web.printed --key {a.key} --expect {len(rows)}")
        return 0
    finally:
        remove(out)


if __name__ == '__main__':
    sys.exit(main())
