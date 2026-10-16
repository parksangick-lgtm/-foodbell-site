// 시제행사 내역서 — 파이어베이스 연결 정보.
// 이 값들은 공개돼도 되는 값이다. 저장소를 지키는 것은 firestore.rules(허락 목록)다.
// SDK 판은 여기 한 곳에만 적는다 — 모든 import 가 이 값을 쓴다.
export const SDK = '12.19.0';

// 실제: 로그인 창이 foodbell.kr/__/ 로 열리게 authDomain 을 사이트 주소로 둔다 (vercel.json 이 firebaseapp.com 으로 넘김).
const PROD = {
  apiKey: 'AIzaSyDBTcnMOrLIBlUBKOjDPNeDHa6BVd-NkXg',
  authDomain: 'foodbell.kr',
  projectId: 'foodbell-sije',
  appId: '1:1055436300094:web:98b9e070b3e24bf681566f',
};

// 시험: 이 컴퓨터 미리보기(127.0.0.1 · localhost)에서만 쓴다. 가짜 자료만 들어 있다.
const TEST = {
  apiKey: 'AIzaSyAM83fxX07d8PL2yCM8jRWep_YZ34novjk',
  authDomain: 'foodbell-sije-test.firebaseapp.com',
  projectId: 'foodbell-sije-test',
  appId: '1:979078744745:web:77a3c42158051c0220b7b8',
};

export function projectConfig(hostname) {
  return hostname === '127.0.0.1' || hostname === 'localhost' ? TEST : PROD;
}
