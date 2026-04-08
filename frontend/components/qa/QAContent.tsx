'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { getDefaultDates } from '@/components/dashboard/FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const PRESET_QUESTIONS = [
  "What's spiking?",
  "How are we doing on housing versus the opposition?",
  "Main negative narratives about our leader?",
  "Which topics have the most negative sentiment?",
]

// Type definitions matching backend schema
interface QAPostItem {
  id: string
  original_text: string
  platform: string
  created_at: string
  sentiment: 'positive' | 'neutral' | 'negative'
  topic: string
  topic_label: string
  subtopic: string | null
  subtopic_label: string | null
  author: string | null
  target: string | null
  intensity: number | null
  similarity_score: number
}

interface QAMetrics {
  total_retrieved: number
  positive_count: number
  neutral_count: number
  negative_count: number
  top_subtopics: Array<{ subtopic: string; subtopic_label: string; count: number }>
}

interface NarrativeCluster {
  label: string
  sentiment: string               // "positive" | "neutral" | "negative"
  post_count: number
  representative_posts: QAPostItem[]   // up to 2 items
}

interface QAResponse {
  question: string
  filters_applied: {
    topic: string | null
    subtopic: string | null
    party: string | null
    start_date: string | null
    end_date: string | null
    platform: string | null
  }
  retrieved_posts: QAPostItem[]
  metrics: QAMetrics
  insufficient_data: boolean
  summary: string | null
  answer_error: string | null
  clusters: NarrativeCluster[]    // 2-4 items, or empty when insufficient_data
}

// Taxonomy types for filter panel
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

// Q&A filter state (simpler than FilterBar's FilterState)
interface QAFilterState {
  topic: string       // '' = no filter
  subtopic: string    // '' = no filter; only meaningful when topic is set
  party: string       // '' = no filter; maps to backend QAFilters.party
  platform: string    // '' = no filter
  startDate: string   // "YYYY-MM-DD" or '' = no filter
  endDate: string     // "YYYY-MM-DD" or '' = no filter
}

const DEFAULT_FILTERS: QAFilterState = {
  topic: '', subtopic: '', party: '', platform: '', startDate: '', endDate: ''
}

const QA_TIME_PRESETS = [
  { label: 'All time', days: 0 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
]

function sentimentStyles(sentiment: string) {
  switch (sentiment) {
    case 'positive':
      return 'text-sentiment-positive bg-sentiment-positive/10'
    case 'negative':
      return 'text-sentiment-negative bg-sentiment-negative/10'
    default:
      return 'text-muted bg-muted/10'
  }
}

function EvidencePostCard({ post }: { post: QAPostItem }) {
  return (
    <div className="rounded border border-border bg-surface p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${sentimentStyles(post.sentiment)}`}
        >
          {post.sentiment}
        </span>
        <span className="text-muted [font-size:var(--font-size-small)]">{post.platform}</span>
      </div>
      <p className="text-foreground [font-size:var(--font-size-body)] [line-height:var(--line-height-body)] line-clamp-3">
        {post.original_text}
      </p>
      <div className="flex items-center justify-between text-muted [font-size:var(--font-size-small)]">
        <span>
          {post.topic_label}
          {post.subtopic_label && ` › ${post.subtopic_label}`}
        </span>
        <span>{post.created_at}</span>
      </div>
    </div>
  )
}

function MetricsStrip({ metrics }: { metrics: QAMetrics }) {
  const total = metrics.total_retrieved
  const pos = metrics.positive_count
  const neu = metrics.neutral_count
  const neg = metrics.negative_count

  return (
    <div className="flex flex-wrap items-center gap-4 [font-size:var(--font-size-body)]">
      <div className="flex items-center gap-1.5">
        <span className="font-semibold text-foreground">{total.toLocaleString()}</span>
        <span className="text-muted">posts</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-sentiment-positive" />
        <span className="text-sentiment-positive">{pos}</span>
        <span className="text-muted">positive</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-muted" />
        <span className="text-muted">{neu}</span>
        <span className="text-muted">neutral</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-sentiment-negative" />
        <span className="text-sentiment-negative">{neg}</span>
        <span className="text-muted">negative</span>
      </div>
    </div>
  )
}

function NarrativeClusterCard({ cluster }: { cluster: NarrativeCluster }) {
  return (
    <div className="rounded border border-border bg-surface p-4 flex flex-col gap-3">
      {/* Header: label + sentiment tag + post count */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="font-medium text-foreground [font-size:var(--font-size-body)]">
          {cluster.label}
        </span>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${sentimentStyles(cluster.sentiment)}`}>
            {cluster.sentiment}
          </span>
          <span className="text-muted [font-size:var(--font-size-small)]">
            {cluster.post_count.toLocaleString()} posts
          </span>
        </div>
      </div>
      {/* Representative quotes */}
      {cluster.representative_posts.length > 0 && (
        <div className="flex flex-col gap-2">
          {cluster.representative_posts.map((post) => (
            <blockquote
              key={post.id}
              className="border-l-2 border-border pl-3 text-muted [font-size:var(--font-size-small)] [line-height:var(--line-height-body)] line-clamp-2"
            >
              {post.original_text}
            </blockquote>
          ))}
        </div>
      )}
    </div>
  )
}

export default function QAContent() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Filter panel state
  const [filterOpen, setFilterOpen] = useState(false)
  const [qaFilters, setQAFilters] = useState<QAFilterState>(DEFAULT_FILTERS)
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null)
  const [platforms, setPlatforms] = useState<string[]>([])

  const searchParams = useSearchParams()

  // Compute if any filter is active
  const hasActiveFilters =
    qaFilters.topic !== '' ||
    qaFilters.subtopic !== '' ||
    qaFilters.party !== '' ||
    qaFilters.platform !== '' ||
    qaFilters.startDate !== '' ||
    qaFilters.endDate !== ''

  // Fetch taxonomy and platforms on mount
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
        // Silently fail — filter options will be empty
      })
  }, [])

  // Apply URL params on mount and when they change (from SpikeAlertBanner or TopicsPanel navigation)
  useEffect(() => {
    const questionParam = searchParams.get('question')
    const topicParam = searchParams.get('topic')
    if (questionParam) setQuestion(questionParam)
    if (topicParam) {
      setQAFilters((f) => ({ ...f, topic: topicParam }))
      setFilterOpen(true)   // open filter panel so user sees the pre-set topic
    }
  }, [searchParams])

  // Cleanup: abort any in-flight request on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  const handlePresetClick = useCallback((preset: string) => {
    setQuestion(preset)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!question.trim()) return

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setLoading(true)
    setError(null)
    setResult(null)

    // Build filters object only when any filter is active
    const activeFilters = hasActiveFilters ? {
      topic: qaFilters.topic || undefined,
      subtopic: qaFilters.subtopic || undefined,
      party: qaFilters.party || undefined,
      platform: qaFilters.platform || undefined,
      start_date: qaFilters.startDate || undefined,
      end_date: qaFilters.endDate || undefined,
    } : undefined

    const body: Record<string, unknown> = { question: question.trim() }
    if (activeFilters) body.filters = activeFilters

    try {
      const response = await fetch(`${API_BASE}/qa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error('Failed to fetch answer')
      }

      let data: QAResponse
      try {
        data = await response.json()
      } catch {
        throw new Error('Invalid response from server.')
      }
      setResult(data)
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      setError('Unable to reach the server. Check that the backend is running.')
    } finally {
      // Only clear loading if this is still the active request
      if (abortControllerRef.current === controller) {
        setLoading(false)
      }
    }
  }, [question, qaFilters, hasActiveFilters])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  // Determine what to render in the answer area
  const renderAnswerArea = () => {
    if (loading) {
      return (
        <div className="col-span-12 flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-muted [font-size:var(--font-size-body)]">Analyzing discourse…</p>
          </div>
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

    if (!result) {
      return null
    }

    if (result.insufficient_data) {
      return (
        <div className="col-span-12">
          <p className="text-muted [font-size:var(--font-size-body)]">
            Not enough data to answer this question. Try a broader question.
          </p>
        </div>
      )
    }

    // Render the Insight Summary Panel
    return (
      <div className="col-span-12 flex flex-col gap-6">
        {/* Warning Banner (if answer_error present) */}
        {result.answer_error && (
          <div className="rounded border border-sentiment-warning/30 bg-sentiment-warning/10 p-4">
            <p className="text-sentiment-warning [font-size:var(--font-size-body)]">
              {result.answer_error}
            </p>
          </div>
        )}

        {/* Summary Section */}
        {result.summary && (
          <div className="flex flex-col gap-2">
            <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">Summary</h3>
            <p className="text-foreground [font-size:var(--font-size-body)] [line-height:var(--line-height-body)]">
              {result.summary}
            </p>
          </div>
        )}

        {/* Metrics Strip */}
        <div className="flex flex-col gap-2">
          <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">Key Metrics</h3>
          <MetricsStrip metrics={result.metrics} />
        </div>

        {/* Evidence Posts */}
        {result.retrieved_posts.length > 0 && (
          <div className="flex flex-col gap-3">
            <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
              Evidence Posts
            </h3>
            <div className="grid grid-cols-1 gap-4">
              {result.retrieved_posts.slice(0, 5).map((post) => (
                <EvidencePostCard key={post.id} post={post} />
              ))}
            </div>
          </div>
        )}

        {/* Narrative Clusters — only show when there are at least 2 distinct clusters */}
        {result.clusters.length >= 2 && (
          <div className="flex flex-col gap-3">
            <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
              Narrative Clusters
            </h3>
            <div className="grid grid-cols-1 gap-4">
              {result.clusters.slice(0, 4).map((cluster, i) => (
                <NarrativeClusterCard key={`${cluster.label}-${i}`} cluster={cluster} />
              ))}
            </div>
          </div>
        )}

        {/* Scope Label */}
        {(() => {
          const total = result.metrics.total_retrieved.toLocaleString()
          const sd = result.filters_applied.start_date
          const ed = result.filters_applied.end_date
          let label = `Based on ${total} posts`
          if (sd && ed) label += ` · ${sd} to ${ed}`
          else if (sd) label += ` · from ${sd}`
          else if (ed) label += ` · up to ${ed}`
          return (
            <p className="text-muted [font-size:var(--font-size-small)]">
              {label}
            </p>
          )
        })()}
      </div>
    )
  }

  return (
    <div className="col-span-12 flex flex-col gap-6">
      {/* Header */}
      <div>
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Q&A
        </h2>
        <p className="mt-2 text-muted [font-size:var(--font-size-body)] [line-height:var(--line-height-body)]">
          Ask political questions and get AI-powered insights based on social media data.
        </p>
      </div>

      {/* Question Input Section */}
      <div className="bg-surface-raised rounded-lg border border-border p-4 flex flex-col gap-4">
        {/* Text Input */}
        <div className="flex flex-col gap-2">
          <label htmlFor="question" className="font-medium text-foreground [font-size:var(--font-size-body)]">
            Your Question
          </label>
          <div className="flex gap-2">
            <input
              id="question"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about political discourse…"
              maxLength={500}
              className="flex-1 px-4 py-2 rounded border border-border bg-surface text-foreground placeholder:text-muted [font-size:var(--font-size-body)] focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              className="px-6 py-2 rounded bg-primary text-white font-medium [font-size:var(--font-size-body)] hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Analyzing…' : 'Ask'}
            </button>
          </div>
        </div>

        {/* Preset Suggestion Chips */}
        <div className="flex flex-col gap-2">
          <span className="text-muted [font-size:var(--font-size-small)]">Suggested questions:</span>
          <div className="flex flex-wrap gap-2">
            {PRESET_QUESTIONS.map((preset) => (
              <button
                key={preset}
                onClick={() => handlePresetClick(preset)}
                className="px-3 py-1.5 rounded-full border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] transition-colors"
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Filter Toggle Button */}
          <button
            type="button"
            onClick={() => setFilterOpen((o) => !o)}
            className="self-start text-muted hover:text-foreground [font-size:var(--font-size-small)] flex items-center gap-1 mt-1"
          >
            Filters {filterOpen ? '▲' : '▼'}
          </button>
        </div>

        {/* Filter Panel */}
        {filterOpen && (
          <div className="flex flex-wrap gap-2 items-center pt-2 border-t border-border">
            {/* Topic select */}
            <select
              value={qaFilters.topic}
              onChange={(e) => {
                const topic = e.target.value
                setQAFilters((f) => ({
                  ...f,
                  topic,
                  subtopic: '', // reset subtopic when topic changes
                }))
              }}
              className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
            >
              <option value="">All Topics</option>
              {taxonomy?.topics.map((t) => (
                <option key={t.name} value={t.name}>{t.label}</option>
              ))}
            </select>

            {/* Subtopic select */}
            <select
              value={qaFilters.subtopic}
              onChange={(e) => setQAFilters((f) => ({ ...f, subtopic: e.target.value }))}
              disabled={!qaFilters.topic}
              className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground disabled:opacity-50"
            >
              <option value="">All Subtopics</option>
              {(() => {
                const selectedTopic = taxonomy?.topics.find((t) => t.name === qaFilters.topic)
                return selectedTopic?.subtopics.map((s) => (
                  <option key={s.name} value={s.name}>{s.label}</option>
                ))
              })()}
            </select>

            {/* Party/Target select */}
            <select
              value={qaFilters.party}
              onChange={(e) => setQAFilters((f) => ({ ...f, party: e.target.value }))}
              className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
            >
              <option value="">All Parties / Leaders</option>
              {(() => {
                const targets = taxonomy
                  ? [...taxonomy.targets.parties, ...taxonomy.targets.leaders]
                  : []
                return targets.map((t) => (
                  <option key={t.name} value={t.name}>{t.label}</option>
                ))
              })()}
            </select>

            {/* Platform select */}
            <select
              value={qaFilters.platform}
              onChange={(e) => setQAFilters((f) => ({ ...f, platform: e.target.value }))}
              className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
            >
              <option value="">All Platforms</option>
              {platforms.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>

            {/* Time range select */}
            {(() => {
              // Compute selected preset from startDate/endDate
              const selectedPreset = QA_TIME_PRESETS.find(({ days }) => {
                if (days === 0) return qaFilters.startDate === '' && qaFilters.endDate === ''
                const { startDate: ps, endDate: pe } = getDefaultDates(days)
                return qaFilters.startDate === ps && qaFilters.endDate === pe
              })
              return (
                <select
                  value={selectedPreset?.days ?? 0}
                  onChange={(e) => {
                    const days = parseInt(e.target.value)
                    if (days === 0) {
                      setQAFilters((f) => ({ ...f, startDate: '', endDate: '' }))
                    } else {
                      const { startDate, endDate } = getDefaultDates(days)
                      setQAFilters((f) => ({ ...f, startDate, endDate }))
                    }
                  }}
                  className="border border-border rounded px-2 py-1 [font-size:var(--font-size-small)] bg-surface text-foreground"
                >
                  {QA_TIME_PRESETS.map(({ label, days }) => (
                    <option key={days} value={days}>{label}</option>
                  ))}
                </select>
              )
            })()}

            {/* Clear filters button */}
            {hasActiveFilters && (
              <button
                type="button"
                onClick={() => { setQAFilters(DEFAULT_FILTERS) }}
                className="px-2 py-1 border border-border rounded text-muted hover:text-foreground [font-size:var(--font-size-small)]"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Answer Area */}
      {renderAnswerArea()}
    </div>
  )
}