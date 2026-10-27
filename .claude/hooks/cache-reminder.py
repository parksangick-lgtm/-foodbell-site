"""캐시 번호 알림 (PostToolUse) — cache-reminder.sh 가 부른다.
css/js 를 고쳤는데, 그 파일을 ?v= 로 부르는 곳(맨 위 폴더의 html · js/ 의 js)의 번호를 아직 안 올렸으면 클로드에게 알린다.
기준은 마지막 저장본(HEAD) — 이미 올렸으면 조용하다. ?v= 로 부르는 곳이 없는 파일(다른 js 가 번호 없이 import)은 올릴 곳이 없으니 조용하다.
2026-10-28: 전에는 'css·js 아무거나 바뀜 = index.html 올려라' 로만 봐서, 다른 화면이 부르는 파일에도 헛알림이 떴다 (기록장 #24)."""
import json
import posixpath
import re
import subprocess
import sys


def git(*args):
    return subprocess.run(['git', '-c', 'core.quotepath=false', *args], capture_output=True).stdout.decode('utf-8', 'replace')


def points_to(text, ref, target):
    """ref 파일의 글(text)에 target 을 ?v= 로 부르는 줄이 있나 — 경로는 ref 가 있는 폴더 기준으로 풀어 본다."""
    pat = re.compile(r'([\w./-]*' + re.escape(posixpath.basename(target)) + r')\?v=\d+')
    return any(posixpath.normpath(posixpath.join(posixpath.dirname(ref), m.group(1))) == target for m in pat.finditer(text))


changed = [f for f in git('diff', '--name-only', 'HEAD', '--', 'css', 'js').splitlines() if f]
referrers = [f for f in git('ls-files').splitlines()
             if (f.endswith('.html') and '/' not in f) or (f.startswith('js/') and f.endswith('.js'))]
need = {}
for f in changed:
    for ref in referrers:
        try:
            with open(ref, encoding='utf-8') as fh:
                text = fh.read()
        except OSError:
            continue
        if not points_to(text, ref, f):
            continue
        added = '\n'.join(l for l in git('diff', 'HEAD', '--', ref).splitlines() if l.startswith('+') and not l.startswith('+++'))
        if not points_to(added, ref, f):
            need.setdefault(ref, []).append(f)

if need:
    where = ' · '.join(f"{ref} ({', '.join(fs)})" for ref, fs in need.items())
    how = ('index.html 은 python 캐시버전올리기.py 로, 다른 곳은 그 줄의 ?v= 를 손으로 한 칸' if 'index.html' in need
           else '그 줄의 ?v= 를 손으로 한 칸')
    msg = f'[캐시 번호] 고친 파일을 ?v= 로 부르는 곳의 번호를 아직 안 올렸습니다: {where}. {how} 올리세요 — css·js 를 다 고친 뒤, 이 답을 끝내기 전에 한 번만.'
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': msg}}))
