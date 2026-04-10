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
      <div className="col-span-12 rounded-lg border border-border bg-surface-raised p-4">
        <p className="text-sentiment-negative [font-size:var(--font-size-body)]">
          {error}
        </p>
      </div>
    )
  }

  if (spikes.length === 0) return null

  return (
    <div className="col-span-12 rounded-lg border border-border bg-surface-raised p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-sentiment-negative font-semibold [font-size:var(--font-size-body)]">
          ⚠ Spike Alerts
        </span>
        <span className="text-muted [font-size:var(--font-size-small)]">
          {spikes.length} topic{spikes.length !== 1 ? 's' : ''} flagged
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {spikes.map((alert, i) => (
          <div
            key={`${alert.topic}-${alert.spike_type}-${i}`}
            className="flex items-center justify-between rounded border border-border bg-surface px-3 py-2"
          >
            <div className="flex items-center gap-3">
              <span className="text-sentiment-negative [font-size:var(--font-size-small)] font-medium">
                <span
                  className={`inline-block w-2 h-2 rounded-full mr-1 ${
                    alert.spike_type === 'volume' ? 'bg-primary' : 'bg-sentiment-negative'
                  }`}
                />
                {alert.spike_type === 'volume' ? 'Volume' : 'Sentiment'} spike
              </span>
              <span className="text-foreground [font-size:var(--font-size-body)]">
                {alert.topic_label}
              </span>
              <span className="text-muted [font-size:var(--font-size-small)]">
                {formatMagnitude(alert)} in last {alert.window_hours}h
              </span>
            </div>
            <button
              onClick={() => {
                const t = encodeURIComponent(alert.topic)
                const q = encodeURIComponent(alert.suggested_question)
                router.push(`/qa?topic=${t}&question=${q}`)
              }}
              className="px-3 py-1 rounded border border-border text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] whitespace-nowrap"
            >
              Investigate →
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
