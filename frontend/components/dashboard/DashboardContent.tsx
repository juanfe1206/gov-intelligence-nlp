'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import VolumeChart from '@/components/charts/VolumeChart'
import SentimentChart from '@/components/charts/SentimentChart'
import FilterBar, { FilterState, getDefaultDates } from './FilterBar'
import TopicsPanel from './TopicsPanel'
import PostsPanel from './PostsPanel'
import ComparisonPanel from './ComparisonPanel'
import SpikeAlertBanner from './SpikeAlertBanner'
import KpiCards from './KpiCards'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

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
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading analytics…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="col-span-12">
        <p className="text-sentiment-negative [font-size:var(--font-size-body)]">{error}</p>
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

  if (isEmpty) {
    return (
      <>
        <div className="col-span-12">
          <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
            Dashboard
          </h2>
          <p className="mt-1 text-muted [font-size:var(--font-size-small)]">
            {filters.startDate} – {filters.endDate}
          </p>
        </div>

        <FilterBar filters={filters} onChange={setFilters} />

        <KpiCards
          totalPosts={kpiData.total}
          positivePct={kpiData.positivePct}
          neutralPct={kpiData.neutralPct}
          negativePct={kpiData.negativePct}
          topTopic={topTopic}
        />

        <SpikeAlertBanner filters={filters} />

        {/* Export and Copy Summary Buttons */}
        <div className="col-span-12 flex justify-end gap-2">
          <button
            onClick={handleCopySummary}
            className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
          >
            {copied ? 'Copied!' : 'Copy summary'}
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
          >
            Export
          </button>
        </div>
        {actionMessage && (
          <div className="col-span-12">
            <p className="text-muted [font-size:var(--font-size-small)]">{actionMessage}</p>
          </div>
        )}

        <TopicsPanel
          filters={filters}
          onTopicSelect={handleTopicSelect}
          onClearTopic={handleClearTopic}
        />
        <ComparisonPanel filters={filters} />
        <PostsPanel filters={filters} />
        <div className="col-span-12">
          <p className="text-muted [font-size:var(--font-size-body)]">
            {hasFilters
              ? 'No data for this filter combination. Try broadening your filters.'
              : 'No data available for the selected period. Try adjusting the time range.'}
          </p>
        </div>
      </>
    )
  }

  return (
    <>
      <div className="col-span-12">
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Dashboard
        </h2>
        <p className="mt-1 text-muted [font-size:var(--font-size-small)]">
          {filters.startDate} – {filters.endDate}
        </p>
      </div>

      <FilterBar filters={filters} onChange={setFilters} />

      <KpiCards
        totalPosts={kpiData.total}
        positivePct={kpiData.positivePct}
        neutralPct={kpiData.neutralPct}
        negativePct={kpiData.negativePct}
        topTopic={topTopic}
      />

      <SpikeAlertBanner filters={filters} />

      {/* Export and Copy Summary Buttons */}
      <div className="col-span-12 flex justify-end gap-2">
        <button
          onClick={handleCopySummary}
          className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
        >
          {copied ? 'Copied!' : 'Copy summary'}
        </button>
        <button
          onClick={handleExport}
          className="px-4 py-2 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-body)]"
        >
          Export
        </button>
      </div>
      {actionMessage && (
        <div className="col-span-12">
          <p className="text-muted [font-size:var(--font-size-small)]">{actionMessage}</p>
        </div>
      )}

      <div className="col-span-12 lg:col-span-6 bg-surface-raised rounded-lg border border-border p-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)] mb-4">
          Post Volume
        </h3>
        <VolumeChart data={volumeData?.data ?? []} />
      </div>

      <div className="col-span-12 lg:col-span-6 bg-surface-raised rounded-lg border border-border p-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)] mb-4">
          Sentiment Over Time
        </h3>
        <SentimentChart data={sentimentData?.data ?? []} />
      </div>

      <TopicsPanel
        filters={filters}
        onTopicSelect={handleTopicSelect}
        onClearTopic={handleClearTopic}
      />
      <ComparisonPanel filters={filters} />
      <PostsPanel filters={filters} />
    </>
  )
}
