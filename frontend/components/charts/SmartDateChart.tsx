'use client'

import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
  Cell,
} from 'recharts'

interface DataPoint {
  date: string
  value: number
  positive: number
  negative: number
  neutral: number
  hasData: boolean
  isAnomaly: boolean
  anomalyType?: 'spike' | 'drop' | 'positive_surge' | 'negative_surge'
}

interface Props {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
  onDateSelect?: (date: string) => void
}

export default function SmartDateChart({ data, onDateSelect }: Props) {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return []

    // Calculate rolling averages and detect anomalies
    const windowSize = 7
    const processed: DataPoint[] = []

    for (let i = 0; i < data.length; i++) {
      const day = data[i]
      const total = day.positive + day.neutral + day.negative

      // Calculate rolling average
      const windowStart = Math.max(0, i - windowSize + 1)
      const window = data.slice(windowStart, i + 1)
      const windowAvg = window.reduce((acc, d) => acc + d.positive + d.neutral + d.negative, 0) / window.length

      // Calculate standard deviation
      const variance = window.reduce((acc, d) => {
        const v = d.positive + d.neutral + d.negative
        return acc + Math.pow(v - windowAvg, 2)
      }, 0) / window.length
      const stdDev = Math.sqrt(variance)

      // Detect anomalies (2 standard deviations)
      const isAnomaly = Math.abs(total - windowAvg) > 2 * stdDev && total > 0

      // Determine anomaly type
      let anomalyType: DataPoint['anomalyType']
      if (isAnomaly) {
        if (total > windowAvg * 1.5) anomalyType = 'spike'
        else if (total < windowAvg * 0.5) anomalyType = 'drop'
        else if (day.positive > day.negative * 2) anomalyType = 'positive_surge'
        else if (day.negative > day.positive * 2) anomalyType = 'negative_surge'
      }

      processed.push({
        date: day.date,
        value: total,
        positive: day.positive,
        negative: day.negative,
        neutral: day.neutral,
        hasData: total > 0,
        isAnomaly,
        anomalyType,
      })
    }

    return processed
  }, [data])

  // Find top 3 event days
  const eventDays = useMemo(() => {
    return processedData
      .filter(d => d.isAnomaly && d.hasData)
      .sort((a, b) => b.value - a.value)
      .slice(0, 3)
  }, [processedData])

  // Calculate insights
  const insights = useMemo(() => {
    const dataDays = processedData.filter(d => d.hasData)
    const emptyDays = processedData.filter(d => !d.hasData)
    const anomalies = processedData.filter(d => d.isAnomaly)

    const avgVolume = dataDays.length > 0
      ? dataDays.reduce((acc, d) => acc + d.value, 0) / dataDays.length
      : 0

    const bestDay = dataDays.length > 0
      ? dataDays.reduce((max, d) => d.positive > max.positive ? d : max, dataDays[0])
      : null

    const worstDay = dataDays.length > 0
      ? dataDays.reduce((max, d) => d.negative > max.negative ? d : max, dataDays[0])
      : null

    return {
      dataCoverage: `${dataDays.length}/${processedData.length} days`,
      avgVolume: Math.round(avgVolume),
      eventCount: anomalies.length,
      bestDay: bestDay ? { date: bestDay.date, score: bestDay.positive } : null,
      worstDay: worstDay ? { date: worstDay.date, score: worstDay.negative } : null,
    }
  }, [processedData])

  const getBarColor = (entry: DataPoint) => {
    if (!entry.hasData) return 'var(--surface-container-high)'
    if (entry.anomalyType === 'spike') return '#fbbf24'
    if (entry.anomalyType === 'positive_surge') return '#48ddbd'
    if (entry.anomalyType === 'negative_surge') return '#ef4444'
    if (entry.anomalyType === 'drop') return '#6b7280'
    return 'var(--primary)'
  }

  return (
    <div className="space-y-4">
      {/* Header with insights */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">Activity Timeline</span>
            {insights.eventCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-tertiary font-medium bg-tertiary/10 px-2 py-0.5 rounded-full">
                <span className="material-symbols-outlined text-xs">auto_awesome</span>
                {insights.eventCount} events detected
              </span>
            )}
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Showing {insights.dataCoverage} with activity • {insights.avgVolume} avg posts/day
          </p>
        </div>
        <div className="text-right text-xs text-on-surface-variant">
          {insights.bestDay && (
            <div className="flex items-center gap-1 text-secondary">
              <span className="material-symbols-outlined text-xs">sentiment_satisfied</span>
              Best: {(() => {
                const [y, m, d] = insights.bestDay!.date.split('-').map(Number)
                return new Date(y, m - 1, d).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
              })()}
            </div>
          )}
          {insights.worstDay && (
            <div className="flex items-center gap-1 text-error mt-0.5">
              <span className="material-symbols-outlined text-xs">sentiment_dissatisfied</span>
              Worst: {(() => {
                const [y, m, d] = insights.worstDay!.date.split('-').map(Number)
                return new Date(y, m - 1, d).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
              })()}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={processedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: 'var(--chart-axis)' }}
            tickFormatter={(v: string) => {
              // Parse ISO date string as local date to avoid UTC timezone issues
              const [year, month, day] = v.split('-').map(Number)
              const date = new Date(year, month - 1, day)
              return date.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
            }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--chart-axis)' }}
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
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const entry = payload[0].payload as DataPoint
                // Parse ISO date string as local date to avoid UTC timezone issues
                const [year, month, day] = entry.date.split('-').map(Number)
                const date = new Date(year, month - 1, day)

                if (!entry.hasData) {
                  return (
                    <div className="p-2">
                      <p className="text-white font-medium mb-1">
                        {date.toLocaleDateString('en-GB', { weekday: 'long', month: 'short', day: 'numeric' })}
                      </p>
                      <p className="text-on-surface-variant text-xs">No data for this date</p>
                    </div>
                  )
                }

                return (
                  <div className="p-2">
                    <p className="text-white font-medium mb-2">
                      {date.toLocaleDateString('en-GB', { weekday: 'long', month: 'short', day: 'numeric' })}
                    </p>
                    <p className="text-primary text-lg font-bold">{entry.value.toLocaleString()} posts</p>
                    <div className="flex gap-2 text-xs mt-2">
                      <span className="text-secondary">+{entry.positive}</span>
                      <span className="text-tertiary">~{entry.neutral}</span>
                      <span className="text-error">-{entry.negative}</span>
                    </div>
                    {entry.isAnomaly && (
                      <p className={`text-xs mt-2 font-medium ${
                        entry.anomalyType?.includes('positive') ? 'text-secondary' :
                        entry.anomalyType?.includes('negative') ? 'text-error' : 'text-tertiary'
                      }`}>
                        ⚡ {entry.anomalyType?.replace('_', ' ')}
                      </p>
                    )}
                  </div>
                )
              }
              return null
            }}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {processedData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={getBarColor(entry)}
                onClick={() => entry.hasData && onDateSelect?.(entry.date)}
                style={{ cursor: entry.hasData ? 'pointer' : 'default' }}
              />
            ))}
          </Bar>
          {eventDays.map((day, i) => (
            <ReferenceDot
              key={i}
              x={day.date}
              y={day.value}
              r={4}
              fill={day.anomalyType?.includes('negative') ? '#ef4444' : '#fbbf24'}
              stroke="none"
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Event Days List */}
      {eventDays.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-white uppercase tracking-wider">Key Event Days</p>
          <div className="flex flex-wrap gap-2">
            {eventDays.map((day, i) => (
              <button
                key={i}
                onClick={() => onDateSelect?.(day.date)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  day.anomalyType?.includes('positive')
                    ? 'bg-secondary/10 border-secondary/30 text-secondary hover:bg-secondary/20'
                    : day.anomalyType?.includes('negative')
                    ? 'bg-error/10 border-error/30 text-error hover:bg-error/20'
                    : 'bg-tertiary/10 border-tertiary/30 text-tertiary hover:bg-tertiary/20'
                }`}
              >
                <span className="material-symbols-outlined text-xs mr-1">
                  {day.anomalyType?.includes('positive') ? 'trending_up' :
                   day.anomalyType?.includes('negative') ? 'trending_down' : 'notifications'}
                </span>
                {(() => {
                  const [y, m, d] = day.date.split('-').map(Number)
                  return new Date(y, m - 1, d).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
                })()}
                : {day.value.toLocaleString()} posts
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
