"""
Helpers para extrair contexto de eventos de negocio.

Sprint 17 - E04
"""
from typing import List


def extrair_vagas_do_contexto(
    tool_calls: List[dict],
    resposta_agente: str = "",
) -> List[str]:
    """
    Extrai vaga_ids do contexto da interacao.

    Args:
        tool_calls: Lista de tool calls feitos pelo agente
        resposta_agente: Resposta final do agente (opcional)

    Returns:
        Lista de vaga_ids mencionados/oferecidos
    """
    vaga_ids = []

    for call in tool_calls:
        tool_name = call.get("name", "")
        result = call.get("result", {})

        if tool_name == "buscar_vagas":
            # Vagas retornadas pela busca
            for vaga in result.get("vagas", []):
                if vaga.get("id"):
                    vaga_ids.append(vaga["id"])

        elif tool_name == "reservar_plantao":
            # Vaga reservada
            if result.get("vaga_id"):
                vaga_ids.append(result["vaga_id"])
            if result.get("id"):
                vaga_ids.append(result["id"])

    return list(set(vaga_ids))  # Dedupe


def tem_mencao_oportunidade(resposta: str) -> bool:
    """
    Verifica se a resposta menciona oportunidades genericas.

    Usado para decidir entre offer_made vs offer_teaser_sent.
    Se menciona oportunidade mas sem vaga especifica, e teaser.

    Args:
        resposta: Texto da resposta do agente

    Returns:
        True se menciona oportunidades genericas
    """
    termos = [
        "temos vagas",
        "temos oportunidades",
        "surgiu uma vaga",
        "apareceu plantão",
        "apareceu plantao",
        "tem interesse",
        "posso te passar",
        "temos plantões",
        "temos plantoes",
        "vagas disponíveis",
        "vagas disponiveis",
        "oportunidades na região",
        "oportunidades na regiao",
    ]

    resposta_lower = resposta.lower()
    return any(termo in resposta_lower for termo in termos)
