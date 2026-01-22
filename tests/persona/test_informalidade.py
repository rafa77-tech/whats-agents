"""
Testes específicos de linguagem informal.

NOTA: Estes testes requerem serviços externos (LLM API, Redis).
Use RUN_PERSONA_TESTS=1 para executá-los.
"""
import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.persona.test_runner import PersonaTestRunner
from tests.persona.criterios_informalidade import verificar_informalidade

# Skip se não estiver rodando testes de persona explicitamente
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERSONA_TESTS") != "1",
    reason="Testes de persona requerem RUN_PERSONA_TESTS=1 (serviços externos)"
)

MENSAGENS_TESTE_INFORMALIDADE = [
    "Oi, tudo bem?",
    "Pode me explicar como funciona?",
    "Quanto custa o plantão?",
    "Vocês trabalham com que hospitais?",
    "Tô interessado na vaga de sábado",
]


@pytest.mark.asyncio
async def test_todas_respostas_informais():
    """Testa que todas as respostas são informais."""
    runner = PersonaTestRunner()
    resultados = []

    for mensagem in MENSAGENS_TESTE_INFORMALIDADE:
        resultado = await runner.testar_resposta(mensagem)
        check = verificar_informalidade(resultado["resposta"])
        resultados.append({
            "mensagem": mensagem,
            "resposta": resultado["resposta"],
            "informalidade": check
        })

    # Verificar que pelo menos 90% passou
    passou = sum(1 for r in resultados if r["informalidade"]["passou"])
    taxa = passou / len(resultados) if resultados else 0

    assert taxa >= 0.9, (
        f"Taxa de informalidade: {taxa*100:.1f}% (mínimo 90%)\n"
        f"Falhas:\n" +
        "\n".join(
            f"- '{r['mensagem']}': {r['informalidade']['score']}/10"
            for r in resultados if not r["informalidade"]["passou"]
        )
    )

