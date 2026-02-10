"""
Servico de deteccao de triggers de handoff.
Identifica quando Julia deve passar a conversa para um humano.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Frases que indicam pedido explicito de humano
FRASES_PEDIDO_HUMANO = [
    r"falar com (um |uma )?(pessoa|humano|atendente|supervisor|supervisora|gente)",
    r"quero (um |uma )?(pessoa|humano|atendente|gente)",
    r"(passa|transfere) (pra|para) (um |uma )?(supervisor|supervisora|gerente|humano)",
    r"nao (quero|vou) falar com (robo|bot|maquina)",
    r"(isso|vc|voce) e (um |uma )?(robo|bot|ia|inteligencia artificial)",
    r"me (liga|ligue|telefona)",
    r"(preciso|quero) (ligar|telefonar)",
    r"fala com (alguem|gente)( de verdade)?",
    r"atendente (humano|de verdade)",
    r"tem (alguem|gente) ai\?",
    r"quero falar com gente",
]

# Frases que indicam situacao juridica/formal
FRASES_JURIDICO = [
    r"\badvogado\b",
    r"\bprocesso\b",
    r"\bjustica\b",
    r"(meu|minha) advogad[oa]",
    r"\bprocon\b",
    r"reclamacao formal",
    r"notificacao extrajudicial",
    r"\bdenuncia\b",
    r"\bdenunciar\b",
    r"\bcrm\b.*\breclamacao\b",
    r"\bautuacao\b",
]

# Palavras que indicam sentimento negativo forte
PALAVRAS_NEGATIVAS = [
    r"\babsurd[oa]\b",
    r"\bridicul[oa]\b",
    r"\bvergonha\b",
    r"\bdesrespeit[oa]\b",
    r"falta de respeito",
    r"\bnunca mais\b",
    r"\bpessim[oa]\b",
    r"\bhorrivel\b",
    r"\bodeio\b",
    r"\braiva\b",
    r"\binaceitavel\b",
    r"\bescandalo\b",
    r"\bpalhaçada\b",
    r"\bsafad[oa]\b",
    r"\bmentir[oa]\b",
    r"\bgolpe\b",
    r"\bfraud[ae]\b",
]


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto removendo acentos para matching mais robusto.
    """
    return (
        texto.lower()
        .replace("ã", "a")
        .replace("á", "a")
        .replace("â", "a")
        .replace("à", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("è", "e")
        .replace("í", "i")
        .replace("î", "i")
        .replace("ì", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ò", "o")
        .replace("ú", "u")
        .replace("û", "u")
        .replace("ù", "u")
        .replace("ç", "c")
    )


def detectar_pedido_humano(texto_normalizado: str) -> bool:
    """
    Detecta se mensagem indica pedido explicito de falar com humano.
    """
    for padrao in FRASES_PEDIDO_HUMANO:
        if re.search(padrao, texto_normalizado):
            return True
    return False


def detectar_situacao_juridica(texto_normalizado: str) -> bool:
    """
    Detecta se mensagem indica situacao juridica/formal.
    """
    for padrao in FRASES_JURIDICO:
        if re.search(padrao, texto_normalizado):
            return True
    return False


def contar_palavras_negativas(texto_normalizado: str) -> int:
    """
    Conta quantas palavras negativas fortes estao na mensagem.
    """
    count = 0
    for padrao in PALAVRAS_NEGATIVAS:
        if re.search(padrao, texto_normalizado):
            count += 1
    return count


def detectar_trigger_handoff(texto: str) -> Optional[dict]:
    """
    Analisa mensagem e detecta se ha trigger de handoff.

    Args:
        texto: Texto da mensagem do medico

    Returns:
        dict com {trigger: True, motivo: str, tipo: str} ou None
    """
    if not texto:
        return None

    texto_normalizado = _normalizar_texto(texto)

    # 1. Verificar pedido explicito de humano
    if detectar_pedido_humano(texto_normalizado):
        logger.info(f"Trigger handoff: pedido_humano em '{texto[:50]}'")
        return {
            "trigger": True,
            "motivo": "Medico pediu para falar com humano",
            "tipo": "pedido_humano",
        }

    # 2. Verificar situacao juridica
    if detectar_situacao_juridica(texto_normalizado):
        logger.info(f"Trigger handoff: juridico em '{texto[:50]}'")
        return {"trigger": True, "motivo": "Situacao juridica/formal detectada", "tipo": "juridico"}

    # 3. Verificar sentimento negativo forte (2+ palavras)
    negativos = contar_palavras_negativas(texto_normalizado)
    if negativos >= 2:
        logger.info(
            f"Trigger handoff: sentimento_negativo ({negativos} palavras) em '{texto[:50]}'"
        )
        return {
            "trigger": True,
            "motivo": "Sentimento muito negativo detectado",
            "tipo": "sentimento_negativo",
        }

    return None


def obter_tipo_trigger(texto: str) -> Optional[str]:
    """
    Retorna apenas o tipo do trigger, se houver.
    Util para verificacoes rapidas.

    Args:
        texto: Texto da mensagem

    Returns:
        Tipo do trigger ou None
    """
    resultado = detectar_trigger_handoff(texto)
    if resultado:
        return resultado["tipo"]
    return None
