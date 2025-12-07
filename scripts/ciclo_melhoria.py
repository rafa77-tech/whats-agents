"""
Script para ciclo de melhoria iterativa do prompt baseado em testes.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.persona.run_tests import run_all_tests
from scripts.analisar_testes import analisar_resultados


async def ciclo_melhoria():
    """
    Ciclo de melhoria do prompt:
    1. Executar testes
    2. Analisar falhas
    3. Ajustar prompt
    4. Re-testar
    5. Repetir até >= 95%
    """
    iteracao = 1
    taxa_aprovacao = 0

    while taxa_aprovacao < 0.95 and iteracao <= 5:
        print(f"\n{'='*50}")
        print(f"ITERAÇÃO {iteracao}")
        print(f"{'='*50}")

        # 1. Executar testes
        resultados = await run_all_tests()

        # 2. Calcular taxa
        passou = sum(1 for r in resultados if r.get("passou", False))
        taxa_aprovacao = passou / len(resultados) if resultados else 0
        print(f"\nTaxa de aprovação: {taxa_aprovacao*100:.1f}%")

        if taxa_aprovacao >= 0.95:
            print("✓ Meta atingida!")
            break

        # 3. Analisar problemas
        analise = analisar_resultados(resultados)
        print(analise["relatorio"])

        # 4. Aguardar ajuste manual do prompt
        print("\n⚠️ Ajuste o prompt em app/core/prompts.py e pressione Enter para continuar...")
        input()

        iteracao += 1

    return taxa_aprovacao


if __name__ == "__main__":
    asyncio.run(ciclo_melhoria())

