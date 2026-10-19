"""옵시디언 사본 시험 — 일일 일정표만 볼트의 푸드벨-업무/일일 일정표/ 에 복사 글로 남긴다. 시험 서버 · 크롬 없음."""
import datetime
import json
import logging

from tools.sije_web import obsidian_copy, office_agent

T1 = datetime.datetime(2026, 10, 20, 9, 0, tzinfo=datetime.timezone.utc)
T2 = datetime.datetime(2026, 10, 20, 9, 5, tzinfo=datetime.timezone.utc)
TEXT = '[푸드벨 일일 일정표]\n2026년 10월 21일 (수) · 음력 9월 11일\n1. 오전 11:00 가짜군 가짜면\nhttps://foodbell.kr/'


def make_vault(tmp_path):
    vault = tmp_path / '볼트'
    (vault / '푸드벨-업무').mkdir(parents=True)
    return vault


def daily(text=TEXT, at=T1, label='2026년 10월 21일 (수)'):
    return {'kind': 'daily-schedule', 'label': label, 'text': text, 'updatedAt': at}


def note_of(vault, name='2026-10-21 (수)'):
    return vault / '푸드벨-업무' / '일일 일정표' / f'{name}.md'


def test_only_daily_schedule_becomes_note(tmp_path):
    vault = make_vault(tmp_path)
    docs = [('d1', daily()), ('s1', {'kind': 'staff-pay', 'label': '가짜', 'text': '가짜', 'updatedAt': T1})]
    assert obsidian_copy.sync_notes(docs, vault, {}) == ['2026-10-21 (수)']
    assert note_of(vault).read_text(encoding='utf-8') == TEXT
    assert [p.name for p in (vault / '푸드벨-업무' / '일일 일정표').iterdir()] == ['2026-10-21 (수).md']


def test_same_version_is_not_written_again(tmp_path):
    vault, state = make_vault(tmp_path), {}
    obsidian_copy.sync_notes([('d1', daily())], vault, state)
    note_of(vault).write_text('사장님이 노트에 덧붙인 글', encoding='utf-8')
    assert obsidian_copy.sync_notes([('d1', daily())], vault, state) == []
    assert note_of(vault).read_text(encoding='utf-8') == '사장님이 노트에 덧붙인 글'


def test_newer_version_overwrites(tmp_path):
    vault, state = make_vault(tmp_path), {}
    obsidian_copy.sync_notes([('d1', daily())], vault, state)
    assert obsidian_copy.sync_notes([('d1', daily('고친 글', T2))], vault, state) == ['2026-10-21 (수)']
    assert note_of(vault).read_text(encoding='utf-8') == '고친 글'


def test_deleted_schedule_keeps_its_note(tmp_path):
    vault, state = make_vault(tmp_path), {}
    obsidian_copy.sync_notes([('d1', daily())], vault, state)
    assert obsidian_copy.sync_notes([], vault, state) == []
    assert note_of(vault).exists()


def test_other_schedule_with_same_date_gets_its_own_note(tmp_path):
    """새 일정표는 날짜가 늘 내일로 시작한다 — 같은 날짜의 다른 일정표가 앞 노트를 덮지 않는다 (검토 I5)."""
    vault, state = make_vault(tmp_path), {}
    obsidian_copy.sync_notes([('d1', daily('첫 일정표'))], vault, state)
    assert obsidian_copy.sync_notes([('d2', daily('둘째 일정표', T2))], vault, state) == ['2026-10-21 (수) (2)']
    assert note_of(vault).read_text(encoding='utf-8') == '첫 일정표'
    assert note_of(vault, '2026-10-21 (수) (2)').read_text(encoding='utf-8') == '둘째 일정표'
    T3 = T2 + datetime.timedelta(minutes=5)
    assert obsidian_copy.sync_notes([('d1', daily('첫 일정표 고침', T3))], vault, state) == ['2026-10-21 (수)']


def test_note_written_by_hand_is_not_overwritten(tmp_path):
    vault = make_vault(tmp_path)
    note_of(vault).parent.mkdir(parents=True)
    note_of(vault).write_text('사장님이 손으로 쓴 노트', encoding='utf-8')
    assert obsidian_copy.sync_notes([('d1', daily())], vault, {}) == ['2026-10-21 (수) (2)']
    assert note_of(vault).read_text(encoding='utf-8') == '사장님이 손으로 쓴 노트'


def test_note_path_uses_date_and_drops_bad_characters(tmp_path):
    base = tmp_path / '푸드벨-업무' / '일일 일정표'
    assert obsidian_copy.note_path(tmp_path, '2026년 10월 21일 (수)') == base / '2026-10-21 (수).md'
    assert obsidian_copy.note_path(tmp_path, '2027년 1월 1일 (금)') == base / '2027-01-01 (금).md'
    assert obsidian_copy.note_path(tmp_path, '가짜/날:짜?') == base / '가짜날짜.md'
    assert obsidian_copy.note_path(tmp_path, '') == base / '(날짜 없음).md'


def write_obsidian_json(tmp_path, vaults):
    p = tmp_path / 'obsidian.json'
    p.write_text(json.dumps({'vaults': {f'v{i}': {'path': str(v), 'ts': ts} for i, (v, ts) in enumerate(vaults)}}),
                 encoding='utf-8')
    return p


def test_find_vault_picks_the_one_with_work_folder(tmp_path):
    good = make_vault(tmp_path)
    other = tmp_path / '다른 볼트'
    other.mkdir()
    cfg = write_obsidian_json(tmp_path, [(other, 2000), (good, 1000)])   # 최근에 연 볼트가 아니어도 푸드벨-업무 가 있는 쪽
    assert obsidian_copy.find_vault(cfg) == good


def test_find_vault_none_when_missing(tmp_path):
    other = tmp_path / '다른 볼트'
    other.mkdir()
    assert obsidian_copy.find_vault(write_obsidian_json(tmp_path, [(other, 1)])) is None
    assert obsidian_copy.find_vault(tmp_path / '없는.json') is None


class DocsSource:
    """행사 쪽은 비어 있고 서류만 주는 저장소."""

    def changed_since(self, since, collection='events'):
        return self.all_docs() if collection == 'docs' else []

    def all_events(self):
        return []

    def all_docs(self):
        return [('d1', daily())]


def test_one_cycle_writes_note_and_remembers(tmp_path):
    vault = make_vault(tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    log = logging.getLogger('test-agent')
    office_agent.one_cycle(DocsSource(), work, tmp_path / 'state.json', 'http://unused/', log, vault=vault)
    assert note_of(vault).read_text(encoding='utf-8') == TEXT
    note_of(vault).write_text('그대로 둘 것', encoding='utf-8')
    office_agent.one_cycle(DocsSource(), work, tmp_path / 'state.json', 'http://unused/', log, vault=vault)
    assert note_of(vault).read_text(encoding='utf-8') == '그대로 둘 것'   # 같은 판은 다음 차례에 다시 안 씀
