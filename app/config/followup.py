"""
Configuracoes de follow-up automatico.

Cadencia documentada em docs/FLUXOS.md:
  Abertura -> 48h -> Follow-up 1
           -> 5d  -> Follow-up 2 (com vaga)
           -> 15d -> Follow-up 3 (ultimo)
           -> stage 'nao_respondeu' + pausa 60 dias
"""
from datetime import timedelta
from typing import Dict, List


# =============================================================================
# CONFIGURACAO DE CADENCIA (conforme docs/FLUXOS.md)
# =============================================================================

FOLLOWUP_CONFIG: Dict[str, Dict] = {
    # Follow-up 1: 48 horas apos ultima mensagem
    "followup_1": {
        "delay": timedelta(hours=48),
        "stage_anterior": "msg_enviada",  # Apos mensagem inicial
        "stage_proximo": "followup_1_enviado",
        "tipo_mensagem": "lembrete_simples",
        "incluir_vaga": False,
        "template_hint": "Oi de novo! Viu minha msg?"
    },

    # Follow-up 2: 5 dias apos follow-up 1
    "followup_2": {
        "delay": timedelta(days=5),
        "stage_anterior": "followup_1_enviado",
        "stage_proximo": "followup_2_enviado",
        "tipo_mensagem": "oferta_vaga",
        "incluir_vaga": True,  # IMPORTANTE: Inclui vaga real
        "template_hint": "Lembrei de vc pq surgiu uma vaga boa..."
    },

    # Follow-up 3 (ultimo): 15 dias apos follow-up 2
    "followup_3": {
        "delay": timedelta(days=15),
        "stage_anterior": "followup_2_enviado",
        "stage_proximo": "nao_respondeu",
        "tipo_mensagem": "ultima_tentativa",
        "incluir_vaga": False,
        "template_hint": "Ultima msg, prometo! Se nao tiver interesse..."
    }
}


# Pausa apos esgotar follow-ups (60 dias conforme docs/FLUXOS.md)
PAUSA_APOS_NAO_RESPOSTA = timedelta(days=60)


# =============================================================================
# STAGES DE CONVERSA
# =============================================================================

# Stages que indicam que conversa esta ativa (nao fazer follow-up)
STAGES_ATIVOS = [
    "respondeu",
    "qualificado",
    "negociando",
    "fechou",
    "optout"
]

# Stages elegiveis para follow-up
STAGES_FOLLOWUP = [
    "msg_enviada",
    "followup_1_enviado",
    "followup_2_enviado"
]

# Stage apos pausa expirar (para recontato)
STAGE_RECONTATO = "recontato"


# =============================================================================
# TEMPLATES DE MENSAGENS (variados para parecer natural)
# =============================================================================

TEMPLATES_FOLLOWUP = {
    "followup_1": [
        "Oi {nome}! Tudo bem?\n\nMandei uma msg outro dia, nao sei se vc viu",
        "Oi de novo {nome}!\n\nViu minha msg? To com vagas legais aqui",
        "E ai {nome}! Sumiu rs\n\nAinda tenho vagas boas, se tiver interesse"
    ],
    "followup_2": [
        "Oi {nome}!\n\nLembrei de vc pq surgiu uma vaga boa\n\n{vaga_info}\n\nTem interesse?",
        "{nome}, achei uma vaga que combina com vc\n\n{vaga_info}\n\nO que acha?",
        "E ai {nome}! Tava olhando as vagas aqui e lembrei de vc\n\n{vaga_info}\n\nBora?"
    ],
    "followup_3": [
        "Oi {nome}! Ultima msg, prometo rs\n\nSe nao tiver interesse em plantoes agora, sem problema!\n\nMas se quiser, e so me chamar",
        "{nome}, vou parar de insistir rs\n\nSe mudar de ideia sobre plantoes, to aqui!",
        "Oi {nome}, to passando pra ultima vez\n\nSe nao for o momento, entendo. Qualquer hora que precisar e so chamar!"
    ]
}


# =============================================================================
# CONFIGURACAO LEGADA (para compatibilidade)
# =============================================================================

# Mantendo a estrutura antiga para nao quebrar codigo existente
REGRAS_FOLLOWUP: Dict[str, Dict] = {
    "primeiro_contato": {
        "dias_ate_followup": 2,  # 48h = 2 dias
        "max_followups": 3,
        "mensagens": TEMPLATES_FOLLOWUP["followup_1"]
    },
    "pos_interesse": {
        "dias_ate_followup": 1,
        "max_followups": 1,
        "mensagens": [
            "Oi {nome}! Entao, conseguiu pensar sobre aquela vaga? To aqui se precisar de mais info!",
        ]
    },
    "pos_oferta": {
        "dias_ate_followup": 2,
        "max_followups": 1,
        "mensagens": [
            "{nome}, a vaga que te ofereci ainda ta aberta! Se tiver interesse me avisa que reservo pra vc",
        ]
    },
}
