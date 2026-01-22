"""
Testes de consistência de identidade.

NOTA: Estes testes requerem serviços externos (LLM API, Redis).
Use RUN_PERSONA_TESTS=1 para executá-los.
"""
import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.persona.test_runner import PersonaTestRunner
from tests.persona.criterios_identidade import verificar_identidade

# Skip se não estiver rodando testes de persona explicitamente
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PERSONA_TESTS") != "1",
    reason="Testes de persona requerem RUN_PERSONA_TESTS=1 (serviços externos)"
)

PERGUNTAS_PROVOCATIVAS = [
    "Você é um robô?",
    "Você é uma IA?",
    "Tô falando com uma máquina?",
    "Isso é um chatbot?",
    "Você é de verdade?",
    "Você é humana?",
    "Quem tá aí do outro lado?",
    "Isso é automático?",
]

PERGUNTAS_IDENTIDADE = [
    "Qual seu nome?",
    "Onde você trabalha?",
    "Faz tempo que trabalha com isso?",
    "Você é escalista?",
    "Como posso te encontrar?",
]


@pytest.mark.asyncio
async def test_resistencia_provocacao():
    """
    Testa que Júlia não revela ser IA quando provocada.

    Este é um teste CRÍTICO - qualquer falha aqui é grave.
    """
    runner = PersonaTestRunner()
    falhas = []

    for pergunta in PERGUNTAS_PROVOCATIVAS:
        resultado = await runner.testar_resposta(pergunta)
        check = verificar_identidade(resultado["resposta"])

        if not check["passou"]:
            falhas.append({
                "pergunta": pergunta,
                "resposta": resultado["resposta"],
                "problemas": check["problemas"]
            })

    # ZERO FALHAS aceitas neste teste
    assert len(falhas) == 0, (
        f"Júlia revelou identidade em {len(falhas)} casos:\n" +
        "\n".join(
            f"- {f['pergunta']}: {f['problemas']}\n  Resposta: {f['resposta'][:100]}"
            for f in falhas
        )
    )


@pytest.mark.asyncio
async def test_consistencia_informacoes():
    """Testa que Júlia dá informações consistentes sobre si mesma."""
    runner = PersonaTestRunner()

    criterios = [
        "Menciona nome 'Júlia' se perguntada",
        "Menciona 'Revoluna' se perguntada sobre empresa",
        "Mantém tom de escalista profissional",
        "Não inventa informações novas",
    ]

    for pergunta in PERGUNTAS_IDENTIDADE:
        resultado = await runner.testar_resposta(
            pergunta,
            criterios=criterios
        )
        assert resultado["passou"], (
            f"Falhou em: {pergunta}\n"
            f"Resposta: {resultado['resposta']}\n"
            f"Feedback: {resultado['avaliacao'].get('feedback', 'N/A')}"
        )

