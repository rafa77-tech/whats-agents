"""
Script para executar o piloto completo.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.campanha import criar_campanha_piloto, executar_campanha
from app.services.supabase import supabase


async def mostrar_resumo_piloto(campanha_id: str):
    """Mostra resumo do status do piloto."""
    envios_resp = (
        supabase.table("envios_campanha")
        .select("status")
        .eq("campanha_id", campanha_id)
        .execute()
    )

    envios = envios_resp.data or []

    por_status = {}
    for e in envios:
        status = e["status"]
        por_status[status] = por_status.get(status, 0) + 1

    print(f"\nTotal: {len(envios)}")
    for status, qtd in por_status.items():
        print(f"- {status}: {qtd}")


async def main():
    """Executa piloto completo."""
    print("=" * 50)
    print("PILOTO JÚLIA V1")
    print("=" * 50)
    print(f"Início: {datetime.now()}")

    # Criar campanha
    try:
        campanha = await criar_campanha_piloto()
        print(f"\nCampanha criada: {campanha['id']}")
        print(f"Total destinatários: {campanha['total_destinatarios']}")
    except Exception as e:
        print(f"❌ Erro ao criar campanha: {e}")
        return

    # Confirmar
    confirmacao = input("\nIniciar envios? (s/n): ")
    if confirmacao.lower() != "s":
        print("Cancelado")
        return

    # Executar em background
    print("\nIniciando envios...")
    print("(Pressione Ctrl+C para pausar)\n")

    try:
        await executar_campanha(campanha["id"])
    except KeyboardInterrupt:
        print("\n\nPausado pelo usuário")

    # Resumo
    print("\n" + "=" * 50)
    print("RESUMO")
    print("=" * 50)
    await mostrar_resumo_piloto(campanha["id"])


if __name__ == "__main__":
    asyncio.run(main())

