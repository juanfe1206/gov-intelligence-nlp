'use client'

import { useEffect, useState } from 'react'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface Topic {
  name: string
  label: string
  subtopics: Array<{ name: string; label: string }>
}

interface Taxonomy {
  topics: Topic[]
  targets: {
    parties: Array<{ name: string; label: string }>
    leaders: Array<{ name: string; label: string }>
  }
}

export interface FilterState {
  topic: string
  subtopic: string
  target: string
  platform: string
  startDate: string
  endDate: string
  selectedParties: string[]
}

interface Props {
  filters: FilterState
  onChange: (filters: FilterState) => void
}

const DEFAULT_DAYS = 3650

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last year', days: 365 },
  { label: 'All time', days: 3650 },
]

export function getDefaultDates(days = 7) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (days - 1))
  const fmt = (d: Date) => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return { startDate: fmt(start), endDate: fmt(end) }
}

interface TimeRangeProps {
  startDate: string
  endDate: string
  onChange: (start: string, end: string) => void
}

function TimeRangeSelect({ startDate, endDate, onChange }: TimeRangeProps) {
  const activePreset = PRESETS.find(({ days }) => {
    const { startDate: ps, endDate: pe } = getDefaultDates(days)
    return ps === startDate && pe === endDate
  })

  return (
    <select
      value={activePreset?.days ?? 'custom'}
      onChange={(e) => {
        const days = parseInt(e.target.value)
        if (!isNaN(days)) {
          const { startDate: s, endDate: en } = getDefaultDates(days)
          onChange(s, en)
        }
      }}
      className="w-full rounded-full border border-outline-variant/20 bg-surface-container px-3 py-2.5 text-sm font-medium text-on-surface transition-colors hover:border-outline focus:border-primary focus:outline-none sm:w-auto sm:min-w-[10rem] sm:py-2"
    >
      {PRESETS.map(({ label, days }) => (
        <option key={days} value={days}>{label}</option>
      ))}
      {!activePreset && <option value="custom">Custom range</option>}
    </select>
  )
}

export default function FilterBar({ filters, onChange }: Props) {
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null)
  const [platforms, setPlatforms] = useState<string[]>([])
  const defaultDates = getDefaultDates(DEFAULT_DAYS)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/taxonomy`).then((r) => r.json()),
      fetch(`${API_BASE}/analytics/platforms`).then((r) => r.json()),
    ])
      .then(([tax, plat]) => {
        setTaxonomy(tax)
        setPlatforms(plat.platforms ?? [])
      })
      .catch(() => {
        // Silently fail - filter options will be empty
      })
  }, [])

  const selectedTopic = taxonomy?.topics.find((t) => t.name === filters.topic)
  const subtopics = selectedTopic?.subtopics ?? []

  function handleTopicChange(value: string) {
    onChange({ ...filters, topic: value, subtopic: '' })
  }

  function handleClear() {
    const { startDate, endDate } = getDefaultDates(DEFAULT_DAYS)
    onChange({ topic: '', subtopic: '', target: '', platform: '', startDate, endDate, selectedParties: [] })
  }

  const targets = taxonomy
    ? [
        ...taxonomy.targets.parties,
        ...taxonomy.targets.leaders,
      ]
    : []

  const hasActiveFilters =
    filters.topic ||
    filters.subtopic ||
    filters.target ||
    filters.platform ||
    (filters.selectedParties?.length ?? 0) > 0 ||
    filters.startDate !== defaultDates.startDate ||
    filters.endDate !== defaultDates.endDate

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <select
        value={filters.topic}
        onChange={(e) => handleTopicChange(e.target.value)}
        className="w-full rounded-full border border-outline-variant/20 bg-surface-container px-3 py-2.5 text-sm font-medium text-on-surface transition-colors hover:border-outline focus:border-primary focus:outline-none sm:w-auto sm:min-w-[10rem] sm:py-2"
      >
        <option value="">All Topics</option>
        {taxonomy?.topics.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.subtopic}
        onChange={(e) => onChange({ ...filters, subtopic: e.target.value })}
        disabled={!filters.topic}
        className="w-full rounded-full border border-outline-variant/20 bg-surface-container px-3 py-2.5 text-sm font-medium text-on-surface transition-colors hover:border-outline focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[10rem] sm:py-2"
      >
        <option value="">All Subtopics</option>
        {subtopics.map((s) => (
          <option key={s.name} value={s.name}>{s.label}</option>
        ))}
      </select>

      <select
        value={filters.target}
        onChange={(e) => onChange({ ...filters, target: e.target.value })}
        className="w-full rounded-full border border-outline-variant/20 bg-surface-container px-3 py-2.5 text-sm font-medium text-on-surface transition-colors hover:border-outline focus:border-primary focus:outline-none sm:w-auto sm:min-w-[12rem] sm:py-2"
      >
        <option value="">All Parties / Leaders</option>
        {targets.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.platform}
        onChange={(e) => onChange({ ...filters, platform: e.target.value })}
        className="w-full rounded-full border border-outline-variant/20 bg-surface-container px-3 py-2.5 text-sm font-medium text-on-surface transition-colors hover:border-outline focus:border-primary focus:outline-none sm:w-auto sm:min-w-[9rem] sm:py-2"
      >
        <option value="">All Platforms</option>
        {platforms.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      <TimeRangeSelect
        startDate={filters.startDate}
        endDate={filters.endDate}
        onChange={(startDate, endDate) => onChange({ ...filters, startDate, endDate })}
      />

      {hasActiveFilters && (
        <button
          onClick={handleClear}
          className="flex w-full items-center justify-center gap-2 rounded-full border border-outline-variant/20 px-4 py-2.5 text-sm font-medium text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-white sm:w-auto sm:py-2"
        >
          <span className="material-symbols-outlined text-sm">close</span>
          Clear filters
        </button>
      )}
    </div>
  )
}
