r"""담당자 내역서 한 장 — 확정 + 링크(viewKey) 있는 행사를 날짜와 상관없이 읽기 전용으로 staffSheets/{viewKey} 에 올리고,
확정이 풀리면 지운다(2026-11-07 사장님 — 처음엔 행사 전날 · 당일만이었으나 '영영 열림'으로 바꿈).
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


def _iso(v) -> str:
    return v.isoformat() if isinstance(v, datetime.datetime) else str(v or '')


def sync_staff_sheets(db, state: dict) -> dict:
    """차례마다 행사 전체를 읽지 않는다 — 무료 읽기 한도(하루 5만)를 웹 서류와 같이 쓴다.
    링크 수(세기, 읽기 1번)가 지난 차례와 같으면 since 뒤에 고친 행사만 본다. 링크를 만들 때는 updatedAt 이 안 바뀌므로
    새 링크는 링크 수가 늘어난 것으로 알고, 그때(와 처음)만 링크 있는 행사 전체 + 올라간 한 장 전체를 읽는다.
    state 는 {'since': 마지막으로 본 updatedAt, 'linked': 링크 수} — 이 함수가 고친다(부르는 쪽이 파일에 저장)."""
    events, sheets = db.collection('events'), db.collection('staffSheets')
    has_key = FieldFilter('viewKey', '>', '')
    linked = events.where(filter=has_key).count().get()[0][0].value
    full = linked != state.get('linked') or not state.get('since')
    if full:
        rows = [s.to_dict() for s in events.where(filter=has_key).stream()]
        current = {s.id: s.to_dict() for s in sheets.stream()}
    else:
        since = datetime.datetime.fromisoformat(state['since'])
        rows = [s.to_dict() for s in events.where(filter=FieldFilter('updatedAt', '>', since)).stream()]
    written, removed = [], []
    for ev in rows:
        key = ev.get('viewKey')
        if not key:
            continue
        old = current.get(key) if full else sheets.document(key).get().to_dict()
        if ev.get('status') == '확정':
            view = staff_view(ev)
            if {k: v for k, v in (old or {}).items() if k != 'at'} != view:   # 담당자 휴대폰이 쓸데없이 다시 받지 않게
                sheets.document(key).set({**view, 'at': firestore.SERVER_TIMESTAMP})
                written.append(view['date'])
        elif old is not None:   # 미확정 · 주문없음이 되면 담당자 화면에서도 사라진다
            sheets.document(key).delete()
            removed.append(old.get('date', ''))
    if full:   # 이끄는 행사가 없는 한 장(지운 행사 등)
        keys = {ev.get('viewKey') for ev in rows}
        for key, old in current.items():
            if key not in keys:
                sheets.document(key).delete()
                removed.append(old.get('date', ''))
    state['since'] = max([state.get('since') or ''] + [_iso(ev.get('updatedAt')) for ev in rows])
    state['linked'] = linked
    return {'written': written, 'removed': removed}
