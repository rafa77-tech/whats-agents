/**
 * Table Skeleton - Sprint 34 E04
 *
 * Skeleton loading state for table rows.
 */

import { Skeleton } from '@/components/ui/skeleton'
import { TableRow, TableCell } from '@/components/ui/table'

interface TableSkeletonProps {
  rows?: number
  columns?: number
}

export function TableSkeleton({ rows = 5, columns = 6 }: TableSkeletonProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: columns }).map((_, j) => (
            <TableCell key={j}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
