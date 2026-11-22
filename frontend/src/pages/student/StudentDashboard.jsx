import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, Hourglass, CheckCircle2, MessageSquareText, PlusCircle, Inbox } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import useLoading from '../../hooks/useLoading';
import { Button, Card, CardHeader } from '../../components/ui/primitives';
import { PageHeader, StatCard, EmptyState, TableSkeleton } from '../../components/ui/feedback';
import ComplaintTable from '../../components/complaints/ComplaintTable';
import { fmtDate } from '../../lib/format';

export default function StudentDashboard() {
  const { user, db } = useApp();
  const loading = useLoading();
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  const { mine, inProgress, resolved, awaiting } = useMemo(() => {
    const mine = db.complaints.filter((c) => c.studentId === user.id);
    const done = new Set(db.feedback.map((f) => f.complaintId));
    const resolved = mine.filter((c) => c.status === 'Resolved');
    return {
      mine, resolved,
      inProgress: mine.filter((c) => c.status === 'Assigned' || c.status === 'In Progress'),
      awaiting: resolved.filter((c) => !done.has(c.id)),
    };
  }, [db, user]);

  return (
    <>
      <PageHeader
        title={`${greeting}, ${user.name.split(' ')[0]}`}
        subtitle="Here is where your reported issues stand."
        actions={<Link to="/student/new"><Button icon={PlusCircle}>Report an issue</Button></Link>}
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total reported" value={mine.length} icon={ClipboardList} tone="navy" loading={loading} to="/student/complaints" />
        <StatCard label="Being worked on" value={inProgress.length} hint="Assigned or in progress" icon={Hourglass} tone="amber" loading={loading} />
        <StatCard label="Resolved" value={resolved.length} icon={CheckCircle2} tone="emerald" loading={loading} />
        <StatCard label="Awaiting your feedback" value={awaiting.length} icon={MessageSquareText} tone="brand" loading={loading} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Recent complaints" action={<Link to="/student/complaints" className="text-[13px] font-bold text-brand-700 hover:underline">View all</Link>} />
          {loading ? <TableSkeleton rows={4} /> : mine.length === 0 ? (
            <EmptyState icon={Inbox} title="You have not reported anything yet" description="Spotted a broken light or a leaking tap? Report it and track the fix here."
              action={<Link to="/student/new"><Button icon={PlusCircle}>Report an issue</Button></Link>} />
          ) : <ComplaintTable complaints={mine.slice(0, 5)} basePath="/student/complaints" />}
        </Card>

        <Card>
          <CardHeader title="Needs your feedback" subtitle="Tell us if the fix worked." />
          <div className="p-5">
            {loading ? <TableSkeleton rows={2} /> : awaiting.length === 0 ? (
              <p className="text-sm text-navy-500">Nothing waiting. Resolved complaints that need a rating will show up here.</p>
            ) : (
              <ul className="space-y-3">
                {awaiting.map((c) => (
                  <li key={c.id}>
                    <Link to={`/student/complaints/${c.id}`} className="block rounded-lg p-3 ring-1 ring-navy-100 hover:bg-navy-50">
                      <p className="text-xs font-bold text-brand-700">{c.id}</p>
                      <p className="text-sm font-semibold text-navy-900">{c.title}</p>
                      <p className="text-[13px] text-navy-400">Resolved {fmtDate(c.resolvedAt)}</p>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
