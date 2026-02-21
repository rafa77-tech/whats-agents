"""
Endpoints para gerenciamento de campanhas.

Sprint 35 - Epic 05: Atualizado para usar novos modulos
Fase 2 DDD: Delega ao CampanhasApplicationService (ADR-007)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.contexts.campanhas.application import get_campanhas_service
from app.core.exceptions import DatabaseError, NotFoundError, ValidationError

router = APIRouter(prefix="/campanhas", tags=["campanhas"])


def _handle_domain_exception(exc: Exception):
    """Converte exceções de domínio para HTTPException."""
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, DatabaseError):
        raise HTTPException(status_code=500, detail=str(exc))
    raise HTTPException(status_code=500, detail="Erro interno inesperado")


class CriarCampanhaRequest(BaseModel):
    """Request para criar campanha."""

    nome_template: str = Field(..., description="Nome da campanha")
    tipo_campanha: str = Field(
        default="oferta",
        description="Tipo: discovery, oferta, oferta_plantao, reativacao, followup",
    )
    corpo: Optional[str] = Field(
        None, description="Corpo da mensagem com placeholders {nome}, {especialidade}"
    )
    tom: Optional[str] = Field(default="amigavel", description="Tom da mensagem")
    objetivo: Optional[str] = Field(None, description="Objetivo da campanha")
    especialidades: Optional[List[str]] = Field(
        default=None, description="Filtro de especialidades"
    )
    regioes: Optional[List[str]] = Field(default=None, description="Filtro de regioes")
    quantidade_alvo: int = Field(default=50, description="Quantidade alvo de envios")
    modo_selecao: str = Field(
        default="deterministico",
        description="Modo de selecao: deterministico (prioriza nunca contatados) ou aleatorio",
    )
    agendar_para: Optional[datetime] = Field(None, description="Data/hora para agendamento")
    pode_ofertar: bool = Field(default=True, description="Se pode ofertar vagas")
    chips_excluidos: Optional[List[str]] = Field(
        default=None, description="IDs de chips a NAO usar nesta campanha"
    )


class CampanhaResponse(BaseModel):
    """Response de campanha."""

    id: int
    nome_template: str
    tipo_campanha: str
    status: str
    total_destinatarios: int
    enviados: int
    entregues: int
    respondidos: int
    created_at: Optional[str] = None


@router.post("/", response_model=CampanhaResponse)
async def criar_campanha(dados: CriarCampanhaRequest):
    """
    Cria nova campanha.

    Usa os novos nomes de colunas do schema atualizado.
    """
    service = get_campanhas_service()

    try:
        campanha = await service.criar_campanha(
            nome_template=dados.nome_template,
            tipo_campanha=dados.tipo_campanha,
            corpo=dados.corpo,
            tom=dados.tom,
            objetivo=dados.objetivo,
            especialidades=dados.especialidades,
            regioes=dados.regioes,
            quantidade_alvo=dados.quantidade_alvo,
            modo_selecao=dados.modo_selecao,
            agendar_para=dados.agendar_para,
            pode_ofertar=dados.pode_ofertar,
            chips_excluidos=dados.chips_excluidos,
        )
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)

    return CampanhaResponse(
        id=campanha.id,
        nome_template=campanha.nome_template,
        tipo_campanha=campanha.tipo_campanha.value,
        status=campanha.status.value,
        total_destinatarios=campanha.total_destinatarios,
        enviados=campanha.enviados,
        entregues=campanha.entregues,
        respondidos=campanha.respondidos,
        created_at=campanha.created_at.isoformat() if campanha.created_at else None,
    )


@router.post("/{campanha_id}/iniciar")
async def iniciar_campanha(campanha_id: int):
    """
    Inicia execucao de campanha.

    Usa o CampanhaExecutor para processar a campanha.
    """
    service = get_campanhas_service()

    try:
        return await service.executar_campanha(campanha_id)
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)


@router.post("/segmento/preview")
async def preview_segmento(filtros: Dict[str, Any]):
    """
    Preview de um segmento antes de criar campanha.

    Retorna contagem e amostra de medicos.
    """
    service = get_campanhas_service()

    return await service.preview_segmento(filtros)


@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: int):
    """
    Retorna relatorio completo da campanha.

    Usa nomes de colunas atualizados.
    """
    service = get_campanhas_service()

    try:
        return await service.relatorio_campanha(campanha_id)
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)


@router.get("/")
async def listar_campanhas(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 50,
):
    """
    Lista campanhas com filtros opcionais.
    """
    service = get_campanhas_service()

    try:
        return await service.listar_campanhas(status=status, tipo=tipo, limit=limit)
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)


@router.get("/{campanha_id}")
async def buscar_campanha(campanha_id: int):
    """
    Busca detalhes de uma campanha.
    """
    service = get_campanhas_service()

    try:
        campanha = await service.buscar_campanha(campanha_id)
        return campanha.to_dict()
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)


@router.patch("/{campanha_id}/status")
async def atualizar_status_campanha(campanha_id: int, novo_status: str):
    """
    Atualiza status de uma campanha.
    """
    service = get_campanhas_service()

    try:
        return await service.atualizar_status(campanha_id, novo_status)
    except (NotFoundError, ValidationError, DatabaseError) as exc:
        _handle_domain_exception(exc)
