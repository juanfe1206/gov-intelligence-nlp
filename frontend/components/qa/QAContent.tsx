'use client'

import { useState, useRef, useCallback, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { getDefaultDates } from '@/components/dashboard/FilterBar'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

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
  sentiment: string
  post_count: number
  representative_posts: QAPostItem[]
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
  clusters: NarrativeCluster[]
  structured_insight: StructuredInsight | null
}

interface StatItem {
  label: string
  value: string | number
  trend?: 'up' | 'down' | 'neutral'
  trend_value?: string
  context?: string
}

interface TrendItem {
  label: string
  direction: 'rising' | 'falling' | 'stable'
  magnitude: 'high' | 'medium' | 'low'
  volume_change?: string
}

interface KeyTakeaway {
  type: 'positive' | 'negative' | 'neutral' | 'warning' | 'opportunity'
  text: string
}

interface RecommendedAction {
  priority: 'high' | 'medium' | 'low'
  text: string
  rationale?: string
}

interface SentimentSummary {
  positive: string
  neutral: string
  negative: string
  interpretation?: string
}

interface StructuredInsight {
  headline: string
  key_stats: StatItem[]
  sentiment_summary: SentimentSummary | null
  trends: TrendItem[]
  key_takeaways: KeyTakeaway[]
  recommended_actions: RecommendedAction[]
}

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

interface QAFilterState {
  topic: string
  subtopic: string
  party: string
  platform: string
  startDate: string
  endDate: string
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

function sentimentStyles(sentiment: string): { chip: string; icon: string } {
  switch (sentiment) {
    case 'positive':
      return { chip: 'text-secondary bg-secondary/10 border-secondary/20', icon: 'sentiment_satisfied' }
    case 'negative':
      return { chip: 'text-error bg-error/10 border-error/20', icon: 'sentiment_dissatisfied' }
    default:
      return { chip: 'text-tertiary bg-tertiary/10 border-tertiary/20', icon: 'sentiment_neutral' }
  }
}

function formatDateString(isoDate: string): string {
  const date = new Date(isoDate + 'T00:00:00')
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function buildEmptyStateMessage(filters: QAResponse['filters_applied'] | undefined): {
  reason: string
  suggestion: string
} {
  if (!filters) {
    return { reason: 'No posts found for this question.', suggestion: 'Try broadening your question.' }
  }

  const parts: string[] = []
  if (filters.topic) parts.push(`for this topic`)
  if (filters.subtopic) parts.push(`with this subtopic`)
  if (filters.party) parts.push(`from ${filters.party}`)
  if (filters.platform) parts.push(`on ${filters.platform}`)
  if (filters.start_date && filters.end_date) {
    parts.push(`between ${formatDateString(filters.start_date)} and ${formatDateString(filters.end_date)}`)
  } else if (filters.start_date) {
    parts.push(`from ${formatDateString(filters.start_date)}`)
  } else if (filters.end_date) {
    parts.push(`up to ${formatDateString(filters.end_date)}`)
  }

  const reason = parts.length > 0
    ? `No posts found ${parts.slice(0, -1).join(', ')}${parts.length > 1 ? ' and ' : ''}${parts[parts.length - 1]}.`
    : 'No posts found for this question.'

  let suggestion = 'Try broadening your question.'
  if (filters.subtopic) {
    suggestion = 'Try removing the subtopic filter.'
  } else if (filters.start_date || filters.end_date) {
    suggestion = 'Try a wider time range.'
  } else if (filters.party) {
    suggestion = 'Try removing the party filter.'
  } else if (filters.platform) {
    suggestion = 'Try removing the platform filter.'
  } else if (filters.topic) {
    suggestion = 'Try removing the topic filter or asking a broader question.'
  }

  return { reason, suggestion }
}

function EvidencePostCard({ post }: { post: QAPostItem }) {
  const { chip, icon } = sentimentStyles(post.sentiment)

  return (
    <div className="rounded-lg border border-outline-variant/10 bg-surface-container p-5 flex flex-col gap-3 hover:border-outline-variant/30 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold border ${chip}`}>
          <span className="material-symbols-outlined text-xs">{icon}</span>
          {post.sentiment}
        </div>
        <span className="text-on-surface-variant text-sm">{post.platform}</span>
      </div>
      <p className="text-white text-sm leading-relaxed line-clamp-3">
        {post.original_text}
      </p>
      <div className="flex items-center justify-between text-on-surface-variant text-xs">
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
    <div className="flex flex-wrap items-center gap-6 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-bold text-white text-lg">{total.toLocaleString()}</span>
        <span className="text-on-surface-variant">posts</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-secondary" />
        <span className="text-secondary font-medium">{pos}</span>
        <span className="text-on-surface-variant">positive</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-tertiary" />
        <span className="text-tertiary font-medium">{neu}</span>
        <span className="text-on-surface-variant">neutral</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-error" />
        <span className="text-error font-medium">{neg}</span>
        <span className="text-on-surface-variant">negative</span>
      </div>
    </div>
  )
}

function NarrativeClusterCard({ cluster }: { cluster: NarrativeCluster }) {
  const { chip, icon } = sentimentStyles(cluster.sentiment)

  return (
    <div className="rounded-lg border border-outline-variant/10 bg-surface-container p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="font-bold text-white">
          {cluster.label}
        </span>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold border ${chip}`}>
            <span className="material-symbols-outlined text-xs">{icon}</span>
            {cluster.sentiment}
          </div>
          <span className="text-on-surface-variant text-sm">
            {cluster.post_count.toLocaleString()} posts
          </span>
        </div>
      </div>
      {cluster.representative_posts.length > 0 && (
        <div className="flex flex-col gap-2">
          {cluster.representative_posts.map((post) => (
            <blockquote
              key={post.id}
              className="border-l-2 border-primary/50 pl-3 text-on-surface-variant text-sm line-clamp-2 italic"
            >
              "{post.original_text}"
            </blockquote>
          ))}
        </div>
      )}
    </div>
  )
}

// Structured Insight Visualization Components

function HeadlineCard({ headline }: { headline: string }) {
  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-5">
      <div className="flex items-start gap-3">
        <span className="material-symbols-outlined text-primary text-2xl">auto_awesome</span>
        <div>
          <p className="text-lg font-bold text-white leading-tight">{headline}</p>
        </div>
      </div>
    </div>
  )
}

function StatsGrid({ stats }: { stats: StatItem[] }) {
  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up': return 'trending_up'
      case 'down': return 'trending_down'
      case 'neutral': return 'trending_flat'
      default: return null
    }
  }

  const getTrendColor = (trend?: string) => {
    switch (trend) {
      case 'up': return 'text-secondary'
      case 'down': return 'text-error'
      case 'neutral': return 'text-tertiary'
      default: return 'text-on-surface-variant'
    }
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.slice(0, 4).map((stat, i) => (
        <div key={i} className="bg-surface-container rounded-lg border border-outline-variant/10 p-4">
          <div className="text-xs text-on-surface-variant mb-1">{stat.label}</div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">{stat.value}</span>
            {stat.trend && getTrendIcon(stat.trend) && (
              <span className={`material-symbols-outlined text-sm ${getTrendColor(stat.trend)}`}>
                {getTrendIcon(stat.trend)}
              </span>
            )}
          </div>
          {stat.trend_value && (
            <div className={`text-xs ${getTrendColor(stat.trend)}`}>{stat.trend_value}</div>
          )}
          {stat.context && (
            <div className="text-xs text-on-surface-variant mt-1">{stat.context}</div>
          )}
        </div>
      ))}
    </div>
  )
}

function SentimentMiniChart({ summary }: { summary: SentimentSummary | null }) {
  if (!summary) return null

  const pos = parseInt(summary.positive) || 0
  const neu = parseInt(summary.neutral) || 0
  const neg = parseInt(summary.negative) || 0

  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/10 p-4">
      <div className="text-xs text-on-surface-variant mb-3">Sentiment Breakdown</div>
      <div className="flex items-center gap-2 mb-3">
        {/* Horizontal stacked bar */}
        <div className="flex-1 h-3 rounded-full overflow-hidden flex">
          {pos > 0 && (
            <div style={{ width: `${pos}%` }} className="bg-secondary h-full" />
          )}
          {neu > 0 && (
            <div style={{ width: `${neu}%` }} className="bg-tertiary h-full" />
          )}
          {neg > 0 && (
            <div style={{ width: `${neg}%` }} className="bg-error h-full" />
          )}
        </div>
      </div>
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-secondary" />
          <span className="text-secondary font-medium">{summary.positive}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-tertiary" />
          <span className="text-tertiary font-medium">{summary.neutral}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-error" />
          <span className="text-error font-medium">{summary.negative}</span>
        </div>
      </div>
      {summary.interpretation && (
        <div className="text-xs text-on-surface-variant mt-2">{summary.interpretation}</div>
      )}
    </div>
  )
}

function TrendingList({ trends }: { trends: TrendItem[] }) {
  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'rising': return 'trending_up'
      case 'falling': return 'trending_down'
      default: return 'trending_flat'
    }
  }

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'rising': return 'text-secondary'
      case 'falling': return 'text-error'
      default: return 'text-tertiary'
    }
  }

  const getMagnitudeBadge = (magnitude: string) => {
    switch (magnitude) {
      case 'high': return 'bg-secondary/20 text-secondary'
      case 'medium': return 'bg-tertiary/20 text-tertiary'
      default: return 'bg-surface-container-high text-on-surface-variant'
    }
  }

  if (!trends.length) return null

  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/10 p-4">
      <div className="text-xs text-on-surface-variant mb-3">Trending Topics</div>
      <div className="flex flex-wrap gap-2">
        {trends.map((trend, i) => (
          <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface border border-outline-variant/10">
            <span className={`material-symbols-outlined text-sm ${getDirectionColor(trend.direction)}`}>
              {getDirectionIcon(trend.direction)}
            </span>
            <span className="text-sm text-white">{trend.label}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${getMagnitudeBadge(trend.magnitude)}`}>
              {trend.magnitude}
            </span>
            {trend.volume_change && (
              <span className="text-xs text-secondary">{trend.volume_change}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function KeyTakeawaysList({ takeaways }: { takeaways: KeyTakeaway[] }) {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'positive': return 'check_circle'
      case 'negative': return 'error'
      case 'warning': return 'warning'
      case 'opportunity': return 'lightbulb'
      default: return 'info'
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'positive': return 'text-secondary'
      case 'negative': return 'text-error'
      case 'warning': return 'text-tertiary'
      case 'opportunity': return 'text-primary'
      default: return 'text-on-surface-variant'
    }
  }

  if (!takeaways.length) return null

  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/10 p-4">
      <div className="text-xs text-on-surface-variant mb-3">Key Takeaways</div>
      <div className="space-y-2">
        {takeaways.slice(0, 3).map((takeaway, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`material-symbols-outlined text-sm ${getTypeColor(takeaway.type)} mt-0.5`}>
              {getTypeIcon(takeaway.type)}
            </span>
            <p className="text-sm text-white">{takeaway.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecommendedActionsList({ actions }: { actions: RecommendedAction[] }) {
  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-error/20 text-error border-error/30'
      case 'medium': return 'bg-tertiary/20 text-tertiary border-tertiary/30'
      default: return 'bg-surface-container-high text-on-surface-variant border-outline-variant/30'
    }
  }

  if (!actions.length) return null

  return (
    <div className="bg-surface-container rounded-lg border border-outline-variant/10 p-4">
      <div className="text-xs text-on-surface-variant mb-3">Recommended Actions</div>
      <div className="space-y-2">
        {actions.slice(0, 2).map((action, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className={`text-xs px-2 py-0.5 rounded border ${getPriorityBadge(action.priority)}`}>
              {action.priority}
            </span>
            <div className="flex-1">
              <p className="text-sm text-white">{action.text}</p>
              {action.rationale && (
                <p className="text-xs text-on-surface-variant mt-0.5">{action.rationale}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function QAContent() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const [filterOpen, setFilterOpen] = useState(false)
  const [qaFilters, setQAFilters] = useState<QAFilterState>(DEFAULT_FILTERS)
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null)
  const [platforms, setPlatforms] = useState<string[]>([])

  const searchParams = useSearchParams()

  const hasActiveFilters =
    qaFilters.topic !== '' ||
    qaFilters.subtopic !== '' ||
    qaFilters.party !== '' ||
    qaFilters.platform !== '' ||
    qaFilters.startDate !== '' ||
    qaFilters.endDate !== ''

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/taxonomy`).then((r) => r.json()),
      fetch(`${API_BASE}/analytics/platforms`).then((r) => r.json()),
    ])
      .then(([tax, plat]) => {
        setTaxonomy(tax)
        setPlatforms(plat.platforms ?? [])
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const questionParam = searchParams.get('question')
    const topicParam = searchParams.get('topic')
    if (questionParam) setQuestion(questionParam)
    if (topicParam) {
      setQAFilters((f) => ({ ...f, topic: topicParam }))
      setFilterOpen(true)
    }
  }, [searchParams])

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

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setLoading(true)
    setError(null)
    setResult(null)

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

  const renderAnswerArea = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-4">
            <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
            <p className="text-on-surface-variant">Analyzing discourse...</p>
          </div>
        </div>
      )
    }

    if (error) {
      return (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-error">
            <span className="material-symbols-outlined">error</span>
            <p>Something went wrong — please try again.</p>
          </div>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            aria-label="Retry the question"
            className="self-start px-4 py-2 rounded-full border border-outline-variant/20 bg-surface-container text-white hover:bg-surface-container-high text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Retry
          </button>
        </div>
      )
    }

    if (!result) {
      return null
    }

    if (result.insufficient_data) {
      const { reason, suggestion } = buildEmptyStateMessage(result.filters_applied)
      return (
        <div className="flex flex-col gap-3 bg-surface-container-low/50 rounded-lg border border-outline-variant/10 p-6 text-center">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant/50">search_off</span>
          <p className="text-on-surface-variant">{reason}</p>
          <p className="text-on-surface-variant text-sm">{suggestion}</p>
        </div>
      )
    }

        // Helper to render markdown bold (**text**) as <strong>
        const renderWithBold = (text: string) => {
          const parts = text.split(/(\*\*.*?\*\*)/g)
          return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={i} className="text-white font-bold">{part.slice(2, -2)}</strong>
            }
            return part
          })
        }

        return (
          <div className="space-y-8">
            {result.answer_error && (
              <div className="rounded-lg border border-tertiary/30 bg-tertiary/10 p-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary">warning</span>
                <p className="text-tertiary">{result.answer_error}</p>
              </div>
            )}

            {/* Structured Insight Visualization - AT TOP */}
            {result.structured_insight && (
              <div className="space-y-4">
                {/* Headline */}
                <HeadlineCard headline={result.structured_insight.headline} />

                {/* Key Stats Grid */}
                {result.structured_insight.key_stats.length > 0 && (
                  <StatsGrid stats={result.structured_insight.key_stats} />
                )}

                {/* Visual Data Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <SentimentMiniChart summary={result.structured_insight.sentiment_summary} />
                  <TrendingList trends={result.structured_insight.trends} />
                </div>

                {/* Takeaways and Actions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <KeyTakeawaysList takeaways={result.structured_insight.key_takeaways} />
                  <RecommendedActionsList actions={result.structured_insight.recommended_actions} />
                </div>
              </div>
            )}

            {/* Key Metrics */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">analytics</span>
                <h3 className="font-bold text-white text-lg">Key Metrics</h3>
              </div>
              <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-5">
                <MetricsStrip metrics={result.metrics} />
              </div>
            </div>

            {/* Summary with markdown bold support */}
            {result.summary && !result.structured_insight && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">summarize</span>
                  <h3 className="font-bold text-white text-lg">Summary</h3>
                </div>
                <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-5">
                  <div className="space-y-2">
                    {result.summary.split('\n').map((line, i) => {
                      const trimmed = line.trim()
                      if (!trimmed) return null
                      // Check for bullet points
                      if (trimmed.startsWith('•') || trimmed.startsWith('-')) {
                        return (
                          <div key={i} className="flex items-start gap-2">
                            <span className="text-primary mt-1">•</span>
                            <p className="text-white leading-relaxed">{renderWithBold(trimmed.slice(1).trim())}</p>
                          </div>
                        )
                      }
                      return <p key={i} className="text-white leading-relaxed">{renderWithBold(trimmed)}</p>
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Narrative Clusters - moved up */}
            {result.clusters.length >= 2 && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">hub</span>
                  <h3 className="font-bold text-white text-lg">Narrative Clusters</h3>
                </div>
                <div className="grid grid-cols-1 gap-4">
                  {result.clusters.slice(0, 4).map((cluster, i) => (
                    <NarrativeClusterCard key={`${cluster.label}-${i}`} cluster={cluster} />
                  ))}
                </div>
              </div>
            )}

            {/* Evidence Posts - MOVED TO BOTTOM */}
            {result.retrieved_posts.length > 0 && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">format_quote</span>
                  <h3 className="font-bold text-white text-lg">Evidence Posts</h3>
                </div>
                <div className="grid grid-cols-1 gap-4">
                  {result.retrieved_posts.slice(0, 5).map((post) => (
                    <EvidencePostCard key={post.id} post={post} />
                  ))}
                </div>
              </div>
            )}

        {(() => {
          const total = result.metrics.total_retrieved.toLocaleString()
          const sd = result.filters_applied.start_date
          const ed = result.filters_applied.end_date
          let label = `Based on ${total} posts`
          if (sd && ed) label += ` · ${sd} to ${ed}`
          else if (sd) label += ` · from ${sd}`
          else if (ed) label += ` · up to ${ed}`
          return (
            <p className="text-on-surface-variant text-sm text-right">
              {label}
            </p>
          )
        })()}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="max-w-3xl">
        <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2">
          Intelligence Q&A
        </h1>
        <p className="text-on-surface-variant text-lg">
          Ask political questions and get AI-powered insights based on social media data.
        </p>
      </section>

      {/* Question Input Section */}
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6 shadow-xl">
        <div className="flex flex-col gap-4">
          <label htmlFor="question" className="font-bold text-white">
            Your Question
          </label>
          <div className="flex gap-3">
            <input
              id="question"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about political discourse..."
              maxLength={500}
              className="flex-1 px-4 py-3 rounded-full bg-surface border border-outline-variant/20 text-white placeholder:text-on-surface-variant focus:outline-none focus:border-primary transition-colors"
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !question.trim()}
              className="px-6 py-3 rounded-full bg-primary-container text-white font-bold hover:bg-primary-container/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">send</span>
              {loading ? 'Analyzing...' : 'Ask'}
            </button>
          </div>
        </div>

        {/* Preset Suggestion Chips */}
        <div className="flex flex-col gap-3 mt-6">
          <span className="text-on-surface-variant text-sm">Suggested questions:</span>
          <div className="flex flex-wrap gap-2">
            {PRESET_QUESTIONS.map((preset) => (
              <button
                key={preset}
                onClick={() => handlePresetClick(preset)}
                className="px-4 py-2 rounded-full border border-outline-variant/20 bg-surface text-sm text-white hover:bg-surface-container-high transition-colors"
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Filter Toggle Button */}
          <button
            type="button"
            onClick={() => setFilterOpen((o) => !o)}
            className="self-start text-on-surface-variant hover:text-white text-sm flex items-center gap-1 mt-2 transition-colors"
          >
            <span className="material-symbols-outlined text-sm">tune</span>
            Filters {filterOpen ? '▲' : '▼'}
          </button>
        </div>

        {/* Filter Panel */}
        {filterOpen && (
          <div className="flex flex-wrap gap-3 items-center pt-4 mt-4 border-t border-outline-variant/10">
            <select
              value={qaFilters.topic}
              onChange={(e) => {
                const topic = e.target.value
                setQAFilters((f) => ({
                  ...f,
                  topic,
                  subtopic: '',
                }))
              }}
              className="px-3 py-2 rounded-full text-sm bg-surface border border-outline-variant/20 text-white focus:outline-none focus:border-primary"
            >
              <option value="">All Topics</option>
              {taxonomy?.topics.map((t) => (
                <option key={t.name} value={t.name}>{t.label}</option>
              ))}
            </select>

            <select
              value={qaFilters.subtopic}
              onChange={(e) => setQAFilters((f) => ({ ...f, subtopic: e.target.value }))}
              disabled={!qaFilters.topic}
              className="px-3 py-2 rounded-full text-sm bg-surface border border-outline-variant/20 text-white focus:outline-none focus:border-primary disabled:opacity-50"
            >
              <option value="">All Subtopics</option>
              {(() => {
                const selectedTopic = taxonomy?.topics.find((t) => t.name === qaFilters.topic)
                return selectedTopic?.subtopics.map((s) => (
                  <option key={s.name} value={s.name}>{s.label}</option>
                ))
              })()}
            </select>

            <select
              value={qaFilters.party}
              onChange={(e) => setQAFilters((f) => ({ ...f, party: e.target.value }))}
              className="px-3 py-2 rounded-full text-sm bg-surface border border-outline-variant/20 text-white focus:outline-none focus:border-primary"
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

            <select
              value={qaFilters.platform}
              onChange={(e) => setQAFilters((f) => ({ ...f, platform: e.target.value }))}
              className="px-3 py-2 rounded-full text-sm bg-surface border border-outline-variant/20 text-white focus:outline-none focus:border-primary"
            >
              <option value="">All Platforms</option>
              {platforms.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>

            {(() => {
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
                  className="px-3 py-2 rounded-full text-sm bg-surface border border-outline-variant/20 text-white focus:outline-none focus:border-primary"
                >
                  {QA_TIME_PRESETS.map(({ label, days }) => (
                    <option key={days} value={days}>{label}</option>
                  ))}
                </select>
              )
            })()}

            {hasActiveFilters && (
              <button
                type="button"
                onClick={() => { setQAFilters(DEFAULT_FILTERS) }}
                className="px-4 py-2 rounded-full text-sm border border-outline-variant/20 text-on-surface-variant hover:text-white hover:bg-surface-container-high transition-colors flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">close</span>
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
