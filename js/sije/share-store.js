// 직원 화면(today.html) 저장소 — 로그인 없이 직원 게시판 한 장만 읽는다 (2026-10-21).
// 로그인 부품은 받지 않는다(산속 약한 신호에서 가볍게). 연결 정보는 firebase-config.js 한 곳 — 127.0.0.1 · localhost 는 시험용.
// 한 번 본 게시판은 기기에 남겨 둬서(오프라인 저장) 신호가 없어도 마지막으로 받은 것을 보여 준다.
// 2026-11-05 부터 직원 '확인' 기록(share/{암호}/marks)은 적는다 — 설계 docs/superpowers/specs/2026-11-04-staff-confirm-design.md 3-3.
import { SDK, projectConfig } from './firebase-config.js';

const CDN = `https://www.gstatic.com/firebasejs/${SDK}`;
const [{ initializeApp }, fs] = await Promise.all([
  import(`${CDN}/firebase-app.js`),
  import(`${CDN}/firebase-firestore.js`),
]);

let db;

function openDb() {
  if (!db) {
    db = fs.initializeFirestore(initializeApp(projectConfig(location.hostname)), {
      localCache: fs.persistentLocalCache({ tabManager: fs.persistentMultipleTabManager() }),
    });
  }
  return db;
}

// cb(entries | null, { fromCache }) — 게시판이 없으면 null (바뀐 옛 링크 · 틀린 링크)
export function watchShare(key, cb, onError) {
  return fs.onSnapshot(fs.doc(openDb(), 'share', key), { includeMetadataChanges: true },
    (snap) => cb(snap.exists() ? (snap.data().entries || {}) : null, { fromCache: snap.metadata.fromCache }), onError);
}

// 직원 '확인' 한 번 — 문서 이름은 일정표id~이름, 시각은 서버 시각(규칙이 휴대폰 시각을 막는다).
// 끊겨 있으면 기기에 들고 있다가 연결되면 올린다(그동안 promise 는 기다린다). 규칙이 거절하면 promise 가 실패한다
export function confirmMark(key, sid, name) {
  return fs.setDoc(fs.doc(openDb(), 'share', key, 'marks', `${sid}~${name}`), { sid, name, at: fs.serverTimestamp() });
}

// cb([{ sid, name, at, pending }]) — 그 게시판의 확인 기록 전부. at 은 ms 숫자, 아직 서버에 안 간 기록은 at null · pending true
export function watchMarks(key, cb, onError) {
  return fs.onSnapshot(fs.collection(openDb(), 'share', key, 'marks'), { includeMetadataChanges: true },
    (snap) => cb(snap.docs.map((d) => {
      const m = d.data();
      return { sid: m.sid, name: m.name, at: typeof m.at?.toMillis === 'function' ? m.at.toMillis() : null,
               pending: d.metadata.hasPendingWrites };
    })), onError);
}

// 담당자 화면(sije-view.html) - 담당자 보기 한 장 staffSheets/{암호}. cb(sheet | null, { fromCache }) - 없으면 null (지난 행사 · 틀린 링크)
export function watchSheet(key, cb, onError) {
  return fs.onSnapshot(fs.doc(openDb(), 'staffSheets', key), { includeMetadataChanges: true },
    (snap) => cb(snap.exists() ? snap.data() : null, { fromCache: snap.metadata.fromCache }), onError);
}
