'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { FilterState } from './FilterBar'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

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

function PostCard({ post }: { post: PostItem }) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [textOverflows, setTextOverflows] = useState(false)
  const bodyRef = useRef<HTMLParagraphElement>(null)
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { chip, icon } = sentimentStyles(post.sentiment)

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
    <div className="rounded-lg border border-outline-variant/10 bg-surface-container p-5 flex flex-col gap-3 hover:border-outline-variant/30 transition-colors">
      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-on-surface-variant text-xs font-medium uppercase tracking-wider">{post.platform}</span>
        <span className="text-on-surface-variant">·</span>
        <span className="text-on-surface-variant text-xs">{post.created_at}</span>
        {post.author && (
          <>
            <span className="text-on-surface-variant">·</span>
            <span className="text-on-surface-variant text-xs font-medium">@{post.author}</span>
          </>
        )}
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-bold ${chip}`}>
          <span className="material-symbols-outlined text-xs">{icon}</span>
          {post.sentiment}
        </div>
        <span className="px-2 py-0.5 rounded-full border border-outline-variant/20 text-on-surface-variant text-xs font-medium">
          {post.topic_label}
        </span>
        {post.subtopic_label && (
          <span className="px-2 py-0.5 rounded-full border border-outline-variant/20 text-on-surface-variant text-xs font-medium">
            {post.subtopic_label}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <p
          ref={bodyRef}
          className={`text-white text-sm leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}
        >
          {post.original_text}
        </p>
        {textOverflows && (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="self-start text-primary text-xs font-medium hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Copy button */}
      <div className="flex justify-end pt-2 border-t border-outline-variant/10">
        <button
          onClick={handleCopy}
          className="text-primary text-xs font-medium hover:underline flex items-center gap-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          <span className="material-symbols-outlined text-xs">{copied ? 'check' : 'content_copy'}</span>
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
  const [limit, setLimit] = useState(20)

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
        params.set('limit', String(limit))

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
  }, [filters, limit])

  if (loading) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <div className="flex items-center gap-2 text-on-surface-variant">
          <span className="material-symbols-outlined animate-spin">progress_activity</span>
          <span>Loading posts…</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <p className="text-error">{error}</p>
      </div>
    )
  }

  const posts = data?.posts ?? []

  if (posts.length === 0) {
    return (
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <p className="text-on-surface-variant">No posts found for the selected filters.</p>
      </div>
    )
  }

  return (
    <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6 shadow-xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">forum</span>
          <h3 className="font-bold text-white text-lg">Representative Posts</h3>
        </div>
        <span className="text-on-surface-variant text-sm">
          Showing {posts.length} of {(data?.total ?? 0).toLocaleString()}
        </span>
      </div>
      <div className="flex flex-col gap-4">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
      {posts.length < (data?.total ?? 0) && (
        <div className="flex justify-center mt-6">
          <button
            onClick={() => setLimit((prev) => prev + 20)}
            className="px-6 py-2.5 rounded-full text-sm font-medium bg-surface-container border border-outline-variant/20 text-white hover:bg-surface-container-high transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">expand_more</span>
            Load more ({((data?.total ?? 0) - posts.length).toLocaleString()} remaining)
          </button>
        </div>
      )}
    </div>
  )
}
