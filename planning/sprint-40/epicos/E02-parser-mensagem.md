# E02 - Parser de Mensagem

**Épico:** E02
**Nome:** Parser de Mensagem
**Dependências:** E01
**Prioridade:** Alta (crítico)

---

## Objetivo

Criar um parser que separa a mensagem bruta em seções estruturadas. O parser identifica onde estão as informações de local, datas, valores e contato, facilitando a extração específica de cada componente.

---

## Contexto do Problema

Mensagens de grupos médicos seguem padrões semi-estruturados. Exemplo:

```
📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/01 - Segunda - Tarde 13-19h
🗓 27/01 - Terça - Noite 19-7h

💰 Segunda a Sexta: R$ 1.700
💰 Sábado e Domingo: R$ 1.800

📲 Eloisa - wa.me/5511939050162
```

O parser deve identificar:
1. **Seção de Local:** linhas com 📍 ou que mencionam hospital/clínica/UPA
2. **Seção de Datas:** linhas com 🗓 ou padrões de data (dd/mm)
3. **Seção de Valores:** linhas com 💰 ou R$ ou padrões monetários
4. **Seção de Contato:** linhas com 📲 ou padrões de telefone/WhatsApp

---

## Entregáveis

### 1. Arquivo: `parser_mensagem.py`

```python
"""
Parser de mensagem para extração de vagas.

Separa a mensagem em seções lógicas:
- Local (hospital, endereço)
- Datas (datas e períodos)
- Valores (valores e regras)
- Contato (nome e telefone)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

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
    texto_original: str
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
EMOJIS_LOCAL = {"📍", "🏥", "🏨", "🏢", "📌", "🗺️"}
EMOJIS_DATA = {"🗓", "📅", "📆", "🗓️", "⏰", "🕐", "🕛"}
EMOJIS_VALOR = {"💰", "💵", "💲", "🤑", "💸", "💳"}
EMOJIS_CONTATO = {"📲", "📞", "📱", "☎️", "🤙", "💬", "👤"}

# Palavras-chave por seção
KEYWORDS_LOCAL = {
    "hospital", "clínica", "clinica", "upa", "pronto socorro",
    "pronto atendimento", "ps ", "pa ", "ama ", "ubs ", "caps ",
    "santa casa", "beneficência", "beneficencia", "maternidade",
    "estrada", "avenida", "av.", "rua", "r.", "alameda", "al."
}

KEYWORDS_DATA = {
    "segunda", "terça", "terca", "quarta", "quinta", "sexta",
    "sábado", "sabado", "domingo", "seg", "ter", "qua", "qui",
    "sex", "sab", "dom", "manhã", "manha", "tarde", "noite",
    "diurno", "noturno", "sd", "sn", "cinderela", "plantão", "plantao"
}

KEYWORDS_VALOR = {
    "r$", "reais", "valor", "paga", "pagamento", "pix",
    "seg-sex", "seg a sex", "sab-dom", "sab e dom",
    "segunda a sexta", "sábado e domingo", "sabado e domingo"
}

KEYWORDS_CONTATO = {
    "contato", "interessados", "falar com", "chamar", "ligar",
    "whatsapp", "whats", "zap", "wa.me", "telefone", "fone",
    "cel", "celular", "@"
}

KEYWORDS_ESPECIALIDADE = {
    "clínica médica", "clinica medica", "cm", "pediatria", "ped",
    "ortopedia", "orto", "cardiologia", "cardio", "ginecologia",
    "gino", "go", "cirurgia", "cir", "neurologia", "neuro",
    "psiquiatria", "psiq", "anestesiologia", "anestesio", "usg",
    "ultrassonografia", "endoscopia", "emergência", "emergencia"
}

# Padrões regex
PATTERN_DATA = re.compile(
    r'\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?'  # dd/mm ou dd/mm/yyyy
)

PATTERN_HORARIO = re.compile(
    r'\d{1,2}[h:]?\d{0,2}\s*[-–aà]\s*\d{1,2}[h:]?\d{0,2}'  # 7h-13h, 19:00-07:00
)

PATTERN_VALOR_MONETARIO = re.compile(
    r'R?\$?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?'  # R$ 1.800, 1800, 1.800,00
)

PATTERN_TELEFONE = re.compile(
    r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?)?\d{4}[-.\s]?\d{4}'
)

PATTERN_WHATSAPP_LINK = re.compile(
    r'wa\.me/\d+'
)


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para análise."""
    return texto.lower().strip()


def _tem_emoji(texto: str, emojis: set) -> bool:
    """Verifica se texto contém algum emoji do conjunto."""
    return any(emoji in texto for emoji in emojis)


def _tem_keyword(texto: str, keywords: set) -> bool:
    """Verifica se texto contém alguma keyword."""
    texto_lower = texto.lower()
    return any(kw in texto_lower for kw in keywords)


def _classificar_linha(linha: str, indice: int) -> LinhaParsed:
    """
    Classifica uma linha de texto.

    A classificação usa múltiplos sinais:
    1. Emojis indicadores (peso alto)
    2. Keywords específicas (peso médio)
    3. Padrões regex (peso médio)
    4. Contexto da posição (peso baixo)

    Returns:
        LinhaParsed com tipo e confiança
    """
    linha_stripped = linha.strip()

    if not linha_stripped:
        return LinhaParsed(
            texto=linha,
            tipo=TipoSecao.DESCONHECIDO,
            indice=indice,
            confianca=0.0
        )

    scores = {
        TipoSecao.LOCAL: 0.0,
        TipoSecao.DATA: 0.0,
        TipoSecao.VALOR: 0.0,
        TipoSecao.CONTATO: 0.0,
        TipoSecao.ESPECIALIDADE: 0.0,
    }

    # 1. Emojis (peso 0.5)
    if _tem_emoji(linha_stripped, EMOJIS_LOCAL):
        scores[TipoSecao.LOCAL] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_DATA):
        scores[TipoSecao.DATA] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_VALOR):
        scores[TipoSecao.VALOR] += 0.5
    if _tem_emoji(linha_stripped, EMOJIS_CONTATO):
        scores[TipoSecao.CONTATO] += 0.5

    # 2. Keywords (peso 0.3)
    if _tem_keyword(linha_stripped, KEYWORDS_LOCAL):
        scores[TipoSecao.LOCAL] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_DATA):
        scores[TipoSecao.DATA] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_VALOR):
        scores[TipoSecao.VALOR] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_CONTATO):
        scores[TipoSecao.CONTATO] += 0.3
    if _tem_keyword(linha_stripped, KEYWORDS_ESPECIALIDADE):
        scores[TipoSecao.ESPECIALIDADE] += 0.3

    # 3. Padrões regex (peso 0.3)
    if PATTERN_DATA.search(linha_stripped):
        scores[TipoSecao.DATA] += 0.3
    if PATTERN_HORARIO.search(linha_stripped):
        scores[TipoSecao.DATA] += 0.2
    if PATTERN_VALOR_MONETARIO.search(linha_stripped):
        scores[TipoSecao.VALOR] += 0.3
    if PATTERN_TELEFONE.search(linha_stripped) or PATTERN_WHATSAPP_LINK.search(linha_stripped):
        scores[TipoSecao.CONTATO] += 0.4

    # Determinar tipo com maior score
    tipo_max = max(scores, key=scores.get)
    score_max = scores[tipo_max]

    if score_max < 0.1:
        tipo_max = TipoSecao.DESCONHECIDO

    return LinhaParsed(
        texto=linha,
        tipo=tipo_max,
        indice=indice,
        confianca=min(score_max, 1.0)
    )


def _agrupar_secoes(linhas: List[LinhaParsed]) -> MensagemParsed:
    """
    Agrupa linhas classificadas em seções.

    Linhas adjacentes do mesmo tipo são agrupadas.
    Linhas DESCONHECIDO são agregadas à seção anterior/posterior mais próxima.
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
        # DESCONHECIDO é ignorado por enquanto

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
        return MensagemParsed(texto_original=texto)

    # Separar em linhas
    linhas = texto.split('\n')

    # Classificar cada linha
    linhas_parsed = [
        _classificar_linha(linha, i)
        for i, linha in enumerate(linhas)
    ]

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
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_parser_mensagem.py`

```python
"""Testes para parser de mensagem."""
import pytest

from app.services.grupos.extrator_v2.parser_mensagem import (
    parsear_mensagem,
    _classificar_linha,
    TipoSecao,
    MensagemParsed,
)


class TestClassificarLinha:
    """Testes para classificação de linhas individuais."""

    def test_linha_local_com_emoji(self):
        """Linha com emoji de local."""
        linha = _classificar_linha("📍 Hospital Campo Limpo", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.5

    def test_linha_local_com_keyword(self):
        """Linha com keyword de local."""
        linha = _classificar_linha("Hospital São Luiz ABC", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.3

    def test_linha_endereco(self):
        """Linha com endereço."""
        linha = _classificar_linha("Av. Brasil, 1000 - Centro", 0)
        assert linha.tipo == TipoSecao.LOCAL
        assert linha.confianca >= 0.3

    def test_linha_data_com_emoji(self):
        """Linha com emoji de data."""
        linha = _classificar_linha("🗓 26/01 - Segunda - Manhã", 0)
        assert linha.tipo == TipoSecao.DATA
        assert linha.confianca >= 0.5

    def test_linha_data_com_pattern(self):
        """Linha com padrão de data."""
        linha = _classificar_linha("26/01 - Segunda - Manhã 7-13h", 0)
        assert linha.tipo == TipoSecao.DATA
        assert linha.confianca >= 0.3

    def test_linha_valor_com_emoji(self):
        """Linha com emoji de valor."""
        linha = _classificar_linha("💰 R$ 1.700", 0)
        assert linha.tipo == TipoSecao.VALOR
        assert linha.confianca >= 0.5

    def test_linha_valor_com_pattern(self):
        """Linha com padrão monetário."""
        linha = _classificar_linha("Segunda a Sexta: R$ 1.700", 0)
        assert linha.tipo == TipoSecao.VALOR
        assert linha.confianca >= 0.3

    def test_linha_contato_com_emoji(self):
        """Linha com emoji de contato."""
        linha = _classificar_linha("📲 Eloisa - 11999999999", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.5

    def test_linha_contato_com_whatsapp(self):
        """Linha com link WhatsApp."""
        linha = _classificar_linha("wa.me/5511939050162", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.4

    def test_linha_contato_com_keyword(self):
        """Linha com keyword de contato."""
        linha = _classificar_linha("Interessados falar com Maria", 0)
        assert linha.tipo == TipoSecao.CONTATO
        assert linha.confianca >= 0.3

    def test_linha_vazia(self):
        """Linha vazia retorna DESCONHECIDO."""
        linha = _classificar_linha("", 0)
        assert linha.tipo == TipoSecao.DESCONHECIDO
        assert linha.confianca == 0.0

    def test_linha_sem_indicadores(self):
        """Linha sem indicadores claros."""
        linha = _classificar_linha("Bom dia pessoal!", 0)
        assert linha.tipo == TipoSecao.DESCONHECIDO


class TestParsearMensagem:
    """Testes para parsing completo de mensagem."""

    def test_mensagem_completa(self):
        """Parseia mensagem com todas as seções."""
        texto = """📍 Hospital Campo Limpo
Estrada Itapecirica, 1661 - SP

🗓 26/01 - Segunda - Tarde 13-19h
🗓 27/01 - Terça - Noite 19-7h

💰 Segunda a Sexta: R$ 1.700
💰 Sábado e Domingo: R$ 1.800

📲 Eloisa
wa.me/5511939050162"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

        assert len(msg.secoes_local) >= 1
        assert len(msg.secoes_data) == 2
        assert len(msg.secoes_valor) == 2
        assert len(msg.secoes_contato) >= 1

    def test_mensagem_sem_emoji(self):
        """Parseia mensagem sem emojis (só keywords)."""
        texto = """Hospital São Luiz ABC
Av. Brasil, 1000

28/01 - Quarta - Noturno 19-7h

Valor: R$ 2.000 PJ

Interessados ligar para João: 11999999999"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_mensagem_minima(self):
        """Parseia mensagem mínima."""
        texto = "Hospital ABC - 26/01 manhã R$ 1500"

        msg = parsear_mensagem(texto)

        # Linha única pode ter múltiplas classificações
        # O parser deve identificar pelo menos data e valor
        assert msg.tem_datas is True or msg.tem_valores is True

    def test_mensagem_vazia(self):
        """Mensagem vazia retorna objeto vazio."""
        msg = parsear_mensagem("")

        assert msg.tem_local is False
        assert msg.tem_datas is False
        assert msg.tem_valores is False
        assert msg.tem_contato is False

    def test_mensagem_none(self):
        """Mensagem None não quebra."""
        msg = parsear_mensagem(None)
        assert isinstance(msg, MensagemParsed)

    def test_preserva_texto_original(self):
        """Preserva texto original na resposta."""
        texto = "📍 Hospital ABC"
        msg = parsear_mensagem(texto)
        assert msg.texto_original == texto

    def test_multiplos_hospitais(self):
        """Detecta múltiplos hospitais."""
        texto = """📍 Hospital ABC
📍 Hospital XYZ
🗓 26/01 manhã"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_local) == 2

    def test_multiplas_datas(self):
        """Detecta múltiplas datas."""
        texto = """📍 Hospital ABC
🗓 26/01 - Segunda
🗓 27/01 - Terça
🗓 28/01 - Quarta
🗓 29/01 - Quinta
🗓 30/01 - Sexta"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_data) == 5

    def test_regras_valor_diferentes(self):
        """Detecta diferentes regras de valor."""
        texto = """💰 Valores:
Segunda a Sexta: R$ 1.700
Sábado: R$ 1.800
Domingo: R$ 2.000
Feriado: R$ 2.500"""

        msg = parsear_mensagem(texto)
        assert len(msg.secoes_valor) >= 4


class TestCasosReais:
    """Testes com casos reais de grupos médicos."""

    def test_caso_real_1(self):
        """Caso real: formato típico com emojis."""
        texto = """🔴🔴PRECISO🔴🔴

📍UPA CAMPO LIMPO
📅 27/01 SEGUNDA
⏰ 19 as 07
💰1.600
📲11964391344"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert msg.tem_datas is True
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_caso_real_2(self):
        """Caso real: formato de lista de datas."""
        texto = """*PLANTÕES CLINICA MÉDICA*

Hospital Santa Casa ABC

26/01 dom diurno 7-19h
27/01 seg noturno 19-7h
28/01 ter diurno 7-19h

Valor R$ 1.500 (dom +100)

Int. Maria 11 99999-9999"""

        msg = parsear_mensagem(texto)

        assert msg.tem_local is True
        assert len(msg.secoes_data) >= 3
        assert msg.tem_valores is True
        assert msg.tem_contato is True

    def test_caso_real_3(self):
        """Caso real: formato compacto."""
        texto = """CM PS Central 28/12 noturno 1800 PJ - Ana 11987654321"""

        msg = parsear_mensagem(texto)

        # Mesmo em formato compacto, deve identificar elementos
        assert len(msg.linhas) > 0
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `parser_mensagem.py`
- [ ] Implementar `_classificar_linha()`
- [ ] Implementar `_agrupar_secoes()`
- [ ] Implementar `parsear_mensagem()`
- [ ] Adicionar exports em `__init__.py`

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar `uv run pytest tests/services/grupos/extrator_v2/test_parser_mensagem.py -v`
- [ ] 100% dos testes passando

### Qualidade
- [ ] Rodar mypy
- [ ] Rodar ruff
- [ ] Zero erros

---

## Definition of Done (E02)

Este épico está **COMPLETO** quando:

1. ✅ Parser implementado e funcionando
2. ✅ Classifica corretamente linhas de LOCAL
3. ✅ Classifica corretamente linhas de DATA
4. ✅ Classifica corretamente linhas de VALOR
5. ✅ Classifica corretamente linhas de CONTATO
6. ✅ Agrupa seções corretamente
7. ✅ 100% dos testes passando
8. ✅ Zero erros de mypy/ruff
