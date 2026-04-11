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
  const posPct = Math.round(subtopic.sentiment_percentage.positive * 100)
  const neuPct = Math.round(subtopic.sentiment_percentage.neutral * 100)
  const negPct = 100 - posPct - neuPct

  return (
    <div className="flex items-center gap-3 py-1">
      <span className="truncate text-on-surface-variant text-sm flex-1">
        {subtopic.subtopic_label}
      </span>
      <div className="flex h-2 w-24 rounded-full overflow-hidden shrink-0">
        {posPct > 0 && (
          <div className="bg-secondary" style={{ width: `${posPct}%` }} />
        )}
        {neuPct > 0 && (
          <div className="bg-tertiary" style={{ width: `${neuPct}%` }} />
        )}
        {negPct > 0 && (
          <div className="bg-error" style={{ width: `${negPct}%` }} />
        )}
      </div>
      <span className="text-error text-sm font-medium whitespace-nowrap">
        {negPct}% neg
      </span>
    </div>
  )
}

function PartyCard({ party }: { party: PartyComparison }) {
  const totalPosts = party.post_count
  const sentiments = [
    { label: 'Positive', count: party.positive_count, color: 'bg-secondary' },
    { label: 'Neutral', count: party.neutral_count, color: 'bg-tertiary' },
    { label: 'Negative', count: party.negative_count, color: 'bg-error' },
  ]

  return (
    <div className="rounded-lg border border-outline-variant/10 bg-surface-container p-5 flex flex-col gap-4">
      <div className="flex items-baseline justify-between border-b border-outline-variant/10 pb-3">
        <h4 className="font-bold text-white text-base">{party.party_label}</h4>
        <span className="text-on-surface-variant text-sm">{totalPosts.toLocaleString()} posts</span>
      </div>

      <div className="flex h-6 w-full overflow-hidden rounded-full">
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
              <div className="hidden group-hover:block absolute top-full mt-1 px-2 py-1 bg-surface-container-high text-white rounded text-xs whitespace-nowrap z-10">
                {s.label}: {s.count}
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex gap-4 text-sm flex-wrap">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-secondary" /> Positive: {(party.sentiment_percentage.positive * 100).toFixed(1)}%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-tertiary" /> Neutral: {(party.sentiment_percentage.neutral * 100).toFixed(1)}%
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-error" /> Negative: {(party.sentiment_percentage.negative * 100).toFixed(1)}%
        </span>
      </div>

      {party.top_subtopics.length > 0 && (
        <div className="border-t border-outline-variant/10 pt-3">
          <p className="text-on-surface-variant text-xs font-bold uppercase tracking-wider mb-2">Top Subtopics</p>
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
      <div className="bg-surface-container-low/50 rounded-lg border border-outline-variant/10 p-6 text-center">
        <span className="material-symbols-outlined text-on-surface-variant text-4xl mb-2">compare_arrows</span>
        <p className="text-on-surface-variant">Select a topic to compare parties.</p>
      </div>
    )
  }

  if (partySlugs.length < 2) {
    return (
      <div className="bg-surface-container-low/50 rounded-lg border border-outline-variant/10 p-6 text-center">
        <span className="material-symbols-outlined text-on-surface-variant text-4xl mb-2">groups</span>
        <p className="text-on-surface-variant">
          Select at least two parties in "Compare Parties" to view a side-by-side comparison.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <div className="flex items-center gap-2 text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          <span>Loading comparison…</span>
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

  const parties = data?.parties ?? []

  if (parties.length === 0) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <p className="text-on-surface-variant">No comparison data available for the selected filters.</p>
      </div>
    )
  }

  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6 shadow-xl">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-primary">compare_arrows</span>
          <h3 className="font-bold text-white text-lg">
            Sentiment Comparison: {data?.topic_label}
          </h3>
        </div>
        <p className="text-on-surface-variant text-sm">
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
