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

/*
  What a failure says out loud. The backend speaks three dialects: a plain `detail` sentence
  written for a person, a pydantic validation array, and rate-limit and crash bodies that carry
  no `detail` at all. Only the first is fit to show, so the rest are translated here rather
  than surfacing "The server responded 500." or "String should have at most 500 characters".
*/
const BY_STATUS = {
  429: "That's a lot of requests in one minute. Give it a moment and try again.",
  500: 'Something broke on my side. Try that again.',
  502: "I can't reach my own services right now. Try again in a moment.",
  503: 'One of my services is unavailable right now. Try again in a moment.',
  504: 'That took too long. Try again in a moment.',
};

function readable(status, details) {
  const detail = details?.detail;
  if (typeof detail === 'string') return detail; // written for a person already
  if (Array.isArray(detail) && detail[0]?.msg) {
    const msg = String(detail[0].msg);
    if (/at most \d+ characters/.test(msg)) return 'That request is too long. Keep it under 500 characters.';
    if (/at least 1 character/.test(msg)) return "Tell me what you'd like to eat.";
    return "I couldn't read that request.";
  }
  return BY_STATUS[status] || 'Something went wrong. Try that again.';
}

async function handle(resp) {
  if (!resp.ok) {
    let details = {};
    try {
      details = await resp.json();
    } catch (e) {
      /* a non-JSON error body is fine; the status still tells us enough */
    }
    throw new ApiError(readable(resp.status, details), resp.status, details);
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
