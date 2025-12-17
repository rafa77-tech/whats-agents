#!/usr/bin/env python
"""
Script para indexar documentação Julia.

Uso:
    uv run python scripts/indexar_conhecimento.py
    uv run python scripts/indexar_conhecimento.py --reindexar
    uv run python scripts/indexar_conhecimento.py --arquivo MENSAGENS_ABERTURA.md
"""
import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Adicionar root do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    parser = argparse.ArgumentParser(description="Indexar documentação Julia")
    parser.add_argument(
        "--reindexar",
        action="store_true",
        help="Remove dados antigos antes de indexar",
    )
    parser.add_argument(
        "--arquivo",
        type=str,
        help="Indexar apenas um arquivo específico",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista arquivos disponíveis para indexação",
    )

    args = parser.parse_args()

    from app.services.conhecimento import IndexadorConhecimento

    indexador = IndexadorConhecimento()

    if args.listar:
        print("\n=== ARQUIVOS DISPONÍVEIS ===")
        arquivos = list(indexador.docs_path.glob("*.md"))
        for arq in sorted(arquivos):
            print(f"  - {arq.name}")
        print(f"\nTotal: {len(arquivos)} arquivos")
        return

    if args.arquivo:
        print(f"\n=== INDEXANDO ARQUIVO: {args.arquivo} ===")
        try:
            count = await indexador.indexar_arquivo(args.arquivo)
            print(f"\n✅ Indexado: {count} chunks")
        except FileNotFoundError as e:
            print(f"\n❌ Erro: {e}")
            sys.exit(1)
    else:
        print("\n=== INDEXAÇÃO COMPLETA ===")
        if args.reindexar:
            print("⚠️  Modo reindexar: dados antigos serão removidos")

        stats = await indexador.indexar_todos(reindexar=args.reindexar)

        print(f"\n=== RESULTADO ===")
        print(f"Arquivos processados: {stats['arquivos']}")
        print(f"Chunks criados: {stats['chunks']}")
        print(f"Embeddings gerados: {stats['embeddings']}")
        print(f"Erros: {stats['erros']}")

        if stats["erros"] > 0:
            print("\n⚠️  Houve erros durante a indexação. Verifique os logs.")
        else:
            print("\n✅ Indexação concluída com sucesso!")


if __name__ == "__main__":
    asyncio.run(main())
