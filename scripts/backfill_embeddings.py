#!/usr/bin/env python
"""
Script para preencher embeddings faltantes respeitando rate limit.

Voyage AI Free Tier: 3 RPM, 10K TPM
Estratégia: 1 request a cada 21 segundos (≈2.8 RPM com margem)

Uso:
    uv run python scripts/backfill_embeddings.py
    uv run python scripts/backfill_embeddings.py --batch 50  # Processar 50 chunks
    uv run python scripts/backfill_embeddings.py --status    # Ver status atual
"""
import asyncio
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Adicionar root do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rate limit: 1 request a cada 21 segundos = ~2.8 RPM (margem de segurança)
DELAY_ENTRE_REQUESTS = 21


async def get_status():
    """Retorna status atual dos embeddings."""
    from app.services.supabase import supabase

    # Query direta usando count
    total = supabase.table("conhecimento_julia").select("id", count="exact").execute()
    com_emb = supabase.table("conhecimento_julia").select("id", count="exact").not_.is_("embedding", "null").execute()

    total_count = total.count or 0
    com_emb_count = com_emb.count or 0
    sem_emb_count = total_count - com_emb_count

    return {
        "total": total_count,
        "com_embedding": com_emb_count,
        "sem_embedding": sem_emb_count,
    }


async def backfill_embeddings(batch_size: int = None):
    """Preenche embeddings faltantes com rate limiting."""
    from app.services.supabase import supabase
    from app.services.embedding import gerar_embedding

    # Buscar chunks sem embedding
    query = supabase.table("conhecimento_julia").select("id, conteudo").is_("embedding", "null")

    if batch_size:
        query = query.limit(batch_size)

    response = query.execute()
    chunks = response.data

    if not chunks:
        logger.info("✅ Todos os chunks já têm embedding!")
        return {"processados": 0, "sucesso": 0, "erros": 0}

    logger.info(f"📦 {len(chunks)} chunks para processar")
    logger.info(f"⏱️  Tempo estimado: {len(chunks) * DELAY_ENTRE_REQUESTS / 60:.1f} minutos")
    logger.info(f"🚀 Iniciando às {datetime.now().strftime('%H:%M:%S')}")

    stats = {"processados": 0, "sucesso": 0, "erros": 0}

    for i, chunk in enumerate(chunks):
        try:
            # Gerar embedding
            embedding = await gerar_embedding(chunk["conteudo"])

            if embedding:
                # Atualizar no banco
                supabase.table("conhecimento_julia").update({
                    "embedding": embedding
                }).eq("id", chunk["id"]).execute()

                stats["sucesso"] += 1
                logger.info(f"✅ [{i+1}/{len(chunks)}] Chunk {chunk['id'][:8]}... OK")
            else:
                stats["erros"] += 1
                logger.warning(f"⚠️ [{i+1}/{len(chunks)}] Chunk {chunk['id'][:8]}... embedding vazio")

        except Exception as e:
            stats["erros"] += 1
            logger.error(f"❌ [{i+1}/{len(chunks)}] Chunk {chunk['id'][:8]}... erro: {e}")

        stats["processados"] += 1

        # Rate limiting - esperar entre requests (exceto no último)
        if i < len(chunks) - 1:
            logger.debug(f"⏳ Aguardando {DELAY_ENTRE_REQUESTS}s...")
            await asyncio.sleep(DELAY_ENTRE_REQUESTS)

    logger.info(f"\n{'='*50}")
    logger.info(f"📊 RESULTADO:")
    logger.info(f"   Processados: {stats['processados']}")
    logger.info(f"   Sucesso: {stats['sucesso']}")
    logger.info(f"   Erros: {stats['erros']}")

    return stats


async def main():
    parser = argparse.ArgumentParser(description="Backfill embeddings faltantes")
    parser.add_argument(
        "--batch",
        type=int,
        help="Número máximo de chunks para processar (default: todos)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Apenas mostrar status atual",
    )

    args = parser.parse_args()

    if args.status:
        status = await get_status()
        print(f"\n{'='*40}")
        print(f"📊 STATUS DOS EMBEDDINGS")
        print(f"{'='*40}")
        print(f"Total chunks:    {status['total']}")
        print(f"Com embedding:   {status['com_embedding']}")
        print(f"Sem embedding:   {status['sem_embedding']}")

        if status['sem_embedding'] > 0:
            tempo_est = status['sem_embedding'] * DELAY_ENTRE_REQUESTS / 60
            print(f"\n⏱️  Tempo para completar: ~{tempo_est:.0f} minutos ({tempo_est/60:.1f} horas)")
        else:
            print(f"\n✅ Todos os embeddings estão completos!")
        return

    print(f"\n{'='*50}")
    print(f"🔄 BACKFILL DE EMBEDDINGS")
    print(f"{'='*50}")

    if args.batch:
        print(f"📦 Processando batch de {args.batch} chunks")
    else:
        print(f"📦 Processando TODOS os chunks faltantes")

    print(f"⏱️  Rate limit: 1 request a cada {DELAY_ENTRE_REQUESTS}s (~2.8 RPM)")
    print()

    await backfill_embeddings(batch_size=args.batch)


if __name__ == "__main__":
    asyncio.run(main())
