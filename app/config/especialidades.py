"""
Configurações por especialidade médica.
"""

from typing import Dict

CONFIGURACOES_ESPECIALIDADE: Dict[str, Dict] = {
    "anestesiologia": {
        "nome_display": "anestesista",
        "tipo_plantao": ["cirúrgico", "obstétrico", "UTI"],
        "valor_medio": "R$ 2.000 - R$ 3.500",
        "vocabulario": {
            "procedimentos": ["anestesia geral", "raqui", "peridural"],
            "setores": ["centro cirúrgico", "sala de parto", "UTI"],
        },
        "contexto_extra": "Anestesistas geralmente preferem plantões de 12h ou 24h.",
    },
    "cardiologia": {
        "nome_display": "cardiologista",
        "tipo_plantao": ["emergência", "UTI coronariana", "consultório"],
        "valor_medio": "R$ 1.800 - R$ 3.000",
        "vocabulario": {
            "procedimentos": ["eco", "eletro", "cateterismo"],
            "setores": ["UTI cardio", "emergência", "hemodinâmica"],
        },
        "contexto_extra": "Cardiologistas têm alta demanda em UTIs e emergências.",
    },
    "clinica_medica": {
        "nome_display": "clínico",
        "tipo_plantao": ["PS", "enfermaria", "UTI"],
        "valor_medio": "R$ 1.200 - R$ 2.000",
        "vocabulario": {
            "procedimentos": ["prescrição", "evolução", "alta"],
            "setores": ["PS", "enfermaria", "UTI geral"],
        },
        "contexto_extra": "Clínicos são muito requisitados em PS e enfermarias.",
    },
    "pediatria": {
        "nome_display": "pediatra",
        "tipo_plantao": ["PS pediátrico", "UTI neo", "berçário"],
        "valor_medio": "R$ 1.500 - R$ 2.500",
        "vocabulario": {
            "procedimentos": ["puericultura", "emergência pediátrica"],
            "setores": ["PS pediátrico", "UTI neo", "alojamento conjunto"],
        },
        "contexto_extra": "Pediatras têm alta demanda em maternidades.",
    },
    "ortopedia": {
        "nome_display": "ortopedista",
        "tipo_plantao": ["emergência", "centro cirúrgico", "ambulatório"],
        "valor_medio": "R$ 1.800 - R$ 3.000",
        "vocabulario": {
            "procedimentos": ["redução", "imobilização", "cirurgia"],
            "setores": ["ortopedia", "trauma", "centro cirúrgico"],
        },
        "contexto_extra": "Ortopedistas são muito procurados para trauma.",
    },
}


def obter_config_especialidade(especialidade_nome: str) -> Dict:
    """
    Retorna configuração da especialidade.

    Args:
        especialidade_nome: Nome da especialidade (ex: "Anestesiologia", "anestesiologia")

    Returns:
        Dict com configuração ou dict vazio se não encontrada
    """
    if not especialidade_nome:
        return {}

    nome_normalizado = especialidade_nome.lower().replace(" ", "_").strip()
    return CONFIGURACOES_ESPECIALIDADE.get(nome_normalizado, {})


def listar_especialidades_configuradas() -> list[str]:
    """Retorna lista de especialidades com configuração."""
    return list(CONFIGURACOES_ESPECIALIDADE.keys())
