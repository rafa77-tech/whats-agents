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
from app.services.chips.sync_evolution import sincronizar_chips_com_evolution, buscar_estado_instancia

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


class ReactivateChipRequest(BaseModel):
    """Request para reativar um chip banido/cancelado."""

    motivo: str
    para_status: str = "pending"


@router.post("/{chip_id}/reactivate")
async def reactivate_chip(chip_id: str, request: ReactivateChipRequest):
    """
    Reativa um chip banido ou cancelado.

    Usado quando um chip volta a funcionar apos recurso ou outro motivo.
    O chip vai para status 'pending' (precisa reconectar) ou 'ready'.

    para_status: 'pending' (default, precisa QR code) ou 'ready' (ja conectado)
    """
    if request.para_status not in ["pending", "ready"]:
        raise HTTPException(400, "para_status deve ser 'pending' ou 'ready'")

    # Verificar se chip existe e esta banido/cancelado
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        raise HTTPException(404, "Chip nao encontrado")

    chip = result.data
    if chip["status"] not in ["banned", "cancelled"]:
        raise HTTPException(
            400,
            f"Chip nao pode ser reativado (status atual: {chip['status']}). "
            "Apenas chips banidos ou cancelados podem ser reativados."
        )

    # Atualizar status e registrar motivo
    update_data = {
        "status": request.para_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Resetar trust score para valor inicial se estava banido
    if chip["status"] == "banned":
        update_data["trust_score"] = 50  # Score inicial conservador

    supabase.table("chips").update(update_data).eq("id", chip_id).execute()

    # Registrar operacao no historico
    supabase.table("orchestrator_operations").insert({
        "chip_id": chip_id,
        "operacao": "reactivate",
        "motivo": request.motivo,
        "metadata": {
            "status_anterior": chip["status"],
            "status_novo": request.para_status,
        },
        "sucesso": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    logger.info(
        f"Chip {chip_id} reativado: {chip['status']} -> {request.para_status}. "
        f"Motivo: {request.motivo}"
    )

    return {
        "success": True,
        "chip_id": chip_id,
        "status_anterior": chip["status"],
        "status_novo": request.para_status,
        "motivo": request.motivo,
        "message": f"Chip reativado com sucesso. "
                   f"{'Gere o QR Code para reconectar.' if request.para_status == 'pending' else ''}"
    }


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


@router.post("/sync-evolution")
async def sync_chips_with_evolution():
    """
    Sincroniza chips com Evolution API.

    Detecta conexoes/desconexoes e atualiza status dos chips.
    """
    stats = await sincronizar_chips_com_evolution()
    return {"status": "ok", "stats": stats}


@router.get("/{chip_id}/check-connection")
async def check_chip_connection(chip_id: str):
    """
    Verifica estado de conexao de um chip especifico na Evolution API.

    Util para verificar se um chip recem-reativado ja esta conectado.
    """
    # Buscar chip
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        raise HTTPException(404, "Chip nao encontrado")

    chip = result.data
    instance_name = chip.get("instance_name")

    if not instance_name:
        raise HTTPException(400, "Chip nao possui instance_name configurado")

    # Verificar estado na Evolution
    estado = await buscar_estado_instancia(instance_name)

    if not estado:
        return {
            "chip_id": chip_id,
            "instance_name": instance_name,
            "connected": False,
            "state": "unknown",
            "message": "Nao foi possivel verificar estado na Evolution API"
        }

    # Estado da Evolution: 'open' = conectado, 'close' = desconectado
    is_connected = estado.get("state") == "open" or estado.get("instance", {}).get("state") == "open"
    state = estado.get("state") or estado.get("instance", {}).get("state", "unknown")

    # Atualizar status do chip se necessario
    if is_connected and chip["status"] == "pending":
        supabase.table("chips").update({
            "status": "warming",
            "evolution_connected": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", chip_id).execute()

        return {
            "chip_id": chip_id,
            "instance_name": instance_name,
            "connected": True,
            "state": state,
            "status_atualizado": True,
            "novo_status": "warming",
            "message": "Chip conectado! Status atualizado para warming."
        }

    # Atualizar flag de conexao
    if chip.get("evolution_connected") != is_connected:
        supabase.table("chips").update({
            "evolution_connected": is_connected,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", chip_id).execute()

    return {
        "chip_id": chip_id,
        "instance_name": instance_name,
        "connected": is_connected,
        "state": state,
        "status_atual": chip["status"],
        "message": "Conectado" if is_connected else "Desconectado"
    }


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


# ════════════════════════════════════════════════════════════
# DIAGNÓSTICO MULTI-CHIP (Debug)
# ════════════════════════════════════════════════════════════


@router.get("/diagnostico-ping")
async def diagnostico_ping():
    """Teste simples para verificar se a rota está acessível."""
    return {"status": "ok", "message": "Rota diagnostico acessivel"}


@router.get("/diagnostico")
async def diagnosticar_multi_chip(
    tipo_mensagem: str = Query("prospeccao", description="prospeccao, followup, ou resposta"),
    telefone_teste: Optional[str] = Query(None, description="Telefone para teste de envio"),
    enviar_teste: bool = Query(False, description="Se True, envia mensagem de teste"),
):
    """
    Diagnóstico completo do sistema multi-chip.

    Testa cada etapa do fluxo:
    1. Verifica MULTI_CHIP_ENABLED
    2. Busca chips elegíveis
    3. Testa seleção de chip
    4. Testa criação do provider
    5. Verifica conexão do provider
    6. (Opcional) Envia mensagem de teste

    Use para identificar onde o sistema está falhando.
    """
    import traceback

    # Wrapper global para capturar qualquer erro não tratado
    try:
        return await _executar_diagnostico(tipo_mensagem, telefone_teste, enviar_teste)
    except Exception as e:
        return {
            "erro": "Exceção não tratada",
            "tipo": type(e).__name__,
            "mensagem": str(e),
            "traceback": traceback.format_exc(),
        }


async def _executar_diagnostico(
    tipo_mensagem: str,
    telefone_teste: Optional[str],
    enviar_teste: bool,
):
    """Execução interna do diagnóstico."""
    import traceback

    try:
        from app.core.config import settings
        from app.services.whatsapp_providers import get_provider
    except Exception as import_error:
        return {
            "erro": "Falha nos imports",
            "detalhe": str(import_error),
            "traceback": traceback.format_exc(),
        }

    diagnostico = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "etapas": [],
        "resultado": "pendente",
        "erro_em": None,
    }

    try:
        # ─────────────────────────────────────────────────────────
        # ETAPA 1: Verificar MULTI_CHIP_ENABLED
        # ─────────────────────────────────────────────────────────
        multi_chip_enabled = getattr(settings, "MULTI_CHIP_ENABLED", False)
        diagnostico["etapas"].append({
            "etapa": 1,
            "nome": "MULTI_CHIP_ENABLED",
            "status": "ok" if multi_chip_enabled else "erro",
            "valor": multi_chip_enabled,
            "detalhe": "Habilitado" if multi_chip_enabled else "DESABILITADO - mensagens vão para Evolution API legada",
        })

        if not multi_chip_enabled:
            diagnostico["resultado"] = "falha"
            diagnostico["erro_em"] = "MULTI_CHIP_ENABLED está False"
            return diagnostico
    except Exception as e:
        diagnostico["etapas"].append({
            "etapa": 1,
            "nome": "MULTI_CHIP_ENABLED",
            "status": "erro",
            "erro": str(e),
        })
        diagnostico["resultado"] = "falha"
        diagnostico["erro_em"] = f"Erro ao verificar config: {e}"
        return diagnostico

    # ─────────────────────────────────────────────────────────
    # ETAPA 2: Buscar chips no banco
    # ─────────────────────────────────────────────────────────
    try:
        # Query direta para ver o que existe
        result = supabase.table("chips").select(
            "id, telefone, status, tipo, provider, trust_score, "
            "pode_prospectar, pode_followup, pode_responder, "
            "evolution_connected, cooldown_until, circuit_breaker_ativo, "
            "msgs_enviadas_hoje, limite_dia, limite_hora"
        ).eq("status", "active").neq("tipo", "listener").execute()

        chips_ativos = result.data or []

        diagnostico["etapas"].append({
            "etapa": 2,
            "nome": "Buscar chips ativos",
            "status": "ok" if chips_ativos else "aviso",
            "quantidade": len(chips_ativos),
            "chips": [
                {
                    "id": c["id"][:8] + "...",
                    "telefone": c["telefone"],
                    "provider": c.get("provider"),
                    "trust_score": c.get("trust_score"),
                    "pode_prospectar": c.get("pode_prospectar"),
                    "evolution_connected": c.get("evolution_connected"),
                    "circuit_breaker_ativo": c.get("circuit_breaker_ativo"),
                }
                for c in chips_ativos
            ],
            "detalhe": f"{len(chips_ativos)} chip(s) ativo(s) encontrado(s)" if chips_ativos else "NENHUM chip ativo encontrado",
        })

        if not chips_ativos:
            diagnostico["resultado"] = "falha"
            diagnostico["erro_em"] = "Nenhum chip com status='active'"
            return diagnostico

    except Exception as e:
        diagnostico["etapas"].append({
            "etapa": 2,
            "nome": "Buscar chips ativos",
            "status": "erro",
            "erro": str(e),
        })
        diagnostico["resultado"] = "falha"
        diagnostico["erro_em"] = f"Erro ao buscar chips: {e}"
        return diagnostico

    # ─────────────────────────────────────────────────────────
    # ETAPA 3: Testar ChipSelector
    # ─────────────────────────────────────────────────────────
    try:
        chip_selecionado = await chip_selector.selecionar_chip(
            tipo_mensagem=tipo_mensagem,
            telefone_destino=telefone_teste,
        )

        if chip_selecionado:
            diagnostico["etapas"].append({
                "etapa": 3,
                "nome": f"Selecionar chip ({tipo_mensagem})",
                "status": "ok",
                "chip_selecionado": {
                    "id": chip_selecionado["id"][:8] + "...",
                    "telefone": chip_selecionado["telefone"],
                    "provider": chip_selecionado.get("provider"),
                    "trust_score": chip_selecionado.get("trust_score"),
                },
                "detalhe": f"Chip {chip_selecionado['telefone']} selecionado",
            })
        else:
            # Tentar entender por que não selecionou
            motivos = []
            for chip in chips_ativos:
                # Verificar trust mínimo
                trust_min = {"prospeccao": 80, "followup": 60, "resposta": 40}.get(tipo_mensagem, 40)
                if (chip.get("trust_score") or 0) < trust_min:
                    motivos.append(f"{chip['telefone']}: trust {chip.get('trust_score')} < {trust_min}")
                    continue

                # Verificar permissão
                perm_field = {"prospeccao": "pode_prospectar", "followup": "pode_followup", "resposta": "pode_responder"}.get(tipo_mensagem)
                if perm_field and not chip.get(perm_field):
                    motivos.append(f"{chip['telefone']}: {perm_field}=false")
                    continue

                # Verificar circuit breaker
                if chip.get("circuit_breaker_ativo"):
                    motivos.append(f"{chip['telefone']}: circuit_breaker_ativo")
                    continue

                # Verificar conexão (Evolution only)
                if chip.get("provider") == "evolution" and not chip.get("evolution_connected"):
                    motivos.append(f"{chip['telefone']}: evolution não conectado")
                    continue

            diagnostico["etapas"].append({
                "etapa": 3,
                "nome": f"Selecionar chip ({tipo_mensagem})",
                "status": "erro",
                "chip_selecionado": None,
                "motivos_rejeicao": motivos if motivos else ["Motivo desconhecido - verificar logs"],
                "detalhe": "Nenhum chip passou nos filtros do selector",
            })
            diagnostico["resultado"] = "falha"
            diagnostico["erro_em"] = "ChipSelector retornou None"
            return diagnostico

    except Exception as e:
        diagnostico["etapas"].append({
            "etapa": 3,
            "nome": f"Selecionar chip ({tipo_mensagem})",
            "status": "erro",
            "erro": str(e),
        })
        diagnostico["resultado"] = "falha"
        diagnostico["erro_em"] = f"Exceção no ChipSelector: {e}"
        return diagnostico

    # ─────────────────────────────────────────────────────────
    # ETAPA 4: Testar criação do Provider
    # ─────────────────────────────────────────────────────────
    try:
        provider = get_provider(chip_selecionado)

        diagnostico["etapas"].append({
            "etapa": 4,
            "nome": "Criar provider",
            "status": "ok",
            "provider_type": provider.provider_type.value if hasattr(provider, 'provider_type') else "unknown",
            "detalhe": f"Provider {type(provider).__name__} criado com sucesso",
        })

    except Exception as e:
        diagnostico["etapas"].append({
            "etapa": 4,
            "nome": "Criar provider",
            "status": "erro",
            "erro": str(e),
            "detalhe": "Falha ao criar provider - verificar credenciais do chip",
        })
        diagnostico["resultado"] = "falha"
        diagnostico["erro_em"] = f"Exceção ao criar provider: {e}"
        return diagnostico

    # ─────────────────────────────────────────────────────────
    # ETAPA 5: Verificar conexão do provider
    # ─────────────────────────────────────────────────────────
    try:
        status = await provider.get_status()

        diagnostico["etapas"].append({
            "etapa": 5,
            "nome": "Verificar conexão",
            "status": "ok" if status.connected else "aviso",
            "connected": status.connected,
            "state": status.state,
            "detalhe": "Conectado" if status.connected else f"DESCONECTADO (state={status.state})",
        })

        if not status.connected:
            diagnostico["resultado"] = "aviso"
            diagnostico["erro_em"] = f"Provider não conectado (state={status.state})"
            # Continua mesmo assim para o teste de envio

    except Exception as e:
        diagnostico["etapas"].append({
            "etapa": 5,
            "nome": "Verificar conexão",
            "status": "erro",
            "erro": str(e),
        })
        # Não falha aqui, tenta enviar mesmo assim

    # ─────────────────────────────────────────────────────────
    # ETAPA 6: (Opcional) Enviar mensagem de teste
    # ─────────────────────────────────────────────────────────
    if enviar_teste and telefone_teste:
        try:
            mensagem_teste = f"[TESTE DIAGNÓSTICO] Multi-chip funcionando! Chip: {chip_selecionado['telefone'][-4:]}"
            result = await provider.send_text(telefone_teste, mensagem_teste)

            diagnostico["etapas"].append({
                "etapa": 6,
                "nome": "Enviar mensagem teste",
                "status": "ok" if result.success else "erro",
                "success": result.success,
                "message_id": result.message_id if result.success else None,
                "error": result.error if not result.success else None,
                "detalhe": f"Mensagem enviada (id={result.message_id})" if result.success else f"Falha: {result.error}",
            })

            if result.success:
                diagnostico["resultado"] = "sucesso"
            else:
                diagnostico["resultado"] = "falha"
                diagnostico["erro_em"] = f"Falha no envio: {result.error}"

        except Exception as e:
            diagnostico["etapas"].append({
                "etapa": 6,
                "nome": "Enviar mensagem teste",
                "status": "erro",
                "erro": str(e),
            })
            diagnostico["resultado"] = "falha"
            diagnostico["erro_em"] = f"Exceção no envio: {e}"
    else:
        if diagnostico["resultado"] == "pendente":
            diagnostico["resultado"] = "ok_sem_envio"
        diagnostico["etapas"].append({
            "etapa": 6,
            "nome": "Enviar mensagem teste",
            "status": "pulado",
            "detalhe": "Use enviar_teste=true e telefone_teste=5511... para testar envio real",
        })

    return diagnostico
