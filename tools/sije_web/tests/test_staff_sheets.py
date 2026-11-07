"""담당자 한 장(staffSheets) 시험 — 저장소 없이 가짜로.
2026-11-07 사장님: 날짜 제한 없이(영영 열림) — 확정 + 링크 있는 행사는 날짜와 상관없이 올린다."""
import datetime
from types import SimpleNamespace

from conftest import fake_event
from tools.sije_web import staff_sheets

KEYS = {n: n * 32 for n in 'abcdef'}
FIELDS = {'date', 'time', 'place', 'titlePlace', 'setting', 'templateType', 'sijeil', 'sansinje', 'meal', 'staffCar',
          'departTime', 'arriveTime', 'customer', 'contacts', 'amount', 'amountDetail', 'mustDo', 'extraItems', 'memo',
          'items'}
T0 = datetime.datetime(2026, 11, 1, 9, 0, tzinfo=datetime.timezone.utc)


def _at(minutes):
    return T0 + datetime.timedelta(minutes=minutes)


class _Snap:
    def __init__(self, id, data):
        self.id, self._d = id, data

    @property
    def exists(self):
        return self._d is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class _Doc:
    def __init__(self, db, store, id):
        self.db, self.store, self.id = db, store, id

    def get(self):
        self.db.reads += 1
        return _Snap(self.id, self.store.get(self.id))

    def set(self, data):
        self.store[self.id] = dict(data)

    def delete(self):
        self.store.pop(self.id, None)


class _Coll:
    def __init__(self, db, store, rows=None):
        self.db, self.store, self.rows = db, store, rows

    def where(self, filter):
        assert filter.op_string == '>' and filter.field_path in ('viewKey', 'updatedAt'), filter.field_path
        rows = {k: v for k, v in self.store.items()
                if v.get(filter.field_path) is not None and v[filter.field_path] > filter.value}
        return _Coll(self.db, self.store, rows)

    def count(self):
        n = len(self.store if self.rows is None else self.rows)
        return SimpleNamespace(get=lambda: [[SimpleNamespace(value=n)]])

    def stream(self):
        rows = self.store if self.rows is None else self.rows
        self.db.reads += len(rows)
        return [_Snap(k, v) for k, v in rows.items()]

    def document(self, id):
        return _Doc(self.db, self.store, id)


class FakeDb:
    def __init__(self):
        self.cols = {'events': {}, 'staffSheets': {}}
        self.reads = 0

    def collection(self, name):
        return _Coll(self, self.cols[name])


def _db_with(events):
    db = FakeDb()
    db.cols['events'].update(events)
    return db


def _events():
    return {
        'past': fake_event(date='2026-10-20', viewKey=KEYS['a'], updatedAt=_at(1)),
        'far': fake_event(date='2026-11-15', viewKey=KEYS['b'], updatedAt=_at(2)),
        'unconfirmed': fake_event(date='2026-11-12', status='미확정', viewKey=KEYS['c'], updatedAt=_at(3)),
        'nokey': fake_event(date='2026-11-12', updatedAt=_at(4)),
        'nodate': fake_event(date='', viewKey=KEYS['d'], updatedAt=_at(5)),
    }


def test_staff_view_keeps_listed_fields_only():
    v = staff_sheets.staff_view(fake_event(viewKey='k' * 32, printedAt='x', expectedDate='y'))
    assert set(v) == FIELDS
    assert v['amount'] == '600,000원'


def test_staff_view_items_left_then_right_and_drops_empty_rows():
    ev = fake_event()
    ev['items']['L02'].update(qty='', note='')
    items = staff_sheets.staff_view(ev)['items']
    assert items[0]['name'] == '배'
    assert '사과' not in [i['name'] for i in items]
    assert items[-1]['name'] == '물김치'   # 오른쪽 마지막 키 R13 '술' 은 수량 · 비고가 비어 빠진다
    assert set(items[0]) == {'group', 'name', 'qty', 'note'}


def test_sync_publishes_every_confirmed_with_key_whatever_the_date():
    db = _db_with(_events())
    out = staff_sheets.sync_staff_sheets(db, {})
    assert set(db.cols['staffSheets']) == {KEYS['a'], KEYS['b'], KEYS['d']}
    assert sorted(out['written']) == ['', '2026-10-20', '2026-11-15'] and out['removed'] == []
    assert 'at' in db.cols['staffSheets'][KEYS['a']]


def test_sync_does_not_rewrite_unchanged():
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    assert staff_sheets.sync_staff_sheets(db, state) == {'written': [], 'removed': []}


def test_quiet_cycle_reads_almost_nothing():
    """무료 읽기 한도(하루 5만)를 웹 서류와 같이 쓴다 — 바뀐 게 없는 차례는 행사 · 한 장을 다 읽지 않는다."""
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    db.reads = 0
    staff_sheets.sync_staff_sheets(db, state)
    assert db.reads == 0


def test_new_link_without_updated_at_change_is_published_next_cycle():
    """링크를 만들면 viewKey 만 생기고 updatedAt 은 그대로다(바뀌면 PDF 를 다시 그린다) — 그래도 다음 차례에 올라간다."""
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    db.cols['events']['nokey']['viewKey'] = KEYS['e']
    out = staff_sheets.sync_staff_sheets(db, state)
    assert out == {'written': ['2026-11-12'], 'removed': []}
    assert KEYS['e'] in db.cols['staffSheets']


def test_edit_is_republished_reading_only_the_changed_event():
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    db.cols['events']['far'].update(memo='바뀐 메모', updatedAt=_at(10))
    db.reads = 0
    out = staff_sheets.sync_staff_sheets(db, state)
    assert out == {'written': ['2026-11-15'], 'removed': []}
    assert db.cols['staffSheets'][KEYS['b']]['memo'] == '바뀐 메모'
    assert db.reads <= 2   # 바뀐 행사 1 + 그 한 장 1


def test_unconfirming_removes_the_sheet():
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    db.cols['events']['far'].update(status='주문없음', updatedAt=_at(10))
    out = staff_sheets.sync_staff_sheets(db, state)
    assert out == {'written': [], 'removed': ['2026-11-15']}
    assert KEYS['b'] not in db.cols['staffSheets']


def test_confirming_later_publishes():
    db, state = _db_with(_events()), {}
    staff_sheets.sync_staff_sheets(db, state)
    db.cols['events']['unconfirmed'].update(status='확정', updatedAt=_at(10))
    out = staff_sheets.sync_staff_sheets(db, state)
    assert out == {'written': ['2026-11-12'], 'removed': []}


def test_full_pass_removes_sheet_without_linked_event():
    db = _db_with(_events())
    db.cols['staffSheets'][KEYS['f']] = {'date': '2026-10-31'}
    out = staff_sheets.sync_staff_sheets(db, {})
    assert out['removed'] == ['2026-10-31']
    assert KEYS['f'] not in db.cols['staffSheets']
