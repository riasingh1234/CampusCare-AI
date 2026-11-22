import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  CartesianGrid, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';

const AXIS = { fontSize: 12, fill: '#667DA3' };
const TIP = { contentStyle: { borderRadius: 10, border: '1px solid #E3E9F3', boxShadow: 'none', fontSize: 12 } };
export const STATUS_COLORS = { Submitted: '#98A9C7', Assigned: '#2F6BE8', 'In Progress': '#F59E0B', Resolved: '#10B981' };
export const PRIORITY_COLORS = { Low: '#98A9C7', Medium: '#0EA5E9', High: '#F97316', Critical: '#DC2626' };
const legend = <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, color: '#455E86' }} />;

export function TrendChart({ data, height = 260 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
        <CartesianGrid stroke="#E3E9F3" vertical={false} />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={28} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip {...TIP} />
        {legend}
        <Area type="monotone" dataKey="reported" name="Reported" stroke="#1D54CC" strokeWidth={2} fill="#1D54CC" fillOpacity={0.08} />
        <Area type="monotone" dataKey="resolved" name="Resolved" stroke="#10B981" strokeWidth={2} fill="none" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function HBarChart({ data, height = 260, color = '#1D54CC', unit = '' }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid stroke="#E3E9F3" horizontal={false} />
        <XAxis type="number" tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
        <YAxis type="category" dataKey="name" width={132} tick={AXIS} tickLine={false} axisLine={false} />
        <Tooltip {...TIP} cursor={{ fill: '#F2F5FA' }} formatter={(v) => `${v}${unit}`} />
        <Bar dataKey="value" name="Value" fill={color} radius={[0, 4, 4, 0]} barSize={16} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ColumnChart({ data, colors, height = 240 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
        <CartesianGrid stroke="#E3E9F3" vertical={false} />
        <XAxis dataKey="name" tick={AXIS} tickLine={false} axisLine={false} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip {...TIP} cursor={{ fill: '#F2F5FA' }} />
        <Bar dataKey="value" name="Complaints" radius={[4, 4, 0, 0]} barSize={36}>
          {data.map((d) => <Cell key={d.name} fill={colors[d.name]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, colors, height = 240 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={58} outerRadius={88} paddingAngle={2} stroke="none">
          {data.map((d) => <Cell key={d.name} fill={colors[d.name]} />)}
        </Pie>
        <Tooltip {...TIP} />
        {legend}
      </PieChart>
    </ResponsiveContainer>
  );
}
