"""
Utilitários para processamento de mensagens.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

RESPOSTA_MENSAGEM_LONGA = (
    "Eita, muita coisa aí! 😅\n\nConsegue me resumir o principal? Assim consigo te ajudar melhor"
)


def quebrar_mensagem(texto: str, max_chars: int = 400) -> list[str]:
    """
    Quebra mensagem longa em várias curtas.

    Regras:
    - Máximo 400 caracteres por mensagem (adequado para WhatsApp)
    - Quebra em pontos naturais (., !, ?)
    - Mantém emojis com o texto anterior
    - Não quebra no meio de palavras

    Args:
        texto: Texto a quebrar
        max_chars: Máximo de caracteres por mensagem

    Returns:
        Lista de mensagens curtas
    """
    if len(texto) <= max_chars:
        return [texto]

    mensagens = []
    resto = texto

    while resto:
        if len(resto) <= max_chars:
            mensagens.append(resto.strip())
            break

        # Encontrar ponto de quebra
        # Prioridade: ponto final, exclamação, interrogação, vírgula
        ponto_quebra = -1

        for separador in [". ", "! ", "? ", ", ", " "]:
            # Procurar última ocorrência antes do limite
            idx = resto.rfind(separador, 0, max_chars)
            if idx > 0:
                ponto_quebra = idx + len(separador) - 1
                break

        if ponto_quebra == -1:
            # Forçar quebra no limite
            ponto_quebra = max_chars

        # Extrair mensagem
        msg = resto[:ponto_quebra].strip()
        resto = resto[ponto_quebra:].strip()

        if msg:
            mensagens.append(msg)

    return mensagens


def tratar_mensagem_longa(texto: str) -> tuple[str, str]:
    """
    Trata mensagem longa.

    Args:
        texto: Texto da mensagem

    Returns:
        (texto_processado, acao)
        acao: "normal", "truncada", "pedir_resumo"
    """
    tamanho = len(texto)

    if tamanho <= settings.MAX_MENSAGEM_CHARS:
        return texto, "normal"

    if tamanho <= settings.MAX_MENSAGEM_CHARS_TRUNCAR:
        # Truncar e avisar
        texto_truncado = texto[: settings.MAX_MENSAGEM_CHARS] + "..."
        return texto_truncado, "truncada"

    # Muito longa, pedir resumo
    return texto[:1000], "pedir_resumo"
