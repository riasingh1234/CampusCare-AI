import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlarmClock, ClipboardList, Flame, Inbox, UserRoundX, ListChecks, ShieldAlert } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Button, Card, CardHeader, Skeleton } from '../../components/ui/primitives';
import { useToast } from '../../components/ui/Toast';
import { PageHeader, StatCard, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import { Tag } from '../../components/ui/badges';
import { TrendChart } from '../../components/ui/charts';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { trendByDay } from '../../lib/analytics';
import { isCriticalFlagged, isOverdue, overdueBy } from '../../lib/format';

export default function AdminDashboard() {
  const { db, runEscalation } = useApp();
  const toast = useToast();
  const loading = useLoading();
  const [checking, setChecking] = useState(false);
  const [lastRun, setLastRun] = useState(null);

  // Runs the same check as the 6-hourly timer. A complaint is never escalated twice for the same reason.
  const checkNow = async () => {
    setChecking(true);
    const res = await runEscalation();
    setChecking(false);
    if (!res.ok) return toast(res.error, 'error');
    setLastRun(res.result);
    toast(res.result.newEscalations ? `${res.result.newEscalations} new escalation${res.result.newEscalations > 1 ? 's' : ''}` : 'Nothing new to escalate');
  };

  const s = useMemo(() => {
    const open = db.complaints.filter((c) => c.status !== 'Resolved');
    const flagged = open.filter((c) => isCriticalFlagged(c));
    const overdue = open.filter((c) => isOverdue(c));
    const unassigned = open.filter((c) => !c.assignedStaffId);
    const attention = open
      .map((c) => ({ c, crit: isCriticalFlagged(c), late: isOverdue(c), free: !c.assignedStaffId }))
      .filter((x) => x.crit || x.late || x.free)
      .sort((a, b) => (b.crit - a.crit) || (b.late - a.late) || (b.free - a.free))
      .slice(0, 6);
    return { open, flagged, overdue, unassigned, attention, trend: trendByDay(db.complaints, 14) };
  }, [db]);

  return (
    <>
      <PageHeader title="Campus overview" subtitle="What needs a decision today." />
      <Card className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600"><ShieldAlert className="h-5 w-5" /></span>
            <div>
              <p className="text-sm font-bold text-navy-900">Escalation check</p>
              <p className="text-[13px] text-navy-500">Runs automatically every 6 hours. Flags overdue complaints and Critical ones open for over 6 hours.</p>
              {lastRun && <p className="mt-1 text-[13px] font-semibold text-navy-700">Last manual run: checked {lastRun.checked} open, {lastRun.newEscalations} new, {lastRun.alreadyEscalated} already escalated.</p>}
            </div>
          </div>
          <Button variant="secondary" loading={checking} onClick={checkNow}>Run check now</Button>
        </div>
      </Card>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Total complaints" value={db.complaints.length} icon={ListChecks} tone="navy" loading={loading} to="/admin/complaints" />
        <StatCard label="Open" value={s.open.length} icon={ClipboardList} tone="brand" loading={loading} />
        <StatCard label="Awaiting assignment" value={s.unassigned.length} icon={UserRoundX} tone="amber" loading={loading} to="/admin/complaints?filter=unassigned" />
        <StatCard label="Overdue" value={s.overdue.length} icon={AlarmClock} tone="red" loading={loading} to="/admin/complaints?filter=overdue" />
        <StatCard label="Critical, unresolved" value={s.flagged.length} icon={Flame} tone="red" loading={loading} to="/admin/complaints?filter=critical" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Complaints over the last 14 days" subtitle="Reported compared with resolved each day." />
          <div className="p-5">{loading ? <Skeleton className="h-[260px] w-full" /> : <TrendChart data={s.trend} />}</div>
        </Card>
        <Card>
          <CardHeader title="Needs attention" subtitle="Flagged by the escalation rules." />
          {loading ? <TableSkeleton rows={4} /> : s.attention.length === 0 ? (
            <EmptyState icon={Inbox} title="Nothing urgent" description="No overdue, critical or unassigned complaints." />
          ) : (
            <ul className="divide-y divide-navy-50">
              {s.attention.map(({ c, crit, late, free }) => (
                <li key={c.id}>
                  <Link to={`/admin/complaints/${c.id}`} className="block px-5 py-3.5 hover:bg-navy-50/70">
                    <p className="truncate text-sm font-semibold text-navy-900">{c.title}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      <span className="text-xs font-bold text-brand-700">{c.id}</span>
                      {crit && <Tag tone="red">Critical, unresolved</Tag>}
                      {late && <Tag tone="amber">Overdue {overdueBy(c)}</Tag>}
                      {free && <Tag>Not assigned</Tag>}
                      {c.isEscalated && <Tag tone="amber">Escalated</Tag>}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader title="Latest complaints" action={<Link to="/admin/complaints" className="text-[13px] font-bold text-brand-700 hover:underline">View all</Link>} />
        {loading ? <TableSkeleton rows={4} /> : <ComplaintTable complaints={db.complaints.slice(0, 5)} basePath="/admin/complaints" showStudent showAssignee />}
      </Card>
    </>
  );
}
