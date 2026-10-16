// 시제행사 내역서 — 파이어베이스 저장소(Firestore) · 구글 로그인 감싸기.
// 화면 코드는 이 파일만 부르고 파이어베이스를 직접 부르지 않는다.
// 오프라인 저장을 켜 둔다: 열어 본 적 있는 행사는 인터넷 없이도 열리고, 고친 것은 연결되면 올라간다.
import { SDK, projectConfig } from './firebase-config.js';
import { newEventFromTemplate } from './model.js';

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

export async function listTemplates() {
  const snap = await fs.getDocs(fs.collection(db, 'templates'));
  return snap.docs.map((d) => ({ name: d.data().name ?? d.id, items: d.data().items ?? {}, itemRows: d.data().itemRows ?? 0 }));
}

export async function createFromTemplate(name) {
  const tpl = (await fs.getDoc(fs.doc(db, 'templates', name))).data();
  const ref = fs.doc(fs.collection(db, 'events'));
  const ev = newEventFromTemplate({ name, items: tpl.items, itemRows: tpl.itemRows });
  const saving = fs.setDoc(ref, { ...ev, updatedAt: fs.serverTimestamp() });
  if (navigator.onLine) await saving;   // 오프라인이면 기다리지 않는다 — 기기에 들고 있다가 연결되면 올라간다
  return ref.id;
}

export async function addImage(id, file) {
  const bmp = await createImageBitmap(file);
  const bytes = fs.Bytes.fromUint8Array(new Uint8Array(await file.arrayBuffer()));
  return fs.addDoc(fs.collection(db, 'events', id, 'images'),
    { order: Date.now(), bytes, width: bmp.width, height: bmp.height });
}

export function watchImages(id, cb) {
  const q = fs.query(fs.collection(db, 'events', id, 'images'), fs.orderBy('order'));
  return fs.onSnapshot(q, (snap) => cb(snap.docs.map((d) => 'data:image/jpeg;base64,' + d.data().bytes.toBase64())));
}
