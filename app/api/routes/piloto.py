"""
Endpoints para monitoramento do piloto.

Sprint 35 - Epic 06: Atualizado para usar nomes de colunas corretos
e fila_mensagens em vez de envios_campanha (tabela removida).
"""
from fastapi import APIRouter
from typing import Dict, Any

from app.services.supabase import supabase

router = APIRouter(prefix="/piloto", tags=["piloto"])


@router.get("/status")
async def status_piloto() -> Dict[str, Any]:
    """
    Retorna status atual do piloto.

    Usa tipo_campanha (não tipo) e fila_mensagens (não envios_campanha).
    """
    # Buscar campanha ativa
    campanha_resp = (
        supabase.table("campanhas")
        .select("*")
        .eq("tipo_campanha", "discovery")  # Era "tipo": "primeiro_contato"
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not campanha_resp.data:
        return {"status": "sem_campanha"}

    campanha = campanha_resp.data[0]
    campanha_id = campanha["id"]

    # Contar envios na fila_mensagens (não mais envios_campanha)
    envios_resp = (
        supabase.table("fila_mensagens")
        .select("status")
        .eq("metadata->>campanha_id", str(campanha_id))
        .execute()
    )

    envios = envios_resp.data or []

    enviados = len([e for e in envios if e["status"] == "enviada"])
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
        "campanha_id": campanha_id,
        "nome": campanha.get("nome_template"),
        "tipo_campanha": campanha.get("tipo_campanha"),
        "status": campanha.get("status"),
        "contadores": {
            "total_destinatarios": campanha.get("total_destinatarios", 0),
            "enviados": campanha.get("enviados", 0),
            "entregues": campanha.get("entregues", 0),
            "respondidos": campanha.get("respondidos", 0),
        },
        "fila": {
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
