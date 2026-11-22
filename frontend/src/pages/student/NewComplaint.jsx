import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, Copy, FileText, ImagePlus, Sparkles, Trash2, TriangleAlert } from 'lucide-react';
import { useApp } from '../../store/AppContext';
import { useToast } from '../../components/ui/Toast';
import { Button, Card, CardHeader, Field, Input, Select, Textarea } from '../../components/ui/primitives';
import { PageHeader } from '../../components/ui/feedback';
import { PriorityBadge, Tag } from '../../components/ui/badges';
import { CAMPUS_LOCATIONS } from '../../lib/constants';
import { api } from '../../lib/api';
import { normalizeSuggestion } from '../../lib/normalize';
import { validateComplaint } from '../../lib/validation';
import { ACCEPTED_FILES, MAX_FILES_PER_FORM, isImage, validateAttachment } from '../../lib/image';
import VoiceInput from '../../components/complaints/VoiceInput';

const EMPTY = { title: '', description: '', categoryId: '', location: '', files: [] };

export default function NewComplaint() {
  const { db, maps, submitComplaint } = useApp();
  const toast = useToast();
  const fileRef = useRef(null);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [created, setCreated] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Suggestions are asked from the backend (Azure AI Foundry, with rule-based fallback) a moment after the student stops typing.
  const [suggestion, setSuggestion] = useState(null);
  const [duplicates, setDuplicates] = useState([]);
  useEffect(() => {
    if (form.description.trim().length < 15) { setSuggestion(null); return undefined; }
    let current = true;
    const timer = setTimeout(async () => {
      try {
        const res = await api.post('/ai/classify', { title: form.title, description: form.description });
        if (current) setSuggestion(normalizeSuggestion(res.suggestion));
      } catch { if (current) setSuggestion(null); } // suggestions are optional: the form still works without them
    }, 700);
    return () => { current = false; clearTimeout(timer); };
  }, [form.title, form.description]);

  // Possible duplicates: only a warning. Submitting is never blocked.
  useEffect(() => {
    if (form.description.trim().length < 15) { setDuplicates([]); return undefined; }
    let current = true;
    const timer = setTimeout(async () => {
      try {
        const res = await api.post('/complaints/duplicates', { title: form.title, description: form.description, location: form.location });
        if (current) setDuplicates(res.duplicates);
      } catch { if (current) setDuplicates([]); }
    }, 900);
    return () => { current = false; clearTimeout(timer); };
  }, [form.title, form.description, form.location]);

  const onFiles = (e) => {
    const picked = Array.from(e.target.files || []);
    e.target.value = '';
    let room = MAX_FILES_PER_FORM - form.files.length;
    const added = [];
    for (const file of picked) {
      const problem = validateAttachment(file);
      if (problem) { setErrors((prev) => ({ ...prev, files: problem })); continue; }
      if (room <= 0) { setErrors((prev) => ({ ...prev, files: `You can add up to ${MAX_FILES_PER_FORM} files.` })); break; }
      added.push({ file, preview: isImage(file) ? URL.createObjectURL(file) : null });
      room -= 1;
    }
    if (added.length) { setForm((f) => ({ ...f, files: [...f.files, ...added] })); setErrors((prev) => ({ ...prev, files: undefined })); }
  };
  const removeFile = (index) => {
    const gone = form.files[index];
    if (gone?.preview) URL.revokeObjectURL(gone.preview);
    setForm((f) => ({ ...f, files: f.files.filter((_, i) => i !== index) }));
  };
  const clearForm = () => { form.files.forEach((x) => x.preview && URL.revokeObjectURL(x.preview)); setForm(EMPTY); setErrors({}); };

  // Text from the microphone is added to the description. The student can edit it before submitting.
  const addSpokenText = (text) => setForm((f) => {
    const joined = f.description.trim() ? `${f.description.trimEnd()} ${text}` : text;
    return { ...f, description: joined.slice(0, 1000) };
  });

  const submit = async (e) => {
    e.preventDefault();
    const err = validateComplaint(form);
    setErrors(err);
    if (Object.keys(err).length) return;
    setBusy(true);
    const res = await submitComplaint(form);
    setBusy(false);
    if (!res.ok) return setErrors({ ...res.details, form: res.error });
    setCreated(res);
  };

  if (created) {
    return (
      <Card className="mx-auto mt-6 max-w-xl p-8 text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600"><CheckCircle2 className="h-7 w-7" /></span>
        <h1 className="mt-5 text-2xl font-extrabold text-navy-900">Complaint submitted</h1>
        <p className="mt-2 text-sm text-navy-500">Keep this ID to follow progress. An administrator will review and assign it.</p>
        {created.uploadFailures > 0 && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-[13px] font-medium text-amber-800">Your complaint was saved, but {created.uploadFailures} file{created.uploadFailures > 1 ? 's' : ''} could not be uploaded. You can tell the administrator about it later.</p>}
        <div className="mx-auto mt-5 flex w-fit items-center gap-3 rounded-xl bg-navy-50 px-5 py-3">
          <span className="text-xl font-extrabold text-navy-900">{created.id}</span>
          <button aria-label="Copy complaint ID" onClick={() => { navigator.clipboard?.writeText(created.id); toast('Complaint ID copied'); }} className="rounded p-1 text-navy-400 hover:text-navy-800"><Copy className="h-4 w-4" /></button>
        </div>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link to={`/student/complaints/${created.id}`}><Button>Track this complaint</Button></Link>
          <Button variant="secondary" onClick={() => { clearForm(); setCreated(null); }}>Report another</Button>
        </div>
      </Card>
    );
  }

  return (
    <>
      <PageHeader title="Report an issue" subtitle="Describe the problem and where it is. Suggestions appear as you type." />
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card>
          <form onSubmit={submit} noValidate className="space-y-5 p-5 sm:p-6">
            <Field label="Title" htmlFor="title" error={errors.title} required>
              <Input id="title" maxLength={100} placeholder="For example: Tap leaking in ground floor washroom" invalid={!!errors.title} value={form.title} onChange={set('title')} />
            </Field>
            <Field label="Description" htmlFor="desc" error={errors.description} hint={`${form.description.length}/1000`} required>
              <Textarea id="desc" rows={5} maxLength={1000} placeholder="What is wrong, since when, and how it affects people. Type it, or use the microphone." invalid={!!errors.description} value={form.description} onChange={set('description')} />
              <VoiceInput onText={addSpokenText} />
            </Field>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Category" htmlFor="cat" error={errors.categoryId} required>
                <Select id="cat" invalid={!!errors.categoryId} value={form.categoryId} onChange={set('categoryId')}>
                  <option value="">Select a category</option>
                  {db.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </Select>
              </Field>
              <Field label="Location" htmlFor="loc" error={errors.location} required>
                <Select id="loc" invalid={!!errors.location} value={form.location} onChange={set('location')}>
                  <option value="">Select a place</option>
                  {CAMPUS_LOCATIONS.map((l) => <option key={l}>{l}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Photos or documents" error={errors.files} hint={`Optional. JPG, PNG, WebP or PDF, up to 5 MB each (max ${MAX_FILES_PER_FORM}).`}>
              {form.files.length > 0 && (
                <ul className="mb-3 space-y-2">
                  {form.files.map((x, i) => (
                    <li key={x.preview || `${x.file.name}-${i}`} className="flex items-center gap-4 rounded-lg p-3 ring-1 ring-navy-200">
                      {x.preview ? <img src={x.preview} alt="Selected upload preview" className="h-16 w-24 rounded-md object-cover" />
                        : <span className="flex h-16 w-24 items-center justify-center rounded-md bg-navy-50 text-navy-400"><FileText className="h-6 w-6" /></span>}
                      <span className="min-w-0 flex-1 truncate text-sm text-navy-700">{x.file.name}</span>
                      <Button type="button" variant="ghost" size="sm" icon={Trash2} onClick={() => removeFile(i)}>Remove</Button>
                    </li>
                  ))}
                </ul>
              )}
              {form.files.length < MAX_FILES_PER_FORM && (
                <button type="button" onClick={() => fileRef.current?.click()} className="flex w-full flex-col items-center gap-1.5 rounded-lg border-2 border-dashed border-navy-200 px-4 py-6 text-sm text-navy-500 hover:border-brand-400 hover:bg-brand-50/40">
                  <ImagePlus className="h-6 w-6 text-navy-400" /><span className="font-semibold text-navy-700">Add a photo or document</span>
                </button>
              )}
              <input ref={fileRef} type="file" multiple accept={ACCEPTED_FILES.join(',')} className="hidden" onChange={onFiles} />
            </Field>
            {errors.form && <p className="rounded-lg bg-red-50 px-3 py-2.5 text-sm font-medium text-red-700" role="alert">{errors.form}</p>}
            <div className="flex justify-end gap-3 border-t border-navy-100 pt-5">
              <Button type="button" variant="secondary" onClick={clearForm}>Clear</Button>
              <Button type="submit" loading={busy}>Submit complaint</Button>
            </div>
          </form>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Smart suggestion" subtitle={suggestion?.source === 'foundry' ? 'Suggested by Azure AI Foundry.' : 'Suggested by simple rules. You can change it.'} />
            <div className="p-5">
              {!suggestion ? (
                <p className="text-sm text-navy-500">Write at least a short description and we will suggest a category, priority and department.</p>
              ) : (
                <div className="space-y-3 text-sm">
                  <div className="flex items-center gap-2 text-navy-500"><Sparkles className="h-4 w-4 text-brand-600" />Suggested for this report</div>
                  <dl className="space-y-2">
                    <div className="flex justify-between gap-3"><dt className="text-navy-500">Category</dt><dd className="font-semibold text-navy-900">{maps.categories.get(suggestion.categoryId)?.name || 'Not sure'}</dd></div>
                    <div className="flex justify-between gap-3"><dt className="text-navy-500">Department</dt><dd className="font-semibold text-navy-900">{maps.departments.get(suggestion.departmentId)?.name || 'Not sure'}</dd></div>
                    <div className="flex items-center justify-between gap-3"><dt className="text-navy-500">Priority</dt><dd><PriorityBadge priority={suggestion.priority} /></dd></div>
                  </dl>
                  <p className="rounded-lg bg-navy-50 p-3 text-[13px] leading-relaxed text-navy-600">{suggestion.explanation}</p>
                  {suggestion.categoryId && form.categoryId !== suggestion.categoryId && (
                    <Button size="sm" variant="secondary" onClick={() => setForm({ ...form, categoryId: suggestion.categoryId })}>Use suggested category</Button>
                  )}
                </div>
              )}
            </div>
          </Card>

          {duplicates.length > 0 && (
            <Card>
              <CardHeader title="Possible duplicate" subtitle="Open complaints that look similar to yours." />
              <ul className="divide-y divide-navy-50">
                {duplicates.map((c) => (
                  <li key={c.id} className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-brand-700">{c.id}</span>
                      <Tag tone="amber">{c.similarity}% similar</Tag>
                    </div>
                    <p className="mt-1 text-sm font-semibold text-navy-900">{c.title}</p>
                    <p className="text-[13px] text-navy-400">{c.location}{c.sameLocation ? ', same place' : ''}</p>
                  </li>
                ))}
              </ul>
              <p className="flex gap-2 border-t border-navy-100 p-4 text-[13px] text-navy-500"><TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />You can still submit. Duplicates are merged by staff.</p>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
