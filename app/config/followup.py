"""
Configurações de follow-up automático.
"""
from typing import Dict, List

REGRAS_FOLLOWUP: Dict[str, Dict] = {
    "primeiro_contato": {
        "dias_ate_followup": 3,
        "max_followups": 2,
        "mensagens": [
            "Oi {nome}! Vi que mandei msg outro dia mas não deu pra gente conversar. Ainda tem interesse em plantão?",
            "E aí {nome}, tudo bem? Só passando pra ver se conseguiu ver as vagas que te mandei. Qualquer coisa só falar!",
        ]
    },
    "pos_interesse": {
        "dias_ate_followup": 1,
        "max_followups": 1,
        "mensagens": [
            "Oi {nome}! Então, conseguiu pensar sobre aquela vaga? To aqui se precisar de mais info!",
        ]
    },
    "pos_oferta": {
        "dias_ate_followup": 2,
        "max_followups": 1,
        "mensagens": [
            "{nome}, a vaga que te ofereci ainda tá aberta! Se tiver interesse me avisa que reservo pra vc",
        ]
    },
}

