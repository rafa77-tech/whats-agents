"""
Utilitario para normalizacao de telefone.

Garante formato unico (apenas digitos, com DDI 55) para evitar
duplicatas de clientes no banco.
"""

import re


def normalizar_telefone(telefone: str) -> str:
    """
    Normaliza telefone para formato numerico com DDI.

    Remove '+', espacos, parenteses, hifen e garante formato 5511999999999.

    Args:
        telefone: Numero em qualquer formato

    Returns:
        Apenas digitos, com DDI 55 adicionado se necessario.
        String vazia se input for vazio.
    """
    if not telefone:
        return ""

    numeros = re.sub(r"\D", "", telefone)

    if not numeros:
        return ""

    if len(numeros) == 11:  # DDD + 9 digitos
        numeros = "55" + numeros
    elif len(numeros) == 10:  # DDD + 8 digitos (fixo/antigo)
        numeros = "55" + numeros

    return numeros
