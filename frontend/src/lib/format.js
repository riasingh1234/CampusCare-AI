import { SLA_HOURS, CRITICAL_FLAG_HOURS } from './constants';

export const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
export const fmtDateTime = (iso) =>
  new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

export function timeAgo(iso) {
  const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return d < 30 ? `${d}d ago` : fmtDate(iso);
}

export const initials = (name = '') =>
  name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('');

export const dueAt = (c) => new Date(new Date(c.createdAt).getTime() + SLA_HOURS[c.priority] * 36e5);
export const isOpen = (c) => c.status !== 'Resolved';
export const isOverdue = (c, now = Date.now()) => isOpen(c) && now > dueAt(c).getTime();
export const isCriticalFlagged = (c, now = Date.now()) =>
  isOpen(c) && c.priority === 'Critical' && now - new Date(c.createdAt).getTime() > CRITICAL_FLAG_HOURS * 36e5;

export function duration(hours) {
  if (hours == null) return '–';
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`;
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}
export const overdueBy = (c, now = Date.now()) => duration((now - dueAt(c).getTime()) / 36e5);
