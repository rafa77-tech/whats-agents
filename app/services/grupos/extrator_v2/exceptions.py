"""
Exceções customizadas para o extrator de vagas v2.

Sprint 40 - E01: Estrutura e Tipos
"""


class ExtracaoError(Exception):
    """Erro base para extração."""

    pass


class MensagemVaziaError(ExtracaoError):
    """Mensagem está vazia ou só tem caracteres especiais."""

    pass


class SemHospitalError(ExtracaoError):
    """Não foi possível identificar nenhum hospital."""

    pass


class SemDataError(ExtracaoError):
    """Não foi possível identificar nenhuma data."""

    pass


class LLMTimeoutError(ExtracaoError):
    """Timeout na chamada ao LLM."""

    pass


class LLMRateLimitError(ExtracaoError):
    """Rate limit atingido no LLM."""

    pass


class JSONParseError(ExtracaoError):
    """Erro ao parsear JSON do LLM."""

    pass
