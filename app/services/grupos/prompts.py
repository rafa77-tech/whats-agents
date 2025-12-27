"""
Prompts para processamento de mensagens de grupos.

Sprint 14 - E04/E05
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


# =============================================================================
# E05 - Prompt de Extração de Dados
# =============================================================================

PROMPT_EXTRACAO = """
Você é um extrator de dados de ofertas de plantão médico.
Analise a mensagem e extraia os dados estruturados de TODAS as vagas mencionadas.

IMPORTANTE:
- Uma mensagem pode conter MÚLTIPLAS vagas (ex: lista de escalas)
- Retorne um ARRAY de vagas, mesmo que seja apenas uma
- Se um campo não puder ser extraído, use null
- Inclua score de confiança (0-1) para cada campo

Data de hoje: {data_hoje}

CAMPOS A EXTRAIR:
- hospital: Nome do hospital/clínica/UPA
- especialidade: Especialidade médica requerida
- data: Data no formato YYYY-MM-DD
- hora_inicio: Horário de início HH:MM
- hora_fim: Horário de fim HH:MM
- valor: Valor em reais (apenas número, sem centavos)
- periodo: Um de [Diurno, Vespertino, Noturno, Cinderela]
- setor: Um de [Pronto atendimento, RPA, Hospital, C. Cirúrgico, SADT]
- tipo_vaga: Um de [Cobertura, Fixo, Ambulatorial, Mensal]
- forma_pagamento: Um de [Pessoa fisica, Pessoa jurídica, CLT, SCP]
- observacoes: Outras informações relevantes

REGRAS:
1. Se a data for ANTERIOR a hoje, marque "data_valida": false
2. Se não conseguir identificar hospital OU especialidade, não inclua a vaga
3. "Amanhã" = {data_amanha}, "hoje" = {data_hoje}
4. Dias da semana devem ser convertidos para a data correta

MENSAGEM:
{texto}

CONTEXTO:
- Grupo: {nome_grupo}
- Região do grupo: {regiao_grupo}
- Quem postou: {nome_contato}

Responda APENAS com JSON no formato:
{{
  "vagas": [
    {{
      "dados": {{
        "hospital": "Hospital São Luiz ABC",
        "especialidade": "Clínica Médica",
        "data": "2024-12-28",
        "hora_inicio": "19:00",
        "hora_fim": "07:00",
        "valor": 1800,
        "periodo": "Noturno",
        "setor": "Pronto atendimento",
        "tipo_vaga": "Cobertura",
        "forma_pagamento": "Pessoa jurídica",
        "observacoes": "Necessário RQE"
      }},
      "confianca": {{
        "hospital": 0.95,
        "especialidade": 0.90,
        "data": 1.0,
        "hora_inicio": 0.95,
        "hora_fim": 0.95,
        "valor": 0.90
      }},
      "data_valida": true
    }}
  ],
  "total_vagas": 1
}}
"""
