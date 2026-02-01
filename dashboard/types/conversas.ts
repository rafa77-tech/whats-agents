/**
 * Types for the /conversas module
 */

// Filter types
export interface ConversationFilters {
  status?: string
  controlled_by?: 'ai' | 'human'
  search?: string
  chip_id?: string
}

// Chip information
export interface ChipInfo {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
}

// Conversation list item (for sidebar)
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
}

// Message in a conversation
export interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  metadata?: {
    tipo_midia?: string
    media_url?: string
  }
}

// Full conversation detail
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
}

// API response types
export interface ConversationListResponse {
  data: ConversationListItem[]
  total: number
  pages: number
}

// Attachment for sending
export interface Attachment {
  type: 'image' | 'document' | 'audio'
  file: File
  preview?: string
}

// Chip with conversation count (for chip selector)
export interface ChipWithCount extends ChipInfo {
  conversation_count: number
}
