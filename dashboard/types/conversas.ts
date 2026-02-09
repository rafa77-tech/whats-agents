/**
 * Types for the /conversas module
 * Sprint 54: Supervision Dashboard
 */

// ============================================
// Filter types
// ============================================

export interface ConversationFilters {
  status?: string
  controlled_by?: 'ai' | 'human'
  search?: string
  chip_id?: string
}

// ============================================
// Chip information
// ============================================

export interface ChipInfo {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
}

// ============================================
// Supervision Tab Types (Sprint 54)
// ============================================

export type SupervisionTab = 'atencao' | 'julia_ativa' | 'aguardando' | 'encerradas'

export interface TabCounts {
  atencao: number
  julia_ativa: number
  aguardando: number
  encerradas: number
}

// ============================================
// Conversation list item (for sidebar)
// ============================================

export interface ConversationListItem {
  id: string
  cliente_nome: string
  cliente_telefone: string
  status: string
  controlled_by: 'ai' | 'human'
  last_message?: string
  last_message_at?: string
  unread_count: number
  chip?: ChipInfo | null
  // Sprint 54: Enrichment fields
  sentimento_score?: number | undefined
  ai_confidence?: number | undefined
  stage_jornada?: string | undefined
  especialidade?: string | undefined
  has_handoff?: boolean | undefined
  handoff_reason?: string | undefined
  last_message_direction?: 'entrada' | 'saida' | undefined
}

// ============================================
// Message in a conversation
// ============================================

export interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  metadata?: {
    tipo_midia?: string
    media_url?: string
  }
  // Sprint 54: Enrichment
  sentimento_score?: number | undefined
  ai_confidence?: number | undefined
}

// ============================================
// Full conversation detail
// ============================================

export interface ConversationDetail {
  id: string
  status: string
  controlled_by: 'ai' | 'human'
  cliente: {
    id: string
    nome: string
    telefone: string
  }
  chip?: ChipInfo | null
  messages: Message[]
  // Sprint 54: Pause state
  pausada_em?: string | null | undefined
  motivo_pausa?: string | null | undefined
}

// ============================================
// API response types
// ============================================

export interface ConversationListResponse {
  data: ConversationListItem[]
  total: number
  pages: number
}

// ============================================
// Attachment for sending
// ============================================

export interface Attachment {
  type: 'image' | 'document' | 'audio'
  file: File
  preview?: string
}

// ============================================
// Chip with conversation count (for chip selector)
// ============================================

export interface ChipWithCount extends ChipInfo {
  conversation_count: number
}

// ============================================
// Doctor Context Types (Sprint 54 - Phase 2)
// ============================================

export interface DoctorProfile {
  nome: string
  telefone: string
  crm?: string | undefined
  especialidade?: string | undefined
  stage_jornada?: string | undefined
  pressure_score?: number | undefined
  tags?: string[] | undefined
  opt_out?: boolean | undefined
  cidade?: string | undefined
  estado?: string | undefined
}

export interface DoctorMemoryItem {
  content: string
  tipo: string
  created_at: string
}

export interface ConversationMetrics {
  total_msg_medico: number
  total_msg_julia: number
  tempo_medio_resposta: number
  duracao_minutos: number
  houve_handoff: boolean
}

export interface HandoffEntry {
  motivo: string
  trigger_type: string
  status: string
  created_at: string
  notas?: string | undefined
}

export interface BusinessEvent {
  event_type: string
  event_props: Record<string, unknown>
  ts: string
}

export interface DoctorContextData {
  doctor: DoctorProfile
  memory: DoctorMemoryItem[]
  metrics: ConversationMetrics
  handoff_history: HandoffEntry[]
  recent_events: BusinessEvent[]
  conversation_count: number
  first_contact_at?: string | undefined
  notes: SupervisorNote[]
}

// ============================================
// Supervisor Types (Sprint 54 - Phase 3)
// ============================================

export interface SupervisorNote {
  id: string
  content: string
  created_at: string
  user_id?: string | undefined
}

export interface MessageFeedback {
  id: string
  interacao_id: number
  feedback_type: 'positive' | 'negative'
  comment?: string | undefined
  created_at: string
}

// ============================================
// Supervisor Channel Types (Sprint 54 - Phase 4)
// ============================================

export interface ChannelMessage {
  id: string
  role: 'supervisor' | 'julia'
  content: string
  metadata?: Record<string, unknown> | undefined
  created_at: string
}

export interface InstructionPreview {
  id: string
  instruction: string
  preview_message: string
  status: string
}
