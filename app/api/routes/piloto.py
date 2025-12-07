"""
Endpoints para monitoramento do piloto.
"""
from fastapi import APIRouter
from typing import Dict, Any

from app.services.supabase import supabase

router = APIRouter(prefix="/piloto", tags=["piloto"])


@router.get("/status")
async def status_piloto() -> Dict[str, Any]:
    """Retorna status atual do piloto."""
    # Buscar campanha ativa
    campanha_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("tipo", "primeiro_contato")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not campanha_resp.data:
        return {"status": "sem_campanha"}

    campanha = campanha_resp.data[0]

    # Contar envios
    envios_resp = (
        supabase.table("envios_campanha")
        .select("status")
        .eq("campanha_id", campanha["id"])
        .execute()
    )

    envios = envios_resp.data or []

    enviados = len([e for e in envios if e["status"] == "enviado"])
    pendentes = len([e for e in envios if e["status"] == "pendente"])
    erros = len([e for e in envios if e["status"] == "erro"])

    # Contar respostas
    medicos_piloto_resp = (
        supabase.table("clientes")
        .select("id")
        .contains("tags", ["piloto_v1"])
        .execute()
    )

    medicos_piloto = medicos_piloto_resp.data or []
    medico_ids = [m["id"] for m in medicos_piloto]

    conversas_resp = (
        supabase.table("conversations")
        .select("id, cliente_id")
        .in_("cliente_id", medico_ids)
        .execute()
    )

    conversas = conversas_resp.data or []
    responderam = len(set(c["cliente_id"] for c in conversas))

    return {
        "campanha_id": campanha["id"],
        "status": campanha["status"],
        "envios": {
            "total": len(envios),
            "enviados": enviados,
            "pendentes": pendentes,
            "erros": erros
        },
        "metricas": {
            "responderam": responderam,
            "taxa_resposta": responderam / enviados if enviados > 0 else 0
        }
    }

