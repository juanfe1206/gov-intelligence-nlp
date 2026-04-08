'use client'

import { useState, useEffect, useCallback } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

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
      return 'bg-sentiment-positive/10 text-sentiment-positive'
    case 'failed':
      return 'bg-sentiment-negative/10 text-sentiment-negative'
    case 'partial':
      return 'bg-sentiment-warning/10 text-sentiment-warning'
    case 'running':
      return 'bg-primary/10 text-primary'
    default:
      return 'bg-muted/10 text-muted'
  }
}

function truncateError(error: string, maxLength: number = 80): string {
  if (error.length <= maxLength) return error
  return error.slice(0, maxLength) + '…'
}

export default function AdminContent() {
  const [jobs, setJobs] = useState<JobResponse[]>([])
  const [total, setTotal] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState<Set<string>>(new Set())
  const [retryError, setRetryError] = useState<Record<string, string>>({})

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

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

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
      // Refetch jobs to show the new running job
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

  // Derive source summary from completed/partial ingest jobs
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
      <div className="col-span-12 flex items-center justify-center py-12">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-muted [font-size:var(--font-size-body)]">
            Loading jobs…
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="col-span-12 flex flex-col gap-3">
        <p className="text-sentiment-negative [font-size:var(--font-size-body)]">
          {error}
        </p>
        <button
          type="button"
          onClick={fetchJobs}
          className="px-3 py-1.5 rounded border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] disabled:opacity-50 self-start"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="col-span-12 flex flex-col gap-6">
      {/* Header */}
      <div>
        <h2 className="text-foreground font-semibold [font-size:var(--font-size-h2)] [line-height:var(--line-height-h2)]">
          Admin Operations
        </h2>
        <p className="mt-2 text-muted [font-size:var(--font-size-body)] [line-height:var(--line-height-body)]">
          Monitor pipeline health, review job history, and recover from failures.
        </p>
      </div>

      {/* Source Summary */}
      {Object.keys(sourceSummary).length > 0 && (
        <div className="bg-surface-raised rounded-lg border border-border p-4">
          <h3 className="font-medium text-foreground [font-size:var(--font-size-body)] mb-3">
            Data Sources
          </h3>
          <div className="flex flex-wrap gap-3">
            {Object.entries(sourceSummary).map(([source, count]) => (
              <div
                key={source}
                className="px-3 py-1.5 rounded bg-surface border border-border text-foreground [font-size:var(--font-size-small)]"
              >
                <span className="font-medium">{source}</span>
                <span className="text-muted">: {count.toLocaleString()} posts</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Jobs Table */}
      <div className="bg-surface-raised rounded-lg border border-border overflow-hidden">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="font-medium text-foreground [font-size:var(--font-size-body)]">
            Job History
          </h3>
          <span className="text-muted [font-size:var(--font-size-small)]">
            {total.toLocaleString()} total jobs
          </span>
        </div>

        {jobs.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-muted [font-size:var(--font-size-body)]">
              No jobs recorded yet.
            </p>
            <p className="text-muted [font-size:var(--font-size-small)] mt-1">
              Jobs will appear here when data ingestion or processing runs.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface border-b border-border">
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    Job Type
                  </th>
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    Source
                  </th>
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    Start Time
                  </th>
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    End Time
                  </th>
                  <th className="px-4 py-3 text-right text-muted font-medium [font-size:var(--font-size-small)]">
                    Rows
                  </th>
                  <th className="px-4 py-3 text-left text-muted font-medium [font-size:var(--font-size-small)]">
                    Error
                  </th>
                  <th className="px-4 py-3 text-center text-muted font-medium [font-size:var(--font-size-small)]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-border last:border-b-0 hover:bg-surface"
                  >
                    <td className="px-4 py-3 text-foreground [font-size:var(--font-size-small)]">
                      {job.job_type}
                    </td>
                    <td className="px-4 py-3 text-foreground [font-size:var(--font-size-small)]">
                      {job.source}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${statusBadgeStyles(
                          job.status
                        )}`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted [font-size:var(--font-size-small)]">
                      {formatDateTime(job.started_at)}
                    </td>
                    <td className="px-4 py-3 text-muted [font-size:var(--font-size-small)]">
                      {job.finished_at ? formatDateTime(job.finished_at) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-foreground [font-size:var(--font-size-small)]">
                      {job.row_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      {job.error_summary && job.error_summary.length > 0 ? (
                        <span
                          className="text-sentiment-negative [font-size:var(--font-size-small)]"
                          title={job.error_summary[0]}
                        >
                          {truncateError(job.error_summary[0])}
                        </span>
                      ) : (
                        <span className="text-muted [font-size:var(--font-size-small)]">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {canRetry(job.status) && (
                        <div className="flex flex-col items-center gap-1">
                          <button
                            type="button"
                            aria-label={`Retry job ${job.id}`}
                            onClick={() => handleRetry(job.id)}
                            disabled={retrying.has(job.id) || loading}
                            className="px-3 py-1.5 rounded border border-border bg-surface text-foreground hover:bg-surface-raised [font-size:var(--font-size-small)] disabled:opacity-50"
                          >
                            {retrying.has(job.id) ? 'Retrying…' : 'Retry'}
                          </button>
                          {retryError[job.id] && (
                            <span className="text-sentiment-negative [font-size:var(--font-size-small)]">
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
    </div>
  )
}
