# EPIC 67.4: Conversation Analytics & Cost Tracking

## Contexto

A Meta cobra por mensagem (desde Jul/2025) com categorias de preco diferentes. Sem tracking de custo, nao sabemos quanto gastamos por campanha, por chip, ou por medico. Conversas user-initiated dentro da janela 24h sao GRATUITAS — Julia deve priorizar responder dentro da janela.

## Escopo

- **Incluido**: Tracking de custo por mensagem, analytics por tipo de conversa, budget alerts, endpoint de consulta
- **Excluido**: Cost optimization engine (Sprint 69), budget auto-cut, dashboard UI (Sprint 69)

## Modelo de Pricing Meta (Jul/2025+)

| Categoria | Custo (Brasil) | Quando |
|-----------|----------------|--------|
| Marketing | ~$0.0625/msg | Template marketing fora da janela |
| Utility | ~$0.0350/msg | Template utility fora da janela |
| Authentication | ~$0.0315/msg | Template auth fora da janela |
| Service | GRATUITO | Resposta dentro da janela 24h (user-initiated) |

---

## Tarefa 1: Migration — Tabela `meta_conversation_costs`

### Objetivo

Rastrear custo de cada mensagem enviada via Meta.

### Schema

```sql
CREATE TABLE meta_conversation_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES julia_chips(id),
    waba_id TEXT NOT NULL,
    telefone TEXT NOT NULL,
    interacao_id UUID,               -- FK para interacoes (se disponivel)
    message_category TEXT NOT NULL,   -- marketing, utility, authentication, service
    is_free BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE se dentro da janela (service)
    cost_usd NUMERIC(10,6) DEFAULT 0,
    template_name TEXT,              -- NULL se free-form
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_meta_conv_costs_chip ON meta_conversation_costs(chip_id);
CREATE INDEX idx_meta_conv_costs_sent ON meta_conversation_costs(sent_at DESC);
CREATE INDEX idx_meta_conv_costs_category ON meta_conversation_costs(message_category);
CREATE INDEX idx_meta_conv_costs_waba_date ON meta_conversation_costs(waba_id, sent_at::date);

-- View agregada para consulta rapida
CREATE OR REPLACE VIEW meta_cost_summary_daily AS
SELECT
    waba_id,
    sent_at::date AS date,
    message_category,
    COUNT(*) AS total_messages,
    COUNT(*) FILTER (WHERE is_free) AS free_messages,
    COUNT(*) FILTER (WHERE NOT is_free) AS paid_messages,
    SUM(cost_usd) AS total_cost_usd
FROM meta_conversation_costs
GROUP BY waba_id, sent_at::date, message_category;
```

### Testes

- [ ] Migration aplica sem erro
- [ ] View agregada retorna dados corretos

---

## Tarefa 2: Conversation Analytics Service

### Objetivo

Servico que registra custos e fornece analytics.

### Arquivo: `app/services/meta/conversation_analytics.py`

### Implementacao

```python
"""
Conversation Analytics & Cost Tracking.

Sprint 67 - Epic 67.4.

Registra custo de cada mensagem Meta e fornece analytics de custo.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase
from app.services.meta.window_tracker import window_tracker

logger = logging.getLogger(__name__)

# Pricing table Brazil (Jul 2025+)
META_PRICING_BRL = {
    "marketing": 0.0625,
    "utility": 0.0350,
    "authentication": 0.0315,
    "service": 0.0,  # Gratuito dentro da janela
}


class MetaConversationAnalytics:
    """
    Registra e analisa custos de mensagens Meta.
    """

    async def registrar_custo_mensagem(
        self,
        chip_id: str,
        waba_id: str,
        telefone: str,
        message_category: str,
        template_name: Optional[str] = None,
        interacao_id: Optional[str] = None,
    ) -> dict:
        """
        Registra custo de uma mensagem enviada.

        Chamado pelo sender.py apos envio bem-sucedido via Meta.

        Args:
            chip_id: ID do chip
            waba_id: ID do WABA
            telefone: Numero destino
            message_category: marketing, utility, authentication, service
            template_name: Nome do template (None se free-form)
            interacao_id: ID da interacao (se disponivel)

        Returns:
            dict com {cost_usd, is_free, category}
        """
        pass

    async def _determinar_categoria(
        self,
        chip_id: str,
        telefone: str,
        template_name: Optional[str],
    ) -> tuple[str, bool]:
        """
        Determina categoria e se e gratuita.

        Logica:
        - Se dentro da janela 24h E sem template: service (gratuito)
        - Se template marketing: marketing
        - Se template utility: utility
        - Se template auth: authentication
        - Se fora da janela com template: depende da categoria do template

        Returns:
            (category, is_free)
        """
        pass

    async def obter_custo_periodo(
        self,
        waba_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> dict:
        """
        Retorna custo agregado por periodo.

        Returns:
            dict com {total_usd, por_categoria, mensagens_pagas, mensagens_gratis}
        """
        pass

    async def obter_custo_por_chip(
        self,
        waba_id: str,
        dias: int = 30,
    ) -> list[dict]:
        """
        Custo por chip (para identificar chips caros).

        Returns:
            Lista ordenada por custo desc
        """
        pass

    async def obter_custo_por_campanha(
        self,
        campanha_id: Optional[str] = None,
        dias: int = 30,
    ) -> list[dict]:
        """
        Custo por campanha (se rastreavel via template_name).
        """
        pass

    async def verificar_budget(
        self,
        waba_id: str,
        budget_diario_usd: float,
    ) -> dict:
        """
        Verifica se gasto diario excedeu budget.

        Returns:
            dict com {dentro_budget, gasto_hoje, budget, percentual}
        """
        pass

    async def alertar_budget_excedido(
        self,
        waba_id: str,
        gasto: float,
        budget: float,
    ) -> None:
        """Envia alerta Slack se budget excedido."""
        pass


conversation_analytics = MetaConversationAnalytics()
```

### Integracao com sender.py

**`app/services/chips/sender.py` — `_enviar_meta_smart()`:**

Apos envio bem-sucedido, registrar custo:
```python
# Apos envio bem-sucedido
if resultado.get("success"):
    from app.services.meta.conversation_analytics import conversation_analytics
    await conversation_analytics.registrar_custo_mensagem(
        chip_id=chip_id,
        waba_id=chip.get("meta_waba_id"),
        telefone=telefone,
        message_category=...,
        template_name=template_info.get("name") if template_info else None,
    )
```

### Testes Obrigatorios (`tests/services/meta/test_conversation_analytics.py`)

- [ ] `test_registrar_custo_service_gratis` — Dentro da janela, custo 0
- [ ] `test_registrar_custo_marketing` — Template marketing, custo correto
- [ ] `test_registrar_custo_utility` — Template utility, custo correto
- [ ] `test_determinar_categoria_na_janela_sem_template` — service/free
- [ ] `test_determinar_categoria_fora_janela_com_template` — depende do template
- [ ] `test_obter_custo_periodo` — Soma correta
- [ ] `test_obter_custo_por_chip` — Ordenado por custo
- [ ] `test_verificar_budget_dentro` — Retorna dentro_budget=True
- [ ] `test_verificar_budget_excedido` — Retorna dentro_budget=False, alerta
- [ ] `test_obter_custo_periodo_sem_dados` — Retorna zeros

### Definition of Done

- [ ] 10 testes passando
- [ ] Custo registrado automaticamente apos envio Meta
- [ ] Budget check funcional
- [ ] Alertas Slack para budget excedido

---

## Tarefa 3: Budget Check Worker

### Objetivo

Job que verifica budget a cada hora.

### Modificacoes

**`app/workers/scheduler.py`:**
```python
{
    "name": "meta_budget_check",
    "cron": "0 * * * *",  # A cada hora
    "handler": "app.workers.meta_analytics_worker.verificar_budget_meta",
    "timeout": 30,
    "enabled": True,
}
```

### Configuracao

Budget configuravel via settings:
```python
META_BUDGET_DIARIO_USD: float = 50.0  # Default: $50/dia
META_BUDGET_ALERT_THRESHOLD: float = 0.8  # Alerta em 80%
```

### Testes

- [ ] `test_verificar_budget_abaixo_threshold` — Sem alerta
- [ ] `test_verificar_budget_acima_threshold` — Alerta enviado

### Definition of Done

- [ ] Worker registrado
- [ ] Budget configuravel
- [ ] Alerta Slack em 80% e 100%
