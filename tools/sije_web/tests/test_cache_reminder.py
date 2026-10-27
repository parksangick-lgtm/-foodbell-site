"""캐시 번호 알림(.claude/hooks/cache-reminder.sh, 2026-10-08 · 10-28 고침) 시험 — 이 저장소의 시험이 모두 여기 있어 같이 둔다.
가짜 저장소를 만들어 css/js 를 고친 뒤 알림을 돌려 본다. 기록장 #24 의 실제 두 경우가 기준이다:
sheet-render.js 는 sije-print.html 이 ?v= 로 부르니 알려야 하고, handoff.js 는 ?v= 로 부르는 화면이 없으니 조용해야 한다."""
import json
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / '.claude' / 'hooks'

FILES = {
    'index.html': '<link href="css/style.css?v=1"><script src="js/main.js?v=1"></script>',
    'sije-print.html': "<script type=module>import { a } from './js/sije/sheet-render.js?v=3';</script>",
    'list.html': '<script type="module" src="js/docs/doc-page.js?v=2"></script>',
    'css/style.css': 'body{}',
    'js/main.js': '1',
    'js/sije/sheet-render.js': 'export const a = 1;',
    'js/docs/doc-page.js': "import { h } from './handoff.js';",
    'js/docs/handoff.js': 'export const h = 1;',
    'js/docs/order-text.js': "import { n } from './amount.js?v=1';",
    'js/docs/amount.js': 'export const n = 1;',
}


def git(root, *args):
    subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


def make_repo(tmp_path):
    root = tmp_path / 'repo'
    for name, text in FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding='utf-8')
    shutil.copytree(HOOKS, root / '.claude' / 'hooks')
    git(root, 'init', '-q')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
    return root


def touch(root, name, text='// 고침'):
    p = root / name
    p.write_text(p.read_text(encoding='utf-8') + '\n' + text, encoding='utf-8')


def bump(root, name, old, new):
    p = root / name
    p.write_text(p.read_text(encoding='utf-8').replace(old, new), encoding='utf-8')


def run_hook(root):
    out = subprocess.run(['bash', str(root / '.claude' / 'hooks' / 'cache-reminder.sh')], capture_output=True,
                         env={**os.environ, 'CLAUDE_PROJECT_DIR': str(root)}, timeout=30)
    text = out.stdout.decode('utf-8').strip()
    return json.loads(text)['hookSpecificOutput']['additionalContext'] if text else ''


def test_silent_when_nothing_changed(tmp_path):
    assert run_hook(make_repo(tmp_path)) == ''


def test_module_only_some_page_numbers_warns_that_page(tmp_path):
    """#24 양성: sheet-render.js 를 고치면 그것을 ?v= 로 부르는 sije-print.html 을 알린다 — index.html 이 아니다."""
    root = make_repo(tmp_path)
    touch(root, 'js/sije/sheet-render.js')
    msg = run_hook(root)
    assert 'sije-print.html' in msg and 'index.html' not in msg, msg
    bump(root, 'sije-print.html', 'sheet-render.js?v=3', 'sheet-render.js?v=4')
    assert run_hook(root) == ''                                  # 올렸으면 조용하다


def test_import_without_number_stays_silent(tmp_path):
    """#24 음성: handoff.js 는 doc-page.js 가 번호 없이 부른다 — 올릴 곳이 없으니 알리지 않는다."""
    root = make_repo(tmp_path)
    touch(root, 'js/docs/handoff.js')
    assert run_hook(root) == ''


def test_js_that_numbers_another_js_is_named(tmp_path):
    """js 가 다른 js 를 ?v= 로 부르면(order-text.js → ./amount.js?v=1) 그 js 를 알린다."""
    root = make_repo(tmp_path)
    touch(root, 'js/docs/amount.js')
    msg = run_hook(root)
    assert 'js/docs/order-text.js' in msg, msg


def test_site_style_still_points_to_script(tmp_path):
    """style.css · main.js 는 예전처럼 index.html 과 캐시버전올리기.py 를 알린다."""
    root = make_repo(tmp_path)
    touch(root, 'css/style.css', '/* 고침 */')
    msg = run_hook(root)
    assert 'index.html' in msg and '캐시버전올리기.py' in msg, msg
    bump(root, 'index.html', 'style.css?v=1', 'style.css?v=2')
    assert run_hook(root) == ''
