import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, GraduationCap, Wrench, ShieldCheck } from 'lucide-react';
import AuthLayout from '../components/layout/AuthLayout';
import { Button, Field, Input } from '../components/ui/primitives';
import { useApp } from '../store/AppContext';
import { DEMO_ACCOUNTS } from '../data/seed';
import { ROLE_HOME } from '../lib/constants';
import { isEmail } from '../lib/validation';

const ICONS = { student: GraduationCap, staff: Wrench, admin: ShieldCheck };

export default function Login() {
  const { login } = useApp();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const attempt = async (email, password) => {
    setError('');
    if (!isEmail(email)) return setError('Enter a valid email address.');
    if (!password) return setError('Enter your password.');
    setBusy(true);
    const res = await login(email, password);
    setBusy(false);
    if (!res.ok) return setError(res.error);
    navigate(ROLE_HOME[res.user.role], { replace: true });
  };

  return (
    <AuthLayout>
      <h1 className="text-3xl font-extrabold text-navy-900">Sign in</h1>
      <p className="mt-2 text-sm text-navy-500">Use your campus account to report or manage maintenance issues.</p>

      <form className="mt-8 space-y-5" onSubmit={(e) => { e.preventDefault(); attempt(form.email, form.password); }} noValidate>
        <Field label="Email" htmlFor="email">
          <Input id="email" type="email" autoComplete="email" placeholder="you@college.edu" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Password" htmlFor="password">
          <div className="relative">
            <Input id="password" type={show ? 'text' : 'password'} autoComplete="current-password" className="pr-11" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-navy-400 hover:text-navy-700">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </Field>
        {error && <p className="rounded-lg bg-red-50 px-3 py-2.5 text-sm font-medium text-red-700" role="alert">{error}</p>}
        <Button type="submit" size="lg" className="w-full" loading={busy}>Sign in</Button>
      </form>

      <p className="mt-6 text-center text-sm text-navy-500">New student? <Link to="/register" className="font-bold text-brand-700 hover:underline">Create an account</Link></p>

      <div className="mt-8 rounded-xl bg-navy-50 p-4">
        <p className="text-[13px] font-bold text-navy-800">Try a demo account</p>
        <p className="mb-3 text-[13px] text-navy-500">Fills in the email. Type the demo password you chose when setting up the database.</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {DEMO_ACCOUNTS.map((a) => {
            const Icon = ICONS[a.role];
            return (
              <button key={a.role} type="button" disabled={busy} onClick={() => { setForm({ email: a.email, password: '' }); setError(''); document.getElementById('password')?.focus(); }}
                className="flex items-center gap-2 rounded-lg bg-white px-3 py-2.5 text-left text-[13px] font-semibold text-navy-800 ring-1 ring-navy-200 transition-colors hover:ring-brand-400 disabled:opacity-50">
                <Icon className="h-4 w-4 shrink-0 text-brand-600" />{a.label}
              </button>
            );
          })}
        </div>
      </div>
    </AuthLayout>
  );
}
