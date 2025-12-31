# Sprint 25: Warmer + Salvy + Trust Score Foundation

**Status:** Planejado
**Inicio:** A definir
**Estimativa:** 3 semanas
**Dependencias:** Nenhuma

---

## Objetivo

Construir o **sistema de aquecimento de chips WhatsApp** com:
- Integração Salvy para provisioning automatico
- Trust Score multiparametrico (não triggers binarios)
- RAG de politicas Meta constantemente atualizado
- Foundation para multi-chip em producao

### Contexto de Negocio

| Metrica | Valor |
|---------|-------|
| Contas banidas sem warm-up | 87% em 72h |
| Tempo minimo de aquecimento | 21 dias |
| Meta Trust Score para producao | ≥ 85 |
| Escala planejada | 50-100+ chips |

### Mudanca de Paradigma

| Antes (triggers) | Agora (Trust Score) |
|------------------|---------------------|
| Ban = pausa | Score continuo 0-100 |
| Regras fixas | Permissoes dinamicas |
| Reativo | Proativo e preditivo |
| 1 chip por vez | N chips com capacidade distribuida |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SPRINT 25 SCOPE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     TRUST SCORER                             │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐               │   │
│  │  │  Fatores  │  │  Calculo  │  │ Permissoes│               │   │
│  │  │  Coleta   │──│  Score    │──│ Dinamicas │               │   │
│  │  └───────────┘  └───────────┘  └───────────┘               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                             │                                       │
│         ┌───────────────────┼───────────────────┐                  │
│         │                   │                   │                  │
│         ▼                   ▼                   ▼                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │   SALVY     │    │   WARMER    │    │  META RAG   │            │
│  │ INTEGRATION │    │   ENGINE    │    │  POLICIES   │            │
│  │             │    │             │    │             │            │
│  │ Provisionar │    │ Aquecimento │    │ Embeddings  │            │
│  │ Cancelar    │    │ 21 dias     │    │ Atualizado  │            │
│  │ Webhook SMS │    │ Conversas   │    │ Consultas   │            │
│  └─────────────┘    └─────────────┘    └─────────────┘            │
│         │                   │                   │                  │
│         └───────────────────┼───────────────────┘                  │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EVOLUTION API POOL                        │   │
│  │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐          │   │
│  │   │ 001 │ │ 002 │ │ 003 │ │ ... │ │ 049 │ │ 050 │          │   │
│  │   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Politicas Meta - Resumo para RAG

### Limites de Mensagens (Outubro 2025+)

| Tier | Limite/dia | Como subir |
|------|------------|------------|
| Tier 1 | 1.000 destinatarios | Inicial |
| Tier 2 | 10.000 destinatarios | Qualidade media+ e usar 50% do limite |
| Tier 3 | 100.000 destinatarios | Qualidade alta e usar 50% do limite |
| Unlimited | Sem limite | Empresas verificadas |

**IMPORTANTE (Out/2025):** Limite e compartilhado por PORTFOLIO, nao por numero.

### Quality Rating

| Cor | Nivel | Impacto |
|-----|-------|---------|
| 🟢 Verde | Alta | Pode subir de tier |
| 🟡 Amarelo | Media | Mantem tier atual |
| 🔴 Vermelho | Baixa | Nao sobe de tier (nao desce mais desde Out/2025) |

### Motivos de Ban (Evitar!)

1. **Spam** - Mensagens em massa nao solicitadas
2. **Automacao nao autorizada** - Bots sem API oficial
3. **Feedback negativo** - Usuarios bloqueando/denunciando
4. **Conteudo proibido** - Ver lista completa
5. **Terceiros nao autorizados** - GB WhatsApp, mods
6. **Mensagens sem consentimento** - Opt-in obrigatorio

### Boas Praticas

- Consentimento explicito antes de enviar
- Botao de unsubscribe em templates
- Mensagens personalizadas e uteis
- Frequencia moderada (nao bombardear)
- Responder dentro de 24h
- Encaminhamento rapido para humano

**Fontes:**
- [WhatsApp Business Policy](https://business.whatsapp.com/policy)
- [Quality Rating - 360Dialog](https://docs.360dialog.com/docs/waba-management/capacity-quality-rating-and-messaging-limits)
- [Messaging Limits - Turn.io](https://learn.turn.io/l/en/article/uvdz8tz40l-quality-ratings-and-messaging-limits)

---

## Stack Tecnico

| Componente | Tecnologia | Motivo |
|------------|------------|--------|
| Backend | FastAPI | Ja existe na Julia |
| Jobs Async | ARQ + Redis | Leve, nativo async |
| Cache | Redis | Trust scores, estados |
| Scheduler | APScheduler | Ja integrado |
| Evolution | 1 instancia/chip | Isolamento |
| Salvy | API REST | Provisioning numeros |
| RAG | pgvector + Voyage | Politicas Meta |
| Alertas | Slack | Notificacoes |

---

## Epicos

| # | Epico | Descricao | Tempo |
|---|-------|-----------|-------|
| E01 | Modelo Dados Unificado | chips, transitions, meta_policies, affinity, cooldown | 5h |
| E02 | Salvy Integration | Client API, provisionar, cancelar, webhook | 4h |
| E03 | Meta Policies RAG | Embeddings, atualizacao, consulta | 4h |
| E04 | Trust Score Engine | Fatores, calculo, permissoes, quilometragem segura | 6h |
| E05 | Human Simulator | Delays, digitando, mark as read | 4h |
| E06 | Conversation Generator | Claude + typos + trending | 4h |
| E07 | Pairing Engine | Pareamento rotativo | 3h |
| E08 | Warming Scheduler | Janela anti-padrao, Dia 0 repouso, limites por fase | 5h |
| E09 | Warming Orchestrator | Ciclo de fases, progressao, teste graduacao | 6h |
| E10 | Early Warning | Deteccao proativa, pausa gradual | 4h |
| E11 | Warmer API | Endpoints de gestao | 3h |
| E12 | Group Entry Engine | Entrada segura em grupos (CSV/Excel, limites, multi-chip) | 8h* |

**Total Estimado:** ~55h

> *E12: 8h (S12.1-S12.5 Sprint 25) + 3h (S12.6 Discovery na Sprint 26)

---

## Ordenação de Execução

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDÊNCIAS ENTRE ÉPICOS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   E01 (Modelo Dados) ─────────────────────────────────────────┐ │
│         │                                                      │ │
│         ├──► E02 (Salvy)                                       │ │
│         ├──► E03 (Meta RAG)                                    │ │
│         ├──► E04 (Trust Score)                                 │ │
│         │         │                                            │ │
│         │         └──► E08 (Warming Scheduler) ◄───────────┐   │ │
│         │                      │                           │   │ │
│         │                      └──► E12 (Group Entry) ─────┘   │ │
│         │                                                      │ │
│         ├──► E05 (Human Simulator) ──► E06 (Conversation Gen)  │ │
│         │                                      │               │ │
│         │                                      ▼               │ │
│         ├──► E07 (Pairing Engine) ◄────────────┘               │ │
│         │                                                      │ │
│         ├──► E09 (Warming Orchestrator)                        │ │
│         ├──► E10 (Early Warning)                               │ │
│         └──► E11 (Warmer API)                                  │ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Ordem sugerida de execução:**

1. **E01** - Modelo de Dados (base para todos)
2. **E02, E03, E04** - Foundation (podem rodar em paralelo)
3. **E05, E06, E07** - Warming core (sequencial)
4. **E08** - Warming Scheduler (define fases e limites)
5. **E12** - Group Entry Engine (depende de E08 para limites por fase)
6. **E09, E10, E11** - Orquestração e API (podem rodar em paralelo)

> **Nota:** E12 consome limites por fase definidos em E08 e Trust Score de E04.

---

## E01: Modelo de Dados Unificado

### Objetivo
Criar schema que unifica Salvy + Evolution + Warming + Trust Score + RAG.

### Migration Principal

```sql
-- =====================================================
-- TABELA CENTRAL: chips
-- Unifica todo ciclo de vida do chip
-- =====================================================
CREATE TABLE chips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefone TEXT UNIQUE NOT NULL,

    -- ══════════════════════════════════════════
    -- SALVY
    -- ══════════════════════════════════════════
    salvy_id TEXT UNIQUE,
    salvy_status TEXT CHECK (salvy_status IN ('active', 'blocked', 'canceled')),
    salvy_created_at TIMESTAMPTZ,

    -- ══════════════════════════════════════════
    -- EVOLUTION
    -- ══════════════════════════════════════════
    instance_name TEXT UNIQUE NOT NULL,
    evolution_connected BOOLEAN DEFAULT false,
    evolution_qr_code TEXT,

    -- ══════════════════════════════════════════
    -- ESTADO NO SISTEMA
    -- ══════════════════════════════════════════
    status TEXT NOT NULL DEFAULT 'provisioned'
        CHECK (status IN (
            'provisioned',  -- Comprado na Salvy, aguardando setup
            'pending',      -- Aguardando conexao Evolution
            'warming',      -- Em aquecimento (21 dias)
            'ready',        -- Pronto, aguardando slot producao
            'active',       -- Em producao na Julia
            'degraded',     -- Trust baixo, modo restrito
            'paused',       -- Pausado manualmente
            'banned',       -- Banido pelo WhatsApp
            'cancelled'     -- Cancelado na Salvy
        )),

    -- ══════════════════════════════════════════
    -- WARMING
    -- ══════════════════════════════════════════
    fase_warmup TEXT DEFAULT 'repouso'
        CHECK (fase_warmup IN (
            'repouso',            -- Dia 0: 24-48h sem atividade (simula chip novo)
            'setup',              -- Dias 1-3: apenas config
            'primeiros_contatos', -- Dias 4-7: max 10 msgs/dia
            'expansao',           -- Dias 8-14: max 30 msgs/dia
            'pre_operacao',       -- Dias 15-21: max 50 msgs/dia
            'teste_graduacao',    -- Dia 22: teste formal antes de ready
            'operacao'            -- Dia 22+: pronto
        )),
    fase_iniciada_em TIMESTAMPTZ DEFAULT now(),
    warming_started_at TIMESTAMPTZ,
    warming_day INT DEFAULT 0,

    -- ══════════════════════════════════════════
    -- TRUST SCORE (multiparametrico)
    -- ══════════════════════════════════════════
    trust_score INT DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    trust_level TEXT DEFAULT 'amarelo'
        CHECK (trust_level IN ('verde', 'amarelo', 'laranja', 'vermelho', 'critico')),
    ultimo_calculo_trust TIMESTAMPTZ,

    -- Fatores do Trust Score (cache)
    trust_factors JSONB DEFAULT '{}',

    -- ══════════════════════════════════════════
    -- METRICAS
    -- ══════════════════════════════════════════
    msgs_enviadas_total INT DEFAULT 0,
    msgs_recebidas_total INT DEFAULT 0,
    msgs_enviadas_hoje INT DEFAULT 0,
    msgs_recebidas_hoje INT DEFAULT 0,

    taxa_resposta DECIMAL(5,4) DEFAULT 0,      -- 0.0000 a 1.0000
    taxa_delivery DECIMAL(5,4) DEFAULT 1,
    taxa_block DECIMAL(5,4) DEFAULT 0,

    conversas_bidirecionais INT DEFAULT 0,
    grupos_count INT DEFAULT 0,
    tipos_midia_usados TEXT[] DEFAULT '{}',

    erros_ultimas_24h INT DEFAULT 0,
    dias_sem_erro INT DEFAULT 0,

    -- ══════════════════════════════════════════
    -- PERMISSOES (calculadas do Trust Score)
    -- ══════════════════════════════════════════
    pode_prospectar BOOLEAN DEFAULT false,
    pode_followup BOOLEAN DEFAULT false,
    pode_responder BOOLEAN DEFAULT true,
    limite_hora INT DEFAULT 5,
    limite_dia INT DEFAULT 30,
    delay_minimo_segundos INT DEFAULT 120,

    -- ══════════════════════════════════════════
    -- COOLDOWN (simula pausas humanas)
    -- ══════════════════════════════════════════
    last_activity_start TIMESTAMPTZ,     -- Inicio do periodo de atividade
    cooldown_until TIMESTAMPTZ,          -- Ate quando esta em cooldown
    -- em_cooldown = (cooldown_until > now()) - computed

    -- ══════════════════════════════════════════
    -- PRODUCAO
    -- ══════════════════════════════════════════
    promoted_to_active_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    dias_em_producao INT DEFAULT 0,      -- "Quilometragem segura"

    -- ══════════════════════════════════════════
    -- AUDITORIA
    -- ══════════════════════════════════════════
    banned_at TIMESTAMPTZ,
    ban_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices para queries frequentes
CREATE INDEX idx_chips_status ON chips(status);
CREATE INDEX idx_chips_trust ON chips(trust_score DESC) WHERE status IN ('warming', 'ready', 'active');
CREATE INDEX idx_chips_ready ON chips(trust_score DESC, warming_started_at ASC) WHERE status = 'ready';


-- =====================================================
-- TRANSICOES DE ESTADO (auditoria)
-- =====================================================
CREATE TABLE chip_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    from_status TEXT,
    to_status TEXT NOT NULL,
    from_trust_score INT,
    to_trust_score INT,

    reason TEXT,
    triggered_by TEXT NOT NULL, -- 'system', 'api', 'orchestrator', 'early_warning'
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chip_transitions_chip ON chip_transitions(chip_id, created_at DESC);


-- =====================================================
-- HISTORICO DE TRUST SCORE
-- =====================================================
CREATE TABLE chip_trust_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    score INT NOT NULL,
    level TEXT NOT NULL,
    factors JSONB NOT NULL,
    permissoes JSONB NOT NULL,

    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chip_trust_history ON chip_trust_history(chip_id, recorded_at DESC);


-- =====================================================
-- ALERTAS DE CHIP
-- =====================================================
CREATE TABLE chip_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    tipo TEXT NOT NULL,
    message TEXT NOT NULL,

    acao_tomada TEXT,  -- 'paused', 'reduced_speed', 'none'

    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chip_alerts_unresolved ON chip_alerts(chip_id, severity) WHERE resolved = false;


-- =====================================================
-- PAREAMENTOS PARA WARM-UP
-- =====================================================
CREATE TABLE chip_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_a_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    chip_b_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    active BOOLEAN DEFAULT true,
    messages_exchanged INT DEFAULT 0,
    conversations_count INT DEFAULT 0,
    last_interaction TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_pair UNIQUE (chip_a_id, chip_b_id),
    CONSTRAINT different_chips CHECK (chip_a_id != chip_b_id)
);

CREATE INDEX idx_chip_pairs_active ON chip_pairs(active) WHERE active = true;


-- =====================================================
-- AFFINITY MEDICO-CHIP
-- Medico prefere continuar no mesmo chip
-- =====================================================
CREATE TABLE medico_chip_affinity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medico_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    msgs_trocadas INT DEFAULT 1,
    ultima_interacao TIMESTAMPTZ DEFAULT now(),

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(medico_id, chip_id)
);

CREATE INDEX idx_affinity_medico ON medico_chip_affinity(medico_id, ultima_interacao DESC);
CREATE INDEX idx_affinity_chip ON medico_chip_affinity(chip_id) WHERE msgs_trocadas > 0;


-- =====================================================
-- CONVERSAS DE WARM-UP
-- =====================================================
CREATE TABLE warmup_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id UUID NOT NULL REFERENCES chip_pairs(id) ON DELETE CASCADE,

    tema TEXT NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]',
    turnos INT DEFAULT 0,

    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_warmup_conversations_pair ON warmup_conversations(pair_id, started_at DESC);


-- =====================================================
-- INTERACOES GRANULARES
-- =====================================================
CREATE TABLE chip_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    tipo TEXT NOT NULL CHECK (tipo IN (
        'msg_enviada', 'msg_recebida', 'chamada',
        'status_criado', 'grupo_entrada', 'grupo_saida', 'midia_enviada'
    )),

    destinatario TEXT,
    midia_tipo TEXT CHECK (midia_tipo IN ('text', 'audio', 'image', 'video', 'document', 'sticker')),

    obteve_resposta BOOLEAN,
    tempo_resposta_segundos INT,

    erro_codigo TEXT,
    erro_mensagem TEXT,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chip_interactions_chip_time ON chip_interactions(chip_id, created_at DESC);
CREATE INDEX idx_chip_interactions_erros ON chip_interactions(chip_id, erro_codigo) WHERE erro_codigo IS NOT NULL;


-- =====================================================
-- RAG: POLITICAS META
-- =====================================================
CREATE TABLE meta_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    categoria TEXT NOT NULL,  -- 'limites', 'proibicoes', 'boas_praticas', 'motivos_ban', 'quality_rating'
    titulo TEXT NOT NULL,

    -- Conteudo
    conteudo TEXT NOT NULL,
    fonte_url TEXT,
    fonte_nome TEXT,

    -- Embedding para RAG
    embedding vector(1024),  -- Voyage AI

    -- Versionamento
    versao INT DEFAULT 1,
    valido_desde DATE DEFAULT CURRENT_DATE,
    valido_ate DATE,

    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_meta_policies_categoria ON meta_policies(categoria);
CREATE INDEX idx_meta_policies_embedding ON meta_policies USING ivfflat (embedding vector_cosine_ops);


-- =====================================================
-- CONFIGURACAO DO POOL
-- =====================================================
CREATE TABLE pool_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Producao
    producao_min INT DEFAULT 5,
    producao_max INT DEFAULT 10,

    -- Warming buffer
    warmup_buffer INT DEFAULT 10,
    warmup_days INT DEFAULT 21,

    -- Ready (reserva quente)
    ready_min INT DEFAULT 3,

    -- Trust thresholds
    trust_min_for_ready INT DEFAULT 85,
    trust_degraded_threshold INT DEFAULT 60,
    trust_critical_threshold INT DEFAULT 20,

    -- Auto-provisioning
    auto_provision BOOLEAN DEFAULT true,
    default_ddd INT DEFAULT 11,

    -- Limites por tipo de msg
    limite_prospeccao_hora INT DEFAULT 10,
    limite_followup_hora INT DEFAULT 20,
    limite_resposta_hora INT DEFAULT 50,

    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT
);

-- Inserir config padrao
INSERT INTO pool_config DEFAULT VALUES;


-- =====================================================
-- TRIGGER: updated_at automatico
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_chips_updated_at
    BEFORE UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_pool_config_updated_at
    BEFORE UPDATE ON pool_config FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_meta_policies_updated_at
    BEFORE UPDATE ON meta_policies FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- FUNCAO: Registrar transicao de estado
-- =====================================================
CREATE OR REPLACE FUNCTION registrar_transicao()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status OR OLD.trust_score IS DISTINCT FROM NEW.trust_score THEN
        INSERT INTO chip_transitions (
            chip_id, from_status, to_status,
            from_trust_score, to_trust_score,
            triggered_by
        ) VALUES (
            NEW.id, OLD.status, NEW.status,
            OLD.trust_score, NEW.trust_score,
            COALESCE(current_setting('app.triggered_by', true), 'system')
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_chip_transition
    AFTER UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION registrar_transicao();
```

### DoD

- [ ] Todas as tabelas criadas
- [ ] Indices otimizados
- [ ] Triggers funcionando
- [ ] Transicoes sendo registradas
- [ ] pgvector habilitado para RAG

---

## E02: Salvy Integration

### Objetivo
Integrar com API Salvy para provisioning automatico de numeros.

### Endpoints Salvy

| Metodo | Endpoint | Funcao |
|--------|----------|--------|
| POST | `/api/v2/virtual-phone-accounts` | Criar numero |
| GET | `/api/v2/virtual-phone-accounts/{id}` | Buscar numero |
| GET | `/api/v2/virtual-phone-accounts` | Listar numeros |
| DELETE | `/api/v2/virtual-phone-accounts/{id}` | Cancelar numero |
| GET | `/api/v2/virtual-phone-accounts/area-codes` | DDDs disponiveis |

### Implementacao

**Arquivo:** `app/services/salvy/client.py`

```python
"""
Salvy API Client - Provisioning de numeros virtuais.

Docs: https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction
"""
import httpx
import logging
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.salvy.com.br/api/v2"


class SalvyNumber(BaseModel):
    """Numero virtual Salvy."""
    id: str
    name: Optional[str]
    phone_number: str
    status: str  # active, blocked, canceled
    created_at: datetime
    canceled_at: Optional[datetime]


class SalvyClient:
    """Cliente para API Salvy."""

    def __init__(self):
        self.token = settings.SALVY_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def criar_numero(
        self,
        ddd: int = 11,
        nome: Optional[str] = None
    ) -> SalvyNumber:
        """
        Cria novo numero virtual.

        Args:
            ddd: Codigo de area (11, 21, etc)
            nome: Label para identificacao

        Returns:
            SalvyNumber criado
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/virtual-phone-accounts",
                headers=self.headers,
                json={
                    "areaCode": ddd,
                    "name": nome or f"julia-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"[Salvy] Numero criado: {data['phoneNumber']}")

            return SalvyNumber(
                id=data["id"],
                name=data.get("name"),
                phone_number=data["phoneNumber"],
                status=data["status"],
                created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
                canceled_at=None,
            )

    async def cancelar_numero(self, salvy_id: str) -> bool:
        """
        Cancela numero virtual (para de pagar).

        Args:
            salvy_id: ID do numero na Salvy

        Returns:
            True se cancelado com sucesso
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 204:
                logger.info(f"[Salvy] Numero cancelado: {salvy_id}")
                return True

            logger.error(f"[Salvy] Erro ao cancelar: {response.text}")
            return False

    async def buscar_numero(self, salvy_id: str) -> Optional[SalvyNumber]:
        """Busca numero por ID."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts/{salvy_id}",
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()

            return SalvyNumber(
                id=data["id"],
                name=data.get("name"),
                phone_number=data["phoneNumber"],
                status=data["status"],
                created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
                canceled_at=datetime.fromisoformat(data["canceledAt"].replace("Z", "+00:00")) if data.get("canceledAt") else None,
            )

    async def listar_numeros(self) -> List[SalvyNumber]:
        """Lista todos os numeros."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()

            return [
                SalvyNumber(
                    id=d["id"],
                    name=d.get("name"),
                    phone_number=d["phoneNumber"],
                    status=d["status"],
                    created_at=datetime.fromisoformat(d["createdAt"].replace("Z", "+00:00")),
                    canceled_at=datetime.fromisoformat(d["canceledAt"].replace("Z", "+00:00")) if d.get("canceledAt") else None,
                )
                for d in response.json()
            ]

    async def listar_ddds_disponiveis(self) -> List[int]:
        """Lista DDDs com numeros disponiveis."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/virtual-phone-accounts/area-codes",
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()


# Singleton
salvy_client = SalvyClient()
```

**Arquivo:** `app/services/salvy/webhooks.py`

```python
"""
Webhook para receber SMS da Salvy.

Usado para receber codigo de verificacao do WhatsApp.
"""
from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/salvy", tags=["salvy"])


@router.post("/sms")
async def webhook_sms(request: Request):
    """
    Recebe SMS via Salvy webhook.

    Usado para:
    - Codigo de verificacao WhatsApp
    - Alertas de operadora
    """
    payload = await request.json()

    logger.info(f"[Salvy Webhook] SMS recebido: {payload}")

    telefone = payload.get("phoneNumber")
    mensagem = payload.get("message")
    remetente = payload.get("from")

    # Se for codigo WhatsApp, processar
    if "whatsapp" in mensagem.lower() or remetente == "WhatsApp":
        await processar_codigo_whatsapp(telefone, mensagem)

    return {"status": "ok"}


async def processar_codigo_whatsapp(telefone: str, mensagem: str):
    """
    Extrai codigo de verificacao e atualiza chip.
    """
    import re

    # Extrair codigo (geralmente 6 digitos)
    match = re.search(r'\b(\d{6})\b', mensagem)
    if match:
        codigo = match.group(1)
        logger.info(f"[Salvy] Codigo WhatsApp extraido: {codigo} para {telefone}")

        # TODO: Usar codigo para verificar no Evolution
        # await evolution_client.verify_code(instance, codigo)
```

### DoD

- [ ] Client Salvy funcionando
- [ ] Criar numero
- [ ] Cancelar numero
- [ ] Listar numeros
- [ ] Webhook SMS configurado
- [ ] Testes de integracao

---

## E03: Meta Policies RAG

### Objetivo
Manter base de conhecimento das politicas Meta atualizada para consulta durante decisoes.

### Implementacao

**Arquivo:** `app/services/meta_rag/policies.py`

```python
"""
RAG de Politicas Meta.

Armazena e consulta politicas do WhatsApp Business
para informar decisoes do Trust Score.
"""
import logging
from typing import List, Optional
from datetime import date

from app.services.supabase import supabase
from app.services.embeddings import gerar_embedding

logger = logging.getLogger(__name__)


# Politicas iniciais para seed
POLITICAS_SEED = [
    # Limites
    {
        "categoria": "limites",
        "titulo": "Tiers de Limite de Mensagens",
        "conteudo": """
        Limites de mensagens por dia (desde Outubro 2025):
        - Tier 1: 1.000 destinatarios/dia (inicial)
        - Tier 2: 10.000 destinatarios/dia
        - Tier 3: 100.000 destinatarios/dia
        - Unlimited: Sem limite (empresas verificadas)

        IMPORTANTE: Desde Outubro 2025, o limite e compartilhado por todo o Portfolio
        (todos os numeros da empresa), nao mais por numero individual.

        Para subir de tier:
        - Quality rating media ou alta
        - Usar pelo menos 50% do limite atual por 7 dias
        - Enviar mensagens de alta qualidade
        """,
        "fonte_url": "https://docs.360dialog.com/docs/waba-management/capacity-quality-rating-and-messaging-limits",
        "fonte_nome": "360Dialog Docs",
    },
    {
        "categoria": "limites",
        "titulo": "Mensagens Iniciadas vs Respostas",
        "conteudo": """
        Os limites se aplicam apenas a mensagens INICIADAS pelo negocio (outbound).

        Respostas a mensagens de clientes (inbound) NAO contam para o limite.
        Desde 2024, conversas iniciadas pelo usuario sao gratuitas.

        Implicacao: Priorizar respostas sobre prospeccao quando proximo do limite.
        """,
        "fonte_url": "https://learn.turn.io/l/en/article/uvdz8tz40l-quality-ratings-and-messaging-limits",
        "fonte_nome": "Turn.io Learn",
    },

    # Quality Rating
    {
        "categoria": "quality_rating",
        "titulo": "Sistema de Quality Rating",
        "conteudo": """
        Quality Rating determina se voce pode subir de tier:

        - Verde (Alta): Pode subir de tier
        - Amarelo (Media): Mantem tier atual
        - Vermelho (Baixa): Nao sobe de tier

        MUDANCA OUTUBRO 2025: Qualidade baixa NAO causa mais downgrade de tier.
        Apenas impede subir para o proximo tier.

        Fatores que afetam qualidade:
        - Bloqueios por usuarios
        - Denuncias de spam
        - Taxa de leitura
        - Feedback negativo nos ultimos 7 dias (peso maior para recentes)
        """,
        "fonte_url": "https://docs.360dialog.com/partner/messaging-and-calling/messaging-health-and-troubleshooting/messaging-limits-and-quality-rating",
        "fonte_nome": "360Dialog Partner Docs",
    },

    # Motivos de Ban
    {
        "categoria": "motivos_ban",
        "titulo": "Principais Motivos de Ban",
        "conteudo": """
        Motivos que levam a ban/restricao:

        1. SPAM: Mensagens em massa nao solicitadas
        2. AUTOMACAO NAO AUTORIZADA: Bots sem API oficial, mods (GB WhatsApp)
        3. FEEDBACK NEGATIVO: Muitos usuarios bloqueando/denunciando
        4. CONTEUDO PROIBIDO: Armas, drogas, adulto, jogos de azar
        5. TERCEIROS NAO AUTORIZADOS: Apps modificados
        6. SEM CONSENTIMENTO: Enviar sem opt-in explicito
        7. VOLUME SUSPEITO: Muitas mensagens em curto periodo

        Estatistica: 6.8 milhoes de contas banidas no 1o semestre de 2025.
        """,
        "fonte_url": "https://support.wati.io/en/articles/11463217",
        "fonte_nome": "Wati.io Help Center",
    },
    {
        "categoria": "motivos_ban",
        "titulo": "Sinais de Automacao Detectados",
        "conteudo": """
        WhatsApp usa machine learning para detectar automacao:

        - Mensagens muito rapidas (sem delay humano)
        - Padroes repetitivos de texto
        - Horarios nao humanos (3h da manha)
        - Ausencia de indicador 'digitando'
        - Proporcao muito alta de enviadas vs recebidas
        - Muitos contatos novos em pouco tempo

        Solucao: Simular comportamento humano (delays, digitando, variedade).
        """,
        "fonte_url": "https://whautomate.com/top-reasons-why-whatsapp-accounts-get-banned-in-2025-and-how-to-avoid-them/",
        "fonte_nome": "WhAutomate Blog",
    },

    # Boas Praticas
    {
        "categoria": "boas_praticas",
        "titulo": "Boas Praticas de Messaging",
        "conteudo": """
        Recomendacoes oficiais da Meta:

        1. CONSENTIMENTO: Obter opt-in explicito antes de enviar
        2. UNSUBSCRIBE: Incluir opcao de descadastro em templates
        3. PERSONALIZACAO: Mensagens relevantes e personalizadas
        4. FREQUENCIA: Nao bombardear (max 1-2 msgs/dia por contato)
        5. HORARIO: Enviar em horario comercial (8h-20h)
        6. RESPOSTA RAPIDA: Responder dentro de 24h
        7. HUMANO DISPONIVEL: Oferecer encaminhamento para atendente
        8. PERFIL COMPLETO: Manter dados de contato atualizados
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
    {
        "categoria": "boas_praticas",
        "titulo": "Broadcast vs Conversa Individual",
        "conteudo": """
        Limite de broadcast: 256 contatos por lista.

        Para escalar com seguranca:
        - Preferir conversas individuais sobre broadcast
        - Segmentar listas por interesse/engajamento
        - Variar conteudo entre mensagens
        - Monitorar taxa de bloqueio por campanha

        Se taxa de bloqueio > 2-3%, pausar e revisar estrategia.
        """,
        "fonte_url": "https://gallabox.com/blog/whatsapp-business-account-blocked",
        "fonte_nome": "Gallabox Blog",
    },

    # Proibicoes
    {
        "categoria": "proibicoes",
        "titulo": "Conteudo Absolutamente Proibido",
        "conteudo": """
        NAO enviar mensagens sobre:

        - Armas de fogo e municao
        - Drogas e substancias controladas
        - Produtos medicos restritos
        - Animais vivos (exceto gado)
        - Especies ameacadas
        - Jogos de azar com dinheiro real
        - Conteudo adulto/sexual
        - Servicos de encontros
        - Marketing multinivel
        - Credito consignado/adiantamento salario
        - Conteudo discriminatorio
        - Informacoes falsas/enganosas

        Violacao = ban permanente.
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
]


async def seed_politicas():
    """Popula banco com politicas iniciais."""
    for politica in POLITICAS_SEED:
        # Gerar embedding
        embedding = await gerar_embedding(politica["conteudo"])

        # Inserir no banco
        supabase.table("meta_policies").upsert({
            "categoria": politica["categoria"],
            "titulo": politica["titulo"],
            "conteudo": politica["conteudo"],
            "fonte_url": politica.get("fonte_url"),
            "fonte_nome": politica.get("fonte_nome"),
            "embedding": embedding,
        }, on_conflict="titulo").execute()

    logger.info(f"[MetaRAG] {len(POLITICAS_SEED)} politicas inseridas/atualizadas")


async def consultar_politicas(
    pergunta: str,
    categoria: Optional[str] = None,
    limite: int = 5,
) -> List[dict]:
    """
    Consulta politicas relevantes via RAG.

    Args:
        pergunta: Texto da consulta
        categoria: Filtrar por categoria (opcional)
        limite: Max resultados

    Returns:
        Lista de politicas relevantes
    """
    # Gerar embedding da pergunta
    query_embedding = await gerar_embedding(pergunta)

    # Buscar similares
    if categoria:
        result = supabase.rpc(
            "match_meta_policies",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": limite,
                "filter_categoria": categoria,
            }
        ).execute()
    else:
        result = supabase.rpc(
            "match_meta_policies",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": limite,
            }
        ).execute()

    return result.data or []


async def verificar_conformidade(acao: str) -> dict:
    """
    Verifica se uma acao esta em conformidade com politicas.

    Args:
        acao: Descricao da acao a verificar

    Returns:
        {
            "permitido": bool,
            "riscos": ["..."],
            "recomendacoes": ["..."],
            "politicas_relacionadas": [...]
        }
    """
    # Buscar politicas relacionadas
    politicas = await consultar_politicas(acao, limite=3)

    # Montar contexto para analise
    contexto = "\n\n".join([
        f"## {p['titulo']}\n{p['conteudo']}"
        for p in politicas
    ])

    # TODO: Usar Claude para analisar conformidade
    # Por enquanto, retornar politicas encontradas

    return {
        "permitido": True,  # Placeholder
        "riscos": [],
        "recomendacoes": [],
        "politicas_relacionadas": politicas,
    }
```

**Migration para funcao de busca:**

```sql
-- Funcao de busca por similaridade
CREATE OR REPLACE FUNCTION match_meta_policies(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_categoria text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    categoria text,
    titulo text,
    conteudo text,
    fonte_url text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        mp.id,
        mp.categoria,
        mp.titulo,
        mp.conteudo,
        mp.fonte_url,
        1 - (mp.embedding <=> query_embedding) as similarity
    FROM meta_policies mp
    WHERE
        (filter_categoria IS NULL OR mp.categoria = filter_categoria)
        AND (mp.valido_ate IS NULL OR mp.valido_ate >= CURRENT_DATE)
        AND 1 - (mp.embedding <=> query_embedding) > match_threshold
    ORDER BY mp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### DoD

- [ ] Tabela meta_policies criada
- [ ] Seed de politicas iniciais
- [ ] Funcao de busca por similaridade
- [ ] Endpoint de consulta
- [ ] Job de atualizacao periodica

---

## E04: Trust Score Engine

### Objetivo
Implementar calculo multiparametrico de Trust Score com permissoes dinamicas.

### Detalhes em arquivo separado
Ver `epic-04-trust-score.md`

---

## Cronograma Sprint 25

### Semana 1: Foundation
```
Dia 1-2: E01 Modelo de Dados Unificado
Dia 2-3: E02 Salvy Integration
Dia 3-4: E03 Meta Policies RAG
Dia 4-5: E04 Trust Score Engine
```

### Semana 2: Warmer Core
```
Dia 1-2: E05 Human Simulator
Dia 2-3: E06 Conversation Generator
Dia 3-4: E07 Pairing Engine
Dia 4-5: E08 Warming Scheduler
```

### Semana 3: Orquestracao
```
Dia 1-2: E09 Warming Orchestrator
Dia 2-3: E10 Early Warning
Dia 3-4: E11 Warmer API
Dia 5: Testes e ajustes
```

---

## Entregavel

Ao final da Sprint 25:
- [ ] Chips podem ser provisionados via Salvy
- [ ] Sistema de aquecimento funcionando (21 dias)
- [ ] Trust Score calculando e atualizando
- [ ] Permissoes dinamicas por nivel
- [ ] RAG de politicas consultavel
- [ ] Early Warning pausando chips problematicos
- [ ] API de gestao do Warmer

---

*Sprint criada em 30/12/2025*
