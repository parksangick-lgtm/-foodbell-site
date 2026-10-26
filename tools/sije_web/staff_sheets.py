r"""담당자 내역서 한 장 — 확정된 오늘 · 내일 행사만 읽기 전용으로 staffSheets/{viewKey} 에 올리고, 기간 밖은 지운다.
사무실 프로그램(office_agent)이 5분마다 부른다. 행사 문서(events)는 건드리지 않는다(updatedAt 이 바뀌면 PDF 를 다시 그린다).
"""
import datetime

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# 한 장에 넣는 칸 (설계서 그대로). 'at' 은 올릴 때 서버 시각으로 붙인다.
_PLAIN = ('date', 'time', 'place', 'titlePlace', 'setting', 'templateType', 'sijeil', 'sansinje', 'meal', 'staffCar',
          'departTime', 'arriveTime', 'customer', 'amount', 'amountDetail', 'mustDo', 'extraItems', 'memo')


def _items(items: dict) -> list:
    """왼쪽 L01… 다음 오른쪽 R01… 순서. 수량 · 비고가 둘 다 빈 줄은 뺀다."""
    out = []
    for side in ('L', 'R'):
        for key in sorted(k for k in items if k.startswith(side)):
            it = items[key] or {}
            if not it.get('qty') and not it.get('note'):
                continue
            out.append({k: it.get(k, '') for k in ('group', 'name', 'qty', 'note')})
    return out


def staff_view(ev: dict) -> dict:
    v = {k: ev.get(k, '') for k in _PLAIN}
    v['contacts'] = list(ev.get('contacts') or [])
    v['items'] = _items(ev.get('items') or {})
    return v


def sync_staff_sheets(db, today: datetime.date) -> dict:
    window = [today.isoformat(), (today + datetime.timedelta(days=1)).isoformat()]
    events = db.collection('events').where(filter=FieldFilter('date', 'in', window)).stream()
    wanted = {}
    for snap in events:
        ev = snap.to_dict()
        if ev.get('status') == '확정' and ev.get('viewKey'):
            wanted[ev['viewKey']] = staff_view(ev)
    sheets = db.collection('staffSheets')
    current = {s.id: s.to_dict() for s in sheets.stream()}
    written, removed = [], []
    for key, view in wanted.items():
        if {k: v for k, v in (current.get(key) or {}).items() if k != 'at'} == view:
            continue
        sheets.document(key).set({**view, 'at': firestore.SERVER_TIMESTAMP})
        written.append(view['date'])
    for key, old in current.items():
        if key not in wanted:
            sheets.document(key).delete()
            removed.append(old.get('date', ''))
    return {'written': written, 'removed': removed}
