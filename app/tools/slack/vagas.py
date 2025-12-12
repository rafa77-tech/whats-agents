"""
Tools de vagas para o agente Slack.

Sprint 10 - S10.E2.3
"""
from datetime import datetime, timezone

from app.services.supabase import supabase
from .medicos import _buscar_medico_por_identificador


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """Busca vagas disponiveis.

QUANDO USAR:
- Gestor pergunta sobre vagas abertas
- Gestor quer ver oportunidades disponiveis
- Gestor menciona hospital e quer ver vagas

EXEMPLOS:
- "quais vagas tem abertas?"
- "tem vaga no Sao Luiz?"
- "o que tem pra essa semana?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "hospital": {
                "type": "string",
                "description": "Nome do hospital (opcional)"
            },
            "especialidade": {
                "type": "string",
                "description": "Especialidade (opcional)"
            },
            "status": {
                "type": "string",
                "enum": ["aberta", "reservada", "fechada", "todas"],
                "description": "Status das vagas"
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade maxima de vagas"
            }
        },
        "required": []
    }
}

TOOL_RESERVAR_VAGA = {
    "name": "reservar_vaga",
    "description": """Reserva uma vaga para um medico.

QUANDO USAR:
- Gestor pede para fechar/reservar vaga para alguem
- Gestor confirma reserva

EXEMPLOS:
- "reserva a vaga do dia 15 pro Dr Carlos"
- "fecha essa vaga pro 11999..."

ACAO CRITICA: Peca confirmacao antes de reservar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone_medico": {
                "type": "string",
                "description": "Telefone do medico"
            },
            "data_vaga": {
                "type": "string",
                "description": "Data da vaga (YYYY-MM-DD)"
            },
            "hospital": {
                "type": "string",
                "description": "Nome do hospital (opcional, para confirmar)"
            }
        },
        "required": ["telefone_medico", "data_vaga"]
    }
}


# =============================================================================
# HANDLERS
# =============================================================================

async def handle_buscar_vagas(params: dict) -> dict:
    """Busca vagas disponiveis."""
    hospital = params.get("hospital")
    especialidade = params.get("especialidade")
    status = params.get("status", "aberta")
    limite = min(params.get("limite", 10), 20)

    try:
        query = supabase.table("vagas").select(
            "id, data, valor, status, hospitais(nome, cidade), periodos(nome), especialidades(nome)"
        )

        if status != "todas":
            query = query.eq("status", status)

        if hospital:
            # Buscar hospital primeiro
            hosp = supabase.table("hospitais").select("id").ilike("nome", f"%{hospital}%").limit(1).execute()
            if hosp.data:
                query = query.eq("hospital_id", hosp.data[0]["id"])

        if especialidade:
            esp = supabase.table("especialidades").select("id").ilike("nome", f"%{especialidade}%").limit(1).execute()
            if esp.data:
                query = query.eq("especialidade_id", esp.data[0]["id"])

        result = query.order("data").limit(limite).execute()

        vagas = []
        for v in result.data or []:
            vagas.append({
                "id": v.get("id"),
                "hospital": v.get("hospitais", {}).get("nome"),
                "cidade": v.get("hospitais", {}).get("cidade"),
                "data": v.get("data"),
                "periodo": v.get("periodos", {}).get("nome"),
                "valor": v.get("valor"),
                "especialidade": v.get("especialidades", {}).get("nome"),
                "status": v.get("status")
            })

        return {"success": True, "vagas": vagas, "total": len(vagas)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_reservar_vaga(params: dict) -> dict:
    """Reserva uma vaga para um medico."""
    telefone = params.get("telefone_medico", "").strip()
    data_vaga = params.get("data_vaga", "").strip()

    if not telefone or not data_vaga:
        return {"success": False, "error": "Telefone e data sao obrigatorios"}

    medico = await _buscar_medico_por_identificador(telefone)
    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        # Buscar vaga pela data
        vaga = supabase.table("vagas").select(
            "*, hospitais(nome), periodos(nome)"
        ).eq("data", data_vaga).eq("status", "aberta").limit(1).execute()

        if not vaga.data:
            return {"success": False, "error": f"Vaga nao encontrada para data {data_vaga}"}

        vaga_data = vaga.data[0]

        # Reservar
        supabase.table("vagas").update({
            "status": "reservada",
            "reservado_para_id": medico["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", vaga_data["id"]).execute()

        return {
            "success": True,
            "vaga": {
                "hospital": vaga_data.get("hospitais", {}).get("nome"),
                "data": vaga_data.get("data"),
                "periodo": vaga_data.get("periodos", {}).get("nome"),
                "valor": vaga_data.get("valor")
            },
            "medico": {
                "nome": medico.get("primeiro_nome"),
                "telefone": medico.get("telefone")
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
