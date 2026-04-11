'use client'

interface SentimentData {
  data: Array<{ date: string; positive: number; neutral: number; negative: number }>
}

interface TopicsData {
  topics: Array<{ name: string; label: string; count: number; positive?: number; negative?: number; neutral?: number }>
}

interface Props {
  totalPosts: number
  positivePct: number
  neutralPct: number
  negativePct: number
  topTopic: string
  sentimentData?: SentimentData
  topicsData?: TopicsData
}

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon: string
  status: 'positive' | 'neutral' | 'negative' | 'warning'
  insight: string
}

function KpiCard({ title, value, subtitle, trend, trendValue, icon, status, insight }: KpiCardProps) {
  const statusColors = {
    positive: {
      bg: 'bg-secondary/10',
      border: 'border-secondary/20',
      text: 'text-secondary',
      icon: 'text-secondary',
    },
    neutral: {
      bg: 'bg-tertiary/10',
      border: 'border-tertiary/20',
      text: 'text-tertiary',
      icon: 'text-tertiary',
    },
    negative: {
      bg: 'bg-error/10',
      border: 'border-error/20',
      text: 'text-error',
      icon: 'text-error',
    },
    warning: {
      bg: 'bg-primary/10',
      border: 'border-primary/20',
      text: 'text-primary',
      icon: 'text-primary',
    },
  }

  const colors = statusColors[status]

  return (
    <div className={`rounded-xl border ${colors.border} ${colors.bg} p-5 hover:translate-y-[-2px] transition-all duration-300`}>
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-lg ${colors.bg} flex items-center justify-center`}>
          <span className={`material-symbols-outlined ${colors.icon}`}>{icon}</span>
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs font-medium ${
            trend === 'up' ? 'text-secondary' : trend === 'down' ? 'text-error' : 'text-tertiary'
          }`}>
            <span className="material-symbols-outlined text-xs">
              {trend === 'up' ? 'trending_up' : trend === 'down' ? 'trending_down' : 'trending_flat'}
            </span>
            {trendValue}
          </div>
        )}
      </div>

      <div className="mb-1">
        <span className="text-2xl font-bold text-white">{value}</span>
        {subtitle && <span className="text-sm text-on-surface-variant ml-1">{subtitle}</span>}
      </div>

      <div className={`text-sm font-medium ${colors.text} mb-1`}>{title}</div>
      <div className="text-xs text-on-surface-variant">{insight}</div>
    </div>
  )
}

export default function KpiCards({
  totalPosts,
  positivePct,
  neutralPct,
  negativePct,
  topTopic,
  sentimentData,
  topicsData,
}: Props) {
  // Calculate Net Sentiment Score (NSS) - key metric for politicians
  const netSentimentScore = positivePct - negativePct

  // Calculate sentiment trend (last 7 days vs previous 7)
  let sentimentTrend: 'up' | 'down' | 'neutral' = 'neutral'
  let sentimentTrendValue = '0%'

  if (sentimentData?.data && sentimentData.data.length >= 14) {
    const recent = sentimentData.data.slice(-7)
    const previous = sentimentData.data.slice(-14, -7)

    const recentAvg = recent.reduce((acc, d) => acc + (d.positive - d.negative), 0) / recent.length
    const prevAvg = previous.reduce((acc, d) => acc + (d.positive - d.negative), 0) / previous.length

    const change = prevAvg !== 0 ? ((recentAvg - prevAvg) / Math.abs(prevAvg)) * 100 : 0
    sentimentTrend = change > 5 ? 'up' : change < -5 ? 'down' : 'neutral'
    sentimentTrendValue = `${change > 0 ? '+' : ''}${change.toFixed(0)}%`
  }

  // Calculate sentiment volatility (standard deviation of daily net sentiment)
  let volatility = 0
  if (sentimentData?.data && sentimentData.data.length > 0) {
    const netSentiments = sentimentData.data.map(d => d.positive - d.negative)
    const mean = netSentiments.reduce((a, b) => a + b, 0) / netSentiments.length
    const variance = netSentiments.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / netSentiments.length
    volatility = Math.sqrt(variance)
  }

  // Find the most problematic topic (highest negative ratio)
  let problematicTopic = { label: 'None', negativeRatio: 0 }
  if (topicsData?.topics) {
    const topicRatios = topicsData.topics
      .filter(t => (t.negative || 0) + (t.positive || 0) + (t.neutral || 0) > 0)
      .map(t => ({
        label: t.label,
        negativeRatio: (t.negative || 0) / ((t.negative || 0) + (t.positive || 0) + (t.neutral || 0)),
      }))
      .sort((a, b) => b.negativeRatio - a.negativeRatio)

    if (topicRatios.length > 0) {
      problematicTopic = topicRatios[0]
    }
  }

  // Calculate engagement rate (posts per day)
  const daysCount = sentimentData?.data?.length || 1
  const postsPerDay = totalPosts / daysCount

  // Determine status based on values
  const netSentimentStatus: 'positive' | 'neutral' | 'negative' =
    netSentimentScore > 10 ? 'positive' : netSentimentScore < -10 ? 'negative' : 'neutral'

  const volatilityStatus: 'positive' | 'warning' | 'negative' =
    volatility < 20 ? 'positive' : volatility < 40 ? 'warning' : 'negative'

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Net Sentiment Score - The most important KPI */}
      <KpiCard
        title="Net Sentiment Score"
        value={netSentimentScore > 0 ? `+${netSentimentScore.toFixed(0)}` : netSentimentScore.toFixed(0)}
        subtitle="/100"
        trend={sentimentTrend}
        trendValue={sentimentTrendValue}
        icon="mood"
        status={netSentimentStatus}
        insight={
          netSentimentScore > 20
            ? 'Strong positive perception - capitalize on momentum'
            : netSentimentScore > 0
            ? 'Slightly favorable - maintain messaging'
            : netSentimentScore > -20
            ? 'Concerns emerging - address proactively'
            : 'Critical negative sentiment - immediate response needed'
        }
      />

      {/* Sentiment Volatility - Stability indicator */}
      <KpiCard
        title="Sentiment Volatility"
        value={volatility.toFixed(1)}
        icon="waves"
        status={volatilityStatus}
        insight={
          volatility < 20
            ? 'Stable discourse - predictable engagement'
            : volatility < 40
            ? 'Moderate volatility - monitor for shifts'
            : 'High volatility - unpredictable reactions'
        }
      />

      {/* Daily Engagement - Volume insight */}
      <KpiCard
        title="Daily Engagement"
        value={Math.round(postsPerDay).toLocaleString()}
        subtitle="posts/day"
        icon="forum"
        status={postsPerDay > 100 ? 'positive' : postsPerDay > 50 ? 'neutral' : 'warning'}
        insight={
          postsPerDay > 200
            ? 'High engagement - key window for messaging'
            : postsPerDay > 100
            ? 'Good engagement level'
            : postsPerDay > 50
            ? 'Moderate activity'
            : 'Low engagement - consider boosting visibility'
        }
      />

      {/* Most Problematic Topic - Actionable insight */}
      <KpiCard
        title="Needs Attention"
        value={problematicTopic.label}
        icon="crisis_alert"
        status={problematicTopic.negativeRatio > 0.5 ? 'negative' : 'warning'}
        insight={
          problematicTopic.negativeRatio > 0.5
            ? `High negative sentiment (${(problematicTopic.negativeRatio * 100).toFixed(0)}%) - address urgently`
            : problematicTopic.negativeRatio > 0.3
            ? 'Rising concerns - monitor closely'
            : 'Manageable sentiment levels'
        }
      />
    </div>
  )
}
