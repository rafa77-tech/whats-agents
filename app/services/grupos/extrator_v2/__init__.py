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

from .parser_mensagem import parsear_mensagem, MensagemParsed, TipoSecao, LinhaParsed

from .extrator_hospitais import extrair_hospitais, extrair_hospitais_llm

from .extrator_datas import extrair_datas_periodos, extrair_data_periodo

from .extrator_valores import extrair_valores, obter_valor_para_dia

from .extrator_contato import extrair_contato

from .gerador_vagas import gerar_vagas, gerar_vagas_para_hospital, validar_vagas, deduplicar_vagas

from .pipeline import extrair_vagas_v2

from .repository import salvar_vagas_atomicas, atualizar_mensagem_processada

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
    # Parser
    "parsear_mensagem",
    "MensagemParsed",
    "TipoSecao",
    "LinhaParsed",
    # Extratores
    "extrair_hospitais",
    "extrair_hospitais_llm",
    "extrair_datas_periodos",
    "extrair_data_periodo",
    "extrair_valores",
    "obter_valor_para_dia",
    "extrair_contato",
    # Gerador
    "gerar_vagas",
    "gerar_vagas_para_hospital",
    "validar_vagas",
    "deduplicar_vagas",
    # Pipeline (função principal)
    "extrair_vagas_v2",
    # Persistência
    "salvar_vagas_atomicas",
    "atualizar_mensagem_processada",
]
