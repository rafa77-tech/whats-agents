# Sprint 15 - Policy Engine (Estado + Decisão Determinística)

**Início:** A definir
**Duração estimada:** 2 semanas
**Dependências:** Sprint 13 (Conhecimento Dinâmico) completa

---

## Objetivo

Separar **DECISÃO** (determinística, auditável) de **EXECUÇÃO** (LLM gerando texto).

Hoje a Julia decide "o que fazer" parcialmente no prompt, o que é não-determinístico e difícil de auditar. Após essa sprint:

- **StateUpdate** atualiza estado do médico a cada interação
- **PolicyDecide** aplica regras determinísticas e retorna ação + constraints
- **LLM** apenas executa a ação dentro dos trilhos definidos

### Benefícios

| Antes | Depois |
|-------|--------|
| Decisão no prompt (não-determinística) | Decisão em código (determinística) |
| Difícil auditar "por que fez X" | Logs com reasoning de cada decisão |
| Estado espalhado em `clientes` | Estado consolidado em `doctor_state` |
| Regras implícitas no prompt | Regras explícitas em `rules.py` |

---

## Arquitetura Final

```
WEBHOOK (mensagem recebida)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  1. CARREGAR CONTEXTO                                   │
│     - montar_contexto_completo() [já existe]            │
│     - load_doctor_state() [NOVO]                        │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  2. DETECTAR SINAIS                                     │
│     - orquestrador.detector_objecao.detectar() [existe] │
│     - Retorna ResultadoDeteccao com severidade [NOVO]   │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  3. STATE UPDATE [NOVO]                                 │
│     - Atualiza temperature (médico respondeu = aquece)  │
│     - Atualiza last_inbound_at                          │
│     - Grava active_objection (persiste até resolução)   │
│     - Detecta opt-out → permission_state = opted_out    │
│     - NÃO limpa objeção automaticamente                 │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  4. POLICY DECIDE [NOVO]                                │
│     - Aplica regras de produção em ordem                │
│     - Retorna PolicyDecision:                           │
│       • primary_action                                  │
│       • allowed_actions / forbidden_actions             │
│       • tone, requires_human, constraints_text          │
└─────────────────────────────────────────────────────────┘
    │
    ├── requires_human=True ──▶ HANDOFF (fluxo existente)
    │
    ├── primary_action=WAIT ──▶ NÃO RESPONDER
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  5. GERAR RESPOSTA                                      │
│     - OrquestradorConhecimento busca contexto/RAG       │
│     - Prompt recebe constraints_text do PolicyDecide    │
│     - LLM gera resposta dentro dos trilhos              │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  6. STATE UPDATE PÓS-ENVIO [NOVO]                       │
│     - Atualiza last_outbound_at                         │
│     - Incrementa contact_count_7d                       │
│     - Atualiza next_allowed_at                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
ENVIAR WHATSAPP (já existe)
```

---

## Épicos

| # | Épico | Descrição |
|---|-------|-----------|
| E01 | Tabela doctor_state | Migração SQL + backfill |
| E02 | Módulo policy | Estrutura, types, regras |
| E03 | Severity Mapper | Mapeamento objeção → severidade |
| E04 | StateUpdate | Lógica de atualização de estado |
| E05 | PolicyDecide | Motor de decisão com regras |
| E06 | Integração no agente | Plugar no fluxo existente |
| E07 | Job de decay | Batch para decaimento de temperatura |
| E08 | Testes e validação | Testes unitários e integração |

---

## E01 - Tabela doctor_state

### Objetivo
Criar tabela dedicada para estado dinâmico do relacionamento com médicos, separada dos dados cadastrais em `clientes`.

### Schema

```sql
-- Migração: create_doctor_state
CREATE TABLE doctor_state (
    -- PK = FK (1:1 com clientes)
    cliente_id UUID PRIMARY KEY REFERENCES clientes(id) ON DELETE CASCADE,

    -- Permissão
    permission_state TEXT NOT NULL DEFAULT 'none'
        CHECK (permission_state IN ('none', 'initial', 'active', 'cooling_off', 'opted_out')),
    cooling_off_until TIMESTAMPTZ,

    -- Temperatura (engajamento)
    temperature DECIMAL(3,2) NOT NULL DEFAULT 0.50
        CHECK (temperature >= 0.00 AND temperature <= 1.00),
    temperature_trend TEXT NOT NULL DEFAULT 'stable'
        CHECK (temperature_trend IN ('warming', 'cooling', 'stable')),
    temperature_band TEXT GENERATED ALWAYS AS (
        CASE
            WHEN temperature < 0.33 THEN 'cold'
            WHEN temperature < 0.66 THEN 'warm'
            ELSE 'hot'
        END
    ) STORED,

    -- Tolerância a risco (conservador por default)
    risk_tolerance TEXT NOT NULL DEFAULT 'unknown'
        CHECK (risk_tolerance IN ('unknown', 'low', 'medium', 'high')),

    -- Controle de contato (inbound/outbound separados)
    last_inbound_at TIMESTAMPTZ,
    last_outbound_at TIMESTAMPTZ,
    last_outbound_actor TEXT CHECK (last_outbound_actor IN ('julia', 'humano')),
    next_allowed_at TIMESTAMPTZ,
    contact_count_7d INT NOT NULL DEFAULT 0,

    -- Objeção ativa (persiste até resolução explícita)
    active_objection TEXT,
    objection_severity TEXT CHECK (objection_severity IN ('low', 'medium', 'high', 'grave')),
    objection_detected_at TIMESTAMPTZ,
    objection_resolved_at TIMESTAMPTZ,

    -- Contexto ativo
    pending_action TEXT,
    current_intent TEXT,

    -- Lifecycle
    lifecycle_stage TEXT NOT NULL DEFAULT 'novo'
        CHECK (lifecycle_stage IN ('novo', 'prospecting', 'engaged', 'qualified', 'active', 'churned')),

    -- Flags livres (migra de clientes.flags_comportamento)
    flags JSONB NOT NULL DEFAULT '{}',

    -- Controle de decay (para job idempotente)
    last_decay_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_doctor_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_doctor_state_updated_at
    BEFORE UPDATE ON doctor_state
    FOR EACH ROW
    EXECUTE FUNCTION update_doctor_state_updated_at();

-- Índices
CREATE INDEX idx_doctor_state_permission ON doctor_state(permission_state);
CREATE INDEX idx_doctor_state_temperature_band ON doctor_state(temperature_band);
CREATE INDEX idx_doctor_state_next_allowed ON doctor_state(next_allowed_at)
    WHERE next_allowed_at IS NOT NULL;
CREATE INDEX idx_doctor_state_active_objection ON doctor_state(objection_severity)
    WHERE active_objection IS NOT NULL;
CREATE INDEX idx_doctor_state_lifecycle ON doctor_state(lifecycle_stage);

-- Comentário
COMMENT ON TABLE doctor_state IS 'Estado dinâmico do relacionamento com cada médico - Sprint 15';
COMMENT ON COLUMN doctor_state.permission_state IS 'none=nunca conversou, initial=contato inicial, active=conversa saudável, cooling_off=pausa por atrito, opted_out=não contatar';
COMMENT ON COLUMN doctor_state.temperature IS 'Engajamento 0.0 (frio) a 1.0 (quente)';
COMMENT ON COLUMN doctor_state.active_objection IS 'Objeção não resolvida - persiste até resolve_objection()';
COMMENT ON COLUMN doctor_state.last_decay_at IS 'Última vez que decay foi aplicado - para idempotência do job';
```

### Backfill

```sql
-- Popular doctor_state a partir de clientes existentes
INSERT INTO doctor_state (
    cliente_id,
    permission_state,
    lifecycle_stage,
    last_inbound_at,
    temperature,
    flags
)
SELECT
    id as cliente_id,
    -- Mapear permission_state
    CASE
        WHEN opted_out = true OR opt_out = true THEN 'opted_out'
        WHEN stage_jornada IN ('respondeu', 'em_conversacao', 'qualificado', 'ativo', 'cadastrado') THEN 'active'
        WHEN stage_jornada IN ('aguardando_resposta', 'msg_enviada') THEN 'initial'
        ELSE 'none'
    END as permission_state,
    -- Mapear lifecycle_stage
    CASE
        WHEN stage_jornada = 'novo' THEN 'novo'
        WHEN stage_jornada IN ('aguardando_resposta', 'nao_respondeu', 'msg_enviada') THEN 'prospecting'
        WHEN stage_jornada IN ('respondeu', 'em_conversacao') THEN 'engaged'
        WHEN stage_jornada = 'qualificado' THEN 'qualified'
        WHEN stage_jornada IN ('cadastrado', 'ativo') THEN 'active'
        WHEN stage_jornada IN ('perdido', 'opt_out', 'inativo') THEN 'churned'
        ELSE 'novo'
    END as lifecycle_stage,
    -- Última interação
    ultima_mensagem_data as last_inbound_at,
    -- Temperatura inicial baseada em engajamento
    CASE
        WHEN stage_jornada IN ('ativo', 'cadastrado', 'qualificado') THEN 0.70
        WHEN stage_jornada IN ('respondeu', 'em_conversacao') THEN 0.50
        WHEN stage_jornada IN ('aguardando_resposta') THEN 0.30
        ELSE 0.20
    END as temperature,
    -- Migrar flags existentes
    COALESCE(flags_comportamento, '{}')::jsonb as flags
FROM clientes
WHERE deleted_at IS NULL
ON CONFLICT (cliente_id) DO NOTHING;
```

### DoD (Definition of Done)

- [ ] Migração SQL aplicada no Supabase
- [ ] Backfill executado com sucesso
- [ ] Todos os clientes existentes têm registro em doctor_state
- [ ] Índices criados e funcionando
- [ ] Trigger de updated_at testado
- [ ] Query de validação: `SELECT COUNT(*) FROM clientes c LEFT JOIN doctor_state ds ON c.id = ds.cliente_id WHERE ds.cliente_id IS NULL AND c.deleted_at IS NULL` retorna 0

---

## E02 - Módulo policy

### Objetivo
Criar estrutura do módulo `app/services/policy/` com types e enums.

### Estrutura de Arquivos

```
app/services/policy/
├── __init__.py
├── types.py           # Enums e dataclasses
├── state_update.py    # StateUpdate (E04)
├── rules.py           # Regras de produção (E05)
├── decide.py          # PolicyDecide (E05)
└── repository.py      # Load/save doctor_state
```

### types.py

```python
"""
Tipos e estruturas do Policy Engine.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PermissionState(Enum):
    """Estado de permissão de contato."""
    NONE = "none"              # Nunca conversou
    INITIAL = "initial"        # Contato inicial estabelecido
    ACTIVE = "active"          # Conversa aberta e saudável
    COOLING_OFF = "cooling_off"  # Pausa por atrito
    OPTED_OUT = "opted_out"    # Não contatar (terminal)


class TemperatureBand(Enum):
    """Faixa de temperatura (derivada)."""
    COLD = "cold"    # < 0.33
    WARM = "warm"    # 0.33 - 0.66
    HOT = "hot"      # > 0.66


class TemperatureTrend(Enum):
    """Tendência de temperatura."""
    WARMING = "warming"
    COOLING = "cooling"
    STABLE = "stable"


class ObjectionSeverity(Enum):
    """Severidade de objeção."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    GRAVE = "grave"  # Aciona handoff


class RiskTolerance(Enum):
    """Tolerância a vagas de risco."""
    UNKNOWN = "unknown"  # Conservador por default
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LifecycleStage(Enum):
    """Estágio no ciclo de vida."""
    NOVO = "novo"
    PROSPECTING = "prospecting"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    CHURNED = "churned"


class PrimaryAction(Enum):
    """Ação principal decidida pela policy."""
    DISCOVERY = "discovery"        # Primeiro contato, conhecer médico
    OFFER = "offer"                # Oferecer vaga
    FOLLOWUP = "followup"          # Dar continuidade
    REACTIVATION = "reactivation"  # Reativar médico inativo
    HANDOFF = "handoff"            # Transferir para humano
    WAIT = "wait"                  # Não fazer nada


class Tone(Enum):
    """Tom da resposta."""
    LEVE = "leve"              # Descontraído, amigável
    DIRETO = "direto"          # Objetivo, sem rodeios
    CAUTELOSO = "cauteloso"    # Cuidado extra
    CRISE = "crise"            # Situação crítica


@dataclass
class DoctorState:
    """Estado atual do médico (lido do banco)."""
    cliente_id: str

    # Permissão
    permission_state: PermissionState
    cooling_off_until: Optional[datetime] = None

    # Temperatura
    temperature: float = 0.5
    temperature_trend: TemperatureTrend = TemperatureTrend.STABLE
    temperature_band: TemperatureBand = TemperatureBand.WARM

    # Risco
    risk_tolerance: RiskTolerance = RiskTolerance.UNKNOWN

    # Contato
    last_inbound_at: Optional[datetime] = None
    last_outbound_at: Optional[datetime] = None
    last_outbound_actor: Optional[str] = None
    next_allowed_at: Optional[datetime] = None
    contact_count_7d: int = 0

    # Objeção
    active_objection: Optional[str] = None
    objection_severity: Optional[ObjectionSeverity] = None
    objection_detected_at: Optional[datetime] = None
    objection_resolved_at: Optional[datetime] = None

    # Contexto
    pending_action: Optional[str] = None
    current_intent: Optional[str] = None
    lifecycle_stage: LifecycleStage = LifecycleStage.NOVO

    # Flags
    flags: dict = field(default_factory=dict)

    # Decay
    last_decay_at: Optional[datetime] = None

    def has_unresolved_objection(self) -> bool:
        """Verifica se há objeção ativa não resolvida."""
        return (
            self.active_objection is not None
            and self.objection_resolved_at is None
        )

    def is_contactable(self) -> bool:
        """Verifica se pode ser contatado."""
        if self.permission_state == PermissionState.OPTED_OUT:
            return False
        if self.permission_state == PermissionState.COOLING_OFF:
            if self.cooling_off_until and datetime.utcnow() < self.cooling_off_until:
                return False
        if self.next_allowed_at and datetime.utcnow() < self.next_allowed_at:
            return False
        return True


@dataclass
class PolicyDecision:
    """Resultado do PolicyDecide - o que a Julia pode/não pode fazer."""
    primary_action: PrimaryAction
    allowed_actions: list[str]
    forbidden_actions: list[str]
    tone: Tone
    requires_human: bool
    constraints_text: str  # Bloco para injetar no prompt
    reasoning: str  # Para logs/debug

    def to_dict(self) -> dict:
        """Serializa para logging."""
        return {
            "primary_action": self.primary_action.value,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "tone": self.tone.value,
            "requires_human": self.requires_human,
            "reasoning": self.reasoning,
        }
```

### repository.py

```python
"""
Repositório para doctor_state.
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json
from .types import (
    DoctorState, PermissionState, TemperatureTrend,
    TemperatureBand, ObjectionSeverity, RiskTolerance, LifecycleStage
)

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos


def _row_to_state(row: dict) -> DoctorState:
    """Converte row do banco para DoctorState."""
    return DoctorState(
        cliente_id=row["cliente_id"],
        permission_state=PermissionState(row["permission_state"]),
        cooling_off_until=row.get("cooling_off_until"),
        temperature=float(row.get("temperature", 0.5)),
        temperature_trend=TemperatureTrend(row.get("temperature_trend", "stable")),
        temperature_band=TemperatureBand(row.get("temperature_band", "warm")),
        risk_tolerance=RiskTolerance(row.get("risk_tolerance", "unknown")),
        last_inbound_at=row.get("last_inbound_at"),
        last_outbound_at=row.get("last_outbound_at"),
        last_outbound_actor=row.get("last_outbound_actor"),
        next_allowed_at=row.get("next_allowed_at"),
        contact_count_7d=row.get("contact_count_7d", 0),
        active_objection=row.get("active_objection"),
        objection_severity=ObjectionSeverity(row["objection_severity"]) if row.get("objection_severity") else None,
        objection_detected_at=row.get("objection_detected_at"),
        objection_resolved_at=row.get("objection_resolved_at"),
        pending_action=row.get("pending_action"),
        current_intent=row.get("current_intent"),
        lifecycle_stage=LifecycleStage(row.get("lifecycle_stage", "novo")),
        flags=row.get("flags", {}),
        last_decay_at=row.get("last_decay_at"),
    )


async def load_doctor_state(cliente_id: str) -> Optional[DoctorState]:
    """
    Carrega estado do médico.

    Tenta cache primeiro, depois banco.
    Se não existir, cria registro default.
    """
    cache_key = f"doctor_state:{cliente_id}"

    # Tentar cache
    cached = await cache_get_json(cache_key)
    if cached:
        return _row_to_state(cached)

    # Buscar no banco
    try:
        response = (
            supabase.table("doctor_state")
            .select("*")
            .eq("cliente_id", cliente_id)
            .single()
            .execute()
        )

        if response.data:
            await cache_set_json(cache_key, response.data, CACHE_TTL)
            return _row_to_state(response.data)

        # Não existe: criar registro default
        return await create_default_state(cliente_id)

    except Exception as e:
        logger.error(f"Erro ao carregar doctor_state: {e}")
        # Retornar estado default em memória para não quebrar fluxo
        return DoctorState(
            cliente_id=cliente_id,
            permission_state=PermissionState.NONE,
        )


async def create_default_state(cliente_id: str) -> DoctorState:
    """Cria registro default para médico novo."""
    try:
        response = (
            supabase.table("doctor_state")
            .insert({"cliente_id": cliente_id})
            .execute()
        )

        if response.data:
            return _row_to_state(response.data[0])

    except Exception as e:
        logger.error(f"Erro ao criar doctor_state: {e}")

    return DoctorState(
        cliente_id=cliente_id,
        permission_state=PermissionState.NONE,
    )


async def save_doctor_state_updates(cliente_id: str, updates: dict) -> bool:
    """
    Salva atualizações no estado do médico.

    Args:
        cliente_id: ID do médico
        updates: Dict com campos a atualizar

    Returns:
        True se sucesso
    """
    if not updates:
        return True

    try:
        # Invalidar cache
        cache_key = f"doctor_state:{cliente_id}"
        await cache_set_json(cache_key, None, 0)

        # Atualizar banco
        response = (
            supabase.table("doctor_state")
            .update(updates)
            .eq("cliente_id", cliente_id)
            .execute()
        )

        logger.debug(f"doctor_state atualizado: {cliente_id} -> {list(updates.keys())}")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar doctor_state: {e}")
        return False


async def resolve_objection(cliente_id: str) -> bool:
    """
    Marca objeção como resolvida.

    Chamado quando:
    - Humano marca como resolvido
    - Médico confirma resolução
    - pending_action resolvida
    """
    return await save_doctor_state_updates(cliente_id, {
        "objection_resolved_at": datetime.utcnow().isoformat(),
    })
```

### DoD (Definition of Done)

- [ ] Arquivos criados em `app/services/policy/`
- [ ] `__init__.py` exporta classes principais
- [ ] Types cobrem todos os estados possíveis
- [ ] Repository com load/save funcionando
- [ ] Cache funcionando corretamente
- [ ] Logs de debug em operações críticas

---

## E03 - Severity Mapper

### Objetivo
Mapear objeções detectadas para severidade de forma determinística.

**IMPORTANTE:** Colocar em módulo neutro para evitar import circular.

### Arquivo: `app/services/classificacao/severity_mapper.py`

```python
"""
Mapeamento determinístico de objeção → severidade.

ARQUITETURA:
- Este módulo é NEUTRO (não depende de policy)
- conhecimento/ pode usar
- policy/ pode usar
- Evita circular imports
"""
from enum import Enum
from typing import Optional


class ObjectionSeverity(Enum):
    """Severidade de objeção (duplicado para evitar import de policy)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    GRAVE = "grave"


# Mapeamento: tipo de objeção → severidade base
# Tipos vêm de app/services/conhecimento/detector_objecao.py
SEVERITY_BY_TYPE = {
    # GRAVE - aciona handoff imediato
    "opt_out": ObjectionSeverity.GRAVE,
    "ameaca": ObjectionSeverity.GRAVE,
    "agressao": ObjectionSeverity.GRAVE,
    "acusacao_etica": ObjectionSeverity.GRAVE,
    "pedido_humano": ObjectionSeverity.GRAVE,
    "denuncia": ObjectionSeverity.GRAVE,

    # HIGH - atenção redobrada, pode escalar
    "desconfianca": ObjectionSeverity.HIGH,
    "conflito_plantao": ObjectionSeverity.HIGH,
    "reclamacao_grave": ObjectionSeverity.HIGH,
    "insatisfacao_servico": ObjectionSeverity.HIGH,

    # MEDIUM - objeções comuns, tratáveis pela Julia
    "valor": ObjectionSeverity.MEDIUM,
    "preco": ObjectionSeverity.MEDIUM,
    "agenda": ObjectionSeverity.MEDIUM,
    "horario": ObjectionSeverity.MEDIUM,
    "ja_tem_escala": ObjectionSeverity.MEDIUM,
    "nao_atende": ObjectionSeverity.MEDIUM,

    # LOW - objeções leves, fácil contornar
    "distancia": ObjectionSeverity.LOW,
    "localizacao": ObjectionSeverity.LOW,
    "curiosidade": ObjectionSeverity.LOW,
    "sem_interesse_agora": ObjectionSeverity.LOW,
    "ocupado": ObjectionSeverity.LOW,
    "depois": ObjectionSeverity.LOW,
}

# Keywords que SEMPRE elevam para GRAVE, independente do tipo detectado
GRAVE_KEYWORDS = [
    # Opt-out explícito
    "não me procure",
    "para de me mandar",
    "não quero mais",
    "me tire da lista",
    "remove meu número",
    "não manda mais",
    "para de mandar",

    # Ameaças legais
    "vou denunciar",
    "vou processar",
    "advogado",
    "processo",
    "procon",
    "anatel",

    # Agressividade
    "spam",
    "bloqueado",
    "vou bloquear",
    "isso é golpe",
    "quem te deu meu número",
]

# Keywords que elevam para HIGH
HIGH_KEYWORDS = [
    "desconfio",
    "não confio",
    "parece bot",
    "é robô",
    "automatizado",
    "quero falar com gente",
    "pessoa de verdade",
]


def map_severity(
    tipo_objecao: str,
    subtipo: Optional[str],
    mensagem: str,
) -> ObjectionSeverity:
    """
    Mapeia objeção para severidade.

    Ordem de prioridade:
    1. Keywords graves (sempre GRAVE)
    2. Keywords high (eleva para HIGH se não for GRAVE)
    3. Mapa por tipo
    4. Default MEDIUM

    Args:
        tipo_objecao: Tipo detectado (ex: "valor", "opt_out")
        subtipo: Subtipo se houver
        mensagem: Mensagem original para análise de keywords

    Returns:
        ObjectionSeverity
    """
    mensagem_lower = mensagem.lower()

    # 1. Checar keywords graves
    for keyword in GRAVE_KEYWORDS:
        if keyword in mensagem_lower:
            return ObjectionSeverity.GRAVE

    # 2. Checar keywords high
    base_severity = SEVERITY_BY_TYPE.get(tipo_objecao.lower(), ObjectionSeverity.MEDIUM)

    for keyword in HIGH_KEYWORDS:
        if keyword in mensagem_lower:
            # Só eleva se não for já GRAVE
            if base_severity not in (ObjectionSeverity.GRAVE,):
                return ObjectionSeverity.HIGH

    # 3. Usar mapa por tipo
    return base_severity


def is_opt_out(tipo_objecao: str, mensagem: str) -> bool:
    """
    Verifica se é opt-out (terminal, não é cooling_off).

    Opt-out é diferente de atrito:
    - Opt-out: "não me procure mais" → permission_state = opted_out
    - Atrito: "spam", agressividade → permission_state = cooling_off
    """
    tipo_lower = tipo_objecao.lower()
    mensagem_lower = mensagem.lower()

    # Tipo explícito
    if tipo_lower == "opt_out":
        return True

    # Keywords de opt-out
    opt_out_keywords = [
        "não me procure",
        "para de me mandar",
        "não quero mais",
        "me tire da lista",
        "remove meu número",
        "não manda mais",
        "para de mandar",
        "me remove",
        "tire meu contato",
    ]

    for keyword in opt_out_keywords:
        if keyword in mensagem_lower:
            return True

    return False
```

### DoD (Definition of Done)

- [ ] Arquivo criado em `app/services/classificacao/`
- [ ] `__init__.py` atualizado para exportar
- [ ] Mapeamento cobre todos os tipos de objeção existentes
- [ ] `is_opt_out()` distingue opt-out de atrito
- [ ] Testes unitários para keywords graves
- [ ] Testes unitários para mapeamento por tipo

---

## E04 - StateUpdate

### Objetivo
Implementar lógica de atualização de estado baseada em eventos.

### Arquivo: `app/services/policy/state_update.py`

```python
"""
StateUpdate - Atualiza doctor_state baseado em eventos.

REGRAS CRÍTICAS:
1. Objeção NÃO é limpa automaticamente - persiste até resolução explícita
2. Opt-out é terminal (opted_out), não vira cooling_off
3. Cooling_off é para atrito/risco, não para quem pediu para parar
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.classificacao.severity_mapper import (
    map_severity, is_opt_out, ObjectionSeverity
)
from .types import DoctorState, PermissionState, TemperatureTrend

logger = logging.getLogger(__name__)


class StateUpdate:
    """Atualiza doctor_state baseado em eventos."""

    def on_inbound_message(
        self,
        state: DoctorState,
        mensagem: str,
        objecao_detectada: Optional[dict],
    ) -> dict:
        """
        Atualiza estado quando médico envia mensagem.

        Args:
            state: Estado atual
            mensagem: Texto da mensagem
            objecao_detectada: ResultadoDeteccao do detector (ou None)

        Returns:
            Dict com campos a atualizar no banco
        """
        updates = {
            "last_inbound_at": datetime.utcnow().isoformat(),
        }

        # === TEMPERATURA ===
        # Médico respondeu → aquece temperatura
        new_temp = min(1.0, state.temperature + 0.1)
        if new_temp != state.temperature:
            updates["temperature"] = round(new_temp, 2)
            updates["temperature_trend"] = TemperatureTrend.WARMING.value

        # === PERMISSION STATE ===
        # Se estava em 'none' ou 'initial', promove para 'active'
        # (exceto se detectar opt-out abaixo)
        if state.permission_state in (PermissionState.NONE, PermissionState.INITIAL):
            updates["permission_state"] = PermissionState.ACTIVE.value

        # Se estava em cooling_off e voltou a falar, volta para active
        if state.permission_state == PermissionState.COOLING_OFF:
            updates["permission_state"] = PermissionState.ACTIVE.value
            updates["cooling_off_until"] = None

        # === LIFECYCLE ===
        # Se estava em 'prospecting', promove para 'engaged'
        if state.lifecycle_stage.value == "prospecting":
            updates["lifecycle_stage"] = "engaged"

        # === OBJEÇÃO ===
        if objecao_detectada and objecao_detectada.get("tem_objecao"):
            tipo = objecao_detectada.get("tipo", "")
            if hasattr(tipo, "value"):
                tipo = tipo.value

            subtipo = objecao_detectada.get("subtipo")

            # Calcular severidade
            severity = map_severity(tipo, subtipo, mensagem)

            # Verificar se é opt-out (terminal)
            if is_opt_out(tipo, mensagem):
                updates["permission_state"] = PermissionState.OPTED_OUT.value
                updates["active_objection"] = "opt_out"
                updates["objection_severity"] = ObjectionSeverity.GRAVE.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()
                logger.warning(f"OPT-OUT detectado para {state.cliente_id}")

            # Objeção grave (não opt-out) → cooling_off
            elif severity == ObjectionSeverity.GRAVE:
                updates["permission_state"] = PermissionState.COOLING_OFF.value
                updates["cooling_off_until"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
                updates["active_objection"] = tipo
                updates["objection_severity"] = severity.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()
                logger.warning(f"Objeção GRAVE para {state.cliente_id}: {tipo}")

            # Objeção não-grave → registrar mas não mudar permission
            else:
                updates["active_objection"] = tipo
                updates["objection_severity"] = severity.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()

        # IMPORTANTE: NÃO limpar objeção se não detectou nova
        # Objeção persiste até resolução explícita via resolve_objection()
        # Apenas atualizar trend se não houver objeção nova
        elif state.has_unresolved_objection():
            # Médico respondeu sem nova objeção → trend pode melhorar
            # mas NÃO limpa a objeção
            updates["temperature_trend"] = TemperatureTrend.STABLE.value

        return updates

    def on_outbound_message(
        self,
        state: DoctorState,
        actor: str = "julia",
    ) -> dict:
        """
        Atualiza estado após Julia/humano enviar mensagem.

        Args:
            state: Estado atual
            actor: 'julia' ou 'humano'

        Returns:
            Dict com campos a atualizar
        """
        return {
            "last_outbound_at": datetime.utcnow().isoformat(),
            "last_outbound_actor": actor,
            "contact_count_7d": state.contact_count_7d + 1,
        }

    def decay_temperature(
        self,
        state: DoctorState,
        now: Optional[datetime] = None,
    ) -> dict:
        """
        Decai temperatura por inatividade (para job batch).

        Usa last_decay_at para ser idempotente.

        Args:
            state: Estado atual
            now: Timestamp atual (para testes)

        Returns:
            Dict com campos a atualizar (vazio se nada a fazer)
        """
        now = now or datetime.utcnow()

        # Calcular dias desde último decay OU último inbound
        reference = state.last_decay_at or state.last_inbound_at
        if not reference:
            return {}

        # Converter se for string
        if isinstance(reference, str):
            reference = datetime.fromisoformat(reference.replace("Z", "+00:00"))

        days_since = (now - reference).days

        if days_since <= 0:
            return {}

        # Decay: -0.05 por dia de inatividade
        decay_amount = min(state.temperature, days_since * 0.05)

        if decay_amount <= 0:
            return {}

        new_temp = max(0.0, state.temperature - decay_amount)

        return {
            "temperature": round(new_temp, 2),
            "temperature_trend": TemperatureTrend.COOLING.value,
            "last_decay_at": now.isoformat(),
        }

    def on_objection_resolved(self, state: DoctorState) -> dict:
        """
        Marca objeção como resolvida.

        Chamado quando:
        - Humano marca como resolvido via Slack/Chatwoot
        - Médico confirma resolução explicitamente
        - Ação pendente foi concluída
        """
        if not state.has_unresolved_objection():
            return {}

        return {
            "objection_resolved_at": datetime.utcnow().isoformat(),
            # NÃO limpa active_objection - mantém histórico
            # NÃO limpa objection_severity - mantém histórico
        }
```

### DoD (Definition of Done)

- [ ] `on_inbound_message` atualiza temperatura corretamente
- [ ] Opt-out seta `permission_state = opted_out` (terminal)
- [ ] Objeção grave seta `cooling_off` com prazo
- [ ] Objeção NÃO é limpa automaticamente
- [ ] `on_outbound_message` incrementa contadores
- [ ] `decay_temperature` usa `last_decay_at` para idempotência
- [ ] Testes unitários para cada cenário

---

## E05 - PolicyDecide

### Objetivo
Implementar motor de decisão com regras determinísticas.

### Arquivo: `app/services/policy/rules.py`

```python
"""
Regras de produção do Policy Engine.

IMPORTANTE:
- Regras são funções PURAS (sem I/O)
- Primeira regra que retorna não-None vence
- rule_default é o fallback (sempre retorna)
"""
from datetime import datetime, timedelta
from typing import Optional

from .types import (
    DoctorState, PolicyDecision, PrimaryAction, Tone,
    PermissionState, ObjectionSeverity, LifecycleStage,
)


def rule_opted_out(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: médico fez opt-out → não contatar.

    Opt-out é TERMINAL. Não há volta automática.
    """
    if state.permission_state == PermissionState.OPTED_OUT:
        return PolicyDecision(
            primary_action=PrimaryAction.WAIT,
            allowed_actions=[],
            forbidden_actions=["*"],
            tone=Tone.LEVE,  # Não vai responder, mas precisa de um valor
            requires_human=False,
            constraints_text="MÉDICO FEZ OPT-OUT. NÃO RESPONDER.",
            reasoning="permission_state=opted_out (terminal)"
        )
    return None


def rule_cooling_off(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: médico em cooling off → aguardar prazo.
    """
    if state.permission_state == PermissionState.COOLING_OFF:
        if state.cooling_off_until:
            now = datetime.utcnow()
            # Converter se for string
            until = state.cooling_off_until
            if isinstance(until, str):
                until = datetime.fromisoformat(until.replace("Z", "+00:00"))

            if now < until:
                days_left = (until - now).days
                return PolicyDecision(
                    primary_action=PrimaryAction.WAIT,
                    allowed_actions=[],
                    forbidden_actions=["proactive_contact", "offer", "followup"],
                    tone=Tone.LEVE,
                    requires_human=False,
                    constraints_text=f"MÉDICO EM PAUSA ({days_left} dias restantes). NÃO INICIAR CONTATO PROATIVO.",
                    reasoning=f"cooling_off até {until.isoformat()}"
                )
    return None


def rule_grave_objection(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: objeção grave ativa → handoff para humano.
    """
    if (
        state.has_unresolved_objection()
        and state.objection_severity == ObjectionSeverity.GRAVE
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.HANDOFF,
            allowed_actions=["acknowledge", "transfer", "apologize"],
            forbidden_actions=["offer", "negotiate", "insist", "pressure"],
            tone=Tone.CRISE,
            requires_human=True,
            constraints_text=(
                "SITUAÇÃO CRÍTICA. Médico tem objeção grave não resolvida.\n"
                "- Apenas reconheça a situação\n"
                "- Transfira para humano\n"
                "- NÃO tente resolver sozinha"
            ),
            reasoning=f"objection_severity=grave, tipo={state.active_objection}"
        )
    return None


def rule_high_objection(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: objeção HIGH ativa → cautela extra.
    """
    if (
        state.has_unresolved_objection()
        and state.objection_severity == ObjectionSeverity.HIGH
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["clarify", "apologize", "offer_help"],
            forbidden_actions=["offer", "pressure", "insist"],
            tone=Tone.CAUTELOSO,
            requires_human=False,
            constraints_text=(
                "ATENÇÃO: Médico tem objeção pendente (alta severidade).\n"
                "- Seja extra cuidadosa\n"
                "- Esclareça dúvidas antes de oferecer\n"
                "- Se escalar, transfira para humano"
            ),
            reasoning=f"objection_severity=high, tipo={state.active_objection}"
        )
    return None


def rule_new_doctor_first_contact(
    state: DoctorState,
    is_first_message: bool = False,
    conversa_status: str = "active",
    **kwargs
) -> Optional[PolicyDecision]:
    """
    Regra: médico novo, primeira mensagem → discovery.
    """
    if (
        state.lifecycle_stage == LifecycleStage.NOVO
        and is_first_message
        and conversa_status == "active"
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.DISCOVERY,
            allowed_actions=["present_julia", "ask_specialty", "build_rapport", "ask_interest"],
            forbidden_actions=["offer_shift", "negotiate_value", "ask_docs", "pressure"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text=(
                "PRIMEIRO CONTATO com médico novo.\n"
                "- Apresente-se de forma leve\n"
                "- Entenda o perfil e interesse\n"
                "- NÃO ofereça vagas ainda\n"
                "- NÃO peça documentos"
            ),
            reasoning="lifecycle=novo, first_message=True"
        )
    return None


def rule_silence_reactivation(
    state: DoctorState,
    conversa_status: str = "active",
    conversa_last_message_at: Optional[datetime] = None,
    **kwargs
) -> Optional[PolicyDecision]:
    """
    Regra: silêncio > 7d + temperatura quente + Julia falou por último → reativação.

    IMPORTANTE: Exige conversa ativa para evitar falso positivo.
    """
    # Só aplica se conversa está ativa
    if conversa_status != "active":
        return None

    # Precisa ter enviado mensagem
    if not state.last_outbound_at:
        return None

    # Converter se for string
    last_out = state.last_outbound_at
    if isinstance(last_out, str):
        last_out = datetime.fromisoformat(last_out.replace("Z", "+00:00"))

    now = datetime.utcnow()
    days_since_outbound = (now - last_out).days

    # Julia falou por último?
    julia_spoke_last = True
    if state.last_inbound_at:
        last_in = state.last_inbound_at
        if isinstance(last_in, str):
            last_in = datetime.fromisoformat(last_in.replace("Z", "+00:00"))
        julia_spoke_last = last_out > last_in

    # Condições: 7+ dias, temperatura >= 0.3, Julia falou por último
    if (
        days_since_outbound >= 7
        and state.temperature >= 0.3
        and julia_spoke_last
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.REACTIVATION,
            allowed_actions=["gentle_followup", "offer_new_shift", "check_in", "ask_availability"],
            forbidden_actions=["pressure", "urgent_tone", "guilt_trip"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text=(
                f"REATIVAÇÃO: Médico não responde há {days_since_outbound} dias.\n"
                "- Seja gentil e natural\n"
                "- Ofereça algo novo/diferente\n"
                "- NÃO pressione ou cobre resposta"
            ),
            reasoning=f"silence={days_since_outbound}d, temp={state.temperature}, julia_last=True"
        )

    return None


def rule_default(state: DoctorState, **kwargs) -> PolicyDecision:
    """
    Regra default: conservadora.

    IMPORTANTE: Defaults são CONSERVADORES.
    - Offer só se permission_state == ACTIVE e sem bloqueios
    - Caso contrário, apenas followup básico
    """
    # Determinar tom baseado em temperatura
    if state.temperature >= 0.6:
        tone = Tone.LEVE
    elif state.temperature >= 0.3:
        tone = Tone.DIRETO
    else:
        tone = Tone.CAUTELOSO

    # Ações permitidas dependem do estado
    if state.permission_state == PermissionState.ACTIVE and state.is_contactable():
        # Médico ativo e sem bloqueios → pode oferecer
        allowed = ["respond", "offer", "ask", "clarify", "followup"]
        forbidden = ["pressure", "insist"]
        constraints = ""
    else:
        # Conservador: apenas responder, não oferecer proativamente
        allowed = ["respond", "clarify", "ask"]
        forbidden = ["offer", "pressure", "insist", "proactive_contact"]
        constraints = (
            "MODO CONSERVADOR: Médico não está em estado 'active' confirmado.\n"
            "- Responda ao que ele perguntar\n"
            "- NÃO ofereça vagas proativamente"
        )

    return PolicyDecision(
        primary_action=PrimaryAction.FOLLOWUP,
        allowed_actions=allowed,
        forbidden_actions=forbidden,
        tone=tone,
        requires_human=False,
        constraints_text=constraints,
        reasoning=f"default_rule, permission={state.permission_state.value}, temp={state.temperature}"
    )


# Ordem de avaliação (primeira que retorna não-None vence)
# IMPORTANTE: Ordem importa! Mais restritivas primeiro.
RULES_IN_ORDER = [
    rule_opted_out,          # Terminal
    rule_cooling_off,        # Bloqueio temporário
    rule_grave_objection,    # Crise → handoff
    rule_high_objection,     # Atenção extra
    # rule_new_doctor_first_contact precisa de parâmetros extras
    rule_silence_reactivation,
    # rule_default é fallback
]
```

### Arquivo: `app/services/policy/decide.py`

```python
"""
PolicyDecide - Motor de decisão determinística.
"""
import logging
from datetime import datetime
from typing import Optional

from .types import DoctorState, PolicyDecision
from .rules import (
    RULES_IN_ORDER,
    rule_new_doctor_first_contact,
    rule_default,
)

logger = logging.getLogger(__name__)


class PolicyDecide:
    """Motor de decisão determinística."""

    def decide(
        self,
        state: DoctorState,
        is_first_message: bool = False,
        conversa_status: str = "active",
        conversa_last_message_at: Optional[datetime] = None,
    ) -> PolicyDecision:
        """
        Aplica regras em ordem e retorna primeira decisão.

        Args:
            state: Estado atual do médico
            is_first_message: Se é primeira mensagem da conversa
            conversa_status: Status da conversa ('active', 'paused', etc)
            conversa_last_message_at: Timestamp da última mensagem na conversa

        Returns:
            PolicyDecision com ação e constraints
        """
        kwargs = {
            "is_first_message": is_first_message,
            "conversa_status": conversa_status,
            "conversa_last_message_at": conversa_last_message_at,
        }

        # Regra especial: primeiro contato com médico novo
        decision = rule_new_doctor_first_contact(state, **kwargs)
        if decision:
            self._log_decision(state, decision)
            return decision

        # Demais regras em ordem de prioridade
        for rule_fn in RULES_IN_ORDER:
            decision = rule_fn(state, **kwargs)
            if decision:
                self._log_decision(state, decision)
                return decision

        # Fallback: regra default (sempre retorna)
        decision = rule_default(state, **kwargs)
        self._log_decision(state, decision)
        return decision

    def _log_decision(self, state: DoctorState, decision: PolicyDecision):
        """Loga decisão para auditoria."""
        logger.info(
            f"PolicyDecide: {decision.primary_action.value} "
            f"[{state.cliente_id[:8]}] "
            f"reason={decision.reasoning}"
        )

        if decision.requires_human:
            logger.warning(
                f"HANDOFF REQUIRED: {state.cliente_id} - {decision.reasoning}"
            )
```

### DoD (Definition of Done)

- [ ] Todas as regras implementadas
- [ ] Ordem de prioridade correta (mais restritivas primeiro)
- [ ] `rule_opted_out` é terminal
- [ ] `rule_cooling_off` respeita prazo
- [ ] `rule_grave_objection` aciona handoff
- [ ] `rule_silence_reactivation` exige conversa ativa
- [ ] `rule_default` é conservadora
- [ ] Logs de decisão para auditoria
- [ ] Testes unitários para cada regra

---

## E06 - Integração no Agente

### Objetivo
Plugar Policy Engine no fluxo existente do agente.

### Modificações em `app/services/agente.py`

```python
# Adicionar imports
from app.services.policy import PolicyDecide, StateUpdate
from app.services.policy.repository import load_doctor_state, save_doctor_state_updates
from app.services.policy.types import PrimaryAction


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa com Policy Engine.

    Fluxo:
    1. Verificar controle (IA vs humano)
    2. Carregar contexto e doctor_state
    3. Detectar objeção (reaproveitar detector existente)
    4. StateUpdate: atualizar estado
    5. PolicyDecide: decidir ação
    6. Se handoff → transferir
    7. Se wait → não responder
    8. Gerar resposta com constraints
    9. StateUpdate pós-envio
    """
    # 1. Verificar se conversa está sob controle da IA
    if conversa.get("controlled_by") != "ai":
        logger.info("Conversa sob controle humano, não processando")
        return None

    # 2. Carregar contexto (já existe)
    contexto = await montar_contexto_completo(
        medico, conversa, vagas, mensagem_atual=mensagem_texto
    )

    # 2b. Carregar doctor_state
    state = await load_doctor_state(medico["id"])

    # 3. Detectar objeção (REUTILIZAR detector do orquestrador)
    orquestrador = OrquestradorConhecimento()
    objecao_result = orquestrador.detector_objecao.detectar(mensagem_texto)
    objecao_dict = {
        "tem_objecao": objecao_result.tem_objecao,
        "tipo": objecao_result.tipo,
        "subtipo": objecao_result.subtipo,
        "confianca": objecao_result.confianca,
    } if objecao_result.tem_objecao else None

    # 4. StateUpdate: atualizar estado
    state_updater = StateUpdate()
    inbound_updates = state_updater.on_inbound_message(
        state, mensagem_texto, objecao_dict
    )
    await save_doctor_state_updates(medico["id"], inbound_updates)

    # Recarregar state atualizado
    state = await load_doctor_state(medico["id"])

    # 5. PolicyDecide: decidir ação
    policy = PolicyDecide()
    decision = policy.decide(
        state,
        is_first_message=contexto.get("primeira_msg", False),
        conversa_status=conversa.get("status", "active"),
        conversa_last_message_at=conversa.get("last_message_at"),
    )

    # 6. Se requer humano → handoff
    if decision.requires_human:
        await criar_handoff(
            conversa_id=conversa["id"],
            motivo=decision.reasoning,
            trigger_type="policy_grave_objection",
        )
        # Resposta padrão de transferência
        return "Entendi. Vou pedir pra minha supervisora te ajudar aqui, um momento."

    # 7. Se ação é WAIT → não responder
    if decision.primary_action == PrimaryAction.WAIT:
        logger.info(f"PolicyDecide: WAIT - {decision.reasoning}")
        return None

    # 8. Gerar resposta com constraints
    resposta = await gerar_resposta_julia(
        mensagem_texto,
        contexto,
        medico=medico,
        conversa=conversa,
        policy_decision=decision,  # NOVO: passa decisão
    )

    # 9. StateUpdate pós-envio
    outbound_updates = state_updater.on_outbound_message(state, actor="julia")
    await save_doctor_state_updates(medico["id"], outbound_updates)

    return resposta


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: PolicyDecision = None,  # NOVO
) -> str:
    """Gera resposta da Julia (ajustado para receber policy_decision)."""

    # ... código existente do orquestrador ...

    # Montar prompt com constraints da policy
    policy_constraints = ""
    if policy_decision and policy_decision.constraints_text:
        policy_constraints = policy_decision.constraints_text

    system_prompt = await montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False),
        # ... outros parâmetros ...
        policy_constraints=policy_constraints,  # NOVO
    )

    # ... resto do código existente ...
```

### Modificações em `app/core/prompts.py`

```python
async def montar_prompt_julia(
    # ... parâmetros existentes ...
    policy_constraints: str = "",  # NOVO
) -> str:
    """Monta prompt da Julia com constraints da policy."""

    prompt_parts = []

    # PRIORIDADE MÁXIMA: Constraints da Policy
    if policy_constraints:
        prompt_parts.append(f"""## DIRETRIZES DE POLÍTICA (PRIORIDADE MÁXIMA)

{policy_constraints}

---
""")

    # ... resto do prompt existente ...
```

### DoD (Definition of Done)

- [ ] `processar_mensagem_completo` integrado com Policy Engine
- [ ] Detector de objeção reutilizado (não duplicado)
- [ ] StateUpdate roda antes e depois de gerar resposta
- [ ] PolicyDecide determina ação
- [ ] Handoff automático quando `requires_human=True`
- [ ] Não responde quando `primary_action=WAIT`
- [ ] Constraints injetados no prompt
- [ ] Testes de integração passando

---

## E07 - Job de Decay

### Objetivo
Criar job batch para decaimento de temperatura por inatividade.

### Arquivo: `app/workers/temperature_decay.py`

```python
"""
Job de decaimento de temperatura.

Executa 1-2x por dia para:
- Decair temperatura de médicos inativos
- Resetar contact_count_7d semanal
- Limpar cooling_off expirados
"""
import logging
from datetime import datetime, timedelta

from app.services.supabase import supabase
from app.services.policy.state_update import StateUpdate
from app.services.policy.repository import load_doctor_state, save_doctor_state_updates

logger = logging.getLogger(__name__)


async def decay_all_temperatures():
    """
    Job principal: decai temperatura de médicos inativos.

    Usa last_decay_at para ser IDEMPOTENTE.
    Pode rodar múltiplas vezes sem efeito cumulativo errado.
    """
    logger.info("Iniciando job de decay de temperatura...")

    now = datetime.utcnow()

    # Buscar médicos que precisam de decay:
    # - Tem last_inbound_at ou last_decay_at
    # - Último decay foi há mais de 1 dia (ou nunca teve)
    cutoff = (now - timedelta(days=1)).isoformat()

    try:
        response = (
            supabase.table("doctor_state")
            .select("cliente_id, temperature, last_inbound_at, last_decay_at")
            .neq("permission_state", "opted_out")  # Não processar opt-out
            .gt("temperature", 0)  # Só quem tem temperatura > 0
            .or_(
                f"last_decay_at.is.null,last_decay_at.lt.{cutoff}"
            )
            .execute()
        )

        states_to_decay = response.data or []
        logger.info(f"Encontrados {len(states_to_decay)} médicos para decay")

        state_updater = StateUpdate()
        decayed = 0

        for row in states_to_decay:
            state = await load_doctor_state(row["cliente_id"])
            updates = state_updater.decay_temperature(state, now)

            if updates:
                await save_doctor_state_updates(row["cliente_id"], updates)
                decayed += 1

        logger.info(f"Decay aplicado em {decayed} médicos")
        return decayed

    except Exception as e:
        logger.error(f"Erro no job de decay: {e}")
        raise


async def expire_cooling_off():
    """
    Expira cooling_off que passou do prazo.

    Médicos em cooling_off com prazo expirado voltam para 'active'.
    """
    logger.info("Verificando cooling_off expirados...")

    now = datetime.utcnow().isoformat()

    try:
        response = (
            supabase.table("doctor_state")
            .update({
                "permission_state": "active",
                "cooling_off_until": None,
            })
            .eq("permission_state", "cooling_off")
            .lt("cooling_off_until", now)
            .execute()
        )

        expired = len(response.data or [])
        if expired:
            logger.info(f"Expirados {expired} cooling_off")

        return expired

    except Exception as e:
        logger.error(f"Erro ao expirar cooling_off: {e}")
        raise


async def reset_weekly_contact_count():
    """
    Reseta contact_count_7d semanalmente.

    Executar toda segunda-feira.
    """
    logger.info("Resetando contact_count_7d...")

    try:
        response = (
            supabase.table("doctor_state")
            .update({"contact_count_7d": 0})
            .gt("contact_count_7d", 0)
            .execute()
        )

        reset = len(response.data or [])
        logger.info(f"Resetados {reset} contadores semanais")
        return reset

    except Exception as e:
        logger.error(f"Erro ao resetar contadores: {e}")
        raise


async def run_daily_maintenance():
    """Job diário completo."""
    logger.info("=== Iniciando manutenção diária de doctor_state ===")

    decayed = await decay_all_temperatures()
    expired = await expire_cooling_off()

    logger.info(f"=== Manutenção concluída: {decayed} decay, {expired} cooling_off expirados ===")

    return {"decayed": decayed, "expired": expired}
```

### Registrar no Scheduler

```python
# Em app/workers/scheduler.py

from app.workers.temperature_decay import run_daily_maintenance, reset_weekly_contact_count

# Adicionar jobs:
# - run_daily_maintenance: todo dia às 03:00
# - reset_weekly_contact_count: toda segunda às 00:00
```

### DoD (Definition of Done)

- [ ] `decay_all_temperatures` usa `last_decay_at` (idempotente)
- [ ] `expire_cooling_off` expira prazos vencidos
- [ ] `reset_weekly_contact_count` reseta contadores
- [ ] Jobs registrados no scheduler
- [ ] Logs adequados para monitoramento
- [ ] Testes de idempotência

---

## E08 - Testes e Validação

### Objetivo
Garantir qualidade e cobertura de testes.

### Estrutura de Testes

```
tests/
├── services/
│   ├── policy/
│   │   ├── test_types.py
│   │   ├── test_rules.py
│   │   ├── test_decide.py
│   │   ├── test_state_update.py
│   │   └── test_repository.py
│   └── classificacao/
│       └── test_severity_mapper.py
└── workers/
    └── test_temperature_decay.py
```

### Casos de Teste Críticos

#### test_rules.py

```python
def test_opted_out_blocks_all():
    """Opt-out bloqueia tudo."""
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.OPTED_OUT,
    )
    decision = rule_opted_out(state)
    assert decision is not None
    assert decision.primary_action == PrimaryAction.WAIT
    assert decision.forbidden_actions == ["*"]


def test_grave_objection_requires_human():
    """Objeção grave aciona handoff."""
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.ACTIVE,
        active_objection="ameaca",
        objection_severity=ObjectionSeverity.GRAVE,
    )
    decision = rule_grave_objection(state)
    assert decision is not None
    assert decision.requires_human is True
    assert decision.primary_action == PrimaryAction.HANDOFF


def test_default_is_conservative():
    """Default não permite offer se não está active."""
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.INITIAL,
    )
    decision = rule_default(state)
    assert "offer" in decision.forbidden_actions
```

#### test_state_update.py

```python
def test_opt_out_is_terminal():
    """Opt-out seta opted_out, não cooling_off."""
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.ACTIVE,
    )
    updater = StateUpdate()
    updates = updater.on_inbound_message(
        state,
        "não me procure mais",
        {"tem_objecao": True, "tipo": "opt_out"},
    )
    assert updates["permission_state"] == "opted_out"


def test_objection_not_cleared_automatically():
    """Objeção não é limpa sem resolução explícita."""
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.ACTIVE,
        active_objection="valor",
        objection_severity=ObjectionSeverity.MEDIUM,
    )
    updater = StateUpdate()
    updates = updater.on_inbound_message(
        state,
        "ok, entendi",
        None,  # Sem nova objeção
    )
    # NÃO deve ter limpado a objeção
    assert "active_objection" not in updates
    assert "objection_severity" not in updates


def test_decay_is_idempotent():
    """Decay usa last_decay_at para ser idempotente."""
    now = datetime.utcnow()
    state = DoctorState(
        cliente_id="123",
        permission_state=PermissionState.ACTIVE,
        temperature=0.5,
        last_inbound_at=now - timedelta(days=10),
        last_decay_at=now - timedelta(hours=1),  # Decay recente
    )
    updater = StateUpdate()
    updates = updater.decay_temperature(state, now)
    # Não deve decair porque last_decay_at é recente
    assert updates == {}
```

### DoD (Definition of Done)

- [ ] Cobertura > 80% no módulo policy
- [ ] Testes para cada regra de produção
- [ ] Testes de borda (opt-out, cooling_off expirado, etc)
- [ ] Testes de idempotência do decay
- [ ] Testes de integração end-to-end
- [ ] CI passando

---

## Checklist Final da Sprint

### Pré-requisitos
- [ ] Sprint 14 concluída (se houver dependências)
- [ ] Ambiente de desenvolvimento configurado
- [ ] Acesso ao Supabase confirmado

### Entregas
- [ ] E01 - Tabela doctor_state migrada e populada
- [ ] E02 - Módulo policy criado com types
- [ ] E03 - Severity mapper implementado
- [ ] E04 - StateUpdate funcionando
- [ ] E05 - PolicyDecide com regras
- [ ] E06 - Integração no agente
- [ ] E07 - Job de decay configurado
- [ ] E08 - Testes passando

### Validação
- [ ] Opt-out funciona (terminal)
- [ ] Objeção grave aciona handoff
- [ ] Objeção não é limpa automaticamente
- [ ] Decay é idempotente
- [ ] Constraints aparecem no prompt
- [ ] Logs de decisão para auditoria

### Documentação
- [ ] CLAUDE.md atualizado com Sprint 15
- [ ] Comentários no código
- [ ] README do módulo policy

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar fluxo existente | Média | Alto | Shadow writes durante transição |
| Regras muito restritivas | Baixa | Médio | Começar conservador, afrouxar gradualmente |
| Import circular | Baixa | Médio | Severity mapper em módulo neutro |
| Performance do decay | Baixa | Baixo | Índices e batch com limite |
| Backfill incorreto | Média | Médio | Validação pós-migração |

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Cobertura de testes policy | > 80% |
| Tempo de decisão PolicyDecide | < 10ms |
| Handoffs automáticos funcionando | 100% |
| Opt-outs respeitados | 100% |
| Logs de decisão completos | 100% |
