import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/layout/AuthLayout';
import { Button, Field, Input } from '../components/ui/primitives';
import { useApp } from '../store/AppContext';
import { isEmail, validatePassword } from '../lib/validation';

export default function Register() {
  const { register } = useApp();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', enrollmentId: '', password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const err = {};
    if (form.name.trim().length < 2) err.name = 'Enter your full name.';
    if (!isEmail(form.email)) err.email = 'Enter a valid email address.';
    const pw = validatePassword(form.password);
    if (pw) err.password = pw;
    if (form.confirm !== form.password) err.confirm = 'Passwords do not match.';
    setErrors(err);
    if (Object.keys(err).length) return;
    setBusy(true);
    const res = await register(form);
    setBusy(false);
    if (!res.ok) return setErrors({ form: res.error });
    navigate('/student', { replace: true });
  };

  return (
    <AuthLayout>
      <h1 className="text-3xl font-extrabold text-navy-900">Create your account</h1>
      <p className="mt-2 text-sm text-navy-500">Student accounts can report issues and track them. Staff and admin accounts are created by the college.</p>
      <form className="mt-8 space-y-4" onSubmit={submit} noValidate>
        <Field label="Full name" htmlFor="name" error={errors.name} required>
          <Input id="name" autoComplete="name" invalid={!!errors.name} value={form.name} onChange={set('name')} />
        </Field>
        <Field label="College email" htmlFor="email" error={errors.email} required>
          <Input id="email" type="email" autoComplete="email" invalid={!!errors.email} value={form.email} onChange={set('email')} />
        </Field>
        <Field label="Enrollment ID" htmlFor="enroll" hint="Optional">
          <Input id="enroll" value={form.enrollmentId} onChange={set('enrollmentId')} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Password" htmlFor="pw" error={errors.password} hint="8+ characters, with a letter and a number" required>
            <Input id="pw" type="password" autoComplete="new-password" invalid={!!errors.password} value={form.password} onChange={set('password')} />
          </Field>
          <Field label="Confirm password" htmlFor="cpw" error={errors.confirm} required>
            <Input id="cpw" type="password" autoComplete="new-password" invalid={!!errors.confirm} value={form.confirm} onChange={set('confirm')} />
          </Field>
        </div>
        {errors.form && <p className="rounded-lg bg-red-50 px-3 py-2.5 text-sm font-medium text-red-700" role="alert">{errors.form}</p>}
        <Button type="submit" size="lg" className="w-full" loading={busy}>Create account</Button>
      </form>
      <p className="mt-6 text-center text-sm text-navy-500">Already registered? <Link to="/login" className="font-bold text-brand-700 hover:underline">Sign in</Link></p>
    </AuthLayout>
  );
}
