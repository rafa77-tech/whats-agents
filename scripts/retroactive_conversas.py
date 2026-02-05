"""
Script para criar retroativamente conversas e interações para mensagens
de campanha que foram enviadas sem criar conversa.

Uso:
    uv run python scripts/retroactive_conversas.py [--dry-run] [--campanha-id ID]

Flags:
    --dry-run       Apenas mostra o que seria feito, sem modificar o banco
    --campanha-id   Filtrar por ID da campanha específica
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import argparse
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def buscar_mensagens_sem_conversa(campanha_id: int | None = None) -> list[dict]:
    """
    Busca mensagens enviadas que não têm conversa_id.
    """
    from app.services.supabase import supabase

    query = (
        supabase.table("fila_mensagens")
        .select("id, cliente_id, conteudo, enviada_em, metadata")
        .eq("status", "enviada")
        .is_("conversa_id", "null")
    )

    # Filtrar por campanha se especificado
    if campanha_id:
        query = query.contains("metadata", {"campanha_id": str(campanha_id)})

    response = query.order("enviada_em").execute()
    return response.data or []


async def criar_conversa_e_interacao(
    mensagem: dict,
    dry_run: bool = False
) -> dict:
    """
    Cria conversa e interação para uma mensagem.

    Returns:
        Dict com resultado da operação
    """
    from app.services.conversa import buscar_ou_criar_conversa
    from app.services.interacao import salvar_interacao
    from app.services.supabase import supabase

    cliente_id = mensagem["cliente_id"]
    mensagem_id = mensagem["id"]
    conteudo = mensagem["conteudo"]
    enviada_em = mensagem.get("enviada_em")
    metadata = mensagem.get("metadata") or {}
    campanha_id = metadata.get("campanha_id")

    result = {
        "mensagem_id": mensagem_id,
        "cliente_id": cliente_id,
        "campanha_id": campanha_id,
        "success": False,
        "conversa_id": None,
        "interacao_id": None,
        "error": None,
    }

    if dry_run:
        logger.info(
            f"[DRY-RUN] Criaria conversa para cliente {cliente_id[:8]}... "
            f"(campanha={campanha_id})"
        )
        result["success"] = True
        result["dry_run"] = True
        return result

    try:
        # 1. Buscar ou criar conversa
        conversa = await buscar_ou_criar_conversa(cliente_id)
        if not conversa:
            result["error"] = "Falha ao criar conversa"
            return result

        conversa_id = conversa["id"]
        result["conversa_id"] = conversa_id

        # 2. Atualizar fila_mensagens com conversa_id
        supabase.table("fila_mensagens").update({
            "conversa_id": conversa_id
        }).eq("id", mensagem_id).execute()

        # 3. Salvar interação de saída
        interacao = await salvar_interacao(
            conversa_id=conversa_id,
            cliente_id=cliente_id,
            tipo="saida",
            conteudo=conteudo,
            autor_tipo="julia",
        )

        if interacao:
            result["interacao_id"] = interacao.get("id")

        result["success"] = True
        logger.info(
            f"✓ Conversa {conversa_id[:8]}... criada para cliente {cliente_id[:8]}..."
        )

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"✗ Erro para cliente {cliente_id[:8]}...: {e}")

    return result


async def main(dry_run: bool = False, campanha_id: int | None = None):
    """
    Executa o script de retroação.
    """
    logger.info("=" * 60)
    logger.info("Script de Criação Retroativa de Conversas")
    logger.info("=" * 60)

    if dry_run:
        logger.info("🔍 MODO DRY-RUN: Nenhuma modificação será feita")

    if campanha_id:
        logger.info(f"📋 Filtrando por campanha ID: {campanha_id}")

    # Buscar mensagens sem conversa
    logger.info("\nBuscando mensagens enviadas sem conversa...")
    mensagens = await buscar_mensagens_sem_conversa(campanha_id)

    if not mensagens:
        logger.info("✓ Nenhuma mensagem encontrada sem conversa!")
        return

    logger.info(f"Encontradas {len(mensagens)} mensagens sem conversa\n")

    # Processar cada mensagem
    stats = {
        "total": len(mensagens),
        "success": 0,
        "errors": 0,
    }

    for i, msg in enumerate(mensagens, 1):
        logger.info(f"[{i}/{len(mensagens)}] Processando mensagem {msg['id'][:8]}...")
        result = await criar_conversa_e_interacao(msg, dry_run)

        if result["success"]:
            stats["success"] += 1
        else:
            stats["errors"] += 1

    # Resumo
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO")
    logger.info("=" * 60)
    logger.info(f"Total de mensagens: {stats['total']}")
    logger.info(f"Processadas com sucesso: {stats['success']}")
    logger.info(f"Erros: {stats['errors']}")

    if dry_run:
        logger.info("\n⚠️  Modo dry-run. Execute sem --dry-run para aplicar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cria retroativamente conversas para mensagens de campanha"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o que seria feito"
    )
    parser.add_argument(
        "--campanha-id",
        type=int,
        help="ID da campanha específica"
    )

    args = parser.parse_args()

    asyncio.run(main(
        dry_run=args.dry_run,
        campanha_id=args.campanha_id
    ))
