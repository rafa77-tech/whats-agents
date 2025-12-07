"""
Endpoints para gerenciamento de campanhas.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.supabase import supabase
from app.services.fila import fila_service
from app.services.segmentacao import segmentacao_service
from app.templates.mensagens import formatar_primeiro_contato

router = APIRouter(prefix="/campanhas", tags=["campanhas"])


class CriarCampanha(BaseModel):
    nome: str
    tipo: str  # 'primeiro_contato', 'followup', 'promocional'
    mensagem_template: str
    filtro_especialidades: Optional[List[str]] = None
    filtro_regioes: Optional[List[str]] = None
    filtro_tags: Optional[List[str]] = None
    agendar_para: Optional[datetime] = None
    max_por_dia: int = 50


@router.post("/")
async def criar_campanha(dados: CriarCampanha):
    """Cria nova campanha."""
    # Contar destinatários
    filtros = {}
    if dados.filtro_especialidades:
        # Por enquanto, assumir primeira especialidade
        filtros["especialidade"] = dados.filtro_especialidades[0]
    if dados.filtro_regioes:
        filtros["regiao"] = dados.filtro_regioes[0]
    if dados.filtro_tags:
        filtros["tag"] = dados.filtro_tags[0]

    total_destinatarios = await segmentacao_service.contar_segmento(filtros)

    campanha_resp = (
        supabase.table("campanhas")
        .insert({
            "nome": dados.nome,
            "tipo": dados.tipo,
            "mensagem_template": dados.mensagem_template,
            "status": "agendada" if dados.agendar_para else "rascunho",
            "total_destinatarios": total_destinatarios,
            "agendar_para": dados.agendar_para.isoformat() if dados.agendar_para else None,
            "config": {
                "filtro_especialidades": dados.filtro_especialidades,
                "filtro_regioes": dados.filtro_regioes,
                "filtro_tags": dados.filtro_tags,
                "max_por_dia": dados.max_por_dia
            }
        })
        .execute()
    )

    if not campanha_resp.data:
        raise HTTPException(status_code=500, detail="Erro ao criar campanha")

    return campanha_resp.data[0]


@router.post("/{campanha_id}/iniciar")
async def iniciar_campanha(campanha_id: str):
    """Inicia execução de campanha."""
    # Atualizar status
    supabase.table("campanhas").update({
        "status": "ativa",
        "iniciada_em": datetime.utcnow().isoformat()
    }).eq("id", campanha_id).execute()

    # Criar envios na fila
    await criar_envios_campanha(campanha_id)

    return {"status": "iniciada"}


async def criar_envios_campanha(campanha_id: str):
    """Cria envios para todos os destinatários da campanha."""
    campanha_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("id", campanha_id)
        .single()
        .execute()
    )

    if not campanha_resp.data:
        return

    campanha = campanha_resp.data
    config = campanha.get("config", {})

    # Montar filtros
    filtros = {}
    if config.get("filtro_especialidades"):
        filtros["especialidade"] = config["filtro_especialidades"][0]
    if config.get("filtro_regioes"):
        filtros["regiao"] = config["filtro_regioes"][0]
    if config.get("filtro_tags"):
        filtros["tag"] = config["filtro_tags"][0]

    # Buscar destinatários
    destinatarios = await segmentacao_service.buscar_segmento(filtros, limite=10000)

    # Criar envio para cada destinatário
    for dest in destinatarios:
        # Personalizar mensagem
        mensagem = campanha["mensagem_template"].format(
            nome=dest.get("primeiro_nome", ""),
            especialidade=dest.get("especialidade_nome", "médico")
        )

        # Enfileirar
        await fila_service.enfileirar(
            cliente_id=dest["id"],
            conteudo=mensagem,
            tipo=campanha["tipo"],
            prioridade=3,  # Prioridade baixa para campanhas
            metadata={"campanha_id": campanha_id}
        )

    # Atualizar contagem
    supabase.table("campanhas").update({
        "envios_criados": len(destinatarios)
    }).eq("id", campanha_id).execute()


@router.post("/segmento/preview")
async def preview_segmento(filtros: Dict[str, Any]):
    """
    Preview de um segmento antes de criar campanha.

    Retorna contagem e amostra de médicos.
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
async def relatorio_campanha(campanha_id: str):
    """Retorna relatório completo da campanha."""
    # Buscar campanha
    campanha_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("id", campanha_id)
        .single()
        .execute()
    )

    if not campanha_resp.data:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    campanha = campanha_resp.data

    # Buscar envios da campanha
    envios_resp = (
        supabase.table("fila_mensagens")
        .select("status")
        .eq("metadata->>campanha_id", campanha_id)
        .execute()
    )

    envios = envios_resp.data or []

    enviados = len([e for e in envios if e["status"] == "enviada"])
    erros = len([e for e in envios if e["status"] == "erro"])
    pendentes = len([e for e in envios if e["status"] == "pendente"])

    return {
        "campanha_id": campanha_id,
        "nome": campanha["nome"],
        "status": campanha["status"],
        "envios": {
            "total": len(envios),
            "enviados": enviados,
            "erros": erros,
            "pendentes": pendentes,
            "taxa_entrega": enviados / len(envios) if envios else 0
        },
        "periodo": {
            "inicio": campanha.get("iniciada_em"),
            "fim": campanha.get("finalizada_em")
        }
    }

