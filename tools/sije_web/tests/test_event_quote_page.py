"""행사 견적서(event-quote.html) 보완 시험 — 서류 7종 보완 2차 (사장님 2026-11-01).
도우미 · 준비물은 2단계 test_doc_pages.py 의 것을 그대로 쓴다. 시험 프로젝트 · 가짜 자료만, 만든 서류는 끝나면 지운다."""
import pytest

from test_doc_pages import ALLOWED, edit_cell, made, new_doc, open_list, pc, text_of  # noqa: F401 (준비물)

FILE = 'event-quote.html'


def open_new_editing(pc, repo_url, custom_token, made):
    """새 행사 견적서를 만들어 편집 모드로."""
    open_list(pc, repo_url, FILE, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    pc.click('#btn-edit')


def test_event_quote_fills_supply_from_head_times_perhead(pc, repo_url, custom_token, made):
    """참석 인원 50 · 1인당 10,000 을 치면 공급가액이 500,000 으로 저절로 — 부가세 · 합계도 따라온다."""
    open_new_editing(pc, repo_url, custom_token, made)
    edit_cell(pc, '[data-k="head"]', '50')
    edit_cell(pc, '[data-k="perhead"]', '10000')
    assert text_of(pc, '[data-k="supply"]') == '500,000'
    assert pc.get_attribute('[data-k="supply"]', 'data-raw') == '500000'
    assert text_of(pc, '[data-k="vat"]') == '50,000'
    assert text_of(pc, '[data-k="total"]') == '550,000'


def test_event_quote_keeps_written_supply(pc, repo_url, custom_token, made):
    """공급가액을 먼저 300,000 으로 적어 두면 인원 · 1인당을 바꿔도 그대로 — 적힌 금액은 덮지 않는다."""
    open_new_editing(pc, repo_url, custom_token, made)
    edit_cell(pc, '[data-k="supply"]', '300000')
    edit_cell(pc, '[data-k="perhead"]', '10000')
    edit_cell(pc, '[data-k="head"]', '50')
    assert text_of(pc, '[data-k="supply"]') == '300,000'
    assert pc.get_attribute('[data-k="supply"]', 'data-raw') == '300000'
    assert text_of(pc, '[data-k="total"]') == '330,000'


def test_event_quote_new_doc_head_is_blank_mark(pc, repo_url, custom_token, made):
    """새 서류의 참석 인원 칸은 예시 숫자(100)가 아니라 빈칸 표기 '○' — 수량 칸의 인원 기준 칸도 같다."""
    open_list(pc, repo_url, FILE, custom_token(ALLOWED, allowed=True))
    new_doc(pc, made)
    assert text_of(pc, '[data-k="head"]') == '○'
    assert pc.get_attribute('[data-k="head"]', 'data-raw') == ''
    assert text_of(pc, 'td[data-fill="head"] span[data-edit]') == '○'
