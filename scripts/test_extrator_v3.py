#!/usr/bin/env python3
"""
Teste do Extrator v3 (LLM Unificado) - Sprint 52

Testa se o v3 resolve o bug do R$ 202 (regex capturando datas).
"""

import asyncio
import sys
from datetime import date
from uuid import uuid4

# Adicionar path do projeto
sys.path.insert(0, "/Users/rafaelpivovar/Documents/Projetos/whatsapp-api")

from app.services.grupos.extrator_v2.extrator_llm import extrair_vagas_v3, extrair_com_llm


# Mensagens de teste (casos que tinham o bug)
MENSAGENS_TESTE = [
    {
        "nome": "Caso 1: Ginecologia sem valor (bug R$ 202)",
        "texto": """🌀 *OGS RECRUTA*

*Ginecologia* 👩🏻‍⚕️

_Procuramos por profissionais com Titulo, Residência completa *ou* RQE._

🏥 *Hospital Dia da Rede Hora Certa M Boi Mirim II*
04/02/2026	07:00 - 19:00
11/02/2026	07:00 - 19:00
18/02/2026	07:00 - 19:00

🏥 *PS HM DR WALDOMIRO DE PAULA*
05/02/2026	DIURNO
12/02/2026	DIURNO

Interessados chamar inbox
http://wa.me/5512997710758 - Thais OGS Saúde""",
        "esperado_valor": None,  # Não tem valor mencionado
    },
    {
        "nome": "Caso 2: Vaga com valor real",
        "texto": """🏥 VAGA URGENTE - CLÍNICA MÉDICA

Hospital Albert Einstein
Data: 10/02/2026
Horário: 07:00 às 19:00 (SD)
Valor: R$ 2.500,00

Interessados enviar currículo
Contato: Maria - 11999887766""",
        "esperado_valor": 2500,
    },
    {
        "nome": "Caso 3: Múltiplos plantões com valor total",
        "texto": """PLANTÕES DISPONÍVEIS - ORTOPEDIA

🏥 Hospital São Paulo
- 05/02/2026 Noturno
- 06/02/2026 Noturno
- 07/02/2026 Diurno

Valor: R$ 7.500 pelos 3 plantões

Contato: João (11) 98765-4321""",
        "esperado_valor": 2500,  # 7500 / 3 = 2500 por plantão
    },
    {
        "nome": "Caso 4: Mensagem que não é vaga",
        "texto": """Bom dia pessoal!

Alguém sabe se o Hospital das Clínicas está com vagas abertas?
Tenho interesse em trabalhar lá.

Abraços!""",
        "esperado_eh_vaga": False,
    },
]


async def testar_extracao_llm():
    """Testa a extração LLM com as mensagens de teste."""
    print("=" * 70)
    print("TESTE DO EXTRATOR v3 (LLM UNIFICADO) - Sprint 52")
    print("=" * 70)
    print()

    for i, caso in enumerate(MENSAGENS_TESTE, 1):
        print(f"\n{'='*70}")
        print(f"CASO {i}: {caso['nome']}")
        print("=" * 70)
        print(f"\nMENSAGEM:\n{caso['texto'][:200]}...")
        print()

        try:
            # Testar extração LLM direta primeiro
            resultado_llm = await extrair_com_llm(
                texto=caso["texto"],
                nome_grupo="Grupo Teste",
                nome_contato="Teste",
                data_referencia=date.today(),
                usar_cache=False  # Não usar cache para teste
            )

            print(f"📊 RESULTADO LLM:")
            print(f"   - eh_vaga: {resultado_llm.eh_vaga}")
            print(f"   - confiança: {resultado_llm.confianca:.2f}")
            print(f"   - motivo_descarte: {resultado_llm.motivo_descarte}")
            print(f"   - tokens: {resultado_llm.tokens_usados}")
            print(f"   - vagas extraídas: {len(resultado_llm.vagas)}")

            if resultado_llm.vagas:
                for j, vaga in enumerate(resultado_llm.vagas, 1):
                    print(f"\n   📋 Vaga {j}:")
                    print(f"      - hospital: {vaga.get('hospital')}")
                    print(f"      - especialidade: {vaga.get('especialidade')}")
                    print(f"      - data: {vaga.get('data')}")
                    print(f"      - periodo: {vaga.get('periodo')}")
                    print(f"      - valor: {vaga.get('valor')}")

            # Verificar expectativas
            print(f"\n✅ VALIDAÇÃO:")

            if "esperado_valor" in caso:
                valor_extraido = resultado_llm.vagas[0].get("valor") if resultado_llm.vagas else None
                if valor_extraido == caso["esperado_valor"]:
                    print(f"   ✅ Valor correto: {valor_extraido}")
                else:
                    print(f"   ❌ Valor incorreto: {valor_extraido} (esperado: {caso['esperado_valor']})")

            if "esperado_eh_vaga" in caso:
                if resultado_llm.eh_vaga == caso["esperado_eh_vaga"]:
                    print(f"   ✅ Classificação correta: eh_vaga={resultado_llm.eh_vaga}")
                else:
                    print(f"   ❌ Classificação incorreta: eh_vaga={resultado_llm.eh_vaga} (esperado: {caso['esperado_eh_vaga']})")

            # Agora testar a função completa
            print(f"\n📊 TESTE extrair_vagas_v3:")
            resultado_v3 = await extrair_vagas_v3(
                texto=caso["texto"],
                mensagem_id=uuid4(),
                grupo_id=uuid4(),
                nome_grupo="Grupo Teste",
                nome_contato="Teste",
                data_referencia=date.today()
            )

            print(f"   - sucesso: {resultado_v3.sucesso}")
            print(f"   - total_vagas: {resultado_v3.total_vagas}")
            print(f"   - erro: {resultado_v3.erro}")
            print(f"   - tempo_ms: {resultado_v3.tempo_processamento_ms}")
            print(f"   - tokens: {resultado_v3.tokens_usados}")

            if resultado_v3.vagas:
                for j, vaga in enumerate(resultado_v3.vagas, 1):
                    print(f"\n   📋 VagaAtomica {j}:")
                    print(f"      - hospital_raw: {vaga.hospital_raw}")
                    print(f"      - especialidade_raw: {vaga.especialidade_raw}")
                    print(f"      - data: {vaga.data}")
                    print(f"      - periodo: {vaga.periodo}")
                    print(f"      - valor: {vaga.valor}")

        except Exception as e:
            print(f"❌ ERRO: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("TESTE CONCLUÍDO")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(testar_extracao_llm())
