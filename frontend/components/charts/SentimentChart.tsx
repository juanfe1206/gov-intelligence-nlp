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
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: '#64748b' }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
        <Tooltip contentStyle={{ fontSize: 12, borderColor: '#e2e8f0' }} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area type="monotone" dataKey="positive" stackId="1" stroke="#16a34a" fill="#16a34a" fillOpacity={0.3} name="Positive" />
        <Area type="monotone" dataKey="neutral" stackId="1" stroke="#d97706" fill="#d97706" fillOpacity={0.3} name="Neutral" />
        <Area type="monotone" dataKey="negative" stackId="1" stroke="#dc2626" fill="#dc2626" fillOpacity={0.3} name="Negative" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
