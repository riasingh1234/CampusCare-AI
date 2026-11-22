// The app's data layer. It keeps the same shape the screens already use ({ db, maps, user, ...actions}),
// but the data now comes from the Azure Functions backend (Azure SQL) through lib/api.js.
// Every action returns { ok: true, ... } or { ok: false, error, details } so screens never need try/catch.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearToken, describeError, getToken, setToken, setUnauthorizedHandler } from '../lib/api';
import { buildMaps, normalizeWorkspace } from '../lib/normalize';
import { isEmail, validatePassword } from '../lib/validation';
import { PageLoader } from '../components/ui/feedback';

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

const EMPTY_DB = { users: [], departments: [], categories: [], complaints: [], history: [], feedback: [] };
const clean = (s) => s.trim().replace(/\s+/g, ' ');

const toUser = (u) => ({ ...u, id: String(u.id), departmentId: u.departmentId == null ? null : String(u.departmentId) });

// Runs an API call and turns any failure into { ok: false, error, details }.
async function attempt(fn) {
  try {
    return { ok: true, ...(await fn()) };
  } catch (err) {
    return { ok: false, error: describeError(err), details: err?.details || {} };
  }
}

export function AppProvider({ children }) {
  const [db, setDb] = useState(EMPTY_DB);
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(!!getToken());
  const [bootError, setBootError] = useState('');

  const loadWorkspace = useCallback(async () => {
    setDb(normalizeWorkspace(await api.get('/workspace')));
  }, []);

  // Reloads data after a change. A failed reload must not hide that the change itself worked.
  const refresh = useCallback(async () => {
    try { await loadWorkspace(); return true; } catch { return false; }
  }, [loadWorkspace]);

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
    setDb(EMPTY_DB);
  }, []);

  useEffect(() => { setUnauthorizedHandler(signOut); }, [signOut]);

  const boot = useCallback(async () => {
    if (!getToken()) { setBooting(false); return; }
    setBooting(true);
    setBootError('');
    try {
      const me = await api.get('/auth/me');
      await loadWorkspace();
      setUser(toUser(me.user));
    } catch (err) {
      if (err.status === 401) signOut(); // token expired or invalid: show the sign-in page
      else setBootError(describeError(err));
    } finally {
      setBooting(false);
    }
  }, [loadWorkspace, signOut]);

  useEffect(() => { boot(); }, [boot]);

  const maps = useMemo(() => buildMaps(db), [db]);

  const actions = useMemo(() => {
    const startSession = async (session) => {
      setToken(session.token);
      await loadWorkspace();
      const u = toUser(session.user);
      setUser(u);
      return { user: u };
    };
    const changed = async (result) => { await refresh(); return result; };

    return {
      // ---------------------------------------------------------------- account
      login: (email, password) => attempt(async () => startSession(await api.post('/auth/login', { email: email.trim(), password }))),
      register: ({ name, email, password, enrollmentId }) => {
        const e = email.trim().toLowerCase();
        if (clean(name).length < 2) return { ok: false, error: 'Enter your full name.' };
        if (!isEmail(e)) return { ok: false, error: 'Enter a valid email address.' };
        const pwError = validatePassword(password);
        if (pwError) return { ok: false, error: pwError };
        return attempt(async () => startSession(await api.post('/auth/register', { name: clean(name), email: e, password, enrollmentId: clean(enrollmentId || '') })));
      },
      logout: signOut,

      // ------------------------------------------------------------- complaints
      // form.files is a list of { file }. The complaint is saved first, then each file is uploaded to Blob Storage.
      submitComplaint: (form) => attempt(async () => {
        const created = await api.post('/complaints', {
          title: form.title, description: form.description, categoryId: form.categoryId, location: form.location,
        });
        let uploadFailures = 0;
        for (const item of form.files || []) {
          try { await api.upload(`/complaints/${created.id}/attachments`, item.file); } catch { uploadFailures += 1; }
        }
        return changed({ id: created.id, uploadFailures });
      }),
      assignComplaint: (id, { departmentId, staffId, priority }) =>
        attempt(async () => changed(await api.post(`/complaints/${id}/assign`, { departmentId, staffId, priority }))),
      updateStatus: (id, status, note) =>
        attempt(async () => changed(await api.post(`/complaints/${id}/status`, { status, note }))),
      addFeedback: (id, { rating, comment }) =>
        attempt(async () => changed(await api.post(`/complaints/${id}/feedback`, { rating, comment }))),

      // ------------------------------------------------------------------ admin
      runEscalation: () => attempt(async () => changed({ result: await api.post('/admin/escalation/run') })),
      saveDepartment: ({ id, name }) => attempt(async () => changed(id
        ? await api.put(`/admin/departments/${id}`, { name })
        : await api.post('/admin/departments', { name }))),
      deleteDepartment: (id) => attempt(async () => changed(await api.del(`/admin/departments/${id}`))),
      saveCategory: ({ id, name, departmentId, defaultPriority, keywords }) => {
        const body = { name, departmentId, defaultPriority, keywords };
        return attempt(async () => changed(id ? await api.put(`/admin/categories/${id}`, body) : await api.post('/admin/categories', body)));
      },
      deleteCategory: (id) => attempt(async () => changed(await api.del(`/admin/categories/${id}`))),
    };
  }, [loadWorkspace, refresh, signOut]);

  if (booting) return <PageLoader />;
  if (bootError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-md rounded-xl bg-white p-8 text-center ring-1 ring-navy-100">
          <h1 className="text-xl font-extrabold text-navy-900">Cannot load CampusCare</h1>
          <p className="mt-2 text-sm text-navy-500">{bootError}</p>
          <button onClick={boot} className="mt-5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700">Try again</button>
        </div>
      </div>
    );
  }
  return <Ctx.Provider value={{ db, maps, user, ...actions }}>{children}</Ctx.Provider>;
}
