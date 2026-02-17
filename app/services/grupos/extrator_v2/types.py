"""
Tipos e dataclasses para o extrator de vagas v2.

Sprint 40 - E01: Estrutura e Tipos
"""

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from typing import List, Optional
from uuid import UUID


# =============================================================================
# Enums
# =============================================================================


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

    MANHA = "manha"  # Geralmente 07:00-13:00
    TARDE = "tarde"  # Geralmente 13:00-19:00
    NOITE = "noite"  # Geralmente 19:00-07:00
    DIURNO = "diurno"  # SD - 12h de dia (07:00-19:00)
    NOTURNO = "noturno"  # SN - 12h de noite (19:00-07:00)
    CINDERELA = "cinderela"  # Geralmente 19:00-01:00


class GrupoDia(str, Enum):
    """Grupo de dias para associação de valor."""

    SEG_SEX = "seg_sex"  # Segunda a Sexta
    SAB_DOM = "sab_dom"  # Sábado e Domingo
    SAB = "sabado"  # Apenas Sábado
    DOM = "domingo"  # Apenas Domingo
    FERIADO = "feriado"  # Feriados
    TODOS = "todos"  # Todos os dias (mesmo valor)


# =============================================================================
# Dataclasses de Entrada (Extração)
# =============================================================================


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


# =============================================================================
# Dataclass de Saída (Vaga Atômica)
# =============================================================================


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
    valor: int  # Valor em reais (inteiro), 0 = não informado
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

    # Multiplicidade
    numero_vagas: int = 1  # Quantidade de posicoes identicas (default 1)

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
            "numero_vagas": self.numero_vagas,
            "confianca_geral": self.confianca_geral,
            "observacoes": self.observacoes,
            "mensagem_id": str(self.mensagem_id) if self.mensagem_id else None,
            "grupo_id": str(self.grupo_id) if self.grupo_id else None,
        }


# =============================================================================
# Dataclass de Resultado
# =============================================================================


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
