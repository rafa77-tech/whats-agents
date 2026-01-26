"""
Extrator de valores e regras de aplicação.

Extrai valores monetários e suas regras (seg-sex, sab-dom, etc).

Sprint 40 - E05: Extrator de Valores
"""

import re
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    GrupoDia,
    Periodo,
    RegraValor,
    ValoresExtraidos,
    DiaSemana,
)

logger = get_logger(__name__)


# =============================================================================
# Padrões de Valor
# =============================================================================

# Padrão de valor monetário: R$ 1.800 ou 1800 ou 1.800
PATTERN_VALOR = re.compile(
    r'R?\$?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
    re.IGNORECASE
)

# Padrões de grupo de dias (ordem importa - mais específicos primeiro)
PATTERNS_GRUPO_DIA = {
    GrupoDia.SAB_DOM: [
        r'sábado\s*(?:e|a|-)\s*domingo',
        r'sabado\s*(?:e|a|-)\s*domingo',
        r'sab[\s\-]*(?:e|a|-|dom)[\s\-]*dom',
        r'sab[\s\-/]*dom',
        r'fim\s+de\s+semana',
        r'fds',
    ],
    GrupoDia.SEG_SEX: [
        r'segunda\s*(?:a|à|-|ate|até)\s*sexta',
        r'seg[\s\-]*(?:a|à|-|ate|até)[\s\-]*sex',
        r'seg[\s\-/]*sex',
        r'dias\s+úteis',
        r'dias\s+uteis',
        r'durante\s+a\s+semana',
    ],
    GrupoDia.SAB: [
        r'sábado(?!\s*(?:e|a|-)\s*dom)',
        r'sabado(?!\s*(?:e|a|-)\s*dom)',
        r'sab(?!\s*[-/]?\s*dom)',
    ],
    GrupoDia.DOM: [
        r'domingo',
        r'\bdom\b',
    ],
    GrupoDia.FERIADO: [
        r'feriado',
        r'feriados',
    ],
}

# Padrões de período para valores
PATTERNS_PERIODO_VALOR = {
    Periodo.DIURNO: [r'diurno', r'\bsd\b', r's\.d\.'],
    Periodo.NOTURNO: [r'noturno', r'\bsn\b', r's\.n\.'],
    Periodo.MANHA: [r'manhã', r'manha', r'matutino'],
    Periodo.TARDE: [r'tarde', r'vespertino'],
    Periodo.NOITE: [r'noite'],
}

# Padrão de adicional: "+100", "+ R$ 100", "(dom +100)"
PATTERN_ADICIONAL = re.compile(
    r'\+\s*R?\$?\s*(\d+)',
    re.IGNORECASE
)


def _normalizar_valor(valor_str: str) -> Optional[int]:
    """
    Normaliza string de valor para inteiro.

    Args:
        valor_str: "1.800", "1800", "1,800.00"

    Returns:
        Valor como inteiro ou None
    """
    if not valor_str:
        return None

    # Remover tudo exceto números
    numeros = re.sub(r'[^\d]', '', valor_str)

    if not numeros:
        return None

    valor = int(numeros)

    # Se valor parece ter centavos (ex: 180000 de "1.800,00")
    # Detectar pelo padrão original se tem ,00 ou .00 no final
    tem_centavos = bool(re.search(r'[,.]00$', valor_str))
    if tem_centavos and valor > 10000:
        # Provavelmente tem centavos, dividir por 100
        valor = valor // 100

    # Validar range razoável (100 a 50000)
    if not (100 <= valor <= 50000):
        return None

    return valor


def _extrair_valores_linha(texto: str) -> List[int]:
    """Extrai todos os valores monetários de uma linha."""
    matches = PATTERN_VALOR.findall(texto)
    valores = []
    for match in matches:
        valor = _normalizar_valor(match)
        if valor:
            valores.append(valor)
    return valores


def _detectar_grupo_dia(texto: str) -> Optional[GrupoDia]:
    """Detecta grupo de dias no texto."""
    texto_lower = texto.lower()

    for grupo, patterns in PATTERNS_GRUPO_DIA.items():
        for pattern in patterns:
            if re.search(pattern, texto_lower):
                return grupo

    return None


def _detectar_periodo(texto: str) -> Optional[Periodo]:
    """Detecta período no texto."""
    texto_lower = texto.lower()

    for periodo, patterns in PATTERNS_PERIODO_VALOR.items():
        for pattern in patterns:
            if re.search(pattern, texto_lower):
                return periodo

    return None


def _detectar_adicional(texto: str) -> Optional[Tuple[int, GrupoDia]]:
    """
    Detecta padrão de adicional sobre valor base.

    Ex: "(dom +100)" retorna (100, GrupoDia.DOM)

    Returns:
        Tupla (valor_adicional, grupo_dia) ou None
    """
    match = PATTERN_ADICIONAL.search(texto)
    if not match:
        return None

    adicional = int(match.group(1))
    grupo = _detectar_grupo_dia(texto)

    if grupo:
        return adicional, grupo

    return None


def _parsear_linha_valor(linha: str) -> List[RegraValor]:
    """
    Parseia uma linha e extrai regras de valor.

    Returns:
        Lista de RegraValor encontradas na linha
    """
    regras = []
    valores = _extrair_valores_linha(linha)

    if not valores:
        return []

    grupo_dia = _detectar_grupo_dia(linha)
    periodo = _detectar_periodo(linha)

    # Se tem grupo específico ou período, criar regra específica
    if grupo_dia or periodo:
        regras.append(RegraValor(
            grupo_dia=grupo_dia or GrupoDia.TODOS,
            periodo=periodo,
            valor=valores[0],
            confianca=0.9 if grupo_dia else 0.7
        ))
    else:
        # Valor geral
        regras.append(RegraValor(
            grupo_dia=GrupoDia.TODOS,
            periodo=None,
            valor=valores[0],
            confianca=0.8
        ))

    return regras


def _consolidar_regras(regras: List[RegraValor]) -> ValoresExtraidos:
    """
    Consolida lista de regras em ValoresExtraidos.

    Remove duplicatas e determina se é valor único.
    """
    if not regras:
        return ValoresExtraidos()

    # Se todas as regras têm mesmo valor e grupo TODOS
    valores_unicos = set(r.valor for r in regras)
    grupos_unicos = set(r.grupo_dia for r in regras)

    if len(valores_unicos) == 1 and grupos_unicos == {GrupoDia.TODOS}:
        return ValoresExtraidos(valor_unico=regras[0].valor)

    # Remover duplicatas mantendo maior confiança
    regras_por_chave = {}
    for regra in regras:
        chave = (regra.grupo_dia, regra.periodo)
        if chave not in regras_por_chave or regra.confianca > regras_por_chave[chave].confianca:
            regras_por_chave[chave] = regra

    return ValoresExtraidos(regras=list(regras_por_chave.values()))


def extrair_valores(linhas_valor: List[str]) -> ValoresExtraidos:
    """
    Extrai valores e regras das linhas de VALOR.

    Args:
        linhas_valor: Linhas classificadas como VALOR pelo parser

    Returns:
        ValoresExtraidos com regras

    Example:
        >>> linhas = ["Segunda a Sexta: R$ 1.700", "Sábado e Domingo: R$ 1.800"]
        >>> valores = extrair_valores(linhas)
        >>> len(valores.regras)
        2
    """
    todas_regras = []

    for linha in linhas_valor:
        regras = _parsear_linha_valor(linha)
        todas_regras.extend(regras)

    resultado = _consolidar_regras(todas_regras)

    logger.debug(
        f"Extraídos {len(resultado.regras)} regras de valor, "
        f"valor_unico={resultado.valor_unico}"
    )

    return resultado


def obter_valor_para_dia(
    valores: ValoresExtraidos,
    dia_semana: DiaSemana,
    periodo: Optional[Periodo] = None
) -> Optional[int]:
    """
    Obtém o valor correto para um dia e período específicos.

    Esta é a função chave que associa o valor correto à vaga.

    Args:
        valores: ValoresExtraidos com regras
        dia_semana: Dia da semana da vaga
        periodo: Período da vaga (opcional)

    Returns:
        Valor em reais ou None

    Example:
        >>> valores = ValoresExtraidos(regras=[
        ...     RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
        ...     RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ... ])
        >>> obter_valor_para_dia(valores, DiaSemana.SEGUNDA)
        1700
        >>> obter_valor_para_dia(valores, DiaSemana.SABADO)
        1800
    """
    # Se tem valor único, retornar direto
    if valores.valor_unico:
        return valores.valor_unico

    if not valores.regras:
        return None

    # Mapear dia da semana para grupo
    dias_seg_sex = {DiaSemana.SEGUNDA, DiaSemana.TERCA, DiaSemana.QUARTA,
                    DiaSemana.QUINTA, DiaSemana.SEXTA}
    dias_sab_dom = {DiaSemana.SABADO, DiaSemana.DOMINGO}

    # Encontrar regra mais específica
    melhor_regra = None
    melhor_especificidade = -1

    for regra in valores.regras:
        especificidade = 0

        # Verificar se grupo de dia se aplica
        grupo_aplicavel = False

        if regra.grupo_dia == GrupoDia.TODOS:
            grupo_aplicavel = True
        elif regra.grupo_dia == GrupoDia.SEG_SEX and dia_semana in dias_seg_sex:
            grupo_aplicavel = True
            especificidade += 2
        elif regra.grupo_dia == GrupoDia.SAB_DOM and dia_semana in dias_sab_dom:
            grupo_aplicavel = True
            especificidade += 2
        elif regra.grupo_dia == GrupoDia.SAB and dia_semana == DiaSemana.SABADO:
            grupo_aplicavel = True
            especificidade += 3  # Mais específico que SAB_DOM
        elif regra.grupo_dia == GrupoDia.DOM and dia_semana == DiaSemana.DOMINGO:
            grupo_aplicavel = True
            especificidade += 3

        if not grupo_aplicavel:
            continue

        # Verificar período
        if regra.periodo and periodo:
            if regra.periodo == periodo:
                especificidade += 2
            else:
                continue  # Período não bate

        if especificidade > melhor_especificidade:
            melhor_especificidade = especificidade
            melhor_regra = regra

    return melhor_regra.valor if melhor_regra else None
