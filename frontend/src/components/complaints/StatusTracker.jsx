import { Check } from 'lucide-react';
import { STATUSES } from '../../lib/constants';
import { fmtDateTime } from '../../lib/format';

// The parcel-style tracker: each stage lights up with the time it was reached.
export default function StatusTracker({ status, history }) {
  const current = STATUSES.indexOf(status);
  return (
    <ol className="grid grid-cols-4 gap-2" aria-label="Complaint progress">
      {STATUSES.map((s, i) => {
        const reached = i <= current;
        const entry = [...history].reverse().find((h) => h.status === s);
        return (
          <li key={s} className="relative text-center" aria-current={i === current ? 'step' : undefined}>
            {i > 0 && <span className={`absolute right-1/2 top-4 h-0.5 w-full ${reached ? 'bg-brand-600' : 'bg-navy-100'}`} aria-hidden />}
            <span className={`relative mx-auto flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
              i < current || (i === current && s === 'Resolved') ? 'bg-brand-600 text-white'
                : i === current ? 'bg-white text-brand-700 ring-2 ring-brand-600' : 'bg-navy-100 text-navy-400'}`}>
              {i < current || (i === current && s === 'Resolved') ? <Check className="h-4 w-4" /> : i + 1}
            </span>
            <p className={`mt-2 text-[13px] font-bold ${reached ? 'text-navy-900' : 'text-navy-300'}`}>{s}</p>
            <p className="text-xs text-navy-400">{reached && entry ? fmtDateTime(entry.at) : '\u00A0'}</p>
          </li>
        );
      })}
    </ol>
  );
}
