"""
Heurística de classificação de mensagens de grupos.

Sprint 14 - E03 - Heurística de Classificação

Filtro rápido baseado em regex e keywords para descartar mensagens
que claramente não são ofertas de plantão.

Meta: Rejeitar 60-70% das mensagens (conversas normais, cumprimentos, etc)
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import GruposConfig


# =============================================================================
# S03.1 - Keywords Positivas (indicam oferta de plantão)
# =============================================================================

KEYWORDS_PLANTAO = [
    # Termos de vaga
    r"\bplant[aã]o\b",
    r"\bvaga\b",
    r"\bescala\b",
    r"\bcobertura\b",
    r"\bsubstitui[çc][aã]o\b",

    # Termos financeiros (não incluir R$ aqui, vai em valor separado)
    r"\breais\b",
    r"\bvalor\b",
    r"\bpago\b",
    r"\bpagamento\b",
    r"\bPJ\b",
    r"\bPF\b",

    # Horários/Períodos
    r"\bnoturno\b",
    r"\bdiurno\b",
    r"\b12h\b",
    r"\b24h\b",
    r"\bcinderela\b",
    r"\d{1,2}h\s*[àa]\s*\d{1,2}h",  # "19h às 7h"
    r"\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}",  # "19:00 - 07:00"

    # Datas
    r"\bdia\s+\d{1,2}\b",
    r"\d{1,2}/\d{1,2}",  # "28/12"
    r"\bamanh[aã]\b",
    r"\bhoje\b",
    r"\bsegunda\b|\bter[çc]a\b|\bquarta\b|\bquinta\b|\bsexta\b",
    r"\bs[aá]bado\b|\bdomingo\b",

    # Termos médicos
    r"\bm[eé]dico\b",
    r"\bdr\.?\b",
    r"\bCRM\b",
    r"\bplantoni[sz]ta\b",

    # Urgência
    r"\burgente\b",
    r"\bpreciso\b",
    r"\bdispon[ií]vel\b",
    r"\baberto\b",
]

KEYWORDS_HOSPITAL = [
    r"\bhospital\b",
    r"\bUPA\b",
    r"\bPS\b",
    r"\bpronto.?socorro\b",
    r"\bcl[ií]nica\b",
    r"\bHU\b",
    r"\bSanta Casa\b",
]

KEYWORDS_ESPECIALIDADE = [
    r"\bcl[ií]nica\s*m[eé]dica\b",
    r"\bCM\b",
    r"\bcardio\b",
    r"\bpediatria\b",
    r"\bortopedia\b",
    r"\bgineco\b",
    r"\bGO\b",
    r"\bcirurgia\b",
    r"\banestesia\b",
    r"\bUTI\b",
    r"\bintensivista\b",
    r"\bemerg[eê]ncia\b",
]


# =============================================================================
# S03.2 - Keywords Negativas (indicam que NÃO é oferta)
# =============================================================================

KEYWORDS_DESCARTE = [
    # Cumprimentos (início de mensagem)
    r"^bom\s*dia\b",
    r"^boa\s*(tarde|noite)\b",
    r"^ol[aá]\b",
    r"^oi\b",

    # Agradecimentos
    r"\bobrigad[oa]\b",
    r"\bvaleu\b",
    r"\bagradec",
    r"\btmj\b",

    # Confirmações simples (início de mensagem)
    r"^ok\b",
    r"^beleza\b",
    r"^blz\b",
    r"^show\b",
    r"^top\b",
    r"^massa\b",

    # Perguntas genéricas
    r"^quem\s",
    r"^algu[eé]m\s",

    # Reações
    r"^(kk|haha|rs)",
]

# Limites de tamanho (centralizados em config)
MIN_TAMANHO_MENSAGEM = GruposConfig.MIN_TAMANHO_MENSAGEM
MAX_TAMANHO_MENSAGEM = GruposConfig.MAX_TAMANHO_MENSAGEM

# Threshold para passar
THRESHOLD_SCORE = GruposConfig.THRESHOLD_HEURISTICA


# =============================================================================
# S03.3 - Função de Score Heurístico
# =============================================================================

@dataclass
class ResultadoHeuristica:
    """Resultado da análise heurística."""
    passou: bool
    score: float
    keywords_encontradas: List[str]
    motivo_rejeicao: Optional[str] = None


def normalizar_texto(texto: str) -> str:
    """Normaliza texto para análise."""
    if not texto:
        return ""

    # Lowercase
    texto = texto.lower()

    # Remover espaços extras
    texto = " ".join(texto.split())

    return texto


def calcular_score_heuristica(texto: str) -> ResultadoHeuristica:
    """
    Calcula score heurístico da mensagem.

    Args:
        texto: Texto da mensagem

    Returns:
        ResultadoHeuristica com score e keywords
    """
    if not texto:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="texto_vazio"
        )

    texto_norm = normalizar_texto(texto)
    texto_len = len(texto_norm)

    # Verificar tamanho
    if texto_len < MIN_TAMANHO_MENSAGEM:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="muito_curta"
        )

    if texto_len > MAX_TAMANHO_MENSAGEM:
        return ResultadoHeuristica(
            passou=False,
            score=0.0,
            keywords_encontradas=[],
            motivo_rejeicao="muito_longa"
        )

    # Primeiro, verificar se há keywords positivas fortes
    # Se houver, não rejeitar por keywords negativas
    tem_keyword_positiva_forte = False
    for pattern in KEYWORDS_PLANTAO_COMPILED:
        if pattern.search(texto_norm):
            tem_keyword_positiva_forte = True
            break

    if not tem_keyword_positiva_forte:
        for pattern in KEYWORDS_HOSPITAL_COMPILED:
            if pattern.search(texto_norm):
                tem_keyword_positiva_forte = True
                break

    # Verificar keywords negativas (só se não houver positivas fortes)
    if not tem_keyword_positiva_forte:
        for pattern in KEYWORDS_DESCARTE_COMPILED:
            if pattern.search(texto_norm):
                return ResultadoHeuristica(
                    passou=False,
                    score=0.0,
                    keywords_encontradas=[],
                    motivo_rejeicao="keyword_negativa"
                )

    # Calcular score positivo
    keywords_encontradas = []
    score = 0.0

    # Keywords de plantão (peso 0.3)
    for pattern in KEYWORDS_PLANTAO_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"plantao:{match.group()}")
            score += 0.3
            break  # Só conta uma vez por categoria

    # Keywords de hospital (peso 0.25)
    for pattern in KEYWORDS_HOSPITAL_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"hospital:{match.group()}")
            score += 0.25
            break

    # Keywords de especialidade (peso 0.25)
    for pattern in KEYWORDS_ESPECIALIDADE_COMPILED:
        match = pattern.search(texto_norm)
        if match:
            keywords_encontradas.append(f"especialidade:{match.group()}")
            score += 0.25
            break

    # Valor mencionado (peso 0.2)
    if VALOR_PATTERN_COMPILED.search(texto_norm):
        keywords_encontradas.append("valor:mencionado")
        score += 0.2

    # Normalizar score para 0-1
    score = min(score, 1.0)

    # Verificar threshold
    passou = score >= THRESHOLD_SCORE

    return ResultadoHeuristica(
        passou=passou,
        score=score,
        keywords_encontradas=keywords_encontradas,
        motivo_rejeicao=None if passou else "score_baixo"
    )


# =============================================================================
# Compilar patterns na inicialização (performance)
# =============================================================================

KEYWORDS_PLANTAO_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_PLANTAO]
KEYWORDS_HOSPITAL_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_HOSPITAL]
KEYWORDS_ESPECIALIDADE_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_ESPECIALIDADE]
KEYWORDS_DESCARTE_COMPILED = [re.compile(p, re.IGNORECASE) for p in KEYWORDS_DESCARTE]
VALOR_PATTERN_COMPILED = re.compile(r"r\$\s*[\d.,]+|\d+\s*(mil|k)\b", re.IGNORECASE)
