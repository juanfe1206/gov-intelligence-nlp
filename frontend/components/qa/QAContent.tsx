'use client'

import { useState, useRef, useCallback, useEffect } from 'react'

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

interface QAResponse {
  question: string
  filters_applied: {
    topic: string | null
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
}

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

export default function QAContent() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QAResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

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

    try {
      const response = await fetch(`${API_BASE}/qa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
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
  }, [question])

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

        {/* Scope Label */}
        <p className="text-muted [font-size:var(--font-size-small)]">
          Based on {result.metrics.total_retrieved.toLocaleString()} posts
        </p>
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
        </div>
      </div>

      {/* Answer Area */}
      {renderAnswerArea()}
    </div>
  )
}