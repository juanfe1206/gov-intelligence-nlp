import { Suspense } from 'react'
import QAContent from '@/components/qa/QAContent'

export default function QAPage() {
  return (
    <Suspense>
      <QAContent />
    </Suspense>
  )
}
