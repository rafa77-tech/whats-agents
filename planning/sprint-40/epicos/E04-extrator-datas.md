# E04 - Extrator de Datas

**Épico:** E04
**Nome:** Extrator de Datas e Períodos
**Dependências:** E01, E02
**Prioridade:** Alta (crítico)

---

## Objetivo

Extrair todas as combinações de data + período + horário das seções de DATA identificadas pelo parser. Cada combinação vira um objeto `DataPeriodoExtraido`.

---

## Contexto

Mensagens de grupos têm diversos formatos de data:

1. **Data explícita:** "26/01", "26/01/2026", "26 de janeiro"
2. **Data relativa:** "amanhã", "hoje", "segunda-feira"
3. **Período explícito:** "manhã", "tarde", "noite", "SD", "SN"
4. **Horário explícito:** "7h-13h", "19:00 às 07:00"
5. **Combinações:** "26/01 - Segunda - Manhã 7-13h"

O extrator deve:
1. Parsear a data para `date`
2. Calcular o `dia_semana` (segunda, terça, etc.)
3. Identificar o `periodo` (manhã, tarde, noite, etc.)
4. Extrair `hora_inicio` e `hora_fim` se disponíveis

---

## Entregáveis

### 1. Arquivo: `extrator_datas.py`

```python
"""
Extrator de datas e períodos de mensagens de grupos.

Extrai todas as combinações data + período + horário.
"""

import re
from datetime import date, time, datetime, timedelta
from typing import List, Optional, Tuple

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import (
    DataPeriodoExtraido,
    DiaSemana,
    Periodo,
)

logger = get_logger(__name__)


# =============================================================================
# Mapeamentos
# =============================================================================

# Mapeamento de dia da semana Python -> enum
WEEKDAY_TO_ENUM = {
    0: DiaSemana.SEGUNDA,
    1: DiaSemana.TERCA,
    2: DiaSemana.QUARTA,
    3: DiaSemana.QUINTA,
    4: DiaSemana.SEXTA,
    5: DiaSemana.SABADO,
    6: DiaSemana.DOMINGO,
}

# Nomes de dias em português
DIAS_SEMANA_PT = {
    "segunda": 0, "seg": 0, "segunda-feira": 0, "2ª": 0,
    "terça": 1, "terca": 1, "ter": 1, "terça-feira": 1, "3ª": 1,
    "quarta": 2, "qua": 2, "quarta-feira": 2, "4ª": 2,
    "quinta": 3, "qui": 3, "quinta-feira": 3, "5ª": 3,
    "sexta": 4, "sex": 4, "sexta-feira": 4, "6ª": 4,
    "sábado": 5, "sabado": 5, "sab": 5, "sáb": 5,
    "domingo": 6, "dom": 6,
}

# Meses em português
MESES_PT = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "março": 3, "marco": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}

# Mapeamento de período
PERIODOS_MAP = {
    # Manhã
    "manhã": Periodo.MANHA, "manha": Periodo.MANHA, "manh": Periodo.MANHA,
    "matutino": Periodo.MANHA,
    # Tarde
    "tarde": Periodo.TARDE, "vespertino": Periodo.TARDE,
    # Noite
    "noite": Periodo.NOITE, "noturno": Periodo.NOTURNO,
    "madrugada": Periodo.NOTURNO,
    # Diurno (SD - 12h)
    "diurno": Periodo.DIURNO, "sd": Periodo.DIURNO, "s.d.": Periodo.DIURNO,
    "plantão diurno": Periodo.DIURNO, "plantao diurno": Periodo.DIURNO,
    # Noturno (SN - 12h)
    "sn": Periodo.NOTURNO, "s.n.": Periodo.NOTURNO,
    "plantão noturno": Periodo.NOTURNO, "plantao noturno": Periodo.NOTURNO,
    # Cinderela
    "cinderela": Periodo.CINDERELA, "cind": Periodo.CINDERELA,
}


# =============================================================================
# Regex Patterns
# =============================================================================

# Data no formato dd/mm ou dd/mm/yyyy
PATTERN_DATA_BARRA = re.compile(
    r'(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?'
)

# Data por extenso "26 de janeiro"
PATTERN_DATA_EXTENSO = re.compile(
    r'(\d{1,2})\s+(?:de\s+)?(' + '|'.join(MESES_PT.keys()) + r')',
    re.IGNORECASE
)

# Horário no formato HH:MM ou HHh
PATTERN_HORARIO = re.compile(
    r'(\d{1,2})[h:]?(\d{0,2})?\s*[-–aàás]\s*(\d{1,2})[h:]?(\d{0,2})?',
    re.IGNORECASE
)

# Horário isolado
PATTERN_HORARIO_SIMPLES = re.compile(
    r'(\d{1,2})[h:](\d{2})?'
)


# =============================================================================
# Funções de Extração
# =============================================================================

def _limpar_texto(texto: str) -> str:
    """Remove emojis e caracteres especiais."""
    texto = re.sub(r'[🗓📅📆⏰🕐🕛]', '', texto)
    texto = texto.replace('*', '')
    return ' '.join(texto.split()).strip()


def _calcular_dia_semana(data: date) -> DiaSemana:
    """Calcula dia da semana de uma data."""
    return WEEKDAY_TO_ENUM[data.weekday()]


def _inferir_ano(mes: int, dia: int, hoje: date) -> int:
    """
    Infere o ano quando não especificado.

    Regra: Se a data já passou este ano, assume próximo ano.
    """
    data_este_ano = date(hoje.year, mes, dia)
    if data_este_ano < hoje:
        return hoje.year + 1
    return hoje.year


def _parsear_data_barra(texto: str, hoje: date) -> Optional[date]:
    """
    Parseia data no formato dd/mm ou dd/mm/yyyy.

    Returns:
        date ou None
    """
    match = PATTERN_DATA_BARRA.search(texto)
    if not match:
        return None

    dia = int(match.group(1))
    mes = int(match.group(2))
    ano_str = match.group(3)

    if ano_str:
        ano = int(ano_str)
        if ano < 100:
            ano += 2000
    else:
        ano = _inferir_ano(mes, dia, hoje)

    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _parsear_data_extenso(texto: str, hoje: date) -> Optional[date]:
    """
    Parseia data por extenso "26 de janeiro".

    Returns:
        date ou None
    """
    match = PATTERN_DATA_EXTENSO.search(texto)
    if not match:
        return None

    dia = int(match.group(1))
    mes_nome = match.group(2).lower()
    mes = MESES_PT.get(mes_nome)

    if not mes:
        return None

    ano = _inferir_ano(mes, dia, hoje)

    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def _parsear_data_relativa(texto: str, hoje: date) -> Optional[date]:
    """
    Parseia datas relativas: hoje, amanhã, dia da semana.

    Returns:
        date ou None
    """
    texto_lower = texto.lower()

    if "hoje" in texto_lower:
        return hoje

    if "amanhã" in texto_lower or "amanha" in texto_lower:
        return hoje + timedelta(days=1)

    # Verificar dia da semana
    for dia_nome, dia_num in DIAS_SEMANA_PT.items():
        if dia_nome in texto_lower:
            # Calcular próxima ocorrência deste dia
            dias_ate = (dia_num - hoje.weekday()) % 7
            if dias_ate == 0:
                dias_ate = 7  # Se é hoje, assume próxima semana
            return hoje + timedelta(days=dias_ate)

    return None


def _parsear_horario(texto: str) -> Tuple[Optional[time], Optional[time]]:
    """
    Extrai horário de início e fim.

    Returns:
        Tupla (hora_inicio, hora_fim)
    """
    match = PATTERN_HORARIO.search(texto)
    if not match:
        return None, None

    try:
        hora_ini = int(match.group(1))
        min_ini = int(match.group(2)) if match.group(2) else 0

        hora_fim = int(match.group(3))
        min_fim = int(match.group(4)) if match.group(4) else 0

        return time(hora_ini, min_ini), time(hora_fim, min_fim)
    except (ValueError, TypeError):
        return None, None


def _inferir_periodo_de_horario(
    hora_inicio: Optional[time],
    hora_fim: Optional[time]
) -> Optional[Periodo]:
    """
    Infere período baseado no horário.

    Regras:
    - Início 6-12h: Manhã
    - Início 12-18h: Tarde
    - Início 18h+ ou fim antes de 8h: Noite
    - 12h de dia (7-19): Diurno
    - 12h de noite (19-7): Noturno
    """
    if not hora_inicio:
        return None

    h_ini = hora_inicio.hour

    # Verificar se é plantão de 12h
    if hora_fim:
        h_fim = hora_fim.hour
        # 7-19 ou similar = Diurno
        if 6 <= h_ini <= 8 and 18 <= h_fim <= 20:
            return Periodo.DIURNO
        # 19-7 ou similar = Noturno
        if 18 <= h_ini <= 20 and 6 <= h_fim <= 8:
            return Periodo.NOTURNO
        # 19-1 ou similar = Cinderela
        if 18 <= h_ini <= 20 and 0 <= h_fim <= 2:
            return Periodo.CINDERELA

    # Inferir por horário de início
    if 6 <= h_ini < 12:
        return Periodo.MANHA
    elif 12 <= h_ini < 18:
        return Periodo.TARDE
    else:
        return Periodo.NOITE


def _extrair_periodo(texto: str) -> Optional[Periodo]:
    """Extrai período do texto por keywords."""
    texto_lower = texto.lower()

    for keyword, periodo in PERIODOS_MAP.items():
        if keyword in texto_lower:
            return periodo

    return None


def extrair_data_periodo(
    linha: str,
    data_referencia: Optional[date] = None
) -> Optional[DataPeriodoExtraido]:
    """
    Extrai data e período de uma linha.

    Args:
        linha: Linha de texto
        data_referencia: Data de referência para "hoje" e "amanhã"

    Returns:
        DataPeriodoExtraido ou None
    """
    hoje = data_referencia or date.today()
    linha_limpa = _limpar_texto(linha)

    if not linha_limpa:
        return None

    # 1. Tentar extrair data
    data = (
        _parsear_data_barra(linha_limpa, hoje) or
        _parsear_data_extenso(linha_limpa, hoje) or
        _parsear_data_relativa(linha_limpa, hoje)
    )

    if not data:
        logger.debug(f"Não encontrou data em: {linha_limpa}")
        return None

    # 2. Calcular dia da semana
    dia_semana = _calcular_dia_semana(data)

    # 3. Extrair horários
    hora_inicio, hora_fim = _parsear_horario(linha_limpa)

    # 4. Extrair ou inferir período
    periodo = _extrair_periodo(linha_limpa)
    if not periodo and (hora_inicio or hora_fim):
        periodo = _inferir_periodo_de_horario(hora_inicio, hora_fim)
    if not periodo:
        # Default para diurno se não conseguir determinar
        periodo = Periodo.DIURNO
        confianca = 0.5
    else:
        confianca = 0.9

    return DataPeriodoExtraido(
        data=data,
        dia_semana=dia_semana,
        periodo=periodo,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        confianca=confianca
    )


def extrair_datas_periodos(
    linhas_data: List[str],
    data_referencia: Optional[date] = None
) -> List[DataPeriodoExtraido]:
    """
    Extrai todas as datas e períodos das linhas de DATA.

    Args:
        linhas_data: Linhas classificadas como DATA pelo parser
        data_referencia: Data de referência

    Returns:
        Lista de DataPeriodoExtraido

    Example:
        >>> linhas = ["🗓 26/01 - Segunda - Manhã 7-13h", "🗓 27/01 - Terça - Noite 19-7h"]
        >>> datas = extrair_datas_periodos(linhas)
        >>> len(datas)
        2
    """
    resultados = []

    for linha in linhas_data:
        resultado = extrair_data_periodo(linha, data_referencia)
        if resultado:
            resultados.append(resultado)

    logger.debug(f"Extraídas {len(resultados)} datas/períodos")
    return resultados
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_extrator_datas.py`

```python
"""Testes para extrator de datas e períodos."""
import pytest
from datetime import date, time

from app.services.grupos.extrator_v2.extrator_datas import (
    extrair_datas_periodos,
    extrair_data_periodo,
    _parsear_data_barra,
    _parsear_horario,
    _extrair_periodo,
    _calcular_dia_semana,
)
from app.services.grupos.extrator_v2.types import DiaSemana, Periodo


# Data de referência para testes
HOJE = date(2026, 1, 25)  # Sábado


class TestParsearDataBarra:
    """Testes para parsing de data com barra."""

    def test_data_dia_mes(self):
        """Data dd/mm."""
        data = _parsear_data_barra("26/01", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_dia_mes_ano_curto(self):
        """Data dd/mm/yy."""
        data = _parsear_data_barra("26/01/26", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_dia_mes_ano_longo(self):
        """Data dd/mm/yyyy."""
        data = _parsear_data_barra("26/01/2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_com_ponto(self):
        """Data com ponto como separador."""
        data = _parsear_data_barra("26.01.2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_com_hifen(self):
        """Data com hífen como separador."""
        data = _parsear_data_barra("26-01-2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_passada_vai_proximo_ano(self):
        """Data que já passou este ano vai para próximo."""
        # Estamos em 25/01/2026, então 24/01 seria 2027
        data = _parsear_data_barra("24/01", HOJE)
        assert data == date(2027, 1, 24)

    def test_data_invalida(self):
        """Data inválida retorna None."""
        data = _parsear_data_barra("32/01/2026", HOJE)
        assert data is None


class TestParsearHorario:
    """Testes para parsing de horário."""

    def test_horario_h(self):
        """Formato 7h-13h."""
        ini, fim = _parsear_horario("7h-13h")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_dois_pontos(self):
        """Formato 07:00-13:00."""
        ini, fim = _parsear_horario("07:00-13:00")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_com_as(self):
        """Formato 7 às 13."""
        ini, fim = _parsear_horario("7 às 13")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_noturno(self):
        """Horário noturno 19-7."""
        ini, fim = _parsear_horario("19h-7h")
        assert ini == time(19, 0)
        assert fim == time(7, 0)

    def test_sem_horario(self):
        """Texto sem horário."""
        ini, fim = _parsear_horario("Segunda manhã")
        assert ini is None
        assert fim is None


class TestExtrairPeriodo:
    """Testes para extração de período por keyword."""

    def test_periodo_manha(self):
        assert _extrair_periodo("manhã") == Periodo.MANHA
        assert _extrair_periodo("Manhã 7-13h") == Periodo.MANHA

    def test_periodo_tarde(self):
        assert _extrair_periodo("tarde") == Periodo.TARDE
        assert _extrair_periodo("Tarde 13-19h") == Periodo.TARDE

    def test_periodo_noite(self):
        assert _extrair_periodo("noite") == Periodo.NOITE
        assert _extrair_periodo("noturno") == Periodo.NOTURNO

    def test_periodo_diurno(self):
        assert _extrair_periodo("SD") == Periodo.DIURNO
        assert _extrair_periodo("diurno") == Periodo.DIURNO

    def test_periodo_noturno_sn(self):
        assert _extrair_periodo("SN") == Periodo.NOTURNO

    def test_periodo_cinderela(self):
        assert _extrair_periodo("cinderela") == Periodo.CINDERELA


class TestCalcularDiaSemana:
    """Testes para cálculo de dia da semana."""

    def test_segunda(self):
        assert _calcular_dia_semana(date(2026, 1, 26)) == DiaSemana.SEGUNDA

    def test_terca(self):
        assert _calcular_dia_semana(date(2026, 1, 27)) == DiaSemana.TERCA

    def test_sabado(self):
        assert _calcular_dia_semana(date(2026, 1, 31)) == DiaSemana.SABADO

    def test_domingo(self):
        assert _calcular_dia_semana(date(2026, 2, 1)) == DiaSemana.DOMINGO


class TestExtrairDataPeriodo:
    """Testes para extração completa."""

    def test_linha_completa(self):
        """Linha com todos os dados."""
        resultado = extrair_data_periodo(
            "🗓 26/01 - Segunda - Manhã 7-13h",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        assert resultado.dia_semana == DiaSemana.SEGUNDA
        assert resultado.periodo == Periodo.MANHA
        assert resultado.hora_inicio == time(7, 0)
        assert resultado.hora_fim == time(13, 0)

    def test_linha_sem_horario(self):
        """Linha sem horário explícito."""
        resultado = extrair_data_periodo(
            "26/01 Segunda Manhã",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        assert resultado.periodo == Periodo.MANHA
        assert resultado.hora_inicio is None

    def test_linha_so_data(self):
        """Linha só com data."""
        resultado = extrair_data_periodo(
            "26/01",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        # Período default

    def test_linha_vazia(self):
        """Linha vazia retorna None."""
        resultado = extrair_data_periodo("", data_referencia=HOJE)
        assert resultado is None


class TestExtrairDatasPeriodos:
    """Testes para extração de múltiplas datas."""

    def test_multiplas_datas(self):
        """Extrai múltiplas datas."""
        linhas = [
            "🗓 26/01 - Segunda - Manhã 7-13h",
            "🗓 27/01 - Terça - Tarde 13-19h",
            "🗓 28/01 - Quarta - Noite 19-7h",
        ]

        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)

        assert len(resultados) == 3
        assert resultados[0].periodo == Periodo.MANHA
        assert resultados[1].periodo == Periodo.TARDE
        assert resultados[2].periodo == Periodo.NOITE

    def test_lista_vazia(self):
        """Lista vazia retorna lista vazia."""
        resultados = extrair_datas_periodos([], data_referencia=HOJE)
        assert resultados == []

    def test_linhas_invalidas_ignoradas(self):
        """Linhas sem data são ignoradas."""
        linhas = [
            "Bom dia",
            "🗓 26/01 - Segunda",
            "Interessados falar comigo",
        ]

        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)
        assert len(resultados) == 1


class TestCasosReais:
    """Testes com formatos reais."""

    def test_formato_completo(self):
        """Formato mais comum em grupos."""
        linhas = [
            "📅 27/01 SEGUNDA",
            "⏰ 19 as 07",
        ]

        # Só a primeira linha tem data
        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)
        assert len(resultados) >= 1

    def test_formato_compacto(self):
        """Formato compacto."""
        linha = "26/01 dom diurno 7-19h"
        resultado = extrair_data_periodo(linha, data_referencia=HOJE)

        assert resultado is not None
        assert resultado.periodo == Periodo.DIURNO

    def test_formato_sd_sn(self):
        """Formato SD/SN."""
        linha1 = "26/01 - SD"
        linha2 = "27/01 - SN"

        r1 = extrair_data_periodo(linha1, data_referencia=HOJE)
        r2 = extrair_data_periodo(linha2, data_referencia=HOJE)

        assert r1.periodo == Periodo.DIURNO
        assert r2.periodo == Periodo.NOTURNO
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar arquivo `extrator_datas.py`
- [ ] Implementar parsing de data (barra, extenso, relativa)
- [ ] Implementar parsing de horário
- [ ] Implementar extração de período
- [ ] Implementar inferência de período por horário
- [ ] Adicionar exports em `__init__.py`

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar testes
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros mypy
- [ ] Zero erros ruff

---

## Definition of Done (E04)

Este épico está **COMPLETO** quando:

1. ✅ Parseia datas em formato dd/mm e dd/mm/yyyy
2. ✅ Parseia datas relativas (hoje, amanhã, dia da semana)
3. ✅ Calcula dia da semana corretamente
4. ✅ Extrai período por keyword (manhã, tarde, noite, SD, SN)
5. ✅ Infere período pelo horário quando não explícito
6. ✅ Extrai hora_inicio e hora_fim
7. ✅ 100% dos testes passando
8. ✅ Zero erros mypy/ruff
