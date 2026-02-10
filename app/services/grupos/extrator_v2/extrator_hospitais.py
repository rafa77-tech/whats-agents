"""
Extrator de hospitais/locais de mensagens de grupos.

Extrai nome, endereço e localização de cada hospital mencionado.

Sprint 40 - E03: Extrator de Hospitais
"""

import re
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import HospitalExtraido

logger = get_logger(__name__)


# =============================================================================
# Padrões e Keywords
# =============================================================================

# Prefixos que indicam nome de hospital
PREFIXOS_HOSPITAL = [
    "hospital",
    "hosp",
    "hosp.",
    "h.",
    "clínica",
    "clinica",
    "clin",
    "clin.",
    "upa",
    "u.p.a.",
    "ama",
    "a.m.a.",
    "ubs",
    "u.b.s.",
    "caps",
    "c.a.p.s.",
    "ps ",
    "p.s.",
    "pronto socorro",
    "pronto-socorro",
    "pa ",
    "p.a.",
    "pronto atendimento",
    "pronto-atendimento",
    "santa casa",
    "beneficência",
    "beneficencia",
    "maternidade",
    "mat.",
    "instituto",
    "inst.",
    "centro médico",
    "centro medico",
]

# Prefixos que indicam endereço
PREFIXOS_ENDERECO = [
    "rua",
    "r.",
    "avenida",
    "av.",
    "av ",
    "alameda",
    "al.",
    "estrada",
    "estr.",
    "rodovia",
    "rod.",
    "travessa",
    "tv.",
    "praça",
    "praca",
    "pç.",
    "largo",
]

# Estados brasileiros
ESTADOS_BR = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}

# Regiões comuns em mensagens de SP
REGIOES_SP = {
    "abc",
    "abcd",
    "grande abc",
    "zona norte",
    "zn",
    "z. norte",
    "zona sul",
    "zs",
    "z. sul",
    "zona leste",
    "zl",
    "z. leste",
    "zona oeste",
    "zo",
    "z. oeste",
    "centro",
    "guarulhos",
    "osasco",
    "santo andré",
    "são bernardo",
    "são caetano",
    "diadema",
    "mauá",
    "maua",
}

# Regex para CEP
PATTERN_CEP = re.compile(r"\d{5}-?\d{3}")

# Regex para número de endereço
PATTERN_NUMERO = re.compile(r",?\s*n?[º°]?\s*(\d+)")


def _limpar_texto(texto: str) -> str:
    """Remove emojis e caracteres especiais extras."""
    # Remove emojis comuns
    texto = re.sub(r"[📍🏥🏨🏢📌🗺️🗺]", "", texto)
    # Remove asteriscos de negrito WhatsApp
    texto = texto.replace("*", "")
    # Remove espaços extras
    texto = " ".join(texto.split())
    return texto.strip()


def _extrair_estado(texto: str) -> Optional[str]:
    """Extrai sigla do estado se presente."""
    texto_upper = texto.upper()
    for estado in ESTADOS_BR:
        # Verifica se estado está no final ou separado por hífen/traço
        if texto_upper.endswith(f" {estado}") or texto_upper.endswith(f"-{estado}"):
            return estado
        if f" {estado} " in texto_upper or texto_upper.startswith(f"{estado} "):
            return estado
    return None


def _extrair_cidade(texto: str, estado: Optional[str] = None) -> Optional[str]:
    """Tenta extrair cidade do texto."""
    texto_lower = texto.lower()

    # Verificar regiões conhecidas de SP (ordenar por tamanho desc para priorizar matches mais longos)
    for regiao in sorted(REGIOES_SP, key=len, reverse=True):
        if regiao in texto_lower:
            return regiao.title()

    # Se tem estado, tentar extrair cidade antes dele
    if estado:
        pattern = rf"([^,\-]+)\s*[-–]\s*{estado}"
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            cidade = match.group(1).strip()
            # Limpar prefixos de endereço
            for pref in PREFIXOS_ENDERECO:
                if cidade.lower().startswith(pref):
                    return None  # É endereço, não cidade
            return cidade

    return None


def _eh_linha_endereco(texto: str) -> bool:
    """Verifica se linha é provavelmente um endereço."""
    texto_lower = texto.lower()
    for prefixo in PREFIXOS_ENDERECO:
        if texto_lower.startswith(prefixo):
            return True
    # Tem número de endereço
    if PATTERN_NUMERO.search(texto):
        return True
    # Tem CEP
    if PATTERN_CEP.search(texto):
        return True
    return False


def _eh_linha_hospital(texto: str) -> bool:
    """Verifica se linha contém nome de hospital."""
    texto_lower = texto.lower()
    for prefixo in PREFIXOS_HOSPITAL:
        if prefixo in texto_lower:
            return True
    return False


def _extrair_nome_hospital(texto: str) -> Tuple[str, float]:
    """
    Extrai nome do hospital de uma linha.

    Returns:
        Tupla (nome, confiança)
    """
    texto_limpo = _limpar_texto(texto)
    texto_lower = texto_limpo.lower()

    # Encontrar prefixo de hospital
    for prefixo in PREFIXOS_HOSPITAL:
        if prefixo in texto_lower:
            # Extrair nome completo até pontuação ou quebra
            idx = texto_lower.find(prefixo)
            resto = texto_limpo[idx:]

            # Pegar até vírgula, ponto ou fim
            match = re.match(r"^([^,.\n]+)", resto)
            if match:
                nome = match.group(1).strip()
                # Remover número de endereço se presente
                nome = PATTERN_NUMERO.sub("", nome).strip()
                return nome, 0.9

    # Fallback: usar linha inteira se não tem indicador claro
    return texto_limpo, 0.5


def extrair_hospitais(linhas_local: List[str]) -> List[HospitalExtraido]:
    """
    Extrai hospitais das linhas de seção LOCAL.

    Args:
        linhas_local: Lista de linhas classificadas como LOCAL pelo parser

    Returns:
        Lista de HospitalExtraido

    Example:
        >>> linhas = ["📍 Hospital Campo Limpo", "Estrada Itapecirica, 1661 - SP"]
        >>> hospitais = extrair_hospitais(linhas)
        >>> len(hospitais)
        1
        >>> hospitais[0].nome
        "Hospital Campo Limpo"
    """
    if not linhas_local:
        return []

    hospitais = []
    hospital_atual: Optional[HospitalExtraido] = None
    endereco_atual: Optional[str] = None

    for linha in linhas_local:
        linha_limpa = _limpar_texto(linha)

        if not linha_limpa:
            continue

        # Verificar se é nome de hospital
        if _eh_linha_hospital(linha):
            # Se já tem hospital pendente, salvar
            if hospital_atual:
                hospitais.append(hospital_atual)

            nome, confianca = _extrair_nome_hospital(linha)
            estado = _extrair_estado(linha)
            cidade = _extrair_cidade(linha, estado)

            hospital_atual = HospitalExtraido(
                nome=nome, cidade=cidade, estado=estado, confianca=confianca
            )
            endereco_atual = None

        # Verificar se é endereço
        elif _eh_linha_endereco(linha):
            if hospital_atual:
                # Adicionar endereço ao hospital atual
                hospital_atual.endereco = linha_limpa
                estado = _extrair_estado(linha)
                if estado:
                    hospital_atual.estado = estado
                cidade = _extrair_cidade(linha, estado)
                if cidade:
                    hospital_atual.cidade = cidade
            else:
                # Endereço sem hospital - guardar para próximo
                endereco_atual = linha_limpa

        # Linha ambígua - pode ser nome de hospital sem prefixo ou info adicional
        else:
            # Se não tem hospital atual, pode ser nome
            if not hospital_atual:
                hospital_atual = HospitalExtraido(nome=linha_limpa, confianca=0.6)
            else:
                # Tentar extrair estado/cidade de linhas adicionais
                estado = _extrair_estado(linha)
                if estado and not hospital_atual.estado:
                    hospital_atual.estado = estado
                cidade = _extrair_cidade(linha, estado)
                if cidade and not hospital_atual.cidade:
                    hospital_atual.cidade = cidade
                # Se tem endereço pendente, aplicar
                if endereco_atual:
                    hospital_atual.endereco = endereco_atual
                    endereco_atual = None

    # Salvar último hospital
    if hospital_atual:
        if endereco_atual:
            hospital_atual.endereco = endereco_atual
        hospitais.append(hospital_atual)

    logger.debug(f"Extraídos {len(hospitais)} hospitais")
    return hospitais


def extrair_hospitais_llm(texto: str) -> List[HospitalExtraido]:
    """
    Versão LLM para casos complexos.

    Usa Claude Haiku para extrair hospitais quando o parser regex falha.
    Deve ser chamado apenas como fallback.

    Args:
        texto: Texto completo da mensagem

    Returns:
        Lista de HospitalExtraido
    """
    # TODO: Implementar chamada LLM
    # Por enquanto retorna lista vazia
    logger.debug("LLM fallback não implementado ainda")
    return []
