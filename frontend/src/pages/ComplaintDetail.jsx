import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarClock, FileText, MapPin, SearchX, Sparkles, Tag as TagIcon, User } from 'lucide-react';
import { useApp } from '../store/AppContext';
import { useToast } from '../components/ui/Toast';
import useLoading from '../hooks/useLoading';
import { Button, Card, CardHeader, Field, Select, Textarea, Skeleton } from '../components/ui/primitives';
import { EmptyState, StarRating } from '../components/ui/feedback';
import { PriorityBadge, StatusBadge, Tag } from '../components/ui/badges';
import StatusTracker from '../components/complaints/StatusTracker';
import Timeline from '../components/complaints/Timeline';
import { PRIORITIES } from '../lib/constants';
import { dueAt, fmtDate, fmtDateTime, isOverdue, overdueBy } from '../lib/format';

const BASE = { student: '/student/complaints', staff: '/staff/tasks', admin: '/admin/complaints' };

function Meta({ icon: Icon, label, children }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-navy-50 text-navy-500"><Icon className="h-4 w-4" /></span>
      <div className="min-w-0"><p className="text-xs text-navy-400">{label}</p><div className="text-sm font-semibold text-navy-900">{children}</div></div>
    </div>
  );
}

function FeedbackPanel({ complaint }) {
  const { db, addFeedback } = useApp();
  const toast = useToast();
  const existing = db.feedback.find((f) => f.complaintId === complaint.id);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (complaint.status !== 'Resolved') {
    return <Card><CardHeader title="What happens next" /><p className="p-5 text-sm text-navy-500">You will be able to rate the fix once this complaint is marked resolved.</p></Card>;
  }
  if (existing) {
    return (
      <Card>
        <CardHeader title="Your feedback" subtitle={`Sent ${fmtDate(existing.createdAt)}`} />
        <div className="space-y-3 p-5"><StarRating value={existing.rating} size="h-5 w-5" />{existing.comment && <p className="text-sm text-navy-700">{existing.comment}</p>}</div>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader title="Was it fixed properly?" subtitle="Your rating helps the team improve." />
      <form className="space-y-4 p-5" onSubmit={async (e) => {
        e.preventDefault();
        if (!rating) return setError('Choose a star rating.');
        setBusy(true);
        const res = await addFeedback(complaint.id, { rating, comment });
        setBusy(false);
        if (!res.ok) return setError(res.error);
        toast('Thanks for your feedback');
      }}>
        <div><StarRating value={rating} onChange={(n) => { setRating(n); setError(''); }} />{error && <p className="mt-1.5 text-[13px] font-medium text-red-600" role="alert">{error}</p>}</div>
        <Field label="Comment" htmlFor="fb" hint="Optional"><Textarea id="fb" rows={3} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} /></Field>
        <Button type="submit" loading={busy}>Send feedback</Button>
      </form>
    </Card>
  );
}

function StaffPanel({ complaint }) {
  const { updateStatus } = useApp();
  const toast = useToast();
  const options = complaint.status === 'Assigned' ? ['In Progress', 'Resolved'] : ['Resolved'];
  const [next, setNext] = useState(options[0]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (complaint.status === 'Resolved') {
    return <Card><CardHeader title="Resolution" /><p className="p-5 text-sm text-navy-700">{complaint.resolutionNote}</p></Card>;
  }
  return (
    <Card>
      <CardHeader title="Update this task" subtitle="Customers see your status and note." />
      <form className="space-y-4 p-5" onSubmit={async (e) => {
        e.preventDefault();
        if (next === 'Resolved' && note.trim().length < 10) return setError('Add a resolution note of at least 10 characters.');
        setBusy(true);
        const res = await updateStatus(complaint.id, next, note);
        setBusy(false);
        if (!res.ok) return setError(res.error);
        setNote(''); setError('');
        toast(`Marked as ${next}`);
      }}>
        <Field label="New status" htmlFor="st"><Select id="st" value={next} onChange={(e) => setNext(e.target.value)}>{options.map((o) => <option key={o}>{o}</option>)}</Select></Field>
        <Field label={next === 'Resolved' ? 'Resolution note' : 'Work note'} htmlFor="note" error={error} required={next === 'Resolved'} hint={next === 'Resolved' ? 'Say what was done.' : 'Optional'}>
          <Textarea id="note" rows={4} maxLength={500} invalid={!!error} value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <Button type="submit" loading={busy}>Save update</Button>
      </form>
    </Card>
  );
}

function AdminPanel({ complaint }) {
  const { db, assignComplaint } = useApp();
  const toast = useToast();
  const ai = complaint.aiSuggestion;
  const [deptId, setDeptId] = useState(complaint.departmentId || ai?.departmentId || '');
  const [staffId, setStaffId] = useState(complaint.assignedStaffId || '');
  const [priority, setPriority] = useState(complaint.priority);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const staff = db.users.filter((u) => u.role === 'staff' && u.departmentId === deptId);

  if (complaint.status === 'Resolved') return <Card><CardHeader title="Assignment" /><p className="p-5 text-sm text-navy-500">This complaint is resolved, so it can no longer be reassigned.</p></Card>;
  return (
    <Card>
      <CardHeader title={complaint.assignedStaffId ? 'Reassign' : 'Assign this complaint'} subtitle="Pick the department, then a staff member." />
      <form className="space-y-4 p-5" onSubmit={async (e) => {
        e.preventDefault();
        if (!deptId || !staffId) return setError('Choose a department and a staff member.');
        setBusy(true);
        const res = await assignComplaint(complaint.id, { departmentId: deptId, staffId, priority });
        setBusy(false);
        if (!res.ok) return setError(res.error);
        setError(''); toast('Complaint assigned');
      }}>
        <Field label="Department" htmlFor="dept">
          <Select id="dept" value={deptId} onChange={(e) => { setDeptId(e.target.value); setStaffId(''); }}>
            <option value="">Select a department</option>{db.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </Select>
        </Field>
        <Field label="Staff member" htmlFor="staff">
          <Select id="staff" value={staffId} disabled={!deptId} onChange={(e) => setStaffId(e.target.value)}>
            <option value="">{deptId ? 'Select staff' : 'Choose a department first'}</option>{staff.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </Select>
        </Field>
        <Field label="Priority" htmlFor="prio"><Select id="prio" value={priority} onChange={(e) => setPriority(e.target.value)}>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</Select></Field>
        {error && <p className="text-[13px] font-medium text-red-600" role="alert">{error}</p>}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" loading={busy}>Assign</Button>
          {ai?.departmentId && <Button type="button" variant="secondary" onClick={() => { setDeptId(ai.departmentId); setStaffId(''); setPriority(ai.priority); }}>Use suggestion</Button>}
        </div>
      </form>
    </Card>
  );
}

export default function ComplaintDetail({ role }) {
  const { id } = useParams();
  const { user, db, maps } = useApp();
  const loading = useLoading(350);
  const c = db.complaints.find((x) => x.id === id);
  const allowed = c && (role === 'admin' || (role === 'student' && c.studentId === user.id) || (role === 'staff' && c.assignedStaffId === user.id));
  const history = useMemo(() => db.history.filter((h) => h.complaintId === id), [db.history, id]);

  const back = <Link to={BASE[role]} className="mb-4 inline-flex items-center gap-1.5 text-[13px] font-bold text-navy-500 hover:text-navy-800"><ArrowLeft className="h-4 w-4" />Back to list</Link>;

  if (loading) return <>{back}<Skeleton className="h-8 w-80" /><Skeleton className="mt-6 h-28 w-full" /><Skeleton className="mt-4 h-64 w-full" /></>;
  if (!allowed) return <>{back}<Card><EmptyState icon={SearchX} title="Complaint not found" description="It may have been removed, or it is not available to your account." /></Card></>;

  const overdue = isOverdue(c);
  const ai = c.aiSuggestion;
  const category = maps.categories.get(c.categoryId);

  return (
    <>
      {back}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-bold text-brand-700">{c.id}</p>
          <h1 className="text-2xl font-extrabold text-navy-900">{c.title}</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2"><PriorityBadge priority={c.priority} /><StatusBadge status={c.status} />{overdue && <Tag tone="red">Overdue {overdueBy(c)}</Tag>}{c.isEscalated && <Tag tone="amber">Escalated</Tag>}</div>
      </div>

      <Card className="mb-6 p-6"><StatusTracker status={c.status} history={history} /></Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card>
            <CardHeader title="Details" />
            <div className="space-y-5 p-5">
              <p className="whitespace-pre-line text-sm leading-relaxed text-navy-700">{c.description}</p>
              {c.attachments.length > 0 && (
                <div className="flex flex-wrap gap-3">
                  {c.attachments.map((a) => (a.url ? (
                    a.type.startsWith('image/')
                      ? <a key={a.id} href={a.url} target="_blank" rel="noreferrer"><img src={a.url} alt={`Attachment: ${a.name}`} className="max-h-72 rounded-lg object-cover ring-1 ring-navy-200" /></a>
                      : <a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg bg-navy-50 px-3 py-2 text-sm font-semibold text-navy-700 ring-1 ring-navy-200 hover:ring-brand-400"><FileText className="h-4 w-4" />{a.name}</a>
                  ) : <span key={a.id} className="rounded-lg bg-navy-50 px-3 py-2 text-[13px] text-navy-400">{a.name} (preview unavailable)</span>))}
                </div>
              )}
              <div className="grid gap-4 border-t border-navy-100 pt-5 sm:grid-cols-2">
                <Meta icon={TagIcon} label="Category">{category?.name}</Meta>
                <Meta icon={MapPin} label="Location">{c.location}</Meta>
                <Meta icon={User} label="Reported by">{maps.users.get(c.studentId)?.name}</Meta>
                <Meta icon={CalendarClock} label="Target resolution">{fmtDateTime(dueAt(c))}</Meta>
                <Meta icon={User} label="Assigned to">{c.assignedStaffId ? `${maps.users.get(c.assignedStaffId)?.name}, ${maps.departments.get(c.departmentId)?.name}` : 'Not assigned yet'}</Meta>
              </div>
              {c.resolutionNote && <div className="rounded-lg bg-emerald-50 p-4"><p className="text-[13px] font-bold text-emerald-800">Resolution note</p><p className="mt-1 text-sm text-emerald-900">{c.resolutionNote}</p></div>}
            </div>
          </Card>
          <Card><CardHeader title="Activity" /><div className="p-5"><Timeline history={history} /></div></Card>
        </div>

        <div className="space-y-6">
          {role === 'student' && <FeedbackPanel complaint={c} />}
          {role === 'staff' && <StaffPanel key={c.status} complaint={c} />}
          {role === 'admin' && <AdminPanel complaint={c} />}
          {role !== 'student' && ai && (
            <Card>
              <CardHeader title="Smart suggestion" subtitle={ai.source === 'foundry' ? 'Suggested by Azure AI Foundry.' : 'Suggested by simple rules.'} />
              <div className="space-y-3 p-5 text-sm">
                <div className="flex items-center gap-2 text-navy-500"><Sparkles className="h-4 w-4 text-brand-600" />Suggested at submission</div>
                <p className="text-navy-700">{maps.categories.get(ai.categoryId)?.name || 'No category match'}, {ai.priority} priority{ai.departmentId ? `, ${maps.departments.get(ai.departmentId)?.name}` : ''}.</p>
                <p className="rounded-lg bg-navy-50 p-3 text-[13px] leading-relaxed text-navy-600">{ai.explanation}</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
