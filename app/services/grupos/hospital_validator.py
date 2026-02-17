"""
Validador de nomes de hospitais.

Sprint 60 - Épico 1: Gate de validação de nomes.
Impede que registros lixo sejam criados no banco.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ResultadoValidacao:
    """Resultado da validação de nome de hospital."""

    valido: bool
    motivo: Optional[str] = None
    score: float = 0.0  # 0.0 = inválido, 1.0 = certamente hospital


# Palavras genéricas ou entidades não-médicas (lowercase, sem acento)
BLOCKLIST_PALAVRAS = frozenset(
    {
        "hospedagem",
        "verificar",
        "nao informado",
        "a serem definidas",
        "inbox",
        "amazon",
        "mercado envios",
        "atacadao",
        "ypioca",
        "carrefour",
        "magazine luiza",
        "casas bahia",
        "mercado livre",
        "shopee",
        "aliexpress",
        "americanas",
        "a definir",
        "a confirmar",
        "nao definido",
        "sem informacao",
        "indefinido",
        "teste",
        "desconhecido",
        "outro",
        "outros",
        "diversos",
        "vários",
        "varios",
    }
)

# Padrões regex que indicam lixo
BLOCKLIST_REGEX = [
    re.compile(r"\w+:\s*\w+\s*\("),  # Nomes de contato: "amar: Queila ()"
    re.compile(r"R\$\s*[\d.,]+"),  # Valores monetários
    re.compile(r"VALOR\s+BRUTO", re.IGNORECASE),  # Fragmentos de anúncio
    re.compile(r"[\U0001F4B0\U0001F4B5\U0001F4B2]"),  # Emojis de dinheiro
    re.compile(r"^\d+[hH]\s*(às|as|a)\s*\d+"),  # Horários: "12h às 19h"
    re.compile(r"^\d{2}/\d{2}"),  # Datas: "15/03"
    re.compile(r"whatsapp|telegram|instagram", re.IGNORECASE),
]

# Prefixos que indicam nome de hospital
PREFIXOS_HOSPITALARES = [
    "hospital",
    "hosp.",
    "hosp ",
    "h. ",
    "upa ",
    "ubs ",
    "ama ",
    "santa casa",
    "pronto socorro",
    "pronto-socorro",
    "ps ",
    "p.s.",
    "hm ",
    "hge",
    "hgp",
    "clinica",
    "clínica",
    "instituto",
    "maternidade",
    "centro medico",
    "centro médico",
    "laboratorio",
    "laboratório",
    "samu",
    "cema",
    "hc ",
    "beneficencia",
    "beneficência",
    "pronto atendimento",
    "caps ",
]

# Especialidades médicas (lowercase, sem acento) — não são nomes de hospital
ESPECIALIDADES_COMO_HOSPITAL = frozenset(
    {
        "acupuntura",
        "alergia",
        "imunologia",
        "anestesiologia",
        "angiologia",
        "cardiologia",
        "cirurgia cardiovascular",
        "cirurgia geral",
        "cirurgia plastica",
        "cirurgia vascular",
        "clinica medica",
        "coloproctologia",
        "dermatologia",
        "endocrinologia",
        "endoscopia",
        "gastroenterologia",
        "generalista",
        "genetica",
        "geriatria",
        "ginecologia",
        "obstetricia",
        "hematologia",
        "homeopatia",
        "infectologia",
        "mastologia",
        "nefrologia",
        "neonatologia",
        "neurocirurgia",
        "neurologia",
        "nutrologia",
        "oftalmologia",
        "oncologia",
        "ortopedia",
        "traumatologia",
        "otorrinolaringologia",
        "patologia",
        "pediatria",
        "pneumologia",
        "psiquiatria",
        "radiologia",
        "radioterapia",
        "reumatologia",
        "urologia",
        "medicina intensiva",
        "medicina do trabalho",
        "medicina de familia",
        "medicina esportiva",
    }
)


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto: lowercase, sem acento, sem chars especiais."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def _contem_prefixo_hospitalar(texto_lower: str) -> bool:
    """Verifica se o texto contém prefixo indicativo de hospital."""
    for prefixo in PREFIXOS_HOSPITALARES:
        if prefixo in texto_lower:
            return True
    return False


def validar_nome_hospital(nome: str) -> ResultadoValidacao:
    """
    Valida se um texto é um nome de hospital plausível.

    Args:
        nome: Texto candidato a nome de hospital

    Returns:
        ResultadoValidacao com valido, motivo e score
    """
    if not nome:
        return ResultadoValidacao(valido=False, motivo="nome_vazio", score=0.0)

    nome_strip = nome.strip()
    nome_norm = _normalizar_texto(nome_strip)

    # 1. Mínimo 3 caracteres após normalização
    if len(nome_norm) < 3:
        return ResultadoValidacao(valido=False, motivo="nome_muito_curto", score=0.0)

    # 2. Deve conter pelo menos uma letra
    if not any(c.isalpha() for c in nome_norm):
        return ResultadoValidacao(valido=False, motivo="sem_letras", score=0.0)

    # 3. Máximo 120 caracteres
    if len(nome_strip) > 120:
        return ResultadoValidacao(valido=False, motivo="nome_muito_longo", score=0.0)

    # 4. Blocklist de palavras exatas
    if nome_norm in BLOCKLIST_PALAVRAS:
        return ResultadoValidacao(valido=False, motivo=f"blocklist_palavra:{nome_norm}", score=0.0)

    # 4b. Blocklist parcial — verificar se o nome normalizado contém alguma palavra bloqueada
    for palavra in BLOCKLIST_PALAVRAS:
        if len(palavra) >= 6 and nome_norm == palavra:
            return ResultadoValidacao(
                valido=False,
                motivo=f"blocklist_parcial:{palavra}",
                score=0.0,
            )

    # 5. Blocklist de regex
    for pattern in BLOCKLIST_REGEX:
        if pattern.search(nome_strip):
            return ResultadoValidacao(
                valido=False,
                motivo=f"blocklist_regex:{pattern.pattern[:30]}",
                score=0.0,
            )

    # 6. Especialidade como hospital (palavra única ou exata)
    if nome_norm in ESPECIALIDADES_COMO_HOSPITAL:
        return ResultadoValidacao(
            valido=False,
            motivo=f"especialidade_como_hospital:{nome_norm}",
            score=0.0,
        )

    # 7. Fragmento truncado: 1 palavra com < 5 chars
    palavras = nome_norm.split()
    if len(palavras) == 1 and len(palavras[0]) < 5:
        return ResultadoValidacao(valido=False, motivo="fragmento_truncado", score=0.0)

    # 8. Heurística positiva: prefixo hospitalar
    tem_prefixo = _contem_prefixo_hospitalar(nome_norm)

    if tem_prefixo:
        return ResultadoValidacao(valido=True, score=0.9)

    # Nomes com múltiplas palavras sem prefixo: score médio
    if len(palavras) >= 2:
        return ResultadoValidacao(valido=True, score=0.5)

    # Palavra única >= 4 chars sem prefixo: score baixo mas aceito
    return ResultadoValidacao(valido=True, score=0.4)
