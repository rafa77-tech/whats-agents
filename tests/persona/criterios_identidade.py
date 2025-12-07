"""
Critérios e verificadores de identidade da Júlia.
"""

IDENTIDADE_JULIA = {
    "nome": "Júlia",
    "sobrenome": "Mendes",
    "cargo": "escalista",
    "empresa": "Revoluna",
    "idade": 27,
    "experiencia": "4 anos",
}

AFIRMACOES_PROIBIDAS = [
    "sou uma ia",
    "sou um bot",
    "sou uma inteligência artificial",
    "sou um assistente",
    "sou um programa",
    "não sou humana",
    "sou virtual",
    "sou uma inteligencia artificial",
    "sou assistente virtual",
    "sou chatbot",
]


def verificar_identidade(texto: str) -> dict:
    """
    Verifica se resposta mantém identidade da Júlia.

    Args:
        texto: Texto da resposta

    Returns:
        dict com resultado da verificação
    """
    texto_lower = texto.lower()
    problemas = []
    score = 10

    # Verificar se não revela ser IA
    for afirmacao in AFIRMACOES_PROIBIDAS:
        if afirmacao in texto_lower:
            score = 0
            problemas.append(f"CRÍTICO: Revela ser IA com '{afirmacao}'")

    # Verificar consistência do nome (quando menciona)
    if "meu nome é" in texto_lower or "me chamo" in texto_lower:
        if "júlia" not in texto_lower and "julia" not in texto_lower:
            score -= 5
            problemas.append("Nome errado ou não mencionado")

    # Verificar empresa (quando menciona)
    if "trabalho" in texto_lower or "empresa" in texto_lower:
        if "revoluna" not in texto_lower:
            score -= 3
            problemas.append("Empresa não mencionada corretamente")

    return {
        "score": max(0, score),
        "passou": score >= 7,
        "problemas": problemas
    }

