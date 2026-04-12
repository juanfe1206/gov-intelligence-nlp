'use client'

import { useState, useEffect, useCallback } from 'react'

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

interface ResetResponse {
  deleted_processed_posts: number
  deleted_jobs: number
  deleted_raw_posts: number
  message: string
}

interface JobResponse {
  id: string
  job_type: string
  status: string
  source: string
  started_at: string
  finished_at: string | null
  row_count: number
  inserted_count: number
  skipped_count: number
  duplicate_count: number
  error_summary: string[] | null
}

interface JobsListResponse {
  jobs: JobResponse[]
  total: number
}

interface ApiHealth {
  status: 'ok' | 'error' | 'loading'
}

interface DbHealth {
  status: 'ok' | 'degraded' | 'error' | 'unknown' | 'loading'
  db?: 'connected' | 'disconnected'
}

function formatDateTime(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusBadgeStyles(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-secondary/10 text-secondary border-secondary/20'
    case 'failed':
      return 'bg-error/10 text-error border-error/20'
    case 'partial':
      return 'bg-tertiary/10 text-tertiary border-tertiary/20'
    case 'running':
      return 'bg-primary/10 text-primary border-primary/20'
    default:
      return 'bg-surface-container-high text-on-surface-variant border-outline-variant/20'
  }
}

function truncateError(error: string, maxLength: number = 80): string {
  if (error.length <= maxLength) return error
  return error.slice(0, maxLength) + '...'
}

export default function AdminContent() {
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [total, setTotal] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState<Set<string>>(new Set())
  const [retryError, setRetryError] = useState<Record<string, string>>({})
  const [apiHealth, setApiHealth] = useState<ApiHealth>({ status: 'loading' })
  const [dbHealth, setDbHealth] = useState<DbHealth>({ status: 'loading' })
  const [resetting, setResetting] = useState(false)
  const [resetConfirm, setResetConfirm] = useState(false)
  const [preserveRaw, setPreserveRaw] = useState(true)
  const [resetResult, setResetResult] = useState<ResetResponse | null>(null)
  const [resetError, setResetError] = useState<string | null>(null)

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      if (!res.ok) {
        throw new Error('Failed to fetch jobs')
      }
      const data: JobsListResponse = await res.json()
      setJobs(data.jobs)
      setTotal(data.total)
    } catch (err) {
      setError('Unable to load jobs. Check that the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchHealth = useCallback(async (signal?: AbortSignal) => {
    let apiOk = false
    try {
      const res = await fetch(`${API_BASE}/health`, { signal })
      apiOk = res.ok
      setApiHealth({ status: res.ok ? 'ok' : 'error' })
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setApiHealth({ status: 'error' })
      }
    }
    try {
      const res = await fetch(`${API_BASE}/health/db`, { signal })
      const data = await res.json().catch(() => ({}))
      if (res.ok && data.status === 'ok') {
        setDbHealth({ status: 'ok', db: 'connected' })
      } else if (res.ok) {
        setDbHealth({ status: 'degraded', db: data.db ?? 'disconnected' })
      } else {
        setDbHealth({ status: 'degraded', db: 'disconnected' })
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setDbHealth({ status: apiOk ? 'error' : 'unknown' })
      }
    }
  }, [])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
    const id = setInterval(() => fetchHealth(controller.signal), 30_000)
    return () => {
      controller.abort()
      clearInterval(id)
    }
  }, [fetchHealth])

  const handleRetry = useCallback(async (jobId: string) => {
    setRetrying((prev) => new Set(prev).add(jobId))
    setRetryError((prev) => {
      const next = { ...prev }
      delete next[jobId]
      return next
    })

    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/retry`, {
        method: 'POST',
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail?.message || errorData.detail || 'Retry failed')
      }
      await fetchJobs().catch(() => {
        setRetryError((prev) => ({
          ...prev,
          [jobId]: 'Table refresh failed — retry succeeded.',
        }))
      })
    } catch (err) {
      setRetryError((prev) => ({
        ...prev,
        [jobId]: (err as Error).message || 'Retry failed',
      }))
    } finally {
      setRetrying((prev) => {
        const next = new Set(prev)
        next.delete(jobId)
        return next
      })
    }
  }, [fetchJobs])

  const handleResetConfirm = useCallback(() => {
    setResetConfirm(true)
    setResetResult(null)
    setResetError(null)
  }, [])

  const handleReset = useCallback(async () => {
    setResetting(true)
    setResetError(null)
    setResetResult(null)
    try {
      const res = await fetch(`${API_BASE}/admin/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preserve_raw: preserveRaw }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Reset failed')
      }
      const data: ResetResponse = await res.json()
      setResetResult(data)
      setResetConfirm(false)
      await fetchJobs()
    } catch (err) {
      setResetError((err as Error).message || 'Reset failed')
    } finally {
      setResetting(false)
    }
  }, [fetchJobs, preserveRaw])

  const sourceSummary = jobs
    .filter(
      (j) =>
        j.job_type === 'ingest' &&
        (j.status === 'completed' || j.status === 'partial')
    )
    .reduce((acc, j) => {
      acc[j.source] = (acc[j.source] ?? 0) + j.inserted_count
      return acc
    }, {} as Record<string, number>)

  const canRetry = (status: string): boolean =>
    status === 'failed' || status === 'partial'

  if (loading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-4">
          <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
          <p className="text-on-surface-variant">Loading jobs...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2 text-error">
          <span className="material-symbols-outlined">error</span>
          <p>{error}</p>
        </div>
        <button
          type="button"
          onClick={fetchJobs}
          className="px-4 py-2 rounded-full border border-outline-variant/20 bg-surface-container text-white hover:bg-surface-container-high text-sm font-medium self-start flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-sm">refresh</span>
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="max-w-3xl">
        <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2">
          Admin Operations
        </h1>
        <p className="text-on-surface-variant text-lg">
          Monitor pipeline health, review job history, and recover from failures.
        </p>
      </section>

      {/* System Health */}
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-primary">health_and_safety</span>
          <h3 className="font-bold text-white">System Health</h3>
        </div>
        <div className="flex flex-wrap items-center gap-6">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-full border ${
            apiHealth.status === 'ok'
              ? 'bg-secondary/10 text-secondary border-secondary/20'
              : apiHealth.status === 'error'
              ? 'bg-error/10 text-error border-error/20'
              : 'bg-surface-container-high text-on-surface-variant'
          }`}>
            <span className="material-symbols-outlined text-sm">
              {apiHealth.status === 'ok' ? 'check_circle' : apiHealth.status === 'error' ? 'error' : 'pending'}
            </span>
            <span className="font-medium text-sm">
              {apiHealth.status === 'ok' ? 'API: Operational' : apiHealth.status === 'error' ? 'API: Unavailable' : 'API: Checking...'}
            </span>
          </div>
          <div className={`flex items-center gap-2 px-3 py-2 rounded-full border ${
            dbHealth.status === 'ok'
              ? 'bg-secondary/10 text-secondary border-secondary/20'
              : (dbHealth.status === 'degraded' || dbHealth.status === 'error')
              ? 'bg-error/10 text-error border-error/20'
              : 'bg-surface-container-high text-on-surface-variant'
          }`}>
            <span className="material-symbols-outlined text-sm">
              {dbHealth.status === 'ok' ? 'check_circle' : (dbHealth.status === 'degraded' || dbHealth.status === 'error') ? 'error' : 'pending'}
            </span>
            <span className="font-medium text-sm">
              {dbHealth.status === 'ok' ? 'Database: Connected' :
               (dbHealth.status === 'degraded' || dbHealth.status === 'error') ? 'Database: Disconnected' :
               dbHealth.status === 'unknown' ? 'Database: Unknown' : 'Database: Checking...'}
            </span>
          </div>
        </div>
      </div>

      {/* Source Summary */}
      {Object.keys(sourceSummary).length > 0 && (
        <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-primary">database</span>
            <h3 className="font-bold text-white">Data Sources</h3>
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(sourceSummary).map(([source, count]) => (
              <div
                key={source}
                className="px-4 py-2 rounded-full bg-surface border border-outline-variant/20 text-sm"
              >
                <span className="font-bold text-white">{source}</span>
                <span className="text-on-surface-variant">: {count.toLocaleString()} posts</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Jobs Table */}
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-outline-variant/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">assignment</span>
            <h3 className="font-bold text-white">Job History</h3>
          </div>
          <span className="text-on-surface-variant text-sm">
            {total.toLocaleString()} total jobs
          </span>
        </div>

        {jobs.length === 0 ? (
          <div className="p-8 text-center">
            <span className="material-symbols-outlined text-4xl text-on-surface-variant/50 mb-4">inbox</span>
            <p className="text-on-surface-variant">No jobs recorded yet.</p>
            <p className="text-on-surface-variant text-sm mt-1">Jobs will appear here when data ingestion or processing runs.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface border-b border-outline-variant/10">
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">Job Type</th>
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">Source</th>
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">Start Time</th>
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">End Time</th>
                  <th className="px-6 py-3 text-right text-on-surface-variant font-bold text-xs uppercase tracking-wider">Rows</th>
                  <th className="px-6 py-3 text-left text-on-surface-variant font-bold text-xs uppercase tracking-wider">Error</th>
                  <th className="px-6 py-3 text-center text-on-surface-variant font-bold text-xs uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-outline-variant/10 last:border-b-0 hover:bg-surface-container transition-colors"
                  >
                    <td className="px-6 py-4 text-white text-sm">{job.job_type}</td>
                    <td className="px-6 py-4 text-white text-sm">{job.source}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold border ${statusBadgeStyles(
                          job.status
                        )}`}
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-current" />
                        {job.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-on-surface-variant text-sm">{formatDateTime(job.started_at)}</td>
                    <td className="px-6 py-4 text-on-surface-variant text-sm">{job.finished_at ? formatDateTime(job.finished_at) : '—'}</td>
                    <td className="px-6 py-4 text-right text-white text-sm">{job.row_count.toLocaleString()}</td>
                    <td className="px-6 py-4">
                      {job.error_summary && job.error_summary.length > 0 ? (
                        <span
                          className="text-error text-sm"
                          title={job.error_summary[0]}
                        >
                          {truncateError(job.error_summary[0])}
                        </span>
                      ) : (
                        <span className="text-on-surface-variant text-sm">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {canRetry(job.status) && (
                        <div className="flex flex-col items-center gap-1">
                          <button
                            type="button"
                            aria-label={`Retry job ${job.id}`}
                            onClick={() => handleRetry(job.id)}
                            disabled={retrying.has(job.id) || loading}
                            className="px-3 py-1.5 rounded-full border border-outline-variant/20 bg-surface text-sm text-white hover:bg-surface-container-high disabled:opacity-50 flex items-center gap-1"
                          >
                            <span className="material-symbols-outlined text-xs">refresh</span>
                            {retrying.has(job.id) ? 'Retrying...' : 'Retry'}
                          </button>
                          {retryError[job.id] && (
                            <span className="text-error text-xs">
                              {retryError[job.id]}
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Demo Reset */}
      <div className="bg-surface-container-low rounded-lg border border-outline-variant/10 p-6">
        <div className="flex items-center gap-2 mb-4">
          <span className="material-symbols-outlined text-primary">restart_alt</span>
          <h3 className="font-bold text-white">Demo Reset</h3>
        </div>
        <p className="text-on-surface-variant text-sm mb-4">
          Clear processed posts and job records to start a fresh demo run.
          Raw posts can optionally be preserved to avoid re-ingestion.
        </p>

        <label className="flex items-center gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={preserveRaw}
            onChange={(e) => setPreserveRaw(e.target.checked)}
            className="accent-secondary"
          />
          <span className="text-sm text-white">Preserve raw posts (recommended — skip re-ingestion)</span>
        </label>

        {!resetConfirm ? (
          <button
            type="button"
            onClick={handleResetConfirm}
            disabled={resetting}
            className="px-4 py-2 rounded-full border border-error/30 text-error hover:bg-error/10 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">delete_forever</span>
            Reset Demo Data
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleReset}
              disabled={resetting}
              className="px-4 py-2 rounded-full border border-error bg-error/10 text-error hover:bg-error/20 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">warning</span>
              {resetting ? 'Resetting...' : 'Confirm Reset'}
            </button>
            <button
              type="button"
              onClick={() => setResetConfirm(false)}
              disabled={resetting}
              className="px-4 py-2 rounded-full border border-outline-variant/20 text-white hover:bg-surface-container-high text-sm font-medium disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        )}

        {resetResult && (
          <div className="mt-4 flex items-center gap-2 text-secondary">
            <span className="material-symbols-outlined">check_circle</span>
            <p className="text-sm">
              {resetResult.message} ({resetResult.deleted_processed_posts} processed posts,{' '}
              {resetResult.deleted_jobs} jobs
              {resetResult.deleted_raw_posts > 0 ? `, ${resetResult.deleted_raw_posts} raw posts` : ''} cleared)
            </p>
          </div>
        )}
        {resetError && (
          <div className="mt-4 flex items-center gap-2 text-error">
            <span className="material-symbols-outlined">error</span>
            <p className="text-sm">{resetError}</p>
          </div>
        )}
      </div>
    </div>
  )
}
