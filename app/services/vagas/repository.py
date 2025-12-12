"""
Queries de vagas no banco de dados.

Sprint 10 - S10.E3.2
"""
import logging
from datetime import date, datetime, timezone
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_por_id(vaga_id: str) -> Optional[dict]:
    """Busca vaga pelo ID com dados relacionados."""
    response = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("id", vaga_id)
        .execute()
    )
    return response.data[0] if response.data else None


async def listar_disponiveis(
    especialidade_id: str,
    limite: int = 10
) -> list[dict]:
    """Lista vagas disponiveis para uma especialidade."""
    hoje = date.today().isoformat()

    response = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data", hoje)
        .order("data")
        .limit(limite)
        .execute()
    )

    logger.info(f"Encontradas {len(response.data or [])} vagas para especialidade {especialidade_id}")
    return response.data or []


async def verificar_conflito(
    cliente_id: str,
    data: str,
    periodo_id: str
) -> dict:
    """
    Verifica se medico ja tem vaga reservada no mesmo dia/periodo.

    Returns:
        dict com conflito, vaga_conflitante, mensagem
    """
    response = (
        supabase.table("vagas")
        .select("id, hospital_id, data, periodo_id, status, hospitais(nome)")
        .eq("cliente_id", cliente_id)
        .eq("data", data)
        .eq("periodo_id", periodo_id)
        .in_("status", ["reservada", "confirmada"])
        .limit(1)
        .execute()
    )

    if response.data:
        vaga = response.data[0]
        hospital_nome = vaga.get("hospitais", {}).get("nome", "Hospital")
        logger.info(f"Conflito: medico {cliente_id} ja tem plantao em {data} no {hospital_nome}")
        return {
            "conflito": True,
            "vaga_conflitante": {
                "id": vaga["id"],
                "hospital": hospital_nome,
                "data": vaga["data"],
                "status": vaga["status"]
            },
            "mensagem": f"Voce ja tem plantao em {data} no {hospital_nome}"
        }

    return {"conflito": False, "vaga_conflitante": None, "mensagem": None}


async def reservar(vaga_id: str, cliente_id: str) -> Optional[dict]:
    """
    Reserva vaga para um medico (operacao atomica).

    Returns:
        Vaga atualizada ou None se falhou
    """
    response = (
        supabase.table("vagas")
        .update({
            "status": "reservada",
            "cliente_id": cliente_id,
            "fechada_em": datetime.now(timezone.utc).isoformat(),
            "fechada_por": "julia",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .eq("status", "aberta")  # Optimistic locking
        .execute()
    )

    if response.data:
        logger.info(f"Vaga {vaga_id} reservada para medico {cliente_id}")
        return response.data[0]
    return None


async def cancelar_reserva(vaga_id: str) -> Optional[dict]:
    """Cancela reserva de uma vaga."""
    response = (
        supabase.table("vagas")
        .update({
            "status": "aberta",
            "cliente_id": None,
            "fechada_em": None,
            "fechada_por": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .execute()
    )
    return response.data[0] if response.data else None
