'use client'

import { useEffect, useState } from 'react'
import VolumeChart from '@/components/charts/VolumeChart'
import SentimentChart from '@/components/charts/SentimentChart'
import FilterBar, { FilterState, getDefaultDates } from './FilterBar'
import TopicsPanel from './TopicsPanel'
import PostsPanel from './PostsPanel'
import ComparisonPanel from './ComparisonPanel'
import SpikeAlertBanner from './SpikeAlertBanner'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// Type definitions
interface VolumeData {
  data: Array<{ date: string; count: number }>
  total: number
}

interface SentimentData {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function DashboardContent() {
  const defaultDates = getDefaultDates(7)
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
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })
        if (filters.topic) params.set('topic', filters.topic)
        if (filters.subtopic) params.set('subtopic', filters.subtopic)
        if (filters.target) params.set('target', filters.target)
        if (filters.platform) params.set('platform', filters.platform)

        const [volRes, sentRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/volume?${params.toString()}`, { signal: controller.signal }),
          fetch(`${API_BASE}/analytics/sentiment?${params.toString()}`, { signal: controller.signal }),
        ])
        if (!volRes.ok || !sentRes.ok) throw new Error('Failed to fetch analytics data')
        const [vol, sent] = await Promise.all([volRes.json(), sentRes.json()])
        if (!isActive) return
        setVolumeData(vol)
        setSentimentData(sent)
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
        <SpikeAlertBanner filters={filters} />
        <FilterBar filters={filters} onChange={setFilters} />
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
      <SpikeAlertBanner filters={filters} />
      <FilterBar filters={filters} onChange={setFilters} />

      <div className="col-span-12">
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Dashboard
        </h2>
        <p className="mt-1 text-muted [font-size:var(--font-size-small)]">
          {filters.startDate} – {filters.endDate}
        </p>
      </div>

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
