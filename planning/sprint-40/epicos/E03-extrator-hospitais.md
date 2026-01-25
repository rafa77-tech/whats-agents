# E03 - Extrator de Hospitais

**Épico:** E03
**Nome:** Extrator de Hospitais
**Dependências:** E01, E02
**Prioridade:** Alta (crítico)

---

## Objetivo

Extrair informações de hospitais/locais das seções identificadas pelo parser. Cada hospital deve ser extraído como um objeto `HospitalExtraido` com nome, endereço e localização.

---

## Contexto

As seções de LOCAL identificadas pelo parser podem conter:

1. **Nome do hospital:** "Hospital Campo Limpo", "UPA Central", "PS São Luiz"
2. **Endereço:** "Estrada Itapecirica, 1661", "Av. Brasil, 1000 - Centro"
3. **Cidade/Estado:** "São Paulo - SP", "ABC", "Grande SP"

Um mesmo texto pode ter múltiplos hospitais (mensagens de "pool" de vagas).

---

## Entregáveis

### 1. Arquivo: `extrator_hospitais.py`

```python
"""
Extrator de hospitais/locais de mensagens de grupos.

Extrai nome, endereço e localização de cada hospital mencionado.
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
    "hospital", "hosp", "hosp.", "h.",
    "clínica", "clinica", "clin", "clin.",
    "upa", "u.p.a.",
    "ama", "a.m.a.",
    "ubs", "u.b.s.",
    "caps", "c.a.p.s.",
    "ps ", "p.s.", "pronto socorro", "pronto-socorro",
    "pa ", "p.a.", "pronto atendimento", "pronto-atendimento",
    "santa casa",
    "beneficência", "beneficencia",
    "maternidade", "mat.",
    "instituto", "inst.",
    "centro médico", "centro medico",
]

# Prefixos que indicam endereço
PREFIXOS_ENDERECO = [
    "rua", "r.",
    "avenida", "av.", "av ",
    "alameda", "al.",
    "estrada", "estr.",
    "rodovia", "rod.",
    "travessa", "tv.",
    "praça", "praca", "pç.",
    "largo",
]

# Estados brasileiros
ESTADOS_BR = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
}

# Regiões comuns em mensagens de SP
REGIOES_SP = {
    "abc", "abcd", "grande abc",
    "zona norte", "zn", "z. norte",
    "zona sul", "zs", "z. sul",
    "zona leste", "zl", "z. leste",
    "zona oeste", "zo", "z. oeste",
    "centro",
    "guarulhos", "osasco", "santo andré", "são bernardo",
    "são caetano", "diadema", "mauá", "maua",
}

# Regex para CEP
PATTERN_CEP = re.compile(r'\d{5}-?\d{3}')

# Regex para número de endereço
PATTERN_NUMERO = re.compile(r',?\s*n?[º°]?\s*(\d+)')


def _limpar_texto(texto: str) -> str:
    """Remove emojis e caracteres especiais extras."""
    # Remove emojis comuns
    texto = re.sub(r'[📍🏥🏨🏢📌🗺️]', '', texto)
    # Remove asteriscos de negrito WhatsApp
    texto = texto.replace('*', '')
    # Remove espaços extras
    texto = ' '.join(texto.split())
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

    # Verificar regiões conhecidas de SP
    for regiao in REGIOES_SP:
        if regiao in texto_lower:
            return regiao.title()

    # Se tem estado, tentar extrair cidade antes dele
    if estado:
        pattern = rf'([^,\-]+)\s*[-–]\s*{estado}'
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
            match = re.match(r'^([^,.\n]+)', resto)
            if match:
                nome = match.group(1).strip()
                # Remover número de endereço se presente
                nome = PATTERN_NUMERO.sub('', nome).strip()
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
    hospital_atual = None
    endereco_atual = None

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
                nome=nome,
                cidade=cidade,
                estado=estado,
                confianca=confianca
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

        # Linha ambígua - pode ser nome de hospital sem prefixo
        else:
            # Se não tem hospital atual, pode ser nome
            if not hospital_atual:
                hospital_atual = HospitalExtraido(
                    nome=linha_limpa,
                    confianca=0.6
                )
            # Se tem hospital e endereço pendente, aplicar
            elif endereco_atual:
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
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_extrator_hospitais.py`

```python
"""Testes para extrator de hospitais."""
import pytest

from app.services.grupos.extrator_v2.extrator_hospitais import (
    extrair_hospitais,
    _extrair_nome_hospital,
    _eh_linha_hospital,
    _eh_linha_endereco,
    _extrair_estado,
    _extrair_cidade,
)
from app.services.grupos.extrator_v2.types import HospitalExtraido


class TestHelperFunctions:
    """Testes para funções auxiliares."""

    def test_eh_linha_hospital_com_prefixo(self):
        """Detecta linhas com prefixo de hospital."""
        assert _eh_linha_hospital("Hospital São Luiz") is True
        assert _eh_linha_hospital("UPA Campo Limpo") is True
        assert _eh_linha_hospital("Clínica Santa Maria") is True
        assert _eh_linha_hospital("PS Central") is True

    def test_eh_linha_hospital_sem_prefixo(self):
        """Não detecta linhas sem prefixo."""
        assert _eh_linha_hospital("Av. Brasil, 1000") is False
        assert _eh_linha_hospital("São Paulo - SP") is False

    def test_eh_linha_endereco_com_prefixo(self):
        """Detecta linhas de endereço."""
        assert _eh_linha_endereco("Rua das Flores, 100") is True
        assert _eh_linha_endereco("Av. Brasil, 1000") is True
        assert _eh_linha_endereco("Estrada Itapecirica, 1661") is True

    def test_eh_linha_endereco_com_numero(self):
        """Detecta endereço pelo número."""
        assert _eh_linha_endereco("Campo Limpo, 1661") is True
        assert _eh_linha_endereco("Centro, nº 500") is True

    def test_extrair_estado(self):
        """Extrai sigla do estado."""
        assert _extrair_estado("São Paulo - SP") == "SP"
        assert _extrair_estado("Centro - RJ") == "RJ"
        assert _extrair_estado("Hospital ABC") is None

    def test_extrair_cidade_regiao_sp(self):
        """Extrai regiões de SP."""
        assert _extrair_cidade("Zona Norte") == "Zona Norte"
        assert _extrair_cidade("ABC") == "Abc"
        assert _extrair_cidade("Grande ABC") == "Grande Abc"

    def test_extrair_nome_hospital(self):
        """Extrai nome do hospital."""
        nome, conf = _extrair_nome_hospital("Hospital São Luiz ABC")
        assert nome == "Hospital São Luiz ABC"
        assert conf >= 0.8

    def test_extrair_nome_hospital_com_emoji(self):
        """Extrai nome removendo emoji."""
        nome, conf = _extrair_nome_hospital("📍 Hospital Campo Limpo")
        assert nome == "Hospital Campo Limpo"
        assert "📍" not in nome


class TestExtrairHospitais:
    """Testes para extração de hospitais."""

    def test_hospital_simples(self):
        """Extrai hospital simples."""
        linhas = ["Hospital São Luiz ABC"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "São Luiz" in hospitais[0].nome

    def test_hospital_com_endereco(self):
        """Extrai hospital com endereço."""
        linhas = [
            "📍 Hospital Campo Limpo",
            "Estrada Itapecirica, 1661 - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Campo Limpo" in hospitais[0].nome
        assert hospitais[0].endereco is not None
        assert "Itapecirica" in hospitais[0].endereco

    def test_hospital_com_estado(self):
        """Extrai estado do hospital."""
        linhas = [
            "Hospital Central",
            "Centro - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert hospitais[0].estado == "SP"

    def test_multiplos_hospitais(self):
        """Extrai múltiplos hospitais."""
        linhas = [
            "📍 Hospital ABC",
            "📍 Hospital XYZ",
            "📍 UPA Central"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 3

    def test_hospital_com_cidade(self):
        """Extrai cidade do hospital."""
        linhas = [
            "Hospital Regional",
            "Santo André - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        # Pode extrair cidade ou incluir no endereço

    def test_linhas_vazias_ignoradas(self):
        """Linhas vazias são ignoradas."""
        linhas = [
            "Hospital ABC",
            "",
            "   ",
            "Rua Central, 100"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1

    def test_lista_vazia(self):
        """Lista vazia retorna lista vazia."""
        hospitais = extrair_hospitais([])
        assert hospitais == []

    def test_confianca_com_prefixo(self):
        """Confiança maior quando tem prefixo claro."""
        linhas = ["Hospital São Luiz"]
        hospitais = extrair_hospitais(linhas)

        assert hospitais[0].confianca >= 0.8

    def test_confianca_sem_prefixo(self):
        """Confiança menor sem prefixo claro."""
        linhas = ["São Luiz ABC"]
        hospitais = extrair_hospitais(linhas)

        assert hospitais[0].confianca < 0.8


class TestCasosReais:
    """Testes com formatos reais de grupos."""

    def test_formato_emoji_padrao(self):
        """Formato padrão com emoji."""
        linhas = [
            "📍 Hospital Campo Limpo",
            "Estrada Itapecirica da Serra, 1661 - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Campo Limpo" in hospitais[0].nome

    def test_formato_upa(self):
        """Formato UPA."""
        linhas = ["UPA CAMPO LIMPO"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "UPA" in hospitais[0].nome.upper()

    def test_formato_ps(self):
        """Formato PS (Pronto Socorro)."""
        linhas = ["PS Central - Guarulhos"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1

    def test_formato_santa_casa(self):
        """Formato Santa Casa."""
        linhas = ["Santa Casa de Misericórdia - ABC"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Santa Casa" in hospitais[0].nome

    def test_formato_beneficencia(self):
        """Formato Beneficência."""
        linhas = ["Beneficência Portuguesa"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Beneficência" in hospitais[0].nome
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `extrator_hospitais.py`
- [ ] Implementar `extrair_hospitais()`
- [ ] Implementar funções auxiliares
- [ ] Adicionar exports em `__init__.py`

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar testes: `uv run pytest tests/services/grupos/extrator_v2/test_extrator_hospitais.py -v`
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros mypy
- [ ] Zero erros ruff

---

## Definition of Done (E03)

Este épico está **COMPLETO** quando:

1. ✅ Extrai nome do hospital corretamente
2. ✅ Extrai endereço quando presente
3. ✅ Extrai cidade/estado quando presente
4. ✅ Suporta múltiplos hospitais por mensagem
5. ✅ Ignora linhas vazias/inválidas
6. ✅ Retorna confiança adequada
7. ✅ 100% dos testes passando
8. ✅ Zero erros mypy/ruff
