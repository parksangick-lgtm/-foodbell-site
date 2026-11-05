"""직원 화면 today.html 시험 — 시험 프로젝트의 직원 게시판에 가짜 일정을 관리자 열쇠로 넣고, 로그인 없는 휴대폰 창(390px)으로 연다.
날짜는 시험 날 기준으로 계산한다(고정 날짜는 다음 주에 깨진다). 손님 정보는 전부 가짜.
사장님 화면이 고친 것이 열린 직원 화면에 바로 오는지는 test_doc_pages.py 의 test_today_updates_live (사장님 화면 도구가 거기 있다)."""
import datetime
import time
import urllib.parse

import pytest
from firebase_admin import firestore

from tools.sije_web import share_link
from test_offline import wait_controlled

WEEK = '월화수목금토일'
CHANGED = '링크가 바뀌었습니다. 단톡방 공지의 새 링크를 눌러 주세요.'
EMPTY = '올라온 일정이 없습니다. 단톡방의 일정표 사진을 확인해 주세요.'
FIELDS = ('staff', 'car', 'leave', 'time', 'place', 'tel', 'work', 'amt', 'lead', 'leadTel', 'guideTel', 'hall', 'depart', 'cremate', 'memo')


def day(n):
    return datetime.date.today() + datetime.timedelta(days=n)


def md(d):
    """'10월 22일 (목)' — 날짜 버튼의 날짜 부분."""
    return f'{d.month}월 {d.day}일 ({WEEK[d.weekday()]})'


def naver(place):
    """휴대폰용 네이버 지도 검색 — map.naver.com/p/search 는 휴대폰 카톡 안에서 '앱 설치' 화면만 나와 장소가 사라졌다 (10-21 저녁)."""
    return 'https://m.map.naver.com/search2/search.naver?query=' + urllib.parse.quote(place, safe='')


def row(no=1, **kw):
    return {'no': no, **{f: '' for f in FIELDS}, **kw}


def entry(d, rows, **kw):
    """게시판 한 장 — 사장님 화면(daily-schedule.html 의 share())이 올리는 꼴."""
    return {'date': d.isoformat(), 'label': f'{d.year}년 {md(d)}', 'lunar': '음력 9월 11일', 'order': '', 'memo': '',
            'rows': rows, **kw}


@pytest.fixture
def key(test_db):
    """시험 프로젝트의 게시판 암호 — 없으면 만들고, 시험마다 비우고 시작한다."""
    k = share_link.current_key(test_db)
    if not k or not test_db.collection('share').document(k).get().exists:
        k = share_link.new_key(test_db)
    test_db.collection('share').document(k).set({'entries': {}})
    return k


def put(test_db, key, **entries):
    test_db.collection('share').document(key).set({'entries': entries})


@pytest.fixture
def ctx(browser):
    c = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    yield c
    c.close()


@pytest.fixture
def phone(ctx):
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    yield pg
    assert errors == [], errors


def open_today(page, repo_url, tail):
    page.goto('about:blank')
    page.goto(f'{repo_url}today.html{tail}')


def cards(page):
    page.locator('article.card').first.wait_for(timeout=20_000)
    return page.locator('article.card')


def hrefs(page, sel):
    return page.eval_on_selector_all(sel, 'els => els.map((a) => a.getAttribute("href"))')


def test_today_cards_match_board(phone, repo_url, test_db, key):
    """카드 = 사진의 줄(번호 그대로), 전화번호마다 [전화](메모 속 숫자 · 날짜는 아님), 장소에 [지도], 빈 칸은 이름표까지 숨김."""
    put(test_db, key, docA=entry(day(0), [
        row(1, staff='가짜직원', car='1톤', time='06:30', place='가짜추모공원 제례실', tel='010-0000-1234, 010-0000-1235',
            work='가짜동 상차림', amt='60명 × 15,000원 = 900,000원', lead='가짜팀장', leadTel='010-0000-2000',
            guideTel='02-000-4000', hall='가짜장례식장', depart='05:30', cremate='07:20', memo='10/22 연기\n350,000 1234'),
        row(3, work='가짜동 제사상'),
    ], order='가짜1 · 가짜2', memo='가짜 전달 메모'))
    open_today(phone, repo_url, f'#{key}')
    c = cards(phone)
    assert [t.strip() for t in phone.locator('article.card .no').all_inner_texts()] == ['1번', '3번']
    assert hrefs(phone, 'a.btn-call') == ['tel:01000001234', 'tel:01000001235', 'tel:01000002000', 'tel:020004000']
    assert hrefs(phone, 'a.btn-map') == [naver('가짜추모공원 제례실')]
    first = c.nth(0).inner_text()
    for s in ('06:30', '가짜직원', '1톤', '가짜추모공원 제례실', '가짜동 상차림', '60명 × 15,000원 = 900,000원',
              '가짜팀장', '가짜장례식장', '발인 05:30', '화장 07:20'):
        assert s in first, s
    assert c.nth(0).locator('.memo').inner_text() == '10/22 연기\n350,000 1234'
    third = c.nth(1).inner_text()
    assert '가짜동 제사상' in third
    for s in ('연락처', '팀장', '안내', '지도', '전화', '발인', '메모'):
        assert s not in third, s
    top = phone.locator('#sheet').inner_text()
    assert '가짜1 · 가짜2' in top and '가짜 전달 메모' in top and '음력 9월 11일' in top


def test_today_day_buttons(phone, repo_url, test_db, key):
    """오늘 이후 일정만 날짜 순 버튼 — 처음은 오늘 것(오전), 오늘 것이 없으면 가장 가까운 날."""
    put(test_db, key, y=entry(day(-1), [row(work='가짜어제')]), t=entry(day(0), [row(work='가짜오늘')]),
        m=entry(day(1), [row(work='가짜내일')]), a=entry(day(2), [row(work='가짜모레')]))
    phone.clock.set_fixed_time(datetime.datetime.combine(day(0), datetime.time(10, 0)))   # 저녁엔 내일 것이 먼저라 오전으로
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    assert [t.strip() for t in phone.locator('button.day-btn').all_inner_texts()] == \
        [f'오늘 {md(day(0))}', f'내일 {md(day(1))}', md(day(2))]
    assert '가짜오늘' in phone.locator('#cards').inner_text()
    phone.locator('button.day-btn').nth(1).click()
    phone.locator('#cards', has_text='가짜내일').wait_for(timeout=5_000)
    assert '가짜오늘' not in phone.locator('#cards').inner_text()
    put(test_db, key, m=entry(day(1), [row(work='가짜내일')]), a=entry(day(2), [row(work='가짜모레')]))
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜내일').wait_for(timeout=20_000)


def test_today_evening_shows_tomorrow_first(phone, repo_url, test_db, key):
    """오후 6시부터는 내일 일정이 먼저 — 사장님이 저녁에 내일 일정 사진을 보낸다 (사장님 10-23).
    내일 것이 없으면 그대로 오늘 것, 오후 6시 전에는 오늘 것."""
    put(test_db, key, t=entry(day(0), [row(work='가짜오늘')]), m=entry(day(1), [row(work='가짜내일')]))
    phone.clock.set_fixed_time(datetime.datetime.combine(day(0), datetime.time(18, 0)))
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜내일').wait_for(timeout=20_000)
    assert phone.locator('button.day-btn[aria-pressed="true"]').inner_text().strip() == f'내일 {md(day(1))}'
    phone.locator('button.day-btn').first.click()                       # 오늘 것은 '오늘' 버튼으로
    phone.locator('#cards', has_text='가짜오늘').wait_for(timeout=5_000)
    phone.clock.set_fixed_time(datetime.datetime.combine(day(0), datetime.time(17, 59)))
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜오늘').wait_for(timeout=20_000)
    put(test_db, key, t=entry(day(0), [row(work='가짜오늘')]), a=entry(day(2), [row(work='가짜모레')]))
    phone.clock.set_fixed_time(datetime.datetime.combine(day(0), datetime.time(19, 0)))
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜오늘').wait_for(timeout=20_000)   # 내일 것이 없으면 오늘 것 (모레가 아니라)


def test_today_hides_empty_and_prefers_latest(phone, repo_url, test_db, key):
    """일이 없는 일정표는 버튼도 안 나오고, 같은 날 일정표가 여럿이면 가장 최근에 고친 것을 먼저 보여 준다
    (10-21 저녁 실제: 같은 날 빈 일정표가 먼저 골라져 [전화] · [지도]가 안 보였다)."""
    t1 = datetime.datetime(2026, 10, 21, 10, 0, tzinfo=datetime.timezone.utc)
    t2 = t1 + datetime.timedelta(minutes=30)
    # 이름 차례(a → b → c)로는 빈 것 · 예전 것이 앞 — 고치기 전 화면은 이 차례로 골랐다
    put(test_db, key, aEmpty=entry(day(1), [], at=t2),
        bOld=entry(day(1), [row(1, work='가짜예전것', tel='010-0000-1111')], at=t1),
        cNew=entry(day(1), [row(1, work='가짜최근것', tel='010-0000-2222')], at=t2))
    open_today(phone, repo_url, f'#{key}')
    cards_or_status = phone.locator('#cards')
    phone.locator('button.day-btn').first.wait_for(timeout=20_000)
    phone.wait_for_timeout(500)
    assert '가짜예전것' not in cards_or_status.inner_text()                # 처음부터 최근 것 (예전 것이 먼저 나오면 안 된다)
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜최근것').wait_for(timeout=20_000)
    assert phone.locator('button.day-btn').count() == 2                  # 빈 일정표는 버튼이 없다
    assert hrefs(phone, 'a.btn-call') == ['tel:01000002222']
    phone.locator('button.day-btn').nth(1).click()
    phone.locator('#cards', has_text='가짜예전것').wait_for(timeout=5_000)


def test_today_bad_or_old_link(phone, repo_url, test_db, key):
    for tail in ('', '#', '#' + 'x' * 32):
        open_today(phone, repo_url, tail)
        phone.locator('#status', has_text=CHANGED).wait_for(timeout=20_000)
        assert phone.locator('article.card').count() == 0, tail
    new = share_link.new_key(test_db)                                   # 링크를 바꾸면 옛 링크는
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#status', has_text=CHANGED).wait_for(timeout=20_000)
    open_today(phone, repo_url, f'#{new}')                              # 새 링크는 열린다 — 일정이 없을 뿐 (대조)
    phone.locator('#status', has_text=EMPTY).wait_for(timeout=20_000)


def test_today_odd_characters(phone, repo_url, test_db, key):
    """장소의 # & % - 는 지도 주소를 안 깨고, 메모의 <b> 는 글자 그대로 보인다(굵은 글씨가 되지 않는다)."""
    place = '가짜동 #3 & 5%-1'
    put(test_db, key, docA=entry(day(0), [row(1, place=place, memo='<b>굵게</b>')]))
    open_today(phone, repo_url, f'#{key}')
    c = cards(phone)
    assert hrefs(phone, 'a.btn-map') == [naver(place)]
    assert place in c.nth(0).inner_text()
    assert c.nth(0).locator('.memo').inner_text() == '<b>굵게</b>'
    assert phone.locator('article.card .memo b').count() == 0


def test_today_fits_phone(phone, repo_url, test_db, key):
    long = '가짜동가짜리산00번지가짜공원묘지가짜관리사무소옆주차장'
    put(test_db, key, docA=entry(day(0), [row(1, place=long, work='가짜씨종중시사상차림' * 3, memo=long * 2,
                                              tel='010-0000-0000, 010-0000-0001', lead='가짜팀장', leadTel='010-0000-0002')]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    assert phone.evaluate('document.documentElement.clientWidth') == 390
    over = phone.evaluate("""() => [...document.querySelectorAll('body *')]
        .filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 0.5)
        .map((e) => e.tagName + '.' + e.className)""")
    assert over == [], over


def test_today_offline_shows_last(ctx, phone, repo_url, test_db, key):
    """한 번 연 화면은 신호가 없어도 지난 카드를 보여 주고, 연결 안 됨을 알린다."""
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜동 산속 상차림')]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    wait_controlled(phone)
    phone.locator('#cards', has_text='가짜동 산속 상차림').wait_for(timeout=20_000)
    assert phone.locator('#offline').is_hidden()
    ctx.set_offline(True)
    open_today(phone, repo_url, f'#{key}')
    phone.locator('#cards', has_text='가짜동 산속 상차림').wait_for(timeout=20_000)
    phone.locator('#offline', has_text='연결 안 됨 — 마지막으로 받은 내용입니다').wait_for(timeout=10_000)


# ---------- 10-24 검토 반영 (설계 docs/superpowers/specs/2026-10-24-daily-schedule-review-fixes-design.md) ----------

def test_today_leave_line_and_map_link(phone, repo_url, test_db, key):
    """출발 줄은 머리 다음에, [지도]는 늘 장소 글자 검색 — 옛 게시판 줄에 지도 링크(map)가 남아 있어도 쓰지 않는다(칸은 10-30 뺌)."""
    put(test_db, key, docA=entry(day(0), [
        row(1, time='06:30', place='가짜추모공원', leave='05:30 가게', work='가짜 상차림'),
        dict(row(2, place='가짜공원', work='둘째'), map='https://naver.me/abc'),   # 10-30 전에 올라간 줄
        row(3, place='가짜납골당', work='셋째')]))
    open_today(phone, repo_url, f'#{key}')
    c = cards(phone)
    lines = [l.strip() for l in c.nth(0).locator('p.line').all_inner_texts()]
    assert lines[0].startswith('출발') and '05:30 가게' in lines[0]
    assert hrefs(phone, 'a.btn-map') == [naver('가짜추모공원'), naver('가짜공원'), naver('가짜납골당')]
    assert '출발' not in c.nth(1).inner_text()


def test_today_marks_postponed_and_cancelled(phone, repo_url, test_db, key):
    """사장님이 연기 · 취소로 표시한 일은 카드 머리 맨 앞에 그 글자 — 표시가 없거나 칸이 없는 옛 게시판 줄에는 없다 (사장님 10-24 저녁)."""
    old = row(4, work='옛 줄')
    old.pop('state', None)                                     # state 칸이 생기기 전에 올라간 줄
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜 시제', state=''), row(2, work='가짜 평토상', state='연기'),
                                          row(3, work='가짜 제사', state='취소'), old]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    states = phone.eval_on_selector_all('article.card', "cs => cs.map((c) => c.querySelector('.head .state')?.textContent || '')")
    assert states == ['', '연기', '취소', '']


def test_today_remembers_key_for_home_icon(phone, repo_url, test_db, key):
    """링크(#암호)로 한 번 열면 같은 브라우저에서 # 없이 열어도(홈 화면 아이콘) 일정이 보인다."""
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜 상차림')]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    open_today(phone, repo_url, '')
    assert cards(phone).count() == 1
    assert phone.evaluate("localStorage.getItem('foodbell-today-key')") == key


def test_today_no_hash_without_saved_key(phone, repo_url, test_db, key):
    """# 없이 열었는데 그 브라우저에 기억된 암호가 없으면(처음 · 저장소 지워짐) '링크가 바뀌었습니다' — 새 문맥이라 아무것도 없다."""
    open_today(phone, repo_url, '')
    phone.locator('#status', has_text=CHANGED).wait_for(timeout=10_000)


def test_today_has_manifest_icons_and_install_guide(phone, repo_url, test_db, key):
    """앱 정보 파일 '푸드벨 일정' + 아이콘이 전부 열리고, 맨 아래 '홈 화면에 아이콘으로 두기' 안내가 있다(카톡 → 다른 브라우저로 열기)."""
    put(test_db, key, docA=entry(day(0), [row(1, work='가짜 상차림')]))
    open_today(phone, repo_url, f'#{key}')
    cards(phone)
    assert phone.get_attribute('link[rel="manifest"]', 'href') == 'manifest-today.webmanifest'
    m = phone.request.get(f'{repo_url}manifest-today.webmanifest')
    assert m.status == 200 and m.json()['name'] == '푸드벨 일정'
    for icon in m.json()['icons']:
        assert phone.request.get(f'{repo_url}{icon["src"]}').status == 200, icon
    guide = phone.locator('#install')
    assert guide.is_visible() and '홈 화면' in guide.inner_text()
    guide.locator('summary').click()
    assert '다른 브라우저로 열기' in guide.inner_text()


# ---------- 11-05 직원 확인 칸 (설계 docs/superpowers/specs/2026-11-04-staff-confirm-design.md 3-3 · 5절) ----------

ASK = '이 일정표를 확인하셨으면 본인 이름을 눌러 주세요'
NAMES = ['가짜하나', '가짜둘']
PAST = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)   # 사장님이 마지막으로 고친 때 — 어떤 확인보다 앞


@pytest.fixture
def marks(test_db, key):
    """그 게시판의 확인 기록 묶음(share/{암호}/marks) — 시험 앞뒤로 비운다. key 가 게시판을 덮어써도 이 묶음은 안 지워진다."""
    col = test_db.collection('share').document(key).collection('marks')

    def clear():
        for d in col.list_documents():
            d.delete()
    clear()
    yield col
    clear()


def named(d=None, names=NAMES, at=PAST, **kw):
    """이름 목록(names)이 있는 게시판 한 장 — 사장님 화면이 11-05 부터 올리는 꼴."""
    return entry(d or day(0), [row(1, staff=' · '.join(names), work='가짜 상차림')], names=names, at=at, **kw)


def confirm_box(page):
    box = page.locator('#confirm')
    box.wait_for(state='visible', timeout=20_000)
    return box


def box_buttons(page):
    return [t.strip() for t in page.locator('#confirm button').all_inner_texts()]


def name_button(box, name):
    return box.get_by_role('button', name=name, exact=True)


def wait_mark(marks, sid, name, timeout=30):
    """관리자 열쇠로 그 기록이 생길 때까지 기다려 내용을 돌려준다."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        snap = marks.document(f'{sid}~{name}').get()
        if snap.exists:
            return snap.to_dict()
        time.sleep(0.5)
    raise AssertionError(f'확인 기록이 안 생김: {sid}~{name}')


def test_today_confirm_names_then_mark(phone, repo_url, test_db, key, marks):
    """이름 단추 = 그 일정표 담당(names) 차례대로 → 누르면 기록(sid · name · 서버 시각)이 생기고 '확인함 · HH:MM' + 다른 이름.
    이름은 이 브라우저에 기억 — 다시 열어도 확인함, 기록이 없으면 기억한 이름 단추 하나, '다른 이름' 이면 이름 단추들."""
    put(test_db, key, docA=named())
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜둘').wait_for(timeout=20_000)
    assert ASK in box.inner_text()
    assert box_buttons(phone) == NAMES
    name_button(box, '가짜둘').click()
    box.locator('.cf-done').wait_for(timeout=20_000)
    m = wait_mark(marks, 'docA', '가짜둘')
    assert set(m) == {'sid', 'name', 'at'} and m['sid'] == 'docA' and m['name'] == '가짜둘'
    hhmm = phone.evaluate('(t) => new Date(t).toTimeString().slice(0, 5)', m['at'].timestamp() * 1000)
    assert box.locator('.cf-done').inner_text().strip() == f'확인함 · {hhmm}'
    assert box.locator('.cf-done svg').count() == 1 and '✓' not in box.inner_text()   # 특수문자 대신 선 아이콘
    assert box_buttons(phone) == ['다른 이름']
    assert phone.evaluate("localStorage.getItem('foodbell-today-name')") == '가짜둘'
    open_today(phone, repo_url, f'#{key}')
    confirm_box(phone).locator('.cf-done').wait_for(timeout=20_000)
    marks.document('docA~가짜둘').delete()                              # 기록이 없으면(아직 안 봄) 기억한 이름 단추 하나
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜둘 님 — 확인').wait_for(timeout=20_000)
    assert box_buttons(phone) == ['가짜둘 님 — 확인', '다른 이름']
    name_button(box, '다른 이름').click()
    assert box_buttons(phone) == NAMES
    assert ASK in box.inner_text()


def test_today_confirm_again_after_owner_edit(phone, repo_url, test_db, key, marks):
    """확인한 뒤 사장님이 고치면(게시판 at = 서버 시각, 기록보다 나중) 열어 둔 화면에 '일정이 바뀌었습니다 — [다시 확인]', 누르면 다시 확인함."""
    put(test_db, key, docA=named())
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜하나').click()
    box.locator('.cf-done').wait_for(timeout=20_000)
    first = wait_mark(marks, 'docA', '가짜하나')['at']
    put(test_db, key, docA=named(at=firestore.SERVER_TIMESTAMP))        # 사장님 화면이 고쳐 올린 것처럼
    edited = test_db.collection('share').document(key).get().to_dict()['entries']['docA']['at']
    assert edited > first
    name_button(box, '다시 확인').wait_for(timeout=20_000)
    assert '일정이 바뀌었습니다 —' in box.inner_text() and box.locator('.cf-done').count() == 0
    name_button(box, '다시 확인').click()
    box.locator('.cf-done').wait_for(timeout=20_000)
    assert marks.document('docA~가짜하나').get().to_dict()['at'] > edited


def test_today_confirm_follows_day_and_hides_without_names(phone, repo_url, test_db, key, marks):
    """날짜 단추로 일정표를 바꾸면 확인 칸도 그 일정표 것 — names 가 없는 옛 게시판 · 담당이 빈 일정표는 칸을 숨긴다.
    (내일 것은 저녁에 먼저 골라지므로 오늘 · 모레 · 글피 · 그글피로)"""
    old = entry(day(2), [row(1, work='가짜모레')], at=PAST)             # names 가 생기기 전에 올라간 게시판
    put(test_db, key, t=named(), a=old, b=named(day(3), names=[]), c=named(day(4), names=['가짜하나']))
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜하나').click()
    box.locator('.cf-done').wait_for(timeout=20_000)
    days = phone.locator('button.day-btn')
    days.nth(1).click()
    phone.locator('#cards', has_text='가짜모레').wait_for(timeout=5_000)
    assert phone.locator('#confirm').is_hidden()
    days.nth(2).click()
    phone.locator('#day-label', has_text=md(day(3))).wait_for(timeout=5_000)
    assert phone.locator('#confirm').is_hidden()
    days.nth(3).click()
    name_button(confirm_box(phone), '가짜하나 님 — 확인').wait_for(timeout=5_000)
    days.nth(0).click()
    confirm_box(phone).locator('.cf-done').wait_for(timeout=5_000)


def test_today_confirm_offline_then_online(ctx, phone, repo_url, test_db, key, marks):
    """끊긴 채 누르면 2초까지는 조용하다가 '연결되면 올라갑니다' — 기록은 기기에 있다가 연결되면 저절로 올라가 '확인함'."""
    put(test_db, key, docA=named())
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜하나').wait_for(timeout=20_000)
    ctx.set_offline(True)
    try:
        start = time.monotonic()
        name_button(box, '가짜하나').click()
        assert '연결되면 올라갑니다' not in box.inner_text()
        box.locator('.cf-wait', has_text='연결되면 올라갑니다').wait_for(timeout=10_000)
        assert time.monotonic() - start >= 1.8
        assert not marks.document('docA~가짜하나').get().exists
    finally:
        ctx.set_offline(False)
    box.locator('.cf-done').wait_for(timeout=60_000)
    assert wait_mark(marks, 'docA', '가짜하나')['name'] == '가짜하나'


def test_today_confirm_refused_says_why_once(ctx, phone, repo_url, test_db, key, marks):
    """끊긴 사이 사장님이 담당을 바꿔 그 이름이 목록에서 빠지면 규칙이 거절 — '확인을 올리지 못했습니다 (이유)' 한 줄, 기록은 없다."""
    put(test_db, key, docA=named())
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    name_button(box, '가짜하나').wait_for(timeout=20_000)
    ctx.set_offline(True)
    try:
        name_button(box, '가짜하나').click()
        put(test_db, key, docA=named(names=['가짜둘']))
    finally:
        ctx.set_offline(False)
    box.locator('.cf-err').wait_for(timeout=60_000)
    name_button(box, '가짜둘').wait_for(timeout=20_000)                 # 바뀐 담당의 이름 단추
    assert box.locator('.cf-err').all_inner_texts() == ['확인을 올리지 못했습니다 (permission-denied)']
    assert not marks.document('docA~가짜하나').get().exists


MEASURE = """() => {
  const W = document.documentElement.clientWidth;
  const box = document.getElementById('confirm');
  const texts = [...box.querySelectorAll('*')].filter((e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()));
  return {
    width: W,
    over: [...document.querySelectorAll('body *')].filter((e) => e.getBoundingClientRect().right > W + 0.5).map((e) => e.tagName),
    buttons: [...box.querySelectorAll('button')].map((b) => b.getBoundingClientRect().height),
    fonts: texts.map((e) => parseFloat(getComputedStyle(e).fontSize)),
    weights: [...new Set(texts.map((e) => getComputedStyle(e).fontWeight))],
  };
}"""


def test_today_confirm_fits_phone(phone, repo_url, test_db, key, marks):
    """확인 칸 네 모양(이름 단추들 · 확인함 · 다시 확인 · 기억한 이름) 모두 — 390px 넘침 0, 단추 44px 이상, 글자 14px 이상, 굵기 400 · 600 · 700 만."""
    names = ['가짜하나', '가짜둘', '가짜셋', '가짜넷', '가짜다섯', '가짜여섯째가짜이름이아주길어서한줄을넘는경우가짜가짜']
    put(test_db, key, docA=named(names=names))
    open_today(phone, repo_url, f'#{key}')
    box = confirm_box(phone)
    seen = {}
    name_button(box, '가짜하나').wait_for(timeout=20_000)
    seen['이름 단추'] = phone.evaluate(MEASURE)
    name_button(box, '가짜하나').click()
    box.locator('.cf-done').wait_for(timeout=20_000)
    seen['확인함'] = phone.evaluate(MEASURE)
    put(test_db, key, docA=named(names=names, at=firestore.SERVER_TIMESTAMP))
    name_button(box, '다시 확인').wait_for(timeout=20_000)
    seen['다시 확인'] = phone.evaluate(MEASURE)
    marks.document('docA~가짜하나').delete()
    open_today(phone, repo_url, f'#{key}')
    name_button(confirm_box(phone), '가짜하나 님 — 확인').wait_for(timeout=20_000)
    seen['기억한 이름'] = phone.evaluate(MEASURE)
    for state, m in seen.items():
        print(state, '폭', m['width'], '넘침', len(m['over']), '단추 최소', min(m['buttons']), '글자 최소', min(m['fonts']),
              '굵기', m['weights'])
        assert m['width'] == 390, state
        assert m['over'] == [], (state, m['over'])
        assert m['buttons'] and min(m['buttons']) >= 44, (state, m['buttons'])
        assert min(m['fonts']) >= 14, (state, m['fonts'])
        assert set(m['weights']) <= {'400', '600', '700'}, (state, m['weights'])
