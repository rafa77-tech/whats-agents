# Epic 02: Chip Selector

## Objetivo

Implementar **seletor inteligente** de chips que escolhe o melhor chip para cada mensagem baseado em:
- Tipo de mensagem (prospeccao, followup, resposta)
- Trust Score e permissoes
- Historico com o contato
- Continuidade de conversa
- Carga atual

## Contexto

| Tipo Mensagem | Trust Min | Permissao | Risco |
|---------------|-----------|-----------|-------|
| Prospeccao | 80 | pode_prospectar | Alto |
| Follow-up | 60 | pode_followup | Medio |
| Resposta | 40 | pode_responder | Baixo |

**Principio:** Mensagem de prospeccao usa chips mais saudaveis, resposta pode usar chips com Trust menor.

---

## Story 2.1: Modelo e Tipos

### Objetivo
Definir tipos e estruturas para selecao.

### Implementacao

**Arquivo:** `app/services/chips/selector.py`

```python
"""
Chip Selector - Selecao inteligente de chip por tipo de mensagem.

Considera:
- Trust Score do chip
- Permissoes (pode_prospectar, pode_followup, pode_responder)
- Uso atual (msgs/hora, msgs/dia)
- Historico com o contato
- Continuidade de conversa
"""
import logging
from typing import Optional, List, Dict, Literal
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Tipos de mensagem
TipoMensagem = Literal["prospeccao", "followup", "resposta"]


@dataclass
class ChipCandidate:
    """Candidato a enviar mensagem."""
    id: str
    telefone: str
    instance_name: str
    trust_score: int
    trust_level: str
    uso_hora: int
    uso_dia: int
    limite_hora: int
    limite_dia: int
    tem_historico: bool = False
    eh_chip_conversa: bool = False

    @property
    def capacidade_disponivel_hora(self) -> int:
        """Capacidade restante na hora."""
        return max(0, self.limite_hora - self.uso_hora)

    @property
    def capacidade_disponivel_dia(self) -> int:
        """Capacidade restante no dia."""
        return max(0, self.limite_dia - self.uso_dia)

    @property
    def score_selecao(self) -> float:
        """
        Score para ordenacao de candidatos.

        Maior = melhor candidato.
        """
        score = 0.0

        # Trust Score (peso alto)
        score += self.trust_score * 2

        # Capacidade disponivel
        score += self.capacidade_disponivel_hora * 5
        score += self.capacidade_disponivel_dia * 0.5

        # Bonus por historico (continuidade)
        if self.tem_historico:
            score += 50

        # Bonus forte se eh o chip da conversa
        if self.eh_chip_conversa:
            score += 200

        return score
```

### DoD

- [ ] TipoMensagem definido
- [ ] ChipCandidate com score

---

## Story 2.2: Selecao por Tipo

### Objetivo
Implementar selecao baseada no tipo de mensagem.

### Implementacao

```python
class ChipSelector:
    """Seletor inteligente de chips."""

    async def selecionar_chip(
        self,
        tipo_mensagem: TipoMensagem,
        conversa_id: Optional[str] = None,
        telefone_destino: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Seleciona melhor chip para enviar mensagem.

        Args:
            tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
            conversa_id: ID da conversa (para continuidade)
            telefone_destino: Telefone do destinatario

        Returns:
            Chip selecionado ou None
        """
        # 1. Se eh resposta e tem conversa, tentar manter no mesmo chip
        if tipo_mensagem == "resposta" and conversa_id:
            chip_conversa = await self._buscar_chip_conversa(conversa_id)
            if chip_conversa and chip_conversa.get("pode_responder"):
                logger.debug(
                    f"[ChipSelector] Mantendo conversa {conversa_id[:8]} no chip existente"
                )
                return chip_conversa

        # 2. Buscar chips elegiveis para o tipo
        candidatos = await self._buscar_candidatos(tipo_mensagem, telefone_destino)

        if not candidatos:
            logger.warning(f"[ChipSelector] Nenhum chip disponivel para {tipo_mensagem}")
            return None

        # 3. Ordenar por score de selecao
        candidatos.sort(key=lambda c: c.score_selecao, reverse=True)

        # 4. Selecionar melhor
        melhor = candidatos[0]

        logger.info(
            f"[ChipSelector] Selecionado {melhor.telefone} para {tipo_mensagem} "
            f"(Trust: {melhor.trust_score}, Score: {melhor.score_selecao:.1f})"
        )

        # Retornar como dict
        return await self._buscar_chip_completo(melhor.id)

    async def _buscar_chip_conversa(self, conversa_id: str) -> Optional[Dict]:
        """Busca chip atualmente associado a conversa."""
        result = supabase.table("conversation_chips").select(
            "chip_id, chips(*)"
        ).eq(
            "conversa_id", conversa_id
        ).eq(
            "active", True
        ).single().execute()

        if result.data and result.data.get("chips"):
            return result.data["chips"]

        return None

    async def _buscar_candidatos(
        self,
        tipo_mensagem: TipoMensagem,
        telefone_destino: Optional[str] = None,
    ) -> List[ChipCandidate]:
        """
        Busca chips elegiveis para o tipo de mensagem.

        Args:
            tipo_mensagem: Tipo da mensagem
            telefone_destino: Telefone destino (para verificar historico)

        Returns:
            Lista de ChipCandidate
        """
        # Query base
        query = supabase.table("chips").select(
            "id, telefone, instance_name, trust_score, trust_level, "
            "msgs_enviadas_hoje, limite_hora, limite_dia, "
            "pode_prospectar, pode_followup, pode_responder"
        ).eq("status", "active")

        # Filtrar por permissao
        if tipo_mensagem == "prospeccao":
            query = query.eq("pode_prospectar", True).gte("trust_score", 80)
        elif tipo_mensagem == "followup":
            query = query.eq("pode_followup", True).gte("trust_score", 60)
        else:  # resposta
            query = query.eq("pode_responder", True).gte("trust_score", 40)

        result = query.order("trust_score", desc=True).execute()

        if not result.data:
            return []

        # Converter para candidatos
        candidatos = []
        chip_ids = [c["id"] for c in result.data]

        # Buscar uso por hora (batch)
        uso_hora = await self._buscar_uso_hora_batch(chip_ids)

        # Buscar historico com telefone destino
        historico_chips = set()
        if telefone_destino:
            historico_chips = await self._buscar_chips_com_historico(
                telefone_destino, chip_ids
            )

        for chip in result.data:
            # Verificar limites
            uso_h = uso_hora.get(chip["id"], 0)
            uso_d = chip["msgs_enviadas_hoje"]

            if uso_h >= chip["limite_hora"]:
                continue  # Limite hora atingido

            if uso_d >= chip["limite_dia"]:
                continue  # Limite dia atingido

            candidatos.append(ChipCandidate(
                id=chip["id"],
                telefone=chip["telefone"],
                instance_name=chip["instance_name"],
                trust_score=chip["trust_score"],
                trust_level=chip["trust_level"],
                uso_hora=uso_h,
                uso_dia=uso_d,
                limite_hora=chip["limite_hora"],
                limite_dia=chip["limite_dia"],
                tem_historico=chip["id"] in historico_chips,
            ))

        return candidatos

    async def _buscar_uso_hora_batch(self, chip_ids: List[str]) -> Dict[str, int]:
        """
        Busca uso na ultima hora para multiplos chips.

        Returns:
            {chip_id: count}
        """
        uma_hora_atras = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        result = supabase.table("chip_interactions").select(
            "chip_id"
        ).in_(
            "chip_id", chip_ids
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        # Contar por chip
        uso = {}
        for row in result.data or []:
            chip_id = row["chip_id"]
            uso[chip_id] = uso.get(chip_id, 0) + 1

        return uso

    async def _buscar_chips_com_historico(
        self,
        telefone: str,
        chip_ids: List[str],
    ) -> set:
        """
        Verifica quais chips ja conversaram com o telefone.

        Returns:
            Set de chip_ids que tem historico
        """
        result = supabase.table("chip_interactions").select(
            "chip_id"
        ).eq(
            "destinatario", telefone
        ).in_(
            "chip_id", chip_ids
        ).execute()

        return {row["chip_id"] for row in result.data or []}

    async def _buscar_chip_completo(self, chip_id: str) -> Dict:
        """Busca chip completo por ID."""
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        return result.data
```

### DoD

- [ ] Selecao por tipo funcionando
- [ ] Filtro por permissao
- [ ] Verificacao de limites
- [ ] Historico considerado

---

## Story 2.3: Registro de Envio

### Objetivo
Registrar envio para metricas e mapeamento.

### Implementacao

```python
    async def registrar_envio(
        self,
        chip_id: str,
        conversa_id: str,
        tipo_mensagem: TipoMensagem,
        telefone_destino: str,
    ):
        """
        Registra envio de mensagem para metricas e mapeamento.

        Args:
            chip_id: ID do chip usado
            conversa_id: ID da conversa
            tipo_mensagem: Tipo da mensagem
            telefone_destino: Telefone destino
        """
        now = datetime.now(timezone.utc).isoformat()

        # 1. Upsert mapeamento conversa-chip
        # Se conversa nao tinha chip, associa
        # Se tinha outro chip, atualiza (migracao)
        existing = supabase.table("conversation_chips").select("id, chip_id").eq(
            "conversa_id", conversa_id
        ).eq("active", True).execute()

        if existing.data:
            # Atualizar se mudou
            if existing.data[0]["chip_id"] != chip_id:
                supabase.table("conversation_chips").update({
                    "chip_id": chip_id,
                    "migrated_at": now,
                    "migrated_from": existing.data[0]["chip_id"],
                }).eq("id", existing.data[0]["id"]).execute()
        else:
            # Criar novo mapeamento
            supabase.table("conversation_chips").insert({
                "conversa_id": conversa_id,
                "chip_id": chip_id,
                "active": True,
            }).execute()

        # 2. Registrar interacao
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": "msg_enviada",
            "destinatario": telefone_destino,
            "metadata": {
                "tipo_mensagem": tipo_mensagem,
                "conversa_id": conversa_id,
            }
        }).execute()

        # 3. Incrementar contadores do chip
        supabase.rpc("incrementar_msgs_chip", {
            "p_chip_id": chip_id,
        }).execute()

        logger.debug(
            f"[ChipSelector] Envio registrado: chip={chip_id[:8]}, "
            f"tipo={tipo_mensagem}, destino={telefone_destino}"
        )

    async def registrar_resposta_recebida(
        self,
        chip_id: str,
        telefone_origem: str,
        tempo_resposta_segundos: Optional[int] = None,
    ):
        """
        Registra resposta recebida para metricas de taxa de resposta.

        Args:
            chip_id: ID do chip que recebeu
            telefone_origem: Telefone que respondeu
            tempo_resposta_segundos: Tempo ate receber resposta
        """
        # Atualizar ultima interacao enviada para marcar como respondida
        # (ultimas 24h com esse destinatario)
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        supabase.table("chip_interactions").update({
            "obteve_resposta": True,
            "tempo_resposta_segundos": tempo_resposta_segundos,
        }).eq(
            "chip_id", chip_id
        ).eq(
            "destinatario", telefone_origem
        ).eq(
            "tipo", "msg_enviada"
        ).is_(
            "obteve_resposta", None
        ).gte(
            "created_at", ontem
        ).order(
            "created_at", desc=True
        ).limit(1).execute()

        # Registrar mensagem recebida
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": "msg_recebida",
            "destinatario": telefone_origem,
        }).execute()

        # Incrementar contador
        supabase.table("chips").update({
            "msgs_recebidas_total": supabase.sql("msgs_recebidas_total + 1"),
            "msgs_recebidas_hoje": supabase.sql("msgs_recebidas_hoje + 1"),
        }).eq("id", chip_id).execute()


# Singleton
chip_selector = ChipSelector()
```

### DoD

- [ ] Mapeamento conversa-chip
- [ ] Registro de interacoes
- [ ] Incremento de contadores
- [ ] Registro de respostas

---

## Story 2.4: Migration conversation_chips

### Objetivo
Tabela para mapeamento conversa-chip.

### Migration

```sql
-- Migration: create_conversation_chips
-- Sprint 26 - E02 - Mapeamento conversa-chip

CREATE TABLE conversation_chips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    chip_id UUID NOT NULL REFERENCES chips(id),

    -- Historico de migracoes
    migrated_at TIMESTAMPTZ,
    migrated_from UUID REFERENCES chips(id),

    -- Controle
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Apenas um mapeamento ativo por conversa
CREATE UNIQUE INDEX idx_conversation_chips_active ON conversation_chips(conversa_id)
    WHERE active = true;

-- Buscar conversas de um chip
CREATE INDEX idx_conversation_chips_chip ON conversation_chips(chip_id)
    WHERE active = true;

COMMENT ON TABLE conversation_chips IS 'Mapeamento conversa-chip para continuidade';


-- Funcao para incrementar contadores
CREATE OR REPLACE FUNCTION incrementar_msgs_chip(p_chip_id UUID)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE chips
    SET
        msgs_enviadas_total = msgs_enviadas_total + 1,
        msgs_enviadas_hoje = msgs_enviadas_hoje + 1,
        updated_at = now()
    WHERE id = p_chip_id;
END;
$$;


-- Job para resetar contadores diarios (rodar a meia-noite)
CREATE OR REPLACE FUNCTION resetar_contadores_diarios_chips()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE chips
    SET
        msgs_enviadas_hoje = 0,
        msgs_recebidas_hoje = 0;
END;
$$;
```

### DoD

- [ ] Tabela criada
- [ ] Indices otimizados
- [ ] Funcoes SQL

---

## Checklist do Epico

- [x] **E02.1** - Modelos e tipos
- [x] **E02.2** - Selecao por tipo
- [x] **E02.3** - Registro de envio
- [x] **E02.4** - Migration
- [x] Testes unitarios
- [x] Integracao com agente Julia (13/01/2026)

### Integracao com Pipeline Julia

**Implementado em:** `app/services/outbound.py`

A integracao usa a flag `MULTI_CHIP_ENABLED`:
- Quando `true`: usa ChipSelector para selecionar melhor chip
- Quando `false`: usa EVOLUTION_INSTANCE fixa (fallback legado)

**Funcoes adicionadas:**
- `_is_multi_chip_enabled()` - verifica flag
- `_determinar_tipo_mensagem(ctx)` - mapeia OutboundContext para tipo
- `_enviar_via_multi_chip()` - envia usando chip selecionado

**Mapeamento de tipos:**
| OutboundMethod | Tipo Mensagem |
|----------------|---------------|
| REPLY | resposta |
| CAMPAIGN (proativo) | prospeccao |
| FOLLOWUP/REACTIVATION | followup |
| outros | resposta (default) |

---

## Diagrama: Fluxo de Selecao

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHIP SELECTOR FLOW                            │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  Nova mensagem   │
                    │  a enviar        │
                    └────────┬─────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │   Qual tipo de mensagem?       │
            └────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │PROSPECCAO │      │ FOLLOWUP  │      │ RESPOSTA  │
   │Trust >= 80│      │Trust >= 60│      │Trust >= 40│
   │Alto risco │      │Medio risco│      │Baixo risco│
   └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │   Tem conversa_id?             │
            │   (continuidade)               │
            └────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │ SIM                         │ NAO
              ▼                             ▼
   ┌─────────────────────┐      ┌─────────────────────┐
   │ Buscar chip da      │      │ Buscar candidatos   │
   │ conversa            │      │ elegiveis           │
   └──────────┬──────────┘      └──────────┬──────────┘
              │                             │
              ▼                             ▼
   ┌─────────────────────┐      ┌─────────────────────┐
   │ Chip ainda tem      │      │ Filtrar por:        │
   │ permissao?          │      │ - Permissao         │
   └──────────┬──────────┘      │ - Limite hora       │
              │                 │ - Limite dia        │
       ┌──────┴──────┐          └──────────┬──────────┘
       │ SIM        │ NAO                   │
       ▼            │                       ▼
  ┌─────────┐       │          ┌─────────────────────┐
  │ Usar    │       │          │ Ordenar por:        │
  │ mesmo   │       │          │ - Score selecao     │
  │ chip    │       │          │   (Trust + Cap +    │
  └────┬────┘       │          │    Historico)       │
       │            │          └──────────┬──────────┘
       │            │                     │
       │            └──────────┐          │
       │                       │          │
       │                       ▼          ▼
       │              ┌─────────────────────────┐
       └─────────────>│    Chip selecionado     │
                      └───────────┬─────────────┘
                                  │
                                  ▼
                      ┌─────────────────────────┐
                      │  registrar_envio()      │
                      │  - Mapeamento           │
                      │  - Interacao            │
                      │  - Contadores           │
                      └─────────────────────────┘
```
