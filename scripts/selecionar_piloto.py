"""
Script para selecionar médicos para o piloto.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.supabase import supabase


def telefone_valido(tel: str) -> bool:
    """Valida formato de telefone brasileiro."""
    if not tel:
        return False
    # Formato: +5511999999999
    return bool(re.match(r'^\+55\d{10,11}$', tel))


def selecionar_medicos_piloto(quantidade: int = 100) -> list:
    """
    Seleciona médicos para piloto usando critérios definidos.

    Prioridade:
    1. Anestesiologistas com CRM
    2. Na região do ABC/SP (DDD 11)
    3. Telefone válido
    4. Não optout
    """
    # Buscar especialidade anestesiologia
    especialidade_resp = (
        supabase.table("especialidades")
        .select("id")
        .eq("nome", "Anestesiologia")
        .single()
        .execute()
    )
    
    if not especialidade_resp.data:
        print("❌ Especialidade 'Anestesiologia' não encontrada no banco")
        return []
    
    especialidade_id = especialidade_resp.data["id"]

    # Buscar médicos elegíveis
    medicos_resp = (
        supabase.table("clientes")
        .select("*")
        .eq("especialidade_id", especialidade_id)
        .not_.is_("crm", "null")
        .not_.is_("telefone", "null")
        .neq("status", "optout")
        .limit(quantidade * 2)  # Buscar mais para filtrar
        .execute()
    )

    medicos = medicos_resp.data or []

    # Filtrar telefones válidos
    medicos_validos = [m for m in medicos if telefone_valido(m.get("telefone"))]

    # Priorizar região ABC (DDDs 11)
    def prioridade(m):
        tel = m.get("telefone", "")
        if tel.startswith("+5511"):
            return 0  # Alta prioridade
        return 1

    medicos_ordenados = sorted(medicos_validos, key=prioridade)

    return medicos_ordenados[:quantidade]


def marcar_como_piloto(medico_ids: list) -> int:
    """Marca médicos selecionados como parte do piloto."""
    total = 0
    
    for medico_id in medico_ids:
        # Buscar médico atual para pegar tags existentes
        medico_resp = (
            supabase.table("clientes")
            .select("tags")
            .eq("id", medico_id)
            .single()
            .execute()
        )
        
        if not medico_resp.data:
            continue
        
        tags_existentes = medico_resp.data.get("tags") or []
        
        # Adicionar tag se não existir
        if "piloto_v1" not in tags_existentes:
            tags_existentes.append("piloto_v1")
        
        # Atualizar médico
        supabase.table("clientes").update({
            "tags": tags_existentes,
            "piloto_selecionado_em": datetime.utcnow().isoformat()
        }).eq("id", medico_id).execute()
        
        total += 1

    return total


def validar_selecao_piloto() -> dict:
    """Valida que seleção está correta."""
    piloto_resp = (
        supabase.table("clientes")
        .select("*")
        .contains("tags", ["piloto_v1"])
        .execute()
    )
    
    piloto = piloto_resp.data or []

    validacao = {
        "total": len(piloto),
        "com_crm": len([m for m in piloto if m.get("crm")]),
        "com_telefone": len([m for m in piloto if m.get("telefone")]),
        "problemas": []
    }

    # Verificar problemas
    for m in piloto:
        if not m.get("telefone"):
            validacao["problemas"].append(f"{m['id']}: sem telefone")
        if m.get("status") == "optout":
            validacao["problemas"].append(f"{m['id']}: fez optout")

    return validacao


def executar_selecao():
    """Script principal de seleção."""
    print("=" * 50)
    print("SELEÇÃO DE MÉDICOS PARA PILOTO")
    print("=" * 50)
    print("\nSelecionando médicos para piloto...")

    medicos = selecionar_medicos_piloto(100)
    print(f"Encontrados {len(medicos)} médicos elegíveis")

    if not medicos:
        print("❌ Nenhum médico encontrado. Verifique os critérios.")
        return

    # Mostrar resumo
    print("\nResumo da seleção:")
    print(f"- Total: {len(medicos)}")
    print(f"- Com CRM: {len([m for m in medicos if m.get('crm')])}")
    print(f"- Região 11: {len([m for m in medicos if m.get('telefone', '').startswith('+5511')])}")

    # Confirmar
    confirmacao = input("\nConfirmar seleção? (s/n): ")
    if confirmacao.lower() == "s":
        ids = [m["id"] for m in medicos]
        total = marcar_como_piloto(ids)
        print(f"✅ {total} médicos marcados como piloto")
        
        # Validar
        print("\nValidando seleção...")
        validacao = validar_selecao_piloto()
        print(f"Total marcados: {validacao['total']}")
        print(f"Com CRM: {validacao['com_crm']}")
        print(f"Com telefone: {validacao['com_telefone']}")
        if validacao['problemas']:
            print(f"⚠️  Problemas encontrados: {len(validacao['problemas'])}")
            for problema in validacao['problemas'][:5]:
                print(f"  - {problema}")
    else:
        print("Cancelado")


if __name__ == "__main__":
    executar_selecao()

