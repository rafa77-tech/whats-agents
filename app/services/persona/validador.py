"""
Validador de Persona para Julia.

Sprint 37 - Epic 10

Valida se respostas de Julia estão de acordo com a persona definida.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# Padrões que indicam bullet points
PADROES_BULLET_POINT = [
    r"^[\s]*[-•*]\s",  # Início de linha com - • *
    r"\n[\s]*[-•*]\s",  # Nova linha com - • *
    r"^\d+\.\s",  # Início de linha com número e ponto
    r"\n\d+\.\s",  # Nova linha com número e ponto
]

# Padrões de linguagem muito formal
PADROES_FORMAL_DEMAIS = [
    r"\bprezado\b",
    r"\batenciosamente\b",
    r"\bcordialmente\b",
    r"\bvenho\s+por\s+meio\b",
    r"\bsolicito\b",
    r"\binformo\b",
    r"\bconforme\b",
    r"\bno\s+entanto\b",
    r"\bportanto\b",
    r"\bdesta\s+forma\b",
    r"\bsenhor(a)?\b",
    r"\besclareço\b",
    r"\baproveito\s+para\b",
]

# Padrões que revelam ser bot/IA
PADROES_REVELA_BOT = [
    r"\bsou\s+(uma?\s+)?(ia|bot|robo|robô|assistente\s+virtual)\b",
    r"\binteligência\s+artificial\b",
    r"\binteligencia\s+artificial\b",
    r"\bmodelo\s+de\s+linguagem\b",
    r"\bassistente\s+de\s+ia\b",
    r"\bcomo\s+uma?\s+ia\b",
    r"\bfui\s+programad[ao]\b",
    r"\bmeus\s+criadores\b",
    r"\bfui\s+treinad[ao]\b",
]

# Abreviações informais esperadas da Julia
ABREVIACOES_INFORMAIS = [
    "vc",
    "pra",
    "ta",
    "blz",
    "msg",
    "ne",
    "q",
    "tb",
    "tbm",
    "td",
    "hj",
    "amanha",  # sem acento
    "qd",
    "qdo",
]


@dataclass
class ResultadoValidacaoResposta:
    """Resultado da validação de resposta."""

    valido: bool
    score: float  # 0.0 - 1.0
    problemas: list[str] = field(default_factory=list)
    sugestao_correcao: Optional[str] = None


def validar_resposta_persona(
    resposta: str,
    max_linhas: int = 4,
    verificar_abreviacoes: bool = True,
) -> ResultadoValidacaoResposta:
    """
    Valida se resposta está de acordo com a persona Julia.

    Args:
        resposta: Texto da resposta a validar
        max_linhas: Máximo de linhas permitidas
        verificar_abreviacoes: Se deve verificar uso de abreviações

    Returns:
        ResultadoValidacaoResposta com análise
    """
    problemas = []
    score = 1.0

    # 1. Verificar bullet points
    if not validar_nao_bullet_points(resposta):
        problemas.append("Contém bullet points (não permitido)")
        score -= 0.3

    # 2. Verificar se revela ser bot
    if not validar_nao_revela_bot(resposta):
        problemas.append("Revela ser IA/bot (violação crítica)")
        score -= 0.5  # Penalidade alta

    # 3. Verificar linguagem formal demais
    if not validar_tom_informal(resposta):
        problemas.append("Linguagem muito formal")
        score -= 0.2

    # 4. Verificar quantidade de linhas
    linhas = resposta.strip().split("\n")
    if len(linhas) > max_linhas:
        problemas.append(f"Muitas linhas ({len(linhas)} > {max_linhas})")
        score -= 0.15

    # 5. Verificar uso de abreviações (opcional)
    if verificar_abreviacoes:
        tem_abreviacao = any(abrev in resposta.lower() for abrev in ABREVIACOES_INFORMAIS)
        if not tem_abreviacao and len(resposta) > 50:
            # Só penaliza se a resposta é longa e não tem nenhuma abreviação
            score -= 0.05

    # Garantir score entre 0 e 1
    score = max(0.0, min(1.0, score))

    # Determinar se é válido
    valido = len(problemas) == 0 or (score >= 0.7 and "crítica" not in str(problemas))

    return ResultadoValidacaoResposta(
        valido=valido,
        score=score,
        problemas=problemas,
        sugestao_correcao=sugerir_correcao(resposta) if problemas else None,
    )


def validar_tom_informal(texto: str) -> bool:
    """
    Verifica se texto não é muito formal.

    Returns:
        True se tom está adequado (informal)
    """
    texto_lower = texto.lower()
    for padrao in PADROES_FORMAL_DEMAIS:
        if re.search(padrao, texto_lower, re.IGNORECASE):
            return False
    return True


def validar_nao_bullet_points(texto: str) -> bool:
    """
    Verifica se texto não contém bullet points.

    Returns:
        True se não contém bullet points
    """
    for padrao in PADROES_BULLET_POINT:
        if re.search(padrao, texto, re.MULTILINE):
            return False
    return True


def validar_nao_revela_bot(texto: str) -> bool:
    """
    Verifica se texto não revela ser bot/IA.

    Returns:
        True se não revela ser bot
    """
    texto_lower = texto.lower()
    for padrao in PADROES_REVELA_BOT:
        if re.search(padrao, texto_lower, re.IGNORECASE):
            return False
    return True


def sugerir_correcao(resposta: str) -> Optional[str]:
    """
    Sugere correção para resposta problemática.

    Args:
        resposta: Texto original

    Returns:
        Sugestão de correção ou None
    """
    sugestoes = []

    # Verificar formalidade
    if not validar_tom_informal(resposta):
        sugestoes.append("Use linguagem mais informal (ex: 'vc' em vez de 'você')")

    # Verificar bullet points
    if not validar_nao_bullet_points(resposta):
        sugestoes.append("Remova listas com bullet points, escreva em texto corrido")

    # Verificar bot
    if not validar_nao_revela_bot(resposta):
        sugestoes.append("CRÍTICO: Nunca revele que é IA/bot")

    if sugestoes:
        return "; ".join(sugestoes)
    return None


def calcular_score_naturalidade(resposta: str) -> float:
    """
    Calcula score de naturalidade da resposta.

    Quanto mais natural/informal, maior o score.

    Args:
        resposta: Texto a analisar

    Returns:
        Score de 0.0 a 1.0
    """
    score = 1.0

    # Penalizar bullet points
    if not validar_nao_bullet_points(resposta):
        score -= 0.3

    # Penalizar linguagem formal
    texto_lower = resposta.lower()
    padroes_formais_encontrados = sum(
        1 for padrao in PADROES_FORMAL_DEMAIS if re.search(padrao, texto_lower)
    )
    score -= padroes_formais_encontrados * 0.1

    # Penalizar respostas muito longas
    linhas = resposta.strip().split("\n")
    if len(linhas) > 5:
        score -= 0.2
    elif len(linhas) > 3:
        score -= 0.1

    # Bonificar uso de abreviações informais
    abreviacoes_usadas = sum(1 for abrev in ABREVIACOES_INFORMAIS if abrev in texto_lower)
    score += min(0.1, abreviacoes_usadas * 0.02)

    # Garantir entre 0 e 1
    return max(0.0, min(1.0, score))
