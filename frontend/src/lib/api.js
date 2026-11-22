// The ONE place the React app talks to the backend. Pages never call fetch() themselves.
//
//   import { api } from '../lib/api';
//   const data = await api.get('/workspace');
//   await api.post('/complaints', { title, description, categoryId, location });
//
// - The base URL comes from VITE_API_BASE_URL (frontend/.env). It is a public address, not a secret.
// - The sign-in token is kept in sessionStorage (cleared when the tab closes) and sent as "Authorization: Bearer ...".
// - Every failure becomes an ApiError with a message that is safe to show to people.

let baseUrl = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:7071/api').replace(/\/$/, '');
const TOKEN_KEY = 'campuscare.token';
let memoryToken = null; // fallback when sessionStorage is unavailable
let onUnauthorized = null;

export const configureApi = ({ baseUrl: url } = {}) => { if (url) baseUrl = url.replace(/\/$/, ''); };
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export function getToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || memoryToken; } catch { return memoryToken; }
}
export function setToken(token) {
  memoryToken = token;
  try { sessionStorage.setItem(TOKEN_KEY, token); } catch { /* memory copy is enough */ }
}
export function clearToken() {
  memoryToken = null;
  try { sessionStorage.removeItem(TOKEN_KEY); } catch { /* nothing to clear */ }
}

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'error', details = {} } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// The most helpful single sentence for a failed request: a field problem if there is one, else the main message.
export function describeError(err) {
  if (err instanceof ApiError) {
    const first = Object.values(err.details || {}).find((v) => typeof v === 'string');
    return first || err.message;
  }
  return 'Something went wrong. Please try again.';
}

async function request(method, path, { json, body, headers } = {}) {
  const h = { ...headers };
  const token = getToken();
  if (token) h.Authorization = `Bearer ${token}`;
  let payload = body;
  if (json !== undefined) {
    h['Content-Type'] = 'application/json';
    payload = JSON.stringify(json);
  }

  let res;
  try {
    res = await fetch(`${baseUrl}${path}`, { method, headers: h, body: payload });
  } catch {
    throw new ApiError('Cannot reach the CampusCare server. Check that the backend is running, then try again.', { status: 0, code: 'network_error' });
  }

  const text = await res.text();
  let data = null;
  if (text) { try { data = JSON.parse(text); } catch { data = null; } }

  if (!res.ok) {
    const e = data?.error || {};
    const isSignIn = path.startsWith('/auth/login') || path.startsWith('/auth/register');
    if (res.status === 401 && token && !isSignIn) {
      clearToken();
      if (onUnauthorized) onUnauthorized();
    }
    throw new ApiError(e.message || `The server returned an error (${res.status}).`, { status: res.status, code: e.code || 'http_error', details: e.details || {} });
  }
  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, json) => request('POST', path, { json: json ?? {} }),
  put: (path, json) => request('PUT', path, { json }),
  del: (path) => request('DELETE', path),
  // Sends the file itself as the request body (the backend stores it in Azure Blob Storage).
  upload: (path, file) => request('POST', `${path}?name=${encodeURIComponent(file.name || 'file')}`, { body: file, headers: { 'Content-Type': file.type } }),
};
