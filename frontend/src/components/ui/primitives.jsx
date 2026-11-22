import { forwardRef, useEffect } from 'react';
import { Loader2, X } from 'lucide-react';

export const cx = (...a) => a.filter(Boolean).join(' ');

const VARIANTS = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700',
  navy: 'bg-navy-900 text-white hover:bg-navy-700',
  secondary: 'bg-white text-navy-800 ring-1 ring-inset ring-navy-200 hover:bg-navy-50',
  ghost: 'text-navy-600 hover:bg-navy-100',
  danger: 'bg-red-600 text-white hover:bg-red-700',
};
const SIZES = { sm: 'h-8 px-3 text-[13px] gap-1.5', md: 'h-10 px-4 text-sm gap-2', lg: 'h-11 px-5 text-sm gap-2' };

export function Button({ variant = 'primary', size = 'md', loading = false, icon: Icon, className, children, disabled, ...rest }) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cx('inline-flex shrink-0 items-center justify-center rounded-lg font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50', VARIANTS[variant], SIZES[size], className)}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function Card({ className, children, ...rest }) {
  return <div className={cx('rounded-xl bg-white shadow-card', className)} {...rest}>{children}</div>;
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-navy-100 px-5 py-4">
      <div className="min-w-0">
        <h2 className="text-[15px] font-bold text-navy-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-[13px] text-navy-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function Field({ label, hint, error, htmlFor, required, children }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-[13px] font-semibold text-navy-700">
        {label}{required && <span className="text-red-500"> *</span>}
      </label>
      {children}
      {error ? <p className="mt-1.5 text-[13px] font-medium text-red-600" role="alert">{error}</p>
        : hint && <p className="mt-1.5 text-[13px] text-navy-400">{hint}</p>}
    </div>
  );
}

const base = 'w-full rounded-lg border-0 bg-white px-3 text-sm text-navy-900 ring-1 ring-inset placeholder:text-navy-300 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:bg-navy-50 disabled:text-navy-400';
export const Input = forwardRef(function Input({ invalid, className, ...p }, ref) {
  return <input ref={ref} aria-invalid={invalid || undefined} className={cx(base, 'h-10', invalid ? 'ring-red-400' : 'ring-navy-200', className)} {...p} />;
});
export const Select = forwardRef(function Select({ invalid, className, children, ...p }, ref) {
  return <select ref={ref} aria-invalid={invalid || undefined} className={cx(base, 'h-10 pr-8', invalid ? 'ring-red-400' : 'ring-navy-200', className)} {...p}>{children}</select>;
});
export const Textarea = forwardRef(function Textarea({ invalid, className, ...p }, ref) {
  return <textarea ref={ref} aria-invalid={invalid || undefined} className={cx(base, 'py-2.5 leading-relaxed', invalid ? 'ring-red-400' : 'ring-navy-200', className)} {...p} />;
});

export function Modal({ open, onClose, title, children, footer }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-900/40 p-4 sm:items-center" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className="w-full max-w-lg rounded-2xl bg-white shadow-pop" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-navy-100 px-5 py-4">
          <h2 className="text-base font-bold text-navy-900">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-navy-400 hover:bg-navy-100 hover:text-navy-700"><X className="h-5 w-5" /></button>
        </div>
        <div className="space-y-4 px-5 py-5">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-navy-100 px-5 py-4">{footer}</div>}
      </div>
    </div>
  );
}

export const Skeleton = ({ className }) => <div className={cx('animate-pulse rounded-md bg-navy-100', className)} />;
