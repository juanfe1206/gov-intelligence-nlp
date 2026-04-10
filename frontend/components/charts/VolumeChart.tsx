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
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: 10, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: 'var(--chart-axis)' }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tick={{ fontSize: 12, fill: 'var(--chart-axis)' }}
          label={{ value: 'Posts', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: 'var(--chart-axis)', fontSize: 12 } }}
        />
        <Tooltip
          contentStyle={{ fontSize: 12, borderColor: 'var(--chart-tooltip-border)' }}
          labelFormatter={(label) => `Date: ${label}`}
        />
        <Bar dataKey="count" fill="var(--color-primary)" name="Posts" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}