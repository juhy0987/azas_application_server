// ── 인증 상태 관리 모듈 ──────────────────────────────────────────────────────
//
// JWT (Bearer token) 기반.
// 토큰은 localStorage 에 보관하여 새로고침 후에도 로그인 세션 유지.
// 인증 상태 변경 시 구독자(subscriber)에게 알린다.
// Ref: Observer 패턴 — https://refactoring.guru/design-patterns/observer

const TOKEN_KEY = "auth.access_token";

/** @type {{ authenticated: boolean, username: string | null }} */
let _authState = { authenticated: false, username: null };

/** @type {Set<(state: typeof _authState) => void>} */
const _subscribers = new Set();

/** 현재 인증 상태를 반환한다 (읽기 전용 복사본). */
export function getAuthState() {
  return { ..._authState };
}

/** 현재 보관 중인 JWT access token (없으면 null). */
export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function _setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // localStorage 접근 불가 환경 — 메모리만으로 동작 (새로고침시 세션 손실)
  }
}

/** 인증 상태가 변경될 때 호출될 콜백을 등록한다. */
export function onAuthChange(callback) {
  _subscribers.add(callback);
  return () => _subscribers.delete(callback);
}

function _notify() {
  const snapshot = { ..._authState };
  _subscribers.forEach((cb) => cb(snapshot));
}

/** 서버에서 현재 인증 상태를 조회한다 (앱 초기화 시 호출). */
export async function fetchAuthStatus() {
  const token = getToken();
  if (!token) {
    _authState = { authenticated: false, username: null };
    _notify();
    return;
  }
  try {
    const res = await fetch("/api/auth/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      // 만료/무효 토큰 — 정리
      _setToken(null);
      _authState = { authenticated: false, username: null };
      _notify();
      return;
    }
    const data = await res.json();
    if (!data.authenticated) {
      _setToken(null);
    }
    _authState = {
      authenticated: data.authenticated,
      username: data.username ?? null,
    };
    _notify();
  } catch {
    // 네트워크 오류 시 미인증 상태 유지
  }
}

/** 로그인 요청을 보낸다. 성공 시 true, 실패 시 에러 메시지 문자열을 반환한다. */
export async function login(username, password) {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    return err.detail ?? "로그인에 실패했습니다.";
  }
  const data = await res.json();
  _setToken(data.access_token);
  _authState = { authenticated: true, username: data.username };
  _notify();
  return true;
}

/** 로그아웃 요청을 보낸다. */
export async function logout() {
  const token = getToken();
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    // 네트워크 오류여도 로컬 토큰은 폐기
  }
  _setToken(null);
  _authState = { authenticated: false, username: null };
  _notify();
}

/**
 * 인증이 필요한 API 응답(401/403)을 처리하는 헬퍼.
 * 기존 api.js의 fetch 래퍼에서 쓰기 실패 시 사용자에게 안내한다.
 */
export function isPermissionError(res) {
  return res.status === 401 || res.status === 403;
}
