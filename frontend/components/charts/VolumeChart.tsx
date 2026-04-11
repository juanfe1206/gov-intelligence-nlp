'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface Props {
  data: Array<{ date: string; count: number }>
}

export default function VolumeChart({ data }: Props) {
  // Calculate trend and insights
  const recentData = data.slice(-7)
  const previousData = data.slice(-14, -7)

  const recentAvg = recentData.length > 0
    ? recentData.reduce((acc, d) => acc + d.count, 0) / recentData.length
    : 0
  const previousAvg = previousData.length > 0
    ? previousData.reduce((acc, d) => acc + d.count, 0) / previousData.length
    : 0

  const trend = recentAvg - previousAvg
  const trendPercent = previousAvg > 0 ? (trend / previousAvg) * 100 : 0

  // Find peak day
  const peakDay = data.reduce((max, d) => d.count > max.count ? d : max, data[0] || { date: '', count: 0 })

  // Calculate volatility (standard deviation)
  const mean = data.reduce((acc, d) => acc + d.count, 0) / (data.length || 1)
  const variance = data.reduce((acc, d) => acc + Math.pow(d.count - mean, 2), 0) / (data.length || 1)
  const volatility = Math.sqrt(variance)
  const volatilityPercent = mean > 0 ? (volatility / mean) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Insight Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">Engagement Volume</span>
            {trendPercent > 20 ? (
              <span className="flex items-center gap-1 text-xs text-secondary font-medium bg-secondary/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_up</span>
                +{trendPercent.toFixed(0)}%
              </span>
            ) : trendPercent < -20 ? (
              <span className="flex items-center gap-1 text-xs text-error font-medium bg-error/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_down</span>
                {trendPercent.toFixed(0)}%
              </span>
            ) : (
              <span className="text-xs text-tertiary font-medium">→ Stable</span>
            )}
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            {trendPercent > 50
              ? 'High engagement spike - opportunity for message amplification'
              : trendPercent < -50
              ? 'Engagement dropping - consider re-engagement strategy'
              : volatilityPercent > 50
              ? 'High volatility - unpredictable engagement patterns'
              : 'Steady engagement - maintain current strategy'}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">
            {Math.round(recentAvg).toLocaleString()}
          </div>
          <div className="text-xs text-on-surface-variant">avg daily posts</div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'var(--chart-axis)' }}
            tickFormatter={(v: string) => {
              // Parse ISO date string as local date to avoid UTC timezone issues
              const [year, month, day] = v.split('-').map(Number)
              const date = new Date(year, month - 1, day)
              return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
            }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'var(--chart-axis)' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--surface-container-high)',
              border: '1px solid var(--outline-variant)',
              borderRadius: '8px',
              fontSize: '12px'
            }}
            content={({ active, payload, label }) => {
              if (active && payload && payload.length) {
                const count = payload[0].value as number
                // Parse ISO date string as local date to avoid UTC timezone issues
                const [y, m, d] = (label as string).split('-').map(Number)
                const date = new Date(y, m - 1, d)
                const isPeak = label === peakDay.date
                const vsAvg = mean > 0 ? ((count - mean) / mean) * 100 : 0

                return (
                  <div className="p-2">
                    <p className="text-white font-medium mb-1">
                      {date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    </p>
                    <p className="text-primary text-lg font-bold">{count.toLocaleString()} posts</p>
                    {isPeak && <p className="text-xs text-secondary mt-1">🔥 Peak activity day</p>}
                    <p className={`text-xs mt-1 ${vsAvg > 0 ? 'text-secondary' : 'text-error'}`}>
                      {vsAvg > 0 ? '+' : ''}{vsAvg.toFixed(0)}% vs avg
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          <Bar dataKey="count" name="Posts" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => {
              const isPeak = entry.date === peakDay.date
              const isRecent = index >= data.length - 7
              const isHigh = entry.count > mean + volatility

              let fill = 'var(--primary-container)'
              if (isPeak) fill = '#fbbf24' // Peak day in amber
              else if (isHigh) fill = '#48ddbd' // High engagement in teal
              else if (isRecent) fill = 'var(--primary)' // Recent in light purple

              return <Cell key={`cell-${index}`} fill={fill} />
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Key Metrics */}
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: '#fbbf24' }} />
          <span className="text-on-surface-variant">Peak: {peakDay.count.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: '#48ddbd' }} />
          <span className="text-on-surface-variant">High Activity</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--primary)' }} />
          <span className="text-on-surface-variant">Last 7 days</span>
        </div>
      </div>
    </div>
  )
}
