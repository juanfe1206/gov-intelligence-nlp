'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface SpikeAlert {
  topic: string
  topic_label: string
  spike_type: 'volume' | 'sentiment'
  magnitude: number
  recent_count: number
  baseline_count: number
  window_hours: number
  suggested_question: string
}

interface SpikesResponse {
  spikes: SpikeAlert[]
  window_hours: number
  detected_at: string
}

interface Props {
  filters: Pick<FilterState, 'platform'>
}

function formatMagnitude(alert: SpikeAlert): string {
  if (alert.spike_type === 'volume') {
    return `${alert.magnitude.toFixed(1)}× increase`
  }
  return `+${(alert.magnitude * 100).toFixed(0)}pp negative sentiment`
}

export default function SpikeAlertBanner({ filters }: Props) {
  const [spikes, setSpikes] = useState<SpikeAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchSpikes() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams()
        if (filters.platform) params.set('platform', filters.platform)

        const res = await fetch(`${API_BASE}/analytics/spikes?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch spikes')
        const json = (await res.json()) as SpikesResponse
        if (!isActive) return
        setSpikes(json.spikes)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setSpikes([])
        setError(
          err instanceof Error ? err.message : 'Failed to load spike alerts',
        )
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchSpikes()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters.platform])

  if (loading) return null

  if (error) {
    return (
      <div className="rounded-lg border border-error/20 bg-error-container/10 p-4">
        <p className="text-error flex items-center gap-2">
          <span className="material-symbols-outlined">error</span>
          {error}
        </p>
      </div>
    )
  }

  if (spikes.length === 0) return null

  return (
    <div className="rounded-xl border border-error/20 bg-error-container/5 p-5 shadow-lg">
      <div className="flex items-center gap-3 mb-4">
        <span className="material-symbols-outlined text-error text-xl animate-pulse">crisis_alert</span>
        <span className="text-error font-bold text-base">
          Spike Alerts
        </span>
        <span className="text-on-surface-variant text-sm">
          {spikes.length} topic{spikes.length !== 1 ? 's' : ''} flagged
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {spikes.map((alert, i) => (
          <div
            key={`${alert.topic}-${alert.spike_type}-${i}`}
            className="flex items-center justify-between rounded-lg border border-outline-variant/10 bg-surface-container p-4 hover:border-error/30 transition-colors"
          >
            <div className="flex items-center gap-4">
              <div className={`flex items-center gap-2 px-2 py-1 rounded-full text-xs font-bold ${
                alert.spike_type === 'volume'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'bg-error/10 text-error border border-error/20'
              }`}>
                <span className="material-symbols-outlined text-xs">
                  {alert.spike_type === 'volume' ? 'trending_up' : 'sentiment_very_dissatisfied'}
                </span>
                {alert.spike_type === 'volume' ? 'Volume' : 'Sentiment'}
              </div>
              <span className="text-white font-medium">
                {alert.topic_label}
              </span>
              <span className="text-on-surface-variant text-sm">
                {formatMagnitude(alert)} in last {alert.window_hours}h
              </span>
            </div>
            <button
              onClick={() => {
                const t = encodeURIComponent(alert.topic)
                const q = encodeURIComponent(alert.suggested_question)
                router.push(`/qa?topic=${t}&question=${q}`)
              }}
              className="px-4 py-2 rounded-full text-sm font-medium bg-primary-container text-white hover:bg-primary-container/90 transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-xs">search</span>
              Investigate
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
