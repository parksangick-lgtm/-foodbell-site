"""내역서 엑셀 한 장 읽기 시험 — 가짜 엑셀만 쓴다. 이름표를 찾아 그 오른쪽 값을 읽는다(줄이 밀려도)."""
import pytest

from conftest import FAKE_PLACE, FAKE_STEM, make_fake_sheet
from tools.sije_web.sheet_parse import (
    SheetError, event_id, extract_images, parse_date_text, parse_sheet, shrink_jpeg, split_filename,
)


def test_parse_date_text_with_time():
    assert parse_date_text('2026년 11월 13일 (금) 10시') == ('2026-11-13', '10시')


def test_parse_date_text_without_time():
    assert parse_date_text('2026년 3월 1일 (일)') == ('2026-03-01', '')


def test_parse_date_text_month_only_raises():
    with pytest.raises(ValueError):
        parse_date_text('2026년10월에')


def test_split_filename_keeps_double_space():
    assert split_filename('2026년11월1일  가짜면 60만원추가 시제행사 내역서') == ('2026년11월1일', '  가짜면 60만원추가')


def test_parse_sheet_reads_all_fields(tmp_path):
    ev = parse_sheet(make_fake_sheet(tmp_path))
    assert ev['status'] == '확정'
    assert (ev['date'], ev['time']) == ('2026-11-13', '10시')
    assert ev['titlePlace'] == '가짜동 1-1'
    assert ev['place'] == FAKE_PLACE and ev['sijeil'] == '음력 10월 3일'
    assert ev['setting'] == '7치 1상' and ev['sansinje'] == '없음' and ev['customer'] == '가짜 문중'
    assert ev['contacts'] == ['010-0000-0000']
    assert ev['meal'] == '20인분' and ev['amountDetail'] == '상차림 60만'
    assert (ev['departTime'], ev['arriveTime']) == ('07시', '09시 30분')
    assert ev['mustDo'] == '산신제 상은 따로 차린다\n도착하면 먼저 전화'
    assert ev['templateType'] == '60만원상'
    assert ev['memo'] == '주차는 가짜 마을회관 앞'
    assert ev['sourceFile'] == FAKE_STEM + '.xlsx'
    assert ev['fileLabel'] == ' 가짜동 1-1'
    assert (ev['expectedDate'], ev['basis'], ev['confirmedText']) == ('', '', '')


def test_parse_sheet_reads_values_by_label_when_rows_shift(tmp_path):
    ev = parse_sheet(make_fake_sheet(tmp_path, contacts=3))
    assert ev['contacts'] == ['010-0000-0000', '010-0000-0001', '010-0000-0002']
    assert ev['staffCar'] == '가짜 담당 · 1호차'
    assert ev['amount'] == '600,000원'


def test_parse_sheet_items_left_right_and_extra(tmp_path):
    ev = parse_sheet(make_fake_sheet(tmp_path, extra=('가짜떡', '2판')))
    assert ev['items']['L01'] == {'group': '과일', 'no': '1', 'name': '배', 'qty': '5개', 'note': ''}
    assert ev['items']['L06']['group'] == '한과'        # 구분이 빈 줄은 위 구분을 이어받는다
    assert ev['items']['R01'] == {'group': '탕', 'no': '18', 'name': '북어탕', 'qty': '1개', 'note': '북어,무'}
    assert len([k for k in ev['items'] if k[0] == 'L']) == 17 and len([k for k in ev['items'] if k[0] == 'R']) == 13
    assert ev['extraItems'] == '가짜떡 2판'
    assert ev['itemRows'] == 17     # 품목표 줄 수 — 엑셀처럼 '추가 기입' 칸을 그리려고


def test_group_starting_with_chuga_is_not_extra_block(tmp_path):
    """'추가 적 (2번째)' 는 진짜 품목 묶음이다 — '추가 기입' 칸으로 착각하면 묶음 이름이 사라진다 (2026-10-16 덕이동 파일)."""
    ev = parse_sheet(make_fake_sheet(tmp_path, rename_group=('전·부침', '추가 적\n(2번째)')))
    assert ev['items']['L15']['group'] == '추가 적\n(2번째)' and ev['items']['L15']['name'] == '녹두부침'
    assert ev['extraItems'] == ''


def test_parse_sheet_amount_kept_as_text(tmp_path):
    assert parse_sheet(make_fake_sheet(tmp_path, amount='2.400,000원'))['amount'] == '2.400,000원'


def test_missing_label_raises_sheet_error(tmp_path):
    with pytest.raises(SheetError) as e:
        parse_sheet(make_fake_sheet(tmp_path, drop_label='담당·차량'))
    assert '담당·차량' in e.value.reason and e.value.file == FAKE_STEM + '.xlsx'


def test_optional_label_missing_becomes_empty(tmp_path):
    """사장님 결정(2026-10-16): 시제일 · 식사 · 금액 내역 이름표가 없는 파일은 그 칸을 빈 칸으로."""
    assert parse_sheet(make_fake_sheet(tmp_path, drop_label='금액 내역'))['amountDetail'] == ''


def test_other_label_moves_to_memo_first_line(tmp_path):
    """사장님 결정(2026-10-16): '지내는 법' · '지내는 곳' 은 메모 맨 앞 줄로, 시제일 칸은 비움."""
    ev = parse_sheet(make_fake_sheet(tmp_path, rename=('시제일', '지내는 법')))
    assert ev['memo'] == '지내는 법 — 음력 10월 3일\n주차는 가짜 마을회관 앞'
    assert ev['sijeil'] == ''


def test_unknown_label_still_raises(tmp_path):
    with pytest.raises(SheetError) as e:
        parse_sheet(make_fake_sheet(tmp_path, rename=('시제일', '가짜 이름표')))
    assert '가짜 이름표' in e.value.reason


def test_extract_and_shrink_image(tmp_path):
    images = extract_images(make_fake_sheet(tmp_path, with_image=True))
    assert len(images) == 1
    small = shrink_jpeg(images[0])
    assert len(small) <= 900_000 and small[:3] == b'\xff\xd8\xff'   # JPEG


def test_event_id_is_stable():
    assert event_id(FAKE_STEM + '.xlsx') == event_id(FAKE_STEM + '.xlsx')
    assert len(event_id(FAKE_STEM + '.xlsx')) == 12
