// 시제행사 내역서 — 파이어베이스 저장소(Firestore) · 구글 로그인 감싸기.
// 화면 코드는 이 파일만 부르고 파이어베이스를 직접 부르지 않는다.
// 오프라인 저장을 켜 둔다: 열어 본 적 있는 행사는 인터넷 없이도 열리고, 고친 것은 연결되면 올라간다.
import { SDK, projectConfig } from './firebase-config.js';
import { newEventFromTemplate } from './model.js?v=1';   // 부르는 곳 모두 같은 주소 — 고치면 전부 올린다
// 이 파일을 고치면 부르는 곳(doc-page.js · list-page.js · sheet-page.js · 시험 test_sheet_page.py)의 store.js?v= 를 같이 올린다

const CDN = `https://www.gstatic.com/firebasejs/${SDK}`;
const [{ initializeApp }, fs, au] = await Promise.all([
  import(`${CDN}/firebase-app.js`),
  import(`${CDN}/firebase-firestore.js`),
  import(`${CDN}/firebase-auth.js`),
]);

let db, auth;

export async function initStore() {
  if (db) return;
  const app = initializeApp(projectConfig(location.hostname));
  db = fs.initializeFirestore(app, {
    localCache: fs.persistentLocalCache({ tabManager: fs.persistentMultipleTabManager() }),
  });
  auth = au.getAuth(app);
  await au.getRedirectResult(auth).catch(() => {});   // 다른 방식(redirect) 로그인에서 돌아온 경우 마무리
}

export function onUser(cb) {
  return au.onAuthStateChanged(auth, cb);
}

// 팝업 로그인 — 홈 화면 앱(standalone)이거나 팝업이 막히면 페이지를 넘겨 로그인(redirect).
// 홈 화면 앱은 팝업이 떠도 결과가 안 돌아오는 일이 많아 처음부터 redirect 로 간다.
export async function signIn() {
  const provider = new au.GoogleAuthProvider();
  if (matchMedia('(display-mode: standalone)').matches) return au.signInWithRedirect(auth, provider);
  try {
    await au.signInWithPopup(auth, provider);
  } catch (e) {
    if (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment') {
      await au.signInWithRedirect(auth, provider);
    } else {
      throw e;
    }
  }
}

export function signOutUser() {
  return au.signOut(auth);
}

// 로그인한 사람의 자리 — 허락 목록(allow)에 있으면 주인, 아니면 보기 명단(viewers)에 있으면 보기 전용(일일 일정표만).
// 규칙이 자기 메일의 문서만 읽게 해 준다. 문서가 없으면 그 자리가 아니고, 못 읽으면(끊김) 실패 — 부르는 쪽이 지난번 것을 쓴다.
export async function myRole(email) {
  const key = (email || '').toLowerCase();
  const has = (c) => fs.getDoc(fs.doc(db, c, key)).then((s) => s.exists());   // 못 읽으면(끊김) 실패로 — '없음' 과 섞지 않는다
  if (await has('allow')) return 'owner';
  if (await has('viewers')) return 'viewer';
  return 'none';
}

// 시험 전용 — 이 컴퓨터 미리보기(127.0.0.1)에서만 된다
export function signInForTest(token) {
  if (location.hostname !== '127.0.0.1') throw new Error('시험 로그인은 127.0.0.1 에서만 됩니다');
  return au.signInWithCustomToken(auth, token);
}

const meta = (snap) => ({ fromCache: snap.metadata.fromCache, pending: snap.metadata.hasPendingWrites });

export function watchEvents(cb, onError) {
  return fs.onSnapshot(fs.collection(db, 'events'), { includeMetadataChanges: true },
    (snap) => cb(snap.docs.map((d) => ({ id: d.id, ev: d.data() })), meta(snap)), onError);
}

export function watchEvent(id, cb, onError) {
  return fs.onSnapshot(fs.doc(db, 'events', id), { includeMetadataChanges: true },
    (snap) => cb(snap.exists() ? snap.data() : null, meta(snap)), onError);
}

// 칸 하나만 고친다 (문서 통째로 덮어쓰지 않음 — 다른 기기가 다른 칸을 동시에 고쳐도 안 지워지게)
export function updateField(id, path, value) {
  return fs.updateDoc(fs.doc(db, 'events', id), { [path]: value, updatedAt: fs.serverTimestamp() });
}

// 담당자 보기 링크의 암호 — 이미 있으면 그대로 돌려주고(덮어쓰지 않음), 없을 때만 새로 만들어 넣는다.
// updatedAt 은 건드리지 않는다(PDF 를 다시 그리고 인쇄한 확정이 '인쇄 전'으로 가는 걸 막는다).
export function ensureViewKey(id, makeKey) {
  const ref = fs.doc(db, 'events', id);
  return fs.runTransaction(db, async (tx) => {
    const have = (await tx.get(ref)).data()?.viewKey;
    if (have) return have;
    const key = makeKey();
    tx.update(ref, { viewKey: key });
    return key;
  });
}

export async function listTemplates() {
  const snap = await fs.getDocs(fs.collection(db, 'templates'));
  return snap.docs.map((d) => ({ name: d.data().name ?? d.id, type: d.data().type, items: d.data().items ?? {}, itemRows: d.data().itemRows ?? 0 }));
}

// extra = 다른 서류에서 옮겨 온 칸 (3단계 — 견적서의 고객 · 날짜 · 장소 · 상차림 · 금액)
export async function createFromTemplate(name, extra = {}) {
  const tpl = (await fs.getDoc(fs.doc(db, 'templates', name))).data();
  const ref = fs.doc(fs.collection(db, 'events'));
  const ev = { ...newEventFromTemplate({ name, type: tpl.type, items: tpl.items, itemRows: tpl.itemRows }), ...extra };
  const saving = fs.setDoc(ref, { ...ev, updatedAt: fs.serverTimestamp() });
  await localSaved(ref);
  if (navigator.onLine) await atMost(saving);   // 끊긴 곳에서는 3초까지만 — 기기에 들고 있다가 연결되면 올라간다
  return ref.id;
}

export async function addImage(id, file) {
  const bmp = await createImageBitmap(file);
  const bytes = fs.Bytes.fromUint8Array(new Uint8Array(await file.arrayBuffer()));
  return fs.addDoc(fs.collection(db, 'events', id, 'images'),
    { order: Date.now(), bytes, width: bmp.width, height: bmp.height });
}

// ---------- 2단계: 웹 서류 5종 (docs) — 서류 한 장을 통째로 (서류 전체 모양 html + 목록 칸) ----------

export function watchDocs(kind, cb, onError) {
  const q = fs.query(fs.collection(db, 'docs'), fs.where('kind', '==', kind));
  return fs.onSnapshot(q, { includeMetadataChanges: true },
    (snap) => cb(snap.docs.map((d) => ({ id: d.id, doc: d.data() })), meta(snap)), onError);
}

export function watchDoc(id, cb, onError) {
  return fs.onSnapshot(fs.doc(db, 'docs', id), { includeMetadataChanges: true },
    (snap) => cb(snap.exists() ? snap.data() : null, meta(snap)), onError);
}

// 같은 종류 서류를 한 번 읽어 최근에 고친 순 n장 — 일일 일정표 '사진으로 채우기' 의 이름 목록용 (2026-11-03).
// 조건은 watchDocs 와 같고 순서는 받은 뒤에 정한다 — kind 와 updatedAt 을 묶은 질의는 저장소에 색인을 따로 만들어야 한다(추정).
// 서버 시각이 아직 없는 방금 만든 서류는 맨 앞(목록의 sortDocs 와 같은 규칙). 끊겼으면 이 기기에 있는 것으로.
export async function recentDocs(kind, n) {
  const snap = await fs.getDocs(fs.query(fs.collection(db, 'docs'), fs.where('kind', '==', kind)));
  const time = (r) => r.doc.updatedAt?.toMillis() ?? Infinity;
  return snap.docs.map((d) => ({ id: d.id, doc: d.data() })).sort((a, b) => time(b) - time(a)).slice(0, n);
}

// 로그인한 사람의 ID 토큰 — 서버 기능(api/read-note)이 이것으로 주인인지 본다. 로그인 안 했으면 실패.
export function idToken() {
  if (!auth?.currentUser) return Promise.reject(new Error('로그인하지 않았습니다'));
  return auth.currentUser.getIdToken();
}

// 서버 확인은 이만큼(ms)까지만 기다린다 — 끊긴 채 연 화면은 navigator.onLine 이 '연결됨'으로 나와서 그것만으로는 못 가린다.
// 그 뒤에는 기기에 들고 있다가 연결되면 올라간다.
export const CONFIRM_WAIT = 3000;
export const atMost = (p, ms = CONFIRM_WAIT) => Promise.race([p, new Promise((ok) => setTimeout(ok, ms))]);

// 방금 쓴 것이 이 기기 저장소에 들어갈 때까지 — 저장소 작업은 차례대로 돌아서, 이 읽기가 끝나면 앞의 쓰기도 기기에 들어가 있다.
// 신호가 아예 없으면(navigator.onLine 거짓) 서버를 안 기다리고 곧장 다음 화면으로 가는데, 그 전에 기기 쓰기가 안 끝나면 새 서류가 사라졌다
// (3단계 최종 검토 I1 — '서류를 찾을 수 없습니다').
const localSaved = (ref) => fs.getDocFromCache(ref).catch(() => {});

export async function createDoc(kind, html, summary) {
  const ref = fs.doc(fs.collection(db, 'docs'));
  const saving = fs.setDoc(ref, { kind, html, ...summary, createdAt: fs.serverTimestamp(), updatedAt: fs.serverTimestamp() });
  await localSaved(ref);
  if (navigator.onLine) await atMost(saving);   // 오프라인이면 기다리지 않는다
  return ref.id;
}

// 고치기만 한다 — 다른 기기에서 지운 서류면 실패한다(다시 만들지 않는다)
export function saveDoc(id, html, summary) {
  return fs.updateDoc(fs.doc(db, 'docs', id), { html, ...summary, updatedAt: fs.serverTimestamp() });
}

export function removeDoc(id) {
  return fs.deleteDoc(fs.doc(db, 'docs', id));
}

// ---------- 직원 게시판 (today.html, 2026-10-21) — 일일 일정표의 사진에 있는 글자를 일정표마다 한 칸씩 ----------
// 게시판 이름(암호)은 config/share 에 있다(사장님만 읽음, tools/sije_web/share_link.py 가 만든다). 없으면 아직 안 만든 것 — 아무것도 안 한다.
// 칸 하나씩 고친다 — 다른 기기가 다른 일정표 칸을 동시에 고쳐도 지워지지 않게. 어제보다 지난 날짜 칸은 같은 고침에서 지운다.
// 올리기 전에 게시판을 읽어, 올라간 것과 at 을 빼고 같으면 쓰지 않는다 — 열기만 해도 at 이 새로 찍혀 직원 모두가 '고친 뒤 안 봄' 이
// 되지 않게 (2026-11-05 직원 확인 설계 3-2). 오타 하나라도 다르면 쓴다(사장님 결정).
let shareKey = null;    // 약속: 암호 또는 null — 못 읽으면(끊김) 다음에 다시 읽는다
const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function readShareKey() {
  if (!shareKey) {
    shareKey = fs.getDoc(fs.doc(db, 'config', 'share')).then((s) => (s.exists() ? s.data().key : null))
      .catch((e) => { shareKey = null; throw e; });
  }
  return shareKey;
}

// 값이 같은지 — 칸(이름표) 순서는 따지지 않고, 줄(목록) 순서는 따진다
function same(a, b) {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => same(x, b[i]));
  }
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  const ka = Object.keys(a);
  return ka.length === Object.keys(b).length && ka.every((k) => k in b && same(a[k], b[k]));
}

export async function publishShare(id, entry) {
  const key = await readShareKey();
  if (!key) return false;
  const ref = fs.doc(db, 'share', key);
  const seen = await fs.getDoc(ref).then((s) => s.data()?.entries || {}, () => ({}));
  const y = new Date();
  y.setDate(y.getDate() - 1);
  const yday = isoDay(y);
  const old = Object.keys(seen).filter((other) => other !== id && typeof seen[other]?.date === 'string' && seen[other].date < yday);
  if (entry && !old.length && seen[id]) {
    const { at, ...have } = seen[id];
    if (same(have, entry)) return true;           // 올라간 것과 같다 — at 을 새로 찍지 않는다
  }
  const args = [new fs.FieldPath('entries', id), entry ? { ...entry, at: fs.serverTimestamp() } : fs.deleteField()];
  for (const other of old) args.push(new fs.FieldPath('entries', other), fs.deleteField());
  await fs.updateDoc(ref, ...args);
  return true;
}

// 직원 확인 (2026-11-05 설계 3-4) — 게시판의 이 일정표 한 장(at · names)과 확인 기록 중 이 일정표 것을 바로 읽어
// cb({ at, names, marks: [{ name, at }] }) (시각은 ms 숫자), 게시판에 그 한 장이 없으면 cb(null). 암호가 없거나 못 읽으면 부르지 않는다.
// 게시판은 서버 시각 대기 중인 at 도 '지금' 으로 친다 — 사장님이 방금 고친 것이 바로 '고친 뒤 안 봄' 으로 보이게.
// 돌려주는 함수를 부르면 끊는다.
export function watchConfirm(id, cb) {
  const stops = [];
  let off = false;
  let entry;   // 약속: 아직 못 받음 = undefined, 없음 = null
  let marks;
  const send = () => { if (entry !== undefined && marks !== undefined) cb(entry && { ...entry, marks }); };
  const ms = (t) => (t ? t.toMillis() : null);
  readShareKey().then((key) => {
    if (!key || off) return;
    stops.push(fs.onSnapshot(fs.doc(db, 'share', key), (snap) => {
      const e = snap.data({ serverTimestamps: 'estimate' })?.entries?.[id];
      entry = e ? { at: ms(e.at), names: e.names || [] } : null;
      send();
    }, () => {}));
    stops.push(fs.onSnapshot(fs.query(fs.collection(db, 'share', key, 'marks'), fs.where('sid', '==', id)), (snap) => {
      marks = snap.docs.map((d) => ({ name: d.data().name, at: ms(d.data().at) }));
      send();
    }, () => {}));
  }, () => {});
  return () => {
    off = true;
    stops.forEach((s) => s());
  };
}

export function watchImages(id, cb) {
  const q = fs.query(fs.collection(db, 'events', id, 'images'), fs.orderBy('order'));
  return fs.onSnapshot(q, (snap) => cb(snap.docs.map((d) => 'data:image/jpeg;base64,' + d.data().bytes.toBase64())));
}
