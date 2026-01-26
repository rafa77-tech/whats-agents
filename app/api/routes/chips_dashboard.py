"""
Chips Dashboard API - Endpoints para dashboard unificado.

Sprint 26 - E05 + Sprint 40 - Instance Management

Endpoints para:
- Status do pool
- Metricas de saude
- Gerenciamento de chips
- Alertas
- Instance Management (Sprint 40)
"""

from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from app.services.supabase import supabase
from app.services.chips.orchestrator import chip_orchestrator
from app.services.chips.health_monitor import health_monitor
from app.services.chips.selector import chip_selector
from app.services.chips.instance_manager import instance_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chips", tags=["chips-dashboard"])


# ════════════════════════════════════════════════════════════
# POOL STATUS
# ════════════════════════════════════════════════════════════

@router.get("/pool/status")
async def get_pool_status():
    """
    Retorna status completo do pool de chips.

    Inclui contagem por status e indicador de saude.
    """
    return await chip_orchestrator.obter_status_pool()


@router.get("/pool/health")
async def get_pool_health():
    """
    Retorna relatorio de saude do pool.

    Inclui alertas ativos e metricas agregadas.
    """
    return await health_monitor.gerar_relatorio()


@router.get("/pool/deficits")
async def get_pool_deficits():
    """Retorna deficits atuais do pool."""
    return await chip_orchestrator.verificar_deficits()


# ════════════════════════════════════════════════════════════
# CHIPS CRUD
# ════════════════════════════════════════════════════════════

@router.get("/")
async def list_chips(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    trust_min: Optional[int] = Query(None, description="Trust Score minimo"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo (julia/listener)"),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Lista chips com filtros.

    Status possiveis: provisioned, warming, ready, active, degraded, banned, cancelled
    """
    query = supabase.table("chips").select("*")

    if status:
        query = query.eq("status", status)

    if trust_min:
        query = query.gte("trust_score", trust_min)

    if tipo:
        query = query.eq("tipo", tipo)

    result = query.order("trust_score", desc=True).limit(limit).execute()

    return {"chips": result.data or [], "count": len(result.data or [])}


@router.get("/{chip_id}")
async def get_chip(chip_id: str):
    """
    Retorna detalhes de um chip especifico.
    """
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        raise HTTPException(404, "Chip nao encontrado")

    return result.data


@router.get("/{chip_id}/metrics")
async def get_chip_metrics(
    chip_id: str,
    periodo: str = Query("24h", description="Periodo: 1h, 6h, 24h, 7d"),
):
    """
    Retorna metricas detalhadas de um chip.
    """
    # Calcular data inicial
    now = datetime.now(timezone.utc)
    periodos = {
        "1h": now - timedelta(hours=1),
        "6h": now - timedelta(hours=6),
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
    }
    desde = periodos.get(periodo, periodos["24h"])

    # Buscar metricas agregadas
    result = supabase.table("chip_metrics_hourly").select("*").eq(
        "chip_id", chip_id
    ).gte(
        "hora", desde.isoformat()
    ).order("hora", desc=False).execute()

    metricas = result.data or []

    # Calcular totais
    totais = {
        "msgs_enviadas": sum(m.get("msgs_enviadas") or 0 for m in metricas),
        "msgs_recebidas": sum(m.get("msgs_recebidas") or 0 for m in metricas),
        "erros": sum(m.get("erros") or 0 for m in metricas),
        "prospeccoes": sum(m.get("prospeccoes") or 0 for m in metricas),
        "followups": sum(m.get("followups") or 0 for m in metricas),
        "respostas": sum(m.get("respostas") or 0 for m in metricas),
    }

    return {
        "chip_id": chip_id,
        "periodo": periodo,
        "desde": desde.isoformat(),
        "metricas_por_hora": metricas,
        "totais": totais,
    }


@router.get("/{chip_id}/history")
async def get_chip_history(
    chip_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    """
    Retorna historico de operacoes e Trust Score de um chip.
    """
    # Operacoes do orchestrator
    ops = supabase.table("orchestrator_operations").select("*").eq(
        "chip_id", chip_id
    ).order("created_at", desc=True).limit(limit).execute()

    # Historico de Trust (se existir tabela)
    trust_history = []
    try:
        trust = supabase.table("chip_trust_history").select(
            "score, recorded_at"
        ).eq(
            "chip_id", chip_id
        ).order("recorded_at", desc=True).limit(limit).execute()
        trust_history = trust.data or []
    except Exception:
        pass  # Tabela pode nao existir ainda

    return {
        "chip_id": chip_id,
        "operacoes": ops.data or [],
        "trust_history": trust_history,
    }


@router.get("/{chip_id}/interactions")
async def get_chip_interactions(
    chip_id: str,
    tipo: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Retorna interacoes recentes de um chip.
    """
    query = supabase.table("chip_interactions").select("*").eq("chip_id", chip_id)

    if tipo:
        query = query.eq("tipo", tipo)

    result = query.order("created_at", desc=True).limit(limit).execute()

    return {"interactions": result.data or [], "count": len(result.data or [])}


# ════════════════════════════════════════════════════════════
# ACOES MANUAIS
# ════════════════════════════════════════════════════════════

@router.post("/{chip_id}/pause")
async def pause_chip(chip_id: str, motivo: str = Query("Manual")):
    """
    Pausa um chip (move para status degraded).
    """
    return await chip_orchestrator.rebaixar_chip_manual(chip_id, motivo)


@router.post("/{chip_id}/resume")
async def resume_chip(chip_id: str, para_status: str = Query("ready")):
    """
    Resume um chip pausado/degradado.

    para_status: 'ready' ou 'active'
    """
    if para_status not in ["ready", "active"]:
        raise HTTPException(400, "para_status deve ser 'ready' ou 'active'")

    return await chip_orchestrator.promover_chip_manual(chip_id, para_status)


@router.post("/{chip_id}/promote")
async def promote_chip(chip_id: str, para_status: str = Query("active")):
    """
    Promove um chip manualmente.

    para_status: 'ready' ou 'active'
    """
    if para_status not in ["ready", "active"]:
        raise HTTPException(400, "para_status deve ser 'ready' ou 'active'")

    return await chip_orchestrator.promover_chip_manual(chip_id, para_status)


# ════════════════════════════════════════════════════════════
# ALERTAS
# ════════════════════════════════════════════════════════════

@router.get("/alertas")
async def list_alertas(
    chip_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resolved: bool = Query(False, description="Incluir resolvidos"),
):
    """
    Lista alertas com filtros.
    """
    return await health_monitor.listar_alertas(
        chip_id=chip_id,
        severity=severity,
        resolved=resolved,
    )


@router.post("/alertas/{alerta_id}/resolve")
async def resolve_alerta(alerta_id: str, resolved_by: str = Query("manual")):
    """
    Marca um alerta como resolvido.
    """
    return await health_monitor.resolver_alerta(alerta_id, resolved_by)


# ════════════════════════════════════════════════════════════
# ORCHESTRATOR CONTROL
# ════════════════════════════════════════════════════════════

@router.post("/orchestrator/cycle")
async def run_orchestrator_cycle():
    """
    Executa um ciclo do orchestrator manualmente.
    """
    await chip_orchestrator.executar_ciclo()
    return {"status": "ok", "message": "Ciclo executado"}


@router.post("/health-monitor/cycle")
async def run_health_monitor_cycle():
    """
    Executa um ciclo do health monitor manualmente.
    """
    await health_monitor.executar_ciclo()
    return {"status": "ok", "message": "Ciclo executado"}


# ════════════════════════════════════════════════════════════
# CONFIGURACAO
# ════════════════════════════════════════════════════════════

@router.get("/config")
async def get_pool_config():
    """
    Retorna configuracao atual do pool.
    """
    result = supabase.table("pool_config").select("*").limit(1).execute()

    if not result.data:
        return {"config": None, "message": "Nenhuma configuracao encontrada"}

    return {"config": result.data[0]}


@router.put("/config")
async def update_pool_config(config: dict):
    """
    Atualiza configuracao do pool.
    """
    allowed_fields = [
        "producao_min", "producao_max", "ready_min", "warmup_buffer",
        "warmup_days", "trust_min_for_ready", "trust_degraded_threshold",
        "trust_critical_threshold", "auto_provision", "default_ddd",
        "limite_prospeccao_hora", "limite_followup_hora", "limite_resposta_hora",
    ]

    # Filtrar apenas campos permitidos
    updates = {k: v for k, v in config.items() if k in allowed_fields}

    if not updates:
        raise HTTPException(400, "Nenhum campo valido para atualizar")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table("pool_config").select("id").limit(1).execute()

    if result.data:
        supabase.table("pool_config").update(updates).eq(
            "id", result.data[0]["id"]
        ).execute()
    else:
        supabase.table("pool_config").insert(updates).execute()

    # Recarregar config no orchestrator
    await chip_orchestrator.carregar_config()

    return {"status": "ok", "updated": list(updates.keys())}


# ════════════════════════════════════════════════════════════
# SELECAO DE CHIP (TESTE)
# ════════════════════════════════════════════════════════════

@router.get("/selecionar")
async def selecionar_chip(
    tipo_mensagem: str = Query(..., description="prospeccao, followup, ou resposta"),
    telefone_destino: Optional[str] = Query(None),
    conversa_id: Optional[str] = Query(None),
):
    """
    Testa selecao de chip para um tipo de mensagem.

    Util para debug e validacao do chip selector.
    """
    chip = await chip_selector.selecionar_chip(
        tipo_mensagem=tipo_mensagem,
        conversa_id=conversa_id,
        telefone_destino=telefone_destino,
    )

    if not chip:
        return {"chip": None, "message": "Nenhum chip disponivel"}

    return {
        "chip": {
            "id": chip["id"],
            "telefone": chip["telefone"],
            "instance_name": chip["instance_name"],
            "trust_score": chip.get("trust_score"),
            "msgs_enviadas_hoje": chip.get("msgs_enviadas_hoje"),
        },
        "tipo_mensagem": tipo_mensagem,
    }


@router.get("/disponiveis")
async def listar_chips_disponiveis(
    tipo_mensagem: Optional[str] = Query(None),
):
    """
    Lista chips disponiveis para envio.
    """
    chips = await chip_selector.listar_chips_disponiveis(tipo_mensagem)

    return {
        "chips": [
            {
                "id": c["id"],
                "telefone": c["telefone"],
                "trust_score": c.get("trust_score"),
                "msgs_enviadas_hoje": c.get("msgs_enviadas_hoje"),
                "pode_prospectar": c.get("pode_prospectar"),
                "pode_followup": c.get("pode_followup"),
                "pode_responder": c.get("pode_responder"),
            }
            for c in chips
        ],
        "count": len(chips),
        "tipo_mensagem": tipo_mensagem,
    }


# ════════════════════════════════════════════════════════════
# INSTANCE MANAGEMENT (Sprint 40)
# ════════════════════════════════════════════════════════════


class CreateInstanceRequest(BaseModel):
    """Request para criar nova instancia."""

    telefone: str
    instance_name: Optional[str] = None


@router.post("/instances")
async def create_instance(request: CreateInstanceRequest):
    """
    Cria uma nova instancia WhatsApp.

    Registra o chip no banco e cria a instancia na Evolution API.
    """
    result = await instance_manager.criar_instancia(
        telefone=request.telefone,
        instance_name=request.instance_name,
    )

    if not result.success:
        raise HTTPException(500, result.error or "Falha ao criar instancia")

    return {
        "success": True,
        "instance_name": result.instance_name,
        "chip_id": result.chip_id,
    }


@router.get("/instances/{instance_name}/qr-code")
async def get_instance_qr_code(instance_name: str):
    """
    Obtem QR code para pareamento da instancia.

    O QR code e retornado em base64 para exibicao no frontend.
    """
    result = await instance_manager.obter_qr_code(instance_name)

    if not result.success:
        raise HTTPException(500, result.error or "Falha ao obter QR code")

    return {
        "qr_code": result.qr_code,
        "state": result.state,
        "pairing_code": result.pairing_code,
    }


@router.get("/instances/{instance_name}/connection-state")
async def get_instance_connection_state(instance_name: str):
    """
    Verifica o estado da conexao de uma instancia.

    Estados possiveis: open, close, connecting
    """
    result = await instance_manager.verificar_conexao(instance_name)

    if not result.success:
        raise HTTPException(500, result.error or "Falha ao verificar conexao")

    return {
        "state": result.state,
        "connected": result.connected,
    }


@router.delete("/instances/{instance_name}")
async def delete_instance(instance_name: str):
    """
    Deleta uma instancia WhatsApp.

    Remove da Evolution API e atualiza status do chip para cancelled.
    """
    result = await instance_manager.deletar_instancia(instance_name)

    if not result.success:
        raise HTTPException(500, result.error or "Falha ao deletar instancia")

    return {
        "success": True,
        "message": f"Instancia {instance_name} deletada com sucesso",
    }
