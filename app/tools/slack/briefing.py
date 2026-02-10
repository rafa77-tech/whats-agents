"""
Tool de processamento de briefings para o agente Slack.

Sprint 11 - Briefing Conversacional
Sprint 23 E06 - Sync imediato via Slack

Permite que o gestor peça para Julia ler e analisar
um briefing do Google Docs, ou sincronizar imediatamente.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.google_docs import (
    listar_documentos,
    buscar_documento_por_nome,
    ler_documento,
    DocInfo,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Rate limit para sync manual (5 minutos)
SYNC_RATE_LIMIT_MINUTES = 5
_ultimo_sync_manual: Optional[datetime] = None


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
                "description": "Nome (ou parte do nome) do documento a processar. Se vazio, lista documentos disponiveis.",
            },
            "acao": {
                "type": "string",
                "enum": ["listar", "ler", "analisar"],
                "description": "Acao a executar: 'listar' mostra docs disponiveis, 'ler' mostra conteudo, 'analisar' faz analise completa com plano.",
            },
        },
        "required": [],
    },
}


# =============================================================================
# HANDLER
# =============================================================================


async def handle_processar_briefing(
    params: dict, channel_id: str = "", user_id: str = ""
) -> dict[str, Any]:
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
            "mensagem": f"Nao achei nenhum briefing com '{nome}'. Temos esses aqui: {', '.join(nomes) if nomes else 'nenhum'}",
        }

    if len(matches) > 1:
        # Multiplos matches - pedir confirmacao
        nomes = [d.nome for d in matches]
        return {
            "success": False,
            "multiplos_matches": True,
            "matches": nomes,
            "mensagem": f"Achei {len(matches)} documentos que batem: {', '.join(nomes)}. Qual deles?",
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
            "mensagem": "Nao tem nenhum briefing na pasta ainda.",
        }

    docs_info = []
    for doc in docs:
        docs_info.append(
            {
                "nome": doc.nome,
                "id": doc.id,
                "ultima_modificacao": doc.ultima_modificacao.strftime("%d/%m %H:%M"),
                "url": doc.url,
            }
        )

    return {
        "success": True,
        "documentos": docs_info,
        "total": len(docs_info),
        "mensagem": f"Temos {len(docs_info)} briefings na pasta.",
    }


async def _ler_briefing(doc_info: DocInfo) -> dict[str, Any]:
    """Le conteudo de um briefing sem analisar."""
    doc = await ler_documento(doc_info.id)

    if not doc:
        return {"success": False, "error": f"Erro ao ler documento {doc_info.nome}"}

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
        "mensagem": f"Li o briefing '{doc.info.nome}'. {'Ja tem um plano meu la.' if doc.ja_processado else 'Ainda nao processei esse.'}",
    }


async def _iniciar_analise_briefing(
    doc_info: DocInfo, channel_id: str = "", user_id: str = ""
) -> dict[str, Any]:
    """
    Inicia analise de um briefing.

    Faz a analise completa com Sonnet, escreve no doc e cria registro pendente.
    """
    doc = await ler_documento(doc_info.id)

    if not doc:
        return {"success": False, "error": f"Erro ao ler documento {doc_info.nome}"}

    # Verificar se conteudo eh muito grande
    if len(doc.conteudo) > 15000:
        return {
            "success": False,
            "error": "Documento muito grande",
            "caracteres": len(doc.conteudo),
            "mensagem": f"Esse briefing tem {len(doc.conteudo)} caracteres, muito grande pra eu processar de uma vez. Pede pro gestor dividir em partes menores.",
        }

    # Verificar se tem conteudo util
    if len(doc.conteudo.strip()) < 50:
        return {
            "success": False,
            "error": "Documento vazio ou muito curto",
            "mensagem": f"O briefing '{doc.info.nome}' ta praticamente vazio. Pede pro gestor escrever o que ele precisa.",
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
            "mensagem": f"Esse briefing '{doc.info.nome}' ja tem um plano meu. Quer que eu faca uma nova analise?",
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
            user_id=user_id,
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
            "aguardando_aprovacao": True,
        }

    except Exception as e:
        logger.error(f"Erro ao processar briefing: {e}")
        return {
            "success": False,
            "error": str(e),
            "mensagem": f"Ops, tive um problema ao analisar o briefing: {e}",
        }


# =============================================================================
# TOOL: SINCRONIZAR BRIEFING (Sprint 23 E06)
# =============================================================================

TOOL_SINCRONIZAR_BRIEFING = {
    "name": "sincronizar_briefing",
    "description": """
Forca sincronizacao imediata do briefing do Google Docs.

Use quando o gestor pedir para:
- Sincronizar: "sync briefing", "sincroniza o briefing"
- Atualizar: "atualiza briefing", "atualiza as diretrizes"
- Puxar: "puxa briefing", "recarrega briefing"
- Refresh: "refresh briefing", "recarrega diretrizes"

Rate limit: 1 sync a cada 5 minutos para evitar spam.
""".strip(),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


async def handle_sincronizar_briefing(params: dict, user_id: str = "") -> dict[str, Any]:
    """
    Handler para sincronizacao imediata de briefing.

    Sprint 23 E06 - Permite sync manual via Slack com feedback rico.

    Features:
    - Rate limit: 1 sync / 5 min
    - Feedback com hash antes/depois
    - Evento BRIEFING_SYNC_TRIGGERED

    Args:
        params: Parametros da tool (nenhum obrigatorio)
        user_id: ID do usuario Slack

    Returns:
        dict com resultado da sincronizacao
    """
    global _ultimo_sync_manual

    now = datetime.now(timezone.utc)

    # 1. Verificar rate limit
    if _ultimo_sync_manual:
        tempo_desde = (now - _ultimo_sync_manual).total_seconds() / 60
        if tempo_desde < SYNC_RATE_LIMIT_MINUTES:
            minutos_restantes = SYNC_RATE_LIMIT_MINUTES - tempo_desde
            return {
                "success": False,
                "rate_limited": True,
                "minutos_restantes": round(minutos_restantes, 1),
                "mensagem": (
                    f"Calma! Ultimo sync foi ha {round(tempo_desde, 1)} minutos. "
                    f"Aguarde mais {round(minutos_restantes, 1)} minutos."
                ),
            }

    # 2. Buscar hash atual antes do sync
    hash_antes = await _buscar_hash_atual()

    # 3. Executar sincronizacao
    try:
        from app.services.briefing import sincronizar_briefing

        resultado = await sincronizar_briefing()

        if not resultado.get("success"):
            return {
                "success": False,
                "error": resultado.get("error"),
                "mensagem": f"Erro ao sincronizar: {resultado.get('error')}",
            }

        # 4. Atualizar rate limit
        _ultimo_sync_manual = now

        # 5. Emitir evento de auditoria
        hash_depois = resultado.get("hash", "")
        atualizado = resultado.get("changed", False)

        await _emitir_evento_sync(
            user_id=user_id,
            hash_antes=hash_antes,
            hash_depois=hash_depois,
            atualizado=atualizado,
            secoes=resultado.get("secoes_atualizadas", []),
        )

        # 6. Formatar resposta
        if atualizado:
            secoes = resultado.get("secoes_atualizadas", [])
            return {
                "success": True,
                "atualizado": True,
                "titulo": resultado.get("titulo", "N/A"),
                "hash_antes": hash_antes[:8] if hash_antes else "N/A",
                "hash_depois": hash_depois[:8] if hash_depois else "N/A",
                "secoes_atualizadas": secoes,
                "avisos": resultado.get("avisos", []),
                "mensagem": (
                    f"Briefing sincronizado!\n\n"
                    f"*Documento:* {resultado.get('titulo', 'N/A')}\n"
                    f"*Secoes atualizadas:* {', '.join(secoes) if secoes else 'todas'}\n"
                    f"*Hash:* `{hash_antes[:8] if hash_antes else 'N/A'}` → `{hash_depois[:8] if hash_depois else 'N/A'}`\n"
                    f"*Timestamp:* {now.strftime('%H:%M:%S')}"
                ),
            }
        else:
            return {
                "success": True,
                "atualizado": False,
                "hash_atual": hash_depois[:8]
                if hash_depois
                else hash_antes[:8]
                if hash_antes
                else "N/A",
                "mensagem": (
                    f"Briefing ja estava atualizado (sem mudancas detectadas)\n"
                    f"*Hash atual:* `{hash_depois[:8] if hash_depois else hash_antes[:8] if hash_antes else 'N/A'}`"
                ),
            }

    except Exception as e:
        logger.error(f"Erro ao sincronizar briefing: {e}")
        return {"success": False, "error": str(e), "mensagem": f"Erro ao sincronizar briefing: {e}"}


async def _buscar_hash_atual() -> Optional[str]:
    """Busca hash do ultimo briefing sincronizado."""
    try:
        response = (
            supabase.table("briefing_sync_log")
            .select("doc_hash")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0].get("doc_hash")
        return None

    except Exception as e:
        logger.warning(f"Erro ao buscar hash atual: {e}")
        return None


async def _emitir_evento_sync(
    user_id: str, hash_antes: Optional[str], hash_depois: str, atualizado: bool, secoes: list
):
    """Emite evento BRIEFING_SYNC_TRIGGERED."""
    try:
        from app.services.business_events import emit_event
        from app.services.business_events.types import (
            BusinessEvent,
            EventType,
            EventSource,
        )

        await emit_event(
            BusinessEvent(
                event_type=EventType.BRIEFING_SYNC_TRIGGERED,
                source=EventSource.SLACK,
                event_props={
                    "actor_id": user_id,
                    "hash_antes": hash_antes,
                    "hash_depois": hash_depois,
                    "atualizado": atualizado,
                    "secoes_atualizadas": secoes,
                },
            )
        )

        logger.info(
            f"Evento BRIEFING_SYNC_TRIGGERED emitido: user={user_id}, atualizado={atualizado}"
        )

    except Exception as e:
        logger.error(f"Erro ao emitir evento de sync: {e}")
