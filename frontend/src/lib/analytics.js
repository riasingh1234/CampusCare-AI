// Used by the overview page for the small 14-day chart. The full Analytics page now gets its numbers from the
// backend (GET /admin/analytics), which counts real rows in Azure SQL.
export function trendByDay(complaints, days = 14) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const out = [];
  for (let i = days - 1; i >= 0; i--) {
    const start = new Date(today);
    start.setDate(start.getDate() - i);
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    const within = (iso) => iso && new Date(iso) >= start && new Date(iso) < end;
    out.push({
      label: start.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
      reported: complaints.filter((c) => within(c.createdAt)).length,
      resolved: complaints.filter((c) => within(c.resolvedAt)).length,
    });
  }
  return out;
}
