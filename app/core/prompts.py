"""
Prompts do sistema para o agente Julia.

Este arquivo mantem funcoes de compatibilidade que internamente
usam o novo sistema de prompts dinamicos do banco.
"""
from app.prompts.builder import construir_prompt_julia as _construir_prompt

# Constantes legadas (mantidas para fallback)
JULIA_PROMPT_PRIMEIRA_MSG = """
Esta e a PRIMEIRA interacao com este medico. Voce esta fazendo prospeccao.
- Se apresente brevemente
- Mencione que trabalha com escalas medicas
- Pergunte se ele esta fazendo plantoes ou tem interesse
- Seja natural, nao pareca roteiro
"""

JULIA_PROMPT_CONTINUACAO = """
Esta e uma conversa em andamento.
- Continue naturalmente de onde parou
- Responda o que o medico perguntou/disse
- Se ele mostrou interesse, ofereca detalhes ou vaga
"""

JULIA_PROMPT_OPT_OUT = """
O medico pediu para NAO receber mais mensagens.
- Respeite imediatamente
- Peca desculpas pelo incomodo
- Confirme que ele foi removido da lista
- Seja breve e educada
"""

JULIA_PROMPT_RETORNO_HANDOFF = """
IMPORTANTE: Esta conversa acabou de voltar do atendimento humano.
- Retome de forma NATURAL, como se nada tivesse acontecido
- NAO mencione "minha supervisora", "equipe", ou que alguem assumiu
- NAO peca desculpas pelo que aconteceu antes
- Continue a conversa normalmente, perguntando como pode ajudar
- Se o medico mencionar o atendimento anterior, seja breve e mude de assunto
"""

JULIA_PROMPT_ABERTURA_JA_ENVIADA = """
IMPORTANTE: A mensagem de abertura JA FOI ENVIADA pelo sistema.
Voce NAO precisa se apresentar novamente.

A abertura que foi enviada incluiu:
- Saudacao (Oi Dr Nome)
- Apresentacao (Julia da Revoluna)
- Contexto (escalas medicas)
- Pergunta de interesse (sobre plantoes)

Sua tarefa e CONTINUAR a conversa a partir da resposta do medico.
NAO repita a apresentacao.
NAO diga "Oi, sou a Julia" novamente.
"""


async def montar_prompt_julia(
    contexto_medico: str = "",
    contexto_vagas: str = "",
    historico: str = "",
    primeira_msg: bool = False,
    data_hora_atual: str = "",
    dia_semana: str = "",
    contexto_especialidade: str = "",
    contexto_handoff: str = "",
    contexto_memorias: str = "",
    especialidade_id: str = None,
    diretrizes: str = "",
    abertura_ja_enviada: bool = False,
    conhecimento: str = "",  # E03: Conhecimento dinâmico RAG
) -> str:
    """
    Monta o system prompt completo para a Julia.

    Agora usa o builder dinamico que carrega prompts do banco.

    Args:
        contexto_medico: Info sobre o medico (nome, especialidade, etc)
        contexto_vagas: Vagas disponiveis relevantes
        historico: Historico recente da conversa
        primeira_msg: Se e primeira interacao
        data_hora_atual: Data/hora atual (YYYY-MM-DD HH:MM)
        dia_semana: Dia da semana atual
        contexto_especialidade: Info da especialidade do medico
        contexto_handoff: Info sobre handoff recente (se houver)
        contexto_memorias: Memorias RAG relevantes (Sprint 8)
        especialidade_id: ID da especialidade para prompt especifico
        diretrizes: Diretrizes do gestor
        abertura_ja_enviada: Se a abertura automatica ja foi enviada
        conhecimento: Conhecimento dinamico do orquestrador (E03)

    Returns:
        System prompt formatado
    """
    # Montar contexto dinamico
    contexto_parts = []

    if data_hora_atual:
        contexto_parts.append(f"DATA/HORA ATUAL: {data_hora_atual} ({dia_semana})")

    if contexto_medico:
        contexto_parts.append(f"SOBRE O MEDICO:\n{contexto_medico}")

    if contexto_especialidade:
        contexto_parts.append(f"INFORMACOES DA ESPECIALIDADE:\n{contexto_especialidade}")

    if contexto_vagas:
        contexto_parts.append(f"VAGAS DISPONIVEIS:\n{contexto_vagas}")

    if historico:
        contexto_parts.append(f"HISTORICO RECENTE:\n{historico}")

    if contexto_handoff:
        contexto_parts.append(f"HANDOFF RECENTE:\n{contexto_handoff}")
        contexto_parts.append(JULIA_PROMPT_RETORNO_HANDOFF)

    # Se abertura ja foi enviada pelo sistema, instruir a nao repetir
    if abertura_ja_enviada:
        contexto_parts.append(JULIA_PROMPT_ABERTURA_JA_ENVIADA)

    contexto = "\n\n".join(contexto_parts) if contexto_parts else ""

    # Usar builder dinamico
    return await _construir_prompt(
        especialidade_id=especialidade_id,
        diretrizes=diretrizes,
        contexto=contexto,
        memorias=contexto_memorias,
        conhecimento=conhecimento,
        primeira_msg=primeira_msg,
    )
