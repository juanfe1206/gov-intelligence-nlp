'use client'

import { useEffect, useState } from 'react'
import VolumeChart from '@/components/charts/VolumeChart'
import SentimentChart from '@/components/charts/SentimentChart'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

// Default: last 7 days
function getDefaultDates() {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 6)
  const fmt = (d: Date) => {
    const year = d.getFullYear()
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  return { startDate: fmt(start), endDate: fmt(end) }
}

// Type definitions
interface VolumeData {
  data: Array<{ date: string; count: number }>
  total: number
}

interface SentimentData {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

export default function DashboardContent() {
  const { startDate, endDate } = getDefaultDates()
  const [volumeData, setVolumeData] = useState<VolumeData | null>(null)
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const params = `start_date=${startDate}&end_date=${endDate}`
        const [volRes, sentRes] = await Promise.all([
          fetch(`${API_BASE}/analytics/volume?${params}`),
          fetch(`${API_BASE}/analytics/sentiment?${params}`),
        ])
        if (!volRes.ok || !sentRes.ok) throw new Error('Failed to fetch analytics data')
        const [vol, sent] = await Promise.all([volRes.json(), sentRes.json()])
        setVolumeData(vol)
        setSentimentData(sent)
      } catch (_e) {
        setError('Unable to load analytics data. Check that the backend is running.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [startDate, endDate])

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

  if (isEmpty) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No data available for the selected period. Try adjusting the time range.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="col-span-12">
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Dashboard
        </h2>
        <p className="mt-1 text-muted [font-size:var(--font-size-small)]">
          Last 7 days · {startDate} – {endDate}
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
    </>
  )
}
