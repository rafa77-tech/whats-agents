"""
Script para analisar performance de queries críticas.
"""
import sys
import time
import asyncio
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.supabase import supabase


def medir_query(nome: str, query_func, iteracoes: int = 10):
    """Mede tempo de execução de uma query."""
    tempos = []
    erros = 0
    
    for _ in range(iteracoes):
        inicio = time.time()
        try:
            query_func()
            tempos.append(time.time() - inicio)
        except Exception as e:
            erros += 1
            print(f"  ⚠️  Erro em {nome}: {e}")
    
    if not tempos:
        return {
            "nome": nome,
            "erro": True,
            "erros": erros
        }
    
    return {
        "nome": nome,
        "media_ms": sum(tempos) / len(tempos) * 1000,
        "max_ms": max(tempos) * 1000,
        "min_ms": min(tempos) * 1000,
        "total": len(tempos),
        "erros": erros
    }


def medir_queries():
    """Mede tempo de execução das queries críticas."""
    print("=" * 60)
    print("ANÁLISE DE PERFORMANCE DE QUERIES")
    print("=" * 60)
    print()
    
    resultados = []
    
    # Query 1: Buscar médico por telefone
    def query_medico():
        return (
            supabase.table("clientes")
            .select("*")
            .eq("telefone", "+5511999999999")
            .limit(1)
            .execute()
        )
    
    print("1. Medindo: buscar_medico_por_telefone...")
    resultados.append(medir_query("buscar_medico_por_telefone", query_medico))
    
    # Query 2: Buscar conversa ativa
    # Precisa de um cliente_id válido, vamos usar um genérico
    def query_conversa():
        return (
            supabase.table("conversations")
            .select("*")
            .eq("status", "active")
            .limit(1)
            .execute()
        )
    
    print("2. Medindo: buscar_conversa_ativa...")
    resultados.append(medir_query("buscar_conversa_ativa", query_conversa))
    
    # Query 3: Carregar histórico
    def query_historico():
        return (
            supabase.table("interacoes")
            .select("*")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
    
    print("3. Medindo: carregar_historico...")
    resultados.append(medir_query("carregar_historico", query_historico))
    
    # Query 4: Buscar vagas
    def query_vagas():
        return (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*)")
            .eq("status", "aberta")
            .limit(10)
            .execute()
        )
    
    print("4. Medindo: buscar_vagas...")
    resultados.append(medir_query("buscar_vagas", query_vagas))
    
    # Exibir resultados
    print()
    print("=" * 60)
    print("RESULTADOS")
    print("=" * 60)
    print()
    
    for r in resultados:
        if r.get("erro"):
            print(f"❌ {r['nome']}: ERRO ({r['erros']} erros)")
        else:
            status = "✅" if r["media_ms"] < 100 else "⚠️" if r["media_ms"] < 500 else "❌"
            print(f"{status} {r['nome']}:")
            print(f"   Média: {r['media_ms']:.2f}ms")
            print(f"   Min: {r['min_ms']:.2f}ms | Max: {r['max_ms']:.2f}ms")
            print(f"   Execuções: {r['total']}")
            if r.get("erros", 0) > 0:
                print(f"   Erros: {r['erros']}")
            print()
    
    # Resumo
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    
    lentas = [r for r in resultados if not r.get("erro") and r["media_ms"] > 100]
    if lentas:
        print(f"⚠️  {len(lentas)} query(s) com tempo > 100ms:")
        for r in lentas:
            print(f"   - {r['nome']}: {r['media_ms']:.2f}ms")
    else:
        print("✅ Todas as queries estão dentro do limite de 100ms")
    
    return resultados


if __name__ == "__main__":
    medir_queries()

