'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

interface PostItem {
  id: string
  original_text: string
  platform: string
  created_at: string
  sentiment: string
  topic: string
  topic_label: string
  subtopic: string | null
  subtopic_label: string | null
  author: string | null
  source: string | null
}

interface PostsData {
  posts: PostItem[]
  total: number
}

interface Props {
  filters: FilterState
}

function sentimentStyles(sentiment: string): { chip: string } {
  switch (sentiment) {
    case 'positive':
      return { chip: 'text-sentiment-positive bg-sentiment-positive/10' }
    case 'negative':
      return { chip: 'text-sentiment-negative bg-sentiment-negative/10' }
    default:
      return { chip: 'text-muted bg-muted/10' }
  }
}

function PostCard({ post }: { post: PostItem }) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [textOverflows, setTextOverflows] = useState(false)
  const bodyRef = useRef<HTMLParagraphElement>(null)
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { chip } = sentimentStyles(post.sentiment)

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current !== null) clearTimeout(copyTimeoutRef.current)
    }
  }, [])

  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    const measure = () => {
      if (expanded) {
        setTextOverflows(true)
        return
      }
      setTextOverflows(el.scrollHeight > el.clientHeight + 1)
    }
    measure()
    const id = requestAnimationFrame(measure)
    return () => cancelAnimationFrame(id)
  }, [post.original_text, expanded])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(post.original_text)
      if (copyTimeoutRef.current !== null) clearTimeout(copyTimeoutRef.current)
      setCopied(true)
      copyTimeoutRef.current = setTimeout(() => {
        copyTimeoutRef.current = null
        setCopied(false)
      }, 2000)
    } catch {
      // clipboard access denied — silently ignore
    }
  }

  return (
    <div className="rounded border border-border bg-surface p-4 flex flex-col gap-2">
      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted [font-size:var(--font-size-small)]">{post.platform}</span>
        <span className="text-muted [font-size:var(--font-size-small)]">·</span>
        <span className="text-muted [font-size:var(--font-size-small)]">{post.created_at}</span>
        <span className={`px-1.5 py-0.5 rounded [font-size:var(--font-size-small)] ${chip}`}>
          {post.sentiment}
        </span>
        <span className="px-1.5 py-0.5 rounded border border-border text-muted [font-size:var(--font-size-small)]">
          {post.topic_label}
        </span>
        {post.subtopic_label && (
          <span className="px-1.5 py-0.5 rounded border border-border text-muted [font-size:var(--font-size-small)]">
            {post.subtopic_label}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <p
          ref={bodyRef}
          className={`text-foreground [font-size:var(--font-size-body)] ${expanded ? '' : 'line-clamp-3'}`}
        >
          {post.original_text}
        </p>
        {textOverflows && (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="self-start text-primary [font-size:var(--font-size-small)] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Copy button */}
      <div className="flex justify-end">
        <button
          onClick={handleCopy}
          className="text-primary [font-size:var(--font-size-small)] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          {copied ? 'Copied!' : 'Copy text'}
        </button>
      </div>
    </div>
  )
}

export default function PostsPanel({ filters }: Props) {
  const [data, setData] = useState<PostsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    let isActive = true

    async function fetchPosts() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })
        if (filters.topic) params.set('topic', filters.topic)
        if (filters.subtopic) params.set('subtopic', filters.subtopic)
        if (filters.target) params.set('target', filters.target)
        if (filters.platform) params.set('platform', filters.platform)

        const res = await fetch(`${API_BASE}/analytics/posts?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!res.ok) throw new Error('Failed to fetch posts')
        const json = await res.json()
        if (!isActive) return
        setData(json)
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        if (!isActive) return
        setError('Unable to load representative posts.')
      } finally {
        if (!isActive) return
        setLoading(false)
      }
    }

    fetchPosts()
    return () => {
      isActive = false
      controller.abort()
    }
  }, [filters])

  if (loading) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">Loading posts…</p>
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

  const posts = data?.posts ?? []

  if (posts.length === 0) {
    return (
      <div className="col-span-12">
        <p className="text-muted [font-size:var(--font-size-body)]">
          No posts found for the selected filters.
        </p>
      </div>
    )
  }

  return (
    <div className="col-span-12 bg-surface-raised rounded-lg border border-border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-foreground [font-size:var(--font-size-h4)]">
          Representative Posts
        </h3>
        <span className="text-muted [font-size:var(--font-size-small)]">
          Showing {posts.length} of {(data?.total ?? 0).toLocaleString()}
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
    </div>
  )
}
