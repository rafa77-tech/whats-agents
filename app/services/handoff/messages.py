"""
Mensagens de transicao para handoff.

Sprint 10 - S10.E3.4
"""

import random

# Mensagens de transicao para cada tipo de handoff
MENSAGENS_TRANSICAO = {
    "pedido_humano": [
        "Claro! Vou pedir pra minha supervisora te ajudar, ela eh otima",
        "Entendi! Vou chamar alguem da equipe pra falar com vc",
        "Sem problema! Ja to passando pro pessoal aqui",
    ],
    "juridico": [
        "Opa, esse assunto eh mais delicado, vou passar pra minha supervisora que entende melhor",
        "Entendi a situacao. Vou pedir pra alguem mais experiente te ajudar, ok?",
    ],
    "sentimento_negativo": [
        "Entendo sua frustracao, vou chamar minha supervisora pra resolver isso da melhor forma",
        "Desculpa por qualquer inconveniente. Vou passar pro pessoal resolver pra vc",
    ],
    "baixa_confianca": [
        "Hmm, deixa eu confirmar uma coisa com o pessoal aqui. Ja volto!",
        "Boa pergunta! Vou checar com a equipe e te retorno",
    ],
    "manual": [
        "Oi! Minha supervisora vai continuar o atendimento, ta?",
    ],
}


def obter_mensagem_transicao(tipo: str) -> str:
    """
    Retorna mensagem de transicao apropriada para o tipo de handoff.

    Args:
        tipo: Tipo do trigger (pedido_humano, juridico, etc)

    Returns:
        Mensagem de transicao
    """
    mensagens = MENSAGENS_TRANSICAO.get(tipo, MENSAGENS_TRANSICAO["manual"])
    return random.choice(mensagens)
