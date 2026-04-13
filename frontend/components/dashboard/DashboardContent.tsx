'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import VolumeChart from '@/components/charts/VolumeChart'
import SentimentChart from '@/components/charts/SentimentChart'
import NetSentimentChart from '@/components/charts/NetSentimentChart'
import SmartDateChart from '@/components/charts/SmartDateChart'
import FilterBar, { FilterState, getDefaultDates } from './FilterBar'
import TopicsPanel from './TopicsPanel'
import PostsPanel from './PostsPanel'
import SpikeAlertBanner from './SpikeAlertBanner'
import KpiCards from './KpiCards'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

// Type definitions
interface VolumeData {
  data: Array<{ date: string; count: number }>
  total: number
}

interface SentimentData {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

interface TopicsData {
  topics: Array<{ name: string; label: string; count: number }>
}

export default function DashboardContent() {
  const defaultDates = getDefaultDates(3650)
  const [filters, setFilters] = useState<FilterState>({
    topic: '',
    subtopic: '',
    target: '',
    platform: '',
    startDate: defaultDates.startDate,
    endDate: defaultDates.endDate,
    selectedParties: [],
  })
  const [volumeData, setVolumeData] = useState<VolumeData | null>(null)
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null)
  const [topicsData, setTopicsData] = useState<TopicsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const copyResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Build export URL from current filters
  const exportUrl = useMemo(() => {
    const params = new URLSearchParams()
    if (filters.startDate) params.set('start_date', filters.startDate)
    if (filters.endDate) params.set('end_date', filters.endDate)
    if (filters.topic) params.set('topic', filters.topic)
    if (filters.subtopic) params.set('subtopic', filters.subtopic)
    if (filters.target) params.set('target', filters.target)
    if (filters.platform) params.set('platform', filters.platform)
    filters.selectedParties.forEach((party) => params.append('parties', party))
    return `${API_BASE}/analytics/export?${params.toString()}`
  }, [filters])

  // Build summary text from current data
  const summaryText = useMemo(() => {
    const lines: string[] = ['=== Gov Intelligence Analytics Summary ===']
    lines.push(`Date range: ${filters.startDate ?? 'default'} → ${filters.endDate ?? 'default'}`)
    if (filters.topic) lines.push(`Topic label: ${filters.topic}`)
    if (filters.subtopic) lines.push(`Subtopic label: ${filters.subtopic}`)
    if (filters.platform) lines.push(`Platform: ${filters.platform}`)
    if (filters.selectedParties.length) lines.push(`Parties: ${filters.selectedParties.join(', ')}`)
    if (volumeData) lines.push(`Total posts: ${volumeData.total.toLocaleString()}`)
    if (sentimentData?.data.length) {
      const totals = sentimentData.data.reduce(
        (acc, d) => ({
          pos: acc.pos + d.positive,
          neu: acc.neu + d.neutral,
          neg: acc.neg + d.negative,
        }),
        { pos: 0, neu: 0, neg: 0 },
      )
      const total = totals.pos + totals.neu + totals.neg || 1
      lines.push(
        `Sentiment: ${((totals.pos / total) * 100).toFixed(1)}% positive, ` +
        `${((totals.neu / total) * 100).toFixed(1)}% neutral, ` +
        `${((totals.neg / total) * 100).toFixed(1)}% negative`,
      )
    }
    return lines.join('\n')
  }, [filters, volumeData, sentimentData])

  // Compute KPI data from volume and sentiment
  const kpiData = useMemo(() => {
    const total = volumeData?.total ?? 0
    let positivePct = 0
    let neutralPct = 0
    let negativePct = 0
    if (sentimentData?.data.length) {
      const totals = sentimentData.data.reduce(
        (acc, d) => ({
          pos: acc.pos + d.positive,
          neu: acc.neu + d.neutral,
          neg: acc.neg + d.negative,
        }),
        { pos: 0, neu: 0, neg: 0 },
      )
      const sum = totals.pos + totals.neu + totals.neg || 1
      positivePct = (totals.pos / sum) * 100
      neutralPct = (totals.neu / sum) * 100
      negativePct = (totals.neg / sum) * 100
    }
    return { total, positivePct, neutralPct, negativePct }
  }, [volumeData, sentimentData])

  const topTopic = topicsData?.topics?.length
    ? topicsData.topics.reduce((a, b) => (b.count > a.count ? b : a)).label
    : ''

  // Copy summary to clipboard
  async function handleCopySummary() {
    try {
      await navigator.clipboard.writeText(summaryText)
      setCopied(true)
      setActionMessage('Summary copied to clipboard.')
      if (copyResetTimeoutRef.current) {
        clearTimeout(copyResetTimeoutRef.current)
      }
      copyResetTimeoutRef.current = setTimeout(() => setCopied(false), 2000)
    } catch {
      setActionMessage('Unable to copy summary. Check clipboard permissions and try again.')
    }
  }

  async function handleExport() {
    try {
      const response = await fetch(exportUrl)
      if (!response.ok) {
        throw new Error('Failed to export snapshot')
      }
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = 'gov-intelligence-export.json'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(downloadUrl)
      setActionMessage('Export started.')
    } catch {
      setActionMessage('Export failed. Please try again.')
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchData() {
      setLoading(true)
      setError(null)
      setActionMessage(null)
      try {
        const params = new URLSearchParams({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })
        if (filters.topic) params.set('topic', filters.topic)
        if (filters.subtopic) params.set('subtopic', filters.subtopic)
        if (filters.target) params.set('target', filters.target)
        if (filters.platform) params.set('platform', filters.platform)

        const [volRes, sentRes, topicRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/volume?${params.toString()}`, { signal: controller.signal }),
          fetch(`${API_BASE}/analytics/sentiment?${params.toString()}`, { signal: controller.signal }),
          fetch(`${API_BASE}/analytics/topics?${params.toString()}`, { signal: controller.signal }),
        ])
        if (!volRes.ok || !sentRes.ok) throw new Error('Failed to fetch analytics data')
        const [vol, sent, topics] = await Promise.all([volRes.json(), sentRes.json(), topicRes.json()])
        if (!isActive) return
        setVolumeData(vol)
        setSentimentData(sent)
        setTopicsData(topics)
      } catch (error) {
        if ((error as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load analytics data. Check that the backend is running.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }
    fetchData()

    return () => {
      isActive = false
      controller.abort()
      if (copyResetTimeoutRef.current) {
        clearTimeout(copyResetTimeoutRef.current)
      }
    }
  }, [filters])

  function handleTopicSelect(topicName: string) {
    setFilters((prev) => ({ ...prev, topic: topicName, subtopic: '' }))
  }
  function handleClearTopic() {
    setFilters((prev) => ({ ...prev, topic: '', subtopic: '' }))
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
        <p className="text-on-surface-variant">Loading analytics...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <span className="material-symbols-outlined text-4xl text-error">error</span>
        <p className="text-error">{error}</p>
      </div>
    )
  }

  const isEmpty = !volumeData?.data?.length && !sentimentData?.data?.length
  const hasFilters =
    filters.topic ||
    filters.subtopic ||
    filters.target ||
    filters.platform ||
    (filters.selectedParties?.length ?? 0) > 0

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <section className="max-w-3xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl mb-2">
          Intelligence Dashboard
        </h1>
      </section>

      {/* Filters */}
      <FilterBar filters={filters} onChange={setFilters} />

      {/* KPI Cards - Now with actionable insights */}
      <KpiCards
        totalPosts={kpiData.total}
        positivePct={kpiData.positivePct}
        neutralPct={kpiData.neutralPct}
        negativePct={kpiData.negativePct}
        topTopic={topTopic}
        sentimentData={sentimentData ?? undefined}
        topicsData={topicsData ?? undefined}
      />

      {/* Spike Alerts */}
      <SpikeAlertBanner filters={filters} />

      {/* Action Buttons */}
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          onClick={handleCopySummary}
          className="flex w-full items-center justify-center gap-2 rounded-full border border-outline-variant/20 px-4 py-2.5 text-sm font-medium text-on-surface transition-colors hover:bg-surface-container hover:text-white sm:w-auto"
        >
          <span className="material-symbols-outlined text-sm">{copied ? 'check' : 'content_copy'}</span>
          {copied ? 'Copied!' : 'Copy summary'}
        </button>
        <button
          onClick={handleExport}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-primary-container px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-container/90 sm:w-auto"
        >
          <span className="material-symbols-outlined text-sm">download</span>
          Export
        </button>
      </div>
      {actionMessage && (
        <p className="text-on-surface-variant text-sm text-center sm:text-right">{actionMessage}</p>
      )}

      {!isEmpty && (
        <>
          {/* Charts Grid - Reorganized for actionable insights */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Net Sentiment Chart - Most important for politicians */}
            <div className="min-w-0 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
              <NetSentimentChart data={sentimentData?.data ?? []} />
            </div>

            {/* Sentiment Distribution Chart */}
            <div className="min-w-0 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
              <SentimentChart data={sentimentData?.data ?? []} />
            </div>

            {/* Smart Activity Timeline with anomaly detection */}
            <div className="min-w-0 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
              <SmartDateChart
                data={sentimentData?.data ?? []}
                onDateSelect={(date) => {
                  setActionMessage(`Selected ${new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} — scroll to posts`)
                  // Scroll to posts section
                  document.getElementById('posts-section')?.scrollIntoView({ behavior: 'smooth' })
                }}
              />
            </div>

            {/* Engagement Volume Chart */}
            <div className="min-w-0 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
              <VolumeChart data={volumeData?.data ?? []} />
            </div>

            {/* Key Insights Card */}
            <div className="min-w-0 rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
              <div className="flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-primary">lightbulb</span>
                <h3 className="font-bold text-white text-base">Key Insights</h3>
              </div>
              <div className="space-y-4">
                {(() => {
                  // Calculate insights
                  const recent = sentimentData?.data?.slice(-7) || []
                  const prev = sentimentData?.data?.slice(-14, -7) || []

                  const recentAvg = recent.length > 0
                    ? recent.reduce((acc, d) => acc + d.positive - d.negative, 0) / recent.length
                    : 0
                  const prevAvg = prev.length > 0
                    ? prev.reduce((acc, d) => acc + d.positive - d.negative, 0) / prev.length
                    : 0

                  const sentimentChange = prevAvg !== 0
                    ? ((recentAvg - prevAvg) / Math.abs(prevAvg)) * 100
                    : 0

                  // Volume trend
                  const recentVol = volumeData?.data?.slice(-7) || []
                  const prevVol = volumeData?.data?.slice(-14, -7) || []
                  const recentVolAvg = recentVol.length > 0
                    ? recentVol.reduce((acc, d) => acc + d.count, 0) / recentVol.length
                    : 0
                  const prevVolAvg = prevVol.length > 0
                    ? prevVol.reduce((acc, d) => acc + d.count, 0) / prevVol.length
                    : 0
                  const volChange = prevVolAvg > 0
                    ? ((recentVolAvg - prevVolAvg) / prevVolAvg) * 100
                    : 0

                  const insights = []

                  if (sentimentChange > 15) {
                    insights.push({
                      icon: 'trending_up',
                      color: 'text-secondary',
                      text: 'Positive sentiment rising significantly. Good time to amplify messaging.',
                    })
                  } else if (sentimentChange < -15) {
                    insights.push({
                      icon: 'trending_down',
                      color: 'text-error',
                      text: 'Negative sentiment spike detected. Consider addressing concerns.',
                    })
                  }

                  if (volChange > 50) {
                    insights.push({
                      icon: 'notifications_active',
                      color: 'text-tertiary',
                      text: 'Engagement surging. High visibility window active.',
                    })
                  } else if (volChange < -30) {
                    insights.push({
                      icon: 'trending_down',
                      color: 'text-on-surface-variant',
                      text: 'Engagement dropping. Consider re-engagement tactics.',
                    })
                  }

                  // Top performing topic
                  if (topicsData?.topics && topicsData.topics.length > 0) {
                    const topTopic = topicsData.topics.reduce((a, b) => a.count > b.count ? a : b)
                    insights.push({
                      icon: 'star',
                      color: 'text-primary',
                      text: `${topTopic.label} is the most discussed topic with ${topTopic.count.toLocaleString()} mentions.`,
                    })
                  }

                  if (insights.length === 0) {
                    insights.push({
                      icon: 'check_circle',
                      color: 'text-secondary',
                      text: 'Sentiment and engagement remain stable. Continue monitoring.',
                    })
                  }

                  return insights.map((insight, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className={"material-symbols-outlined " + insight.color + " mt-0.5"}>{insight.icon}</span>
                      <p className="text-sm text-white">{insight.text}</p>
                    </div>
                  ))
                })()}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Topics Panel */}
      <TopicsPanel
        filters={filters}
        onTopicSelect={handleTopicSelect}
        onClearTopic={handleClearTopic}
      />

      {/* Posts Panel */}
      <div id="posts-section">
        <PostsPanel filters={filters} />
      </div>

      {isEmpty && (
        <div className="text-center py-12">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant/50 mb-4">analytics</span>
          <p className="text-on-surface-variant">
            {hasFilters
              ? 'No data for this filter combination. Try broadening your filters.'
              : 'No data available for the selected period. Try adjusting the time range.'}
          </p>
        </div>
      )}
    </div>
  )
}
