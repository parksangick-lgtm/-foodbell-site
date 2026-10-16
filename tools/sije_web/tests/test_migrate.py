"""옮기기 프로그램 시험 — 가짜 엑셀 폴더로 연습(--dry-run)과 쓰기(--write, 시험 프로젝트)를 해 본다."""
import json

import pymupdf
import pytest

from conftest import FAKE_DATE_TEXT, FAKE_PLACE, FAKE_STEM, make_fake_blank, make_fake_list, make_fake_sheet
from tools.sije_web import fsdb, migrate
from tools.sije_web.sheet_parse import event_id

EID = event_id(FAKE_STEM + '.xlsx')


@pytest.fixture
def excel(tmp_path):
    """가짜 작업장: 2026년/확정/한 장 + 확정 목록 · 미확정 목록 + 빈 양식 하나."""
    sheet = make_fake_sheet(tmp_path, with_image=True)
    confirmed = make_fake_list(tmp_path / '2026년 확정 날짜 목록.xlsx', [
        (FAKE_DATE_TEXT, FAKE_PLACE, '010-0000-0000', '', '작년 음력 날짜', '2026년 11월 13일 (금) 10시')])
    pending = make_fake_list(tmp_path / '2026년 미확정 목록.xlsx', [])
    blank = make_fake_blank(tmp_path)
    return {'root': tmp_path / '2026년', 'sheet': sheet, 'lists': [confirmed, pending], 'blanks': [blank]}


def args(x, *mode):
    return ['--excel-root', str(x['root']), '--lists', *map(str, x['lists']), '--blanks', *map(str, x['blanks']), *mode]


@pytest.fixture
def cleanup(test_db):
    yield
    ref = test_db.collection('events').document(EID)
    for img in ref.collection('images').stream():
        img.reference.delete()
    ref.delete()
    test_db.collection('templates').document('60만원상').delete()


def count_events(db):
    return sum(1 for _ in db.collection('events').select([]).stream())


def test_migrate_stops_when_excel_lock_file_present(excel, tmp_path, capsys):
    lock = excel['sheet'].parent / ('~$' + excel['sheet'].name)
    lock.write_bytes(b'')
    out = tmp_path / 'dry'
    assert migrate.main(args(excel, '--dry-run', str(out))) != 0
    said = capsys.readouterr().out
    assert '엑셀을 닫아 주세요' in said and lock.name in said
    assert not (out / 'events.json').exists()


def test_migrate_write_refuses_when_any_problem(excel, test_db, capsys):
    make_fake_list(excel['lists'][1], [('2026년 11월 20일 (금) 10시', '가짜동 없는 곳', '', '', '', '')])
    before = count_events(test_db)
    assert migrate.main(args(excel, '--write', '--key', str(fsdb.KEY_TEST))) != 0
    assert count_events(test_db) == before
    assert '2번째 줄' in capsys.readouterr().out


def test_migrate_dry_run_writes_json_and_pdfs_no_db(excel, tmp_path, test_db):
    out = tmp_path / 'dry'
    assert migrate.main(args(excel, '--dry-run', str(out))) == 0
    data = json.loads((out / 'events.json').read_text(encoding='utf-8'))
    assert [d['id'] for d in data] == [EID]
    assert data[0]['event']['basis'] == '작년 음력 날짜' and data[0]['images'] == 1
    assert '60만원상' in json.loads((out / 'templates.json').read_text(encoding='utf-8'))
    pdf = out / 'pdf' / '확정' / f'{FAKE_STEM}.pdf'
    with pymupdf.open(pdf) as doc:
        assert doc.page_count == 1 and len(doc[0].get_images()) >= 1
    assert not test_db.collection('events').document(EID).get().exists


def test_migrate_rerun_is_idempotent(excel, test_db, cleanup):
    assert migrate.main(args(excel, '--write', '--key', str(fsdb.KEY_TEST))) == 0
    before = count_events(test_db)
    assert migrate.main(args(excel, '--write', '--force', '--key', str(fsdb.KEY_TEST))) == 0
    assert count_events(test_db) == before
    ref = test_db.collection('events').document(EID)
    assert ref.get().get('status') == '확정'
    imgs = list(ref.collection('images').stream())
    assert len(imgs) == 1 and len(imgs[0].get('bytes')) <= 900_000
    assert test_db.collection('templates').document('60만원상').get().get('items')['L01']['name'] == '배'


def test_second_write_refuses_without_force(excel, test_db, cleanup, capsys):
    """갈아탄 뒤 옮기기를 또 돌리면 웹에서 고친 것을 옛 엑셀로 덮는다 — --force 없이는 멈춘다 (검토 M3)."""
    assert migrate.main(args(excel, '--write', '--key', str(fsdb.KEY_TEST))) == 0
    test_db.collection('events').document(EID).update({'memo': '웹에서 고침'})
    assert migrate.main(args(excel, '--write', '--key', str(fsdb.KEY_TEST))) != 0
    assert '이미 옮긴 행사' in capsys.readouterr().out
    assert test_db.collection('events').document(EID).get().get('memo') == '웹에서 고침'


def test_pdf_name_change_is_a_problem(tmp_path, capsys):
    """사무실 PC 는 PDF 이름을 날짜 칸에서 새로 짓는다 — 엑셀 파일 이름과 다르면 PDF 가 둘이 되므로 미리 알린다 (검토 I6)."""
    make_fake_sheet(tmp_path, stem='2026년11월14일 가짜동 1-1 시제행사 내역서')     # 칸의 날짜는 11월 13일
    x = {'root': tmp_path / '2026년', 'lists': [make_fake_list(tmp_path / '확정.xlsx', []),
                                               make_fake_list(tmp_path / '미확정.xlsx', [])],
         'blanks': [make_fake_blank(tmp_path)]}
    out = tmp_path / 'dry'
    assert migrate.main(args(x, '--dry-run', str(out))) != 0
    said = capsys.readouterr().out
    assert 'PDF 이름' in said and '2026년11월14일 가짜동 1-1 시제행사 내역서.xlsx' in said
    assert (out / 'pdf' / '확정' / '2026년11월13일 가짜동 1-1 시제행사 내역서.pdf').exists()   # 사무실 PC 가 쓸 이름


def test_same_file_name_in_two_folders_is_a_problem(tmp_path, capsys):
    """id 는 파일 이름에서 나온다 — 같은 이름이 두 폴더에 있으면 하나가 조용히 덮이므로 멈춘다 (검토 M2)."""
    make_fake_sheet(tmp_path)
    make_fake_sheet(tmp_path, status='미확정')
    x = {'root': tmp_path / '2026년', 'lists': [make_fake_list(tmp_path / '확정.xlsx', []),
                                               make_fake_list(tmp_path / '미확정.xlsx', [])],
         'blanks': [make_fake_blank(tmp_path)]}
    assert migrate.main(args(x, '--dry-run', str(tmp_path / 'dry'))) != 0
    assert '같은 파일 이름' in capsys.readouterr().out


def test_dry_run_refuses_output_inside_repo(excel, capsys):
    """연습 결과(손님 정보)를 저장소 폴더 안에 쓰면 자동 저장이 공개한다 — 멈춘다 (검토 M4)."""
    out = migrate.ROOT / '_dry_should_not_exist'
    assert migrate.main(args(excel, '--dry-run', str(out))) == 2
    assert not out.exists()
    assert '저장소 밖' in capsys.readouterr().out


def test_migrate_never_saves_source(excel, tmp_path):
    files = [excel['sheet'], *excel['lists'], *excel['blanks']]
    before = [f.read_bytes() for f in files]
    assert migrate.main(args(excel, '--dry-run', str(tmp_path / 'dry'))) == 0
    assert [f.read_bytes() for f in files] == before
