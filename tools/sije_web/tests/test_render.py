"""인쇄 그리기 → PDF 시험 — A4 한 장, 잘린 글자 0, 핵심 글자 그대로. PDF 는 시험 임시 폴더에만 만든다."""
import pymupdf
import pytest

from conftest import fake_event, fake_jpeg
from tools.sije_web.render_pdf import TooLong, clipped_words, render_pdf


def pdf_text(path) -> str:
    with pymupdf.open(path) as doc:
        return ''.join(''.join(p.get_text().split()) for p in doc)


def test_normal_event_is_one_page_without_clipping(tmp_path, repo_url):
    out = tmp_path / 'normal.pdf'
    assert render_pdf(fake_event(), [], out, repo_url) == 1
    assert clipped_words(out) == []


def test_pdf_contains_key_values(tmp_path, repo_url):
    out = tmp_path / 'values.pdf'
    render_pdf(fake_event(), [], out, repo_url)
    text = pdf_text(out)
    for want in ['가짜동1-1', '2026년11월13일(금)10시', '배', '5개', '산신제상은따로차린다', '도착하면먼저전화',
                 '010-0000-0000', '600,000원', '주차는가짜마을회관앞', '■준비품목—60만원상']:
        assert want in text, want


def test_long_text_event_still_fits_one_page(tmp_path, repo_url):
    must = '\n'.join(f'꼭 지킬 것 {i}번째 줄 — 상 차리는 순서와 자리를 손님과 다시 확인한다' for i in range(1, 9))
    memo = '\n'.join(f'메모 {i}번째 줄 — 가는 길 · 주차 · 연락할 사람 · 남은 음식 처리' for i in range(1, 16))
    out = tmp_path / 'long.pdf'
    assert render_pdf(fake_event(mustDo=must, memo=memo), [], out, repo_url) == 1
    assert clipped_words(out) == []
    text = pdf_text(out)
    assert '꼭지킬것8번째줄' in text and '메모15번째줄' in text


def test_absurdly_long_event_raises_too_long(tmp_path, repo_url):
    memo = '\n'.join(f'메모 {i}번째 줄' for i in range(1, 81))
    with pytest.raises(TooLong):
        render_pdf(fake_event(memo=memo), [], tmp_path / 'too-long.pdf', repo_url)


def test_item_rows_draw_extra_blocks_on_both_sides(tmp_path, repo_url):
    """옛 엑셀은 줄 수를 합치기 전 기준으로 잡아 양쪽 모두에 '추가 기입' 칸이 생기기도 한다 (2026-10-16 비교에서 14장)."""
    out = tmp_path / 'rows.pdf'
    assert render_pdf(fake_event(itemRows=18), [], out, repo_url) == 1
    assert pdf_text(out).count('추가기입') == 2


def test_image_is_drawn_in_memo(tmp_path, repo_url):
    out = tmp_path / 'image.pdf'
    assert render_pdf(fake_event(), [fake_jpeg()], out, repo_url) == 1
    with pymupdf.open(out) as doc:
        assert len(doc[0].get_images()) >= 1
