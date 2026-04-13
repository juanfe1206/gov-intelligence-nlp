'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FilterState } from './FilterBar'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface SubtopicItem {
  name: string
  label: string
  count: number
  positive: number
  neutral: number
  negative: number
}

interface TopicItem {
  name: string
  label: string
  count: number
  positive: number
  neutral: number
  negative: number
  subtopics: SubtopicItem[]
}

interface TopicsData {
  topics: TopicItem[]
}

interface Props {
  filters: FilterState
  onTopicSelect: (topicName: string) => void
  onClearTopic: () => void
}

export default function TopicsPanel({ filters, onTopicSelect, onClearTopic }: Props) {
  const [data, setData] = useState<TopicsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchTopics() {
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

        const res = await fetch(`${API_BASE}/analytics/topics?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch topics')
        const json = await res.json()
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load topics data.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchTopics()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters])

  const topics = data?.topics ?? []
  const isDrillDown = Boolean(filters.topic)

  // Determine items to display: when topic filter is set, show that topic's subtopics
  const displayItems: Array<{ name: string; label: string; count: number; positive: number; neutral: number; negative: number }> =
    isDrillDown && topics.length > 0
      ? topics[0].subtopics
      : topics

  const panelTitle =
    isDrillDown && topics.length > 0
      ? `${topics[0].label} — Subtopics`
      : isDrillDown && filters.topic
        ? `${filters.topic} — Subtopics`
        : 'Topic Distribution'

  const emptyMessage = (() => {
    if (!isDrillDown) {
      return 'No topic data for the selected filters.'
    }
    if (topics.length === 0) {
      return 'No posts matched this topic for the selected date range and filters.'
    }
    return 'No subtopic breakdown for this topic—posts may not specify a subtopic, or none fall in the selected range.'
  })()

  // Badge logic (only for top-level topics view)
  let mostNegativeName = ''
  let mostPositiveName = ''
  if (!isDrillDown && topics.length > 1) {
    const withRatios = topics.map((t) => ({
      name: t.name,
      negRatio: t.count > 0 ? t.negative / t.count : 0,
      posRatio: t.count > 0 ? t.positive / t.count : 0,
    }))
    mostNegativeName = withRatios.reduce((a, b) => (b.negRatio > a.negRatio ? b : a)).name
    mostPositiveName = withRatios.reduce((a, b) => (b.posRatio > a.posRatio ? b : a)).name
  }

  if (loading) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <div className="flex items-center gap-2 text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          <span>Loading topics…</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <p className="text-error">{error}</p>
      </div>
    )
  }

  if (displayItems.length === 0) {
    if (isDrillDown) {
      return (
        <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
          <div className="flex items-center gap-3 mb-4">
            <button
              type="button"
              onClick={onClearTopic}
              className="text-primary text-sm font-medium hover:underline flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-sm">arrow_back</span>
              All topics
            </button>
            <h3 className="font-bold text-white text-lg">{panelTitle}</h3>
          </div>
          <p className="text-on-surface-variant">{emptyMessage}</p>
        </div>
      )
    }
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <p className="text-on-surface-variant">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-outline-variant/10 bg-surface-container-low p-4 shadow-xl sm:p-6">
      <div className="flex items-center gap-3 mb-6">
        {isDrillDown && (
          <button
            type="button"
            onClick={onClearTopic}
            className="text-primary text-sm font-medium hover:underline flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            All topics
          </button>
        )}
        <h3 className="font-bold text-white text-lg">{panelTitle}</h3>
      </div>

      <div className="flex flex-col gap-3">
        {displayItems.map((item) => {
          const total = item.positive + item.neutral + item.negative || 1
          const posW = Math.round((item.positive / total) * 100)
          const neuW = Math.round((item.neutral / total) * 100)
          const negW = 100 - posW - neuW

          return (
            <div
              key={item.name}
              className={`w-full text-left rounded-lg border border-outline-variant/10 p-4 transition-all duration-200 ${
                !isDrillDown ? 'hover:border-primary/50 hover:bg-surface-container cursor-pointer' : ''
              }`}
              onClick={() => !isDrillDown && onTopicSelect(item.name)}
            >
              <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <span className="font-medium text-white">{item.label}</span>
                  {!isDrillDown && item.name === mostNegativeName && (
                    <span className="px-2 py-0.5 rounded-full bg-error/10 text-error text-xs font-bold">
                      Most negative
                    </span>
                  )}
                  {!isDrillDown && item.name === mostPositiveName && item.name !== mostNegativeName && (
                    <span className="px-2 py-0.5 rounded-full bg-secondary/10 text-secondary text-xs font-bold">
                      Most positive
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2 sm:gap-3">
                  <span className="text-sm text-on-surface-variant">
                    {item.count.toLocaleString()} posts
                  </span>
                  {/* Q&A investigate button — top-level only */}
                  {!isDrillDown && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        const q = encodeURIComponent(`What are people saying about ${item.label}?`)
                        router.push(`/qa?topic=${encodeURIComponent(item.name)}&question=${q}`)
                      }}
                      className="flex items-center gap-1 rounded-full border border-outline-variant/20 px-3 py-1 text-xs font-medium text-on-surface-variant transition-colors hover:border-primary hover:text-white"
                    >
                      <span className="material-symbols-outlined text-xs">chat</span>
                      Q&A
                    </button>
                  )}
                </div>
              </div>

              {/* Sentiment bar */}
              <div className="flex h-2 rounded-full overflow-hidden">
                {posW > 0 && (
                  <div className="bg-secondary" style={{ width: `${posW}%` }} />
                )}
                {neuW > 0 && (
                  <div className="bg-tertiary" style={{ width: `${neuW}%` }} />
                )}
                {negW > 0 && (
                  <div className="bg-error" style={{ width: `${negW}%` }} />
                )}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                <span className="font-medium text-secondary">{posW}% Positive</span>
                <span className="font-medium text-tertiary">{neuW}% Neutral</span>
                <span className="font-medium text-error">{negW}% Negative</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
