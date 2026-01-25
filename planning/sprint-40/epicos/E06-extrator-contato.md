# E06 - Extrator de Contato

**Épico:** E06
**Nome:** Extrator de Contato
**Dependências:** E01, E02
**Prioridade:** Média

---

## Objetivo

Extrair informações de contato (nome e WhatsApp) das seções de CONTATO identificadas pelo parser.

---

## Contexto

Mensagens de grupos têm diversos formatos de contato:

1. **Link WhatsApp:** `wa.me/5511999999999`
2. **Telefone direto:** `11 99999-9999`, `(11) 99999-9999`
3. **Nome + telefone:** `Eloisa - 11999999999`
4. **Formato completo:** `📲 Interessados falar com Eloisa: wa.me/5511999999999`

---

## Entregáveis

### 1. Arquivo: `extrator_contato.py`

```python
"""
Extrator de contato de mensagens de grupos.

Extrai nome e WhatsApp do responsável pela vaga.
"""

import re
from typing import Optional, Tuple

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import ContatoExtraido

logger = get_logger(__name__)


# =============================================================================
# Padrões de Contato
# =============================================================================

# Link WhatsApp: wa.me/5511999999999
PATTERN_WAME = re.compile(
    r'wa\.me/(\d{10,15})',
    re.IGNORECASE
)

# Link WhatsApp alternativo: api.whatsapp.com/send?phone=5511999999999
PATTERN_WA_API = re.compile(
    r'api\.whatsapp\.com/send\?phone=(\d{10,15})',
    re.IGNORECASE
)

# Telefone brasileiro: (11) 99999-9999, 11999999999, +55 11 99999-9999
PATTERN_TELEFONE = re.compile(
    r'(?:\+?55\s?)?'           # DDI opcional
    r'(?:\(?\d{2}\)?\s?)?'     # DDD opcional
    r'(?:9\s?)?'               # 9 inicial opcional
    r'\d{4}[-.\s]?\d{4}'       # 8-9 dígitos
)

# Padrão para telefone com formato mais rígido
PATTERN_TELEFONE_COMPLETO = re.compile(
    r'(?:\+?55\s?)?'           # DDI opcional
    r'\(?(\d{2})\)?\s?'        # DDD
    r'(9?\d{4})[-.\s]?(\d{4})' # Número
)

# Palavras que indicam nome antes do telefone
INDICADORES_NOME = [
    r'falar\s+com\s+',
    r'chamar\s+',
    r'ligar\s+para\s+',
    r'contato[:\s]+',
    r'interessados[:\s]+',
    r'informações[:\s]+',
    r'info[:\s]+',
]

# Padrão para nome antes de telefone: "Nome - 11999999999" ou "Nome: 11999"
PATTERN_NOME_TELEFONE = re.compile(
    r'([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)?)\s*[-:]\s*(?:\+?55\s?)?\d',
    re.UNICODE
)


def _limpar_texto(texto: str) -> str:
    """Remove emojis e caracteres especiais."""
    texto = re.sub(r'[📲📞📱☎️🤙💬👤]', '', texto)
    texto = texto.replace('*', '')
    return ' '.join(texto.split()).strip()


def _normalizar_telefone(telefone: str) -> str:
    """
    Normaliza telefone para formato internacional.

    Remove caracteres especiais e adiciona DDI 55 se necessário.

    Returns:
        Telefone normalizado: "5511999999999"
    """
    # Remover tudo exceto números
    numeros = re.sub(r'\D', '', telefone)

    # Adicionar DDI se não tiver
    if len(numeros) == 11:  # DDD + 9 dígitos
        numeros = '55' + numeros
    elif len(numeros) == 10:  # DDD + 8 dígitos (antigo)
        numeros = '55' + numeros
    elif len(numeros) == 9:  # Só celular
        numeros = '5511' + numeros  # Assume SP
    elif len(numeros) == 8:  # Só celular antigo
        numeros = '5511' + numeros

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

    # Tentar padrão "falar com Nome"
    for indicador in INDICADORES_NOME:
        pattern = re.compile(
            indicador + r'([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]+)?)',
            re.IGNORECASE | re.UNICODE
        )
        match = pattern.search(texto_limpo)
        if match:
            nome = match.group(1).strip()
            # Validar que é nome razoável
            if 2 <= len(nome) <= 50:
                return nome

    # Tentar padrão "Nome - telefone"
    match = PATTERN_NOME_TELEFONE.search(texto_limpo)
    if match:
        nome = match.group(1).strip()
        if 2 <= len(nome) <= 50:
            return nome

    return None


def extrair_contato(linhas_contato: list[str]) -> Optional[ContatoExtraido]:
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
    texto_completo = ' '.join(linhas_contato)

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
        nome=nome,
        whatsapp=telefone_normalizado,
        whatsapp_raw=telefone_raw,
        confianca=confianca
    )

    logger.debug(f"Contato extraído: {nome or 'sem nome'} - {telefone_normalizado}")
    return contato
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_extrator_contato.py`

```python
"""Testes para extrator de contato."""
import pytest

from app.services.grupos.extrator_v2.extrator_contato import (
    extrair_contato,
    _normalizar_telefone,
    _extrair_telefone,
    _extrair_nome,
)


class TestNormalizarTelefone:
    """Testes para normalização de telefone."""

    def test_telefone_completo(self):
        """Telefone já com DDI."""
        assert _normalizar_telefone("5511999999999") == "5511999999999"

    def test_telefone_sem_ddi(self):
        """Telefone sem DDI."""
        assert _normalizar_telefone("11999999999") == "5511999999999"

    def test_telefone_com_formatacao(self):
        """Telefone formatado."""
        assert _normalizar_telefone("(11) 99999-9999") == "5511999999999"
        assert _normalizar_telefone("+55 11 99999-9999") == "5511999999999"

    def test_telefone_curto(self):
        """Telefone só com número."""
        assert _normalizar_telefone("999999999").startswith("5511")


class TestExtrairTelefone:
    """Testes para extração de telefone."""

    def test_wame(self):
        """Link wa.me."""
        tel, raw = _extrair_telefone("wa.me/5511939050162")
        assert tel == "5511939050162"
        assert "wa.me" in raw

    def test_telefone_direto(self):
        """Telefone direto no texto."""
        tel, raw = _extrair_telefone("Ligar: 11999999999")
        assert tel == "5511999999999"

    def test_telefone_formatado(self):
        """Telefone formatado."""
        tel, raw = _extrair_telefone("(11) 99999-9999")
        assert tel == "5511999999999"

    def test_sem_telefone(self):
        """Texto sem telefone."""
        resultado = _extrair_telefone("Interessados mandar mensagem")
        assert resultado is None


class TestExtrairNome:
    """Testes para extração de nome."""

    def test_falar_com(self):
        """Padrão 'falar com Nome'."""
        nome = _extrair_nome("Interessados falar com Eloisa")
        assert nome == "Eloisa"

    def test_contato(self):
        """Padrão 'contato: Nome'."""
        nome = _extrair_nome("Contato: Maria")
        assert nome == "Maria"

    def test_nome_telefone(self):
        """Padrão 'Nome - telefone'."""
        nome = _extrair_nome("João - 11999999999")
        assert nome == "João"

    def test_nome_composto(self):
        """Nome composto."""
        nome = _extrair_nome("Falar com Maria Silva")
        assert nome == "Maria Silva"

    def test_sem_nome(self):
        """Texto sem nome."""
        nome = _extrair_nome("11999999999")
        assert nome is None


class TestExtrairContato:
    """Testes para extração completa de contato."""

    def test_contato_completo(self):
        """Extrai contato com nome e telefone."""
        linhas = [
            "📲 Interessados falar com Eloisa",
            "wa.me/5511939050162"
        ]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"
        assert contato.whatsapp == "5511939050162"
        assert contato.confianca >= 0.9

    def test_contato_so_telefone(self):
        """Extrai apenas telefone."""
        linhas = ["📲 11999999999"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.whatsapp == "5511999999999"
        assert contato.nome is None

    def test_contato_em_uma_linha(self):
        """Contato em uma única linha."""
        linhas = ["Eloisa - wa.me/5511939050162"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"
        assert contato.whatsapp == "5511939050162"

    def test_lista_vazia(self):
        """Lista vazia retorna None."""
        contato = extrair_contato([])
        assert contato is None

    def test_sem_telefone_retorna_none(self):
        """Sem telefone retorna None."""
        linhas = ["Interessados mandar mensagem"]
        contato = extrair_contato(linhas)
        assert contato is None


class TestCasosReais:
    """Testes com formatos reais."""

    def test_formato_emoji(self):
        """Formato com emoji."""
        linhas = ["📲11964391344"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert "64391344" in contato.whatsapp

    def test_formato_wame_completo(self):
        """wa.me com DDI."""
        linhas = ["wa.me/5511939050162"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.whatsapp == "5511939050162"

    def test_formato_nome_separado(self):
        """Nome em linha separada."""
        linhas = [
            "📲 Eloisa",
            "wa.me/5511939050162"
        ]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Eloisa"

    def test_formato_interessados(self):
        """Formato 'Interessados...'."""
        linhas = ["Interessados chamar Maria: 11 99999-9999"]
        contato = extrair_contato(linhas)

        assert contato is not None
        assert contato.nome == "Maria"
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `extrator_contato.py`
- [ ] Implementar `_normalizar_telefone()`
- [ ] Implementar `_extrair_telefone()`
- [ ] Implementar `_extrair_nome()`
- [ ] Implementar `extrair_contato()`
- [ ] Adicionar exports em `__init__.py`

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar testes
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros mypy
- [ ] Zero erros ruff

---

## Definition of Done (E06)

Este épico está **COMPLETO** quando:

1. ✅ Normaliza telefones para formato internacional
2. ✅ Extrai telefones de links wa.me
3. ✅ Extrai telefones diretos no texto
4. ✅ Extrai nome quando presente
5. ✅ Suporta múltiplos formatos de contato
6. ✅ 100% dos testes passando
7. ✅ Zero erros mypy/ruff
