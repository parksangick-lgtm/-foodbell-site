"""선택자 함정 점검 (기록장 #54 · #93) — 시험 파일의 JS 글 안에서 querySelector(…) · querySelectorAll(…) 이
파이썬에서 넘어온 값(evaluate · wait_for_function 의 arg, f-string · % · .format · + 로 끼운 값)을 받으면 실패한다.

왜: PAGES 의 선택자에는 Playwright 전용 문법(:text-is 등)이 있어 브라우저 querySelector 에서 'is not a valid selector' 로
깨진다. 그 선택자를 쓰는 서류 하나에서만 깨지므로 -k 로 좁혀 돌리면 안 보인다. 규칙으로 적어 둔 뒤에도 모양을 바꿔
다시 생겼다(10-24 도우미 · 10-29 wait_for_function) — 그래서 시험이 잡는다.
글자 그대로 쓴 querySelector('.btn-open') 은 괜찮다(unfold_if_folded). 브라우저 없이 1초 안에 돈다."""
import ast
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS_FIRST = {'evaluate', 'evaluate_handle', 'wait_for_function', 'add_init_script'}   # JS 가 첫 인자
JS_SECOND = {'eval_on_selector', 'eval_on_selector_all'}                             # 첫 인자는 선택자, JS 는 둘째
PY = '\x00'   # 파이썬이 끼워 넣은 값 자리
QS = re.compile(r'querySelector(?:All)?\(')
FN_HEAD = re.compile(r'\s*(?:async\s+)?(?:\(([^)]*)\)\s*=>|([A-Za-z_$][\w$]*)\s*=>|function\s*[\w$]*\s*\(([^)]*)\))')
HOW = "선택자 글은 page.locator(sel) 로 넘긴다 — 예: page.locator(sel).first.evaluate('(e) => …') (기록장 #54 · #93)"


def _js(node, consts, top=True):
    """JS 글로 쓰인 파이썬 식 → 글자 (파이썬이 끼운 값은 PY 자리). 못 읽으면 None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):                                              # f-string
        return ''.join(v.value if isinstance(v, ast.Constant) else PY for v in node.values)
    if isinstance(node, ast.Name):
        return consts.get(node.id, None if top else PY)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):                 # 'a' + sel + 'b'
        left, right = _js(node.left, consts, False), _js(node.right, consts, False)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):                 # '…%s…' % sel
        left = _js(node.left, consts, top)
        return None if left is None else re.sub(r'%(?:\([^)]*\))?[sdr]', PY, left)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'format'
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)):   # '…{}…'.format(sel)
        return re.sub(r'\{\{|\}\}|\{[^{}]*\}', lambda m: {'{{': '{', '}}': '}'}.get(m.group(), PY), node.func.value.value)
    return None if top else PY


def _inside(js, start):
    """js[start] 바로 뒤가 여는 괄호 다음 — 짝이 맞는 닫는 괄호까지의 글 (따옴표 안 괄호는 셈하지 않음)."""
    depth, i, quote = 1, start, None
    while i < len(js):
        c = js[i]
        if quote:
            if c == '\\':
                i += 1
            elif c == quote:
                quote = None
        elif c in '\'"`':
            quote = c
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return js[start:i]
        i += 1
    return js[start:]


def _params(js):
    m = FN_HEAD.match(js)
    return set(re.findall(r'[A-Za-z_$][\w$]*', ''.join(g for g in m.groups() if g))) if m else set()


def find_traps(source, name='<글>'):
    """파이썬 글(시험 파일 하나)에서 함정 줄을 찾는다 → (걸린 것 [(줄, 설명)], 살펴본 querySelector 수)."""
    tree = ast.parse(source)
    consts = {}
    for st in tree.body:                                                             # 맨 위 JS 상수 (OVERFLOW = """…""")
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            v = _js(st.value, {}, True)
            if v is not None:
                consts[st.targets[0].id] = v
    hits, seen = [], 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        at = 0 if node.func.attr in JS_FIRST else 1 if node.func.attr in JS_SECOND else None
        if at is None or len(node.args) <= at:
            continue
        js = _js(node.args[at], consts)
        if js is None:
            continue
        passed = len(node.args) > at + 1 or any(k.arg == 'arg' for k in node.keywords)
        params = _params(js) if passed else set()
        for m in QS.finditer(js):
            seen += 1
            inner = _inside(js, m.end()).strip()
            first = re.match(r'[A-Za-z_$][\w$]*', inner)
            why = None
            if PY in inner:
                why = '파이썬 값을 선택자 글에 끼워 넣음'
            elif first and first.group() in params:
                why = f'파이썬에서 넘긴 인자 {first.group()!r} 를 그대로 받음'
            elif inner.startswith('`'):
                for t in re.finditer(r'\$\{\s*([A-Za-z_$][\w$]*)', inner):
                    if t.group(1) in params and inner[t.start() - 1] not in '"\'=':
                        why = f'파이썬에서 넘긴 인자 {t.group(1)!r} 를 선택자 글에 끼움'
            if why:
                hits.append((f'{name}:{node.lineno}', f'{m.group()}…) 가 {why}'))
    return hits, seen


def test_no_selector_trap_in_test_files():
    files = sorted(HERE.glob('*.py'))
    assert len(files) > 10, f'시험 파일을 못 찾음: {HERE}'
    hits, seen = [], 0
    for p in files:
        h, s = find_traps(p.read_text(encoding='utf-8'), p.name)
        hits += h
        seen += s
    raw = sum(len(QS.findall(p.read_text(encoding='utf-8'))) for p in files)   # 다른 방법(글자 찾기)으로 센 수
    assert raw > 0 and seen > 0, f'살펴본 querySelector {seen}개 / 글자로 센 것 {raw}개 — 0 이면 점검이 고장난 것이다'
    assert hits == [], '\n'.join(f'{w}: {m}' for w, m in hits) + '\n' + HOW


# ---- 양성 대조: 실제로 깨졌던 줄 그대로 (지어낸 줄이 아니다) ----

BROKEN_1024 = '''
def unfold_if_folded(page, selector):
    """일정표의 장례 칸이 접혀 있으면(10-24 검토 반영) 사람이 하듯 '장례 칸 펼치기'를 먼저 누른다. 다른 서류에는 해당 없음."""
    page.evaluate("""(sel) => { const e = document.querySelector(sel); const td = e && e.closest('td.meet.folded');
                                if (td) td.querySelector('.btn-open').click(); }""", selector)
'''   # 저장 기록 9149038 (2026-10-24) — 시제 작업지시서 시험 3개가 'is not a valid selector' 로 깨졌다 (기록장 #54)

BROKEN_1029 = '''
def test_digits_only_phone_gets_dashes_on_leave(pc, repo_url, custom_token, made, kind, file, noun, title, send, label, edit_sel):
    open_list(pc, repo_url, file, custom_token(EMAIL, allowed=True))
    new_doc(pc, made)
    set_text(pc, edit_sel, '담당 01012345678')
    pc.keyboard.press('Tab')
    pc.wait_for_function('sel => document.querySelector(sel).textContent.includes("010-1234-5678")', arg=edit_sel, timeout=3_000)
'''   # 2026-10-29 사무실 대화 기록 — 저장 전에 고쳐 저장 기록에는 없다. 작업지시서 한 장만 깨졌다 (기록장 #93)


def test_finder_catches_the_real_broken_lines():
    for src in (BROKEN_1024, BROKEN_1029):
        hits, seen = find_traps(src)
        assert len(hits) == 1, (hits, src)
    hits, seen = find_traps(BROKEN_1024)
    assert seen == 2   # 같은 JS 의 td.querySelector('.btn-open') 은 글자 그대로라 안 걸린다 (걸린 것은 sel 하나)


def test_finder_catches_python_side_insertion():
    # 파이썬에서 선택자를 끼워 넣는 모양 — 이 저장소에 실제 예는 아직 없어 모양만 지어 시험한다
    shapes = [
        'page.evaluate(f"document.querySelector(\'{sel}\').click()")',
        'page.evaluate("document.querySelector(\'" + sel + "\').click()")',
        'page.evaluate("document.querySelector(\'%s\').click()" % sel)',
        'page.evaluate("document.querySelector(\'{}\').click()".format(sel))',
        'page.evaluate("(s) => document.querySelectorAll(`${s} dd`).length", sel)',
        'page.eval_on_selector("body", "(b, s) => b.querySelector(s)", sel)',
    ]
    for src in shapes:
        hits, _ = find_traps(src)
        assert len(hits) == 1, src


# ---- 음성 대조: 지금 쓰는 줄 (test_doc_pages.py 에서 그대로 읽는다) ----

def _function_source(path, name):
    src = path.read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    raise AssertionError(f'{path.name} 에 {name} 이 없다 — 이름을 바꿨으면 이 시험의 대조 줄도 바꾼다')


def test_finder_passes_literal_selectors():
    doc_pages = HERE / 'test_doc_pages.py'
    for name, examined in (('unfold_if_folded', 1),                    # locator 로 찾고 querySelector('.btn-open') 은 글자 그대로
                           ('test_digits_only_phone_gets_dashes_on_leave', 0),   # 10-29 줄을 locator 로 고친 지금 모양
                           ('wait_view', 0),                           # f-string 이지만 querySelector 가 없다
                           ('pay_fill', 3)):                           # 파이썬 값(n)을 넘기지만 선택자는 JS 안에서 만든다
        hits, seen = find_traps(_function_source(doc_pages, name), name)
        assert hits == [], hits
        assert seen == examined, (name, seen)
