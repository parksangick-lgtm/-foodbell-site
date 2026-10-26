"""담당자 한 장(staffSheets) 시험 — 저장소 없이 가짜로."""
import datetime

from conftest import fake_event
from tools.sije_web import staff_sheets

TODAY = datetime.date(2026, 10, 27)
KEYS = {n: n * 32 for n in 'abcdef'}
FIELDS = {'date', 'time', 'place', 'titlePlace', 'setting', 'templateType', 'sijeil', 'sansinje', 'meal', 'staffCar',
          'departTime', 'arriveTime', 'customer', 'contacts', 'amount', 'amountDetail', 'mustDo', 'extraItems', 'memo',
          'items'}


class _Snap:
    def __init__(self, id, data):
        self.id, self._d = id, data

    @property
    def exists(self):
        return self._d is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class _Doc:
    def __init__(self, store, id):
        self.store, self.id = store, id

    def get(self):
        return _Snap(self.id, self.store.get(self.id))

    def set(self, data):
        self.store[self.id] = dict(data)

    def delete(self):
        self.store.pop(self.id, None)


class _Coll:
    def __init__(self, store, rows=None):
        self.store, self.rows = store, rows

    def where(self, filter):
        assert filter.field_path == 'date' and filter.op_string == 'in'
        return _Coll(self.store, {k: v for k, v in self.store.items() if v.get('date') in filter.value})

    def stream(self):
        return [_Snap(k, v) for k, v in (self.store if self.rows is None else self.rows).items()]

    def document(self, id):
        return _Doc(self.store, id)


class FakeDb:
    def __init__(self):
        self.cols = {'events': {}, 'staffSheets': {}}

    def collection(self, name):
        return _Coll(self.cols[name])


def _db_with(events):
    db = FakeDb()
    db.cols['events'].update(events)
    return db


def _window_events():
    return {
        'today': fake_event(date='2026-10-27', viewKey=KEYS['a']),
        'tomorrow': fake_event(date='2026-10-28', viewKey=KEYS['b']),
        'unconfirmed': fake_event(date='2026-10-28', status='미확정', viewKey=KEYS['c']),
        'nokey': fake_event(date='2026-10-28'),
        'dayafter': fake_event(date='2026-10-29', viewKey=KEYS['d']),
        'yesterday': fake_event(date='2026-10-26', viewKey=KEYS['e']),
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


def test_sync_publishes_only_confirmed_with_key_today_or_tomorrow():
    db = _db_with(_window_events())
    out = staff_sheets.sync_staff_sheets(db, TODAY)
    assert set(db.cols['staffSheets']) == {KEYS['a'], KEYS['b']}
    assert sorted(out['written']) == ['2026-10-27', '2026-10-28'] and out['removed'] == []
    assert 'at' in db.cols['staffSheets'][KEYS['a']]


def test_sync_does_not_rewrite_unchanged():
    db = _db_with(_window_events())
    staff_sheets.sync_staff_sheets(db, TODAY)
    assert staff_sheets.sync_staff_sheets(db, TODAY)['written'] == []


def test_sync_removes_out_of_window():
    db = _db_with(_window_events())
    staff_sheets.sync_staff_sheets(db, TODAY)
    db.cols['events']['tomorrow']['date'] = '2026-11-03'
    out = staff_sheets.sync_staff_sheets(db, TODAY)
    assert out == {'written': [], 'removed': ['2026-10-28']}
    assert set(db.cols['staffSheets']) == {KEYS['a']}
