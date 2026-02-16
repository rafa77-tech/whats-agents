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
  shiftCreateSchema,
  parseShiftListParams,
  parseShiftUpdateBody,
  parseShiftCreateBody,
  VALID_STATUSES,
  type ShiftListParams,
  type ShiftUpdateBody,
  type ShiftCreateBody,
} from './schemas'

// Hooks
export { useShifts, useShiftDetail, useDoctorSearch } from './hooks'

// Campaign helpers (Sprint 58)
export { buildCampaignInitialData } from './campaign-helpers'
export type { VagaResumo, EscopoVagas, WizardInitialData } from './campaign-helpers'
