import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildMaps, normalizeWorkspace } from '../src/lib/normalize.js';
import { isImage, validateAttachment } from '../src/lib/image.js';

const workspace = {
  departments: [{ id: 2, name: 'Plumbing & Water' }],
  categories: [{ id: 5, name: 'Water & plumbing', departmentId: 2, defaultPriority: 'Medium', keywords: ['tap'] }],
  users: [{ id: 9, name: 'Anil', role: 'staff', departmentId: 2 }, { id: 1, name: 'Meera', role: 'admin', departmentId: null }],
  complaints: [{
    id: 'CC-2026-0001', title: 't', categoryId: 5, studentId: 4, departmentId: 2, assignedStaffId: 9, status: 'Assigned', priority: 'High',
    createdAt: '2026-11-20T10:00:00Z', dueAt: '2026-11-22T10:00:00Z', isEscalated: false,
    aiSuggestion: { categoryId: 5, departmentId: 2, priority: 'High', explanation: 'x', source: 'rules' },
    attachments: [{ id: 1, name: 'a.pdf', type: 'application/pdf', url: 'https://b/a.pdf' }, { id: 2, name: 'p.png', type: 'image/png', url: 'https://b/p.png' }],
  }, {
    id: 'CC-2026-0002', title: 'u', categoryId: 5, studentId: 4, departmentId: null, assignedStaffId: null, status: 'Submitted', priority: 'Low',
    createdAt: '2026-11-21T10:00:00Z', aiSuggestion: null, attachments: [],
  }],
  history: [{ id: 3, complaintId: 'CC-2026-0001', status: 'Assigned', note: '', byId: 1, at: '2026-11-20T11:00:00Z' },
    { id: 4, complaintId: 'CC-2026-0001', status: 'Assigned', note: 'Escalated', byId: null, at: '2026-11-22T11:00:00Z' }],
  feedback: [{ id: 7, complaintId: 'CC-2026-0001', studentId: 4, rating: 5, comment: '', createdAt: '2026-11-22T12:00:00Z' }],
};

test('ids become text so they match <select> values', () => {
  const db = normalizeWorkspace(workspace);
  assert.equal(db.departments[0].id, '2');
  assert.equal(db.categories[0].departmentId, '2');
  assert.equal(db.users[1].departmentId, null);
  const c = db.complaints[0];
  assert.deepEqual([c.categoryId, c.studentId, c.departmentId, c.assignedStaffId], ['5', '4', '2', '9']);
  assert.equal(c.aiSuggestion.categoryId, '5');
  assert.equal(db.complaints[1].assignedStaffId, null);
  assert.equal(db.complaints[1].aiSuggestion, null);
  assert.equal(db.history[1].byId, null); // system entries (escalation) stay without a person
  assert.equal(db.feedback[0].studentId, '4');
});

test('complaint reference stays the id, and the first image becomes c.image', () => {
  const db = normalizeWorkspace(workspace);
  assert.equal(db.complaints[0].id, 'CC-2026-0001');
  assert.equal(db.complaints[0].image, 'https://b/p.png');
  assert.equal(db.complaints[1].image, null);
});

test('maps can be looked up with the same text ids', () => {
  const maps = buildMaps(normalizeWorkspace(workspace));
  assert.equal(maps.users.get('9').name, 'Anil');
  assert.equal(maps.categories.get('5').name, 'Water & plumbing');
});

test('file checks mirror the server rules', () => {
  assert.equal(validateAttachment({ type: 'image/png', size: 100 }), null);
  assert.equal(validateAttachment({ type: 'application/pdf', size: 100 }), null);
  assert.match(validateAttachment({ type: 'image/gif', size: 100 }), /JPG, PNG or WebP/);
  assert.match(validateAttachment({ type: 'image/png', size: 6 * 1024 * 1024 }), /5 MB/);
  assert.match(validateAttachment({ type: 'image/png', size: 0 }), /empty/);
  assert.equal(isImage('image/webp'), true);
  assert.equal(isImage({ type: 'application/pdf' }), false);
});
