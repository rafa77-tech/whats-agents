# EPIC 67.3: Template Analytics

## Contexto

Templates sao o unico jeito de iniciar conversa com medicos fora da janela 24h. Saber quais templates performam bem (alto delivery/read rate) e quais performam mal e critico para otimizar campanhas. A Meta fornece Template Analytics API com metricas granulares.

## Escopo

- **Incluido**: Polling da Analytics API, armazenamento de metricas, endpoint REST para consulta, alertas de baixa performance
- **Excluido**: A/B testing automatico (Sprint 70+), auto-rewrite de templates, dashboard UI (Sprint 69)

---

## Tarefa 1: Migration — Tabela `meta_template_analytics`

### Objetivo

Criar tabela para armazenar metricas de performance de templates.

### Schema

```sql
CREATE TABLE meta_template_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    waba_id TEXT NOT NULL,
    template_name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'pt_BR',
    date DATE NOT NULL,                    -- Data da metrica
    granularity TEXT NOT NULL DEFAULT 'DAILY',  -- DAILY ou HALF_HOUR
    sent INT NOT NULL DEFAULT 0,
    delivered INT NOT NULL DEFAULT 0,
    read_count INT NOT NULL DEFAULT 0,     -- 'read' e reservado em SQL
    clicked INT NOT NULL DEFAULT 0,        -- Clicks em buttons/CTAs
    failed INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10,4) DEFAULT 0,     -- Custo estimado em USD
    delivery_rate NUMERIC(5,2) GENERATED ALWAYS AS (
        CASE WHEN sent > 0 THEN (delivered::numeric / sent * 100) ELSE 0 END
    ) STORED,
    read_rate NUMERIC(5,2) GENERATED ALWAYS AS (
        CASE WHEN delivered > 0 THEN (read_count::numeric / delivered * 100) ELSE 0 END
    ) STORED,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(waba_id, template_name, language, date, granularity)
);

-- Indices
CREATE INDEX idx_meta_template_analytics_waba ON meta_template_analytics(waba_id);
CREATE INDEX idx_meta_template_analytics_template ON meta_template_analytics(template_name);
CREATE INDEX idx_meta_template_analytics_date ON meta_template_analytics(date DESC);
CREATE INDEX idx_meta_template_analytics_delivery ON meta_template_analytics(delivery_rate)
    WHERE sent > 10;  -- So indexa templates com volume relevante
```

### Testes

- [ ] Migration aplica sem erro
- [ ] Computed columns (delivery_rate, read_rate) calculam corretamente
- [ ] Unique constraint funciona no upsert

---

## Tarefa 2: Template Analytics Service

### Objetivo

Servico que consulta a Meta Template Analytics API e armazena resultados.

### Arquivo: `app/services/meta/template_analytics.py`

### Implementacao

```python
"""
Template Analytics Service.

Sprint 67 - Epic 67.3.

Consulta a Meta Template Analytics API e armazena metricas
de performance (delivery, read, click) por template.
"""

import logging
from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaTemplateAnalytics:
    """
    Coleta e armazena analytics de templates Meta.

    Endpoint Meta:
    GET /{waba_id}/template_analytics?start={unix}&end={unix}&granularity=DAILY
    → {data_points: [{template_id, sent, delivered, read, clicked, cost}]}
    """

    def __init__(self):
        self.graph_api_version = settings.META_GRAPH_API_VERSION

    async def coletar_analytics(
        self,
        waba_id: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> dict:
        """
        Coleta analytics de todos templates de um WABA.

        Args:
            waba_id: ID do WABA
            data_inicio: Data inicio (default: ontem)
            data_fim: Data fim (default: hoje)

        Returns:
            dict com {templates_processados, registros_salvos, erros}
        """
        pass

    async def _consultar_analytics_api(
        self, waba_id: str, access_token: str, start_unix: int, end_unix: int
    ) -> list[dict]:
        """
        Consulta Meta Template Analytics API.

        Returns:
            Lista de data_points do Meta
        """
        pass

    async def _salvar_analytics(self, waba_id: str, data_points: list[dict]) -> int:
        """
        Salva data points no banco (upsert).

        Returns:
            Numero de registros salvos
        """
        pass

    async def obter_analytics_template(
        self,
        template_name: str,
        waba_id: Optional[str] = None,
        dias: int = 30,
    ) -> list[dict]:
        """
        Retorna analytics de um template especifico.

        Returns:
            Lista de metricas diarias
        """
        pass

    async def obter_ranking_templates(
        self,
        waba_id: str,
        metrica: str = "delivery_rate",  # delivery_rate, read_rate, sent
        dias: int = 7,
        limite: int = 20,
    ) -> list[dict]:
        """
        Ranking de templates por metrica.

        Returns:
            Lista ordenada por metrica (desc)
        """
        pass

    async def detectar_templates_baixa_performance(
        self,
        waba_id: str,
        threshold_delivery: float = 70.0,
        min_envios: int = 10,
        dias: int = 7,
    ) -> list[dict]:
        """
        Detecta templates com delivery < threshold.

        Returns:
            Lista de templates com low performance + sugestao
        """
        pass


template_analytics = MetaTemplateAnalytics()
```

### Testes Obrigatorios (`tests/services/meta/test_template_analytics.py`)

- [ ] `test_coletar_analytics_sucesso` — Coleta e salva data points
- [ ] `test_coletar_analytics_sem_token` — Graceful error se token ausente
- [ ] `test_coletar_analytics_api_erro` — HTTP error tratado
- [ ] `test_salvar_analytics_upsert` — Atualiza se registro existe
- [ ] `test_obter_analytics_template` — Retorna metricas diarias
- [ ] `test_obter_analytics_template_nenhum` — Retorna lista vazia
- [ ] `test_obter_ranking_por_delivery` — Ordenado por delivery_rate desc
- [ ] `test_obter_ranking_por_read` — Ordenado por read_rate desc
- [ ] `test_detectar_baixa_performance` — Detecta template <70% delivery
- [ ] `test_detectar_baixa_performance_ignora_baixo_volume` — Ignora <10 envios
- [ ] `test_computed_columns_corretas` — delivery_rate e read_rate calculam

### Definition of Done

- [ ] 11 testes passando
- [ ] Metricas coletadas e armazenadas no banco
- [ ] Ranking funcional

---

## Tarefa 3: API Routes para Analytics

### Objetivo

Endpoints REST para consultar analytics de templates.

### Arquivo: `app/api/routes/meta_analytics.py`

### Endpoints

```
GET /meta/analytics/templates?waba_id=X&dias=30
  → Lista analytics de todos templates (ranking)

GET /meta/analytics/templates/{name}?waba_id=X&dias=30
  → Analytics detalhado de 1 template (serie temporal)

GET /meta/analytics/templates/alerts?waba_id=X
  → Templates com baixa performance
```

### Testes Obrigatorios (`tests/api/routes/test_meta_analytics.py`)

- [ ] `test_listar_analytics_sucesso` — Retorna ranking
- [ ] `test_listar_analytics_sem_auth` — 401 sem X-API-Key
- [ ] `test_detalhe_template_sucesso` — Retorna serie temporal

### Definition of Done

- [ ] 3 testes passando
- [ ] Router registrado no main.py
- [ ] Auth via X-API-Key

---

## Tarefa 4: Worker de Coleta

### Objetivo

Job que coleta analytics diariamente.

### Modificacoes

**`app/workers/scheduler.py`:**
```python
{
    "name": "meta_template_analytics",
    "cron": "0 6 * * *",  # 6h da manha (dados do dia anterior)
    "handler": "app.workers.meta_analytics_worker.coletar_template_analytics",
    "timeout": 120,
    "enabled": True,
}
```

### Definition of Done

- [ ] Worker registrado
- [ ] Coleta automatica as 6h
