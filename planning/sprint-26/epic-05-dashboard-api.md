# Epic 05: Dashboard API

## Objetivo

Implementar **endpoints de API** para visualizacao e gestao do pool:
- Status do pool em tempo real
- Metricas por chip
- Historico de operacoes
- Acoes manuais (pause/resume)

## Contexto

A API serve tanto um dashboard web futuro quanto comandos Slack para gestao.

---

## Story 5.1: Endpoints de Status

### Objetivo
Endpoints para visualizar status do pool.

### Implementacao

**Arquivo:** `app/api/routes/chips_dashboard.py`

```python
"""
Dashboard API - Endpoints para gestao do pool de chips.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.services.chips.orchestrator import chip_orchestrator
from app.services.chips.health_monitor import health_monitor
from app.services.supabase import supabase

router = APIRouter(prefix="/dashboard/chips", tags=["dashboard"])


# ════════════════════════════════════════════════════════════════
# STATUS DO POOL
# ════════════════════════════════════════════════════════════════

@router.get("/pool/status")
async def get_pool_status():
    """
    Retorna status completo do pool.

    Inclui contagem por status, saude geral e metricas.
    """
    return await chip_orchestrator.obter_status_pool()


@router.get("/pool/health")
async def get_pool_health():
    """
    Retorna relatorio de saude do pool.

    Inclui alertas ativos e chips criticos.
    """
    return await health_monitor.gerar_relatorio()


@router.get("/pool/deficits")
async def get_pool_deficits():
    """
    Retorna deficits atuais do pool.

    Util para saber se precisa provisionar mais chips.
    """
    await chip_orchestrator.carregar_config()
    return await chip_orchestrator.verificar_deficits()


# ════════════════════════════════════════════════════════════════
# LISTAGEM DE CHIPS
# ════════════════════════════════════════════════════════════════

@router.get("/list")
async def list_chips(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    trust_min: Optional[int] = Query(None, ge=0, le=100, description="Trust minimo"),
    trust_max: Optional[int] = Query(None, ge=0, le=100, description="Trust maximo"),
    trust_level: Optional[str] = Query(None, description="Filtrar por nivel"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Lista chips com filtros.

    Suporta paginacao e filtros por status, trust score e nivel.
    """
    query = supabase.table("chips").select(
        "id, telefone, instance_name, status, trust_score, trust_level, "
        "fase_warmup, msgs_enviadas_hoje, msgs_recebidas_hoje, "
        "evolution_connected, warming_started_at, ready_at, created_at"
    )

    if status:
        query = query.eq("status", status)

    if trust_min is not None:
        query = query.gte("trust_score", trust_min)

    if trust_max is not None:
        query = query.lte("trust_score", trust_max)

    if trust_level:
        query = query.eq("trust_level", trust_level)

    result = query.order(
        "trust_score", desc=True
    ).range(offset, offset + limit - 1).execute()

    # Contar total
    count_query = supabase.table("chips").select("id", count="exact")
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()

    return {
        "chips": result.data or [],
        "total": count_result.count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{chip_id}")
async def get_chip_detail(chip_id: str):
    """
    Retorna detalhes completos de um chip.

    Inclui todas as metricas, fatores de trust e permissoes.
    """
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        raise HTTPException(404, "Chip not found")

    return result.data


# ════════════════════════════════════════════════════════════════
# METRICAS E HISTORICO
# ════════════════════════════════════════════════════════════════

@router.get("/{chip_id}/metrics")
async def get_chip_metrics(
    chip_id: str,
    periodo: str = Query("24h", description="Periodo: 1h, 24h, 7d, 30d"),
):
    """
    Retorna metricas detalhadas de um chip.

    Inclui contagens, taxas e tendencias.
    """
    # Calcular desde
    if periodo == "1h":
        desde = datetime.now(timezone.utc) - timedelta(hours=1)
    elif periodo == "24h":
        desde = datetime.now(timezone.utc) - timedelta(days=1)
    elif periodo == "7d":
        desde = datetime.now(timezone.utc) - timedelta(days=7)
    else:
        desde = datetime.now(timezone.utc) - timedelta(days=30)

    # Buscar chip
    chip = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not chip.data:
        raise HTTPException(404, "Chip not found")

    # Buscar interacoes no periodo
    interacoes = supabase.table("chip_interactions").select(
        "tipo", count="exact"
    ).eq(
        "chip_id", chip_id
    ).gte(
        "created_at", desde.isoformat()
    ).execute()

    # Contar por tipo
    enviadas = supabase.table("chip_interactions").select(
        "*", count="exact"
    ).eq("chip_id", chip_id).eq("tipo", "msg_enviada").gte(
        "created_at", desde.isoformat()
    ).execute()

    recebidas = supabase.table("chip_interactions").select(
        "*", count="exact"
    ).eq("chip_id", chip_id).eq("tipo", "msg_recebida").gte(
        "created_at", desde.isoformat()
    ).execute()

    respondidas = supabase.table("chip_interactions").select(
        "*", count="exact"
    ).eq("chip_id", chip_id).eq("tipo", "msg_enviada").eq(
        "obteve_resposta", True
    ).gte("created_at", desde.isoformat()).execute()

    erros = supabase.table("chip_interactions").select(
        "*", count="exact"
    ).eq("chip_id", chip_id).not_.is_("erro_codigo", None).gte(
        "created_at", desde.isoformat()
    ).execute()

    # Calcular taxas
    total_enviadas = enviadas.count or 0
    total_respondidas = respondidas.count or 0
    taxa_resposta = total_respondidas / total_enviadas if total_enviadas > 0 else 0

    return {
        "chip_id": chip_id,
        "periodo": periodo,
        "metricas": {
            "msgs_enviadas": total_enviadas,
            "msgs_recebidas": recebidas.count or 0,
            "msgs_respondidas": total_respondidas,
            "taxa_resposta": round(taxa_resposta, 4),
            "erros": erros.count or 0,
        },
        "atual": {
            "trust_score": chip.data["trust_score"],
            "trust_level": chip.data["trust_level"],
            "status": chip.data["status"],
        }
    }


@router.get("/{chip_id}/trust-history")
async def get_chip_trust_history(
    chip_id: str,
    dias: int = Query(7, ge=1, le=30),
):
    """
    Retorna historico de Trust Score.

    Util para visualizar tendencias.
    """
    desde = datetime.now(timezone.utc) - timedelta(days=dias)

    result = supabase.table("chip_trust_history").select(
        "score, level, factors, recorded_at"
    ).eq(
        "chip_id", chip_id
    ).gte(
        "recorded_at", desde.isoformat()
    ).order(
        "recorded_at", desc=True
    ).limit(100).execute()

    return {
        "chip_id": chip_id,
        "dias": dias,
        "historico": result.data or [],
    }


@router.get("/{chip_id}/transitions")
async def get_chip_transitions(
    chip_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    """
    Retorna historico de transicoes de estado.
    """
    result = supabase.table("chip_transitions").select("*").eq(
        "chip_id", chip_id
    ).order(
        "created_at", desc=True
    ).limit(limit).execute()

    return {
        "chip_id": chip_id,
        "transicoes": result.data or [],
    }


# ════════════════════════════════════════════════════════════════
# ALERTAS
# ════════════════════════════════════════════════════════════════

@router.get("/alertas")
async def list_alertas(
    resolved: bool = Query(False, description="Incluir resolvidos"),
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Lista alertas do pool.
    """
    query = supabase.table("chip_alerts").select(
        "*, chips(telefone, instance_name)"
    )

    if not resolved:
        query = query.eq("resolved", False)

    if severity:
        query = query.eq("severity", severity)

    result = query.order("created_at", desc=True).limit(limit).execute()

    return {
        "alertas": result.data or [],
        "total": len(result.data or []),
    }


@router.post("/alertas/{alerta_id}/resolve")
async def resolve_alerta(
    alerta_id: str,
    resolution_notes: Optional[str] = None,
):
    """
    Marca alerta como resolvido.
    """
    result = supabase.table("chip_alerts").update({
        "resolved": True,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "resolved_by": "api",
        "resolution_notes": resolution_notes,
    }).eq("id", alerta_id).execute()

    if not result.data:
        raise HTTPException(404, "Alert not found")

    return {"status": "ok", "alerta": result.data[0]}


# ════════════════════════════════════════════════════════════════
# ACOES MANUAIS
# ════════════════════════════════════════════════════════════════

@router.post("/{chip_id}/pause")
async def pause_chip(chip_id: str, motivo: Optional[str] = None):
    """
    Pausa chip manualmente.

    Chip pausado nao envia nem recebe mensagens via Julia.
    """
    result = supabase.table("chips").update({
        "status": "paused",
    }).eq("id", chip_id).in_(
        "status", ["active", "warming", "ready"]
    ).execute()

    if not result.data:
        raise HTTPException(404, "Chip not found or already paused")

    # Registrar operacao
    supabase.table("orchestrator_operations").insert({
        "operacao": "demotion",
        "chip_id": chip_id,
        "motivo": motivo or "Pausa manual via API",
    }).execute()

    return {"status": "ok", "chip": result.data[0]}


@router.post("/{chip_id}/resume")
async def resume_chip(chip_id: str):
    """
    Resume chip pausado.

    Volta para status anterior (warming ou ready).
    """
    # Buscar chip
    chip = supabase.table("chips").select("*").eq("id", chip_id).eq(
        "status", "paused"
    ).single().execute()

    if not chip.data:
        raise HTTPException(404, "Chip not found or not paused")

    # Determinar novo status
    novo_status = "warming"
    if chip.data.get("ready_at"):
        novo_status = "ready"

    result = supabase.table("chips").update({
        "status": novo_status,
    }).eq("id", chip_id).execute()

    return {"status": "ok", "chip": result.data[0], "novo_status": novo_status}


@router.post("/{chip_id}/recalculate-trust")
async def recalculate_trust(chip_id: str):
    """
    Forca recalculo do Trust Score.
    """
    from app.services.trust_score.service import trust_score_service

    result = await trust_score_service.atualizar_trust_score(chip_id)

    return {
        "status": "ok",
        "trust_score": result.score,
        "trust_level": result.level.value,
        "breakdown": result.breakdown,
    }


# ════════════════════════════════════════════════════════════════
# OPERACOES DO ORCHESTRATOR
# ════════════════════════════════════════════════════════════════

@router.get("/operations")
async def list_operations(
    operacao: Optional[str] = Query(None, description="Filtrar por tipo"),
    chip_id: Optional[str] = Query(None, description="Filtrar por chip"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Lista operacoes do orchestrator.
    """
    query = supabase.table("orchestrator_operations").select(
        "*, chips!chip_id(telefone)"
    )

    if operacao:
        query = query.eq("operacao", operacao)

    if chip_id:
        query = query.eq("chip_id", chip_id)

    result = query.order("created_at", desc=True).limit(limit).execute()

    return {
        "operacoes": result.data or [],
    }


@router.post("/orchestrator/run-cycle")
async def run_orchestrator_cycle():
    """
    Executa ciclo do orchestrator manualmente.

    Util para forcar verificacoes imediatas.
    """
    await chip_orchestrator.executar_ciclo()
    return {"status": "ok", "message": "Ciclo executado"}
```

### DoD

- [ ] Endpoints de status
- [ ] Endpoints de listagem
- [ ] Endpoints de metricas
- [ ] Endpoints de acoes

---

## Checklist do Epico

- [ ] **E05.1** - Endpoints implementados
- [ ] Documentacao OpenAPI
- [ ] Testes de integracao
