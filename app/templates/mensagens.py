"""
Templates de mensagens para campanhas.
"""
from typing import Optional


MENSAGEM_PRIMEIRO_CONTATO = """Oi Dr(a) {nome}! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas aqui no ABC

Vi que vc é {especialidade}, certo? Temos umas vagas bem interessantes essa semana

Posso te contar mais?"""


def formatar_primeiro_contato(medico: dict) -> str:
    """Formata mensagem de primeiro contato."""
    nome = medico.get("primeiro_nome", "")
    especialidade_nome = medico.get("especialidade_nome", "")
    
    # Se não tiver especialidade_nome, buscar da relação
    if not especialidade_nome and medico.get("especialidade_id"):
        # Tentar buscar nome da especialidade
        # Por enquanto, usar valor padrão
        especialidade_nome = "médico"
    
    especialidade = especialidade_nome.lower() if especialidade_nome else "médico"

    return MENSAGEM_PRIMEIRO_CONTATO.format(
        nome=nome,
        especialidade=especialidade
    )

