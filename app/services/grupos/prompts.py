"""
Prompts para classificação de mensagens de grupos.

Sprint 14 - E04 - S04.1
"""

PROMPT_CLASSIFICACAO = """
Você é um classificador de mensagens de grupos de WhatsApp de staffing médico.

Sua tarefa: Determinar se a mensagem é uma OFERTA DE PLANTÃO/VAGA MÉDICA.

CONSIDERA OFERTA DE PLANTÃO:
- Anúncio de vaga/plantão disponível
- Lista de escalas disponíveis
- Cobertura urgente sendo oferecida
- Hospital/clínica buscando médico para data específica

NÃO CONSIDERA OFERTA:
- Perguntas sobre vagas ("alguém tem vaga?")
- Cumprimentos e conversas sociais
- Médicos se oferecendo para trabalhar
- Discussões sobre valores de mercado
- Regras do grupo

MENSAGEM:
{texto}

CONTEXTO:
- Grupo: {nome_grupo}
- Enviado por: {nome_contato}

Responda APENAS com JSON:
{{"eh_oferta": true/false, "confianca": 0.0-1.0, "motivo": "explicação breve"}}
"""


EXEMPLOS_CLASSIFICACAO = [
    {
        "texto": "Bom dia pessoal!",
        "resposta": {"eh_oferta": False, "confianca": 0.99, "motivo": "Cumprimento"}
    },
    {
        "texto": "🚨 URGENTE - Plantão disponível Hospital São Luiz, CM, 28/12 noturno, R$ 1800 PJ",
        "resposta": {"eh_oferta": True, "confianca": 0.98, "motivo": "Oferta completa com hospital, especialidade, data e valor"}
    },
    {
        "texto": "Alguém sabe se tem vaga de cardio essa semana?",
        "resposta": {"eh_oferta": False, "confianca": 0.95, "motivo": "Pergunta sobre vaga, não oferta"}
    },
    {
        "texto": "Preciso de CM pro PS Central amanhã, pago 2k",
        "resposta": {"eh_oferta": True, "confianca": 0.92, "motivo": "Oferta informal mas com dados de vaga"}
    },
    {
        "texto": "Sou pediatra com disponibilidade, alguém contrata?",
        "resposta": {"eh_oferta": False, "confianca": 0.90, "motivo": "Médico se oferecendo, não oferta de vaga"}
    },
]
