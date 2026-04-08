import { Suspense } from 'react'
import AdminContent from '@/components/admin/AdminContent'

export default function AdminPage() {
  return (
    <Suspense>
      <AdminContent />
    </Suspense>
  )
}
