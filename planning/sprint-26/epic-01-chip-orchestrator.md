# Epic 01: Chip Orchestrator

## Objetivo

Implementar **orquestrador central** do pool de chips que gerencia:
- Pool de chips (producao, ready, warming)
- Auto-replace quando chip degrada
- Auto-provision quando pool baixo
- Promocao automatica (warming -> ready -> active)

## Contexto

O Chip Orchestrator e o "cerebro" do sistema multi-chip, responsavel por:
1. Manter pool saudavel (N chips em producao)
2. Substituir chips automaticamente
3. Provisionar novos chips via Salvy
4. Promover chips do warming para producao

---

## Story 1.1: Pool Manager

### Objetivo
Gerenciar estado do pool de chips.

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
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from app.services.supabase import supabase
from app.services.salvy.provisioning import provisionar_chip, cancelar_chip
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
        Retorna status completo do pool.

        Returns:
            {
                "producao": {"count": N, "min": M, "max": X, "chips": [...]},
                "ready": {"count": N, "min": M, "chips": [...]},
                "warming": {"count": N, "buffer": M, "chips": [...]},
                "degraded": {"count": N, "chips": [...]},
                "saude": "saudavel" | "atencao" | "critico"
            }
        """
        if not self.config:
            await self.carregar_config()

        # Buscar todos os chips relevantes
        result = supabase.table("chips").select(
            "id, telefone, instance_name, status, trust_score, trust_level, "
            "fase_warmup, warming_started_at, msgs_enviadas_hoje"
        ).in_(
            "status", ["warming", "ready", "active", "degraded"]
        ).execute()

        chips = result.data or []

        # Agrupar por status
        producao = [c for c in chips if c["status"] == "active"]
        ready = [c for c in chips if c["status"] == "ready"]
        warming = [c for c in chips if c["status"] == "warming"]
        degraded = [c for c in chips if c["status"] == "degraded"]

        # Determinar saude do pool
        saude = "saudavel"
        if len(producao) < self.config["producao_min"]:
            saude = "critico"
        elif len(ready) < self.config["ready_min"]:
            saude = "atencao"
        elif len(warming) < self.config["warmup_buffer"] // 2:
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
            "totais": {
                "total_chips": len(chips),
                "trust_medio": sum(c["trust_score"] for c in producao) / len(producao) if producao else 0,
            }
        }

    async def verificar_deficits(self) -> Dict:
        """
        Verifica deficits no pool.

        Returns:
            {"producao": N, "ready": N, "warming": N}
        """
        status = await self.obter_status_pool()

        return {
            "producao": max(0, self.config["producao_min"] - status["producao"]["count"]),
            "ready": max(0, self.config["ready_min"] - status["ready"]["count"]),
            "warming": max(0, self.config["warmup_buffer"] - status["warming"]["count"]),
        }
```

### DoD

- [ ] Status do pool funcionando
- [ ] Contagem correta por status
- [ ] Calculo de saude

---

## Story 1.2: Auto-Replace

### Objetivo
Detectar e substituir chips degradados automaticamente.

### Implementacao

```python
    # ════════════════════════════════════════════════════════════
    # AUTO-REPLACE
    # ════════════════════════════════════════════════════════════

    async def verificar_chips_degradados(self) -> List[Dict]:
        """
        Identifica chips ativos que precisam ser substituidos.

        Criterios:
        - Trust Score abaixo do threshold degradado
        - Status 'banned'
        - Desconectado por mais de 30 min
        """
        if not self.config:
            await self.carregar_config()

        threshold = self.config["trust_degraded_threshold"]

        # Chips ativos com trust baixo
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).lt(
            "trust_score", threshold
        ).execute()

        degradados = result.data or []

        # Chips desconectados
        desconectados = supabase.table("chips").select("*").eq(
            "status", "active"
        ).eq(
            "evolution_connected", False
        ).execute()

        for chip in desconectados.data or []:
            if chip not in degradados:
                degradados.append(chip)

        return degradados

    async def substituir_chip(self, chip_degradado: Dict) -> Optional[Dict]:
        """
        Substitui chip degradado por um ready.

        Fluxo:
        1. Buscar melhor chip ready
        2. Migrar conversas ativas
        3. Promover novo chip para active
        4. Rebaixar chip degradado

        Args:
            chip_degradado: Chip a ser substituido

        Returns:
            Novo chip promovido ou None se nao houver ready
        """
        logger.warning(
            f"[Orchestrator] Iniciando substituicao de {chip_degradado['telefone']} "
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
            logger.error("[Orchestrator] Nenhum chip ready disponivel para substituicao!")

            await notificar_slack(
                f":rotating_light: *CRITICO*: Chip `{chip_degradado['telefone']}` degradado "
                f"(Trust: {chip_degradado['trust_score']}) mas NAO HA CHIPS READY!\n"
                f"Pool precisa de atencao imediata.",
                canal="alertas"
            )
            return None

        novo_chip = result.data[0]

        # 2. Migrar conversas ativas
        conversas_migradas = await self._migrar_conversas(
            chip_degradado["id"],
            novo_chip["id"]
        )

        # 3. Promover novo chip
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("chips").update({
            "status": "active",
            "promoted_to_active_at": now,
        }).eq("id", novo_chip["id"]).execute()

        # 4. Rebaixar chip degradado
        supabase.table("chips").update({
            "status": "degraded",
        }).eq("id", chip_degradado["id"]).execute()

        # 5. Registrar operacao
        supabase.table("orchestrator_operations").insert({
            "operacao": "auto_replace",
            "chip_id": chip_degradado["id"],
            "chip_destino_id": novo_chip["id"],
            "motivo": f"Trust Score {chip_degradado['trust_score']} < {self.config['trust_degraded_threshold']}",
            "metadata": {
                "conversas_migradas": conversas_migradas,
                "trust_degradado": chip_degradado["trust_score"],
                "trust_novo": novo_chip["trust_score"],
            },
        }).execute()

        # 6. Notificar
        await notificar_slack(
            f":arrows_counterclockwise: *Auto-Replace executado*\n"
            f"- Degradado: `{chip_degradado['telefone']}` (Trust: {chip_degradado['trust_score']})\n"
            f"- Promovido: `{novo_chip['telefone']}` (Trust: {novo_chip['trust_score']})\n"
            f"- Conversas migradas: {conversas_migradas}",
            canal="operacoes"
        )

        logger.info(
            f"[Orchestrator] Substituicao concluida: "
            f"{chip_degradado['telefone']} -> {novo_chip['telefone']}"
        )

        return novo_chip

    async def _migrar_conversas(self, chip_antigo_id: str, chip_novo_id: str) -> int:
        """
        Migra conversas ativas para novo chip.

        Args:
            chip_antigo_id: Chip de origem
            chip_novo_id: Chip de destino

        Returns:
            Numero de conversas migradas
        """
        now = datetime.now(timezone.utc).isoformat()

        # Buscar conversas ativas
        result = supabase.table("conversation_chips").select("id").eq(
            "chip_id", chip_antigo_id
        ).eq(
            "active", True
        ).execute()

        count = len(result.data or [])

        if count > 0:
            # Atualizar todas de uma vez
            supabase.table("conversation_chips").update({
                "chip_id": chip_novo_id,
                "migrated_at": now,
                "migrated_from": chip_antigo_id,
            }).eq(
                "chip_id", chip_antigo_id
            ).eq(
                "active", True
            ).execute()

        logger.info(f"[Orchestrator] {count} conversas migradas")

        return count
```

### DoD

- [ ] Deteccao de degradados funcionando
- [ ] Substituicao completa
- [ ] Migracao de conversas
- [ ] Notificacoes Slack

---

## Story 1.3: Auto-Provision

### Objetivo
Provisionar novos chips automaticamente quando pool baixo.

### Implementacao

```python
    # ════════════════════════════════════════════════════════════
    # AUTO-PROVISION
    # ════════════════════════════════════════════════════════════

    async def verificar_provisioning(self):
        """
        Verifica se precisa provisionar novos chips.

        Provisiona quando:
        - warming < warmup_buffer
        - ready < ready_min (e nao ha chips warming suficientes)
        """
        if not self.config or not self.config["auto_provision"]:
            return

        deficits = await self.verificar_deficits()

        # Prioridade: manter warming buffer
        if deficits["warming"] > 0:
            logger.info(f"[Orchestrator] Provisionando {deficits['warming']} chips (warming deficit)")

            for _ in range(min(deficits["warming"], 3)):  # Max 3 por ciclo
                await self._provisionar_novo_chip()

    async def _provisionar_novo_chip(self, ddd: Optional[int] = None) -> Optional[Dict]:
        """
        Provisiona novo chip via Salvy.

        Args:
            ddd: DDD desejado (usa default se nao especificado)

        Returns:
            Chip criado ou None
        """
        ddd = ddd or self.config["default_ddd"]

        try:
            chip = await provisionar_chip(ddd=ddd)

            if chip:
                # Registrar operacao
                supabase.table("orchestrator_operations").insert({
                    "operacao": "auto_provision",
                    "chip_id": chip["id"],
                    "motivo": "Pool buffer baixo",
                    "metadata": {"ddd": ddd},
                }).execute()

            return chip

        except Exception as e:
            logger.error(f"[Orchestrator] Erro ao provisionar: {e}")

            await notificar_slack(
                f":x: *Erro no auto-provisioning*: {str(e)}",
                canal="alertas"
            )

            return None
```

### DoD

- [ ] Deteccao de deficit funcionando
- [ ] Provisioning via Salvy
- [ ] Limite por ciclo

---

## Story 1.4: Promocao Automatica

### Objetivo
Promover chips warming -> ready -> active automaticamente.

### Implementacao

```python
    # ════════════════════════════════════════════════════════════
    # PROMOCAO AUTOMATICA
    # ════════════════════════════════════════════════════════════

    async def verificar_promocoes_warming_ready(self):
        """
        Verifica chips warming que podem ser promovidos para ready.

        Criterios:
        - Trust Score >= trust_min_for_ready
        - Dias de warmup >= warmup_days
        - Fase = 'operacao'
        """
        if not self.config:
            await self.carregar_config()

        # Buscar candidatos
        result = supabase.table("chips").select("*").eq(
            "status", "warming"
        ).eq(
            "fase_warmup", "operacao"
        ).gte(
            "trust_score", self.config["trust_min_for_ready"]
        ).execute()

        promovidos = 0

        for chip in result.data or []:
            # Verificar dias de warmup
            if not chip.get("warming_started_at"):
                continue

            warming_started = datetime.fromisoformat(
                chip["warming_started_at"].replace("Z", "+00:00")
            )
            dias = (datetime.now(timezone.utc) - warming_started).days

            if dias >= self.config["warmup_days"]:
                # Promover para ready
                now = datetime.now(timezone.utc).isoformat()

                supabase.table("chips").update({
                    "status": "ready",
                    "ready_at": now,
                }).eq("id", chip["id"]).execute()

                # Registrar
                supabase.table("orchestrator_operations").insert({
                    "operacao": "promotion_warming_ready",
                    "chip_id": chip["id"],
                    "motivo": f"Trust {chip['trust_score']} >= {self.config['trust_min_for_ready']}, {dias} dias",
                }).execute()

                promovidos += 1

                logger.info(
                    f"[Orchestrator] Chip {chip['telefone']} promovido para READY "
                    f"(Trust: {chip['trust_score']}, Dias: {dias})"
                )

        if promovidos > 0:
            await notificar_slack(
                f":white_check_mark: *{promovidos} chip(s) promovido(s) para READY*\n"
                f"Disponiveis para producao quando necessario.",
                canal="operacoes"
            )

        return promovidos

    async def verificar_promocoes_ready_active(self):
        """
        Verifica se precisa promover chips ready para active.

        Apenas quando producao < producao_min.
        """
        status = await self.obter_status_pool()

        deficit = self.config["producao_min"] - status["producao"]["count"]

        if deficit <= 0:
            return 0  # Pool de producao ok

        # Buscar melhores ready
        result = supabase.table("chips").select("*").eq(
            "status", "ready"
        ).order(
            "trust_score", desc=True
        ).limit(deficit).execute()

        promovidos = 0
        now = datetime.now(timezone.utc).isoformat()

        for chip in result.data or []:
            supabase.table("chips").update({
                "status": "active",
                "promoted_to_active_at": now,
            }).eq("id", chip["id"]).execute()

            supabase.table("orchestrator_operations").insert({
                "operacao": "promotion_ready_active",
                "chip_id": chip["id"],
                "motivo": f"Deficit de producao: {deficit}",
            }).execute()

            promovidos += 1

            logger.info(f"[Orchestrator] Chip {chip['telefone']} promovido para ACTIVE")

        if promovidos > 0:
            await notificar_slack(
                f":rocket: *{promovidos} chip(s) promovido(s) para PRODUCAO*\n"
                f"Pool de producao normalizado.",
                canal="operacoes"
            )

        return promovidos
```

### DoD

- [ ] Promocao warming -> ready
- [ ] Promocao ready -> active
- [ ] Verificacao de criterios

---

## Story 1.5: Loop Principal

### Objetivo
Executar ciclo de verificacao periodicamente.

### Implementacao

```python
    # ════════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ════════════════════════════════════════════════════════════

    async def executar_ciclo(self):
        """
        Executa um ciclo completo de verificacao.

        Ordem:
        1. Carregar config
        2. Verificar e substituir degradados
        3. Verificar promocoes warming -> ready
        4. Verificar promocoes ready -> active
        5. Verificar provisioning
        6. Log status
        """
        logger.debug("[Orchestrator] Iniciando ciclo")

        try:
            # 1. Carregar config
            await self.carregar_config()

            # 2. Verificar chips degradados e substituir
            degradados = await self.verificar_chips_degradados()
            for chip in degradados:
                await self.substituir_chip(chip)

            # 3. Verificar promocoes warming -> ready
            await self.verificar_promocoes_warming_ready()

            # 4. Verificar promocoes ready -> active
            await self.verificar_promocoes_ready_active()

            # 5. Verificar provisioning
            await self.verificar_provisioning()

            # 6. Log status
            status = await self.obter_status_pool()
            logger.info(
                f"[Orchestrator] Pool: "
                f"producao={status['producao']['count']}/{status['producao']['min']}, "
                f"ready={status['ready']['count']}/{status['ready']['min']}, "
                f"warming={status['warming']['count']}/{status['warming']['buffer']}, "
                f"saude={status['saude']}"
            )

            # Alertar se saude nao ok
            if status["saude"] == "critico":
                await notificar_slack(
                    f":rotating_light: *Pool em estado CRITICO*\n"
                    f"- Producao: {status['producao']['count']}/{status['producao']['min']}\n"
                    f"- Ready: {status['ready']['count']}/{status['ready']['min']}\n"
                    f"- Warming: {status['warming']['count']}/{status['warming']['buffer']}",
                    canal="alertas"
                )

        except Exception as e:
            logger.error(f"[Orchestrator] Erro no ciclo: {e}")

    async def iniciar(self, intervalo_segundos: int = 60):
        """
        Inicia loop do orchestrator.

        Args:
            intervalo_segundos: Intervalo entre ciclos (default 1 min)
        """
        self._running = True
        logger.info(f"[Orchestrator] Iniciando com intervalo de {intervalo_segundos}s")

        while self._running:
            await self.executar_ciclo()
            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o orchestrator."""
        self._running = False
        logger.info("[Orchestrator] Parando...")


# Singleton
chip_orchestrator = ChipOrchestrator()
```

### DoD

- [ ] Ciclo completo funcionando
- [ ] Ordem de operacoes correta
- [ ] Alertas de saude
- [ ] Logging adequado

---

## Story 1.6: Migration orchestrator_operations

### Objetivo
Tabela para historico de operacoes.

### Migration

```sql
-- Migration: create_orchestrator_operations
-- Sprint 26 - E01 - Historico de operacoes

CREATE TABLE orchestrator_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    operacao TEXT NOT NULL CHECK (operacao IN (
        'auto_replace',
        'auto_provision',
        'promotion_warming_ready',
        'promotion_ready_active',
        'demotion',
        'migration',
        'cancel'
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
CREATE INDEX idx_orchestrator_ops_time ON orchestrator_operations(created_at DESC);

COMMENT ON TABLE orchestrator_operations IS 'Historico de operacoes do Orchestrator';
```

### DoD

- [ ] Tabela criada
- [ ] Indices otimizados

---

## Checklist do Epico

- [ ] **E01.1** - Pool Manager
- [ ] **E01.2** - Auto-Replace
- [ ] **E01.3** - Auto-Provision
- [ ] **E01.4** - Promocao Automatica
- [ ] **E01.5** - Loop Principal
- [ ] **E01.6** - Migration
- [ ] Testes de integracao
- [ ] Documentacao atualizada

---

## Diagrama: Fluxo do Orchestrator

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHIP ORCHESTRATOR LOOP                        │
│                      (a cada 60s)                                │
└─────────────────────────────────────────────────────────────────┘

     ┌─────────────────────────────────────────────────────────┐
     │                  1. CARREGAR CONFIG                      │
     │    pool_config: producao_min, ready_min, warmup_buffer  │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────┐
     │              2. VERIFICAR DEGRADADOS                     │
     │                                                          │
     │   Criterios:                                             │
     │   - Trust < trust_degraded_threshold                     │
     │   - evolution_connected = false (>30min)                 │
     │   - status = 'banned'                                    │
     │                                                          │
     │   Acao: substituir_chip()                               │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────┐
     │           3. PROMOCOES WARMING -> READY                  │
     │                                                          │
     │   Criterios:                                             │
     │   - Trust >= trust_min_for_ready (85)                   │
     │   - dias >= warmup_days (21)                            │
     │   - fase = 'operacao'                                   │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────┐
     │           4. PROMOCOES READY -> ACTIVE                   │
     │                                                          │
     │   Quando: producao < producao_min                        │
     │   Criterio: maior Trust Score                           │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────┐
     │              5. AUTO-PROVISIONING                        │
     │                                                          │
     │   Quando: warming < warmup_buffer                        │
     │   Acao: provisionar_chip() via Salvy                    │
     │   Limite: 3 por ciclo                                   │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
     ┌─────────────────────────────────────────────────────────┐
     │                 6. LOG E ALERTAS                         │
     │                                                          │
     │   Se saude = "critico": notificar_slack()               │
     └─────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                          sleep(60s)
                                 │
                                 └─────────────────────┐
                                                       │
                                                       ▼
                                               (volta ao inicio)
```
