"""
Configurações de regiões geográficas.
"""

from typing import Dict, Optional

REGIOES: Dict[str, Dict] = {
    "abc": {
        "nome": "ABC Paulista",
        "cidades": [
            "Santo André",
            "São Bernardo do Campo",
            "São Caetano do Sul",
            "Diadema",
            "Mauá",
            "Ribeirão Pires",
            "Rio Grande da Serra",
        ],
        "ddds": ["11"],
    },
    "sp_capital": {
        "nome": "São Paulo Capital",
        "cidades": ["São Paulo"],
        "ddds": ["11"],
    },
    "campinas": {
        "nome": "Região de Campinas",
        "cidades": ["Campinas", "Sumaré", "Hortolândia", "Indaiatuba", "Valinhos"],
        "ddds": ["19"],
    },
    "baixada_santista": {
        "nome": "Baixada Santista",
        "cidades": ["Santos", "São Vicente", "Guarujá", "Praia Grande"],
        "ddds": ["13"],
    },
}


def detectar_regiao_por_telefone(telefone: str) -> Optional[str]:
    """
    Detecta região do médico pelo telefone (DDD).

    Args:
        telefone: Telefone no formato +5511999999999

    Returns:
        Nome da região ou None
    """
    if not telefone or len(telefone) < 5:
        return None

    # Extrair DDD (assumindo formato +55DDD...)
    ddd = telefone[3:5] if telefone.startswith("+55") else telefone[:2]

    for regiao, config in REGIOES.items():
        if ddd in config["ddds"]:
            return regiao

    return None


def obter_regiao(regiao_id: str) -> Dict:
    """Retorna configuração de uma região."""
    return REGIOES.get(regiao_id, {})
