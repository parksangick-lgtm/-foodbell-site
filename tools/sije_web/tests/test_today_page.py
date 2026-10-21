"""직원 화면 today.html 시험 — 시험 프로젝트의 직원 게시판에 가짜 일정을 관리자 열쇠로 넣고, 로그인 없는 휴대폰 창(390px)으로 연다.
날짜는 시험 날 기준으로 계산한다(고정 날짜는 다음 주에 깨진다). 손님 정보는 전부 가짜.
사장님 화면이 고친 것이 열린 직원 화면에 바로 오는지는 test_doc_pages.py 의 test_today_updates_live (사장님 화면 도구가 거기 있다)."""
import datetime
import urllib.parse

import pytest

from tools.sije_web import share_link
from test_offline import wait_controlled

WEEK = '월화수목금토일'
CHANGED = '링크가 바뀌었습니다. 단톡방 공지의 새 링크를 눌러 주세요.'
EMPTY = '올라온 일정이 없습니다. 단톡방의 일정표 사진을 확인해 주세요.'
FIELDS = ('staff', 'car', 'time', 'place', 'tel', 'work', 'amt', 'lead', 'leadTel', 'guideTel', 'hall', 'depart', 'cremate', 'memo')


def day(n):
    return datetime.date.today() + datetime.timedelta(days=n)


def md(d):
    """'10월 22일 (목)' — 날짜 버튼의 날짜 부분."""
    return f'{d.month}월 {d.day}일 ({WEEK[d.weekday()]})'


def naver(place):
    return 'https://map.naver.com/p/search/' + urllib.parse.quote(place, safe='')


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
    """오늘 이후 일정만 날짜 순 버튼 — 처음은 오늘 것, 오늘 것이 없으면 가장 가까운 날."""
    put(test_db, key, y=entry(day(-1), [row(work='가짜어제')]), t=entry(day(0), [row(work='가짜오늘')]),
        m=entry(day(1), [row(work='가짜내일')]), a=entry(day(2), [row(work='가짜모레')]))
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
