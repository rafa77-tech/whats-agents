# E01 - Estrutura e Tipos

**Épico:** E01
**Nome:** Estrutura e Tipos
**Dependências:** Nenhuma
**Prioridade:** Alta (fundação)

---

## Objetivo

Criar a estrutura de diretórios e os tipos (dataclasses/Pydantic models) que serão usados por todos os outros épicos. Este é o épico fundacional - todos os outros dependem dele.

---

## Entregáveis

### 1. Estrutura de Diretórios

```
app/services/grupos/extrator_v2/
├── __init__.py           # Exports públicos
├── types.py              # Todos os tipos
└── exceptions.py         # Exceções customizadas
```

### 2. Arquivo: `types.py`

#### 2.1 Enums

```python
from enum import Enum

class DiaSemana(str, Enum):
    """Dia da semana em português."""
    SEGUNDA = "segunda"
    TERCA = "terca"
    QUARTA = "quarta"
    QUINTA = "quinta"
    SEXTA = "sexta"
    SABADO = "sabado"
    DOMINGO = "domingo"


class Periodo(str, Enum):
    """Período do plantão."""
    MANHA = "manha"      # Geralmente 07:00-13:00
    TARDE = "tarde"      # Geralmente 13:00-19:00
    NOITE = "noite"      # Geralmente 19:00-07:00
    DIURNO = "diurno"    # SD - 12h de dia (07:00-19:00)
    NOTURNO = "noturno"  # SN - 12h de noite (19:00-07:00)
    CINDERELA = "cinderela"  # Geralmente 19:00-01:00


class GrupoDia(str, Enum):
    """Grupo de dias para associação de valor."""
    SEG_SEX = "seg_sex"      # Segunda a Sexta
    SAB_DOM = "sab_dom"      # Sábado e Domingo
    SAB = "sabado"           # Apenas Sábado
    DOM = "domingo"          # Apenas Domingo
    FERIADO = "feriado"      # Feriados
    TODOS = "todos"          # Todos os dias (mesmo valor)
```

#### 2.2 Dataclasses de Entrada

```python
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional, List
from uuid import UUID


@dataclass
class HospitalExtraido:
    """Hospital/local extraído da mensagem."""
    nome: str
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    confianca: float = 0.0


@dataclass
class DataPeriodoExtraido:
    """Uma combinação data + período extraída."""
    data: date
    dia_semana: DiaSemana
    periodo: Periodo
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    confianca: float = 0.0


@dataclass
class RegraValor:
    """Regra de valor para um grupo de dias."""
    grupo_dia: GrupoDia
    periodo: Optional[Periodo] = None  # None = todos os períodos
    valor: int = 0
    confianca: float = 0.0


@dataclass
class ValoresExtraidos:
    """Conjunto de valores e suas regras."""
    regras: List[RegraValor] = field(default_factory=list)
    valor_unico: Optional[int] = None  # Quando há só um valor para tudo
    observacoes: Optional[str] = None


@dataclass
class ContatoExtraido:
    """Contato extraído da mensagem."""
    nome: Optional[str] = None
    whatsapp: Optional[str] = None  # Normalizado: apenas números, com código país
    whatsapp_raw: Optional[str] = None  # Formato original
    confianca: float = 0.0


@dataclass
class EspecialidadeExtraida:
    """Especialidade médica extraída."""
    nome: str
    abreviacao: Optional[str] = None  # Ex: "CM" para Clínica Médica
    confianca: float = 0.0
```

#### 2.3 Dataclass de Saída (Vaga Atômica)

```python
@dataclass
class VagaAtomica:
    """
    Uma vaga atômica - unidade indivisível.

    Representa um plantão específico em:
    - Um hospital específico
    - Uma data específica
    - Um período específico
    - Com um valor específico
    """
    # Campos obrigatórios
    data: date
    dia_semana: DiaSemana
    periodo: Periodo
    valor: int  # Valor em reais (inteiro)
    hospital_raw: str

    # Campos de horário
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None

    # Campos de local
    endereco_raw: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None

    # Especialidade
    especialidade_raw: Optional[str] = None

    # Contato
    contato_nome: Optional[str] = None
    contato_whatsapp: Optional[str] = None

    # Metadados
    confianca_geral: float = 0.0
    observacoes: Optional[str] = None

    # Rastreabilidade
    mensagem_id: Optional[UUID] = None
    grupo_id: Optional[UUID] = None

    def to_dict(self) -> dict:
        """Converte para dicionário para persistência."""
        return {
            "data": self.data.isoformat(),
            "dia_semana": self.dia_semana.value,
            "periodo": self.periodo.value,
            "valor": self.valor,
            "hora_inicio": self.hora_inicio.isoformat() if self.hora_inicio else None,
            "hora_fim": self.hora_fim.isoformat() if self.hora_fim else None,
            "hospital_raw": self.hospital_raw,
            "endereco_raw": self.endereco_raw,
            "cidade": self.cidade,
            "estado": self.estado,
            "especialidade_raw": self.especialidade_raw,
            "contato_nome": self.contato_nome,
            "contato_whatsapp": self.contato_whatsapp,
            "confianca_geral": self.confianca_geral,
            "observacoes": self.observacoes,
            "mensagem_id": str(self.mensagem_id) if self.mensagem_id else None,
            "grupo_id": str(self.grupo_id) if self.grupo_id else None,
        }
```

#### 2.4 Dataclass de Resultado

```python
@dataclass
class ResultadoExtracaoV2:
    """Resultado completo de uma extração."""
    vagas: List[VagaAtomica] = field(default_factory=list)

    # Dados intermediários (para debug/auditoria)
    hospitais: List[HospitalExtraido] = field(default_factory=list)
    datas_periodos: List[DataPeriodoExtraido] = field(default_factory=list)
    valores: Optional[ValoresExtraidos] = None
    contato: Optional[ContatoExtraido] = None
    especialidades: List[EspecialidadeExtraida] = field(default_factory=list)

    # Métricas
    total_vagas: int = 0
    tokens_usados: int = 0
    tempo_processamento_ms: int = 0

    # Erros
    erro: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def sucesso(self) -> bool:
        """Retorna True se extração foi bem-sucedida."""
        return self.erro is None and len(self.vagas) > 0
```

### 3. Arquivo: `exceptions.py`

```python
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
```

### 4. Arquivo: `__init__.py`

```python
"""
Extrator de Vagas v2 - Sprint 40

Extrai vagas atômicas de mensagens de grupos de WhatsApp.
Cada vaga é uma combinação única de: data + período + valor + hospital.
"""

from .types import (
    # Enums
    DiaSemana,
    Periodo,
    GrupoDia,
    # Dataclasses de entrada
    HospitalExtraido,
    DataPeriodoExtraido,
    RegraValor,
    ValoresExtraidos,
    ContatoExtraido,
    EspecialidadeExtraida,
    # Dataclass de saída
    VagaAtomica,
    ResultadoExtracaoV2,
)

from .exceptions import (
    ExtracaoError,
    MensagemVaziaError,
    SemHospitalError,
    SemDataError,
    LLMTimeoutError,
    LLMRateLimitError,
    JSONParseError,
)

__all__ = [
    # Enums
    "DiaSemana",
    "Periodo",
    "GrupoDia",
    # Dataclasses
    "HospitalExtraido",
    "DataPeriodoExtraido",
    "RegraValor",
    "ValoresExtraidos",
    "ContatoExtraido",
    "EspecialidadeExtraida",
    "VagaAtomica",
    "ResultadoExtracaoV2",
    # Exceptions
    "ExtracaoError",
    "MensagemVaziaError",
    "SemHospitalError",
    "SemDataError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "JSONParseError",
]
```

---

## Testes Obrigatórios

### Arquivo: `tests/services/grupos/extrator_v2/test_types.py`

```python
"""Testes para tipos do extrator v2."""
import pytest
from datetime import date, time
from uuid import uuid4

from app.services.grupos.extrator_v2 import (
    DiaSemana,
    Periodo,
    GrupoDia,
    HospitalExtraido,
    DataPeriodoExtraido,
    RegraValor,
    ValoresExtraidos,
    ContatoExtraido,
    VagaAtomica,
    ResultadoExtracaoV2,
)


class TestEnums:
    """Testes para enums."""

    def test_dia_semana_valores(self):
        """Verifica todos os dias da semana."""
        assert DiaSemana.SEGUNDA.value == "segunda"
        assert DiaSemana.TERCA.value == "terca"
        assert DiaSemana.QUARTA.value == "quarta"
        assert DiaSemana.QUINTA.value == "quinta"
        assert DiaSemana.SEXTA.value == "sexta"
        assert DiaSemana.SABADO.value == "sabado"
        assert DiaSemana.DOMINGO.value == "domingo"
        assert len(DiaSemana) == 7

    def test_periodo_valores(self):
        """Verifica todos os períodos."""
        assert Periodo.MANHA.value == "manha"
        assert Periodo.TARDE.value == "tarde"
        assert Periodo.NOITE.value == "noite"
        assert Periodo.DIURNO.value == "diurno"
        assert Periodo.NOTURNO.value == "noturno"
        assert Periodo.CINDERELA.value == "cinderela"
        assert len(Periodo) == 6

    def test_grupo_dia_valores(self):
        """Verifica grupos de dia."""
        assert GrupoDia.SEG_SEX.value == "seg_sex"
        assert GrupoDia.SAB_DOM.value == "sab_dom"
        assert GrupoDia.TODOS.value == "todos"


class TestHospitalExtraido:
    """Testes para HospitalExtraido."""

    def test_criacao_minima(self):
        """Cria hospital apenas com nome."""
        hospital = HospitalExtraido(nome="Hospital ABC")
        assert hospital.nome == "Hospital ABC"
        assert hospital.endereco is None
        assert hospital.confianca == 0.0

    def test_criacao_completa(self):
        """Cria hospital com todos os campos."""
        hospital = HospitalExtraido(
            nome="Hospital São Luiz",
            endereco="Av. Brasil, 1000",
            cidade="São Paulo",
            estado="SP",
            confianca=0.95
        )
        assert hospital.nome == "Hospital São Luiz"
        assert hospital.endereco == "Av. Brasil, 1000"
        assert hospital.cidade == "São Paulo"
        assert hospital.estado == "SP"
        assert hospital.confianca == 0.95


class TestDataPeriodoExtraido:
    """Testes para DataPeriodoExtraido."""

    def test_criacao_minima(self):
        """Cria data/período com mínimo."""
        dp = DataPeriodoExtraido(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.MANHA
        )
        assert dp.data == date(2026, 1, 26)
        assert dp.dia_semana == DiaSemana.SEGUNDA
        assert dp.periodo == Periodo.MANHA
        assert dp.hora_inicio is None

    def test_criacao_com_horarios(self):
        """Cria data/período com horários."""
        dp = DataPeriodoExtraido(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.MANHA,
            hora_inicio=time(7, 0),
            hora_fim=time(13, 0),
            confianca=0.9
        )
        assert dp.hora_inicio == time(7, 0)
        assert dp.hora_fim == time(13, 0)
        assert dp.confianca == 0.9


class TestRegraValor:
    """Testes para RegraValor."""

    def test_regra_seg_sex(self):
        """Cria regra para seg-sex."""
        regra = RegraValor(
            grupo_dia=GrupoDia.SEG_SEX,
            valor=1700,
            confianca=0.95
        )
        assert regra.grupo_dia == GrupoDia.SEG_SEX
        assert regra.valor == 1700
        assert regra.periodo is None  # Todos os períodos

    def test_regra_sab_dom_noturno(self):
        """Cria regra para sáb-dom noturno."""
        regra = RegraValor(
            grupo_dia=GrupoDia.SAB_DOM,
            periodo=Periodo.NOTURNO,
            valor=2000,
            confianca=0.9
        )
        assert regra.grupo_dia == GrupoDia.SAB_DOM
        assert regra.periodo == Periodo.NOTURNO
        assert regra.valor == 2000


class TestValoresExtraidos:
    """Testes para ValoresExtraidos."""

    def test_valor_unico(self):
        """Quando há apenas um valor para tudo."""
        valores = ValoresExtraidos(valor_unico=1800)
        assert valores.valor_unico == 1800
        assert len(valores.regras) == 0

    def test_multiplas_regras(self):
        """Múltiplas regras de valor."""
        valores = ValoresExtraidos(
            regras=[
                RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
                RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
            ]
        )
        assert len(valores.regras) == 2
        assert valores.valor_unico is None


class TestContatoExtraido:
    """Testes para ContatoExtraido."""

    def test_criacao_completa(self):
        """Cria contato com todos os dados."""
        contato = ContatoExtraido(
            nome="Eloisa",
            whatsapp="5511939050162",
            whatsapp_raw="wa.me/5511939050162",
            confianca=0.95
        )
        assert contato.nome == "Eloisa"
        assert contato.whatsapp == "5511939050162"
        assert contato.whatsapp_raw == "wa.me/5511939050162"


class TestVagaAtomica:
    """Testes para VagaAtomica."""

    def test_criacao_minima(self):
        """Cria vaga com campos mínimos obrigatórios."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.TARDE,
            valor=1700,
            hospital_raw="Hospital Campo Limpo"
        )
        assert vaga.data == date(2026, 1, 26)
        assert vaga.valor == 1700
        assert vaga.hospital_raw == "Hospital Campo Limpo"

    def test_criacao_completa(self):
        """Cria vaga com todos os campos."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.TARDE,
            valor=1700,
            hospital_raw="Hospital Campo Limpo",
            hora_inicio=time(13, 0),
            hora_fim=time(19, 0),
            endereco_raw="Estrada Itapecirica, 1661",
            cidade="São Paulo",
            estado="SP",
            especialidade_raw="Clínica Médica",
            contato_nome="Eloisa",
            contato_whatsapp="5511939050162",
            confianca_geral=0.92,
            mensagem_id=uuid4(),
            grupo_id=uuid4()
        )
        assert vaga.hora_inicio == time(13, 0)
        assert vaga.contato_nome == "Eloisa"

    def test_to_dict(self):
        """Testa conversão para dicionário."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.TARDE,
            valor=1700,
            hospital_raw="Hospital ABC",
            hora_inicio=time(13, 0)
        )
        d = vaga.to_dict()

        assert d["data"] == "2026-01-26"
        assert d["dia_semana"] == "segunda"
        assert d["periodo"] == "tarde"
        assert d["valor"] == 1700
        assert d["hora_inicio"] == "13:00:00"
        assert d["hospital_raw"] == "Hospital ABC"


class TestResultadoExtracaoV2:
    """Testes para ResultadoExtracaoV2."""

    def test_sucesso_true(self):
        """Resultado é sucesso quando tem vagas e sem erro."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.TARDE,
            valor=1700,
            hospital_raw="Hospital ABC"
        )
        resultado = ResultadoExtracaoV2(vagas=[vaga], total_vagas=1)

        assert resultado.sucesso is True
        assert resultado.erro is None

    def test_sucesso_false_com_erro(self):
        """Resultado não é sucesso quando tem erro."""
        resultado = ResultadoExtracaoV2(erro="Falha ao processar")
        assert resultado.sucesso is False

    def test_sucesso_false_sem_vagas(self):
        """Resultado não é sucesso quando não tem vagas."""
        resultado = ResultadoExtracaoV2(vagas=[])
        assert resultado.sucesso is False
```

---

## Checklist de Conclusão

### Implementação
- [ ] Criar diretório `app/services/grupos/extrator_v2/`
- [ ] Criar arquivo `types.py` com todos os tipos
- [ ] Criar arquivo `exceptions.py` com exceções
- [ ] Criar arquivo `__init__.py` com exports

### Testes
- [ ] Criar arquivo de testes
- [ ] Rodar `uv run pytest tests/services/grupos/extrator_v2/test_types.py -v`
- [ ] 100% dos testes passando

### Qualidade
- [ ] Rodar `uv run mypy app/services/grupos/extrator_v2/`
- [ ] Zero erros de tipo
- [ ] Rodar `uv run ruff check app/services/grupos/extrator_v2/`
- [ ] Zero erros de lint

---

## Definition of Done (E01)

Este épico está **COMPLETO** quando:

1. ✅ Estrutura de diretórios criada
2. ✅ Todos os tipos definidos em `types.py`
3. ✅ Todas as exceções definidas em `exceptions.py`
4. ✅ Exports em `__init__.py`
5. ✅ 100% dos testes passando
6. ✅ Zero erros de mypy
7. ✅ Zero erros de ruff
