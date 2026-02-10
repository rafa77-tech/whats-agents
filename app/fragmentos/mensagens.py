"""
Fragmentos de mensagens para campanhas.

NOTA: Renomeado de templates para fragmentos (Sprint 32).
"""

MENSAGEM_PRIMEIRO_CONTATO = """Oi Dr(a) {nome}! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas aqui no ABC

{saudacao_especialidade}

Posso te contar mais?"""


SAUDACOES_ESPECIALIDADE = {
    "anestesiologia": "Vi que vc é anestesista, certo? Temos umas vagas bem interessantes em centro cirúrgico",
    "cardiologia": "Vi que vc é cardio, certo? Temos vagas em UTI e emergência que podem te interessar",
    "clinica_medica": "Vi que vc é clínico, né? Sempre tem vaga boa de PS e enfermaria",
    "pediatria": "Vi que vc é pediatra! Temos vagas legais em PS pediátrico e maternidade",
    "ortopedia": "Vi que vc é ortopedista! Sempre surge vaga boa de trauma e centro cirúrgico",
}


def obter_saudacao_especialidade(especialidade: str) -> str:
    """
    Retorna saudação personalizada para especialidade.

    Args:
        especialidade: Nome da especialidade

    Returns:
        Saudação personalizada ou padrão
    """
    if not especialidade:
        return "Vi que você é médico, certo? Temos umas vagas interessantes essa semana"

    nome_normalizado = especialidade.lower().replace(" ", "_").strip()
    return SAUDACOES_ESPECIALIDADE.get(
        nome_normalizado,
        f"Vi que vc é {especialidade.lower()}, certo? Temos umas vagas bem interessantes essa semana",
    )


def formatar_primeiro_contato(medico: dict) -> str:
    """Formata mensagem de primeiro contato."""
    nome = medico.get("primeiro_nome", "")
    especialidade_nome = medico.get("especialidade_nome", "")

    # Se não tiver especialidade_nome, buscar da relação
    if not especialidade_nome and medico.get("especialidade_id"):
        # Tentar buscar nome da especialidade
        # Por enquanto, usar valor padrão
        especialidade_nome = "médico"

    saudacao = obter_saudacao_especialidade(especialidade_nome)

    return MENSAGEM_PRIMEIRO_CONTATO.format(nome=nome, saudacao_especialidade=saudacao)


# ============================================================================
# LINKS DO APP REVOLUNA
# ============================================================================

LINK_APP_IOS = "https://apps.apple.com/br/app/revoluna/id6744747736"
LINK_APP_ANDROID = "https://play.google.com/store/apps/details?id=com.mycompany.revoluna&hl=pt_BR"


# ============================================================================
# TEMPLATES DE DOWNLOAD DO APP
# Usados quando médico demonstra interesse na Revoluna
# ============================================================================

# Variações da mensagem de convite para baixar o app
# Formato: lista de mensagens para enviar em sequência (simula conversa natural)
TEMPLATES_DOWNLOAD_APP = [
    # Variação 1 - Direta e animada
    [
        "Show! Fico feliz que curtiu",
        "Baixa nosso app que la vc ve todas as vagas disponiveis e pode se candidatar direto",
        "iPhone: {link_ios}",
        "Android: {link_android}",
        "Qualquer duvida me chama aqui!",
    ],
    # Variação 2 - Explicativa
    [
        "Que bom! Deixa eu te explicar como funciona",
        "A gente tem um app onde vc consegue ver os plantoes disponiveis, valores, horarios... tudo certinho",
        "E pode se candidatar com um clique",
        "Segue os links:",
        "iOS: {link_ios}",
        "Android: {link_android}",
    ],
    # Variação 3 - Casual
    [
        "Massa! Entao faz o seguinte",
        "Baixa o app da Revoluna que la tem tudo",
        "Se for iPhone: {link_ios}",
        "Se for Android: {link_android}",
        "Depois me conta o que achou",
    ],
    # Variação 4 - Prestativa
    [
        "Otimo! Vou te passar o link do nosso app",
        "La vc ve as vagas da regiao, valores, e consegue se inscrever rapidinho",
        "Apple: {link_ios}",
        "Google Play: {link_android}",
        "Se precisar de ajuda pra baixar ou usar, me avisa!",
    ],
]

# Template único (para casos onde uma só mensagem é preferível)
TEMPLATE_DOWNLOAD_APP_UNICO = """Show! Vou te passar o link do app

La vc ve todas as vagas disponiveis e pode se candidatar

iPhone: {link_ios}
Android: {link_android}

Qualquer coisa me chama!"""


def obter_mensagens_download_app(variacao: int = None) -> list[str]:
    """
    Retorna lista de mensagens para enviar links do app.

    Args:
        variacao: Índice da variação (0-3) ou None para aleatório

    Returns:
        Lista de mensagens formatadas com os links
    """
    import random

    if variacao is None:
        variacao = random.randint(0, len(TEMPLATES_DOWNLOAD_APP) - 1)

    variacao = variacao % len(TEMPLATES_DOWNLOAD_APP)
    template = TEMPLATES_DOWNLOAD_APP[variacao]

    return [msg.format(link_ios=LINK_APP_IOS, link_android=LINK_APP_ANDROID) for msg in template]


def obter_mensagem_download_app_unica() -> str:
    """
    Retorna mensagem única com links do app.

    Returns:
        String com mensagem formatada
    """
    return TEMPLATE_DOWNLOAD_APP_UNICO.format(link_ios=LINK_APP_IOS, link_android=LINK_APP_ANDROID)
