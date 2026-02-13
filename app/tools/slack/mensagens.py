"""
Tools de mensagens para o agente Slack.

Sprint 10 - S10.E2.3
"""

import re

from app.core.config import settings
from app.services.http_client import get_http_client
from app.services.supabase import supabase
from app.services.tipos_abordagem import (
    TipoAbordagem,
    inferir_tipo,
    descrever_tipo,
    extrair_hospital,
    extrair_data,
)
from .medicos import _buscar_medico_por_identificador


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_ENVIAR_MENSAGEM = {
    "name": "enviar_mensagem",
    "description": """Envia mensagem WhatsApp para um medico.

QUANDO USAR:
- Gestor pede para contatar/mandar msg/falar com um medico
- Gestor quer enviar uma mensagem especifica
- Gestor menciona telefone e quer enviar algo

EXEMPLOS:
- "manda msg pro 11999..."
- "contata o Dr Carlos"
- "fala com o 11988..."
- "envia uma mensagem oferecendo a vaga..."

ACAO CRITICA: Sempre mostre preview da mensagem e peca confirmacao antes de enviar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {
                "type": "string",
                "description": "Numero de telefone do medico com DDD (ex: 11999887766)",
            },
            "instrucao": {
                "type": "string",
                "description": "Instrucao sobre o que dizer na mensagem (ex: 'oferecer vaga do Sao Luiz')",
            },
            "tipo": {
                "type": "string",
                "enum": ["discovery", "oferta", "reativacao", "followup", "custom"],
                "description": "Tipo de abordagem. Use 'discovery' para primeiro contato, 'oferta' para vaga especifica.",
            },
        },
        "required": ["telefone"],
    },
}

TOOL_BUSCAR_HISTORICO = {
    "name": "buscar_historico",
    "description": """Busca historico de conversa com um medico.

QUANDO USAR:
- Gestor quer ver conversa anterior
- Gestor pergunta o que foi falado com alguem

EXEMPLOS:
- "o que falamos com o Dr Carlos?"
- "mostra o historico do 11999..."

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "telefone": {"type": "string", "description": "Telefone do medico"},
            "limite": {"type": "integer", "description": "Quantidade de mensagens (padrao: 10)"},
        },
        "required": ["telefone"],
    },
}


# =============================================================================
# HANDLERS
# =============================================================================


async def handle_enviar_mensagem(params: dict) -> dict:
    """Envia mensagem WhatsApp para medico."""
    telefone = params.get("telefone", "").strip()
    instrucao = params.get("instrucao", "")
    tipo_param = params.get("tipo", "")

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    # Limpar telefone
    telefone_limpo = re.sub(r"\D", "", telefone)
    if len(telefone_limpo) < 8:
        return {"success": False, "error": "Telefone invalido"}

    # Buscar medico se existir
    medico = await _buscar_medico_por_identificador(telefone_limpo)

    # Verificar opt-out
    if medico and (medico.get("opt_out") or medico.get("opted_out")):
        return {
            "success": False,
            "error": f"Medico {medico.get('primeiro_nome')} esta bloqueado (opt-out)",
        }

    # Verificar se eh medico novo (nunca contatado)
    eh_novo = medico is None

    # Verificar se menciona vaga
    tem_vaga = False
    hospital = None
    data_vaga = None
    if instrucao:
        hospital = extrair_hospital(instrucao)
        data_vaga = extrair_data(instrucao)
        tem_vaga = hospital is not None or data_vaga is not None

    # Inferir tipo de abordagem se nao foi especificado
    if tipo_param and tipo_param in [t.value for t in TipoAbordagem]:
        tipo = tipo_param
    else:
        tipo_inferido = inferir_tipo(instrucao, tem_vaga=tem_vaga, eh_novo=eh_novo)
        tipo = tipo_inferido.value

    try:
        client = await get_http_client()
        payload = {"telefone": telefone_limpo, "tipo": tipo, "instrucao": instrucao}

        # Adicionar dados de vaga se detectados
        if hospital:
            payload["hospital"] = hospital
        if data_vaga:
            payload["data_vaga"] = data_vaga

        response = await client.post(
            f"{settings.JULIA_API_URL}/jobs/primeira-mensagem", json=payload, timeout=30.0
        )

        if response.status_code == 200:
            data = response.json()
            nome = medico.get("primeiro_nome") if medico else "novo contato"
            return {
                "success": True,
                "telefone": telefone_limpo,
                "nome": nome,
                "tipo_abordagem": descrever_tipo(TipoAbordagem(tipo)),
                "mensagem": data.get("mensagem_enviada", "Mensagem enviada"),
            }
        else:
            return {"success": False, "error": f"Erro na API: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_buscar_historico(params: dict) -> dict:
    """Busca historico de conversa."""
    telefone = params.get("telefone", "").strip()
    limite = min(params.get("limite", 10), 30)

    if not telefone:
        return {"success": False, "error": "Telefone nao informado"}

    medico = await _buscar_medico_por_identificador(telefone)
    if not medico:
        return {"success": False, "error": f"Medico nao encontrado: {telefone}"}

    try:
        interacoes = (
            supabase.table("interacoes")
            .select("tipo, autor_tipo, conteudo, created_at")
            .eq("cliente_id", medico["id"])
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

        mensagens = []
        for i in interacoes.data or []:
            mensagens.append(
                {
                    "autor": "julia" if i.get("autor_tipo") == "julia" else "medico",
                    "texto": i.get("conteudo"),
                    "data": i.get("created_at"),
                }
            )

        return {
            "success": True,
            "medico": medico.get("primeiro_nome"),
            "mensagens": list(reversed(mensagens)),
            "total": len(mensagens),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
