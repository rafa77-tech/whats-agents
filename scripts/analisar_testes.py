"""
Script para analisar resultados dos testes de persona.
"""
from typing import List, Dict, Any


def analisar_resultados(resultados: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisa resultados dos testes e identifica padrões de falha.

    Args:
        resultados: Lista de resultados dos testes

    Returns:
        dict com problemas mais comuns e sugestões
    """
    problemas = {
        "formalidade_excessiva": [],
        "mensagem_longa": [],
        "bullet_points": [],
        "inconsistencia_identidade": [],
        "revelou_ia": [],
    }

    for r in resultados:
        if not r.get("passou", False):
            resposta = r.get("resposta", "")
            feedback = r.get("avaliacao", {}).get("feedback", "")

            # Categorizar problema
            if "formal" in feedback.lower():
                problemas["formalidade_excessiva"].append(r)
            if len(resposta.split('\n')) > 3:
                problemas["mensagem_longa"].append(r)
            if any(c in resposta for c in ['•', '- ', '* ']):
                problemas["bullet_points"].append(r)

            # Verificar revelação de IA
            resposta_lower = resposta.lower()
            if any(termo in resposta_lower for termo in ["sou uma ia", "sou um bot", "sou assistente"]):
                problemas["revelou_ia"].append(r)

    # Gerar relatório
    relatorio = []
    for problema, casos in problemas.items():
        if casos:
            relatorio.append(f"\n## {problema.upper()} ({len(casos)} casos)")
            for caso in casos[:3]:  # Mostrar até 3 exemplos
                relatorio.append(f"- Msg: {caso.get('mensagem', 'N/A')}")
                relatorio.append(f"  Resp: {caso.get('resposta', 'N/A')[:100]}...")

    return {
        "problemas": problemas,
        "relatorio": "\n".join(relatorio)
    }

