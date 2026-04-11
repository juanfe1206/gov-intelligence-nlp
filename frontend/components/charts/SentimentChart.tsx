'use client'

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface Props {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function SentimentChart({ data }: Props) {
  // Filter out days with no data for trend calculations
  const dataWithActivity = data.filter(d => d.positive + d.neutral + d.negative > 0)

  // Calculate key insights from last 7 days with actual data
  const recentData = dataWithActivity.slice(-7)
  const previousData = dataWithActivity.slice(-14, -7)

  const calculateSentimentRatio = (d: typeof data[0]) => {
    const total = d.positive + d.neutral + d.negative || 1
    return {
      positive: (d.positive / total) * 100,
      neutral: (d.neutral / total) * 100,
      negative: (d.negative / total) * 100,
    }
  }

  const recentRatios = recentData.map(calculateSentimentRatio)
  const previousRatios = previousData.map(calculateSentimentRatio)

  const recentAvg = recentRatios.length > 0
    ? {
        positive: recentRatios.reduce((acc, r) => acc + r.positive, 0) / recentRatios.length,
        neutral: recentRatios.reduce((acc, r) => acc + r.neutral, 0) / recentRatios.length,
        negative: recentRatios.reduce((acc, r) => acc + r.negative, 0) / recentRatios.length,
      }
    : { positive: 0, neutral: 0, negative: 0 }

  const previousAvg = previousRatios.length > 0
    ? {
        positive: previousRatios.reduce((acc, r) => acc + r.positive, 0) / previousRatios.length,
        neutral: previousRatios.reduce((acc, r) => acc + r.neutral, 0) / previousRatios.length,
        negative: previousRatios.reduce((acc, r) => acc + r.negative, 0) / previousRatios.length,
      }
    : { positive: 0, neutral: 0, negative: 0 }

  const posChange = recentAvg.positive - previousAvg.positive
  const negChange = recentAvg.negative - previousAvg.negative

  // Find the dominant sentiment trend
  // positive trend = more positive sentiment OR less negative sentiment
  // negative trend = more negative sentiment OR less positive sentiment
  const dominantTrend =
    (posChange > 0 && posChange > Math.abs(negChange)) ? 'positive' :
    (negChange > 0 && negChange > Math.abs(posChange)) ? 'negative' :
    'stable'

  // Calculate Net Sentiment Score (-100 to +100 scale)
  // This is the industry standard: positive% - negative%
  const netSentimentScore = recentAvg.positive - recentAvg.negative
  // Normalize to 0-100 scale for display (add 100, divide by 2)
  const sentimentScore = Math.round((netSentimentScore + 100) / 2)

  return (
    <div className="space-y-4">
      {/* Insight Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">Sentiment Distribution</span>
            {dominantTrend === 'positive' ? (
              <span className="flex items-center gap-1 text-xs text-secondary font-medium bg-secondary/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_up</span>
                +{posChange.toFixed(1)}%
              </span>
            ) : dominantTrend === 'negative' ? (
              <span className="flex items-center gap-1 text-xs text-error font-medium bg-error/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">trending_down</span>
                +{negChange.toFixed(1)}%
              </span>
            ) : (
              <span className="text-xs text-tertiary font-medium">→ Stable</span>
            )}
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            {dominantTrend === 'positive'
              ? 'Positive sentiment improving - capitalize on momentum'
              : dominantTrend === 'negative'
              ? 'Negative sentiment increasing - address concerns proactively'
              : netSentimentScore > 20
              ? 'Strong positive baseline - maintain messaging strategy'
              : netSentimentScore < -20
              ? 'Negative baseline - consider reputation management'
              : 'Sentiment stable - monitor for emerging trends'}
          </p>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${
            netSentimentScore >= 20 ? 'text-secondary' :
            netSentimentScore >= -20 ? 'text-tertiary' : 'text-error'
          }`}>
            {netSentimentScore > 0 ? '+' : ''}{netSentimentScore.toFixed(0)}
          </div>
          <div className="text-xs text-on-surface-variant">net sentiment</div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="positiveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#48ddbd" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#48ddbd" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="neutralGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#fbbf24" stopOpacity={0}/>
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
                const total = payload.reduce((acc, p) => acc + (p.value as number), 0) || 1
                // Parse ISO date string as local date to avoid UTC timezone issues
                const [y, m, d] = (label as string).split('-').map(Number)
                const date = new Date(y, m - 1, d)
                return (
                  <div className="p-2">
                    <p className="text-white font-medium mb-2">
                      {date.toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </p>
                    {payload.map((p, i) => (
                      <div key={i} className="flex justify-between gap-4 text-xs mb-1">
                        <span style={{ color: p.color }}>{p.name}</span>
                        <span className="text-white">
                          {p.value?.toLocaleString()} ({(((p.value as number) / total) * 100).toFixed(0)}%)
                        </span>
                      </div>
                    ))}
                  </div>
                )
              }
              return null
            }}
          />
          <Area
            type="monotone"
            dataKey="positive"
            stackId="1"
            stroke="#48ddbd"
            fill="url(#positiveGradient)"
            name="Positive"
          />
          <Area
            type="monotone"
            dataKey="neutral"
            stackId="1"
            stroke="#fbbf24"
            fill="url(#neutralGradient)"
            name="Neutral"
          />
          <Area
            type="monotone"
            dataKey="negative"
            stackId="1"
            stroke="#ef4444"
            fill="url(#negativeGradient)"
            name="Negative"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#48ddbd]" />
          <span className="text-on-surface-variant">{recentAvg.positive.toFixed(0)}% Positive</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#fbbf24]" />
          <span className="text-on-surface-variant">{recentAvg.neutral.toFixed(0)}% Neutral</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-[#ef4444]" />
          <span className="text-on-surface-variant">{recentAvg.negative.toFixed(0)}% Negative</span>
        </div>
      </div>
    </div>
  )
}
