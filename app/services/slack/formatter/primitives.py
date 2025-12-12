"""
Primitivos de formatacao Slack.

Funcoes basicas para formatacao de texto no Slack.
Sprint 10 - S10.E2.1
"""


def bold(texto: str) -> str:
    """Formata texto em negrito."""
    return f"*{texto}*"


def italic(texto: str) -> str:
    """Formata texto em italico."""
    return f"_{texto}_"


def code(texto: str) -> str:
    """Formata texto como codigo (monospace)."""
    return f"`{texto}`"


def code_block(texto: str, linguagem: str = "") -> str:
    """Formata texto como bloco de codigo."""
    return f"```{linguagem}\n{texto}\n```"


def quote(texto: str) -> str:
    """Formata texto como citacao."""
    linhas = texto.split("\n")
    return "\n".join(f"> {linha}" for linha in linhas)


def lista(itens: list[str], max_itens: int = 7) -> str:
    """Formata lista com bullets."""
    if len(itens) > max_itens:
        itens_mostrar = itens[:max_itens]
        resto = len(itens) - max_itens
        resultado = "\n".join(f"• {item}" for item in itens_mostrar)
        resultado += f"\n_...e mais {resto}_"
        return resultado
    return "\n".join(f"• {item}" for item in itens)


def lista_numerada(itens: list[str], max_itens: int = 7) -> str:
    """Formata lista numerada."""
    if len(itens) > max_itens:
        itens_mostrar = itens[:max_itens]
        resto = len(itens) - max_itens
        resultado = "\n".join(f"{i+1}. {item}" for i, item in enumerate(itens_mostrar))
        resultado += f"\n_...e mais {resto}_"
        return resultado
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(itens))


def link(url: str, texto: str) -> str:
    """Formata link clicavel."""
    return f"<{url}|{texto}>"
