'use client'

import { useEffect, useState } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

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
      className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary"
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

  function handlePartyToggle(partyName: string) {
    const current = filters.selectedParties || []
    const updated = current.includes(partyName)
      ? current.filter((p) => p !== partyName)
      : [...current, partyName]
    onChange({ ...filters, selectedParties: updated })
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
    <div className="flex flex-wrap gap-3 items-center">
      <select
        value={filters.topic}
        onChange={(e) => handleTopicChange(e.target.value)}
        className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary"
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
        className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <option value="">All Subtopics</option>
        {subtopics.map((s) => (
          <option key={s.name} value={s.name}>{s.label}</option>
        ))}
      </select>

      <select
        value={filters.target}
        onChange={(e) => onChange({ ...filters, target: e.target.value })}
        className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary"
      >
        <option value="">All Parties / Leaders</option>
        {targets.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.platform}
        onChange={(e) => onChange({ ...filters, platform: e.target.value })}
        className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary"
      >
        <option value="">All Platforms</option>
        {platforms.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Party multi-select dropdown */}
      <div className="relative group">
        <button
          type="button"
          className="px-3 py-2 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-on-surface hover:border-outline transition-colors focus:outline-none focus:border-primary min-w-[160px] text-left flex items-center justify-between gap-2"
        >
          <span>
            {(filters.selectedParties?.length ?? 0) === 0
              ? 'Compare Parties'
              : `${filters.selectedParties.length} selected`}
          </span>
          <span className="material-symbols-outlined text-sm">expand_more</span>
        </button>
        <div className="absolute top-full left-0 mt-2 w-64 bg-surface-container-high border border-outline-variant/20 rounded-xl shadow-2xl hidden group-hover:block z-50 p-3">
          <p className="text-on-surface-variant text-xs font-bold uppercase tracking-wider mb-2 px-2">Select parties to compare:</p>
          {targets.map((t) => {
            const isSelected = filters.selectedParties?.includes(t.name) ?? false
            return (
              <label
                key={t.name}
                className="flex items-center gap-3 px-2 py-1.5 hover:bg-surface-container rounded-lg cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handlePartyToggle(t.name)}
                  className="rounded border-outline-variant"
                />
                <span className="text-sm text-on-surface">{t.label}</span>
              </label>
            )
          })}
        </div>
      </div>

      <TimeRangeSelect
        startDate={filters.startDate}
        endDate={filters.endDate}
        onChange={(startDate, endDate) => onChange({ ...filters, startDate, endDate })}
      />

      {hasActiveFilters && (
        <button
          onClick={handleClear}
          className="px-4 py-2 rounded-full text-sm font-medium border border-outline-variant/20 text-on-surface-variant hover:text-white hover:bg-surface-container-high transition-colors flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">close</span>
          Clear filters
        </button>
      )}
    </div>
  )
}
