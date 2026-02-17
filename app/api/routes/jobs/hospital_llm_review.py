"""
Job de revisao LLM de hospitais.

Classifica hospitais e detecta duplicatas semanticas usando Claude Haiku.
"""

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/revisao-llm-hospitais")
@job_endpoint("revisao-llm-hospitais")
async def job_revisao_llm_hospitais():
    """
    Revisao LLM batch de hospitais pendentes.

    Fase 1: Classifica hospitais (real / invalido / lixo)
    Fase 2: Detecta e executa merges de duplicatas semanticas

    Job one-shot - executar manualmente quando necessario.
    """
    from app.services.grupos.hospital_llm_review import executar_revisao_llm_completa

    resultado = await executar_revisao_llm_completa()

    return {
        "status": "ok",
        "message": (
            f"Classificados: {resultado.hospitais_classificados}, "
            f"Deletados: {resultado.deletados}, "
            f"Merges auto: {resultado.merges_auto}, "
            f"Merges revisao: {resultado.merges_revisao}"
        ),
        "processados": resultado.hospitais_classificados + resultado.pares_analisados,
        "fase1_classificacao": {
            "hospitais_classificados": resultado.hospitais_classificados,
            "hospitais_reais": resultado.hospitais_reais,
            "genericos_invalidos": resultado.genericos_invalidos,
            "fragmentos_lixo": resultado.fragmentos_lixo,
            "deletados": resultado.deletados,
            "flagged_revisao": resultado.flagged_revisao,
            "nomes_atualizados": resultado.nomes_atualizados,
            "cidades_inferidas": resultado.cidades_inferidas,
        },
        "fase2_duplicatas": {
            "pares_analisados": resultado.pares_analisados,
            "merges_auto": resultado.merges_auto,
            "merges_revisao": resultado.merges_revisao,
            "merges_skip": resultado.merges_skip,
        },
        "tokens": {
            "input": resultado.tokens_input,
            "output": resultado.tokens_output,
        },
        "erros": resultado.erros,
    }
