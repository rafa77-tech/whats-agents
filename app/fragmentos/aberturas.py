"""
Fragmentos de mensagens de abertura.

Variacoes para evitar que Julia pareca robotica.
Medicos que recebem mensagens identicas percebem padrao.

NOTA: Renomeado de templates para fragmentos (Sprint 32).
"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class FragmentoAbertura:
    """Fragmento de abertura com metadata."""

    id: str
    saudacao: str  # Primeira linha
    apresentacao: str  # Segunda linha (quem sou)
    contexto: Optional[str] = None  # Terceira linha opcional
    periodo: Optional[str] = None  # manha, tarde, noite, qualquer
    dia_semana: Optional[str] = None  # seg, sex, fds, qualquer
    tom: str = "padrao"  # padrao, casual, profissional


# Saudacoes (primeira linha)
# Formato: (id, texto, periodo)
SAUDACOES = [
    ("s1", "Oi Dr {nome}! Tudo bem?", None),
    ("s2", "E ai Dr {nome}, td certo?", None),
    ("s3", "Opa Dr {nome}! Como vai?", None),
    ("s4", "Dr {nome}, tudo tranquilo?", None),
    ("s5", "Oi! Fala Dr {nome}", None),
    ("s6", "Oi Dr {nome}!", None),
    ("s7", "Bom dia Dr {nome}!", "manha"),
    ("s8", "Boa tarde Dr {nome}!", "tarde"),
    ("s9", "Boa noite Dr {nome}!", "noite"),
    ("s10", "E ai Dr {nome}! Tudo joia?", None),
    ("s11", "Oi Dr {nome}, td bem?", None),
    ("s12", "Fala Dr {nome}! Blz?", None),
    ("s13", "Dr {nome}! Tudo certo ai?", None),
    ("s14", "Opa! Dr {nome}, tudo bem?", None),
    ("s15", "Oi Dr {nome}, como vai?", None),
    ("s16", "Hey Dr {nome}!", None),
    ("s17", "Ola Dr {nome}, tudo bom?", None),
    ("s18", "Bom dia, Dr {nome}! Como ta?", "manha"),
    ("s19", "Boa tarde, Dr {nome}! Td certo?", "tarde"),
    ("s20", "Boa noite, Dr {nome}! Tudo bem?", "noite"),
]

# Saudacoes SEM nome (para quando nao temos o nome do medico)
# Formato: (id, texto, periodo)
SAUDACOES_SEM_NOME = [
    ("sn1", "Oi! Tudo bem?", None),
    ("sn2", "E ai, td certo?", None),
    ("sn3", "Opa! Como vai?", None),
    ("sn4", "Oi, tudo tranquilo?", None),
    ("sn5", "Oi!", None),
    ("sn6", "Bom dia!", "manha"),
    ("sn7", "Boa tarde!", "tarde"),
    ("sn8", "Boa noite!", "noite"),
    ("sn9", "E ai! Tudo joia?", None),
    ("sn10", "Oi, td bem?", None),
    ("sn11", "Opa! Blz?", None),
    ("sn12", "Oi! Tudo certo ai?", None),
    ("sn13", "Ola, tudo bom?", None),
    ("sn14", "Bom dia! Como ta?", "manha"),
    ("sn15", "Boa tarde! Td certo?", "tarde"),
    ("sn16", "Boa noite! Tudo bem?", "noite"),
]

# Apresentacoes (segunda linha)
# Formato: (id, texto)
APRESENTACOES = [
    ("a1", "Sou a Julia da Revoluna"),
    ("a2", "Aqui e a Julia, da Revoluna"),
    ("a3", "Julia aqui, da Revoluna"),
    ("a4", "Meu nome e Julia, sou da Revoluna"),
    ("a5", "Sou Julia, escalista da Revoluna"),
    ("a6", "Aqui e Julia da equipe Revoluna"),
    ("a7", "Julia da Revoluna aqui"),
    ("a8", "Oi! Julia da Revoluna"),
    ("a9", "Sou a Julia, da Revoluna"),
    ("a10", "Aqui e a Julia da Revoluna"),
]

# Contextos (terceira linha - o que faz)
# Formato: (id, texto)
CONTEXTOS = [
    ("c1", "Trabalho com escalas medicas aqui na regiao"),
    ("c2", "A gente trabalha com plantoes medicos"),
    ("c3", "Cuido das escalas medicas aqui"),
    ("c4", "Trabalho conectando medicos com plantoes"),
    ("c5", "Ajudo medicos a encontrar plantoes"),
    ("c6", "Trabalho com oportunidades de plantao"),
    ("c7", "Cuido da parte de escalas e plantoes"),
    ("c8", "A Revoluna trabalha com escalas medicas"),
    ("c9", "Trabalho com staffing medico aqui no ABC"),
    ("c10", "Cuido das vagas de plantao aqui na regiao"),
]

# Ganchos (quarta linha - pergunta/interesse)
# Formato: (id, texto)
GANCHOS = [
    ("g1", "Vc ta fazendo plantoes?"),
    ("g2", "Ta aceitando plantao?"),
    ("g3", "Tem interesse em plantoes?"),
    ("g4", "Vc faz plantao avulso?"),
    ("g5", "Ta com disponibilidade pra plantao?"),
    ("g6", "Procurando plantao?"),
    ("g7", "Surgiu umas vagas boas, tem interesse?"),
    ("g8", "Vi umas vagas que podem te interessar"),
    ("g9", "Posso te mostrar algumas oportunidades?"),
    ("g10", "Quer saber das vagas disponiveis?"),
]

# ============================================================================
# FRAGMENTOS SOFT DISCOVERY (sem mencionar plantao na primeira abordagem)
# ============================================================================

# Contextos soft - focados em apresentar a Revoluna sem falar de plantao
CONTEXTOS_SOFT = [
    ("cs1", "Trabalho com escalas medicas aqui na regiao"),
    ("cs2", "A Revoluna conecta medicos com hospitais"),
    ("cs3", "A gente trabalha com staffing medico"),
    ("cs4", "Somos uma empresa de staffing medico"),
    ("cs5", "Trabalho na area de escalas hospitalares"),
    ("cs6", "A Revoluna e especializada em staffing"),
    ("cs7", "Trabalho conectando medicos com oportunidades"),
    ("cs8", "A gente ajuda medicos na regiao do ABC"),
]

# Ganchos soft - perguntas de descoberta sem mencionar plantao
GANCHOS_SOFT = [
    ("gs1", "Posso te contar mais sobre a gente?"),
    ("gs2", "Vc conhece a Revoluna?"),
    ("gs3", "Ja ouviu falar da gente?"),
    ("gs4", "Posso te apresentar nosso trabalho?"),
    ("gs5", "Quer saber como a gente funciona?"),
    ("gs6", "Conhece nosso modelo de trabalho?"),
    ("gs7", "Posso te explicar o que fazemos?"),
    ("gs8", "Ta aberto a conhecer a Revoluna?"),
]


def montar_abertura_completa(
    nome: str,
    saudacao_id: str = None,
    apresentacao_id: str = None,
    contexto_id: str = None,
    gancho_id: str = None,
    incluir_contexto: bool = None,
    soft: bool = False,
) -> list[str]:
    """
    Monta abertura completa com IDs especificos ou aleatorios.

    Args:
        nome: Nome do medico (pode ser None/vazio para contatos sem nome)
        saudacao_id: ID da saudacao (ou None para aleatorio)
        apresentacao_id: ID da apresentacao
        contexto_id: ID do contexto
        gancho_id: ID do gancho
        incluir_contexto: Incluir linha de contexto (None = 70% chance)
        soft: Se True, usa fragmentos soft (sem mencionar plantao)

    Returns:
        Lista de strings (cada uma e uma mensagem separada)
    """
    mensagens = []

    # Selecionar listas de contexto e gancho baseado no modo
    lista_contextos = CONTEXTOS_SOFT if soft else CONTEXTOS
    lista_ganchos = GANCHOS_SOFT if soft else GANCHOS

    # Verificar se temos nome valido
    tem_nome = nome and nome.strip() and nome.strip().lower() not in ("none", "null", "")

    # Saudacao - usar versao sem nome se nao temos nome
    if tem_nome:
        if saudacao_id:
            saudacao = next((s for s in SAUDACOES if s[0] == saudacao_id), None)
        else:
            saudacao = random.choice(SAUDACOES)
        if saudacao:
            mensagens.append(saudacao[1].format(nome=nome.strip()))
    else:
        # Usar saudacao sem nome
        if saudacao_id and saudacao_id.startswith("sn"):
            saudacao = next((s for s in SAUDACOES_SEM_NOME if s[0] == saudacao_id), None)
        else:
            saudacao = random.choice(SAUDACOES_SEM_NOME)
        if saudacao:
            mensagens.append(saudacao[1])

    # Apresentacao
    if apresentacao_id:
        apresentacao = next((a for a in APRESENTACOES if a[0] == apresentacao_id), None)
    else:
        apresentacao = random.choice(APRESENTACOES)

    if apresentacao:
        mensagens.append(apresentacao[1])

    # Contexto (opcional - 70% das vezes se nao especificado)
    if incluir_contexto is None:
        incluir_contexto = random.random() < 0.7

    if incluir_contexto:
        if contexto_id:
            contexto = next((c for c in lista_contextos if c[0] == contexto_id), None)
        else:
            contexto = random.choice(lista_contextos)

        if contexto:
            mensagens.append(contexto[1])

    # Gancho (sempre)
    if gancho_id:
        gancho = next((g for g in lista_ganchos if g[0] == gancho_id), None)
    else:
        gancho = random.choice(lista_ganchos)

    if gancho:
        mensagens.append(gancho[1])

    return mensagens


def gerar_abertura_texto_unico(
    nome: str,
    saudacao_id: str = None,
    apresentacao_id: str = None,
    contexto_id: str = None,
    gancho_id: str = None,
    soft: bool = False,
) -> str:
    """
    Gera abertura como texto unico (para envio em uma so mensagem).

    Args:
        nome: Nome do medico
        saudacao_id: ID da saudacao
        apresentacao_id: ID da apresentacao
        contexto_id: ID do contexto
        gancho_id: ID do gancho
        soft: Se True, usa fragmentos soft (sem mencionar plantao)

    Returns:
        String com abertura completa separada por quebras de linha
    """
    mensagens = montar_abertura_completa(
        nome=nome,
        saudacao_id=saudacao_id,
        apresentacao_id=apresentacao_id,
        contexto_id=contexto_id,
        gancho_id=gancho_id,
        soft=soft,
    )
    return "\n\n".join(mensagens)


def obter_saudacao_por_periodo(periodo: str) -> list:
    """
    Retorna saudacoes filtradas por periodo.

    Args:
        periodo: manha, tarde, noite ou None para todas

    Returns:
        Lista de saudacoes compativeis
    """
    if periodo is None:
        return SAUDACOES

    return [s for s in SAUDACOES if s[2] == periodo or s[2] is None]


def contar_variacoes() -> dict:
    """
    Conta total de variacoes possiveis.

    Returns:
        Dicionario com contagens
    """
    return {
        "saudacoes": len(SAUDACOES),
        "apresentacoes": len(APRESENTACOES),
        "contextos": len(CONTEXTOS),
        "ganchos": len(GANCHOS),
        "combinacoes_possiveis": (
            len(SAUDACOES)
            * len(APRESENTACOES)
            * (len(CONTEXTOS) + 1)  # +1 para "sem contexto"
            * len(GANCHOS)
        ),
    }
