/**
 * Módulo de Médicos - Exports centralizados
 */

// Types
export type {
  Doctor,
  DoctorDetail,
  DoctorStats,
  DoctorActions,
  DoctorFilters,
  DoctorListResponse,
  TimelineEvent,
  JourneyStage,
  TimelineEventType,
  SelectOption,
} from './types'

// Constants
export {
  STAGE_COLORS,
  STAGE_LABELS,
  STAGE_OPTIONS,
  ESPECIALIDADE_OPTIONS,
  EVENT_COLORS,
  ALL_STAGES,
  PAGINATION,
  SEARCH_DEBOUNCE_MS,
} from './constants'

// Formatters
export {
  getInitials,
  getStageColor,
  getStageLabel,
  getEventColor,
  formatFullName,
  formatLocation,
} from './formatters'
