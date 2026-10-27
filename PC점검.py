"""이 PC 점검 — 세 PC 공통 (foodbell-site-dev 스킬 8절). 사용: python -X utf8 PC점검.py [--tests]
읽기만 한다(아무것도 고치지 않는다). 줄마다 '정상' · '확인'(살펴볼 것) · '문제' 를 숫자와 함께 찍고, 끝에 모아 보여 준다.
2026-10-28: 점검할 때마다 목록을 손으로 다시 짜던 것을(기록장 #40, 일곱 번) 한 번에. 그날 걸린 측정 함정 넷을 피한다 —
  · node --test 에 폴더를 주면 0개 돌고 '실패 1' 로 나온다 → 파일 목록(*.test.mjs)을 준다
  · git 이 한글 경로를 \\354… 로 내보낸다 → core.quotepath=false
  · 이 PC 파일은 줄바꿈이 CRLF 로 풀려 있어 서버와 늘 다르게 나온다 → 서버와는 저장본(git show HEAD:)을 비교한다
  · PDF 프로그램의 '옛 코드' 는 저장(커밋) 시각이 아니라 그 프로그램이 부르는 파일을 고친 시각으로 판단한다
--tests 를 주면 시험 전체(JS + 파이썬, 15분쯤)도 돈다. 서류 시험은 시험 프로젝트를 쓰므로 다른 서류 시험과 겹쳐 돌리지 않는다."""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import winreg
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent
DEV = Path(r'C:\dev')
HOME = Path.home()
CLAUDE = HOME / '.claude'
KEYS = Path(r'C:\foodbell-keys')
SITE = 'https://foodbell.kr/'
rows = []


def row(group, name, state, detail=''):
    rows.append((state, group, name, detail))
    print(f'{state}  [{group}] {name}' + (f' — {detail}' if detail else ''), flush=True)


def run(cmd, timeout=120):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def git(repo, *args, timeout=60):
    return run(['git', '-C', str(repo), '-c', 'core.quotepath=false', *args], timeout=timeout)


def ps_json(script, timeout=90):
    """파워셸 결과를 JSON 목록으로 (한 개면 목록으로 감싼다)."""
    _, out, _ = run(['powershell', '-NoProfile', '-Command',
                     '[Console]::OutputEncoding=[Text.Encoding]::UTF8; ' + script + ' | ConvertTo-Json -Compress -Depth 3'], timeout)
    out = out.strip()
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


WEB = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))


def http(url):
    """(상태 번호, 넘겨주는 주소, 본문). 넘겨주기(308)는 따라가지 않는다."""
    try:
        r = WEB.open(url, timeout=25)
        return r.status, r.headers.get('Location'), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Location'), b''
    except Exception as e:
        return None, f'{type(e).__name__}: {e}', b''


# ---------------------------------------------------------------- 1. PC · 저장소
def pc_and_repos():
    row('PC', '이름', '정상', f"{os.environ.get('COMPUTERNAME')} · 커밋 이름 {git(REPO, 'config', 'user.name')[1].strip()}")
    dirs = [REPO] + sorted(p for p in DEV.iterdir() if p.is_dir())
    for d in dirs:
        if not (d / '.git').exists():
            row('저장소', d.name, '확인', 'git 저장소가 아님 — 자동 저장으로 다른 PC 에 안 따라감')
            continue
        git(d, 'fetch', '-q', timeout=60)
        head = git(d, 'status', '-sb')[1].splitlines()[0]
        dirty = len([l for l in git(d, 'status', '--porcelain')[1].splitlines() if l])
        lag = re.findall(r'(ahead|behind) (\d+)', head)
        state = '정상' if not lag and dirty == 0 else '확인'
        row('저장소', d.name, state, head.replace('## ', '') + (f' · 안 올린 변경 {dirty}개' if dirty else ''))


# ---------------------------------------------------------------- 2. 클로드 설정 · 스킬
def claude_setup():
    user = (CLAUDE / 'settings.json').read_text(encoding='utf-8')
    proj = (REPO / '.claude' / 'settings.json').read_text(encoding='utf-8')
    miss = [h for h in ('git-auto-sync', 'korean-reminder', 'korean-reply-check') if h not in user]
    miss += [h for h in ('auto-save', 'cache-reminder', 'index-guard') if h not in proj]
    row('클로드', '자동 규칙(훅)', '문제' if miss else '정상', f'빠짐: {", ".join(miss)}' if miss else '자동 저장 · 한국어 · 캐시 번호 · index 지킴이 모두 있음')
    master = DEV / 'vibe-study' / 'tools' / 'claude-global' / 'CLAUDE.md'
    same = master.exists() and (CLAUDE / 'CLAUDE.md').read_bytes() == master.read_bytes()
    row('클로드', '전역 CLAUDE.md = 원본', '정상' if same else '확인', '' if same else '다름 — 대화를 두 번 열면 pc-sync 가 맞춘다')
    mem = os.path.realpath(CLAUDE / 'projects' / 'c--galleypark' / 'memory')
    row('클로드', '기억 연결', '정상' if 'vibe-study' in mem else '문제', mem)
    old = [p.name for p in (CLAUDE / 'skill-observations', CLAUDE / 'task-observer-workspace') if p.exists()]
    row('클로드', '옛 기록장 폴더', '확인' if old else '정상', f'남아 있음: {old} — 작업원칙.md 대로 합친 뒤 물어보고 지움' if old else '없음')

    masters = [REPO / '.claude' / 'skills', DEV / 'vibe-study' / 'tools' / 'skills', DEV / 'park-obsidian-save' / '.claude' / 'skills']
    benign = {('obsidian-save', 'obsidian_save.py')}   # 설치 때만 복사되는 파일 (스킬 글에 그렇게 적혀 있음)
    same, bad = 0, []
    for m in masters:
        for s in sorted(p for p in m.iterdir() if p.is_dir()) if m.exists() else []:
            inst = CLAUDE / 'skills' / s.name
            if not inst.exists():
                bad.append(f'{s.name} 설치 안 됨')
                continue
            a = {str(f.relative_to(s)) for f in s.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
            b = {str(f.relative_to(inst)) for f in inst.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
            diff = [f for f in a if f not in b or (s / f).read_bytes() != (inst / f).read_bytes()]
            diff += [f for f in b - a if (s.name, f) not in benign]
            if diff:
                bad.append(f'{s.name} 다름({diff[0]} 등 {len(diff)}개)')
            else:
                same += 1
    row('클로드', '스킬 설치본 = 원본(세 곳)', '확인' if bad else '정상', f'같음 {same}개' + (f' · {"; ".join(bad)}' if bad else ''))


def claude_tools():
    exes = glob.glob(str(HOME / '.vscode' / 'extensions' / 'anthropic.claude-code-*-win32-x64' / 'resources' / 'native-binary' / 'claude.exe'))
    ver = lambda p: tuple(int(x) for x in re.search(r'claude-code-(\d+)\.(\d+)\.(\d+)', p).groups())
    exe = shutil.which('claude') or (max(exes, key=ver) if exes else None)   # 보통 PATH 에 없다 — VS Code 확장 안의 것을 쓴다
    if not exe:
        row('클로드', '연결 도구(MCP)', '확인', 'claude 실행 파일을 못 찾음 — VS Code 확장이 없나?')
        return
    _, out, _ = run([exe, 'mcp', 'list'], timeout=240)
    lines = [l for l in out.splitlines() if ' - ' in l]
    bad = [l.split(': ', 1)[0] for l in lines if not l.rstrip().endswith(' Connected')]   # 표시 글자는 PC 마다 다르다(✔ · √) — 낱말로 본다 (기록장 #81)
    row('클로드', '연결 도구(MCP)', '확인' if bad or not lines else '정상', f'{len(lines) - len(bad)}/{len(lines)} 연결' + (f' · 안 됨: {", ".join(bad)}' if bad else ''))
    script = DEV / 'vibe-study' / 'tools' / 'MCP-설치.ps1'
    if script.exists():
        want = re.findall(r"Add-Mcp '([\w-]+)'", script.read_text(encoding='utf-8-sig'))
        have = {l.split(':')[0].strip() for l in lines}
        miss = [w for w in want if w not in have]
        row('클로드', 'MCP-설치.ps1 목록이 다 있나', '확인' if miss else '정상', f'없음: {", ".join(miss)} (설치 조건이 없는 PC 면 정상)' if miss else f'{len(want)}개 모두')
    _, out, _ = run([exe, 'plugin', 'list'], timeout=120)
    names = re.findall(r'❯ (\S+)', out)
    states = re.findall(r'Status: (.+)', out)
    failed = [n for n, s in zip(names, states) if 'enabled' not in s and 'disabled' not in s]
    plist = DEV / 'vibe-study' / 'tools' / '플러그인-설치.ps1'
    ptext = plist.read_text(encoding='utf-8-sig') if plist.exists() else ''
    off_list = [n for n, s in zip(names, states) if 'enabled' in s and n.split('@')[0] not in ptext]
    row('클로드', '플러그인', '문제' if failed else '정상',
        f'켜짐 {sum("enabled" in s for s in states)} · 꺼짐 {sum("disabled" in s for s in states)}' + (f' · 이상: {failed}' if failed else ''))
    if off_list:
        row('클로드', '플러그인 설치 목록', '확인', f'이 PC 에만 켜져 있고 플러그인-설치.ps1 에 없음: {", ".join(off_list)} — 다른 PC 에는 안 깔림')


# ---------------------------------------------------------------- 3. 파이썬 · 열쇠 · 도구
def python_and_keys():
    mods = ['playwright', 'pytest', 'firebase_admin', 'google.cloud.firestore', 'fitz', 'pandas', 'openpyxl', 'PIL', 'cv2']
    optional = {'cv2': 'python -m pip install opencv-python'}   # 시험 · 도구가 안 쓰고 사진 비교 · QR 읽기에만 — 없으면 '확인' (기록장 #81)
    bad, opt_bad = [], []
    for m in mods:   # 따로 띄워 본다 — 스마트 앱 컨트롤이 막으면 그 부품만 실패한다 (기록장 #76)
        code, _, err = run([sys.executable, '-X', 'utf8', '-c', f'import {m}'], timeout=60)
        if code:
            (opt_bad if m in optional else bad).append(f'{m}({err.strip().splitlines()[-1][:60] if err.strip() else code})')
    detail = '; '.join([f'안 됨: {"; ".join(bad)}'] * bool(bad) + [f'사진 비교용만 없음: {"; ".join(opt_bad)} — 쓸 때 {" · ".join(optional[o.split("(")[0]] for o in opt_bad)}'] * bool(opt_bad))
    row('파이썬', '부품', '문제' if bad else '확인' if opt_bad else '정상', detail or f'{len(mods)}개 모두 불러옴')
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\CI\Policy') as k:
            sac = winreg.QueryValueEx(k, 'VerifiedAndReputablePolicyState')[0]
    except OSError:
        sac = None
    row('파이썬', '스마트 앱 컨트롤', '확인' if sac in (1, 2) else '정상',
        {0: '꺼짐', 1: '켜짐 — 서명 없는 파이썬 부품이 막힐 수 있음', 2: '평가 중', None: '값 없음'}.get(sac, str(sac)))
    keys = {KEYS / 'sije-admin.json': '실제 저장소 도구', KEYS / 'sije-test-admin.json': '서류 시험',
            KEYS / 'sije-calendar.txt': '캘린더 맞추기', HOME / '.config' / 'gws' / 'client_secret.json': 'gws',
            HOME / '.llm-council' / 'gemini-key.txt': '카운슬'}
    miss = [f'{p.name}({use})' for p, use in keys.items() if not p.exists()]
    row('열쇠', 'PC 마다 두는 비밀 파일', '확인' if miss else '정상', f'없음: {", ".join(miss)} — 그 기능만 이 PC 에서 안 됨' if miss else f'{len(keys)}개 모두 있음')
    g = shutil.which('gws')
    if g:
        code, _, err = run([g, 'drive', 'files', 'list', '--params', '{"pageSize": 1}', '--format', 'json'], timeout=60)
        row('열쇠', 'gws 로그인', '정상' if code == 0 else '문제', '드라이브 읽기 성공' if code == 0 else f'실패 — CLAUDE.md gws 절의 로그인 명령 ({err.strip()[:80]})')
    else:
        row('열쇠', 'gws', '확인', '설치 안 됨 — CLAUDE.md gws 절')
    free = shutil.disk_usage('C:\\').free / 2**30
    row('PC', 'C: 남은 공간', '정상' if free > 20 else '확인', f'{free:.0f}GB')


# ---------------------------------------------------------------- 4. 바탕화면 아이콘
def desktop():
    items = ps_json("$d=[Environment]::GetFolderPath('Desktop'); $sh=New-Object -ComObject WScript.Shell; "
                    "Get-ChildItem -Path $d -Recurse -Depth 1 -Include *.lnk,*.url | ForEach-Object { if ($_.Extension -eq '.lnk') { "
                    "$l=$sh.CreateShortcut($_.FullName); [pscustomobject]@{n=$_.FullName.Substring($d.Length); "
                    "ok=[bool]($l.TargetPath -and (Test-Path -LiteralPath $l.TargetPath))} } else { [pscustomobject]@{n=$_.FullName.Substring($d.Length); ok=$true} } }")
    food = [i for i in items if i['n'].startswith('\\푸드벨\\')]
    broken = [i['n'] for i in items if not i['ok']]
    row('바탕화면', '아이콘', '확인' if broken else '정상', f'푸드벨 폴더 {len(food)}개 · 전체 {len(items)}개' + (f' · 대상 없음: {", ".join(broken)}' if broken else ''))


# ---------------------------------------------------------------- 5. 사이트
def site():
    pages = ['', 'index.html', 'sije-quote.html', 'event-quote.html', 'sije-worksheet.html', 'statement.html', 'staff-pay.html',
             'daily-schedule.html', 'today.html', 'sije-list.html', 'sije-sheet.html', 'sije-view.html', 'privacy.html', 'sw.js']
    bad = [f'{p or "/"} {c}' for p in pages if (c := http(SITE + p)[0]) != 200]
    neg = http(SITE + 'no-such-file-zz91.html')[0]
    if neg != 404:
        row('사이트', '주소', '문제', f'측정 실패 — 없는 주소가 {neg} (404 여야 함)')
        return
    row('사이트', f'주소 {len(pages)}개', '문제' if bad else '정상', f'200 아님: {", ".join(bad)}' if bad else '모두 200 (없는 주소 404 대조 통과)')
    for name, url in (('www', 'https://www.foodbell.kr/'), ('푸드벨.kr', 'https://xn--hy1bx1mqsv.kr/')):
        c, loc, _ = http(url)
        row('사이트', f'{name} 넘겨주기', '정상' if c == 308 and loc == SITE else '문제', f'{c} → {loc}')
    files = git(REPO, 'ls-files')[1].splitlines()
    work = [f for f in files if f.endswith(('.py', '.bat', '.ps1', '.md'))][:12] + [f for f in files if f in ('firestore.rules', '.vercelignore', 'CLAUDE.md')]
    leak = [f for f in work if http(SITE + urllib.parse.quote(f))[0] != 404]
    row('사이트', f'작업 파일 {len(work)}개가 바깥에서 막힘', '문제' if leak else '정상', f'열림: {", ".join(leak)}' if leak else '모두 404')

    head = git(REPO, 'status', '-sb')[1].splitlines()[0]
    if 'ahead' in head:
        row('사이트', '서버 = 저장본', '확인', '아직 안 올린 저장이 있어 비교하지 않음')
        return
    pub = [f for f in files if (('/' not in f and f.endswith(('.html', '.webmanifest', '.js'))) or
                                (f.startswith(('css/', 'js/')) and f.endswith(('.css', '.js'))))]
    diff = []
    for f in pub:
        blob = subprocess.run(['git', '-C', str(REPO), 'show', f'HEAD:{f}'], capture_output=True).stdout
        if http(SITE + urllib.parse.quote(f))[2] != blob:
            diff.append(f)
    probe = subprocess.run(['git', '-C', str(REPO), 'show', 'HEAD:index.html'], capture_output=True).stdout + b' '
    if probe == http(SITE + 'index.html')[2]:
        row('사이트', '서버 = 저장본', '문제', '측정 실패 — 일부러 바꾼 대조가 같게 나옴')
        return
    age = time.time() - int(git(REPO, 'log', '-1', '--format=%ct')[1].strip() or 0)
    state = '정상' if not diff else ('확인' if age < 300 else '문제')
    row('사이트', f'서버 = 저장본 (화면 파일 {len(pub)}개)', state,
        '모두 같음' if not diff else f'다름: {", ".join(diff[:5])}' + (' — 방금 올려서 배포 중일 수 있음, 몇 분 뒤 다시' if age < 300 else ''))


# ---------------------------------------------------------------- 6. 사무실 PC 만 — PDF 프로그램 · n8n · 실제 저장소
def office():
    state = Path(os.environ.get('LOCALAPPDATA', '')) / 'foodbell-sije' / 'state-sije-admin.json'
    if not state.exists():
        row('사무실', 'PDF 프로그램', '정상', '이 PC 에서는 안 돎 (사무실 PC 만)')
        return
    mins = (time.time() - state.stat().st_mtime) / 60
    row('사무실', 'PDF 프로그램 살아 있나', '정상' if mins < 10 else '문제', f'마지막 차례 {mins:.0f}분 전 (5분마다)')
    procs = ps_json("Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object CommandLine -like '*office_agent*' | "
                    "ForEach-Object { [pscustomobject]@{p=$_.ProcessId; s=$_.CreationDate.ToString('o')} }")
    if procs:
        start = min(datetime.datetime.fromisoformat(p['s']).timestamp() for p in procs)
        src = (REPO / 'tools' / 'sije_web' / 'office_agent.py').read_text(encoding='utf-8')
        mods = {'office_agent'} | set(re.findall(r'from tools\.sije_web\.(\w+) import', src))
        for m in re.findall(r'from tools\.sije_web import ([\w, ]+)', src):
            mods |= {x.strip() for x in m.split(',')}
        newest = max((REPO / 'tools' / 'sije_web' / f'{m}.py').stat().st_mtime for m in mods if (REPO / 'tools' / 'sije_web' / f'{m}.py').exists())
        old = start < newest
        row('사무실', 'PDF 프로그램이 새 코드인가', '문제' if old else '정상',
            f'켜진 때 {datetime.datetime.fromtimestamp(start):%m-%d %H:%M} · 부르는 파일 {len(mods)}개 중 마지막 고침 {datetime.datetime.fromtimestamp(newest):%m-%d %H:%M}'
            + (' — 예약 작업 "푸드벨 시제 PDF" 를 껐다 켜야 함' if old else ''))
    else:
        row('사무실', 'PDF 프로그램이 새 코드인가', '문제', 'office_agent 가 돌고 있지 않음')
    log = state.parent / 'agent.log'
    errs = [l for l in log.read_text(encoding='utf-8', errors='replace').splitlines()[-500:] if 'ERROR' in l and 'pytest-of-' not in l] if log.exists() else []
    row('사무실', 'agent.log 오류(마지막 500줄)', '확인' if errs else '정상', errs[-1][:120] if errs else '없음')
    for t in ps_json("Get-ScheduledTask | Where-Object { $_.TaskName -like '*푸드벨*' } | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
                     "[pscustomobject]@{n=$_.TaskName; s=[string]$_.State} }"):
        row('사무실', f'예약 작업 {t["n"]}', '정상' if t['s'] == 'Running' else '확인', t['s'])
    n8n = http('http://127.0.0.1:5678/healthz')
    row('사무실', 'n8n', '정상' if n8n[0] == 200 else '확인', 'healthz 200' if n8n[0] == 200 else f'응답 없음 ({n8n[1]}) — 10분마다 스스로 켜짐')
    sys.path.insert(0, str(REPO))
    from tools.sije_web import fsdb, pdf_sync
    from tools.sije_web.office_agent import WORK_ROOT
    today = datetime.date.today()
    bk = [WORK_ROOT / '백업' / f'{d} 시제행사 백업.xlsx' for d in (today, today - datetime.timedelta(days=1))]
    row('사무실', '백업 엑셀', '정상' if any(p.exists() for p in bk) else '문제', next((p.name for p in bk if p.exists()), '오늘 · 어제 것이 없음'))
    db = fsdb.open_db(fsdb.KEY_PROD)
    events = [(d.id, d.to_dict()) for d in db.collection('events').stream()]
    want = {pdf_sync.target_path(WORK_ROOT, e) for _, e in events if e.get('date')}
    have = set((WORK_ROOT / f'{pdf_sync.SEASON}년 PDF (휴대폰용)').rglob('*.pdf'))
    miss, extra = len(want - have), len(have - want)
    row('사무실', 'PDF = 날짜 있는 행사', '정상' if not miss and not extra else '확인',
        f'행사 {len(want)} · PDF {len(have)}' + (f' · 없는 PDF {miss} · 남는 PDF {extra} (방금 고쳤으면 5분 뒤 다시)' if miss or extra else ''))


def rules():
    try:
        from tools.sije_web import fsdb  # noqa: F401 — 불러오면 윈도우 인증서를 합친다(백신이 보안 연결을 검사하는 노트북, 기록장 #81)
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account
    except Exception as e:
        row('저장소 규칙', '실제 · 시험 = 저장소 파일', '확인', f'부품을 못 불러 건너뜀 ({type(e).__name__})')
        return
    repo = subprocess.run(['git', '-C', str(REPO), 'show', 'HEAD:firestore.rules'], capture_output=True).stdout.decode('utf-8')
    norm = lambda t: t.replace('\r\n', '\n').strip()
    for name, key in (('실제', KEYS / 'sije-admin.json'), ('시험', KEYS / 'sije-test-admin.json')):
        if not key.exists():
            row('저장소 규칙', name, '확인', f'열쇠 {key.name} 이 없어 건너뜀')
            continue
        project = json.loads(key.read_text(encoding='utf-8'))['project_id']
        s = AuthorizedSession(service_account.Credentials.from_service_account_file(str(key), scopes=['https://www.googleapis.com/auth/cloud-platform']))
        base = 'https://firebaserules.googleapis.com/v1/'
        rs = s.get(base + s.get(f'{base}projects/{project}/releases/cloud.firestore').json()['rulesetName']).json()
        same = norm(rs['source']['files'][0]['content']) == norm(repo)
        row('저장소 규칙', f'{name} 프로젝트 = 저장소 파일', '정상' if same else ('확인' if name == '시험' else '문제'),
            f'올린 때 {rs.get("createTime", "")[:16]}' + ('' if same else ' — 다름'))


# ---------------------------------------------------------------- 7. 시험 (--tests)
def tests():
    js = sorted(glob.glob(str(REPO / 'tools' / 'sije_web' / 'js-tests' / '*.test.mjs')))
    _, out, err = run(['node', '--test', *js], timeout=300)   # 폴더를 주면 0개 돌고 '실패 1' — 파일을 하나하나 준다
    n = dict(re.findall(r'ℹ (tests|pass|fail) (\d+)', out + err))
    row('시험', 'JS', '정상' if n.get('fail') == '0' and n.get('tests', '0') != '0' else '문제', f'{n.get("pass")}/{n.get("tests")} 통과')
    print('   파이썬 시험 전체 — 15분쯤 걸린다 …', flush=True)
    _, out, _ = run([sys.executable, '-X', 'utf8', '-m', 'pytest', str(REPO / 'tools' / 'sije_web' / 'tests'), '-q', '-p', 'no:cacheprovider'], timeout=3600)
    tail = [l for l in out.splitlines() if re.search(r'passed|failed|^FAILED|^ERROR', l)]
    row('시험', '파이썬', '문제' if any('failed' in l or l.startswith(('FAILED', 'ERROR')) for l in tail) else '정상', ' / '.join(tail[-4:]))


def main():
    ap = argparse.ArgumentParser(description='이 PC 점검 — 읽기만 한다')
    ap.add_argument('--tests', action='store_true', help='시험 전체도 돌린다 (15분쯤)')
    a = ap.parse_args()
    t0 = time.time()
    steps = [pc_and_repos, claude_setup, claude_tools, python_and_keys, desktop, site, office, rules] + ([tests] if a.tests else [])
    for step in steps:
        try:
            step()
        except Exception as e:   # 한 항목이 멈춰도 나머지는 본다
            row('점검', step.__name__, '문제', f'점검 자체가 멈춤 — {type(e).__name__}: {e}')
    look = [r for r in rows if r[0] != '정상']
    print(f'\n=== 끝 ({time.time() - t0:.0f}초) — 정상 {len(rows) - len(look)} · 확인 {sum(r[0] == "확인" for r in look)} · 문제 {sum(r[0] == "문제" for r in look)}')
    for state, group, name, detail in look:
        print(f'{state}  [{group}] {name} — {detail}')
    sys.exit(1 if any(r[0] == '문제' for r in rows) else 0)


if __name__ == '__main__':
    main()
