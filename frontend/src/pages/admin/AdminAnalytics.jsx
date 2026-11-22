import { useCallback, useEffect, useState } from 'react';
import { CheckCheck, Clock, ShieldCheck, Star } from 'lucide-react';
import { api, describeError } from '../../lib/api';
import { Button, Card, CardHeader, Skeleton } from '../../components/ui/primitives';
import { PageHeader, StatCard } from '../../components/ui/feedback';
import { ColumnChart, DonutChart, HBarChart, PRIORITY_COLORS, STATUS_COLORS, TrendChart } from '../../components/ui/charts';
import { duration } from '../../lib/format';

const dash = (v, suffix = '') => (v == null ? '–' : `${v}${suffix}`);

export default function AdminAnalytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const loading = !data && !error;

  // Numbers are counted on the server from Azure SQL. tz lets "per day" follow the admin's own time zone.
  const load = useCallback(async () => {
    setError('');
    try { setData(await api.get(`/admin/analytics?tz=${-new Date().getTimezoneOffset()}`)); }
    catch (err) { setError(describeError(err)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const s = data?.summary || {};
  const a = {
    trend: data?.trend || [],
    status: (data?.byStatus || []).filter((d) => d.value),
    priority: data?.byPriority || [],
    category: data?.byCategory || [],
    depts: data?.departments || [],
  };

  const chart = (node, h = 'h-[260px]') => (loading ? <Skeleton className={`${h} w-full`} /> : node);

  return (
    <>
      <PageHeader title="Analytics" subtitle="Live numbers from Azure SQL: volume, speed and satisfaction across campus." />
      {error && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm font-medium text-red-700" role="alert">
          <span>{error}</span><Button size="sm" variant="secondary" onClick={load}>Try again</Button>
        </div>
      )}
      <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Total complaints" value={s.total ?? 0} icon={CheckCheck} tone="navy" loading={loading} />
        <StatCard label="Pending (open)" value={s.open ?? 0} icon={Clock} tone="brand" loading={loading} />
        <StatCard label="Resolved" value={s.resolved ?? 0} icon={ShieldCheck} tone="emerald" loading={loading} />
        <StatCard label="Overdue" value={s.overdue ?? 0} icon={Clock} tone="red" loading={loading} />
        <StatCard label="Escalated" value={s.escalated ?? 0} icon={Star} tone="amber" loading={loading} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Resolution rate" value={`${s.resolvedPct ?? 0}%`} icon={CheckCheck} tone="emerald" loading={loading} />
        <StatCard label="Average time to resolve" value={duration(s.avgHours)} icon={Clock} tone="brand" loading={loading} />
        <StatCard label="Resolved within target" value={dash(s.sla, '%')} icon={ShieldCheck} tone="navy" loading={loading} />
        <StatCard label="Average rating" value={s.rating == null ? '–' : s.rating.toFixed(1)} hint="Out of 5" icon={Star} tone="amber" loading={loading} />
      </div>

      <Card className="mt-6">
        <CardHeader title="Complaint volume, last 30 days" />
        <div className="p-5">{chart(<TrendChart data={a.trend} height={280} />, 'h-[280px]')}</div>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card><CardHeader title="By category" /><div className="p-5">{chart(<HBarChart data={a.category} />)}</div></Card>
        <Card><CardHeader title="By status" /><div className="p-5">{chart(<DonutChart data={a.status} colors={STATUS_COLORS} height={260} />)}</div></Card>
        <Card><CardHeader title="By priority" /><div className="p-5">{chart(<ColumnChart data={a.priority} colors={PRIORITY_COLORS} />)}</div></Card>
        <Card>
          <CardHeader title="Average hours to resolve" subtitle="By department, resolved complaints only." />
          <div className="p-5">{chart(<HBarChart data={a.depts.filter((d) => d.avgHours != null).map((d) => ({ name: d.name, value: Math.round(d.avgHours) }))} color="#0B1B33" unit=" h" />)}</div>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Department performance" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-navy-100 text-xs font-semibold text-navy-400">
                {['Department', 'Total', 'Open', 'Resolved', 'Avg. time to resolve', 'Within target', 'Rating'].map((h, i) => <th key={h} className={`py-3 font-semibold ${i === 0 ? 'px-5' : 'px-3'}`}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {loading ? <tr><td colSpan={7} className="p-5"><Skeleton className="h-24 w-full" /></td></tr> : a.depts.map((d) => (
                <tr key={d.id} className="border-b border-navy-50 last:border-0">
                  <td className="px-5 py-3.5 font-semibold text-navy-900">{d.name}</td>
                  <td className="px-3 py-3.5">{d.total}</td><td className="px-3 py-3.5">{d.open}</td><td className="px-3 py-3.5">{d.resolved}</td>
                  <td className="px-3 py-3.5">{duration(d.avgHours)}</td><td className="px-3 py-3.5">{dash(d.sla, '%')}</td>
                  <td className="px-3 py-3.5">{d.rating == null ? '–' : d.rating.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
