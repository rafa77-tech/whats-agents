#!/usr/bin/env python3
"""
Script de Reprocessamento de Valores - Sprint 52

Reprocessa mensagens que tiveram valores extraídos incorretamente pelo v2
usando o extrator LLM v3 para obter valores corretos.

Casos tratados:
- R$ 202 (extraído de datas "2026")
- R$ 551, 915, etc (extraído de telefones)
- Valores < R$ 500 (suspeitos)
- Valores > R$ 10.000 (pacotes mensais sem divisão)

Uso:
    python scripts/reprocessar_valores_v3.py --dry-run  # Apenas simula
    python scripts/reprocessar_valores_v3.py --batch=100  # Processa 100 mensagens
    python scripts/reprocessar_valores_v3.py --all  # Processa todas
"""

import asyncio
import argparse
import sys
from datetime import date
from uuid import UUID

# Adicionar path do projeto
sys.path.insert(0, "/Users/rafaelpivovar/Documents/Projetos/whatsapp-api")

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

# Valores que indicam bug de extração
VALORES_BUGADOS = [
    # Códigos de área (55 + DDD)
    551, 552, 553, 554, 555, 556, 557, 558, 559,
    # Padrões de celular 9xxxx
    915, 916, 917, 918, 919,
    983, 984, 985, 986, 987, 988, 989,
    991, 992, 993, 994, 995, 996, 997, 998, 999,
    # Datas (202x)
    202, 203, 204, 205, 206,
]


# =============================================================================
# FUNÇÕES DE BUSCA
# =============================================================================

async def buscar_vagas_para_reprocessar(limit: int = 100) -> list:
    """
    Busca vagas que precisam ser reprocessadas.

    Critérios:
    - valor_original IS NOT NULL (já foi corrigido mas pode ter valor real)
    - OU valor era suspeito (< 500, em VALORES_BUGADOS, ou > 10000)
    """
    # Buscar vagas que foram anuladas (tem valor_original ou observacoes indica bug)
    result = supabase.table("vagas_grupo") \
        .select("id, mensagem_id, valor, valor_original, observacoes_raw") \
        .or_("valor.is.null,valor.eq.0") \
        .not_.is_("mensagem_id", "null") \
        .limit(limit) \
        .execute()

    return result.data or []


async def buscar_mensagem(mensagem_id: str) -> dict | None:
    """Busca texto da mensagem original."""
    result = supabase.table("mensagens_grupo") \
        .select("id, texto, grupo_id, grupos_whatsapp(nome)") \
        .eq("id", mensagem_id) \
        .single() \
        .execute()

    return result.data


# =============================================================================
# FUNÇÃO DE REPROCESSAMENTO
# =============================================================================

async def reprocessar_vaga(vaga: dict, dry_run: bool = True) -> dict:
    """
    Reprocessa uma vaga usando o extrator v3.

    Args:
        vaga: Dados da vaga_grupo
        dry_run: Se True, apenas simula sem atualizar

    Returns:
        Resultado do reprocessamento
    """
    from app.services.grupos.extrator_v2.extrator_llm import extrair_com_llm

    vaga_id = vaga["id"]
    mensagem_id = vaga["mensagem_id"]

    # Buscar mensagem original
    mensagem = await buscar_mensagem(mensagem_id)
    if not mensagem:
        return {
            "vaga_id": vaga_id,
            "status": "erro",
            "motivo": "mensagem_nao_encontrada"
        }

    texto = mensagem.get("texto", "")
    if not texto or len(texto) < 20:
        return {
            "vaga_id": vaga_id,
            "status": "skip",
            "motivo": "texto_muito_curto"
        }

    grupo_info = mensagem.get("grupos_whatsapp") or {}

    # Extrair com v3
    try:
        resultado = await extrair_com_llm(
            texto=texto,
            nome_grupo=grupo_info.get("nome", ""),
            data_referencia=date.today(),
            usar_cache=True  # Usar cache para economizar tokens
        )
    except Exception as e:
        return {
            "vaga_id": vaga_id,
            "status": "erro",
            "motivo": f"erro_llm: {str(e)}"
        }

    # Verificar se extraiu valor
    if not resultado.eh_vaga or not resultado.vagas:
        return {
            "vaga_id": vaga_id,
            "status": "skip",
            "motivo": "nao_eh_vaga_ou_sem_vagas"
        }

    # Pegar primeiro valor encontrado (ou None se não tiver)
    valor_extraido = None
    for v in resultado.vagas:
        if v.get("valor") and v["valor"] > 0:
            valor_extraido = v["valor"]
            break

    if valor_extraido is None:
        return {
            "vaga_id": vaga_id,
            "status": "sem_valor",
            "motivo": "v3_nao_encontrou_valor"
        }

    # Validar valor extraído
    if valor_extraido < 500 or valor_extraido > 10000:
        return {
            "vaga_id": vaga_id,
            "status": "valor_suspeito",
            "valor_extraido": valor_extraido,
            "motivo": f"valor_fora_range: {valor_extraido}"
        }

    # Atualizar no banco (se não for dry_run)
    if not dry_run:
        try:
            # Salvar valor anterior em valor_original (auditoria)
            valor_anterior = vaga.get("valor")

            supabase.table("vagas_grupo") \
                .update({
                    "valor": valor_extraido,
                    "valor_tipo": "fixo",
                    "valor_original": valor_anterior,  # Guardar para auditoria
                }) \
                .eq("id", vaga_id) \
                .execute()
        except Exception as e:
            return {
                "vaga_id": vaga_id,
                "status": "erro",
                "motivo": f"erro_update: {str(e)}"
            }

    return {
        "vaga_id": vaga_id,
        "status": "sucesso",
        "valor_anterior": vaga.get("valor"),
        "valor_novo": valor_extraido,
        "dry_run": dry_run
    }


# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

async def main(args):
    """Função principal do script."""
    print("=" * 70)
    print("REPROCESSAMENTO DE VALORES - Pipeline v3")
    print("=" * 70)
    print(f"\nModo: {'DRY-RUN (simulação)' if args.dry_run else 'EXECUÇÃO REAL'}")
    print(f"Limite: {args.batch if not args.all else 'TODAS'}")
    print()

    # Buscar vagas para reprocessar
    limit = 10000 if args.all else args.batch
    print(f"Buscando vagas para reprocessar (limit={limit})...")

    vagas = await buscar_vagas_para_reprocessar(limit)
    print(f"Encontradas: {len(vagas)} vagas\n")

    if not vagas:
        print("Nenhuma vaga para reprocessar.")
        return

    # Estatísticas
    stats = {
        "total": len(vagas),
        "sucesso": 0,
        "sem_valor": 0,
        "skip": 0,
        "erro": 0,
        "valor_suspeito": 0,
    }

    # Processar
    for i, vaga in enumerate(vagas, 1):
        if i % 10 == 0 or i == 1:
            print(f"Processando {i}/{len(vagas)}...")

        resultado = await reprocessar_vaga(vaga, dry_run=args.dry_run)
        status = resultado.get("status", "erro")
        stats[status] = stats.get(status, 0) + 1

        if status == "sucesso":
            print(f"  ✅ Vaga {resultado['vaga_id'][:8]}: "
                  f"{resultado['valor_anterior']} → {resultado['valor_novo']}")
        elif status == "valor_suspeito":
            print(f"  ⚠️ Vaga {resultado['vaga_id'][:8]}: "
                  f"valor suspeito {resultado['valor_extraido']}")
        elif args.verbose and status == "erro":
            print(f"  ❌ Vaga {vaga['id'][:8]}: {resultado.get('motivo')}")

    # Resumo
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"Total processadas: {stats['total']}")
    print(f"  ✅ Sucesso: {stats['sucesso']}")
    print(f"  ⚠️ Valor suspeito: {stats['valor_suspeito']}")
    print(f"  ⏭️ Skip: {stats['skip']}")
    print(f"  📭 Sem valor: {stats['sem_valor']}")
    print(f"  ❌ Erro: {stats['erro']}")

    if args.dry_run:
        print("\n⚠️ MODO DRY-RUN: Nenhuma alteração foi feita no banco.")
        print("Execute sem --dry-run para aplicar as alterações.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reprocessa valores de vagas usando extrator v3"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas simula, não altera o banco"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=100,
        help="Número de vagas a processar (default: 100)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Processa todas as vagas pendentes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra detalhes de erros"
    )

    args = parser.parse_args()
    asyncio.run(main(args))
