# E01: Schema conversation_mode

**Status:** Pendente
**Estimativa:** 2h
**Dependencia:** Nenhuma
**Responsavel:** Dev

---

## Objetivo

Adicionar campo `conversation_mode` na tabela `conversations` para persistir o modo atual de cada conversa.

---

## Schema

### Migração SQL

```sql
-- Migração: add_conversation_mode
-- Nome: 20260102_add_conversation_mode

-- 1. Criar enum type
CREATE TYPE conversation_mode_enum AS ENUM (
    'discovery',
    'oferta',
    'followup',
    'reativacao'
);

-- 2. Adicionar coluna principal na tabela conversations
ALTER TABLE conversations
ADD COLUMN conversation_mode conversation_mode_enum NOT NULL DEFAULT 'discovery';

-- 3. Adicionar colunas de auditoria de transição
ALTER TABLE conversations
ADD COLUMN mode_updated_at TIMESTAMPTZ;

ALTER TABLE conversations
ADD COLUMN mode_updated_reason TEXT;

-- 4. Adicionar campo de origem do modo (AJUSTE 5)
ALTER TABLE conversations
ADD COLUMN mode_source TEXT;  -- "inbound", "campaign:<id>", "manual"

-- 5. Adicionar campos para micro-confirmação (AJUSTE 4)
ALTER TABLE conversations
ADD COLUMN pending_transition conversation_mode_enum;

ALTER TABLE conversations
ADD COLUMN pending_transition_at TIMESTAMPTZ;

-- 6. Criar índices
CREATE INDEX idx_conversations_mode ON conversations(conversation_mode)
    WHERE status = 'active';

CREATE INDEX idx_conversations_pending_transition ON conversations(pending_transition)
    WHERE pending_transition IS NOT NULL;

-- 7. Comentários
COMMENT ON COLUMN conversations.conversation_mode IS
    'Modo atual da conversa: discovery (conhecer), oferta (vender), followup (acompanhar), reativacao (reativar)';
COMMENT ON COLUMN conversations.mode_updated_at IS
    'Última vez que o modo foi alterado';
COMMENT ON COLUMN conversations.mode_updated_reason IS
    'Motivo da última transição de modo (para auditoria)';
COMMENT ON COLUMN conversations.mode_source IS
    'Origem do modo: inbound (médico iniciou), campaign:<id> (campanha), manual (gestor)';
COMMENT ON COLUMN conversations.pending_transition IS
    'Transição pendente de confirmação do médico';
COMMENT ON COLUMN conversations.pending_transition_at IS
    'Quando a transição pendente foi proposta';
```

### Backfill de Dados Existentes

```sql
-- Backfill: inferir modo baseado no estado atual
-- Executar APÓS a migração

UPDATE conversations
SET conversation_mode = CASE
    -- Conversa nova, sem interações significativas
    WHEN (
        SELECT COUNT(*) FROM interacoes
        WHERE conversa_id = conversations.id
    ) <= 2 THEN 'discovery'::conversation_mode_enum

    -- Silêncio prolongado (7+ dias)
    WHEN last_message_at < NOW() - INTERVAL '7 days'
    AND status = 'active' THEN 'reativacao'::conversation_mode_enum

    -- Conversa ativa recente
    WHEN last_message_at > NOW() - INTERVAL '24 hours'
    THEN 'followup'::conversation_mode_enum

    -- Default
    ELSE 'followup'::conversation_mode_enum
END,
mode_updated_at = NOW(),
mode_updated_reason = 'backfill_sprint_29'
WHERE conversation_mode IS NULL OR conversation_mode = 'discovery';
```

---

## Tipos Python

### Arquivo: `app/services/conversation_mode/types.py`

```python
"""
Tipos do Conversation Mode.
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ConversationMode(Enum):
    """Modos de conversa."""
    DISCOVERY = "discovery"      # Conhecer o médico
    OFERTA = "oferta"            # Oferecer vaga
    FOLLOWUP = "followup"        # Dar continuidade
    REATIVACAO = "reativacao"    # Reativar inativo


@dataclass
class ModeInfo:
    """Informações do modo atual de uma conversa."""
    conversa_id: str
    mode: ConversationMode
    updated_at: Optional[datetime] = None
    updated_reason: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict) -> "ModeInfo":
        """Cria ModeInfo a partir de row do banco."""
        return cls(
            conversa_id=row["id"],
            mode=ConversationMode(row.get("conversation_mode", "discovery")),
            updated_at=row.get("mode_updated_at"),
            updated_reason=row.get("mode_updated_reason"),
        )


@dataclass
class ModeTransition:
    """Representa uma transição de modo."""
    from_mode: ConversationMode
    to_mode: ConversationMode
    reason: str
    confidence: float  # 0.0 a 1.0
    evidence: str  # Texto/sinal que motivou

    def is_valid(self) -> bool:
        """Verifica se transição é permitida."""
        # Transições proibidas
        forbidden = [
            (ConversationMode.DISCOVERY, ConversationMode.FOLLOWUP),
            (ConversationMode.REATIVACAO, ConversationMode.REATIVACAO),
        ]
        return (self.from_mode, self.to_mode) not in forbidden
```

---

## Repository

### Arquivo: `app/services/conversation_mode/repository.py`

```python
"""
Repositório para conversation_mode.
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase
from .types import ConversationMode, ModeInfo

logger = logging.getLogger(__name__)


async def get_conversation_mode(conversa_id: str) -> ModeInfo:
    """
    Busca modo atual da conversa.

    Returns:
        ModeInfo com modo atual (default: discovery)
    """
    try:
        response = (
            supabase.table("conversations")
            .select("id, conversation_mode, mode_updated_at, mode_updated_reason")
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if response.data:
            return ModeInfo.from_row(response.data)

        # Conversa não encontrada - retornar default
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar conversation_mode: {e}")
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )


async def set_conversation_mode(
    conversa_id: str,
    mode: ConversationMode,
    reason: str,
) -> bool:
    """
    Atualiza modo da conversa.

    Args:
        conversa_id: ID da conversa
        mode: Novo modo
        reason: Motivo da transição (para auditoria)

    Returns:
        True se sucesso
    """
    try:
        response = (
            supabase.table("conversations")
            .update({
                "conversation_mode": mode.value,
                "mode_updated_at": datetime.utcnow().isoformat(),
                "mode_updated_reason": reason,
            })
            .eq("id", conversa_id)
            .execute()
        )

        logger.info(f"Mode atualizado: {conversa_id} -> {mode.value} ({reason})")
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar conversation_mode: {e}")
        return False
```

---

## DoD (Definition of Done)

### Migração

- [ ] Migração SQL aplicada no Supabase (DEV primeiro, depois PROD)
- [ ] Enum `conversation_mode_enum` criado com 4 valores
- [ ] Coluna `conversation_mode` adicionada com default `discovery`
- [ ] Colunas de auditoria adicionadas (`mode_updated_at`, `mode_updated_reason`)
- [ ] Índice criado e funcionando
- [ ] Backfill executado para conversas existentes

### Código Python

- [ ] Arquivo `app/services/conversation_mode/__init__.py` criado
- [ ] Arquivo `types.py` com enum e dataclasses
- [ ] Arquivo `repository.py` com get/set
- [ ] `ConversationMode` exportado no `__init__.py`

### Validação

- [ ] Query retorna modo correto:
  ```sql
  SELECT id, conversation_mode FROM conversations LIMIT 10;
  ```
- [ ] Transição funciona:
  ```python
  await set_conversation_mode(id, ConversationMode.OFERTA, "test")
  info = await get_conversation_mode(id)
  assert info.mode == ConversationMode.OFERTA
  ```

### Não fazer neste epic

- [ ] NÃO implementar Capabilities Gate (E02)
- [ ] NÃO implementar Mode Router (E03)
- [ ] NÃO integrar no agente (E04)

---

## Comandos de Verificação

```bash
# Verificar migração aplicada
mcp__supabase-prod__execute_sql "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'conversations' AND column_name LIKE '%mode%';"

# Verificar distribuição de modos
mcp__supabase-prod__execute_sql "SELECT conversation_mode, COUNT(*) FROM conversations WHERE status = 'active' GROUP BY conversation_mode;"

# Verificar backfill
mcp__supabase-prod__execute_sql "SELECT COUNT(*) FROM conversations WHERE conversation_mode IS NULL;"
```

---

## Rollback

Se precisar reverter:

```sql
-- Rollback: remover conversation_mode
ALTER TABLE conversations DROP COLUMN IF EXISTS conversation_mode;
ALTER TABLE conversations DROP COLUMN IF EXISTS mode_updated_at;
ALTER TABLE conversations DROP COLUMN IF EXISTS mode_updated_reason;
DROP TYPE IF EXISTS conversation_mode_enum;
```

---

## Próximo

Após E01 concluído: [E02: Capabilities Gate](./epic-02-capabilities.md)
