"""
Tools de mensagens interativas do WhatsApp para a Julia.

Sprint 67 (R2, R10, Epic 67.2 T1, Chunk 7b).

3 tools para o agente LLM:
- enviar_opcoes: Botões de resposta rápida (max 3)
- enviar_lista: Lista selecionável (max 10 itens)
- enviar_cta: Botão CTA com URL

Comportamento:
- Handler ENVIA a mensagem diretamente (side effect)
- Retorna {success: True, mensagem_enviada: True} ou
  {success: False, instrucao: "..."} para fallback em texto
"""

import logging
from typing import Optional

from app.services.outbound.interactive import send_outbound_interactive

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Tool Definitions (schema para o LLM)
# ──────────────────────────────────────────────

TOOL_ENVIAR_OPCOES = {
    "name": "enviar_opcoes",
    "description": (
        "Envia mensagem com botões de resposta rápida ao médico. "
        "Máximo 3 opções. Ideal para confirmações (Sim/Não) ou escolhas simples. "
        "Se o WhatsApp não suportar botões neste chat, o sistema automaticamente "
        "envia um texto equivalente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima dos botões (corpo da msg)",
            },
            "opcoes": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 3,
                "description": "Lista de opções (max 3, max 20 chars cada)",
            },
        },
        "required": ["texto", "opcoes"],
    },
}

TOOL_ENVIAR_LISTA = {
    "name": "enviar_lista",
    "description": (
        "Envia mensagem com lista selecionável ao médico. "
        "Ideal para mostrar vagas, horários ou opções detalhadas (max 10 itens). "
        "Cada item pode ter título e descrição. "
        "Se o WhatsApp não suportar lista neste chat, envia texto equivalente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima da lista",
            },
            "botao_texto": {
                "type": "string",
                "description": "Texto do botão que abre a lista (max 20 chars)",
            },
            "itens": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {
                            "type": "string",
                            "description": "Título do item (max 24 chars)",
                        },
                        "descricao": {
                            "type": "string",
                            "description": "Descrição do item (max 72 chars)",
                        },
                    },
                    "required": ["titulo"],
                },
                "minItems": 1,
                "maxItems": 10,
                "description": "Itens da lista",
            },
        },
        "required": ["texto", "botao_texto", "itens"],
    },
}

TOOL_ENVIAR_CTA = {
    "name": "enviar_cta",
    "description": (
        "Envia mensagem com botão de link (CTA URL) ao médico. "
        "Ideal para enviar links de confirmação, formulários ou documentos. "
        "URL deve ser HTTPS. Se não suportado, envia texto com o link."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "texto": {
                "type": "string",
                "description": "Texto da mensagem acima do botão",
            },
            "botao_texto": {
                "type": "string",
                "description": "Texto do botão CTA (max 20 chars)",
            },
            "url": {
                "type": "string",
                "description": "URL do link (deve ser HTTPS)",
            },
        },
        "required": ["texto", "botao_texto", "url"],
    },
}

# Lista de todas as tools interativas
TOOLS_INTERACTIVE = [TOOL_ENVIAR_OPCOES, TOOL_ENVIAR_LISTA, TOOL_ENVIAR_CTA]


# ──────────────────────────────────────────────
# Payload Builders
# ──────────────────────────────────────────────


def _gerar_payload_buttons(texto: str, opcoes: list[str]) -> dict:
    """Gera payload de botões para a API Meta."""
    buttons = []
    for i, opcao in enumerate(opcoes[:3]):
        buttons.append(
            {
                "type": "reply",
                "reply": {
                    "id": f"btn_{i}",
                    "title": opcao[:20],
                },
            }
        )

    return {
        "type": "button",
        "body": {"text": texto},
        "action": {"buttons": buttons},
    }


def _gerar_payload_list(
    texto: str,
    botao_texto: str,
    itens: list[dict],
) -> dict:
    """Gera payload de lista para a API Meta."""
    rows = []
    for i, item in enumerate(itens[:10]):
        row = {
            "id": f"row_{i}",
            "title": item["titulo"][:24],
        }
        if item.get("descricao"):
            row["description"] = item["descricao"][:72]
        rows.append(row)

    return {
        "type": "list",
        "body": {"text": texto},
        "action": {
            "button": botao_texto[:20],
            "sections": [{"title": "Opções", "rows": rows}],
        },
    }


def _gerar_payload_cta(texto: str, botao_texto: str, url: str) -> dict:
    """Gera payload de CTA URL para a API Meta."""
    return {
        "type": "cta_url",
        "body": {"text": texto},
        "action": {
            "name": "cta_url",
            "parameters": {
                "display_text": botao_texto[:20],
                "url": url,
            },
        },
    }


# ──────────────────────────────────────────────
# Fallback Text Generators
# ──────────────────────────────────────────────


def _gerar_fallback_texto_opcoes(texto: str, opcoes: list[str]) -> str:
    """Gera texto de fallback para botões."""
    opcoes_texto = "\n".join(f"  {i + 1}. {o}" for i, o in enumerate(opcoes))
    return f"{texto}\n\nResponda com o número:\n{opcoes_texto}"


def _gerar_fallback_texto_lista(
    texto: str,
    itens: list[dict],
) -> str:
    """Gera texto de fallback para lista."""
    itens_texto = []
    for i, item in enumerate(itens):
        line = f"  {i + 1}. {item['titulo']}"
        if item.get("descricao"):
            line += f" — {item['descricao']}"
        itens_texto.append(line)
    return f"{texto}\n\n" + "\n".join(itens_texto)


def _gerar_fallback_texto_cta(texto: str, url: str) -> str:
    """Gera texto de fallback para CTA URL."""
    return f"{texto}\n\n{url}"


# ──────────────────────────────────────────────
# Tool Handlers
# ──────────────────────────────────────────────


async def handle_enviar_opcoes(
    input_data: dict,
    medico: Optional[dict] = None,
    conversa: Optional[dict] = None,
) -> dict:
    """
    Handler para tool enviar_opcoes.

    Valida, verifica janela, envia interativo ou fallback texto.
    """
    texto = input_data.get("texto", "")
    opcoes = input_data.get("opcoes", [])

    if not texto or not opcoes:
        return {"success": False, "error": "Texto e opções são obrigatórios"}

    # Gerar payloads
    interactive_payload = _gerar_payload_buttons(texto, opcoes)
    fallback_text = _gerar_fallback_texto_opcoes(texto, opcoes)

    return await _enviar_interactive_ou_fallback(
        medico=medico,
        conversa=conversa,
        interactive_payload=interactive_payload,
        fallback_text=fallback_text,
        tipo="buttons",
    )


async def handle_enviar_lista(
    input_data: dict,
    medico: Optional[dict] = None,
    conversa: Optional[dict] = None,
) -> dict:
    """Handler para tool enviar_lista."""
    texto = input_data.get("texto", "")
    botao_texto = input_data.get("botao_texto", "Ver opções")
    itens = input_data.get("itens", [])

    if not texto or not itens:
        return {"success": False, "error": "Texto e itens são obrigatórios"}

    interactive_payload = _gerar_payload_list(texto, botao_texto, itens)
    fallback_text = _gerar_fallback_texto_lista(texto, itens)

    return await _enviar_interactive_ou_fallback(
        medico=medico,
        conversa=conversa,
        interactive_payload=interactive_payload,
        fallback_text=fallback_text,
        tipo="list",
    )


async def handle_enviar_cta(
    input_data: dict,
    medico: Optional[dict] = None,
    conversa: Optional[dict] = None,
) -> dict:
    """Handler para tool enviar_cta."""
    texto = input_data.get("texto", "")
    botao_texto = input_data.get("botao_texto", "Acessar")
    url = input_data.get("url", "")

    if not texto or not url:
        return {"success": False, "error": "Texto e URL são obrigatórios"}

    interactive_payload = _gerar_payload_cta(texto, botao_texto, url)
    fallback_text = _gerar_fallback_texto_cta(texto, url)

    return await _enviar_interactive_ou_fallback(
        medico=medico,
        conversa=conversa,
        interactive_payload=interactive_payload,
        fallback_text=fallback_text,
        tipo="cta_url",
    )


async def _enviar_interactive_ou_fallback(
    medico: Optional[dict],
    conversa: Optional[dict],
    interactive_payload: dict,
    fallback_text: str,
    tipo: str,
) -> dict:
    """
    Tenta enviar mensagem interativa; se não possível, instrui fallback.

    Verifica:
    1. Se o chat usa chip Meta
    2. Se está dentro da janela 24h (R10)
    Se ambos OK → envia interactive via send_outbound_interactive
    Se não → retorna instrucao para LLM gerar texto

    Returns:
        Dict com resultado.
    """
    telefone = None
    if medico:
        telefone = medico.get("telefone")

    if not telefone:
        return {
            "success": False,
            "instrucao": (
                "Não foi possível enviar mensagem interativa (telefone não encontrado). "
                f"Envie o seguinte texto como mensagem normal:\n\n{fallback_text}"
            ),
        }

    # Verificar se chip é Meta e está na janela
    try:
        conversa_id = conversa.get("id") if conversa else None

        result = await send_outbound_interactive(
            telefone=telefone,
            interactive_payload=interactive_payload,
            fallback_text=fallback_text,
            conversa_id=conversa_id,
        )

        if result.success:
            return {
                "success": True,
                "mensagem_enviada": True,
                "tipo": tipo,
            }

    except Exception as e:
        logger.warning("Erro ao enviar interactive, usando fallback: %s", e)

    # Fallback: instruir LLM a enviar como texto
    return {
        "success": False,
        "instrucao": (
            "Este chat não suporta mensagens interativas no momento. "
            f"Envie o seguinte texto como mensagem normal:\n\n{fallback_text}"
        ),
    }
