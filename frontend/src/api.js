/* The backend, in one place. Cookies carry the session and the sign-in. */

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

const BASE = '';

async function handle(resp) {
  if (!resp.ok) {
    let details = {};
    try {
      details = await resp.json();
    } catch (e) {
      /* a non-JSON error body is fine; the status still tells us enough */
    }
    const detail = details.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail) && detail[0]?.msg
          ? detail[0].msg
          : `The server responded ${resp.status}.`;
    throw new ApiError(message, resp.status, details);
  }
  return resp.json();
}

function get(path) {
  return fetch(`${BASE}${path}`, { credentials: 'include' }).then(handle);
}

function send(path, body, method = 'POST') {
  return fetch(`${BASE}${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  }).then(handle);
}

// ── The conversation ────────────────────────────────────────────────────────
/** One turn: exactly one of text, answer, critique or skip, plus an optional location. */
export const chat = (turn) => send('/chat', turn);
export const approve = (dishId) => send('/approve', { dish_id: dishId });
export const alternate = (rejected) => send('/alternate', { already_rejected: rejected });

// ── Places ──────────────────────────────────────────────────────────────────
export const areas = () => get('/areas');

/** The browser's location, or null if the user says no or it takes too long. */
export function locate(timeout = 8000) {
  if (!navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: 'Where you are' }),
      () => resolve(null),
      { timeout },
    );
  });
}

// ── Account ─────────────────────────────────────────────────────────────────
export const me = () => get('/auth/me');
export const login = (email, password) => send('/auth/login', { email, password });
export const register = (body) => send('/auth/register', body);
export const logout = (everywhere = false) => send(`/auth/logout?everywhere=${everywhere}`);
export const personas = () => get('/personas');

// ── Profile ─────────────────────────────────────────────────────────────────
export const profile = () => get('/profile');
export const setDietary = (body) => send('/profile/dietary', body, 'PUT');
export const setGoals = (body) => send('/profile/goals', body, 'PUT');
export const setTaste = (values) => send('/profile/taste', { values }, 'PUT');
export const setWeights = (body) => send('/profile/weights', body, 'PUT');
export const resetTaste = (persona) => send('/profile/taste/reset', { persona: persona ?? null });
export const learning = () => get('/profile/learning');
export const history = (limit = 50) => get(`/profile/history?limit=${limit}`);
export const similarTastes = (k = 5) => get(`/profile/similar-tastes?k=${k}`);
export const deleteAccount = (password) => send('/profile/delete', { password });
export const exportUrl = `${BASE}/profile/export`;
