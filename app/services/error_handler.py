"""
Tratamento de erros e mensagens amigáveis para o usuário.
"""

import random
import logging

logger = logging.getLogger(__name__)

MENSAGENS_ERRO = {
    "llm_timeout": [
        "Opa, demorou mais que o esperado aqui 😅 Pode tentar de novo?",
        "Eita, deu um tempo maior que o normal. Tenta de novo?",
        "Ops, demorou um pouco. Pode repetir?",
    ],
    "llm_error": [
        "Desculpa, tive um probleminha aqui. Pode tentar de novo?",
        "Opa, deu um erro aqui. Tenta de novo?",
        "Eita, algo deu errado. Pode repetir a mensagem?",
    ],
    "whatsapp_error": [
        "Ops, tive um probleminha pra enviar a mensagem. Tenta de novo?",
        "Eita, não consegui enviar agora. Pode tentar mais uma vez?",
        "Desculpa, deu um erro no envio. Tenta de novo?",
    ],
    "generico": [
        "Opa, deu um probleminha aqui 😅 Pode tentar de novo?",
        "Eita, algo deu errado. Tenta de novo?",
        "Ops, tive um erro aqui. Pode repetir?",
        "Desculpa, deu um problema. Tenta de novo?",
    ],
}


def obter_mensagem_erro(tipo: str = "generico") -> str:
    """
    Retorna mensagem de erro amigável e informal.

    Args:
        tipo: Tipo de erro (llm_timeout, llm_error, whatsapp_error, generico)

    Returns:
        Mensagem de erro amigável
    """
    mensagens = MENSAGENS_ERRO.get(tipo, MENSAGENS_ERRO["generico"])
    return random.choice(mensagens)


def logar_erro(tipo: str, erro: Exception, contexto: dict = None):
    """
    Loga erro com contexto.

    Args:
        tipo: Tipo de erro
        erro: Exceção ocorrida
        contexto: Contexto adicional (opcional)
    """
    contexto_str = f" | Contexto: {contexto}" if contexto else ""
    logger.error(f"Erro {tipo}: {erro}{contexto_str}", exc_info=True)
