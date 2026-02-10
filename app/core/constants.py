"""
Constantes do sistema.

Sprint 31 - S31.E6.2

Centraliza valores constantes usados em múltiplos lugares,
facilitando ajustes e mantendo consistência.
"""

# =============================================================================
# LLM Configuration
# =============================================================================

# Tokens máximos para respostas
DEFAULT_MAX_TOKENS = 300
DEFAULT_MAX_TOKENS_SHORT = 150
DEFAULT_MAX_TOKENS_COMPLEX = 1000

# Temperatura (criatividade)
DEFAULT_TEMPERATURE = 0.7

# =============================================================================
# Tool Execution
# =============================================================================

# Máximo de iterações de tool calls sequenciais
MAX_TOOL_ITERATIONS = 3

# Timeout para execução de tools (segundos)
TOOL_TIMEOUT_SECONDS = 30

# =============================================================================
# Response Detection
# =============================================================================

# Comprimento mínimo para resposta válida
MIN_RESPONSE_LENGTH = 20

# Padrões que indicam resposta incompleta
INCOMPLETE_RESPONSE_PATTERNS = [
    ":",  # "Vou verificar o que temos:"
    "...",  # Reticências no final
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
    "deixa eu buscar",
]

# =============================================================================
# Rate Limiting (WhatsApp)
# =============================================================================

# Limites por período
MESSAGES_PER_HOUR = 20
MESSAGES_PER_DAY = 100

# Intervalo entre mensagens (segundos)
MIN_INTERVAL_SECONDS = 45
MAX_INTERVAL_SECONDS = 180

# Horário comercial
BUSINESS_HOURS_START = 8  # 08:00
BUSINESS_HOURS_END = 20  # 20:00

# =============================================================================
# Circuit Breaker
# =============================================================================

# Falhas antes de abrir o circuito
CIRCUIT_FAILURE_THRESHOLD = 5

# Tempo de reset (segundos)
CIRCUIT_RESET_TIMEOUT = 60

# =============================================================================
# Tracing
# =============================================================================

# Tamanho do trace ID
TRACE_ID_LENGTH = 8

# =============================================================================
# Conversation Mode
# =============================================================================

# Timeout para transição pendente (minutos)
PENDING_TRANSITION_TIMEOUT_MINUTES = 5

# Cooldown entre transições (minutos)
MODE_TRANSITION_COOLDOWN_MINUTES = 3

# =============================================================================
# Knowledge / RAG
# =============================================================================

# Quantidade de chunks a retornar
DEFAULT_RAG_TOP_K = 5

# Score mínimo para considerar relevante
RAG_MIN_SCORE = 0.7

# =============================================================================
# Histórico
# =============================================================================

# Quantidade de mensagens no histórico para contexto
MAX_HISTORY_MESSAGES = 10

# Quantidade de mensagens recebidas para análise
MAX_RECEIVED_MESSAGES_FOR_ANALYSIS = 5
