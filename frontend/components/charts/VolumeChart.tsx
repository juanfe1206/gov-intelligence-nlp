'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ date: string; count: number }>
}

export default function VolumeChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: '#64748b' }}
          tickFormatter={(v: string) => v.slice(5)} // "MM-DD"
        />
        <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderColor: '#e2e8f0' }}
          labelFormatter={(label) => `Date: ${label}`}
        />
        <Bar dataKey="count" fill="#1d4ed8" name="Posts" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
