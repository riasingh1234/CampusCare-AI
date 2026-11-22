// The API sends numbers for ids; the existing screens compare ids as text (form fields give text).
// This file converts once, in one place, so no page has to care.

const sid = (v) => (v == null ? null : String(v));

export function normalizeSuggestion(s) {
  if (!s) return null;
  return { ...s, categoryId: sid(s.categoryId), departmentId: sid(s.departmentId) };
}

export function normalizeComplaint(c) {
  const attachments = c.attachments || [];
  const firstImage = attachments.find((a) => a.type?.startsWith('image/') && a.url);
  return {
    ...c,
    categoryId: sid(c.categoryId),
    studentId: sid(c.studentId),
    departmentId: sid(c.departmentId),
    assignedStaffId: sid(c.assignedStaffId),
    aiSuggestion: normalizeSuggestion(c.aiSuggestion),
    attachments,
    image: firstImage ? firstImage.url : null,
  };
}

export function normalizeWorkspace(w) {
  return {
    departments: w.departments.map((d) => ({ ...d, id: sid(d.id) })),
    categories: w.categories.map((c) => ({ ...c, id: sid(c.id), departmentId: sid(c.departmentId), keywords: c.keywords || [] })),
    users: w.users.map((u) => ({ ...u, id: sid(u.id), departmentId: sid(u.departmentId) })),
    complaints: w.complaints.map(normalizeComplaint),
    history: w.history.map((h) => ({ ...h, id: sid(h.id), byId: sid(h.byId) })),
    feedback: w.feedback.map((f) => ({ ...f, id: sid(f.id), studentId: sid(f.studentId) })),
  };
}

export function buildMaps(db) {
  return {
    users: new Map(db.users.map((u) => [u.id, u])),
    departments: new Map(db.departments.map((d) => [d.id, d])),
    categories: new Map(db.categories.map((c) => [c.id, c])),
  };
}
