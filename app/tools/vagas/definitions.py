"""
Definicoes de schemas das tools de vagas.

Sprint 58 - E5: Extraido de vagas.py monolitico.
"""

# =============================================================================
# TOOL: BUSCAR VAGAS
# =============================================================================

TOOL_BUSCAR_VAGAS = {
    "name": "buscar_vagas",
    "description": """LISTA vagas de plantao disponiveis. Esta tool apenas MOSTRA opcoes, NAO reserva.

QUANDO USAR:
- Medico pergunta por vagas/plantoes disponiveis
- Medico quer saber o que tem de vaga
- Medico menciona interesse em trabalhar
- Medico pergunta sobre oportunidades

EXEMPLOS DE GATILHO:
- "Tem alguma vaga?"
- "Quais plantoes tem?"
- "To procurando plantao"
- "O que voces tem de vaga?"
- "Tem algo pra essa semana?"
- "Quero ver as vagas"
- "Tem vaga de cardiologia?" (especifica especialidade)

NAO USE ESTA TOOL PARA RESERVAR!
Se o medico quer RESERVAR uma vaga, use 'reservar_plantao' ao inves.

PARAMETROS OPCIONAIS:
- especialidade: Se medico pedir especialidade DIFERENTE da dele (ex: "vagas de cardiologia")
- regiao: Se medico mencionar regiao especifica (ex: "zona sul", "ABC")
- periodo: Se medico pedir turno especifico (diurno, noturno)
- valor_minimo: Se medico mencionar valor minimo aceitavel
- dias_semana: Se medico restringir a dias especificos

DICA: Apos buscar vagas, considere usar 'enviar_opcoes' (ate 3 vagas) ou
'enviar_lista' (ate 10 vagas) para apresentar as opcoes de forma interativa.

NAO use esta tool se:
- Medico ja recusou vagas recentemente
- Medico pediu para parar de mandar vagas
- Contexto indica opt-out""",
    "input_schema": {
        "type": "object",
        "properties": {
            "especialidade": {
                "type": "string",
                "description": "Especialidade solicitada pelo medico (ex: 'cardiologia', 'anestesiologia'). Se nao especificada, usa a especialidade cadastrada do medico.",
            },
            "regiao": {
                "type": "string",
                "description": "Regiao de preferencia do medico (ex: 'zona sul', 'ABC', 'centro'). Extrair da mensagem se mencionado.",
            },
            "periodo": {
                "type": "string",
                "enum": ["diurno", "noturno", "12h", "24h", "qualquer"],
                "description": "Tipo de plantao preferido. Use 'qualquer' se nao especificado.",
            },
            "valor_minimo": {
                "type": "number",
                "description": "Valor minimo do plantao em reais. Extrair se medico mencionar (ex: 'acima de 2000').",
            },
            "dias_semana": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dias preferidos (ex: ['segunda', 'terca']). Deixar vazio para qualquer dia.",
            },
            "limite": {
                "type": "integer",
                "default": 5,
                "description": "Maximo de vagas a retornar (padrao: 5, max: 10).",
            },
        },
        "required": [],
    },
}

# =============================================================================
# TOOL: RESERVAR PLANTAO
# =============================================================================

TOOL_RESERVAR_PLANTAO = {
    "name": "reservar_plantao",
    "description": """RESERVA um plantao/vaga para o medico. Use esta tool para CONFIRMAR uma reserva.

QUANDO USAR:
- Medico pede para RESERVAR uma vaga
- Medico ACEITA uma vaga oferecida
- Medico diz: "Pode reservar", "Quero essa", "Fechado", "Aceito", "Pode ser", "Vou querer"
- Medico pede: "Reserva pra mim", "Quero reservar", "Fecha essa vaga"
- Medico especifica: "Quero a vaga do dia X no hospital Y"

COMO USAR:
- Use o parametro 'data_plantao' com a data no formato YYYY-MM-DD (ex: 2025-12-09)
- A data e OBRIGATORIA e suficiente para identificar a vaga
- Extraia a data da conversa (se medico diz "hoje" use a data atual, se diz "dia 15" use essa data)
- NAO invente IDs - use apenas a data do plantao

IMPORTANTE: Se o medico quer VER vagas antes de reservar, use 'buscar_vagas' primeiro.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_plantao": {
                "type": "string",
                "description": "Data do plantao no formato YYYY-MM-DD (ex: 2025-12-12). OBRIGATORIO.",
            },
            "confirmacao": {
                "type": "string",
                "description": "Breve descricao da confirmacao do medico (ex: 'medico disse pode reservar')",
            },
        },
        "required": ["data_plantao", "confirmacao"],
    },
}

# =============================================================================
# TOOL: BUSCAR INFO HOSPITAL
# =============================================================================

TOOL_BUSCAR_INFO_HOSPITAL = {
    "name": "buscar_info_hospital",
    "description": """Busca informacoes sobre um hospital (endereco, cidade, bairro).

QUANDO USAR:
- Medico pergunta endereco de um hospital
- Medico quer saber onde fica um hospital
- Medico pergunta: "Qual endereco?", "Onde fica?", "Como chego la?"
- Medico menciona nome de hospital e quer mais info

IMPORTANTE: Use esta tool para buscar informacoes do banco. NAO invente enderecos!

PARAMETROS:
- nome_hospital: Nome (ou parte do nome) do hospital a buscar""",
    "input_schema": {
        "type": "object",
        "properties": {
            "nome_hospital": {
                "type": "string",
                "description": "Nome do hospital (ou parte dele) para buscar. Ex: 'Salvalus', 'Santa Casa'",
            }
        },
        "required": ["nome_hospital"],
    },
}

# =============================================================================
# Lista aggregada
# =============================================================================

# Lista de todas as tools de vagas
TOOLS_VAGAS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
]
