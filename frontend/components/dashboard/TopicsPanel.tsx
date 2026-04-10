'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

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
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading topics…</p>
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

  if (displayItems.length === 0) {
    if (isDrillDown) {
      return (
        <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
          <div className="flex items-center gap-3 mb-4">
            <button
              type="button"
              onClick={onClearTopic}
              className="text-primary [font-size:var(--font-size-small)] hover:underline"
            >
              ← All topics
            </button>
            <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">{panelTitle}</h3>
          </div>
          <p className="text-muted [font-size:var(--font-size-body)]">{emptyMessage}</p>
        </div>
      )
    }
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="flex items-center gap-3 mb-4">
        {isDrillDown && (
          <button
            type="button"
            onClick={onClearTopic}
            className="text-primary [font-size:var(--font-size-small)] hover:underline"
          >
            ← All topics
          </button>
        )}
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">{panelTitle}</h3>
      </div>

      <div className="flex flex-col gap-2">
        {displayItems.map((item) => {
          const total = item.positive + item.neutral + item.negative || 1
          const posW = Math.round((item.positive / total) * 100)
          const neuW = Math.round((item.neutral / total) * 100)
          const negW = 100 - posW - neuW

          return (
            <div
              key={item.name}
              className={`w-full text-left rounded border border-border p-3 transition-colors ${
                !isDrillDown ? 'hover:border-primary hover:bg-surface' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <button
                  type="button"
                  onClick={() => !isDrillDown && onTopicSelect(item.name)}
                  disabled={isDrillDown}
                  className={`flex-1 text-left ${!isDrillDown ? 'cursor-pointer' : 'cursor-default'}`}
                >
                  <span className="font-medium text-foreground [font-size:var(--font-size-body)]">
                    {item.label}
                  </span>
                </button>
                <div className="flex items-center gap-2">
                  {!isDrillDown && item.name === mostNegativeName && (
                    <span className="px-1.5 py-0.5 rounded bg-sentiment-negative/10 text-sentiment-negative [font-size:var(--font-size-small)]">
                      Most negative
                    </span>
                  )}
                  {!isDrillDown && item.name === mostPositiveName && item.name !== mostNegativeName && (
                    <span className="px-1.5 py-0.5 rounded bg-sentiment-positive/10 text-sentiment-positive [font-size:var(--font-size-small)]">
                      Most positive
                    </span>
                  )}
                  <span className="text-muted [font-size:var(--font-size-small)]">
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
                      className="px-2 py-0.5 rounded border border-border text-muted hover:text-foreground hover:border-primary [font-size:var(--font-size-small)] whitespace-nowrap"
                    >
                      → Q&A
                    </button>
                  )}
                </div>
              </div>

              {/* Sentiment bar */}
              <div className="flex h-2.5 rounded overflow-hidden gap-px">
                {posW > 0 && (
                  <div className="bg-sentiment-positive" style={{ width: `${posW}%` }} />
                )}
                {neuW > 0 && (
                  <div className="bg-sentiment-warning" style={{ width: `${neuW}%` }} />
                )}
                {negW > 0 && (
                  <div className="bg-sentiment-negative" style={{ width: `${negW}%` }} />
                )}
              </div>
              <div className="flex gap-3 mt-1 [font-size:var(--font-size-small)]">
                <span className="text-sentiment-positive">{posW}%</span>
                <span className="text-sentiment-warning">{neuW}%</span>
                <span className="text-sentiment-negative">{negW}%</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
