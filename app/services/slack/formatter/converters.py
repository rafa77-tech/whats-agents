"""
Conversores de dados para exibicao no Slack.

Funcoes para formatacao de telefones, datas, valores, etc.
Sprint 10 - S10.E2.1
"""
import re
from datetime import datetime, date
from typing import Union

from .primitives import code


def formatar_telefone(telefone: str) -> str:
    """
    Formata telefone para exibicao.

    Args:
        telefone: Numero com ou sem formatacao

    Returns:
        Telefone formatado como codigo: `11 99999-9999`
    """
    tel_limpo = re.sub(r'\D', '', telefone)
    if len(tel_limpo) >= 11:
        return f"`{tel_limpo[:2]} {tel_limpo[2:7]}-{tel_limpo[7:]}`"
    elif len(tel_limpo) >= 8:
        return f"`{tel_limpo}`"
    return code(telefone)


def formatar_valor(valor: Union[float, int]) -> str:
    """
    Formata valor monetario.

    Args:
        valor: Valor numerico

    Returns:
        Valor formatado: R$ 2.500
    """
    if valor >= 1000:
        return f"R$ {valor:,.0f}".replace(",", ".")
    return f"R$ {valor:.0f}"


def formatar_porcentagem(valor: float) -> str:
    """
    Formata porcentagem.

    Args:
        valor: Valor numerico (ex: 25.5)

    Returns:
        Porcentagem formatada: 25.5% ou 25%
    """
    if valor == int(valor):
        return f"{int(valor)}%"
    return f"{valor:.1f}%"


def formatar_data(data: Union[str, datetime, date]) -> str:
    """
    Formata data para exibicao.

    Args:
        data: Data em varios formatos

    Returns:
        Data formatada: dd/mm
    """
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            return data

    return data.strftime("%d/%m")


def formatar_data_hora(data: Union[str, datetime]) -> str:
    """
    Formata data e hora para exibicao.

    Args:
        data: Data em varios formatos

    Returns:
        Data e hora formatadas: dd/mm HH:MM
    """
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            return data

    return data.strftime("%d/%m %H:%M")


def formatar_data_longa(data: Union[str, datetime, date]) -> str:
    """
    Formata data em formato longo.

    Args:
        data: Data em varios formatos

    Returns:
        Data formatada: 15 de dezembro
    """
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            return data

    meses = [
        "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    return f"{data.day} de {meses[data.month - 1]}"
