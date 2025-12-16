"""
Tool de processamento de briefings para o agente Slack.

Sprint 11 - Briefing Conversacional

Permite que o gestor peça para Julia ler e analisar
um briefing do Google Docs.
"""
import logging
from typing import Any

from app.services.google_docs import (
    listar_documentos,
    buscar_documento_por_nome,
    ler_documento,
    DocInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DEFINICAO DA TOOL
# =============================================================================

TOOL_PROCESSAR_BRIEFING = {
    "name": "processar_briefing",
    "description": """
Processa um briefing do Google Docs.

Use quando o gestor pedir para:
- Ler um briefing: "le o briefing X", "olha o doc X"
- Analisar um briefing: "analisa o X", "processa o briefing X"
- Ver briefings disponiveis: "quais briefings tem?", "lista os docs"

Se o nome nao for especificado ou for muito vago, liste os documentos disponiveis.
""".strip(),
    "input_schema": {
        "type": "object",
        "properties": {
            "nome_documento": {
                "type": "string",
                "description": "Nome (ou parte do nome) do documento a processar. Se vazio, lista documentos disponiveis."
            },
            "acao": {
                "type": "string",
                "enum": ["listar", "ler", "analisar"],
                "description": "Acao a executar: 'listar' mostra docs disponiveis, 'ler' mostra conteudo, 'analisar' faz analise completa com plano."
            }
        },
        "required": []
    }
}


# =============================================================================
# HANDLER
# =============================================================================

async def handle_processar_briefing(params: dict, channel_id: str = "", user_id: str = "") -> dict[str, Any]:
    """
    Handler para processar briefing.

    1. Se acao=listar ou sem nome: lista documentos
    2. Se nome fornecido: busca documento
       - Se unico match: le/analisa
       - Se multiplos: pede confirmacao
       - Se nenhum: mostra disponiveis

    Args:
        params: Parametros da tool
        channel_id: ID do canal Slack (passado pelo executor)
        user_id: ID do usuario Slack (passado pelo executor)
    """
    nome = params.get("nome_documento", "").strip()
    acao = params.get("acao", "analisar")

    # Se acao explicitamente "listar" ou sem nome
    if acao == "listar" or not nome:
        return await _listar_briefings()

    # Buscar documento por nome
    matches = await buscar_documento_por_nome(nome)

    if not matches:
        # Nenhum match - mostrar disponiveis
        docs = await listar_documentos()
        nomes = [d.nome for d in docs]
        return {
            "success": False,
            "error": f"Nao encontrei documento com '{nome}'",
            "documentos_disponiveis": nomes,
            "mensagem": f"Nao achei nenhum briefing com '{nome}'. Temos esses aqui: {', '.join(nomes) if nomes else 'nenhum'}"
        }

    if len(matches) > 1:
        # Multiplos matches - pedir confirmacao
        nomes = [d.nome for d in matches]
        return {
            "success": False,
            "multiplos_matches": True,
            "matches": nomes,
            "mensagem": f"Achei {len(matches)} documentos que batem: {', '.join(nomes)}. Qual deles?"
        }

    # Match unico - processar
    doc_info = matches[0]

    if acao == "ler":
        return await _ler_briefing(doc_info)
    else:  # analisar
        return await _iniciar_analise_briefing(doc_info, channel_id, user_id)


async def _listar_briefings() -> dict[str, Any]:
    """Lista todos os briefings disponiveis."""
    docs = await listar_documentos()

    if not docs:
        return {
            "success": True,
            "documentos": [],
            "mensagem": "Nao tem nenhum briefing na pasta ainda."
        }

    docs_info = []
    for doc in docs:
        docs_info.append({
            "nome": doc.nome,
            "id": doc.id,
            "ultima_modificacao": doc.ultima_modificacao.strftime("%d/%m %H:%M"),
            "url": doc.url
        })

    return {
        "success": True,
        "documentos": docs_info,
        "total": len(docs_info),
        "mensagem": f"Temos {len(docs_info)} briefings na pasta."
    }


async def _ler_briefing(doc_info: DocInfo) -> dict[str, Any]:
    """Le conteudo de um briefing sem analisar."""
    doc = await ler_documento(doc_info.id)

    if not doc:
        return {
            "success": False,
            "error": f"Erro ao ler documento {doc_info.nome}"
        }

    return {
        "success": True,
        "acao": "ler",
        "documento": {
            "nome": doc.info.nome,
            "id": doc.info.id,
            "url": doc.info.url,
            "ultima_modificacao": doc.info.ultima_modificacao.strftime("%d/%m %H:%M"),
            "ja_processado": doc.ja_processado,
        },
        "conteudo": doc.conteudo,
        "caracteres": len(doc.conteudo),
        "mensagem": f"Li o briefing '{doc.info.nome}'. {'Ja tem um plano meu la.' if doc.ja_processado else 'Ainda nao processei esse.'}"
    }


async def _iniciar_analise_briefing(doc_info: DocInfo, channel_id: str = "", user_id: str = "") -> dict[str, Any]:
    """
    Inicia analise de um briefing.

    Faz a analise completa com Sonnet, escreve no doc e cria registro pendente.
    """
    doc = await ler_documento(doc_info.id)

    if not doc:
        return {
            "success": False,
            "error": f"Erro ao ler documento {doc_info.nome}"
        }

    # Verificar se conteudo eh muito grande
    if len(doc.conteudo) > 15000:
        return {
            "success": False,
            "error": "Documento muito grande",
            "caracteres": len(doc.conteudo),
            "mensagem": f"Esse briefing tem {len(doc.conteudo)} caracteres, muito grande pra eu processar de uma vez. Pede pro gestor dividir em partes menores."
        }

    # Verificar se tem conteudo util
    if len(doc.conteudo.strip()) < 50:
        return {
            "success": False,
            "error": "Documento vazio ou muito curto",
            "mensagem": f"O briefing '{doc.info.nome}' ta praticamente vazio. Pede pro gestor escrever o que ele precisa."
        }

    # Verificar se ja tem plano pendente
    if doc.ja_processado:
        return {
            "success": True,
            "acao": "ja_processado",
            "documento": {
                "nome": doc.info.nome,
                "id": doc.info.id,
                "url": doc.info.url,
            },
            "mensagem": f"Esse briefing '{doc.info.nome}' ja tem um plano meu. Quer que eu faca uma nova analise?"
        }

    # Processar briefing completo (analise + escrita + pendente)
    try:
        from app.services.briefing_aprovacao import processar_briefing_completo

        briefing_id, mensagem_slack = await processar_briefing_completo(
            doc_id=doc.info.id,
            doc_nome=doc.info.nome,
            conteudo=doc.conteudo,
            doc_url=doc.info.url,
            channel_id=channel_id,
            user_id=user_id
        )

        return {
            "success": True,
            "acao": "analisado",
            "briefing_id": briefing_id,
            "documento": {
                "nome": doc.info.nome,
                "id": doc.info.id,
                "url": doc.info.url,
                "ultima_modificacao": doc.info.ultima_modificacao.strftime("%d/%m %H:%M"),
            },
            "mensagem": mensagem_slack,
            "aguardando_aprovacao": True
        }

    except Exception as e:
        logger.error(f"Erro ao processar briefing: {e}")
        return {
            "success": False,
            "error": str(e),
            "mensagem": f"Ops, tive um problema ao analisar o briefing: {e}"
        }
