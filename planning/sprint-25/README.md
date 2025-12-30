# Sprint 25: Julia Warmer - Sistema de Aquecimento de WhatsApp

**Status:** Planejado
**Inicio:** A definir
**Estimativa:** 3 semanas
**Dependencias:** Sprint 21 (Production Gate)

---

## Objetivo

Construir sistema proprio de **aquecimento de numeros WhatsApp** para operacao em escala industrial, eliminando dependencia de ferramentas terceiras e integrando nativamente com a plataforma Julia.

### Contexto

- **87% das contas novas** sofrem restricoes em 72h sem aquecimento
- Contas aquecidas por 21+ dias alcancam **20-30 msgs/dia para desconhecidos**
- Meta: ser o **maior comunicador com medicos do Brasil**
- Escala planejada: **50-100+ chips**, **1000+ grupos**

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                     JULIA PLATFORM                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   WARMER    │  │   AGENT     │  │  OPERATOR   │          │
│  │  (warm-up)  │  │ (conversas) │  │  (gestao)   │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│  ┌───────────────────────▼────────────────────────┐         │
│  │           Evolution API Pool (N instancias)     │         │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │         │
│  │  │Chip1│ │Chip2│ │Chip3│ │ ... │ │ChipN│      │         │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘      │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Ciclo de Vida do Chip

```
NOVO CHIP
    │
    ▼
┌─────────┐     21 dias      ┌─────────┐    Continuo    ┌─────────┐
│ WARMER  │ ───────────────► │  AGENT  │ ─────────────► │ MONITOR │
│(warm-up)│  Health >= 85%   │ (Julia) │   Health ok    │(saude)  │
└─────────┘                  └─────────┘                └─────────┘
    ▲                                                        │
    │                      Health < 50%                      │
    └────────────────────────────────────────────────────────┘
                        (volta pro warm-up)
```

---

## Stack Tecnico

| Componente | Tecnologia | Motivo |
|------------|------------|--------|
| Backend | FastAPI | Ja existe na Julia |
| Jobs Async | ARQ + Redis | Leve, nativo async |
| Cache | Redis | Trending topics, estados |
| Scheduler | APScheduler | Ja integrado |
| Evolution | 1 instancia/chip | Isolamento |
| Proxies | Residenciais BR | Obrigatorio anti-ban |
| Alertas | Slack + Telegram | Redundancia |
| Dashboard | Streamlit | MVP rapido |

---

## Epicos

| # | Epico | Descricao | Tempo |
|---|-------|-----------|-------|
| E01 | Modelo de Dados | Tabelas warmup_chips, warmup_pairs, warmup_interactions | 3h |
| E02 | Human Simulator | Delays calibrados + "digitando" + mark as read | 4h |
| E03 | Conversation Generator | Claude + typos + trending topics | 5h |
| E04 | Health Score v2 | Algoritmo completo com todos fatores | 4h |
| E05 | Pairing Engine | Pareamento rotativo entre chips | 4h |
| E06 | Message Scheduler | Agenda com distribuicao anti-padrao | 4h |
| E07 | Orchestrator | Coordena fases do warm-up | 6h |
| E08 | Early Warning System | Detecta problemas e pausa automaticamente | 4h |
| E09 | API Endpoints | CRUD chips, start/stop, status | 4h |
| E10 | Dashboard | Visualizacao health, progresso, alertas | 8h |

**Total Estimado:** ~46-50 horas

---

## E01: Modelo de Dados

### Objetivo
Criar estrutura de banco para tracking completo do warm-up.

### Migrations

```sql
-- =============================================
-- TABELA: warmup_chips
-- Chips/instancias gerenciadas pelo warmer
-- =============================================
CREATE TABLE warmup_chips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefone TEXT UNIQUE NOT NULL,
    instance_name TEXT UNIQUE NOT NULL,

    -- Status e fase
    status TEXT DEFAULT 'pending', -- pending, warming, ready, active, paused, banned
    fase_warmup TEXT DEFAULT 'setup', -- setup, primeiros_contatos, expansao, pre_operacao, operacao
    fase_iniciada_em TIMESTAMPTZ DEFAULT now(),

    -- Health tracking
    health_score INT DEFAULT 40,
    ultimo_calculo_health TIMESTAMPTZ,

    -- Metricas agregadas
    msgs_enviadas INT DEFAULT 0,
    msgs_recebidas INT DEFAULT 0,
    taxa_resposta DECIMAL(5,2) DEFAULT 0,
    tipos_midia_usados TEXT[] DEFAULT '{}', -- ['text', 'audio', 'image', 'video']
    status_criados_semana INT DEFAULT 0,
    teve_chamada BOOLEAN DEFAULT false,
    dias_inativo INT DEFAULT 0,

    -- Grupos
    grupos_count INT DEFAULT 0,

    -- Timestamps
    warming_started_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_warmup_chips_status ON warmup_chips(status);
CREATE INDEX idx_warmup_chips_fase ON warmup_chips(fase_warmup);

-- =============================================
-- TABELA: warmup_pairs
-- Pareamentos ativos entre chips
-- =============================================
CREATE TABLE warmup_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_a_id UUID REFERENCES warmup_chips(id) ON DELETE CASCADE,
    chip_b_id UUID REFERENCES warmup_chips(id) ON DELETE CASCADE,

    active BOOLEAN DEFAULT true,
    messages_exchanged INT DEFAULT 0,
    last_interaction TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_pair UNIQUE (chip_a_id, chip_b_id)
);

CREATE INDEX idx_warmup_pairs_active ON warmup_pairs(active) WHERE active = true;

-- =============================================
-- TABELA: warmup_conversations
-- Historico de conversas de warm-up
-- =============================================
CREATE TABLE warmup_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id UUID REFERENCES warmup_pairs(id) ON DELETE CASCADE,

    tema TEXT NOT NULL,
    messages JSONB NOT NULL, -- [{from: 'a', text: '...', sent_at: '...'}, ...]
    turnos INT DEFAULT 0,

    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_warmup_conversations_pair ON warmup_conversations(pair_id);

-- =============================================
-- TABELA: warmup_interactions
-- Tracking granular de todas interacoes
-- =============================================
CREATE TABLE warmup_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID REFERENCES warmup_chips(id) ON DELETE CASCADE,

    tipo TEXT NOT NULL, -- 'msg_enviada', 'msg_recebida', 'chamada', 'status', 'grupo_entrada'
    destinatario TEXT,
    midia_tipo TEXT, -- 'text', 'audio', 'image', 'video'

    -- Para mensagens
    obteve_resposta BOOLEAN,
    tempo_resposta_segundos INT,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_warmup_interactions_chip ON warmup_interactions(chip_id, created_at DESC);
CREATE INDEX idx_warmup_interactions_tipo ON warmup_interactions(tipo);

-- =============================================
-- TABELA: warmup_health_log
-- Historico de health scores
-- =============================================
CREATE TABLE warmup_health_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID REFERENCES warmup_chips(id) ON DELETE CASCADE,

    score INT NOT NULL,
    factors JSONB NOT NULL, -- {age: 10, msgs_sent: 5, response_rate: 0.45, ...}

    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_warmup_health_log_chip ON warmup_health_log(chip_id, recorded_at DESC);

-- =============================================
-- TABELA: warmup_alerts
-- Alertas e incidentes
-- =============================================
CREATE TABLE warmup_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID REFERENCES warmup_chips(id) ON DELETE CASCADE,

    severity TEXT NOT NULL, -- 'critical', 'warning', 'info'
    tipo TEXT NOT NULL, -- 'health_drop', 'spam_error', 'low_response', 'inactivity'
    message TEXT NOT NULL,

    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_warmup_alerts_unresolved ON warmup_alerts(chip_id, resolved) WHERE resolved = false;
```

### Aceite
- [ ] Migrations aplicadas
- [ ] Indices criados
- [ ] Tipos TypeScript gerados

---

## E02: Human Simulator

### Objetivo
Simular comportamento humano ao enviar mensagens (digitando, delays, leitura).

### Implementacao

**Arquivo:** `app/services/warmer/human_simulator.py`

```python
"""
Human Simulator - Simula comportamento humano no WhatsApp.

Baseado no whitepaper da Meta sobre deteccao de automacao.
O indicador "digitando..." e critico para evitar flags.
"""
import asyncio
import random
from typing import Optional

from app.services.evolution import evolution_client


async def enviar_mensagem_humanizada(
    instance: str,
    destinatario: str,
    texto: str,
    simular_leitura: bool = True,
) -> bool:
    """
    Envia mensagem simulando comportamento humano completo.

    Fluxo:
    1. Delay de "leitura" (3-15s)
    2. Marca como lido
    3. Delay de "pensar" (1-3s)
    4. Envia evento "digitando"
    5. Aguarda tempo proporcional ao texto
    6. Envia mensagem

    Args:
        instance: Nome da instancia Evolution
        destinatario: JID do destinatario
        texto: Texto da mensagem
        simular_leitura: Se deve simular leitura antes

    Returns:
        True se enviou com sucesso
    """
    try:
        # 1. Delay antes de "ler" (distribuicao normal, media 8s)
        if simular_leitura:
            delay_leitura = random.gauss(8, 3)
            delay_leitura = max(3, min(15, delay_leitura))
            await asyncio.sleep(delay_leitura)

            # 2. Marcar como lido
            await evolution_client.mark_as_read(instance, destinatario)

        # 3. Delay de "pensar" (1-3s)
        await asyncio.sleep(random.uniform(1, 3))

        # 4. Enviar evento "digitando"
        # Duracao proporcional ao tamanho da mensagem (~50ms por caractere)
        tempo_digitacao = len(texto) * 0.05
        tempo_digitacao = max(1.5, min(5, tempo_digitacao))

        await evolution_client.send_presence(
            instance,
            destinatario,
            "composing"
        )
        await asyncio.sleep(tempo_digitacao)

        # 5. Parar de digitar
        await evolution_client.send_presence(
            instance,
            destinatario,
            "paused"
        )

        # 6. Delay final antes de enviar (0.5-2s)
        await asyncio.sleep(random.uniform(0.5, 2))

        # 7. Enviar mensagem
        await evolution_client.send_text(instance, destinatario, texto)

        return True

    except Exception as e:
        logger.error(f"Erro ao enviar msg humanizada: {e}")
        return False


def calcular_delay_entre_turnos() -> float:
    """
    Calcula delay entre turnos de conversa.
    Distribuicao exponencial para parecer natural.

    Returns:
        Delay em segundos (20-90s)
    """
    # Exponencial com media 45s
    delay = random.expovariate(1/45)
    return max(20, min(90, delay))


def calcular_delay_resposta() -> float:
    """
    Calcula delay para responder uma mensagem recebida.

    Returns:
        Delay em segundos (3-15s)
    """
    return random.gauss(8, 3)
```

### Aceite
- [ ] Funcao `enviar_mensagem_humanizada` implementada
- [ ] Delays calibrados conforme pesquisa (20s-90s entre turnos)
- [ ] Evento "digitando" funcionando via Evolution API
- [ ] Testes unitarios

---

## E03: Conversation Generator

### Objetivo
Gerar dialogos naturais usando Claude com typos intencionais e trending topics.

### Implementacao

**Arquivo:** `app/services/warmer/conversation_generator.py`

```python
"""
Conversation Generator - Gera dialogos naturais para warm-up.

Usa Claude para criar conversas com:
- Linguagem informal brasileira
- Typos intencionais com correcao
- Trending topics para contexto atual
"""
import random
import json
import feedparser
from typing import Optional

from app.services.claude import claude_client
from app.services.redis import redis_client


TEMAS_WARMUP = [
    "cotidiano",
    "clima e tempo",
    "futebol brasileiro",
    "filmes e series",
    "viagens",
    "comida e restaurantes",
    "tecnologia",
    "noticias leves",
    "fim de semana",
    "trabalho generico",
    "familia",
    "musica",
    "series netflix",
    "compras online",
]


async def buscar_trending_brasil() -> str:
    """
    Busca trending topic brasileiro.
    Usa cache Redis (1 hora) para evitar requests excessivos.

    Returns:
        String com topico trending ou tema generico
    """
    # Checar cache
    cached = await redis_client.get("warmer:trending_brasil")
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached

    try:
        # RSS G1 (mais estavel que Google Trends)
        feed = feedparser.parse('https://g1.globo.com/rss/g1/')
        if feed.entries:
            manchetes = [entry.title for entry in feed.entries[:10]]
            trending = random.choice(manchetes)

            # Cache por 1 hora
            await redis_client.setex("warmer:trending_brasil", 3600, trending)
            return trending

    except Exception as e:
        logger.warning(f"Erro ao buscar trending: {e}")

    # Fallback
    return random.choice(TEMAS_WARMUP)


async def gerar_dialogo(
    tema: Optional[str] = None,
    usar_trending: bool = True,
) -> list[dict]:
    """
    Gera dialogo natural entre duas pessoas.

    Args:
        tema: Tema especifico (opcional)
        usar_trending: Se deve usar trending topics

    Returns:
        Lista de mensagens: [{from: 'A', text: '...'}, ...]
    """
    # Escolher tema
    if not tema:
        if usar_trending and random.random() < 0.3:  # 30% chance trending
            tema = await buscar_trending_brasil()
        else:
            tema = random.choice(TEMAS_WARMUP)

    # Numero de turnos variavel (4-12)
    turnos = random.randint(4, 12)

    prompt = f"""Gere um dialogo casual de WhatsApp entre duas pessoas (A e B) sobre: {tema}

REGRAS OBRIGATORIAS:
- Exatamente {turnos} mensagens no total (alternando A e B)
- Mensagens CURTAS (1-3 linhas maximo cada)
- Linguagem informal brasileira: vc, pra, ta, blz, tb, msg, tmb, nd, oq
- Emojis ocasionais (3-5 no dialogo todo, NAO em toda msg)
- IMPORTANTE: Inclua 1-2 typos com correcao, exemplos:
  * "voc" seguido de "vc*" na proxima msg
  * "trbalhando" seguido de "trabalhando*"
  * "aond" seguido de "onde*"
- Termine naturalmente (despedida ou combinado)
- Varie tamanho das msgs (algumas bem curtas "blz", outras medias)
- Pareca conversa REAL entre amigos

FORMATO JSON (array de objetos):
[
  {{"from": "A", "text": "mensagem aqui"}},
  {{"from": "B", "text": "resposta aqui"}},
  ...
]

APENAS O JSON, sem explicacoes."""

    try:
        response = await claude_client.generate(
            prompt=prompt,
            model="haiku",
            max_tokens=1000,
        )

        # Parse JSON
        mensagens = json.loads(response)

        if not isinstance(mensagens, list) or len(mensagens) < 4:
            raise ValueError("Formato invalido")

        return mensagens

    except Exception as e:
        logger.error(f"Erro ao gerar dialogo: {e}")
        # Fallback: dialogo pre-definido
        return gerar_dialogo_fallback()


def gerar_dialogo_fallback() -> list[dict]:
    """Dialogo fallback caso Claude falhe."""
    dialogos = [
        [
            {"from": "A", "text": "e ai, blz?"},
            {"from": "B", "text": "tudo bem e vc?"},
            {"from": "A", "text": "de boa, so trabalhando"},
            {"from": "B", "text": "sei como e kkk"},
            {"from": "A", "text": "fds ta chegando pelo menos"},
            {"from": "B", "text": "ne, ja ta precisando"},
        ],
        [
            {"from": "A", "text": "viu o jogo ontem?"},
            {"from": "B", "text": "vi, que jogo hein"},
            {"from": "A", "text": "demais, nao esperava"},
            {"from": "B", "text": "tb nao, achei q ia perder"},
            {"from": "A", "text": "sorte q deu certo no final"},
            {"from": "B", "text": "agr e torcer pro proximo"},
        ],
    ]
    return random.choice(dialogos)
```

### Aceite
- [ ] Geracao de dialogos via Claude funcionando
- [ ] Trending topics com cache Redis
- [ ] Typos intencionais incluidos
- [ ] Fallback para dialogos pre-definidos
- [ ] Testes com diferentes temas

---

## E04: Health Score v2

### Objetivo
Implementar algoritmo completo de health score baseado na pesquisa de mercado.

### Implementacao

**Arquivo:** `app/services/warmer/health_score.py`

```python
"""
Health Score v2 - Algoritmo de saude do chip.

Score 0-100 baseado em multiplos fatores identificados na pesquisa:
- Taxa de resposta (critico)
- Proporcao enviadas/recebidas
- Variacao de midia
- Idade da conta
- Atividade em grupos
- Erros e warnings
"""
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

from app.services.supabase import supabase


@dataclass
class HealthFactors:
    """Fatores que compoem o health score."""
    idade_dias: int = 0
    msgs_enviadas: int = 0
    msgs_recebidas: int = 0
    conversas_bidirecionais: int = 0
    grupos_ativos: int = 0
    tipos_midia: int = 0
    status_semana: int = 0
    teve_chamada: bool = False
    erros_spam: int = 0
    warnings: int = 0
    dias_inativo: int = 0
    taxa_resposta: float = 0.0


async def calcular_health_score(chip_id: str) -> tuple[int, HealthFactors]:
    """
    Calcula health score completo do chip.

    Args:
        chip_id: UUID do chip

    Returns:
        Tupla (score, factors)
    """
    factors = await coletar_fatores(chip_id)

    # Base reduzida - precisa "ganhar" confianca
    score = 40

    # ══════════════════════════════════════════
    # FATORES POSITIVOS
    # ══════════════════════════════════════════

    # Idade da conta (+2/dia, max +14)
    score += min(factors.idade_dias * 2, 14)

    # Mensagens ENVIADAS (+1 por 10, max +10)
    score += min(factors.msgs_enviadas // 10, 10)

    # Mensagens RECEBIDAS (+1 por 10, max +10)
    score += min(factors.msgs_recebidas // 10, 10)

    # Conversas bidirecionais genuinas (+3 cada, max +12)
    score += min(factors.conversas_bidirecionais * 3, 12)

    # Grupos ativos onde enviou msg (+3 cada, max +9)
    score += min(factors.grupos_ativos * 3, 9)

    # Variacao de midia (+2 por tipo, max +8)
    score += min(factors.tipos_midia * 2, 8)

    # Status criado esta semana (+3 cada, max +6)
    score += min(factors.status_semana * 3, 6)

    # ══════════════════════════════════════════
    # FATORES NEGATIVOS
    # ══════════════════════════════════════════

    # Erros de spam (-15 cada)
    score -= factors.erros_spam * 15

    # Warnings (-8 cada)
    score -= factors.warnings * 8

    # Inatividade (-3/dia, max -12)
    score -= min(factors.dias_inativo * 3, 12)

    # Proporcao enviadas/recebidas ruim
    if factors.msgs_recebidas > 0:
        proporcao = factors.msgs_enviadas / factors.msgs_recebidas
        if proporcao > 3:
            score -= 10
        elif proporcao > 2:
            score -= 5

    # Taxa de resposta
    if factors.taxa_resposta < 0.20:
        score -= 10
    elif factors.taxa_resposta < 0.30:
        score -= 5
    elif factors.taxa_resposta > 0.50:
        score += 5  # Bonus

    # ══════════════════════════════════════════
    # BONUS
    # ══════════════════════════════════════════

    # Chamada de voz/video realizada (+5)
    if factors.teve_chamada:
        score += 5

    # Garantir range 0-100
    score = max(0, min(100, score))

    return score, factors


async def coletar_fatores(chip_id: str) -> HealthFactors:
    """Coleta todos os fatores do banco."""
    # Buscar chip
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return HealthFactors()

    c = chip.data
    now = datetime.now(timezone.utc)
    created = datetime.fromisoformat(c["created_at"].replace("Z", "+00:00"))

    # Calcular dias inativo
    last_activity = c.get("last_activity_at")
    if last_activity:
        last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        dias_inativo = (now - last_dt).days
    else:
        dias_inativo = 0

    # Contar conversas bidirecionais (ultimos 7 dias)
    conversas = supabase.table("warmup_interactions") \
        .select("destinatario, obteve_resposta", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "msg_enviada") \
        .eq("obteve_resposta", True) \
        .gte("created_at", (now - timedelta(days=7)).isoformat()) \
        .execute()

    # Contar erros recentes
    erros = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "spam_error") \
        .gte("created_at", (now - timedelta(days=7)).isoformat()) \
        .execute()

    warnings = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("severity", "warning") \
        .gte("created_at", (now - timedelta(days=7)).isoformat()) \
        .execute()

    return HealthFactors(
        idade_dias=(now - created).days,
        msgs_enviadas=c.get("msgs_enviadas", 0),
        msgs_recebidas=c.get("msgs_recebidas", 0),
        conversas_bidirecionais=conversas.count or 0,
        grupos_ativos=c.get("grupos_count", 0),
        tipos_midia=len(c.get("tipos_midia_usados", [])),
        status_semana=c.get("status_criados_semana", 0),
        teve_chamada=c.get("teve_chamada", False),
        erros_spam=erros.count or 0,
        warnings=warnings.count or 0,
        dias_inativo=dias_inativo,
        taxa_resposta=float(c.get("taxa_resposta", 0)),
    )


async def registrar_health_score(chip_id: str):
    """Calcula e registra health score no historico."""
    score, factors = await calcular_health_score(chip_id)

    # Atualizar chip
    supabase.table("warmup_chips") \
        .update({
            "health_score": score,
            "ultimo_calculo_health": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", chip_id) \
        .execute()

    # Registrar historico
    supabase.table("warmup_health_log") \
        .insert({
            "chip_id": chip_id,
            "score": score,
            "factors": {
                "idade_dias": factors.idade_dias,
                "msgs_enviadas": factors.msgs_enviadas,
                "msgs_recebidas": factors.msgs_recebidas,
                "conversas_bidi": factors.conversas_bidirecionais,
                "grupos": factors.grupos_ativos,
                "tipos_midia": factors.tipos_midia,
                "taxa_resposta": factors.taxa_resposta,
                "erros": factors.erros_spam,
                "warnings": factors.warnings,
            },
        }) \
        .execute()

    return score
```

### Aceite
- [ ] Algoritmo implementado com todos os fatores
- [ ] Taxa de resposta calculada corretamente
- [ ] Proporcao enviadas/recebidas funcionando
- [ ] Historico de health registrado
- [ ] Testes com cenarios diversos

---

## E05: Pairing Engine

### Objetivo
Gerenciar pareamento rotativo entre chips para warm-up cruzado.

### Implementacao

**Arquivo:** `app/services/warmer/pairing_engine.py`

```python
"""
Pairing Engine - Gerencia pareamentos entre chips.

Regras:
- Cada chip pode ter max 15 interacoes/dia com outros chips
- Pareamentos rotacionam para evitar padrao
- Chips na mesma fase tem prioridade
"""
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase


MAX_INTERACOES_DIA = 15
MAX_PARES_ATIVOS = 10


async def obter_pareamentos_dia(chip_id: str) -> list[str]:
    """
    Obtem lista de chips pareados para hoje.
    Cria novos pareamentos se necessario.

    Args:
        chip_id: UUID do chip

    Returns:
        Lista de chip_ids para interagir hoje
    """
    # Buscar pares ativos
    pares = supabase.table("warmup_pairs") \
        .select("chip_a_id, chip_b_id") \
        .or_(f"chip_a_id.eq.{chip_id},chip_b_id.eq.{chip_id}") \
        .eq("active", True) \
        .execute()

    parceiros = []
    for par in pares.data or []:
        if par["chip_a_id"] == chip_id:
            parceiros.append(par["chip_b_id"])
        else:
            parceiros.append(par["chip_a_id"])

    # Se tem poucos pares, criar novos
    if len(parceiros) < MAX_PARES_ATIVOS:
        novos = await criar_novos_pareamentos(chip_id, MAX_PARES_ATIVOS - len(parceiros))
        parceiros.extend(novos)

    return parceiros[:MAX_PARES_ATIVOS]


async def criar_novos_pareamentos(chip_id: str, quantidade: int) -> list[str]:
    """
    Cria novos pareamentos com chips disponiveis.
    Prioriza chips na mesma fase de warm-up.
    """
    # Buscar chip atual
    chip = supabase.table("warmup_chips") \
        .select("fase_warmup") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    fase_atual = chip.data.get("fase_warmup") if chip.data else "setup"

    # Buscar chips disponiveis (mesma fase primeiro)
    disponiveis = supabase.table("warmup_chips") \
        .select("id, fase_warmup") \
        .eq("status", "warming") \
        .neq("id", chip_id) \
        .execute()

    if not disponiveis.data:
        return []

    # Ordenar: mesma fase primeiro
    chips = sorted(
        disponiveis.data,
        key=lambda c: (0 if c["fase_warmup"] == fase_atual else 1, random.random())
    )

    # Filtrar chips que ja sao pares
    pares_existentes = supabase.table("warmup_pairs") \
        .select("chip_a_id, chip_b_id") \
        .or_(f"chip_a_id.eq.{chip_id},chip_b_id.eq.{chip_id}") \
        .execute()

    ja_pareados = set()
    for par in pares_existentes.data or []:
        ja_pareados.add(par["chip_a_id"])
        ja_pareados.add(par["chip_b_id"])

    # Criar novos pares
    novos = []
    for c in chips:
        if c["id"] not in ja_pareados and len(novos) < quantidade:
            # Criar par
            supabase.table("warmup_pairs") \
                .insert({
                    "chip_a_id": chip_id,
                    "chip_b_id": c["id"],
                }) \
                .execute()
            novos.append(c["id"])

    return novos


async def registrar_interacao(chip_a: str, chip_b: str):
    """Registra interacao entre par de chips."""
    # Atualizar par
    supabase.table("warmup_pairs") \
        .update({
            "messages_exchanged": supabase.sql("messages_exchanged + 1"),
            "last_interaction": datetime.now(timezone.utc).isoformat(),
        }) \
        .or_(
            f"and(chip_a_id.eq.{chip_a},chip_b_id.eq.{chip_b}),"
            f"and(chip_a_id.eq.{chip_b},chip_b_id.eq.{chip_a})"
        ) \
        .execute()


async def rotacionar_pareamentos():
    """
    Rotaciona pareamentos antigos para evitar padrao.
    Executar semanalmente.
    """
    uma_semana_atras = datetime.now(timezone.utc) - timedelta(days=7)

    # Desativar pares antigos
    supabase.table("warmup_pairs") \
        .update({"active": False}) \
        .lt("created_at", uma_semana_atras.isoformat()) \
        .eq("active", True) \
        .execute()
```

### Aceite
- [ ] Pareamento automatico funcionando
- [ ] Priorizacao por fase implementada
- [ ] Rotacao semanal funcionando
- [ ] Max 15 interacoes/dia respeitado
- [ ] Testes de pareamento

---

## E06: Message Scheduler

### Objetivo
Agendar mensagens com distribuicao anti-padrao para evitar deteccao.

### Implementacao

**Arquivo:** `app/services/warmer/scheduler.py`

```python
"""
Message Scheduler - Agenda mensagens com distribuicao anti-padrao.

Cada chip tem janela de atividade unica baseada em hash do ID.
Previne que todos os chips enviem no mesmo horario.
"""
import hashlib
from datetime import datetime, date, time, timedelta, timezone
from typing import Tuple
import random

from app.services.redis import redis_client


def calcular_janela_atividade(chip_id: str, dia: date) -> Tuple[int, int, int, int]:
    """
    Calcula janela de atividade unica para o chip neste dia.

    Baseado em hash deterministico do chip_id + dia.
    Cada chip tem janela de 6 horas dentro do periodo 8h-22h.

    Args:
        chip_id: UUID do chip
        dia: Data

    Returns:
        Tupla (hora_inicio, minuto_inicio, hora_fim, minuto_fim)
    """
    # Hash deterministico
    seed = f"{chip_id}{dia}".encode()
    hash_int = int(hashlib.md5(seed).hexdigest(), 16)

    # Janela de 6 horas dentro de 8h-22h (14h disponiveis)
    inicio_possivel = 8   # 8h da manha
    fim_possivel = 16     # Ate 16h (pra janela de 6h terminar as 22h)

    hora_inicio = inicio_possivel + (hash_int % (fim_possivel - inicio_possivel))
    minuto_inicio = hash_int % 30  # Variacao de 0-30 min

    hora_fim = hora_inicio + 6
    minuto_fim = (hash_int >> 8) % 30

    return (hora_inicio, minuto_inicio, hora_fim, minuto_fim)


def esta_na_janela(chip_id: str) -> bool:
    """Verifica se o chip esta na sua janela de atividade."""
    agora = datetime.now(timezone.utc)
    # Ajustar para horario de Brasilia (UTC-3)
    agora_br = agora - timedelta(hours=3)

    janela = calcular_janela_atividade(chip_id, agora_br.date())
    hora_inicio, min_inicio, hora_fim, min_fim = janela

    inicio = time(hora_inicio, min_inicio)
    fim = time(hora_fim, min_fim)
    atual = agora_br.time()

    return inicio <= atual <= fim


async def pode_enviar_mensagem(chip_id: str) -> Tuple[bool, str]:
    """
    Verifica se o chip pode enviar mensagem agora.

    Checks:
    1. Esta na janela de atividade
    2. Nao excedeu limite diario
    3. Respeitou delay minimo desde ultima msg

    Returns:
        Tupla (pode_enviar, motivo)
    """
    # Check 1: Janela de atividade
    if not esta_na_janela(chip_id):
        return False, "fora_janela"

    # Check 2: Limite diario
    hoje = date.today().isoformat()
    key = f"warmer:msgs_dia:{chip_id}:{hoje}"
    msgs_hoje = await redis_client.get(key)
    msgs_hoje = int(msgs_hoje or 0)

    # Limite varia por fase
    chip = await get_chip(chip_id)
    limites = {
        "setup": 0,
        "primeiros_contatos": 10,
        "expansao": 30,
        "pre_operacao": 50,
        "operacao": 100,
    }
    limite = limites.get(chip.fase_warmup, 10)

    if msgs_hoje >= limite:
        return False, "limite_diario"

    # Check 3: Delay minimo (2 min entre msgs)
    key_ultima = f"warmer:ultima_msg:{chip_id}"
    ultima = await redis_client.get(key_ultima)
    if ultima:
        ultima_dt = datetime.fromisoformat(ultima.decode())
        if (datetime.now(timezone.utc) - ultima_dt).seconds < 120:
            return False, "delay_minimo"

    return True, "ok"


async def registrar_envio(chip_id: str):
    """Registra que uma mensagem foi enviada."""
    agora = datetime.now(timezone.utc)
    hoje = date.today().isoformat()

    # Incrementar contador diario
    key = f"warmer:msgs_dia:{chip_id}:{hoje}"
    await redis_client.incr(key)
    await redis_client.expire(key, 86400 * 2)  # Expira em 2 dias

    # Registrar timestamp
    key_ultima = f"warmer:ultima_msg:{chip_id}"
    await redis_client.set(key_ultima, agora.isoformat())
```

### Aceite
- [ ] Janela de atividade calculada por hash
- [ ] Distribuicao anti-padrao funcionando
- [ ] Limites diarios por fase respeitados
- [ ] Delay minimo entre mensagens
- [ ] Testes de scheduling

---

## E07: Orchestrator

### Objetivo
Coordenar todo o fluxo de warm-up, gerenciando fases e disparando acoes.

### Implementacao

**Arquivo:** `app/services/warmer/orchestrator.py`

```python
"""
Orchestrator - Coordena o fluxo de warm-up.

Responsabilidades:
- Avaliar progressao de fases
- Disparar conversas entre pares
- Monitorar saude dos chips
- Responder a alertas
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.warmer.health_score import calcular_health_score, registrar_health_score
from app.services.warmer.pairing_engine import obter_pareamentos_dia, registrar_interacao
from app.services.warmer.conversation_generator import gerar_dialogo
from app.services.warmer.human_simulator import enviar_mensagem_humanizada, calcular_delay_entre_turnos
from app.services.warmer.scheduler import pode_enviar_mensagem, registrar_envio
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


# Criterios de progressao por fase
CRITERIOS_FASE = {
    "setup": {
        "dias_min": 3,
        "health_min": 45,
        "proxima": "primeiros_contatos",
    },
    "primeiros_contatos": {
        "dias_min": 4,
        "health_min": 55,
        "taxa_resposta_min": 0.5,
        "proxima": "expansao",
    },
    "expansao": {
        "dias_min": 7,
        "health_min": 70,
        "taxa_resposta_min": 0.4,
        "proxima": "pre_operacao",
    },
    "pre_operacao": {
        "dias_min": 7,
        "health_min": 85,
        "taxa_resposta_min": 0.35,
        "proxima": "operacao",
    },
}


async def executar_ciclo_warmup():
    """
    Executa um ciclo de warm-up para todos os chips ativos.
    Deve ser chamado a cada 5 minutos via scheduler.
    """
    # Buscar chips em warm-up
    chips = supabase.table("warmup_chips") \
        .select("*") \
        .eq("status", "warming") \
        .execute()

    for chip in chips.data or []:
        try:
            await processar_chip(chip)
        except Exception as e:
            logger.error(f"Erro processando chip {chip['id']}: {e}")


async def processar_chip(chip: dict):
    """Processa um chip individual."""
    chip_id = chip["id"]

    # 1. Verificar se pode enviar
    pode, motivo = await pode_enviar_mensagem(chip_id)
    if not pode:
        logger.debug(f"Chip {chip_id[:8]} nao pode enviar: {motivo}")
        return

    # 2. Avaliar progressao de fase
    await avaliar_progressao_fase(chip_id)

    # 3. Se nao esta em setup, executar conversa
    if chip["fase_warmup"] != "setup":
        await executar_conversa_warmup(chip_id)

    # 4. Atualizar health score
    await registrar_health_score(chip_id)


async def avaliar_progressao_fase(chip_id: str):
    """Avalia se o chip pode avancar para proxima fase."""
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return

    c = chip.data
    fase_atual = c["fase_warmup"]

    criterio = CRITERIOS_FASE.get(fase_atual)
    if not criterio:
        return  # Ja em operacao

    # Calcular metricas
    fase_iniciada = datetime.fromisoformat(c["fase_iniciada_em"].replace("Z", "+00:00"))
    dias_fase = (datetime.now(timezone.utc) - fase_iniciada).days
    health = c["health_score"]
    taxa_resposta = float(c.get("taxa_resposta", 0))

    # Verificar criterios
    criterios_ok = (
        dias_fase >= criterio["dias_min"] and
        health >= criterio["health_min"] and
        taxa_resposta >= criterio.get("taxa_resposta_min", 0)
    )

    if criterios_ok:
        nova_fase = criterio["proxima"]

        # Atualizar fase
        supabase.table("warmup_chips") \
            .update({
                "fase_warmup": nova_fase,
                "fase_iniciada_em": datetime.now(timezone.utc).isoformat(),
            }) \
            .eq("id", chip_id) \
            .execute()

        # Notificar
        await enviar_slack({
            "text": f":rocket: Chip {c['telefone'][-4:]} avancou para fase: {nova_fase}",
            "attachments": [{
                "color": "#22C55E",
                "fields": [
                    {"title": "Health", "value": str(health), "short": True},
                    {"title": "Taxa Resposta", "value": f"{taxa_resposta:.0%}", "short": True},
                ],
            }]
        })

        # Se chegou em operacao, marcar como ready
        if nova_fase == "operacao":
            supabase.table("warmup_chips") \
                .update({
                    "status": "ready",
                    "ready_at": datetime.now(timezone.utc).isoformat(),
                }) \
                .eq("id", chip_id) \
                .execute()


async def executar_conversa_warmup(chip_id: str):
    """Executa uma conversa de warm-up com um par."""
    # Obter parceiros
    parceiros = await obter_pareamentos_dia(chip_id)
    if not parceiros:
        return

    # Escolher parceiro aleatorio
    parceiro_id = random.choice(parceiros)

    # Buscar dados dos chips
    chip = await get_chip_com_instance(chip_id)
    parceiro = await get_chip_com_instance(parceiro_id)

    if not chip or not parceiro:
        return

    # Gerar dialogo
    mensagens = await gerar_dialogo()

    # Executar conversa
    for i, msg in enumerate(mensagens):
        # Determinar quem envia
        if msg["from"] == "A":
            remetente = chip
            destinatario = parceiro
        else:
            remetente = parceiro
            destinatario = chip

        # Enviar com simulacao humana
        await enviar_mensagem_humanizada(
            instance=remetente["instance_name"],
            destinatario=destinatario["telefone"],
            texto=msg["text"],
        )

        # Registrar envio
        await registrar_envio(remetente["id"])

        # Delay entre turnos
        if i < len(mensagens) - 1:
            delay = calcular_delay_entre_turnos()
            await asyncio.sleep(delay)

    # Registrar interacao
    await registrar_interacao(chip_id, parceiro_id)

    logger.info(f"Conversa warmup: {chip['telefone'][-4:]} <-> {parceiro['telefone'][-4:]}")
```

### Aceite
- [ ] Ciclo de warm-up executando corretamente
- [ ] Progressao de fases automatica
- [ ] Conversas entre pares funcionando
- [ ] Notificacoes Slack de progressao
- [ ] Testes de orquestracao

---

## E08: Early Warning System

### Objetivo
Detectar problemas precocemente e pausar chips automaticamente.

### Implementacao

**Arquivo:** `app/services/warmer/early_warning.py`

```python
"""
Early Warning System - Detecta problemas e pausa chips.

Thresholds:
- Critico: pausa imediata
- Warning: reduz velocidade e alerta
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


# Thresholds de alerta
THRESHOLDS = {
    "critico": {
        "taxa_erro_1h": 0.5,      # 50% de erros em 1h
        "health_drop_1h": 20,      # Health caiu 20 pontos em 1h
        "spam_error": 1,           # Qualquer erro 131048
    },
    "warning": {
        "taxa_resposta_24h": 0.2,  # Taxa resposta < 20%
        "health_drop_24h": 10,     # Health caiu 10 pontos em 24h
        "msgs_sem_resposta": 5,    # 5 msgs consecutivas sem resposta
    },
}


async def monitorar_chip(chip_id: str) -> Tuple[str, str]:
    """
    Monitora saude do chip em tempo real.

    Returns:
        Tupla (status, motivo) - status: 'ok', 'warning', 'critico'
    """
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return "ok", ""

    c = chip.data
    now = datetime.now(timezone.utc)

    # ══════════════════════════════════════════
    # CHECKS CRITICOS
    # ══════════════════════════════════════════

    # Check: Erro de spam
    erros_spam = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "spam_error") \
        .gte("created_at", (now - timedelta(hours=1)).isoformat()) \
        .execute()

    if (erros_spam.count or 0) >= THRESHOLDS["critico"]["spam_error"]:
        await pausar_chip(chip_id, "CRITICO: Erro de spam detectado")
        return "critico", "spam_error"

    # Check: Health drop 1h
    health_1h_atras = await get_health_em(chip_id, now - timedelta(hours=1))
    if health_1h_atras and (health_1h_atras - c["health_score"]) > THRESHOLDS["critico"]["health_drop_1h"]:
        await pausar_chip(chip_id, f"CRITICO: Health caiu {health_1h_atras - c['health_score']} pontos em 1h")
        return "critico", "health_drop"

    # Check: Taxa de erro 1h
    total_1h = await contar_msgs_periodo(chip_id, 1)
    erros_1h = await contar_erros_periodo(chip_id, 1)
    if total_1h > 5 and (erros_1h / total_1h) > THRESHOLDS["critico"]["taxa_erro_1h"]:
        await pausar_chip(chip_id, f"CRITICO: {erros_1h/total_1h:.0%} de erros em 1h")
        return "critico", "taxa_erro"

    # ══════════════════════════════════════════
    # CHECKS WARNING
    # ══════════════════════════════════════════

    # Check: Taxa resposta 24h
    taxa_resposta = float(c.get("taxa_resposta", 0))
    if taxa_resposta < THRESHOLDS["warning"]["taxa_resposta_24h"]:
        await criar_alerta(chip_id, "warning", "low_response",
                          f"Taxa resposta baixa: {taxa_resposta:.0%}")
        await reduzir_velocidade(chip_id, 0.5)
        return "warning", "low_response"

    # Check: Health drop 24h
    health_24h_atras = await get_health_em(chip_id, now - timedelta(hours=24))
    if health_24h_atras and (health_24h_atras - c["health_score"]) > THRESHOLDS["warning"]["health_drop_24h"]:
        await criar_alerta(chip_id, "warning", "health_drop",
                          f"Health caiu {health_24h_atras - c['health_score']} pontos em 24h")
        return "warning", "health_drop"

    # Check: Msgs sem resposta consecutivas
    sem_resposta = await contar_msgs_sem_resposta_consecutivas(chip_id)
    if sem_resposta >= THRESHOLDS["warning"]["msgs_sem_resposta"]:
        await criar_alerta(chip_id, "warning", "no_response",
                          f"{sem_resposta} msgs sem resposta")
        return "warning", "no_response"

    return "ok", ""


async def pausar_chip(chip_id: str, motivo: str):
    """Pausa chip imediatamente."""
    supabase.table("warmup_chips") \
        .update({"status": "paused"}) \
        .eq("id", chip_id) \
        .execute()

    # Criar alerta
    await criar_alerta(chip_id, "critical", "paused", motivo)

    # Notificar
    chip = await get_chip(chip_id)
    await enviar_slack({
        "text": f":octagonal_sign: CHIP PAUSADO",
        "attachments": [{
            "color": "#EF4444",
            "fields": [
                {"title": "Telefone", "value": chip["telefone"][-4:], "short": True},
                {"title": "Motivo", "value": motivo, "short": False},
            ],
        }]
    })

    logger.warning(f"Chip {chip_id} pausado: {motivo}")


async def reduzir_velocidade(chip_id: str, fator: float):
    """Reduz velocidade de envio do chip."""
    # Implementar via flag no Redis
    from app.services.redis import redis_client
    key = f"warmer:velocidade:{chip_id}"
    await redis_client.set(key, str(fator))
    await redis_client.expire(key, 86400)  # 24h


async def criar_alerta(chip_id: str, severity: str, tipo: str, message: str):
    """Cria registro de alerta."""
    supabase.table("warmup_alerts") \
        .insert({
            "chip_id": chip_id,
            "severity": severity,
            "tipo": tipo,
            "message": message,
        }) \
        .execute()
```

### Aceite
- [ ] Deteccao de erros de spam funcionando
- [ ] Pausa automatica em casos criticos
- [ ] Reducao de velocidade em warnings
- [ ] Alertas registrados no banco
- [ ] Notificacoes Slack de incidentes

---

## E09: API Endpoints

### Objetivo
Expor endpoints REST para gerenciamento dos chips.

### Endpoints

| Metodo | Path | Descricao |
|--------|------|-----------|
| GET | /warmer/chips | Lista todos os chips |
| POST | /warmer/chips | Adiciona novo chip |
| GET | /warmer/chips/{id} | Detalhes do chip |
| POST | /warmer/chips/{id}/start | Inicia warm-up |
| POST | /warmer/chips/{id}/pause | Pausa warm-up |
| POST | /warmer/chips/{id}/resume | Retoma warm-up |
| GET | /warmer/chips/{id}/health | Historico de health |
| GET | /warmer/stats | Estatisticas gerais |

### Aceite
- [ ] Todos endpoints implementados
- [ ] Validacao de entrada
- [ ] Tratamento de erros
- [ ] Documentacao OpenAPI

---

## E10: Dashboard

### Objetivo
Dashboard Streamlit para visualizacao do status dos chips.

### Features

- Lista de chips com status e health score
- Grafico de evolucao de health por chip
- Alertas ativos
- Acoes rapidas (pausar, retomar)
- Metricas agregadas

### Aceite
- [ ] Dashboard funcional
- [ ] Visualizacao de health em tempo real
- [ ] Lista de alertas
- [ ] Acoes de gestao funcionando

---

## Cronograma

### Semana 1: Core
```
Dia 1-2: E01 Modelo de Dados
Dia 2-3: E02 Human Simulator
Dia 3-4: E03 Conversation Generator
Dia 4-5: E04 Health Score v2
```

### Semana 2: Orquestracao
```
Dia 1-2: E05 Pairing Engine
Dia 2-3: E06 Message Scheduler
Dia 3-5: E07 Orchestrator
```

### Semana 3: Operacao
```
Dia 1-2: E08 Early Warning System
Dia 2-3: E09 API Endpoints
Dia 3-5: E10 Dashboard
```

---

## Fase 2 (Futuro): Pool Externo

Apos validar o sistema interno:

1. Pool entre clientes Julia (se houver)
2. Parceria com outros sistemas
3. Marketplace de warm-up

---

*Sprint criada em 29/12/2025*
