'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function SentimentChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 10, bottom: 4 }}>
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
        <Tooltip contentStyle={{ fontSize: 12, borderColor: 'var(--chart-tooltip-border)' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="positive" stackId="1" stroke="#16a34a" fill="#16a34a" fillOpacity={0.3} name="Positive" />
        <Area type="monotone" dataKey="neutral" stackId="1" stroke="var(--chart-neutral)" fill="var(--chart-neutral)" fillOpacity={0.3} name="Neutral" />
        <Area type="monotone" dataKey="negative" stackId="1" stroke="#dc2626" fill="#dc2626" fillOpacity={0.3} name="Negative" />
      </AreaChart>
    </ResponsiveContainer>
  )
}