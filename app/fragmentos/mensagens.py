"""
Fragmentos de mensagens para campanhas.

NOTA: Renomeado de templates para fragmentos (Sprint 32).
"""
from typing import Optional
from app.config.especialidades import obter_config_especialidade


MENSAGEM_PRIMEIRO_CONTATO = """Oi Dr(a) {nome}! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas aqui no ABC

{saudacao_especialidade}

Posso te contar mais?"""


SAUDACOES_ESPECIALIDADE = {
    "anestesiologia": "Vi que vc é anestesista, certo? Temos umas vagas bem interessantes em centro cirúrgico",
    "cardiologia": "Vi que vc é cardio, certo? Temos vagas em UTI e emergência que podem te interessar",
    "clinica_medica": "Vi que vc é clínico, né? Sempre tem vaga boa de PS e enfermaria",
    "pediatria": "Vi que vc é pediatra! Temos vagas legais em PS pediátrico e maternidade",
    "ortopedia": "Vi que vc é ortopedista! Sempre surge vaga boa de trauma e centro cirúrgico",
}


def obter_saudacao_especialidade(especialidade: str) -> str:
    """
    Retorna saudação personalizada para especialidade.

    Args:
        especialidade: Nome da especialidade

    Returns:
        Saudação personalizada ou padrão
    """
    if not especialidade:
        return "Vi que você é médico, certo? Temos umas vagas interessantes essa semana"

    nome_normalizado = especialidade.lower().replace(" ", "_").strip()
    return SAUDACOES_ESPECIALIDADE.get(
        nome_normalizado,
        f"Vi que vc é {especialidade.lower()}, certo? Temos umas vagas bem interessantes essa semana"
    )


def formatar_primeiro_contato(medico: dict) -> str:
    """Formata mensagem de primeiro contato."""
    nome = medico.get("primeiro_nome", "")
    especialidade_nome = medico.get("especialidade_nome", "")

    # Se não tiver especialidade_nome, buscar da relação
    if not especialidade_nome and medico.get("especialidade_id"):
        # Tentar buscar nome da especialidade
        # Por enquanto, usar valor padrão
        especialidade_nome = "médico"

    saudacao = obter_saudacao_especialidade(especialidade_nome)

    return MENSAGEM_PRIMEIRO_CONTATO.format(
        nome=nome,
        saudacao_especialidade=saudacao
    )
