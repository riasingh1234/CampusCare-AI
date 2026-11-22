import { Link } from 'react-router-dom';
import { Loader2, Star } from 'lucide-react';
import { Card, Skeleton, cx } from './primitives';

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-extrabold text-navy-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-navy-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

const TONES = {
  brand: 'bg-brand-50 text-brand-600', navy: 'bg-navy-100 text-navy-700', amber: 'bg-amber-50 text-amber-600',
  red: 'bg-red-50 text-red-600', emerald: 'bg-emerald-50 text-emerald-600',
};

export function StatCard({ label, value, hint, icon: Icon, tone = 'brand', loading, to }) {
  const body = (
    <Card className={cx('h-full p-5 transition-colors', to && 'hover:bg-navy-50/60')}>
      <div className="flex items-start justify-between">
        <p className="text-[13px] font-semibold text-navy-500">{label}</p>
        {Icon && <span className={cx('flex h-9 w-9 items-center justify-center rounded-lg', TONES[tone])}><Icon className="h-[18px] w-[18px]" /></span>}
      </div>
      {loading ? <Skeleton className="mt-3 h-8 w-16" /> : <p className="mt-2 text-3xl font-extrabold text-navy-900">{value}</p>}
      {hint && !loading && <p className="mt-1 text-[13px] text-navy-400">{hint}</p>}
    </Card>
  );
  return to ? <Link to={to} className="block h-full rounded-xl">{body}</Link> : body;
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      {Icon && <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-navy-100 text-navy-500"><Icon className="h-6 w-6" /></span>}
      <h3 className="text-base font-bold text-navy-900">{title}</h3>
      {description && <p className="mt-1 max-w-sm text-sm text-navy-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-3 p-5">
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
    </div>
  );
}

export const PageLoader = () => (
  <div className="flex min-h-screen items-center justify-center bg-[#F8FAFD]">
    <Loader2 className="h-6 w-6 animate-spin text-brand-600" aria-label="Loading" />
  </div>
);

export function StarRating({ value = 0, onChange, size = 'h-6 w-6' }) {
  return (
    <div className="flex gap-1" role={onChange ? 'radiogroup' : 'img'} aria-label={`${value} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((n) => {
        const star = <Star className={cx(size, n <= value ? 'fill-amber-400 text-amber-400' : 'text-navy-200')} />;
        return onChange ? (
          <button key={n} type="button" role="radio" aria-checked={n === value} aria-label={`${n} star${n > 1 ? 's' : ''}`} onClick={() => onChange(n)} className="rounded p-0.5">{star}</button>
        ) : <span key={n}>{star}</span>;
      })}
    </div>
  );
}
