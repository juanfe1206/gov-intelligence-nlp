'use client'

import { useEffect, useMemo, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface SubtopicSentiment {
  subtopic: string
  subtopic_label: string
  positive_count: number
  neutral_count: number
  negative_count: number
  total: number
  sentiment_percentage: {
    positive: number
    neutral: number
    negative: number
  }
}

interface PartyComparison {
  party: string
  party_label: string
  post_count: number
  positive_count: number
  neutral_count: number
  negative_count: number
  sentiment_percentage: {
    positive: number
    neutral: number
    negative: number
  }
  top_subtopics: SubtopicSentiment[]
}

interface ComparisonData {
  topic: string
  topic_label: string
  parties: PartyComparison[]
  total_posts: number
  date_range: {
    start_date: string
    end_date: string
  }
}

interface Props {
  filters: FilterState
}

/** Slugs sent to /analytics/compare — multi-select takes precedence over single target. */
function comparisonPartySlugs(filters: FilterState): string[] {
  if (filters.selectedParties?.length) return filters.selectedParties
  if (filters.target) return [filters.target]
  return []
}

function SubtopicItem({ subtopic }: { subtopic: SubtopicSentiment }) {
  const negPct = (subtopic.sentiment_percentage.negative * 100).toFixed(0)
  return (
    <div className="flex items-center justify-between text-muted [font-size:var(--font-size-small)] py-1">
      <span className="truncate">{subtopic.subtopic_label}</span>
      <span className="text-sentiment-negative whitespace-nowrap ml-2">{negPct}% negative</span>
    </div>
  )
}

function PartyCard({ party }: { party: PartyComparison }) {
  const totalPosts = party.post_count
  const sentiments = [
    { label: 'Positive', count: party.positive_count, color: 'bg-sentiment-positive' },
    { label: 'Neutral', count: party.neutral_count, color: 'bg-muted' },
    { label: 'Negative', count: party.negative_count, color: 'bg-sentiment-negative' },
  ]

  return (
    <div className="rounded border border-border bg-surface-raised p-4 flex flex-col gap-3">
      <div className="flex items-baseline justify-between border-b border-border pb-2">
        <h4 className="font-medium text-foreground [font-size:var(--font-size-h4)]">{party.party_label}</h4>
        <span className="text-muted [font-size:var(--font-size-small)]">{totalPosts.toLocaleString()} posts</span>
      </div>

      <div className="flex h-6 w-full overflow-hidden rounded">
        {sentiments.map((s) => {
          const widthPct = totalPosts > 0 ? (s.count / totalPosts) * 100 : 0
          const pctLabel = (
            party.sentiment_percentage[s.label.toLowerCase() as 'positive' | 'neutral' | 'negative'] * 100
          ).toFixed(1)
          return (
            <div
              key={s.label}
              className={`h-full shrink-0 ${s.color} opacity-80 hover:opacity-100 transition-opacity group relative`}
              style={{ width: `${widthPct}%` }}
              title={`${s.label}: ${s.count} (${pctLabel}%)`}
            >
              <div className="hidden group-hover:block absolute top-full mt-1 px-2 py-1 bg-foreground text-surface rounded [font-size:var(--font-size-small)] whitespace-nowrap z-10">
                {s.label}: {s.count}
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex gap-4 text-muted [font-size:var(--font-size-small)] flex-wrap">
        <span>
          <span className="text-sentiment-positive">●</span> Positive: {(party.sentiment_percentage.positive * 100).toFixed(1)}%
        </span>
        <span>
          <span className="text-muted">●</span> Neutral: {(party.sentiment_percentage.neutral * 100).toFixed(1)}%
        </span>
        <span>
          <span className="text-sentiment-negative">●</span> Negative: {(party.sentiment_percentage.negative * 100).toFixed(1)}%
        </span>
      </div>

      {party.top_subtopics.length > 0 && (
        <div className="border-t border-border pt-3">
          <p className="text-muted [font-size:var(--font-size-small)] font-medium mb-2">Top Subtopics</p>
          <div className="flex flex-col gap-1">
            {party.top_subtopics.slice(0, 5).map((st) => (
              <SubtopicItem key={st.subtopic} subtopic={st} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ComparisonPanel({ filters }: Props) {
  const [data, setData] = useState<ComparisonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const partySlugs = useMemo(() => comparisonPartySlugs(filters), [filters])

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchComparison() {
      setError(null)

      if (!filters.topic) {
        setData(null)
        setLoading(false)
        return
      }
      if (partySlugs.length < 2) {
        setData(null)
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const params = new URLSearchParams({
          topic: filters.topic,
          start_date: filters.startDate,
          end_date: filters.endDate,
        })
        partySlugs.forEach((party) => params.append('parties', party))
        if (filters.platform) {
          params.append('platform', filters.platform)
        }

        const res = await fetch(`${API_BASE}/analytics/compare?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) {
          if (res.status === 400) {
            const errData = (await res.json().catch(() => ({}))) as { detail?: string }
            const detail = errData.detail
            if (!isActive) return
            setError(
              typeof detail === 'string'
                ? detail
                : 'Select at least two parties to run a comparison.',
            )
            return
          }
          throw new Error('Failed to fetch comparison data')
        }
        const json = (await res.json()) as ComparisonData
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load comparison data.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchComparison()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters.topic, filters.startDate, filters.endDate, filters.platform, partySlugs])

  if (!filters.topic) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Select a topic to compare parties.</p>
      </div>
    )
  }

  if (partySlugs.length < 2) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          Select at least two parties in &quot;Compare Parties&quot; to view a side-by-side comparison.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading comparison…</p>
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

  const parties = data?.parties ?? []

  if (parties.length === 0) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No comparison data available for the selected filters.
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="mb-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          Sentiment Comparison: {data?.topic_label}
        </h3>
        <p className="text-muted [font-size:var(--font-size-small)] mt-1">
          {data?.date_range.start_date} to {data?.date_range.end_date} — {data?.total_posts.toLocaleString()} posts
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {parties.map((party) => (
          <PartyCard key={party.party} party={party} />
        ))}
      </div>
    </div>
  )
}
