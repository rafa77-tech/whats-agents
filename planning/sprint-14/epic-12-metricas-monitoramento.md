# E12 - Métricas e Monitoramento

## Objetivo

Implementar métricas e dashboard para acompanhar performance do pipeline de grupos.

## Contexto

Precisamos monitorar:
- Volume de mensagens por grupo
- Taxa de conversão (mensagem → vaga)
- Taxa de duplicação
- Performance do LLM (tempo, custo)
- Qualidade da extração
- Saúde do pipeline

## Stories

### S12.1 - Criar tabela de métricas

**Descrição:** Estrutura para armazenar métricas agregadas.

```sql
-- Métricas diárias de grupos
CREATE TABLE metricas_grupos_diarias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data DATE NOT NULL,
    grupo_id UUID REFERENCES grupos_whatsapp(id),

    -- Volume
    mensagens_total INT DEFAULT 0,
    mensagens_processadas INT DEFAULT 0,
    mensagens_descartadas INT DEFAULT 0,

    -- Vagas
    vagas_extraidas INT DEFAULT 0,
    vagas_importadas INT DEFAULT 0,
    vagas_revisao INT DEFAULT 0,
    vagas_descartadas INT DEFAULT 0,
    vagas_duplicadas INT DEFAULT 0,

    -- Performance
    tempo_medio_processamento_ms INT,
    tempo_medio_llm_ms INT,

    -- Custos
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,
    custo_estimado_usd DECIMAL(10, 4) DEFAULT 0,

    -- Qualidade
    confianca_media_extracao DECIMAL(3, 2),
    confianca_media_match DECIMAL(3, 2),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_metricas_dia_grupo UNIQUE(data, grupo_id)
);

-- Índices
CREATE INDEX idx_metricas_grupos_data ON metricas_grupos_diarias(data);
CREATE INDEX idx_metricas_grupos_grupo ON metricas_grupos_diarias(grupo_id);

-- Métricas consolidadas (sem grupo)
CREATE TABLE metricas_pipeline_diarias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data DATE NOT NULL UNIQUE,

    -- Volume total
    grupos_ativos INT DEFAULT 0,
    mensagens_total INT DEFAULT 0,
    mensagens_processadas INT DEFAULT 0,

    -- Funnel
    heuristica_passou INT DEFAULT 0,
    llm_classificou INT DEFAULT 0,
    extracao_sucesso INT DEFAULT 0,
    normalizacao_sucesso INT DEFAULT 0,

    -- Resultado
    vagas_importadas INT DEFAULT 0,
    vagas_revisao INT DEFAULT 0,
    vagas_duplicadas INT DEFAULT 0,

    -- Performance
    p50_tempo_ms INT,
    p95_tempo_ms INT,
    p99_tempo_ms INT,

    -- Custos
    custo_total_usd DECIMAL(10, 4),

    -- Erros
    erros_total INT DEFAULT 0,
    erros_por_estagio JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Estimativa:** 1h

---

### S12.2 - Coletor de métricas em tempo real

**Descrição:** Serviço para coletar métricas durante processamento.

```python
# app/services/grupos/metricas.py

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date
from uuid import UUID
import time


@dataclass
class MetricasProcessamento:
    """Métricas coletadas durante processamento."""
    inicio: float = field(default_factory=time.time)
    fim: Optional[float] = None

    # Contadores
    mensagens_processadas: int = 0
    vagas_extraidas: int = 0

    # Tempos
    tempo_heuristica_ms: int = 0
    tempo_llm_ms: int = 0
    tempo_extracao_ms: int = 0
    tempo_normalizacao_ms: int = 0

    # LLM
    tokens_input: int = 0
    tokens_output: int = 0

    # Resultado
    resultado: Optional[str] = None
    confianca: Optional[float] = None

    def finalizar(self):
        self.fim = time.time()

    @property
    def tempo_total_ms(self) -> int:
        if self.fim:
            return int((self.fim - self.inicio) * 1000)
        return 0


class ColetorMetricas:
    """Coleta e persiste métricas de processamento."""

    def __init__(self):
        self.metricas_pendentes = []

    async def registrar(
        self,
        grupo_id: UUID,
        metricas: MetricasProcessamento
    ) -> None:
        """Registra métricas de um processamento."""
        self.metricas_pendentes.append({
            "grupo_id": str(grupo_id),
            "data": date.today().isoformat(),
            "metricas": metricas,
        })

        # Flush a cada 100 registros
        if len(self.metricas_pendentes) >= 100:
            await self.flush()

    async def flush(self) -> None:
        """Persiste métricas pendentes."""
        if not self.metricas_pendentes:
            return

        # Agregar por grupo/data
        agregado = {}
        for item in self.metricas_pendentes:
            key = (item["data"], item["grupo_id"])
            if key not in agregado:
                agregado[key] = {
                    "mensagens_processadas": 0,
                    "vagas_extraidas": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "tempos": [],
                    "confiancas": [],
                }

            m = item["metricas"]
            agregado[key]["mensagens_processadas"] += 1
            agregado[key]["vagas_extraidas"] += m.vagas_extraidas
            agregado[key]["tokens_input"] += m.tokens_input
            agregado[key]["tokens_output"] += m.tokens_output
            agregado[key]["tempos"].append(m.tempo_total_ms)
            if m.confianca:
                agregado[key]["confiancas"].append(m.confianca)

        # Upsert no banco
        for (data, grupo_id), valores in agregado.items():
            await self._upsert_metricas_grupo(data, grupo_id, valores)

        self.metricas_pendentes = []

    async def _upsert_metricas_grupo(
        self,
        data: str,
        grupo_id: str,
        valores: dict
    ) -> None:
        """Atualiza ou insere métricas do grupo."""

        # Calcular médias
        tempo_medio = sum(valores["tempos"]) // len(valores["tempos"]) if valores["tempos"] else 0
        confianca_media = sum(valores["confiancas"]) / len(valores["confiancas"]) if valores["confiancas"] else None

        # Custo estimado (Claude Haiku)
        custo = (valores["tokens_input"] * 0.25 / 1_000_000) + \
                (valores["tokens_output"] * 1.25 / 1_000_000)

        supabase.rpc("incrementar_metricas_grupo", {
            "p_data": data,
            "p_grupo_id": grupo_id,
            "p_mensagens": valores["mensagens_processadas"],
            "p_vagas": valores["vagas_extraidas"],
            "p_tokens_in": valores["tokens_input"],
            "p_tokens_out": valores["tokens_output"],
            "p_tempo_medio": tempo_medio,
            "p_confianca": confianca_media,
            "p_custo": custo,
        }).execute()


# Instância global
coletor_metricas = ColetorMetricas()
```

**Estimativa:** 2h

---

### S12.3 - Função SQL de agregação

**Descrição:** Funções para agregar métricas.

```sql
-- Função para incrementar métricas de grupo
CREATE OR REPLACE FUNCTION incrementar_metricas_grupo(
    p_data DATE,
    p_grupo_id UUID,
    p_mensagens INT,
    p_vagas INT,
    p_tokens_in INT,
    p_tokens_out INT,
    p_tempo_medio INT,
    p_confianca DECIMAL,
    p_custo DECIMAL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO metricas_grupos_diarias (
        data, grupo_id,
        mensagens_processadas, vagas_extraidas,
        tokens_input, tokens_output,
        tempo_medio_processamento_ms,
        confianca_media_extracao,
        custo_estimado_usd
    ) VALUES (
        p_data, p_grupo_id,
        p_mensagens, p_vagas,
        p_tokens_in, p_tokens_out,
        p_tempo_medio,
        p_confianca,
        p_custo
    )
    ON CONFLICT (data, grupo_id) DO UPDATE SET
        mensagens_processadas = metricas_grupos_diarias.mensagens_processadas + p_mensagens,
        vagas_extraidas = metricas_grupos_diarias.vagas_extraidas + p_vagas,
        tokens_input = metricas_grupos_diarias.tokens_input + p_tokens_in,
        tokens_output = metricas_grupos_diarias.tokens_output + p_tokens_out,
        tempo_medio_processamento_ms = (
            metricas_grupos_diarias.tempo_medio_processamento_ms + p_tempo_medio
        ) / 2,
        confianca_media_extracao = COALESCE(
            (metricas_grupos_diarias.confianca_media_extracao + p_confianca) / 2,
            p_confianca
        ),
        custo_estimado_usd = metricas_grupos_diarias.custo_estimado_usd + p_custo,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;


-- Função para consolidar métricas diárias
CREATE OR REPLACE FUNCTION consolidar_metricas_pipeline(p_data DATE)
RETURNS VOID AS $$
BEGIN
    INSERT INTO metricas_pipeline_diarias (
        data,
        grupos_ativos,
        mensagens_total,
        mensagens_processadas,
        vagas_importadas,
        vagas_revisao,
        vagas_duplicadas,
        custo_total_usd
    )
    SELECT
        p_data,
        COUNT(DISTINCT grupo_id),
        SUM(mensagens_total),
        SUM(mensagens_processadas),
        SUM(vagas_importadas),
        SUM(vagas_revisao),
        SUM(vagas_duplicadas),
        SUM(custo_estimado_usd)
    FROM metricas_grupos_diarias
    WHERE data = p_data
    ON CONFLICT (data) DO UPDATE SET
        grupos_ativos = EXCLUDED.grupos_ativos,
        mensagens_total = EXCLUDED.mensagens_total,
        mensagens_processadas = EXCLUDED.mensagens_processadas,
        vagas_importadas = EXCLUDED.vagas_importadas,
        vagas_revisao = EXCLUDED.vagas_revisao,
        vagas_duplicadas = EXCLUDED.vagas_duplicadas,
        custo_total_usd = EXCLUDED.custo_total_usd;
END;
$$ LANGUAGE plpgsql;
```

**Estimativa:** 1h

---

### S12.4 - Endpoint de métricas

**Descrição:** API para consultar métricas.

```python
# app/api/routes/metricas_grupos.py

from fastapi import APIRouter, Query
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/metricas/grupos", tags=["metricas"])


@router.get("/resumo")
async def get_resumo_metricas(
    periodo: str = Query("7d", description="Período: 1d, 7d, 30d"),
):
    """Retorna resumo de métricas do pipeline."""

    dias = {"1d": 1, "7d": 7, "30d": 30}.get(periodo, 7)
    data_inicio = (date.today() - timedelta(days=dias)).isoformat()

    result = supabase.table("metricas_pipeline_diarias") \
        .select("*") \
        .gte("data", data_inicio) \
        .order("data", desc=True) \
        .execute()

    # Calcular totais
    totais = {
        "mensagens": sum(r["mensagens_processadas"] or 0 for r in result.data),
        "vagas_importadas": sum(r["vagas_importadas"] or 0 for r in result.data),
        "vagas_revisao": sum(r["vagas_revisao"] or 0 for r in result.data),
        "vagas_duplicadas": sum(r["vagas_duplicadas"] or 0 for r in result.data),
        "custo_usd": sum(float(r["custo_total_usd"] or 0) for r in result.data),
        "grupos_ativos": max((r["grupos_ativos"] or 0) for r in result.data) if result.data else 0,
    }

    # Calcular taxas
    if totais["mensagens"] > 0:
        totais["taxa_conversao"] = totais["vagas_importadas"] / totais["mensagens"]
        totais["taxa_duplicacao"] = totais["vagas_duplicadas"] / (totais["vagas_importadas"] + totais["vagas_duplicadas"]) if (totais["vagas_importadas"] + totais["vagas_duplicadas"]) > 0 else 0

    return {
        "periodo": periodo,
        "data_inicio": data_inicio,
        "totais": totais,
        "por_dia": result.data,
    }


@router.get("/grupos")
async def get_metricas_grupos(
    data_inicio: Optional[date] = None,
    limite: int = 20,
):
    """Retorna métricas por grupo."""

    if not data_inicio:
        data_inicio = date.today() - timedelta(days=7)

    result = supabase.table("metricas_grupos_diarias") \
        .select("""
            grupo_id,
            grupos_whatsapp(nome, regiao),
            SUM(mensagens_processadas) as total_msgs,
            SUM(vagas_importadas) as total_vagas,
            AVG(confianca_media_extracao) as confianca_media
        """) \
        .gte("data", data_inicio.isoformat()) \
        .group_by("grupo_id, grupos_whatsapp.nome, grupos_whatsapp.regiao") \
        .order("total_vagas", desc=True) \
        .limit(limite) \
        .execute()

    return {
        "data_inicio": data_inicio.isoformat(),
        "grupos": result.data,
    }


@router.get("/custos")
async def get_metricas_custos(
    periodo: str = Query("30d"),
):
    """Retorna métricas de custo do LLM."""

    dias = {"7d": 7, "30d": 30, "90d": 90}.get(periodo, 30)
    data_inicio = (date.today() - timedelta(days=dias)).isoformat()

    result = supabase.table("metricas_pipeline_diarias") \
        .select("data, custo_total_usd, mensagens_processadas") \
        .gte("data", data_inicio) \
        .order("data") \
        .execute()

    total_custo = sum(float(r["custo_total_usd"] or 0) for r in result.data)
    total_msgs = sum(r["mensagens_processadas"] or 0 for r in result.data)
    custo_por_msg = total_custo / total_msgs if total_msgs > 0 else 0

    return {
        "periodo": periodo,
        "total_usd": round(total_custo, 4),
        "custo_por_mensagem": round(custo_por_msg, 6),
        "projecao_mensal": round(total_custo / dias * 30, 2),
        "por_dia": [
            {"data": r["data"], "custo": float(r["custo_total_usd"] or 0)}
            for r in result.data
        ],
    }
```

**Estimativa:** 2h

---

### S12.5 - Dashboard no Slack

**Descrição:** Comando para ver dashboard de métricas.

```python
async def tool_dashboard_grupos() -> dict:
    """
    Mostra dashboard de métricas de grupos.

    Returns:
        Dashboard formatado para Slack
    """
    from datetime import date, timedelta

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    semana = hoje - timedelta(days=7)

    # Métricas de hoje
    hoje_result = supabase.table("metricas_pipeline_diarias") \
        .select("*") \
        .eq("data", hoje.isoformat()) \
        .single() \
        .execute()

    # Métricas de ontem
    ontem_result = supabase.table("metricas_pipeline_diarias") \
        .select("*") \
        .eq("data", ontem.isoformat()) \
        .single() \
        .execute()

    # Métricas da semana
    semana_result = supabase.table("metricas_pipeline_diarias") \
        .select("*") \
        .gte("data", semana.isoformat()) \
        .execute()

    hoje_data = hoje_result.data or {}
    ontem_data = ontem_result.data or {}

    # Calcular variações
    def variacao(atual, anterior):
        if not anterior:
            return "+∞"
        diff = ((atual - anterior) / anterior) * 100
        return f"+{diff:.0f}%" if diff >= 0 else f"{diff:.0f}%"

    # Totais da semana
    semana_importadas = sum(r.get("vagas_importadas", 0) or 0 for r in semana_result.data)
    semana_custo = sum(float(r.get("custo_total_usd", 0) or 0) for r in semana_result.data)

    return {
        "titulo": "Dashboard de Grupos",
        "data": hoje.isoformat(),

        "hoje": {
            "mensagens": hoje_data.get("mensagens_processadas", 0),
            "vagas_importadas": hoje_data.get("vagas_importadas", 0),
            "vagas_revisao": hoje_data.get("vagas_revisao", 0),
            "duplicadas": hoje_data.get("vagas_duplicadas", 0),
            "grupos_ativos": hoje_data.get("grupos_ativos", 0),
        },

        "comparacao_ontem": {
            "mensagens": variacao(
                hoje_data.get("mensagens_processadas", 0),
                ontem_data.get("mensagens_processadas", 0)
            ),
            "vagas": variacao(
                hoje_data.get("vagas_importadas", 0),
                ontem_data.get("vagas_importadas", 0)
            ),
        },

        "semana": {
            "total_vagas": semana_importadas,
            "custo_total": f"${semana_custo:.2f}",
            "media_diaria": semana_importadas // 7,
        },

        "fila": await get_status_fila(),

        "mensagem": f"Hoje: {hoje_data.get('vagas_importadas', 0)} vagas importadas de {hoje_data.get('mensagens_processadas', 0)} mensagens"
    }


async def get_status_fila() -> dict:
    """Retorna status da fila de processamento."""

    result = supabase.rpc("status_fila_grupos").execute()

    return result.data[0] if result.data else {}
```

**Estimativa:** 2h

---

### S12.6 - Alertas automáticos

**Descrição:** Sistema de alertas para anomalias.

```python
# app/services/grupos/alertas.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TipoAlerta(Enum):
    FILA_GRANDE = "fila_grande"
    MUITOS_ERROS = "muitos_erros"
    CUSTO_ALTO = "custo_alto"
    TAXA_BAIXA = "taxa_baixa"
    PIPELINE_PARADO = "pipeline_parado"


@dataclass
class Alerta:
    tipo: TipoAlerta
    severidade: str  # info, warning, critical
    mensagem: str
    valor_atual: float
    threshold: float


class MonitorAlertas:
    """Monitor de alertas do pipeline."""

    THRESHOLDS = {
        "fila_pendente": 1000,
        "erros_hora": 50,
        "custo_dia": 5.0,  # USD
        "taxa_conversao_min": 0.05,  # 5%
        "tempo_sem_processar_min": 30,
    }

    async def verificar_alertas(self) -> list[Alerta]:
        """Verifica todas as condições de alerta."""
        alertas = []

        # Verificar fila
        fila = await self._verificar_fila()
        if fila:
            alertas.append(fila)

        # Verificar erros
        erros = await self._verificar_erros()
        if erros:
            alertas.append(erros)

        # Verificar custos
        custo = await self._verificar_custos()
        if custo:
            alertas.append(custo)

        # Verificar taxa de conversão
        taxa = await self._verificar_taxa_conversao()
        if taxa:
            alertas.append(taxa)

        # Verificar se pipeline está parado
        parado = await self._verificar_pipeline_ativo()
        if parado:
            alertas.append(parado)

        return alertas

    async def _verificar_fila(self) -> Optional[Alerta]:
        """Verifica tamanho da fila."""
        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", "pendente") \
            .execute()

        if result.count > self.THRESHOLDS["fila_pendente"]:
            return Alerta(
                tipo=TipoAlerta.FILA_GRANDE,
                severidade="warning" if result.count < 5000 else "critical",
                mensagem=f"Fila com {result.count} itens pendentes",
                valor_atual=result.count,
                threshold=self.THRESHOLDS["fila_pendente"],
            )
        return None

    async def _verificar_erros(self) -> Optional[Alerta]:
        """Verifica taxa de erros."""
        from datetime import datetime, timedelta

        uma_hora = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", "erro") \
            .gte("updated_at", uma_hora) \
            .execute()

        if result.count > self.THRESHOLDS["erros_hora"]:
            return Alerta(
                tipo=TipoAlerta.MUITOS_ERROS,
                severidade="critical",
                mensagem=f"{result.count} erros na última hora",
                valor_atual=result.count,
                threshold=self.THRESHOLDS["erros_hora"],
            )
        return None

    async def _verificar_custos(self) -> Optional[Alerta]:
        """Verifica custo do dia."""
        from datetime import date

        result = supabase.table("metricas_pipeline_diarias") \
            .select("custo_total_usd") \
            .eq("data", date.today().isoformat()) \
            .single() \
            .execute()

        custo = float(result.data.get("custo_total_usd", 0) or 0) if result.data else 0

        if custo > self.THRESHOLDS["custo_dia"]:
            return Alerta(
                tipo=TipoAlerta.CUSTO_ALTO,
                severidade="warning",
                mensagem=f"Custo do dia: ${custo:.2f}",
                valor_atual=custo,
                threshold=self.THRESHOLDS["custo_dia"],
            )
        return None

    async def _verificar_taxa_conversao(self) -> Optional[Alerta]:
        """Verifica taxa de conversão."""
        from datetime import date

        result = supabase.table("metricas_pipeline_diarias") \
            .select("mensagens_processadas, vagas_importadas") \
            .eq("data", date.today().isoformat()) \
            .single() \
            .execute()

        if not result.data:
            return None

        msgs = result.data.get("mensagens_processadas", 0) or 0
        vagas = result.data.get("vagas_importadas", 0) or 0

        if msgs < 100:  # Muito cedo para avaliar
            return None

        taxa = vagas / msgs if msgs > 0 else 0

        if taxa < self.THRESHOLDS["taxa_conversao_min"]:
            return Alerta(
                tipo=TipoAlerta.TAXA_BAIXA,
                severidade="info",
                mensagem=f"Taxa de conversão baixa: {taxa*100:.1f}%",
                valor_atual=taxa,
                threshold=self.THRESHOLDS["taxa_conversao_min"],
            )
        return None

    async def _verificar_pipeline_ativo(self) -> Optional[Alerta]:
        """Verifica se pipeline está processando."""
        from datetime import datetime, timedelta

        limite = (datetime.utcnow() - timedelta(minutes=self.THRESHOLDS["tempo_sem_processar_min"])).isoformat()

        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .gte("updated_at", limite) \
            .execute()

        # Se tem itens pendentes mas nada foi processado recentemente
        pendentes = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", "pendente") \
            .execute()

        if pendentes.count > 0 and result.count == 0:
            return Alerta(
                tipo=TipoAlerta.PIPELINE_PARADO,
                severidade="critical",
                mensagem=f"Pipeline parado há {self.THRESHOLDS['tempo_sem_processar_min']} minutos",
                valor_atual=0,
                threshold=1,
            )
        return None


# Job para verificar alertas periodicamente
async def job_verificar_alertas():
    """Job que roda a cada 5 minutos."""
    from app.services.slack import enviar_notificacao_slack

    monitor = MonitorAlertas()
    alertas = await monitor.verificar_alertas()

    for alerta in alertas:
        if alerta.severidade in ["warning", "critical"]:
            await enviar_notificacao_slack(
                canal="#alertas-julia",
                mensagem=f"[{alerta.severidade.upper()}] {alerta.tipo.value}: {alerta.mensagem}",
            )
```

**Estimativa:** 2h

---

### S12.7 - Função SQL de status da fila

**Descrição:** Função para retornar status da fila.

```sql
CREATE OR REPLACE FUNCTION status_fila_grupos()
RETURNS TABLE (
    pendentes BIGINT,
    em_processamento BIGINT,
    finalizados_hoje BIGINT,
    erros_hoje BIGINT,
    tempo_medio_ms BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE estagio = 'pendente')::BIGINT as pendentes,
        COUNT(*) FILTER (WHERE estagio NOT IN ('pendente', 'finalizado', 'descartado', 'erro'))::BIGINT as em_processamento,
        COUNT(*) FILTER (WHERE estagio = 'finalizado' AND DATE(updated_at) = CURRENT_DATE)::BIGINT as finalizados_hoje,
        COUNT(*) FILTER (WHERE estagio = 'erro' AND DATE(updated_at) = CURRENT_DATE)::BIGINT as erros_hoje,
        AVG(
            CASE WHEN estagio = 'finalizado'
            THEN EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000
            END
        )::BIGINT as tempo_medio_ms
    FROM fila_processamento_grupos;
END;
$$ LANGUAGE plpgsql;
```

**Estimativa:** 0.5h

---

### S12.8 - Testes de métricas

**Estimativa:** 2h

---

## Resumo

| Story | Descrição | Estimativa |
|-------|-----------|------------|
| S12.1 | Tabela de métricas | 1h |
| S12.2 | Coletor em tempo real | 2h |
| S12.3 | Funções SQL agregação | 1h |
| S12.4 | Endpoint de métricas | 2h |
| S12.5 | Dashboard Slack | 2h |
| S12.6 | Alertas automáticos | 2h |
| S12.7 | Função status fila | 0.5h |
| S12.8 | Testes | 2h |

**Total:** 12.5h (~1.5 dias)

## Dependências

- E11 (Worker) - integração com pipeline

## Entregáveis

- Tabelas de métricas agregadas
- Coletor em tempo real
- API de métricas
- Dashboard no Slack
- Sistema de alertas
- Monitoramento de custos
