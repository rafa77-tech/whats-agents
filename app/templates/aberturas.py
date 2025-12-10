"""
Templates de mensagens de abertura.

Variacoes para evitar que Julia pareca robotica.
Medicos que recebem mensagens identicas percebem padrao.
"""
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class TemplateAbertura:
    """Template de abertura com metadata."""
    id: str
    saudacao: str                   # Primeira linha
    apresentacao: str               # Segunda linha (quem sou)
    contexto: Optional[str] = None  # Terceira linha opcional
    periodo: Optional[str] = None   # manha, tarde, noite, qualquer
    dia_semana: Optional[str] = None  # seg, sex, fds, qualquer
    tom: str = "padrao"             # padrao, casual, profissional


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


def montar_abertura_completa(
    nome: str,
    saudacao_id: str = None,
    apresentacao_id: str = None,
    contexto_id: str = None,
    gancho_id: str = None,
    incluir_contexto: bool = None
) -> list[str]:
    """
    Monta abertura completa com IDs especificos ou aleatorios.

    Args:
        nome: Nome do medico
        saudacao_id: ID da saudacao (ou None para aleatorio)
        apresentacao_id: ID da apresentacao
        contexto_id: ID do contexto
        gancho_id: ID do gancho
        incluir_contexto: Incluir linha de contexto (None = 70% chance)

    Returns:
        Lista de strings (cada uma e uma mensagem separada)
    """
    mensagens = []

    # Saudacao
    if saudacao_id:
        saudacao = next((s for s in SAUDACOES if s[0] == saudacao_id), None)
    else:
        saudacao = random.choice(SAUDACOES)

    if saudacao:
        mensagens.append(saudacao[1].format(nome=nome))

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
            contexto = next((c for c in CONTEXTOS if c[0] == contexto_id), None)
        else:
            contexto = random.choice(CONTEXTOS)

        if contexto:
            mensagens.append(contexto[1])

    # Gancho (sempre)
    if gancho_id:
        gancho = next((g for g in GANCHOS if g[0] == gancho_id), None)
    else:
        gancho = random.choice(GANCHOS)

    if gancho:
        mensagens.append(gancho[1])

    return mensagens


def gerar_abertura_texto_unico(
    nome: str,
    saudacao_id: str = None,
    apresentacao_id: str = None,
    contexto_id: str = None,
    gancho_id: str = None
) -> str:
    """
    Gera abertura como texto unico (para envio em uma so mensagem).

    Args:
        nome: Nome do medico
        saudacao_id: ID da saudacao
        apresentacao_id: ID da apresentacao
        contexto_id: ID do contexto
        gancho_id: ID do gancho

    Returns:
        String com abertura completa separada por quebras de linha
    """
    mensagens = montar_abertura_completa(
        nome=nome,
        saudacao_id=saudacao_id,
        apresentacao_id=apresentacao_id,
        contexto_id=contexto_id,
        gancho_id=gancho_id
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
            len(SAUDACOES) *
            len(APRESENTACOES) *
            (len(CONTEXTOS) + 1) *  # +1 para "sem contexto"
            len(GANCHOS)
        )
    }
