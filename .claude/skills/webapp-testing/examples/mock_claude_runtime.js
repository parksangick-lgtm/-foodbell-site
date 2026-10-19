(() => {
  // Stand-in for the claude.ai viewer's db/user capabilities, following db.d.ts:
  // a write is applied and echoed to listeners at once (hasPendingWrites: true),
  // and its promise resolves after a simulated server round trip.
  // MODE decides whether a second "confirmed" snapshot follows, and when.
  const MODE = '__MODE__'; // 'none' | 'before-resolve' | 'after-resolve'
  const SEED = __SEED__;
  const SERVER_MS = 150;
  const UID = 'u_test';
  const store = new Map();
  const listeners = new Set();
  window.__store = store;
  window.__mock = { listeners };

  for (const [p, d] of Object.entries(SEED)) store.set(p.replace('{uid}', UID), d);

  const split = (p) => p.split('/');
  const parentOf = (p) => split(p).slice(0, -1).join('/');
  const lastOf = (p) => split(p).slice(-1)[0];
  const clone = (o) => JSON.parse(JSON.stringify(o));

  function assertParity(p, wantDoc) {
    const n = split(p).length;
    if (split(p).some((s) => !s)) throw new TypeError('empty segment in path: ' + p);
    if (wantDoc && n % 2 !== 0) throw new TypeError('document path needs an even segment count: ' + p);
    if (!wantDoc && n % 2 !== 1) throw new TypeError('collection path needs an odd segment count: ' + p);
  }

  function docSnap(path, pending) {
    const exists = store.has(path);
    const body = exists ? Object.freeze(clone(store.get(path))) : undefined;
    return Object.freeze({ id: lastOf(path), exists, data: () => body, metadata: { fromCache: false, hasPendingWrites: pending } });
  }

  function querySnap(q, pending) {
    const docs = [];
    for (const p of store.keys()) if (parentOf(p) === q.path) docs.push(docSnap(p, pending));
    if (q.field) {
      docs.sort((a, b) => {
        const av = a.data()[q.field];
        const bv = b.data()[q.field];
        if (av === undefined) return bv === undefined ? 0 : 1;
        if (bv === undefined) return -1;
        const c = av < bv ? -1 : av > bv ? 1 : 0;
        return q.dir === 'desc' ? -c : c;
      });
    } else {
      docs.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    }
    return Object.freeze({ docs, size: docs.length, empty: docs.length === 0, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: pending } });
  }

  function deliver(l, pending) {
    if (!listeners.has(l)) return;
    l.next(l.kind === 'doc' ? docSnap(l.path, pending) : querySnap(l, pending));
  }

  function notify(changed, pending) {
    for (const l of [...listeners]) {
      if ((l.kind === 'doc' && l.path === changed) || (l.kind === 'query' && l.path === parentOf(changed))) deliver(l, pending);
    }
  }

  function write(path, apply) {
    apply();
    setTimeout(() => notify(path, true), 0);
    return new Promise((resolve) => {
      setTimeout(() => {
        if (MODE === 'before-resolve') notify(path, false);
        resolve();
        if (MODE === 'after-resolve') setTimeout(() => notify(path, false), 0);
      }, SERVER_MS);
    });
  }

  function subscribe(l) {
    listeners.add(l);
    setTimeout(() => deliver(l, false), 0);
    return () => listeners.delete(l);
  }

  let counter = 0;
  const mint = () => 'x' + String(++counter).padStart(3, '0') + Math.random().toString(36).slice(2, 6);

  function docRef(path) {
    assertParity(path, true);
    return Object.freeze({
      id: lastOf(path),
      path,
      get: () => Promise.resolve(docSnap(path, false)),
      set: (data) => write(path, () => store.set(path, clone(data))),
      update: (data) =>
        store.has(path)
          ? write(path, () => store.set(path, Object.assign(clone(store.get(path)), clone(data))))
          : Promise.reject({ code: 'invalid_argument', message: 'update on a missing document: ' + path }),
      delete: () => write(path, () => store.delete(path)),
      onSnapshot: (next, error) => subscribe({ kind: 'doc', path, next, error }),
      collection: (sub) => colRef(path + '/' + sub),
    });
  }

  function makeQuery(path, field, dir) {
    return {
      orderBy: (f, d) => makeQuery(path, f, d || 'asc'),
      limit: () => makeQuery(path, field, dir),
      where: () => {
        throw new Error('where is not mocked');
      },
      get: () => Promise.resolve(querySnap({ path, field, dir }, false)),
      onSnapshot: (next, error) => subscribe({ kind: 'query', path, field, dir, next, error }),
    };
  }

  function colRef(path) {
    assertParity(path, false);
    return Object.freeze(
      Object.assign(makeQuery(path, null, 'asc'), {
        path,
        doc: (id) => docRef(path + '/' + (id === undefined ? mint() : id)),
        add: (data) => {
          const ref = docRef(path + '/' + mint());
          return ref.set(data).then(() => ref);
        },
      })
    );
  }

  const db = Object.freeze({ doc: (p) => docRef(p), collection: (p) => colRef(p) });
  const user = Object.freeze({
    id: () => Promise.resolve(UID),
    isOwner: () => Promise.resolve(true),
    canEdit: () => Promise.resolve(true),
    can: () => Promise.resolve(true),
  });
  window.claude = Object.freeze({
    use: (name) => new Promise((resolve) => setTimeout(() => resolve(name === 'db' ? db : name === 'user' ? user : null), 20)),
  });
})();
