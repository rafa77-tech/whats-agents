"""
Extrator de contato de mensagens de grupos.

Extrai nome e WhatsApp do responsável pela vaga.

Sprint 40 - E06: Extrator de Contato
"""

import re
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import ContatoExtraido

logger = get_logger(__name__)


# =============================================================================
# Padrões de Contato
# =============================================================================

# Link WhatsApp: wa.me/5511999999999
PATTERN_WAME = re.compile(r"wa\.me/(\d{10,15})", re.IGNORECASE)

# Link WhatsApp alternativo: api.whatsapp.com/send?phone=5511999999999
PATTERN_WA_API = re.compile(r"api\.whatsapp\.com/send\?phone=(\d{10,15})", re.IGNORECASE)

# Telefone brasileiro: (11) 99999-9999, 11999999999, +55 11 99999-9999
PATTERN_TELEFONE = re.compile(
    r"(?:\+?55\s?)?"  # DDI opcional
    r"(?:\(?\d{2}\)?\s?)?"  # DDD opcional
    r"(?:9\s?)?"  # 9 inicial opcional
    r"\d{4}[-.\s]?\d{4}"  # 8-9 dígitos
)

# Padrão para telefone com formato mais rígido
PATTERN_TELEFONE_COMPLETO = re.compile(
    r"(?:\+?55\s?)?"  # DDI opcional
    r"\(?(\d{2})\)?\s?"  # DDD
    r"(9?\d{4})[-.\s]?(\d{4})"  # Número
)

# Palavras que indicam nome antes do telefone
INDICADORES_NOME = [
    r"falar\s+com\s+",
    r"chamar\s+",
    r"ligar\s+para\s+",
    r"contato[:\s]+",
    r"interessados[:\s]+",
    r"informações[:\s]+",
    r"info[:\s]+",
]

# Padrão para nome antes de telefone: "Nome - 11999999999" ou "Nome: 11999"
PATTERN_NOME_TELEFONE = re.compile(
    r"([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)?)\s*[-:]\s*(?:wa\.me/|api\.whatsapp|(?:\+?55\s?)?\d)",
    re.UNICODE | re.IGNORECASE,
)

# Padrão para nome isolado em linha com emoji de contato
PATTERN_NOME_ISOLADO = re.compile(
    r"^[📲📞📱☎️🤙💬👤\s]*([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)\s*$", re.UNICODE
)


def _limpar_texto(texto: str) -> str:
    """Remove emojis e caracteres especiais."""
    texto = re.sub(r"[📲📞📱☎️🤙💬👤]", "", texto)
    texto = texto.replace("*", "")
    return " ".join(texto.split()).strip()


def _normalizar_telefone(telefone: str) -> str:
    """
    Normaliza telefone para formato internacional.

    Remove caracteres especiais e adiciona DDI 55 se necessário.

    Returns:
        Telefone normalizado: "5511999999999"
    """
    # Remover tudo exceto números
    numeros = re.sub(r"\D", "", telefone)

    # Adicionar DDI se não tiver
    if len(numeros) == 11:  # DDD + 9 dígitos
        numeros = "55" + numeros
    elif len(numeros) == 10:  # DDD + 8 dígitos (antigo)
        numeros = "55" + numeros
    elif len(numeros) == 9:  # Só celular
        numeros = "5511" + numeros  # Assume SP
    elif len(numeros) == 8:  # Só celular antigo
        numeros = "5511" + numeros

    return numeros


def _extrair_telefone(texto: str) -> Optional[Tuple[str, str]]:
    """
    Extrai telefone do texto.

    Returns:
        Tupla (telefone_normalizado, telefone_raw) ou None
    """
    # Tentar wa.me primeiro
    match = PATTERN_WAME.search(texto)
    if match:
        raw = f"wa.me/{match.group(1)}"
        normalizado = _normalizar_telefone(match.group(1))
        return normalizado, raw

    # Tentar API WhatsApp
    match = PATTERN_WA_API.search(texto)
    if match:
        raw = f"api.whatsapp.com/send?phone={match.group(1)}"
        normalizado = _normalizar_telefone(match.group(1))
        return normalizado, raw

    # Tentar telefone direto
    match = PATTERN_TELEFONE.search(texto)
    if match:
        raw = match.group(0)
        normalizado = _normalizar_telefone(raw)
        # Validar que parece telefone válido
        if len(normalizado) >= 12:  # DDI + DDD + número
            return normalizado, raw

    return None


def _extrair_nome(texto: str) -> Optional[str]:
    """
    Extrai nome do contato do texto.

    Returns:
        Nome ou None
    """
    texto_limpo = _limpar_texto(texto)

    # Tentar padrão "falar com Nome" (com negative lookahead para não capturar wa.me)
    for indicador in INDICADORES_NOME:
        # Nome: letra maiúscula + minúsculas, opcionalmente segundo nome
        # Não captura "wa" ou palavras que começam com número
        pattern = re.compile(
            indicador + r"([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)(?:\s|$|[:\-])",
            re.IGNORECASE | re.UNICODE,
        )
        match = pattern.search(texto_limpo)
        if match:
            nome = match.group(1).strip()
            # Validar que é nome razoável e não é parte de URL
            if 2 <= len(nome) <= 50 and nome.lower() not in ("wa", "api", "http", "https"):
                return nome

    # Tentar padrão "Nome - telefone" ou "Nome - wa.me"
    match = PATTERN_NOME_TELEFONE.search(texto_limpo)
    if match:
        nome = match.group(1).strip()
        if 2 <= len(nome) <= 50 and nome.lower() not in ("wa", "api"):
            return nome

    return None


def _extrair_nome_isolado(linha: str) -> Optional[str]:
    """
    Extrai nome de uma linha isolada (só nome, possivelmente com emoji).

    Ex: "📲 Eloisa" -> "Eloisa"
    """
    match = PATTERN_NOME_ISOLADO.match(linha.strip())
    if match:
        nome = match.group(1).strip()
        if 2 <= len(nome) <= 50:
            return nome
    return None


def extrair_contato(linhas_contato: List[str]) -> Optional[ContatoExtraido]:
    """
    Extrai contato das linhas de CONTATO.

    Args:
        linhas_contato: Linhas classificadas como CONTATO pelo parser

    Returns:
        ContatoExtraido ou None

    Example:
        >>> linhas = ["📲 Eloisa", "wa.me/5511939050162"]
        >>> contato = extrair_contato(linhas)
        >>> contato.nome
        "Eloisa"
        >>> contato.whatsapp
        "5511939050162"
    """
    if not linhas_contato:
        return None

    # Juntar todas as linhas para análise
    texto_completo = " ".join(linhas_contato)

    # Extrair telefone (obrigatório)
    resultado_telefone = _extrair_telefone(texto_completo)
    if not resultado_telefone:
        # Tentar linha por linha
        for linha in linhas_contato:
            resultado_telefone = _extrair_telefone(linha)
            if resultado_telefone:
                break

    if not resultado_telefone:
        logger.debug("Não encontrou telefone nas linhas de contato")
        return None

    telefone_normalizado, telefone_raw = resultado_telefone

    # Extrair nome (opcional)
    # Primeiro, tentar extrair nome isolado de linhas individuais (ex: "📲 Eloisa")
    nome = None
    for linha in linhas_contato:
        nome = _extrair_nome_isolado(linha)
        if nome:
            break

    # Se não achou nome isolado, tentar padrões mais complexos
    if not nome:
        nome = _extrair_nome(texto_completo)

    if not nome:
        # Tentar linha por linha
        for linha in linhas_contato:
            nome = _extrair_nome(linha)
            if nome:
                break

    # Calcular confiança
    confianca = 0.7
    if nome and telefone_normalizado:
        confianca = 0.95
    elif telefone_normalizado and len(telefone_normalizado) >= 13:
        confianca = 0.9

    contato = ContatoExtraido(
        nome=nome, whatsapp=telefone_normalizado, whatsapp_raw=telefone_raw, confianca=confianca
    )

    logger.debug(f"Contato extraído: {nome or 'sem nome'} - {telefone_normalizado}")
    return contato
