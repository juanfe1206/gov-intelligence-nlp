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
      className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
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
    <div className="col-span-12 flex flex-wrap gap-2 items-center">
      <select
        value={filters.topic}
        onChange={(e) => handleTopicChange(e.target.value)}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
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
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground disabled:opacity-50"
      >
        <option value="">All Subtopics</option>
        {subtopics.map((s) => (
          <option key={s.name} value={s.name}>{s.label}</option>
        ))}
      </select>

      <select
        value={filters.target}
        onChange={(e) => onChange({ ...filters, target: e.target.value })}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
      >
        <option value="">All Parties / Leaders</option>
        {targets.map((t) => (
          <option key={t.name} value={t.name}>{t.label}</option>
        ))}
      </select>

      <select
        value={filters.platform}
        onChange={(e) => onChange({ ...filters, platform: e.target.value })}
        className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
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
          className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground min-w-[160px] text-left flex items-center justify-between"
        >
          <span>
            {(filters.selectedParties?.length ?? 0) === 0
              ? 'Compare Parties'
              : `${filters.selectedParties.length} selected`}
          </span>
          <span className="ml-2">▼</span>
        </button>
        <div className="absolute top-full left-0 mt-1 w-64 bg-surface border border-border rounded shadow-lg hidden group-hover:block z-50 p-2">
          <p className="text-muted [font-size:var(--font-size-small)] mb-2 px-2">Select parties to compare:</p>
          {targets.map((t) => {
            const isSelected = filters.selectedParties?.includes(t.name) ?? false
            return (
              <label
                key={t.name}
                className="flex items-center gap-2 px-2 py-1 hover:bg-surface-raised cursor-pointer rounded"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => handlePartyToggle(t.name)}
                  className="rounded"
                />
                <span className="[font-size:var(--font-size-small)]">{t.label}</span>
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
          className="px-2 py-1 border border-border rounded text-muted hover:text-foreground [font-size:var(--font-size-small)]"
        >
          Clear filters
        </button>
      )}
    </div>
  )
}
