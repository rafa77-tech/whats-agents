# Sprint 26: Orchestrator + Multi-Julia

**Status:** Em Progresso
**Inicio:** 12/01/2026
**Estimativa:** 2-3 semanas
**Dependencias:** Sprint 25 (Warmer + Trust Score)

---

## Objetivo

Construir o **sistema de orquestracao multi-chip em producao** com:
- N chips ativos para Julia (escala horizontal)
- Auto-replace quando chip degrada/bane
- Chip Selector inteligente por tipo de mensagem
- Continuidade de conversa (medico sempre no mesmo chip)
- Dashboard unificado de operacao

### Contexto de Negocio

| Metrica | Valor |
|---------|-------|
| Chips em producao | 5-10 ativos |
| Buffer de ready | 3+ chips |
| Warmup buffer | 10+ chips |
| Tempo substituicao | < 5 min |
| Escala maxima | 50-100+ chips |

### Mudanca de Paradigma

| Antes (Sprint 25) | Agora (Sprint 26) |
|-------------------|-------------------|
| Warmer isolado | Warmer + Producao integrados |
| Chips individuais | Pool gerenciado |
| Promocao manual | Auto-promocao por Trust Score |
| 1 webhook | Multi-webhook com routing |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SPRINT 26 SCOPE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        CHIP ORCHESTRATOR                                │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │ │
│  │  │    Pool     │  │    Auto     │  │   Health    │  │    Auto     │   │ │
│  │  │   Manager   │──│   Replace   │──│   Monitor   │──│  Provision  │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         CHIP SELECTOR                                   │ │
│  │                                                                         │ │
│  │   Msg Type      Chip Selection Criteria                                │ │
│  │   ─────────     ──────────────────────                                 │ │
│  │   prospeccao    Trust >= 80, pode_prospectar, menor uso/hora          │ │
│  │   followup      Trust >= 60, pode_followup, menor uso/hora            │ │
│  │   resposta      Trust >= 40, pode_responder, conversa existente       │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐         │
│         │                            │                            │         │
│         ▼                            ▼                            ▼         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │   PRODUCTION    │    │   PRODUCTION    │    │   PRODUCTION    │         │
│  │   CHIP 001      │    │   CHIP 002      │    │   CHIP 00N      │         │
│  │                 │    │                 │    │                 │         │
│  │ Trust: 87       │    │ Trust: 92       │    │ Trust: 78       │         │
│  │ Msgs hoje: 45   │    │ Msgs hoje: 23   │    │ Msgs hoje: 61   │         │
│  │ Status: active  │    │ Status: active  │    │ Status: active  │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│         │                        │                       │                  │
│         └────────────────────────┼───────────────────────┘                  │
│                                  ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        JULIA AGENT (Existente)                         │ │
│  │                                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │ │
│  │  │ Webhook  │──│ Pipeline │──│  Agente  │──│ Resposta │              │ │
│  │  │ Router   │  │          │  │  Claude  │  │          │              │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Fluxo de Auto-Replace

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO AUTO-REPLACE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

  CHIP ATIVO                    ORCHESTRATOR                 CHIP READY
      │                              │                            │
      │  Trust cai para 35           │                            │
      │  (vermelho)                  │                            │
      │ ────────────────────────────>│                            │
      │                              │                            │
      │                              │ 1. Detecta degradacao      │
      │                              │                            │
      │                              │ 2. Busca ready com         │
      │                              │    maior Trust Score       │
      │                              │ ──────────────────────────>│
      │                              │                            │
      │                              │ 3. Promove ready → active  │
      │                              │<────────────────────────── │
      │                              │                            │
      │                              │ 4. Migra conversas         │
      │                              │    ativas                  │
      │                              │                            │
      │ 5. Rebaixa para 'degraded'   │                            │
      │<───────────────────────────── │                            │
      │                              │                            │
      │                              │ 6. Notifica Slack          │
      │                              │                            │
      │                              │ 7. Se pool < ready_min,    │
      │                              │    provisiona novo         │
      │                              │    via Salvy               │
      │                              │                            │

ESTADOS DE TRANSICAO:

  warming ──(Trust >= 85)──> ready ──(slot disponivel)──> active
                                                              │
                             ready <──(recupera Trust)── degraded
                                                              │
                          cancelled <──(ban ou 30+ dias)── banned
```

---

## Epicos

| # | Epico | Descricao | Tempo | Status |
|---|-------|-----------|-------|--------|
| E01 | Chip Orchestrator | Pool manager, auto-replace, auto-provision, ready pool dinamico | 9h | ✅ |
| E02 | Chip Selector | Selecao inteligente, cooldown, affinity medico-chip | 7h | ✅ |
| E03 | Webhook Router | Multi-chip routing, continuidade conversa | 6h | ✅ |
| E04 | Health Monitor | Monitoramento producao, alertas proativos | 5h | ✅ |
| E05 | Dashboard Unificado | API Warmer + Producao + Metricas | 6h | ✅ |
| E06 | Webhook Robustness | DLQ, idempotency, retry | 4h | ✅ |
| E07 | Migracao Anunciada | Notificar medico antes de trocar chip (degradacao) | 4h | ✅ |
| S12.6* | Crawler & Source Discovery | Crawler de sites agregadores, discovery Google/Bing | 3h | 📋 |

**Total Estimado:** ~44h (7/8 implementados)

> *S12.6 é parte do E12 (Group Entry Engine) da Sprint 25. Detalhes em `planning/sprint-25/epic-12-group-entry-engine.md`

---

## E01: Chip Orchestrator

### Objetivo
Gerenciar pool de chips com auto-replace e auto-provision.

### Responsabilidades

1. **Pool Manager**
   - Manter `producao_min` chips ativos
   - Manter `ready_min` chips em reserva
   - Manter `warmup_buffer` chips aquecendo

2. **Auto-Replace**
   - Detectar chips degradados (Trust < threshold)
   - Promover chips ready para producao
   - Migrar conversas ativas

3. **Auto-Provision**
   - Quando pool_ready < ready_min, provisionar via Salvy
   - Configurar Evolution automaticamente

### Implementacao

**Arquivo:** `app/services/chips/orchestrator.py`

```python
"""
Chip Orchestrator - Gerenciamento do pool de chips.

Responsavel por:
- Manter pool saudavel (producao, ready, warming)
- Auto-replace de chips degradados
- Auto-provision quando necessario
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from app.services.supabase import supabase
from app.services.salvy.client import salvy_client
from app.services.chips.selector import chip_selector
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


class ChipOrchestrator:
    """Orquestrador central do pool de chips."""

    def __init__(self):
        self.config: Optional[Dict] = None
        self._running = False

    async def carregar_config(self) -> Dict:
        """Carrega configuracao do pool."""
        result = supabase.table("pool_config").select("*").single().execute()
        self.config = result.data
        return self.config

    # ════════════════════════════════════════════════════════════
    # POOL STATUS
    # ════════════════════════════════════════════════════════════

    async def obter_status_pool(self) -> Dict:
        """
        Retorna status atual do pool.

        Returns:
            {
                "producao": {"count": N, "min": M, "chips": [...]},
                "ready": {"count": N, "min": M, "chips": [...]},
                "warming": {"count": N, "buffer": M, "chips": [...]},
                "degraded": {"count": N, "chips": [...]},
                "saude": "saudavel" | "atencao" | "critico"
            }
        """
        if not self.config:
            await self.carregar_config()

        # Buscar chips por status
        result = supabase.table("chips").select("*").execute()
        chips = result.data or []

        producao = [c for c in chips if c["status"] == "active"]
        ready = [c for c in chips if c["status"] == "ready"]
        warming = [c for c in chips if c["status"] == "warming"]
        degraded = [c for c in chips if c["status"] == "degraded"]

        # Determinar saude
        saude = "saudavel"
        if len(producao) < self.config["producao_min"]:
            saude = "critico"
        elif len(ready) < self.config["ready_min"]:
            saude = "atencao"

        return {
            "producao": {
                "count": len(producao),
                "min": self.config["producao_min"],
                "max": self.config["producao_max"],
                "chips": producao,
            },
            "ready": {
                "count": len(ready),
                "min": self.config["ready_min"],
                "chips": ready,
            },
            "warming": {
                "count": len(warming),
                "buffer": self.config["warmup_buffer"],
                "chips": warming,
            },
            "degraded": {
                "count": len(degraded),
                "chips": degraded,
            },
            "saude": saude,
        }

    # ════════════════════════════════════════════════════════════
    # AUTO-REPLACE
    # ════════════════════════════════════════════════════════════

    async def verificar_chips_degradados(self) -> List[Dict]:
        """
        Identifica chips que precisam ser substituidos.

        Criterios:
        - Trust Score abaixo do threshold
        - Status 'banned'
        - Muitos erros nas ultimas 24h
        """
        if not self.config:
            await self.carregar_config()

        threshold = self.config["trust_degraded_threshold"]

        result = supabase.table("chips").select("*").in_(
            "status", ["active"]
        ).lt("trust_score", threshold).execute()

        return result.data or []

    async def substituir_chip(self, chip_degradado: Dict) -> Optional[Dict]:
        """
        Substitui chip degradado por um ready.

        Args:
            chip_degradado: Chip a ser substituido

        Returns:
            Novo chip promovido ou None se nao houver ready
        """
        logger.warning(
            f"[Orchestrator] Substituindo chip {chip_degradado['telefone']} "
            f"(Trust: {chip_degradado['trust_score']})"
        )

        # 1. Buscar melhor chip ready
        result = supabase.table("chips").select("*").eq(
            "status", "ready"
        ).gte(
            "trust_score", self.config["trust_min_for_ready"]
        ).order(
            "trust_score", desc=True
        ).limit(1).execute()

        if not result.data:
            logger.error("[Orchestrator] Nenhum chip ready disponivel!")
            await notificar_slack(
                f":rotating_light: *CRITICO*: Chip {chip_degradado['telefone']} degradado "
                f"mas NAO HA CHIPS READY para substituir!",
                canal="alertas"
            )
            return None

        novo_chip = result.data[0]

        # 2. Migrar conversas ativas
        await self._migrar_conversas(chip_degradado["id"], novo_chip["id"])

        # 3. Promover novo chip
        supabase.table("chips").update({
            "status": "active",
            "promoted_to_active_at": datetime.utcnow().isoformat(),
        }).eq("id", novo_chip["id"]).execute()

        # 4. Rebaixar chip degradado
        supabase.table("chips").update({
            "status": "degraded",
        }).eq("id", chip_degradado["id"]).execute()

        # 5. Notificar
        await notificar_slack(
            f":arrows_counterclockwise: *Auto-Replace*\n"
            f"- Degradado: `{chip_degradado['telefone']}` (Trust: {chip_degradado['trust_score']})\n"
            f"- Promovido: `{novo_chip['telefone']}` (Trust: {novo_chip['trust_score']})",
            canal="operacoes"
        )

        logger.info(
            f"[Orchestrator] Chip {novo_chip['telefone']} promovido para producao"
        )

        # 6. Verificar se precisa provisionar mais
        await self.verificar_provisioning()

        return novo_chip

    async def _migrar_conversas(self, chip_antigo_id: str, chip_novo_id: str):
        """
        Migra conversas ativas para novo chip.

        Atualiza tabela conversation_chips para manter continuidade.
        """
        # Atualizar mapeamento de conversas
        supabase.table("conversation_chips").update({
            "chip_id": chip_novo_id,
            "migrated_at": datetime.utcnow().isoformat(),
            "migrated_from": chip_antigo_id,
        }).eq("chip_id", chip_antigo_id).eq("active", True).execute()

        logger.info(
            f"[Orchestrator] Conversas migradas de {chip_antigo_id} para {chip_novo_id}"
        )

    # ════════════════════════════════════════════════════════════
    # AUTO-PROVISION
    # ════════════════════════════════════════════════════════════

    async def verificar_provisioning(self):
        """
        Verifica se precisa provisionar novos chips.
        """
        if not self.config or not self.config["auto_provision"]:
            return

        status = await self.obter_status_pool()

        # Calcular deficit
        deficit_warming = self.config["warmup_buffer"] - status["warming"]["count"]

        if deficit_warming > 0:
            logger.info(f"[Orchestrator] Provisionando {deficit_warming} chips")

            for _ in range(deficit_warming):
                await self.provisionar_chip()

    async def provisionar_chip(self, ddd: Optional[int] = None) -> Optional[Dict]:
        """
        Provisiona novo chip via Salvy.

        Args:
            ddd: DDD do numero (default da config)

        Returns:
            Chip criado ou None
        """
        if not self.config:
            await self.carregar_config()

        ddd = ddd or self.config["default_ddd"]

        try:
            # 1. Criar numero na Salvy
            salvy_number = await salvy_client.criar_numero(ddd=ddd)

            # 2. Criar registro no banco
            instance_name = f"julia-{salvy_number.phone_number[-8:]}"

            result = supabase.table("chips").insert({
                "telefone": salvy_number.phone_number,
                "salvy_id": salvy_number.id,
                "salvy_status": salvy_number.status,
                "salvy_created_at": salvy_number.created_at.isoformat(),
                "instance_name": instance_name,
                "status": "provisioned",
            }).execute()

            chip = result.data[0]

            # 3. TODO: Criar instancia Evolution
            # await evolution_client.criar_instancia(instance_name)

            logger.info(f"[Orchestrator] Chip provisionado: {salvy_number.phone_number}")

            await notificar_slack(
                f":sparkles: *Novo chip provisionado*: `{salvy_number.phone_number}`",
                canal="operacoes"
            )

            return chip

        except Exception as e:
            logger.error(f"[Orchestrator] Erro ao provisionar: {e}")
            await notificar_slack(
                f":x: *Erro ao provisionar chip*: {str(e)}",
                canal="alertas"
            )
            return None

    # ════════════════════════════════════════════════════════════
    # PROMOCAO AUTOMATICA
    # ════════════════════════════════════════════════════════════

    async def verificar_promocoes(self):
        """
        Verifica chips warming que podem ser promovidos para ready.

        Criterios:
        - Trust Score >= trust_min_for_ready
        - Dias de warmup >= warmup_days
        - Fase = 'operacao'
        """
        if not self.config:
            await self.carregar_config()

        result = supabase.table("chips").select("*").eq(
            "status", "warming"
        ).eq(
            "fase_warmup", "operacao"
        ).gte(
            "trust_score", self.config["trust_min_for_ready"]
        ).execute()

        for chip in result.data or []:
            # Verificar dias de warmup
            warming_started = datetime.fromisoformat(
                chip["warming_started_at"].replace("Z", "+00:00")
            )
            dias = (datetime.now(warming_started.tzinfo) - warming_started).days

            if dias >= self.config["warmup_days"]:
                # Promover para ready
                supabase.table("chips").update({
                    "status": "ready",
                    "ready_at": datetime.utcnow().isoformat(),
                }).eq("id", chip["id"]).execute()

                logger.info(
                    f"[Orchestrator] Chip {chip['telefone']} promovido para ready "
                    f"(Trust: {chip['trust_score']}, Dias: {dias})"
                )

                await notificar_slack(
                    f":white_check_mark: *Chip pronto*: `{chip['telefone']}` "
                    f"(Trust: {chip['trust_score']}) disponivel para producao",
                    canal="operacoes"
                )

    # ════════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ════════════════════════════════════════════════════════════

    async def executar_ciclo(self):
        """
        Executa um ciclo de verificacao do orchestrator.
        """
        logger.debug("[Orchestrator] Iniciando ciclo")

        # 1. Carregar config
        await self.carregar_config()

        # 2. Verificar chips degradados e substituir
        degradados = await self.verificar_chips_degradados()
        for chip in degradados:
            await self.substituir_chip(chip)

        # 3. Verificar promocoes warming -> ready
        await self.verificar_promocoes()

        # 4. Verificar provisioning
        await self.verificar_provisioning()

        # 5. Log status
        status = await self.obter_status_pool()
        logger.info(
            f"[Orchestrator] Pool: "
            f"producao={status['producao']['count']}/{status['producao']['min']}, "
            f"ready={status['ready']['count']}/{status['ready']['min']}, "
            f"warming={status['warming']['count']}/{status['warming']['buffer']}, "
            f"saude={status['saude']}"
        )

    async def iniciar(self, intervalo_segundos: int = 60):
        """
        Inicia loop do orchestrator.

        Args:
            intervalo_segundos: Intervalo entre ciclos
        """
        self._running = True
        logger.info("[Orchestrator] Iniciando...")

        while self._running:
            try:
                await self.executar_ciclo()
            except Exception as e:
                logger.error(f"[Orchestrator] Erro no ciclo: {e}")

            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o orchestrator."""
        self._running = False
        logger.info("[Orchestrator] Parando...")


# Singleton
chip_orchestrator = ChipOrchestrator()
```

### Migration Adicional

```sql
-- =====================================================
-- MAPEAMENTO CONVERSA -> CHIP
-- Garante continuidade (medico sempre no mesmo chip)
-- =====================================================
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

CREATE UNIQUE INDEX idx_conversation_chips_active ON conversation_chips(conversa_id)
    WHERE active = true;
CREATE INDEX idx_conversation_chips_chip ON conversation_chips(chip_id)
    WHERE active = true;


-- =====================================================
-- METRICAS AGREGADAS POR CHIP
-- Para dashboard e decisoes
-- =====================================================
CREATE TABLE chip_metrics_hourly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    hora TIMESTAMPTZ NOT NULL,

    -- Contadores
    msgs_enviadas INT DEFAULT 0,
    msgs_recebidas INT DEFAULT 0,
    erros INT DEFAULT 0,

    -- Tipos de mensagem
    prospeccoes INT DEFAULT 0,
    followups INT DEFAULT 0,
    respostas INT DEFAULT 0,

    -- Qualidade
    taxa_resposta DECIMAL(5,4),
    tempo_resposta_medio_segundos INT,

    UNIQUE(chip_id, hora)
);

CREATE INDEX idx_chip_metrics_hora ON chip_metrics_hourly(chip_id, hora DESC);


-- =====================================================
-- HISTORICO DE OPERACOES DO ORCHESTRATOR
-- =====================================================
CREATE TABLE orchestrator_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    operacao TEXT NOT NULL CHECK (operacao IN (
        'auto_replace',
        'auto_provision',
        'promotion_warming_ready',
        'promotion_ready_active',
        'demotion',
        'migration'
    )),

    chip_id UUID REFERENCES chips(id),
    chip_destino_id UUID REFERENCES chips(id),

    motivo TEXT,
    metadata JSONB DEFAULT '{}',

    sucesso BOOLEAN DEFAULT true,
    erro TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_orchestrator_ops_chip ON orchestrator_operations(chip_id, created_at DESC);
CREATE INDEX idx_orchestrator_ops_tipo ON orchestrator_operations(operacao, created_at DESC);
```

### DoD

- [ ] Pool Manager funcionando
- [ ] Auto-replace detectando e substituindo
- [ ] Migracao de conversas preservando continuidade
- [ ] Auto-provision via Salvy
- [ ] Promocao automatica warming -> ready
- [ ] Notificacoes Slack funcionando

---

## E02: Chip Selector

### Objetivo
Selecionar melhor chip para cada tipo de mensagem.

### Regras de Selecao

| Tipo Mensagem | Trust Min | Permissao | Criterio Desempate |
|---------------|-----------|-----------|-------------------|
| Prospeccao | 80 | pode_prospectar | Menor uso/hora |
| Follow-up | 60 | pode_followup | Menor uso/hora |
| Resposta | 40 | pode_responder | Chip da conversa |

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
from datetime import datetime, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

TipoMensagem = Literal["prospeccao", "followup", "resposta"]


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
        # 1. Se eh resposta e tem conversa, manter no mesmo chip
        if tipo_mensagem == "resposta" and conversa_id:
            chip_existente = await self._buscar_chip_conversa(conversa_id)
            if chip_existente and chip_existente["pode_responder"]:
                return chip_existente

        # 2. Buscar chips elegiveis
        chips = await self._buscar_chips_elegiveis(tipo_mensagem)

        if not chips:
            logger.warning(f"[ChipSelector] Nenhum chip disponivel para {tipo_mensagem}")
            return None

        # 3. Verificar historico com o contato
        if telefone_destino:
            chip_historico = await self._buscar_chip_historico(
                telefone_destino, chips
            )
            if chip_historico:
                return chip_historico

        # 4. Selecionar por menor uso
        chip_selecionado = await self._selecionar_menor_uso(chips)

        logger.debug(
            f"[ChipSelector] Selecionado {chip_selecionado['telefone']} "
            f"para {tipo_mensagem}"
        )

        return chip_selecionado

    async def _buscar_chip_conversa(self, conversa_id: str) -> Optional[Dict]:
        """Busca chip atualmente associado a conversa."""
        result = supabase.table("conversation_chips").select(
            "chips(*)"
        ).eq(
            "conversa_id", conversa_id
        ).eq(
            "active", True
        ).single().execute()

        if result.data:
            return result.data["chips"]
        return None

    async def _buscar_chips_elegiveis(self, tipo_mensagem: TipoMensagem) -> List[Dict]:
        """
        Busca chips que podem enviar o tipo de mensagem.
        """
        query = supabase.table("chips").select("*").eq("status", "active")

        # Filtrar por permissao
        if tipo_mensagem == "prospeccao":
            query = query.eq("pode_prospectar", True).gte("trust_score", 80)
        elif tipo_mensagem == "followup":
            query = query.eq("pode_followup", True).gte("trust_score", 60)
        else:  # resposta
            query = query.eq("pode_responder", True).gte("trust_score", 40)

        result = query.order("trust_score", desc=True).execute()

        # Filtrar por limite de uso
        chips_disponiveis = []
        for chip in result.data or []:
            if chip["msgs_enviadas_hoje"] < chip["limite_dia"]:
                # Verificar limite por hora
                uso_hora = await self._contar_msgs_ultima_hora(chip["id"])
                if uso_hora < chip["limite_hora"]:
                    chip["_uso_hora"] = uso_hora
                    chips_disponiveis.append(chip)

        return chips_disponiveis

    async def _buscar_chip_historico(
        self,
        telefone: str,
        chips: List[Dict]
    ) -> Optional[Dict]:
        """
        Verifica se algum dos chips ja conversou com este telefone.
        Preferir para manter consistencia.
        """
        chip_ids = [c["id"] for c in chips]

        result = supabase.table("chip_interactions").select(
            "chip_id"
        ).eq(
            "destinatario", telefone
        ).in_(
            "chip_id", chip_ids
        ).order(
            "created_at", desc=True
        ).limit(1).execute()

        if result.data:
            chip_id = result.data[0]["chip_id"]
            for chip in chips:
                if chip["id"] == chip_id:
                    logger.debug(
                        f"[ChipSelector] Usando chip com historico: {chip['telefone']}"
                    )
                    return chip

        return None

    async def _contar_msgs_ultima_hora(self, chip_id: str) -> int:
        """Conta mensagens enviadas na ultima hora."""
        uma_hora_atras = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        result = supabase.table("chip_interactions").select(
            "id", count="exact"
        ).eq(
            "chip_id", chip_id
        ).eq(
            "tipo", "msg_enviada"
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        return result.count or 0

    async def _selecionar_menor_uso(self, chips: List[Dict]) -> Dict:
        """Seleciona chip com menor uso na hora atual."""
        # Ordenar por uso da hora (menor primeiro), depois por Trust (maior primeiro)
        return sorted(
            chips,
            key=lambda c: (c.get("_uso_hora", 0), -c["trust_score"])
        )[0]

    async def registrar_envio(
        self,
        chip_id: str,
        conversa_id: str,
        tipo_mensagem: TipoMensagem,
        telefone_destino: str,
    ):
        """
        Registra envio para metricas e mapeamento.

        Args:
            chip_id: ID do chip usado
            conversa_id: ID da conversa
            tipo_mensagem: Tipo da mensagem
            telefone_destino: Telefone destino
        """
        # 1. Atualizar/criar mapeamento conversa-chip
        supabase.table("conversation_chips").upsert({
            "conversa_id": conversa_id,
            "chip_id": chip_id,
            "active": True,
        }, on_conflict="conversa_id").execute()

        # 2. Registrar interacao
        supabase.table("chip_interactions").insert({
            "chip_id": chip_id,
            "tipo": "msg_enviada",
            "destinatario": telefone_destino,
            "metadata": {"tipo_mensagem": tipo_mensagem},
        }).execute()

        # 3. Incrementar contadores
        supabase.rpc("incrementar_msgs_chip", {
            "p_chip_id": chip_id,
        }).execute()


# Singleton
chip_selector = ChipSelector()
```

**Funcao SQL para incrementar:**

```sql
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
CREATE OR REPLACE FUNCTION resetar_contadores_diarios()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE chips SET msgs_enviadas_hoje = 0, msgs_recebidas_hoje = 0;
END;
$$;
```

### DoD

- [ ] Selecao por tipo funcionando
- [ ] Continuidade de conversa preservada
- [ ] Historico de contato considerado
- [ ] Limites respeitados (hora/dia)
- [ ] Balanceamento de carga funcionando

---

## E03: Webhook Router

### Objetivo
Rotear webhooks da Evolution para chips corretos e manter continuidade.

### Implementacao

**Arquivo:** `app/api/routes/webhook_router.py`

```python
"""
Webhook Router - Roteamento multi-chip.

Recebe webhooks de multiplas instancias Evolution
e roteia para o processamento correto.
"""
from fastapi import APIRouter, Request, HTTPException
import logging

from app.services.chips.selector import chip_selector
from app.services.supabase import supabase
from app.pipeline.manager import pipeline_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/evolution", tags=["evolution"])


@router.post("/{instance_name}")
async def webhook_evolution(instance_name: str, request: Request):
    """
    Recebe webhook de uma instancia Evolution.

    O instance_name identifica qual chip recebeu a mensagem.
    """
    payload = await request.json()
    event_type = payload.get("event")

    logger.debug(f"[WebhookRouter] {instance_name}: {event_type}")

    # Buscar chip pelo instance_name
    result = supabase.table("chips").select("*").eq(
        "instance_name", instance_name
    ).single().execute()

    if not result.data:
        logger.error(f"[WebhookRouter] Instancia desconhecida: {instance_name}")
        raise HTTPException(404, "Instance not found")

    chip = result.data

    # Verificar se chip esta ativo
    if chip["status"] not in ["active", "warming"]:
        logger.warning(
            f"[WebhookRouter] Chip {instance_name} nao esta ativo "
            f"(status={chip['status']})"
        )
        # Ainda processa para nao perder mensagens
        # mas nao envia respostas

    # Rotear por tipo de evento
    if event_type == "messages.upsert":
        await processar_mensagem_recebida(chip, payload)
    elif event_type == "connection.update":
        await processar_conexao(chip, payload)
    elif event_type == "messages.update":
        await processar_status_mensagem(chip, payload)

    return {"status": "ok"}


async def processar_mensagem_recebida(chip: dict, payload: dict):
    """
    Processa mensagem recebida no chip.
    """
    data = payload.get("data", {})
    message = data.get("message", {})
    remote_jid = data.get("key", {}).get("remoteJid", "")

    # Extrair telefone
    telefone = remote_jid.split("@")[0]

    # Registrar interacao
    supabase.table("chip_interactions").insert({
        "chip_id": chip["id"],
        "tipo": "msg_recebida",
        "destinatario": telefone,
    }).execute()

    # Incrementar contador
    supabase.table("chips").update({
        "msgs_recebidas_total": chip["msgs_recebidas_total"] + 1,
        "msgs_recebidas_hoje": chip["msgs_recebidas_hoje"] + 1,
    }).eq("id", chip["id"]).execute()

    # Se chip esta em producao, processar via pipeline
    if chip["status"] == "active":
        # Adicionar contexto do chip ao payload
        payload["_chip"] = chip
        await pipeline_manager.processar(payload)


async def processar_conexao(chip: dict, payload: dict):
    """Atualiza status de conexao do chip."""
    state = payload.get("data", {}).get("state")

    connected = state == "open"

    supabase.table("chips").update({
        "evolution_connected": connected,
    }).eq("id", chip["id"]).execute()

    if not connected:
        logger.warning(f"[WebhookRouter] Chip desconectado: {chip['telefone']}")


async def processar_status_mensagem(chip: dict, payload: dict):
    """Processa atualizacao de status (entregue, lido, etc)."""
    # TODO: Atualizar metricas de delivery/read
    pass
```

### DoD

- [ ] Multi-instance routing funcionando
- [ ] Contexto do chip adicionado ao pipeline
- [ ] Contadores atualizando
- [ ] Conexao sendo monitorada

---

## E04: Health Monitor

### Objetivo
Monitorar chips em producao e detectar problemas proativamente.

### Implementacao

**Arquivo:** `app/services/chips/health_monitor.py`

```python
"""
Health Monitor - Monitoramento proativo de chips em producao.

Detecta:
- Taxa de resposta caindo
- Erros aumentando
- Desconexoes
- Trust Score degradando
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from app.services.supabase import supabase
from app.services.notificacoes import notificar_slack

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor de saude dos chips."""

    def __init__(self):
        self._running = False
        self.thresholds = {
            "taxa_resposta_minima": 0.20,  # 20%
            "erros_por_hora_max": 5,
            "trust_drop_alerta": 10,  # Queda de 10 pontos
        }

    async def verificar_saude_chips(self) -> List[Dict]:
        """
        Verifica saude de todos os chips ativos.

        Returns:
            Lista de alertas gerados
        """
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).execute()

        alertas = []

        for chip in result.data or []:
            chip_alertas = await self._verificar_chip(chip)
            alertas.extend(chip_alertas)

        return alertas

    async def _verificar_chip(self, chip: Dict) -> List[Dict]:
        """Verifica saude de um chip."""
        alertas = []

        # 1. Verificar conexao
        if not chip["evolution_connected"]:
            alertas.append({
                "chip_id": chip["id"],
                "tipo": "desconectado",
                "severity": "critical",
                "message": f"Chip {chip['telefone']} desconectado",
            })

        # 2. Verificar taxa de resposta
        if chip["taxa_resposta"] < self.thresholds["taxa_resposta_minima"]:
            alertas.append({
                "chip_id": chip["id"],
                "tipo": "taxa_resposta_baixa",
                "severity": "warning",
                "message": f"Taxa de resposta {chip['taxa_resposta']:.1%} < 20%",
            })

        # 3. Verificar erros
        if chip["erros_ultimas_24h"] > self.thresholds["erros_por_hora_max"] * 24:
            alertas.append({
                "chip_id": chip["id"],
                "tipo": "muitos_erros",
                "severity": "warning",
                "message": f"Erros nas 24h: {chip['erros_ultimas_24h']}",
            })

        # 4. Verificar queda de Trust Score
        queda = await self._verificar_queda_trust(chip)
        if queda >= self.thresholds["trust_drop_alerta"]:
            alertas.append({
                "chip_id": chip["id"],
                "tipo": "trust_caindo",
                "severity": "warning",
                "message": f"Trust Score caiu {queda} pontos nas ultimas 24h",
            })

        # Salvar alertas no banco
        for alerta in alertas:
            supabase.table("chip_alerts").insert(alerta).execute()

        return alertas

    async def _verificar_queda_trust(self, chip: Dict) -> int:
        """Verifica queda de Trust Score nas ultimas 24h."""
        ontem = (datetime.utcnow() - timedelta(days=1)).isoformat()

        result = supabase.table("chip_trust_history").select(
            "score"
        ).eq(
            "chip_id", chip["id"]
        ).gte(
            "recorded_at", ontem
        ).order(
            "recorded_at", desc=False
        ).limit(1).execute()

        if result.data:
            score_ontem = result.data[0]["score"]
            return score_ontem - chip["trust_score"]

        return 0

    async def gerar_relatorio(self) -> Dict:
        """
        Gera relatorio de saude do pool.

        Returns:
            {
                "timestamp": "...",
                "pool": {...},
                "alertas_ativos": [...],
                "chips_saudaveis": N,
                "chips_atencao": N,
                "chips_criticos": N
            }
        """
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).execute()

        chips = result.data or []

        # Classificar por saude
        saudaveis = [c for c in chips if c["trust_score"] >= 80]
        atencao = [c for c in chips if 60 <= c["trust_score"] < 80]
        criticos = [c for c in chips if c["trust_score"] < 60]

        # Buscar alertas nao resolvidos
        alertas = supabase.table("chip_alerts").select("*").eq(
            "resolved", False
        ).execute()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "pool": {
                "total": len(chips),
                "saudaveis": len(saudaveis),
                "atencao": len(atencao),
                "criticos": len(criticos),
            },
            "alertas_ativos": alertas.data or [],
            "trust_medio": sum(c["trust_score"] for c in chips) / len(chips) if chips else 0,
            "msgs_hoje": sum(c["msgs_enviadas_hoje"] for c in chips),
        }

    async def iniciar(self, intervalo_segundos: int = 300):
        """Inicia monitoramento continuo (default 5 min)."""
        self._running = True
        logger.info("[HealthMonitor] Iniciando...")

        while self._running:
            try:
                alertas = await self.verificar_saude_chips()

                # Notificar alertas criticos
                criticos = [a for a in alertas if a["severity"] == "critical"]
                if criticos:
                    await notificar_slack(
                        f":rotating_light: *{len(criticos)} alertas criticos*\n" +
                        "\n".join([f"- {a['message']}" for a in criticos]),
                        canal="alertas"
                    )

            except Exception as e:
                logger.error(f"[HealthMonitor] Erro: {e}")

            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o monitor."""
        self._running = False


# Singleton
health_monitor = HealthMonitor()
```

### DoD

- [ ] Monitoramento de conexao
- [ ] Deteccao de queda de Trust
- [ ] Alertas sendo criados
- [ ] Notificacoes Slack
- [ ] Relatorio de saude

---

## E05: Dashboard Unificado

### Objetivo
Interface visual para Warmer + Producao + Metricas.

### Endpoints API

```python
# app/api/routes/dashboard.py

@router.get("/pool/status")
async def get_pool_status():
    """Retorna status completo do pool."""
    return await chip_orchestrator.obter_status_pool()

@router.get("/pool/health")
async def get_pool_health():
    """Retorna relatorio de saude."""
    return await health_monitor.gerar_relatorio()

@router.get("/chips")
async def list_chips(
    status: Optional[str] = None,
    trust_min: Optional[int] = None,
):
    """Lista chips com filtros."""
    query = supabase.table("chips").select("*")
    if status:
        query = query.eq("status", status)
    if trust_min:
        query = query.gte("trust_score", trust_min)
    return query.execute().data

@router.get("/chips/{chip_id}/metrics")
async def get_chip_metrics(chip_id: str, periodo: str = "24h"):
    """Metricas detalhadas de um chip."""
    ...

@router.get("/chips/{chip_id}/history")
async def get_chip_history(chip_id: str):
    """Historico de transicoes e Trust Score."""
    ...

@router.post("/chips/{chip_id}/pause")
async def pause_chip(chip_id: str):
    """Pausa chip manualmente."""
    ...

@router.post("/chips/{chip_id}/resume")
async def resume_chip(chip_id: str):
    """Resume chip pausado."""
    ...

@router.get("/alertas")
async def list_alertas(resolved: bool = False):
    """Lista alertas."""
    ...

@router.post("/alertas/{alerta_id}/resolve")
async def resolve_alerta(alerta_id: str):
    """Marca alerta como resolvido."""
    ...
```

### DoD

- [ ] Endpoints de status
- [ ] Endpoints de chips
- [ ] Endpoints de alertas
- [ ] Acoes manuais (pause/resume)

---

## E06: Webhook Robustness

### Objetivo
Garantir que nenhuma mensagem seja perdida.

### Implementacao

```python
# Dead Letter Queue para webhooks falhos
# Idempotency via message_id
# Retry com backoff exponencial
```

### DoD

- [ ] DLQ funcionando
- [ ] Idempotency implementada
- [ ] Retry com backoff
- [ ] Metricas de falhas

---

## E07: Migracao Anunciada

### Objetivo
Quando chip degrada (mas ainda funciona), notificar o medico da troca de numero para manter transparencia e confianca.

### Regras

**Quando usar:**
- Chip degradando (Trust baixo, warnings)
- Chip ainda funcional (nao banido)
- Medico tem historico de respostas (relacionamento existe)
- NAO e prospeccao fria (ja houve conversas)

**Quando NAO usar:**
- Ban abrupto (nao da tempo)
- Prospeccao fria (medico nao conhece o numero)
- Chip ja desconectado

### Fluxo

```
1. Chip A (degradado) envia:
   "Oi Dr Joao! Vou trocar de numero essa semana,
    me salva esse novo aqui: 11999...
    Continuo te avisando das vagas por la!"

2. Aguarda 24-48h (medico salva o numero)

3. Chip B (novo) envia:
   "Oi Dr Joao, sou a Julia! Continuando nossa
    conversa sobre aquela vaga de PS..."

4. Chip A desativado apos confirmacao de Chip B
```

### Implementacao

```python
async def migrar_conversa_anunciada(
    chip_antigo: Dict,
    chip_novo: Dict,
    medico_id: str,
) -> bool:
    """
    Migra conversa com aviso ao medico.

    Returns:
        True se iniciou migracao com sucesso
    """
    # 1. Verificar se medico tem historico
    affinity = await buscar_affinity(medico_id, chip_antigo["id"])
    if not affinity or affinity["msgs_trocadas"] < 2:
        # Prospeccao fria, pular aviso
        return await migrar_conversa_silenciosa(chip_antigo, chip_novo, medico_id)

    # 2. Buscar dados do medico
    medico = await buscar_medico_por_id(medico_id)

    # 3. Gerar mensagem de aviso
    mensagem = await gerar_mensagem_troca_numero(
        nome=medico.get("primeiro_nome", ""),
        numero_novo=chip_novo["telefone"],
    )

    # 4. Enviar pelo chip antigo
    await enviar_mensagem(
        instance=chip_antigo["instance_name"],
        telefone=medico["telefone"],
        texto=mensagem,
    )

    # 5. Agendar continuacao em 24-48h
    await agendar_continuacao_migracao(
        chip_novo_id=chip_novo["id"],
        medico_id=medico_id,
        delay_horas=random.randint(24, 48),
    )

    return True
```

### DoD

- [ ] Deteccao de relacionamento (affinity > 2 msgs)
- [ ] Template de mensagem de aviso natural
- [ ] Agendamento de continuacao
- [ ] Mensagem de continuacao pelo novo chip
- [ ] Logs de migracao para auditoria

---

## Cronograma Sprint 26

### Semana 1: Orchestrator Core
```
Dia 1-2: E01 Chip Orchestrator (8h)
Dia 3-4: E02 Chip Selector (6h)
Dia 5: E03 Webhook Router (6h)
```

### Semana 2: Monitor + Dashboard
```
Dia 1-2: E04 Health Monitor (5h)
Dia 3-4: E05 Dashboard API (6h)
Dia 5: E06 Webhook Robustness (4h)
```

### Semana 3: Integracao + Testes
```
Dia 1: E07 Migracao Anunciada (4h)
Dia 2-3: Integracao com Julia existente
Dia 4-5: Testes end-to-end e ajustes
```

---

## Entregavel

Ao final da Sprint 26:
- [ ] Pool de N chips em producao
- [ ] Auto-replace funcionando
- [ ] Ready pool dinamico (ajusta por taxa de degradacao)
- [ ] Chip Selector distribuindo carga
- [ ] Chip Affinity (medico fica no mesmo chip)
- [ ] Cooldown (pausas de 1-2h apos 4h ativo)
- [ ] Migracao Anunciada (notifica medico antes de trocar)
- [ ] Continuidade de conversa garantida
- [ ] Health Monitor alertando proativamente
- [ ] Dashboard com visao completa
- [ ] Zero perda de mensagens

---

## Integracao com Julia Existente

### Mudancas Necessarias

1. **Pipeline**: Adicionar contexto do chip
2. **Envio de mensagens**: Usar Chip Selector
3. **Campanhas**: Distribuir entre chips
4. **Metricas**: Agregar por chip

### Exemplo de Uso

```python
# Antes (1 chip fixo)
await enviar_mensagem(telefone, texto)

# Depois (multi-chip)
chip = await chip_selector.selecionar_chip(
    tipo_mensagem="prospeccao",
    telefone_destino=telefone
)
await enviar_mensagem(telefone, texto, instance=chip["instance_name"])
await chip_selector.registrar_envio(
    chip_id=chip["id"],
    conversa_id=conversa.id,
    tipo_mensagem="prospeccao",
    telefone_destino=telefone
)
```

---

*Sprint criada em 30/12/2025*
