"""
Parser de mensagem para extração de vagas.

Separa a mensagem em seções lógicas:
- Local (hospital, endereço)
- Datas (datas e períodos)
- Valores (valores e regras)
- Contato (nome e telefone)

Sprint 40 - E02: Parser de Mensagem
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from app.core.logging import get_logger

logger = get_logger(__name__)


class TipoSecao(str, Enum):
    """Tipos de seção identificados."""

    LOCAL = "local"
    DATA = "data"
    VALOR = "valor"
    CONTATO = "contato"
    ESPECIALIDADE = "especialidade"
    OBSERVACAO = "observacao"
    DESCONHECIDO = "desconhecido"


@dataclass
class LinhaParsed:
    """Uma linha com sua classificação."""

    texto: str
    tipo: TipoSecao
    indice: int
    confianca: float = 0.0


@dataclass
class MensagemParsed:
    """Resultado do parsing de uma mensagem."""

    texto_original: str = ""
    linhas: List[LinhaParsed] = field(default_factory=list)

    # Seções agrupadas (linhas adjacentes do mesmo tipo)
    secoes_local: List[str] = field(default_factory=list)
    secoes_data: List[str] = field(default_factory=list)
    secoes_valor: List[str] = field(default_factory=list)
    secoes_contato: List[str] = field(default_factory=list)
    secoes_especialidade: List[str] = field(default_factory=list)

    @property
    def tem_local(self) -> bool:
        """Verifica se tem seção de local."""
        return len(self.secoes_local) > 0

    @property
    def tem_datas(self) -> bool:
        """Verifica se tem seção de datas."""
        return len(self.secoes_data) > 0

    @property
    def tem_valores(self) -> bool:
        """Verifica se tem seção de valores."""
        return len(self.secoes_valor) > 0

    @property
    def tem_contato(self) -> bool:
        """Verifica se tem seção de contato."""
        return len(self.secoes_contato) > 0


# =============================================================================
# Padrões de Detecção
# =============================================================================

# Emojis indicadores de seção
EMOJIS_LOCAL = {"📍", "🏥", "🏨", "🏢", "📌", "🗺️", "🗺"}
EMOJIS_DATA = {"🗓", "📅", "📆", "🗓️", "⏰", "🕐", "🕛"}
EMOJIS_VALOR = {"💰", "💵", "💲", "🤑", "💸", "💳"}
EMOJIS_CONTATO = {"📲", "📞", "📱", "☎️", "🤙", "💬", "👤", "☎"}

# Palavras-chave por seção
KEYWORDS_LOCAL = {
    "hospital",
    "clínica",
    "clinica",
    "upa",
    "pronto socorro",
    "pronto atendimento",
    "ps ",
    "pa ",
    "ama ",
    "ubs ",
    "caps ",
    "santa casa",
    "beneficência",
    "beneficencia",
    "maternidade",
    "estrada",
    "avenida",
    "av.",
    "rua",
    "r.",
    "alameda",
    "al.",
}

KEYWORDS_DATA = {
    "segunda",
    "terça",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sábado",
    "sabado",
    "domingo",
    "seg",
    "ter",
    "qua",
    "qui",
    "sex",
    "sab",
    "dom",
    "manhã",
    "manha",
    "tarde",
    "noite",
    "diurno",
    "noturno",
    "sd",
    "sn",
    "cinderela",
    "plantão",
    "plantao",
}

KEYWORDS_VALOR = {
    "r$",
    "reais",
    "valor",
    "paga",
    "pagamento",
    "pix",
    "seg-sex",
    "seg a sex",
    "sab-dom",
    "sab e dom",
    "segunda a sexta",
    "sábado e domingo",
    "sabado e domingo",
}

KEYWORDS_CONTATO = {
    "contato",
    "interessados",
    "falar com",
    "chamar",
    "ligar",
    "whatsapp",
    "whats",
    "zap",
    "wa.me",
    "telefone",
    "fone",
    "cel",
    "celular",
    "@",
}

KEYWORDS_ESPECIALIDADE = {
    "clínica médica",
    "clinica medica",
    "cm",
    "pediatria",
    "ped",
    "ortopedia",
    "orto",
    "cardiologia",
    "cardio",
    "ginecologia",
    "gino",
    "go",
    "cirurgia",
    "cir",
    "neurologia",
    "neuro",
    "psiquiatria",
    "psiq",
    "anestesiologia",
    "anestesio",
    "usg",
    "ultrassonografia",
    "endoscopia",
    "emergência",
    "emergencia",
}

# Padrões regex
PATTERN_DATA = re.compile(
    r"\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?"  # dd/mm ou dd/mm/yyyy
)

PATTERN_HORARIO = re.compile(
    r"\d{1,2}[h:]?\d{0,2}\s*[-–aà]\s*\d{1,2}[h:]?\d{0,2}"  # 7h-13h, 19:00-07:00
)

# Valor monetário - exige R$ ou valor típico de plantão (>= 1.000)
PATTERN_VALOR_COM_RS = re.compile(
    r"R\$\s*\d{1,3}(?:[.,]\d{3})*",
    re.IGNORECASE,  # R$ 1.800, R$1800
)

PATTERN_VALOR_GRANDE = re.compile(
    r"\d{1,2}[.,]\d{3}"  # 1.800, 1,800 (valores com milhar)
)

PATTERN_TELEFONE = re.compile(r"(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?)?\d{4}[-.\s]?\d{4}")

PATTERN_WHATSAPP_LINK = re.compile(r"wa\.me/\d+")


def _tem_emoji(texto: str, emojis: set) -> bool:
    """Verifica se texto contém algum emoji do conjunto."""
    return any(emoji in texto for emoji in emojis)


def _tem_keyword(texto: str, keywords: set) -> bool:
    """Verifica se texto contém alguma keyword."""
    texto_lower = texto.lower()
    for kw in keywords:
        # Para keywords curtas (<=3 chars) que são puramente alfanuméricas, usar word boundary
        # Isso evita "ter" casar com "Interessados", mas permite "av." ou "r$" casar normalmente
        if len(kw) <= 3 and kw.isalnum():
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, texto_lower):
                return True
        elif kw in texto_lower:
            return True
    return False


def _classificar_linha(linha: str, indice: int) -> LinhaParsed:
    """
    Classifica uma linha de texto.

    A classificação usa múltiplos sinais:
    1. Emojis indicadores (peso alto)
    2. Keywords específicas (peso médio)
    3. Padrões regex (peso médio)
    4. Regras de desempate

    Returns:
        LinhaParsed com tipo e confiança
    """
    linha_stripped = linha.strip()

    if not linha_stripped:
        return LinhaParsed(texto=linha, tipo=TipoSecao.DESCONHECIDO, indice=indice, confianca=0.0)

    scores = {
        TipoSecao.LOCAL: 0.0,
        TipoSecao.DATA: 0.0,
        TipoSecao.VALOR: 0.0,
        TipoSecao.CONTATO: 0.0,
        TipoSecao.ESPECIALIDADE: 0.0,
    }

    linha_lower = linha_stripped.lower()
    tem_rs = "r$" in linha_lower or PATTERN_VALOR_COM_RS.search(linha_stripped)
    tem_valor_grande = PATTERN_VALOR_GRANDE.search(linha_stripped)
    tem_data_pattern = PATTERN_DATA.search(linha_stripped)
    tem_telefone = PATTERN_TELEFONE.search(linha_stripped) or PATTERN_WHATSAPP_LINK.search(
        linha_stripped
    )

    # 1. Emojis (peso 0.5)
    if _tem_emoji(linha_stripped, EMOJIS_LOCAL):
        scores[TipoSecao.LOCAL] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_DATA):
        scores[TipoSecao.DATA] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_VALOR):
        scores[TipoSecao.VALOR] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_CONTATO):
        scores[TipoSecao.CONTATO] += 0.5

    # 2. Keywords (peso 0.3) - com regras especiais
    if _tem_keyword(linha_stripped, KEYWORDS_LOCAL):
        scores[TipoSecao.LOCAL] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_CONTATO):
        scores[TipoSecao.CONTATO] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_ESPECIALIDADE):
        scores[TipoSecao.ESPECIALIDADE] += 0.3

    # Keywords de valor - peso maior se tem R$
    if _tem_keyword(linha_stripped, KEYWORDS_VALOR):
        scores[TipoSecao.VALOR] += 0.4 if tem_rs else 0.3

    # Keywords de data - NÃO adicionar se tem R$ sem data pattern
    # (evita "Segunda a Sexta: R$ 1.700" ser classificado como DATA)
    if _tem_keyword(linha_stripped, KEYWORDS_DATA):
        if tem_rs and not tem_data_pattern:
            # Linha com R$ e dia da semana mas sem data = provavelmente VALOR
            scores[TipoSecao.VALOR] += 0.3
        else:
            scores[TipoSecao.DATA] += 0.3

    # 3. Padrões regex
    if tem_data_pattern:
        scores[TipoSecao.DATA] += 0.3
    # Só adicionar score de horário se não houver telefone
    # (evita "99999-9999" ser reconhecido como "99h-99h")
    if PATTERN_HORARIO.search(linha_stripped) and not tem_telefone:
        scores[TipoSecao.DATA] += 0.2
    if tem_rs:
        # R$ tem peso alto para VALOR
        scores[TipoSecao.VALOR] += 0.5
    elif tem_valor_grande:
        # Valor grande sem R$ (ex: 1.800) - peso médio
        scores[TipoSecao.VALOR] += 0.3
    if tem_telefone:
        scores[TipoSecao.CONTATO] += 0.5

    # 4. Regras de desempate
    # Se tem R$ sem data pattern, priorizar VALOR
    if tem_rs and not tem_data_pattern:
        scores[TipoSecao.VALOR] += 0.2
    # Se tem telefone, priorizar CONTATO sobre DATA
    if tem_telefone and not tem_data_pattern:
        scores[TipoSecao.CONTATO] += 0.2

    # Determinar tipo com maior score
    tipo_max = max(scores, key=scores.get)
    score_max = scores[tipo_max]

    if score_max < 0.1:
        tipo_max = TipoSecao.DESCONHECIDO

    return LinhaParsed(texto=linha, tipo=tipo_max, indice=indice, confianca=min(score_max, 1.0))


def _agrupar_secoes(linhas: List[LinhaParsed]) -> MensagemParsed:
    """
    Agrupa linhas classificadas em seções.

    Linhas adjacentes do mesmo tipo são agrupadas.
    Linhas DESCONHECIDO são ignoradas.
    """
    secoes_local = []
    secoes_data = []
    secoes_valor = []
    secoes_contato = []
    secoes_especialidade = []

    for linha in linhas:
        texto = linha.texto.strip()
        if not texto:
            continue

        if linha.tipo == TipoSecao.LOCAL:
            secoes_local.append(texto)
        elif linha.tipo == TipoSecao.DATA:
            secoes_data.append(texto)
        elif linha.tipo == TipoSecao.VALOR:
            secoes_valor.append(texto)
        elif linha.tipo == TipoSecao.CONTATO:
            secoes_contato.append(texto)
        elif linha.tipo == TipoSecao.ESPECIALIDADE:
            secoes_especialidade.append(texto)
        # DESCONHECIDO é ignorado

    return MensagemParsed(
        texto_original="",
        linhas=linhas,
        secoes_local=secoes_local,
        secoes_data=secoes_data,
        secoes_valor=secoes_valor,
        secoes_contato=secoes_contato,
        secoes_especialidade=secoes_especialidade,
    )


def parsear_mensagem(texto: str) -> MensagemParsed:
    """
    Função principal: parseia uma mensagem de grupo.

    Args:
        texto: Texto bruto da mensagem

    Returns:
        MensagemParsed com seções identificadas

    Example:
        >>> msg = parsear_mensagem("📍 Hospital ABC\\n🗓 26/01 - Manhã")
        >>> msg.tem_local
        True
        >>> msg.secoes_local
        ["📍 Hospital ABC"]
    """
    if not texto or not texto.strip():
        return MensagemParsed(texto_original=texto or "")

    # Separar em linhas
    linhas = texto.split("\n")

    # Classificar cada linha
    linhas_parsed = [_classificar_linha(linha, i) for i, linha in enumerate(linhas)]

    # Agrupar em seções
    resultado = _agrupar_secoes(linhas_parsed)
    resultado.texto_original = texto

    logger.debug(
        f"Parsed mensagem: {len(resultado.secoes_local)} local, "
        f"{len(resultado.secoes_data)} datas, "
        f"{len(resultado.secoes_valor)} valores, "
        f"{len(resultado.secoes_contato)} contato"
    )

    return resultado
