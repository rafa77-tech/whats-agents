"""
Endpoints para gerenciamento de campanhas.

Sprint 35 - Epic 05: Atualizado para usar novos modulos
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.supabase import supabase
from app.services.segmentacao import segmentacao_service
from app.services.campanhas import (
    campanha_executor,
    campanha_repository,
    AudienceFilters,
    StatusCampanha,
    TipoCampanha,
)

router = APIRouter(prefix="/campanhas", tags=["campanhas"])


class CriarCampanhaRequest(BaseModel):
    """Request para criar campanha."""
    nome_template: str = Field(..., description="Nome da campanha")
    tipo_campanha: str = Field(
        default="oferta",
        description="Tipo: discovery, oferta, oferta_plantao, reativacao, followup"
    )
    corpo: Optional[str] = Field(
        None,
        description="Corpo da mensagem com placeholders {nome}, {especialidade}"
    )
    tom: Optional[str] = Field(default="amigavel", description="Tom da mensagem")
    objetivo: Optional[str] = Field(None, description="Objetivo da campanha")
    especialidades: Optional[List[str]] = Field(
        default=None,
        description="Filtro de especialidades"
    )
    regioes: Optional[List[str]] = Field(
        default=None,
        description="Filtro de regioes"
    )
    quantidade_alvo: int = Field(default=50, description="Quantidade alvo de envios")
    agendar_para: Optional[datetime] = Field(
        None,
        description="Data/hora para agendamento"
    )
    pode_ofertar: bool = Field(default=True, description="Se pode ofertar vagas")


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
    # Validar tipo de campanha
    try:
        tipo = TipoCampanha(dados.tipo_campanha)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de campanha invalido: {dados.tipo_campanha}"
        )

    # Montar filtros para contagem
    filtros = {}
    if dados.especialidades:
        filtros["especialidade"] = dados.especialidades[0]
    if dados.regioes:
        filtros["regiao"] = dados.regioes[0]

    # Contar destinatarios
    total_destinatarios = await segmentacao_service.contar_segmento(filtros)

    # Criar audience_filters
    audience_filters = AudienceFilters(
        regioes=dados.regioes or [],
        especialidades=dados.especialidades or [],
        quantidade_alvo=dados.quantidade_alvo,
    )

    # Criar campanha usando o repository
    campanha = await campanha_repository.criar(
        nome_template=dados.nome_template,
        tipo_campanha=tipo,
        corpo=dados.corpo,
        tom=dados.tom,
        objetivo=dados.objetivo,
        agendar_para=dados.agendar_para,
        audience_filters=audience_filters,
        pode_ofertar=dados.pode_ofertar,
    )

    if not campanha:
        raise HTTPException(status_code=500, detail="Erro ao criar campanha")

    # Atualizar total de destinatarios
    await campanha_repository.atualizar_total_destinatarios(
        campanha.id,
        total_destinatarios
    )

    return CampanhaResponse(
        id=campanha.id,
        nome_template=campanha.nome_template,
        tipo_campanha=campanha.tipo_campanha.value,
        status=campanha.status.value,
        total_destinatarios=total_destinatarios,
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
    # Verificar se campanha existe
    campanha = await campanha_repository.buscar_por_id(campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    # Verificar status
    if campanha.status not in (StatusCampanha.AGENDADA, StatusCampanha.RASCUNHO):
        raise HTTPException(
            status_code=400,
            detail=f"Campanha com status '{campanha.status.value}' nao pode ser iniciada"
        )

    # Executar campanha
    sucesso = await campanha_executor.executar(campanha_id)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao executar campanha")

    return {
        "status": "iniciada",
        "campanha_id": campanha_id,
        "message": "Campanha iniciada com sucesso"
    }


@router.post("/segmento/preview")
async def preview_segmento(filtros: Dict[str, Any]):
    """
    Preview de um segmento antes de criar campanha.

    Retorna contagem e amostra de medicos.
    """
    total = await segmentacao_service.contar_segmento(filtros)
    amostra = await segmentacao_service.buscar_segmento(filtros, limite=10)

    return {
        "total": total,
        "amostra": [
            {
                "nome": m.get("primeiro_nome"),
                "especialidade": m.get("especialidade_nome"),
                "regiao": m.get("regiao")
            }
            for m in amostra
        ]
    }


@router.get("/{campanha_id}/relatorio")
async def relatorio_campanha(campanha_id: int):
    """
    Retorna relatorio completo da campanha.

    Usa nomes de colunas atualizados.
    """
    # Buscar campanha usando repository
    campanha = await campanha_repository.buscar_por_id(campanha_id)

    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    # Buscar envios da campanha na fila_mensagens
    envios_resp = (
        supabase.table("fila_mensagens")
        .select("status")
        .eq("metadata->>campanha_id", str(campanha_id))
        .execute()
    )

    envios = envios_resp.data or []

    enviados_fila = len([e for e in envios if e["status"] == "enviada"])
    erros = len([e for e in envios if e["status"] == "erro"])
    pendentes = len([e for e in envios if e["status"] == "pendente"])

    return {
        "campanha_id": campanha_id,
        "nome": campanha.nome_template,
        "tipo_campanha": campanha.tipo_campanha.value,
        "status": campanha.status.value,
        "contadores": {
            "total_destinatarios": campanha.total_destinatarios,
            "enviados": campanha.enviados,
            "entregues": campanha.entregues,
            "respondidos": campanha.respondidos,
        },
        "fila": {
            "total": len(envios),
            "enviados": enviados_fila,
            "erros": erros,
            "pendentes": pendentes,
            "taxa_entrega": enviados_fila / len(envios) if envios else 0
        },
        "periodo": {
            "criada_em": campanha.created_at.isoformat() if campanha.created_at else None,
            "agendada_para": campanha.agendar_para.isoformat() if campanha.agendar_para else None,
            "iniciada_em": campanha.iniciada_em.isoformat() if campanha.iniciada_em else None,
            "concluida_em": campanha.concluida_em.isoformat() if campanha.concluida_em else None,
        },
        "audience_filters": campanha.audience_filters.to_dict() if campanha.audience_filters else {},
    }


@router.get("/")
async def listar_campanhas(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    limit: int = 50,
):
    """
    Lista campanhas com filtros opcionais.
    """
    query = supabase.table("campanhas").select("*")

    if status:
        query = query.eq("status", status)
    if tipo:
        query = query.eq("tipo_campanha", tipo)

    query = query.order("created_at", desc=True).limit(limit)

    resp = query.execute()

    campanhas = []
    for row in resp.data or []:
        campanhas.append({
            "id": row["id"],
            "nome_template": row.get("nome_template"),
            "tipo_campanha": row.get("tipo_campanha"),
            "status": row.get("status"),
            "total_destinatarios": row.get("total_destinatarios", 0),
            "enviados": row.get("enviados", 0),
            "entregues": row.get("entregues", 0),
            "respondidos": row.get("respondidos", 0),
            "created_at": row.get("created_at"),
            "agendar_para": row.get("agendar_para"),
        })

    return {"campanhas": campanhas, "total": len(campanhas)}


@router.get("/{campanha_id}")
async def buscar_campanha(campanha_id: int):
    """
    Busca detalhes de uma campanha.
    """
    campanha = await campanha_repository.buscar_por_id(campanha_id)

    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    return campanha.to_dict()


@router.patch("/{campanha_id}/status")
async def atualizar_status_campanha(campanha_id: int, novo_status: str):
    """
    Atualiza status de uma campanha.
    """
    # Validar status
    try:
        status = StatusCampanha(novo_status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Status invalido: {novo_status}"
        )

    # Verificar se campanha existe
    campanha = await campanha_repository.buscar_por_id(campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")

    # Atualizar status
    sucesso = await campanha_repository.atualizar_status(campanha_id, status)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao atualizar status")

    return {
        "campanha_id": campanha_id,
        "status_anterior": campanha.status.value,
        "status_novo": status.value,
    }
