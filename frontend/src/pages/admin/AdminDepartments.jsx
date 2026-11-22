import { useState } from 'react';
import { Layers, Pencil, Plus, Tags, Trash2 } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import { useToast } from '../../components/ui/Toast';
import { Button, Card, CardHeader, Field, Input, Modal, Select } from '../../components/ui/primitives';
import { PageHeader, EmptyState } from '../../components/ui/feedback';
import { PriorityBadge } from '../../components/ui/badges';
import { PRIORITIES } from '../../lib/constants';

export default function AdminDepartments() {
  const { db, maps, saveDepartment, deleteDepartment, saveCategory, deleteCategory } = useApp();
  const toast = useToast();
  const [dept, setDept] = useState(null);   // { id?, name }
  const [cat, setCat] = useState(null);     // category form values
  const [confirm, setConfirm] = useState(null); // { label, run }
  const [error, setError] = useState('');

  const close = () => { setDept(null); setCat(null); setConfirm(null); setError(''); };
  const finish = async (pending, message) => { const res = await pending; if (!res.ok) return setError(res.error); toast(message); close(); };

  return (
    <>
      <PageHeader title="Departments and categories" subtitle="Categories decide which department a complaint is suggested to." />
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Departments" action={<Button size="sm" icon={Plus} onClick={() => setDept({ name: '' })}>Add</Button>} />
          {db.departments.length === 0 ? <EmptyState icon={Layers} title="No departments yet" description="Add a department so complaints can be assigned." /> : (
            <ul className="divide-y divide-navy-50">
              {db.departments.map((d) => {
                const staff = db.users.filter((u) => u.role === 'staff' && u.departmentId === d.id);
                return (
                  <li key={d.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-navy-900">{d.name}</p>
                      <p className="truncate text-[13px] text-navy-400">{staff.length ? staff.map((s) => s.name).join(', ') : 'No staff yet'}</p>
                    </div>
                    <Button variant="ghost" size="sm" aria-label={`Edit ${d.name}`} onClick={() => setDept(d)}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="sm" aria-label={`Delete ${d.name}`} onClick={() => setConfirm({ label: `department "${d.name}"`, run: () => deleteDepartment(d.id) })}><Trash2 className="h-4 w-4" /></Button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="Complaint categories" action={<Button size="sm" icon={Plus} onClick={() => setCat({ name: '', departmentId: '', defaultPriority: 'Medium', keywords: '' })}>Add</Button>} />
          {db.categories.length === 0 ? <EmptyState icon={Tags} title="No categories yet" description="Add a category so students can classify their reports." /> : (
            <ul className="divide-y divide-navy-50">
              {db.categories.map((c) => (
                <li key={c.id} className="flex items-center gap-3 px-5 py-3.5">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-navy-900">{c.name}</p>
                    <p className="truncate text-[13px] text-navy-400">{maps.departments.get(c.departmentId)?.name}, {c.keywords.length} keywords</p>
                  </div>
                  <PriorityBadge priority={c.defaultPriority} />
                  <Button variant="ghost" size="sm" aria-label={`Edit ${c.name}`} onClick={() => setCat({ ...c, keywords: c.keywords.join(', ') })}><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="sm" aria-label={`Delete ${c.name}`} onClick={() => setConfirm({ label: `category "${c.name}"`, run: () => deleteCategory(c.id) })}><Trash2 className="h-4 w-4" /></Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Modal open={!!dept} onClose={close} title={dept?.id ? 'Edit department' : 'Add department'}
        footer={<><Button variant="secondary" onClick={close}>Cancel</Button><Button onClick={() => finish(saveDepartment(dept), 'Department saved')}>Save department</Button></>}>
        <Field label="Department name" htmlFor="dname" error={error}><Input id="dname" invalid={!!error} value={dept?.name || ''} onChange={(e) => setDept({ ...dept, name: e.target.value })} /></Field>
      </Modal>

      <Modal open={!!cat} onClose={close} title={cat?.id ? 'Edit category' : 'Add category'}
        footer={<><Button variant="secondary" onClick={close}>Cancel</Button><Button onClick={() => finish(saveCategory(cat), 'Category saved')}>Save category</Button></>}>
        <Field label="Category name" htmlFor="cname"><Input id="cname" value={cat?.name || ''} onChange={(e) => setCat({ ...cat, name: e.target.value })} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Handled by" htmlFor="cdept"><Select id="cdept" value={cat?.departmentId || ''} onChange={(e) => setCat({ ...cat, departmentId: e.target.value })}><option value="">Select</option>{db.departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</Select></Field>
          <Field label="Default priority" htmlFor="cprio"><Select id="cprio" value={cat?.defaultPriority || 'Medium'} onChange={(e) => setCat({ ...cat, defaultPriority: e.target.value })}>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</Select></Field>
        </div>
        <Field label="Keywords" htmlFor="ckw" hint="Separate with commas. The classifier looks for these words.">
          <Input id="ckw" value={cat?.keywords || ''} onChange={(e) => setCat({ ...cat, keywords: e.target.value })} />
        </Field>
        {error && <p className="text-[13px] font-medium text-red-600" role="alert">{error}</p>}
      </Modal>

      <Modal open={!!confirm} onClose={close} title="Delete this item?"
        footer={<><Button variant="secondary" onClick={close}>Keep it</Button><Button variant="danger" onClick={() => finish(confirm.run(), 'Deleted')}>Delete</Button></>}>
        <p className="text-sm text-navy-600">You are about to delete {confirm?.label}. This cannot be undone.</p>
        {error && <p className="text-[13px] font-medium text-red-600" role="alert">{error}</p>}
      </Modal>
    </>
  );
}
