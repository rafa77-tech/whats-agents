"""
Critérios e verificadores de informalidade.
"""

ABREVIACOES_ESPERADAS = [
    ("você", "vc"),
    ("para", "pra"),
    ("está", "tá"),
    ("estou", "tô"),
    ("beleza", "blz"),
    ("combinado", "fechado"),
    ("mensagem", "msg"),
]

PALAVRAS_PROIBIDAS = [
    "prezado",
    "senhor",
    "senhora",
    "atenciosamente",
    "cordialmente",
    "caro",
    "estimado",
]


def verificar_informalidade(texto: str) -> dict:
    """
    Verifica se texto é informal o suficiente.

    Args:
        texto: Texto a verificar

    Returns:
        dict com score e detalhes
    """
    texto_lower = texto.lower()
    pontos = 0
    max_pontos = 10
    detalhes = []

    # Verificar uso de abreviações
    for formal, informal in ABREVIACOES_ESPERADAS:
        if informal in texto_lower:
            pontos += 1
            detalhes.append(f"✓ Usa '{informal}'")
        elif formal in texto_lower:
            detalhes.append(f"✗ Usa '{formal}' ao invés de '{informal}'")

    # Verificar ausência de palavras formais
    for palavra in PALAVRAS_PROIBIDAS:
        if palavra in texto_lower:
            pontos -= 2
            detalhes.append(f"✗ Usa palavra formal: '{palavra}'")

    # Verificar tamanho da mensagem (curta = mais informal)
    linhas = texto.count('\n') + 1
    if linhas <= 2:
        pontos += 2
        detalhes.append("✓ Mensagem curta")
    elif linhas > 4:
        pontos -= 1
        detalhes.append("✗ Mensagem muito longa")

    # Verificar se não tem bullet points
    if not any(c in texto for c in ['•', '-', '*', '1.', '2.']):
        pontos += 1
        detalhes.append("✓ Sem bullet points")
    else:
        pontos -= 2
        detalhes.append("✗ Usa bullet points/listas")

    score = max(0, min(10, pontos))

    return {
        "score": score,
        "passou": score >= 6,
        "detalhes": detalhes
    }

