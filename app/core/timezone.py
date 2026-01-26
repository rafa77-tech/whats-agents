"""
Módulo centralizado para tratamento de timezone.

Sprint 40 - Padronização de fuso horário.

O projeto usa:
- UTC para armazenamento no banco de dados
- America/Sao_Paulo para lógica de negócio (horário comercial, schedules)

Convenções:
- `agora_utc()`: Para armazenar no banco
- `agora_brasilia()`: Para lógica de negócio (horário comercial, schedules de jobs)
- `para_brasilia(dt)`: Converter datetime para Brasília
- `para_utc(dt)`: Converter datetime para UTC
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# Constantes de timezone
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")
TZ_UTC = timezone.utc


def agora_utc() -> datetime:
    """
    Retorna datetime atual em UTC (timezone-aware).

    Use para:
    - Armazenar no banco de dados
    - Logs e timestamps
    - Comparações com dados do banco

    Returns:
        datetime em UTC com tzinfo
    """
    return datetime.now(TZ_UTC)


def agora_brasilia() -> datetime:
    """
    Retorna datetime atual no horário de Brasília (timezone-aware).

    Use para:
    - Verificar horário comercial
    - Schedules de jobs (cron expressions)
    - Lógica de negócio baseada em hora local
    - Exibição para usuários brasileiros

    Returns:
        datetime em America/Sao_Paulo com tzinfo
    """
    return datetime.now(TZ_BRASILIA)


def para_brasilia(dt: datetime) -> datetime:
    """
    Converte datetime para horário de Brasília.

    Args:
        dt: datetime a converter (pode ser naive ou aware)

    Returns:
        datetime em America/Sao_Paulo
    """
    if dt.tzinfo is None:
        # Assume que datetime naive está em UTC
        dt = dt.replace(tzinfo=TZ_UTC)
    return dt.astimezone(TZ_BRASILIA)


def para_utc(dt: datetime) -> datetime:
    """
    Converte datetime para UTC.

    Args:
        dt: datetime a converter (pode ser naive ou aware)

    Returns:
        datetime em UTC
    """
    if dt.tzinfo is None:
        # Assume que datetime naive está em Brasília
        dt = dt.replace(tzinfo=TZ_BRASILIA)
    return dt.astimezone(TZ_UTC)


def formatar_data_brasilia(dt: datetime, formato: str = "%d/%m/%Y %H:%M") -> str:
    """
    Formata datetime para exibição no formato brasileiro.

    Args:
        dt: datetime a formatar
        formato: formato strftime (padrão: "DD/MM/YYYY HH:MM")

    Returns:
        String formatada no horário de Brasília
    """
    return para_brasilia(dt).strftime(formato)


def hoje_brasilia() -> datetime:
    """
    Retorna o início do dia atual no horário de Brasília.

    Útil para filtros de "hoje" em queries.

    Returns:
        datetime às 00:00:00 de hoje em Brasília
    """
    agora = agora_brasilia()
    return agora.replace(hour=0, minute=0, second=0, microsecond=0)


def iso_utc(dt: datetime | None = None) -> str:
    """
    Retorna datetime em formato ISO 8601 UTC.

    Conveniente para inserir no banco de dados.

    Args:
        dt: datetime a formatar (padrão: agora)

    Returns:
        String ISO 8601 em UTC
    """
    if dt is None:
        dt = agora_utc()
    return para_utc(dt).isoformat()
