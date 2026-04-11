'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

interface DataPoint {
  date: string
  netSentiment: number
  positive: number
  negative: number
  total: number
}

interface Props {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function NetSentimentChart({ data }: Props) {
  // Transform data to show net sentiment (positive - negative)
  const transformedData: DataPoint[] = data.map((d) => ({
    date: d.date,
    netSentiment: d.positive - d.negative,
    positive: d.positive,
    negative: d.negative,
    total: d.positive + d.neutral + d.negative,
  }))

  // Calculate trend
  const recentData = transformedData.slice(-7)
  const olderData = transformedData.slice(-14, -7)

  const recentAvg = recentData.length > 0
    ? recentData.reduce((acc, d) => acc + d.netSentiment, 0) / recentData.length
    : 0
  const olderAvg = olderData.length > 0
    ? olderData.reduce((acc, d) => acc + d.netSentiment, 0) / olderData.length
    : 0

  const trend = recentAvg - olderAvg
  const trendPercent = olderAvg !== 0 ? (trend / Math.abs(olderAvg)) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Insight Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">Net Sentiment Trend</span>
            {trend > 0 ? (
              <span className="flex items-center gap-1 text-xs text-secondary font-medium bg-secondary/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_up</span>
                +{trendPercent.toFixed(0)}%
              </span>
            ) : trend < 0 ? (
              <span className="flex items-center gap-1 text-xs text-error font-medium bg-error/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_down</span>
                {trendPercent.toFixed(0)}%
              </span>
            ) : (
              <span className="text-xs text-tertiary font-medium">→ Stable</span>
            )}
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            {trend > 0
              ? 'Positive momentum building - capitalize on this window'
              : trend < 0
              ? 'Negative sentiment increasing - address concerns urgently'
              : 'Sentiment stable - monitor for changes'}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">
            {recentAvg > 0 ? '+' : ''}{recentAvg.toFixed(0)}
          </div>
          <div className="text-xs text-on-surface-variant">avg last 7 days</div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={transformedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="positiveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#48ddbd" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#48ddbd" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="negativeGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
          </defs>
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
                const data = payload[0].payload as DataPoint
                const sentimentScore = ((data.positive / (data.total || 1)) * 100) - ((data.negative / (data.total || 1)) * 100)
                // Parse ISO date string as local date to avoid UTC timezone issues
                const [y, m, d] = (label as string).split('-').map(Number)
                const date = new Date(y, m - 1, d)
                return (
                  <div className="p-2">
                    <p className="text-white font-medium mb-1">{date.toLocaleDateString()}</p>
                    <p className="text-secondary text-xs">Positive: {data.positive.toLocaleString()}</p>
                    <p className="text-error text-xs">Negative: {data.negative.toLocaleString()}</p>
                    <p className={`text-xs font-bold mt-1 ${sentimentScore > 0 ? 'text-secondary' : sentimentScore < 0 ? 'text-error' : 'text-tertiary'}`}>
                      Net Score: {sentimentScore > 0 ? '+' : ''}{sentimentScore.toFixed(1)}%
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          <ReferenceLine y={0} stroke="#948da2" strokeDasharray="3 3" />
          <Area
            type="monotone"
            dataKey="netSentiment"
            stroke={trend >= 0 ? '#48ddbd' : '#ef4444'}
            fill={trend >= 0 ? 'url(#positiveGradient)' : 'url(#negativeGradient)'}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
