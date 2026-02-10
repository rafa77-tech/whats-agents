"""
Tools de medicos para o agente Slack.

Sprint 10 - S10.E2.3
"""

import re
from datetime import datetime, timezone, timedelta

from app.services.supabase import supabase


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_BUSCAR_MEDICO = {
    "name": "buscar_medico",
    "description": """Busca informacoes de um medico especifico.

QUANDO USAR:
- Gestor pergunta sobre um medico
- Gestor quer ver dados de alguem
- Gestor menciona nome/telefone e quer info

EXEMPLOS:
- "quem eh o Dr Carlos?"
- "me fala do 11999..."
- "busca o CRM 123456"
- "tem algum Carlos aqui?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "identificador": {"type": "string", "description": "Telefone, nome ou CRM do medico"}
        },
        "required": ["identificador"],
    },
}

TOOL_LISTAR_MEDICOS = {
    "name": "listar_medicos",
    "description": """Lista medicos com filtros.

QUANDO USAR:
- Gestor quer ver lista de medicos
- Gestor pergunta quem respondeu/nao respondeu
- Gestor quer ver interessados/positivos

EXEMPLOS:
- "quem respondeu hoje?"
- "lista os interessados"
- "quem ta sem resposta?"
- "mostra os medicos novos"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "filtro": {
                "type": "string",
                "enum": ["responderam_hoje", "positivos", "sem_resposta", "novos", "todos"],
                "description": "Tipo de filtro a aplicar",
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade maxima de medicos a retornar (padrao: 10)",
            },
        },
        "required": ["filtro"],
    },
}

TOOL_BLOQUEAR_MEDICO = {
    "name": "bloquear_medico",
    "description": """Bloqueia um medico (opt-out).

QUANDO USAR:
- Gestor pede para bloquear alguem
- Gestor diz que medico pediu para parar
- Gestor quer remover medico da lista

EXEMPLOS:
- "bloqueia o 11999..."
- "tira ele da lista"
- "nao manda mais pro Dr Carlos"

ACAO CRITICA: Peca confirmacao antes de bloquear.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {"type": "string", "description": "Telefone do medico"},
            "motivo": {"type": "string", "description": "Motivo do bloqueio (opcional)"},
        },
        "required": ["telefone"],
    },
}

TOOL_DESBLOQUEAR_MEDICO = {
    "name": "desbloquear_medico",
    "description": """Remove bloqueio de um medico.

QUANDO USAR:
- Gestor pede para desbloquear alguem
- Gestor quer reativar contato

EXEMPLOS:
- "desbloqueia o 11999..."
- "pode voltar a contatar o Dr Carlos"

ACAO CRITICA: Peca confirmacao antes de desbloquear.""",
    "input_schema": {
        "type": "object",
        "properties": {"telefone": {"type": "string", "description": "Telefone do medico"}},
        "required": ["telefone"],
    },
}


# =============================================================================
# HELPERS
# =============================================================================


async def _buscar_medico_por_identificador(identificador: str) -> dict | None:
    """Busca medico por telefone, nome ou CRM."""
    identificador = identificador.strip()
    telefone_limpo = re.sub(r"\D", "", identificador)

    # Por telefone
    if telefone_limpo and len(telefone_limpo) >= 8:
        result = (
            supabase.table("clientes")
            .select("*")
            .or_(f"telefone.like.%{telefone_limpo[-8:]}")
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    # Por CRM
    crm_limpo = re.sub(r"[^0-9]", "", identificador)
    if crm_limpo:
        result = (
            supabase.table("clientes")
            .select("*")
            .or_(f"crm.eq.{crm_limpo},crm.ilike.%{crm_limpo}%")
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    # Por nome
    if not telefone_limpo:
        result = (
            supabase.table("clientes")
            .select("*")
            .ilike("primeiro_nome", f"%{identificador}%")
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]

    return None


# =============================================================================
# HANDLERS
# =============================================================================


async def handle_buscar_medico(params: dict) -> dict:
    """Busca informacoes de um medico."""
    identificador = params.get("identificador", "").strip()

    if not identificador:
        return {"success": False, "error": "Identificador nao informado"}

    medico = await _buscar_medico_por_identificador(identificador)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {identificador}"}

    # Buscar ultima interacao
    ultima = (
        supabase.table("interacoes")
        .select("created_at, conteudo")
        .eq("cliente_id", medico["id"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    ultima_interacao = None
    if ultima.data:
        ultima_interacao = ultima.data[0].get("created_at")

    return {
        "success": True,
        "medico": {
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone"),
            "crm": medico.get("crm"),
            "especialidade": medico.get("especialidade"),
            "cidade": medico.get("cidade"),
            "bloqueado": medico.get("opt_out") or medico.get("opted_out"),
            "ultima_interacao": ultima_interacao,
        },
    }


async def handle_listar_medicos(params: dict) -> dict:
    """Lista medicos com filtros."""
    filtro = params.get("filtro", "todos")
    limite = min(params.get("limite", 10), 20)

    agora = datetime.now(timezone.utc)
    hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        if filtro == "responderam_hoje":
            # Medicos que tiveram interacao de entrada hoje
            interacoes = (
                supabase.table("interacoes")
                .select("cliente_id")
                .eq("tipo", "entrada")
                .gte("created_at", hoje)
                .execute()
            )

            cliente_ids = (
                list(set([i["cliente_id"] for i in interacoes.data])) if interacoes.data else []
            )

            if not cliente_ids:
                return {"success": True, "medicos": [], "total": 0}

            medicos = (
                supabase.table("clientes")
                .select("primeiro_nome, telefone, especialidade")
                .in_("id", cliente_ids[:limite])
                .execute()
            )

        elif filtro == "positivos":
            # Conversas com sentimento positivo
            conversas = (
                supabase.table("conversations")
                .select("cliente_id")
                .eq("sentimento", "positivo")
                .limit(limite)
                .execute()
            )

            cliente_ids = [c["cliente_id"] for c in conversas.data] if conversas.data else []

            if not cliente_ids:
                return {"success": True, "medicos": [], "total": 0}

            medicos = (
                supabase.table("clientes")
                .select("primeiro_nome, telefone, especialidade")
                .in_("id", cliente_ids)
                .execute()
            )

        elif filtro == "sem_resposta":
            # Medicos sem interacao de entrada
            medicos = (
                supabase.table("clientes")
                .select("primeiro_nome, telefone, especialidade")
                .eq("opted_out", False)
                .order("created_at", desc=True)
                .limit(limite)
                .execute()
            )

        elif filtro == "novos":
            # Medicos criados nos ultimos 7 dias
            semana_atras = (agora - timedelta(days=7)).isoformat()
            medicos = (
                supabase.table("clientes")
                .select("primeiro_nome, telefone, especialidade")
                .gte("created_at", semana_atras)
                .limit(limite)
                .execute()
            )

        else:
            medicos = (
                supabase.table("clientes")
                .select("primeiro_nome, telefone, especialidade")
                .eq("opted_out", False)
                .limit(limite)
                .execute()
            )

        lista = []
        for m in medicos.data or []:
            lista.append(
                {
                    "nome": m.get("primeiro_nome"),
                    "telefone": m.get("telefone"),
                    "especialidade": m.get("especialidade"),
                }
            )

        return {"success": True, "medicos": lista, "total": len(lista)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_bloquear_medico(params: dict) -> dict:
    """Bloqueia um medico."""
    telefone = params.get("telefone", "").strip()
    motivo = params.get("motivo", "Bloqueado via Slack")

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        supabase.table("clientes").update(
            {
                "opt_out": True,
                "opted_out": True,
                "opted_out_at": datetime.now(timezone.utc).isoformat(),
                "opted_out_reason": motivo,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", medico["id"]).execute()

        return {
            "success": True,
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_desbloquear_medico(params: dict) -> dict:
    """Remove bloqueio de um medico."""
    telefone = params.get("telefone", "").strip()

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)

    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        supabase.table("clientes").update(
            {
                "opt_out": False,
                "opted_out": False,
                "opted_out_at": None,
                "opted_out_reason": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", medico["id"]).execute()

        return {
            "success": True,
            "nome": medico.get("primeiro_nome"),
            "telefone": medico.get("telefone"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
