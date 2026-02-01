/**
 * Módulo de Vagas - Exports centralizados
 */

// Types
export type {
  Shift,
  ShiftDetail,
  ShiftFilters,
  ShiftListResponse,
  ShiftStatus,
  Doctor,
  ViewMode,
  SelectOption,
} from './types'

// Constants
export {
  STATUS_BADGE_COLORS,
  STATUS_INDICATOR_COLORS,
  STATUS_LABELS,
  STATUS_OPTIONS,
  ALL_STATUSES,
  WEEK_DAYS,
  PAGINATION,
} from './constants'

// Formatters
export {
  formatCurrency,
  parseShiftDate,
  getStatusBadgeColor,
  getStatusIndicatorColor,
  getStatusLabel,
  formatTimeRange,
  formatReservasCount,
} from './formatters'

// Schemas
export {
  shiftListParamsSchema,
  shiftUpdateSchema,
  parseShiftListParams,
  parseShiftUpdateBody,
  VALID_STATUSES,
  type ShiftListParams,
  type ShiftUpdateBody,
} from './schemas'

// Hooks
export { useShifts, useShiftDetail, useDoctorSearch } from './hooks'
