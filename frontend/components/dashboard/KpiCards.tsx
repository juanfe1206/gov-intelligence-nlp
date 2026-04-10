'use client'

interface Props {
  totalPosts: number
  positivePct: number
  neutralPct: number
  negativePct: number
  topTopic: string
}

function KpiCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-surface-raised rounded-lg border border-border p-4 flex flex-col gap-1">
      <span className="text-muted [font-size:var(--font-size-small)]">{label}</span>
      <span
        className={`font-semibold [font-size:var(--font-size-h3)] [line-height:var(--line-height-h3)] ${
          accent ?? 'text-foreground'
        }`}
      >
        {value}
      </span>
    </div>
  )
}

export default function KpiCards({ totalPosts, positivePct, neutralPct, negativePct, topTopic }: Props) {
  return (
    <div className="col-span-12 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      <KpiCard label="Total Posts" value={totalPosts.toLocaleString()} />
      <KpiCard label="Positive" value={`${positivePct.toFixed(1)}%`} accent="text-sentiment-positive" />
      <KpiCard label="Neutral" value={`${neutralPct.toFixed(1)}%`} accent="text-sentiment-warning" />
      <KpiCard label="Negative" value={`${negativePct.toFixed(1)}%`} accent="text-sentiment-negative" />
      <KpiCard label="Top Topic" value={topTopic || '—'} />
    </div>
  )
}