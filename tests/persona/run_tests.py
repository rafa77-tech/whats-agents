"""
Runner principal para executar todos os testes de persona.
"""
import asyncio
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.persona.test_runner import PersonaTestRunner
from tests.persona.test_cases import CASOS_TESTE


async def run_all_tests():
    """Executa todos os testes de persona."""
    runner = PersonaTestRunner()

    for categoria, casos in CASOS_TESTE.items():
        print(f"\n=== Testando: {categoria} ===")

        for caso in casos:
            resultado = await runner.testar_resposta(
                mensagem_medico=caso["mensagem"],
                contexto=caso.get("contexto", {})
            )

            status = "✓" if resultado["passou"] else "✗"
            score = resultado["avaliacao"].get("score", 0)
            print(f"{status} '{caso['mensagem']}' -> Score: {score}/10")
            if not resultado["passou"]:
                print(f"  Feedback: {resultado['avaliacao'].get('feedback', 'N/A')}")

    # Resumo
    total = len(runner.resultados)
    passou = sum(1 for r in runner.resultados if r["passou"])
    taxa = (passou / total * 100) if total > 0 else 0

    print(f"\n{'='*50}")
    print(f"=== RESUMO ===")
    print(f"{'='*50}")
    print(f"Total: {total}")
    print(f"Passou: {passou} ({taxa:.1f}%)")
    print(f"Falhou: {total - passou}")

    return runner.resultados


if __name__ == "__main__":
    asyncio.run(run_all_tests())

