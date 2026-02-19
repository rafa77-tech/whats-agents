"""
Conversation Summarizer - Sumarização de conversas longas.

Sprint 44 T02.3

Quando a conversa tem muitas mensagens, sumariza as mais antigas
mantendo apenas as recentes completas. Isso reduz tokens e melhora
a qualidade das respostas.

Estratégia:
- Se histórico tem <= THRESHOLD_MSGS: usa completo
- Se histórico tem > THRESHOLD_MSGS:
  - Sumariza as (N - MSGS_RECENTES) primeiras mensagens
  - Mantém as últimas MSGS_RECENTES completas
  - Contexto final = [resumo] + [mensagens_recentes]
"""

import logging
from typing import List, Dict, Optional, Tuple

from anthropic import AsyncAnthropic
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuração de thresholds
THRESHOLD_MSGS = 12  # Sumarizar se tiver mais que isso
MSGS_RECENTES = 5  # Manter as últimas N mensagens completas
MAX_TOKENS_RESUMO = 500  # Tokens máximos para o resumo


async def sumarizar_se_necessario(
    historico: List[Dict],
    conversa_id: Optional[str] = None,
) -> Tuple[str, List[Dict]]:
    """
    Sumariza histórico se necessário, retornando resumo + mensagens recentes.

    Args:
        historico: Lista de interações ordenadas (mais antigas primeiro)
        conversa_id: ID da conversa (para logging)

    Returns:
        Tupla (resumo, mensagens_recentes):
        - resumo: String vazia se não precisou sumarizar, ou resumo das antigas
        - mensagens_recentes: Lista de mensagens para usar completas
    """
    if not historico:
        return "", []

    total_msgs = len(historico)

    # Se não atingiu threshold, retorna tudo sem resumo
    if total_msgs <= THRESHOLD_MSGS:
        logger.debug(
            f"[Summarizer] Conversa {conversa_id or 'N/A'}: {total_msgs} msgs, "
            f"abaixo do threshold ({THRESHOLD_MSGS})"
        )
        return "", historico

    # Separar mensagens antigas (para resumo) e recentes (completas)
    msgs_para_resumir = historico[:-MSGS_RECENTES]
    msgs_recentes = historico[-MSGS_RECENTES:]

    logger.info(
        f"[Summarizer] T02.3: Conversa {conversa_id or 'N/A'}: {total_msgs} msgs, "
        f"sumarizando {len(msgs_para_resumir)} antigas, mantendo {len(msgs_recentes)} recentes"
    )

    # Gerar resumo das mensagens antigas
    resumo = await _gerar_resumo(msgs_para_resumir, conversa_id)

    return resumo, msgs_recentes


async def _gerar_resumo(
    mensagens: List[Dict],
    conversa_id: Optional[str] = None,
) -> str:
    """
    Gera resumo das mensagens usando Claude Haiku.

    Args:
        mensagens: Lista de mensagens a sumarizar
        conversa_id: ID da conversa para logging

    Returns:
        String com resumo da conversa
    """
    if not mensagens:
        return ""

    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Formatar mensagens para o prompt
        msgs_formatadas = _formatar_mensagens_para_resumo(mensagens)

        prompt = f"""Você é um assistente que resume conversas de WhatsApp.

Resuma a seguinte conversa de forma concisa, mantendo:
- Os pontos principais discutidos
- Decisões tomadas ou pendentes
- Informações importantes mencionadas (datas, valores, nomes)
- O tom geral da conversa (interesse, dúvida, reclamação)

NÃO inclua:
- Saudações repetidas
- Mensagens vazias ou de confirmação simples
- Detalhes irrelevantes

Conversa a resumir:
{msgs_formatadas}

RESUMO (máximo 150 palavras, em português):"""

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",  # Haiku para custo baixo
            max_tokens=MAX_TOKENS_RESUMO,
            messages=[{"role": "user", "content": prompt}],
        )

        resumo = response.content[0].text.strip()

        logger.debug(
            f"[Summarizer] Resumo gerado para conversa {conversa_id or 'N/A'}: "
            f"{len(resumo)} chars, {len(mensagens)} msgs resumidas"
        )

        return resumo

    except Exception as e:
        logger.warning(f"[Summarizer] Erro ao gerar resumo: {e}")
        # Fallback: resumo simples sem LLM
        return _gerar_resumo_fallback(mensagens)


def _formatar_mensagens_para_resumo(mensagens: List[Dict]) -> str:
    """Formata mensagens para incluir no prompt de resumo."""
    linhas = []
    for msg in mensagens:
        autor = msg.get("autor_tipo", "medico")
        remetente = "Médico" if autor == "medico" else "Júlia"
        conteudo = msg.get("conteudo", "")
        linhas.append(f"{remetente}: {conteudo}")

    return "\n".join(linhas)


def _gerar_resumo_fallback(mensagens: List[Dict]) -> str:
    """Gera resumo simplificado sem usar LLM (fallback)."""
    total = len(mensagens)
    msgs_medico = [m for m in mensagens if m.get("autor_tipo") == "medico"]
    [m for m in mensagens if m.get("autor_tipo") != "medico"]

    # Extrair primeira e última mensagem do médico
    primeira_medico = msgs_medico[0].get("conteudo", "")[:100] if msgs_medico else ""
    ultima_medico = msgs_medico[-1].get("conteudo", "")[:100] if msgs_medico else ""

    resumo = (
        f"[Resumo de {total} mensagens anteriores] "
        f'Médico iniciou com: "{primeira_medico}..." '
        f'Última msg do médico: "{ultima_medico}..."'
    )

    return resumo


def formatar_contexto_com_resumo(
    resumo: str,
    mensagens_recentes: List[Dict],
) -> str:
    """
    Formata contexto combinando resumo e mensagens recentes.

    Usado para incluir no prompt quando há summarization.

    Args:
        resumo: Resumo das mensagens antigas
        mensagens_recentes: Mensagens recentes completas

    Returns:
        Contexto formatado para o prompt
    """
    partes = []

    if resumo:
        partes.append(f"### Resumo das mensagens anteriores:\n{resumo}")

    if mensagens_recentes:
        partes.append("### Mensagens recentes:")
        for msg in mensagens_recentes:
            autor = msg.get("autor_tipo", "medico")
            remetente = "Médico" if autor == "medico" else "Júlia"
            conteudo = msg.get("conteudo", "")
            partes.append(f"{remetente}: {conteudo}")

    return "\n\n".join(partes) if partes else ""


# Métricas para observabilidade
_metricas = {
    "conversas_sumarizadas": 0,
    "tokens_economizados_estimado": 0,
}


def obter_metricas_summarizer() -> Dict:
    """Retorna métricas do summarizer para observabilidade."""
    return _metricas.copy()


async def registrar_summarization(
    conversa_id: str,
    msgs_originais: int,
    msgs_resumidas: int,
    tamanho_resumo: int,
) -> None:
    """Registra métricas de summarization."""
    _metricas["conversas_sumarizadas"] += 1
    # Estimativa: ~4 chars por token
    tokens_originais = sum(len(m.get("conteudo", "")) for m in []) // 4
    tokens_resumo = tamanho_resumo // 4
    _metricas["tokens_economizados_estimado"] += max(0, tokens_originais - tokens_resumo)

    logger.info(
        f"[Summarizer] Métricas: {_metricas['conversas_sumarizadas']} conversas sumarizadas, "
        f"~{_metricas['tokens_economizados_estimado']} tokens economizados"
    )
