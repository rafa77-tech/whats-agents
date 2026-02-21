# EPIC 67.1: Quality Monitor Service

## Contexto

A Meta atribui quality ratings (GREEN/YELLOW/RED) aos numeros de telefone e templates. Quando quality cai para RED, o numero pode ser restringido ou banido. Hoje a unica protecao e o filtro no `selector.py` que exclui chips RED — mas e reativo (so detecta quando tenta enviar). Precisamos de monitoramento proativo.

## Escopo

- **Incluido**: Polling da Quality API, historico, auto-degradacao, auto-recovery, alerts Slack, kill switch
- **Excluido**: Quality prediction com ML (Sprint 70+), dashboard UI (Sprint 69)

---

## Tarefa 1: Migration — Tabela `meta_quality_history`

### Objetivo

Criar tabela para armazenar historico de quality ratings.

### Schema

```sql
CREATE TABLE meta_quality_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES julia_chips(id),
    waba_id TEXT NOT NULL,
    quality_rating TEXT NOT NULL,  -- GREEN, YELLOW, RED
    previous_rating TEXT,          -- Rating anterior (para detectar transicao)
    messaging_tier TEXT,           -- TIER_1K, TIER_10K, TIER_100K, TIER_UNLIMITED
    source TEXT NOT NULL DEFAULT 'polling',  -- polling, webhook, manual
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_meta_quality_history_chip_id ON meta_quality_history(chip_id);
CREATE INDEX idx_meta_quality_history_checked_at ON meta_quality_history(checked_at DESC);
CREATE INDEX idx_meta_quality_history_rating ON meta_quality_history(quality_rating);

-- Indice para consulta rapida: ultimo rating de cada chip
CREATE INDEX idx_meta_quality_history_chip_latest
    ON meta_quality_history(chip_id, checked_at DESC);
```

### Testes Obrigatorios

- [ ] Migration aplica sem erro
- [ ] Tabela criada com todas as colunas
- [ ] Indices criados

### Definition of Done

- [ ] Migration aplicada via Supabase MCP
- [ ] Schema verificado

---

## Tarefa 2: Quality Monitor Service

### Objetivo

Servico que consulta a Meta Quality API e reage a mudancas de quality.

### Arquivo: `app/services/meta/quality_monitor.py`

### Implementacao

```python
"""
Quality Monitor Service para chips Meta.

Sprint 67 - Epic 67.1: Monitoramento proativo de quality rating.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaQualityMonitor:
    """
    Monitora quality rating dos chips Meta via API.

    Funcionalidades:
    - Polling periodico da Meta API
    - Deteccao de transicoes (GREEN->YELLOW, YELLOW->RED)
    - Auto-degradacao quando quality cai
    - Auto-recovery quando quality volta
    - Alertas Slack
    - Kill switch por WABA
    """

    def __init__(self):
        self.graph_api_version = settings.META_GRAPH_API_VERSION

    async def verificar_quality_chips(self) -> dict:
        """
        Verifica quality de TODOS os chips Meta ativos.

        Returns:
            dict com summary: {total, green, yellow, red, transicoes}
        """
        # 1. Buscar todos chips Meta ativos
        # 2. Para cada chip, consultar API
        # 3. Comparar com ultimo rating
        # 4. Se mudou, registrar transicao
        # 5. Se degradou, acionar auto-degrade
        # 6. Se melhorou, acionar auto-recovery
        pass

    async def _consultar_quality_api(self, waba_id: str, access_token: str) -> dict:
        """
        Consulta quality rating de um WABA via Graph API.

        Endpoint: GET /{waba_id}?fields=quality_rating,messaging_limit
        """
        pass

    async def _registrar_quality(
        self,
        chip_id: str,
        waba_id: str,
        quality_rating: str,
        previous_rating: Optional[str],
        messaging_tier: Optional[str],
        source: str = "polling",
    ) -> None:
        """Registra quality no historico."""
        pass

    async def _obter_ultimo_rating(self, chip_id: str) -> Optional[str]:
        """Busca ultimo rating registrado de um chip."""
        pass

    async def _auto_degradar_chip(self, chip_id: str, quality: str) -> None:
        """
        Degrada chip automaticamente.

        RED -> desativa chip (degradado=True, motivo='meta_quality_red')
        YELLOW -> reduz prioridade (trust_score *= 0.5)
        """
        pass

    async def _auto_recovery_chip(self, chip_id: str, quality: str) -> None:
        """
        Recupera chip automaticamente.

        GREEN (vindo de YELLOW) -> restaura trust_score
        GREEN (vindo de RED) -> reativa chip mas com trust_score baixo
        """
        pass

    async def _alertar_slack(
        self,
        chip_id: str,
        chip_nome: str,
        transicao: str,  # ex: "GREEN -> YELLOW"
        waba_id: str,
    ) -> None:
        """Envia alerta de quality para Slack."""
        pass

    async def _detectar_padrao_degradacao(self, waba_id: str) -> bool:
        """
        Detecta padrao de degradacao (>= 2 chips YELLOW na mesma WABA).

        Diferencial agentico: reduz volume ANTES de virar RED.

        Returns:
            True se padrao detectado
        """
        pass

    async def kill_switch_waba(self, waba_id: str, motivo: str) -> dict:
        """
        Desativa TODOS os chips de uma WABA.

        Returns:
            dict com chips_afetados e status
        """
        pass

    async def obter_historico(
        self,
        chip_id: Optional[str] = None,
        waba_id: Optional[str] = None,
        limite: int = 50,
    ) -> list[dict]:
        """Retorna historico de quality ratings."""
        pass


quality_monitor = MetaQualityMonitor()
```

### Testes Obrigatorios

**Unitarios (`tests/services/meta/test_quality_monitor.py`):**

- [ ] `test_verificar_quality_chips_todos_green` — Todos chips GREEN, sem acoes
- [ ] `test_verificar_quality_chips_transicao_yellow` — GREEN->YELLOW detectado, alert enviado
- [ ] `test_verificar_quality_chips_transicao_red` — YELLOW->RED detectado, chip degradado
- [ ] `test_verificar_quality_chips_recovery_green` — RED->GREEN detectado, chip recuperado
- [ ] `test_consultar_quality_api_sucesso` — Graph API retorna quality_rating
- [ ] `test_consultar_quality_api_token_invalido` — 401 tratado gracefully
- [ ] `test_consultar_quality_api_rate_limit` — 429 com retry
- [ ] `test_registrar_quality_historico` — Insercao no banco
- [ ] `test_obter_ultimo_rating_existente` — Retorna ultimo rating
- [ ] `test_obter_ultimo_rating_nenhum` — Retorna None se nunca checado
- [ ] `test_auto_degradar_red` — Chip desativado, motivo registrado
- [ ] `test_auto_degradar_yellow` — Trust score reduzido
- [ ] `test_auto_recovery_de_yellow` — Trust score restaurado
- [ ] `test_auto_recovery_de_red` — Chip reativado com trust baixo
- [ ] `test_detectar_padrao_degradacao` — 2+ chips YELLOW na mesma WABA
- [ ] `test_kill_switch_waba` — Todos chips desativados
- [ ] `test_alertar_slack_yellow` — Alerta enviado com formato correto
- [ ] `test_alertar_slack_red` — Alerta critico enviado

### Definition of Done

- [ ] Todos os 18 testes passando
- [ ] Integracao com orchestrator.py funcional
- [ ] Alertas Slack formatados corretamente

---

## Tarefa 3: Quality Worker (Scheduler)

### Objetivo

Worker que roda a cada 15 minutos para checar quality.

### Arquivo: `app/workers/meta_quality_worker.py`

### Implementacao

```python
"""
Worker de monitoramento de quality Meta.

Sprint 67 - Epic 67.1.
Roda a cada 15 min via scheduler.
"""

import logging

from app.services.meta.quality_monitor import quality_monitor

logger = logging.getLogger(__name__)


async def executar_quality_check() -> dict:
    """
    Job principal: verifica quality de todos chips Meta.

    Registrado no scheduler como:
    - Nome: meta_quality_check
    - Cron: */15 * * * *  (a cada 15 min)
    - Timeout: 60s
    """
    try:
        resultado = await quality_monitor.verificar_quality_chips()
        logger.info(
            "Quality check concluido",
            extra={
                "total": resultado.get("total", 0),
                "green": resultado.get("green", 0),
                "yellow": resultado.get("yellow", 0),
                "red": resultado.get("red", 0),
                "transicoes": resultado.get("transicoes", 0),
            },
        )
        return resultado
    except Exception as e:
        logger.error(f"Erro no quality check: {e}")
        return {"error": str(e)}
```

### Modificacoes

**`app/workers/scheduler.py`:**
Adicionar job:
```python
{
    "name": "meta_quality_check",
    "cron": "*/15 * * * *",
    "handler": "app.workers.meta_quality_worker.executar_quality_check",
    "timeout": 60,
    "enabled": True,
}
```

### Testes Obrigatorios

- [ ] `test_executar_quality_check_sucesso` — Retorna summary correto
- [ ] `test_executar_quality_check_erro` — Exception tratada, retorna error

### Definition of Done

- [ ] Worker registrado no scheduler
- [ ] Logs estruturados com metricas
- [ ] Erro nao derruba o scheduler
