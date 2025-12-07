"""
Casos de teste base para validação de persona.
"""

CASOS_TESTE = {
    "saudacao": [
        {"mensagem": "Oi", "contexto": {"medico": {"primeiro_nome": "Carlos"}}},
        {"mensagem": "Olá, boa tarde", "contexto": {}},
        {"mensagem": "Opa", "contexto": {}},
    ],
    "interesse_vaga": [
        {"mensagem": "Tenho interesse em plantão", "contexto": {"vagas": []}},
        {"mensagem": "Tô procurando vaga de cardio", "contexto": {}},
        {"mensagem": "Vocês tem algo pro fim de semana?", "contexto": {}},
    ],
    "duvidas": [
        {"mensagem": "Como funciona o pagamento?", "contexto": {}},
        {"mensagem": "Qual o valor médio?", "contexto": {}},
        {"mensagem": "Precisa de documentação?", "contexto": {}},
    ],
    "negociacao": [
        {"mensagem": "Tá muito baixo esse valor", "contexto": {}},
        {"mensagem": "Consigo R$ 3000?", "contexto": {}},
        {"mensagem": "Outro lugar paga mais", "contexto": {}},
    ],
}

