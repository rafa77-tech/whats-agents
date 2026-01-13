"""
API de gerenciamento do Group Entry Engine.

Sprint 25 - E12 - S12.5

Endpoints para:
- Importação de links (CSV/Excel)
- Validação de links
- Agendamento de entradas
- Monitoramento da fila
- Configuração de limites
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel

from app.services.supabase import supabase
from app.services.group_entry.importer import (
    importar_csv,
    importar_excel,
    listar_links,
    contar_links_por_status,
)
from app.services.group_entry.validator import (
    validar_link,
    validar_links_pendentes,
    revalidar_link,
)
from app.services.group_entry.scheduler import (
    agendar_entrada,
    agendar_lote,
    buscar_proximas_entradas,
    cancelar_agendamento,
    estatisticas_fila,
)
from app.services.group_entry.worker import (
    processar_fila,
    processar_entrada,
    verificar_entradas_aguardando,
)
from app.services.group_entry.chip_selector import (
    listar_chips_disponiveis,
    capacidade_total_disponivel,
    buscar_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/group-entry", tags=["group-entry"])


# =============================================================================
# Models
# =============================================================================


class ImportResult(BaseModel):
    """Resultado de importação."""

    total_linhas: int
    importados: int
    duplicados: int
    invalidos: int
    erros: list[str]


class ValidationResult(BaseModel):
    """Resultado de validação."""

    valido: bool
    grupo_nome: Optional[str] = None
    grupo_tamanho: Optional[int] = None
    erro: Optional[str] = None


class ScheduleRequest(BaseModel):
    """Request para agendar entrada."""

    link_id: str
    prioridade: int = 50
    chip_id: Optional[str] = None


class BatchScheduleRequest(BaseModel):
    """Request para agendar lote."""

    limite: int = 10
    categoria: Optional[str] = None


class ConfigUpdate(BaseModel):
    """Atualização de configuração."""

    trust_minimo_grupos: Optional[int] = None
    max_falhas_consecutivas: Optional[int] = None
    limite_expansao: Optional[int] = None
    limite_pre_operacao: Optional[int] = None
    limite_operacao: Optional[int] = None
    limite_6h_expansao: Optional[int] = None
    limite_6h_pre_operacao: Optional[int] = None
    limite_6h_operacao: Optional[int] = None
    delay_min_expansao: Optional[int] = None
    delay_min_pre_operacao: Optional[int] = None
    delay_min_operacao: Optional[int] = None


# =============================================================================
# Importação
# =============================================================================


@router.post("/import/csv", response_model=ImportResult)
async def api_importar_csv(
    file: UploadFile = File(...),
    categoria: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
):
    """
    Importa links de grupos de um arquivo CSV.

    Colunas esperadas: name, url/invite_code/link, state, category
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Arquivo deve ser CSV")

    # Salvar arquivo temporário
    temp_path = Path(f"/tmp/{file.filename}")
    content = await file.read()
    temp_path.write_bytes(content)

    try:
        resultado = await importar_csv(temp_path, categoria=categoria, estado=estado)
        return ImportResult(**resultado)
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/import/excel", response_model=ImportResult)
async def api_importar_excel(
    file: UploadFile = File(...),
    categoria: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
):
    """
    Importa links de grupos de um arquivo Excel (.xlsx).
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Arquivo deve ser Excel (.xlsx)")

    temp_path = Path(f"/tmp/{file.filename}")
    content = await file.read()
    temp_path.write_bytes(content)

    try:
        resultado = await importar_excel(temp_path, categoria=categoria, estado=estado)
        return ImportResult(**resultado)
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# Links
# =============================================================================


@router.get("/links")
async def api_listar_links(
    status: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    limite: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Lista links de grupos com filtros.
    """
    links = await listar_links(
        status=status, categoria=categoria, limite=limite, offset=offset
    )
    return {"links": links, "total": len(links)}


@router.get("/links/stats")
async def api_estatisticas_links():
    """
    Retorna estatísticas de links por status.
    """
    contagem = await contar_links_por_status()
    total = sum(contagem.values())
    return {"total": total, "por_status": contagem}


@router.get("/links/{link_id}")
async def api_buscar_link(link_id: str):
    """
    Busca um link específico.
    """
    result = (
        supabase.table("group_links").select("*").eq("id", link_id).single().execute()
    )

    if not result.data:
        raise HTTPException(404, "Link não encontrado")

    return result.data


# =============================================================================
# Validação
# =============================================================================


@router.post("/validate/{link_id}", response_model=ValidationResult)
async def api_validar_link(link_id: str):
    """
    Valida um link específico.
    """
    result = (
        supabase.table("group_links")
        .select("invite_code")
        .eq("id", link_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(404, "Link não encontrado")

    validacao = await validar_link(result.data["invite_code"])
    return ValidationResult(**validacao)


@router.post("/validate/batch")
async def api_validar_lote(limite: int = Query(50, le=100)):
    """
    Valida lote de links pendentes.
    """
    resultado = await validar_links_pendentes(limite=limite)
    return resultado


@router.post("/revalidate/{link_id}", response_model=ValidationResult)
async def api_revalidar_link(link_id: str):
    """
    Revalida um link (para links inválidos ou com erro).
    """
    validacao = await revalidar_link(link_id)
    return ValidationResult(**validacao)


# =============================================================================
# Agendamento
# =============================================================================


@router.post("/schedule")
async def api_agendar_entrada(request: ScheduleRequest):
    """
    Agenda entrada em um grupo específico.
    """
    entrada = await agendar_entrada(
        link_id=request.link_id,
        prioridade=request.prioridade,
        chip_id=request.chip_id,
    )

    if not entrada:
        raise HTTPException(400, "Não foi possível agendar entrada")

    return entrada


@router.post("/schedule/batch")
async def api_agendar_lote(request: BatchScheduleRequest):
    """
    Agenda lote de links validados.
    """
    resultado = await agendar_lote(limite=request.limite, categoria=request.categoria)
    return resultado


@router.get("/queue")
async def api_listar_fila(limite: int = Query(20, le=100)):
    """
    Lista próximas entradas na fila.
    """
    entradas = await buscar_proximas_entradas(limite=limite)
    return {"entradas": entradas, "total": len(entradas)}


@router.get("/queue/stats")
async def api_estatisticas_fila():
    """
    Retorna estatísticas da fila.
    """
    stats = await estatisticas_fila()
    return stats


@router.delete("/queue/{queue_id}")
async def api_cancelar_agendamento(queue_id: str):
    """
    Cancela um agendamento específico.
    """
    cancelado = await cancelar_agendamento(queue_id)

    if not cancelado:
        raise HTTPException(404, "Agendamento não encontrado")

    return {"cancelado": True}


# =============================================================================
# Processamento
# =============================================================================


@router.post("/process")
async def api_processar_fila(limite: int = Query(5, le=20)):
    """
    Processa entradas pendentes na fila.
    """
    resultado = await processar_fila(limite=limite)
    return resultado


@router.post("/process/{queue_id}")
async def api_processar_entrada(queue_id: str):
    """
    Processa uma entrada específica.
    """
    status = await processar_entrada(queue_id)
    return {"status": status}


@router.post("/check-pending")
async def api_verificar_aguardando():
    """
    Verifica entradas aguardando aprovação.
    """
    resultado = await verificar_entradas_aguardando()
    return resultado


# =============================================================================
# Chips
# =============================================================================


@router.get("/chips")
async def api_listar_chips():
    """
    Lista chips disponíveis para entrada em grupos.
    """
    chips = await listar_chips_disponiveis()
    return {"chips": chips, "total": len(chips)}


@router.get("/capacity")
async def api_capacidade():
    """
    Retorna capacidade total disponível.
    """
    capacidade = await capacidade_total_disponivel()
    return capacidade


# =============================================================================
# Configuração
# =============================================================================


@router.get("/config")
async def api_buscar_config():
    """
    Retorna configuração atual.
    """
    result = supabase.table("group_entry_config").select("*").limit(1).execute()

    if not result.data:
        raise HTTPException(404, "Configuração não encontrada")

    return result.data[0]


@router.patch("/config")
async def api_atualizar_config(update: ConfigUpdate):
    """
    Atualiza configuração de limites.
    """
    # Filtrar apenas campos não-nulos
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(400, "Nenhum campo para atualizar")

    update_data["updated_at"] = datetime.now(UTC).isoformat()

    result = supabase.table("group_entry_config").update(update_data).execute()

    return {"atualizado": True, "campos": list(update_data.keys())}


# =============================================================================
# Dashboard
# =============================================================================


@router.get("/dashboard")
async def api_dashboard():
    """
    Retorna visão consolidada para dashboard.
    """
    # Links por status
    links_stats = await contar_links_por_status()

    # Fila
    fila_stats = await estatisticas_fila()

    # Capacidade
    capacidade = await capacidade_total_disponivel()

    # Config
    config = await buscar_config()

    return {
        "links": {
            "total": sum(links_stats.values()),
            "por_status": links_stats,
        },
        "fila": fila_stats,
        "capacidade": capacidade,
        "config": {
            "trust_minimo": config["trust_minimo"],
            "max_falhas": config["max_falhas"],
        },
    }
