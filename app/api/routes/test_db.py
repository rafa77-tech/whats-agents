"""
Rotas de teste para validar conexao com banco.
Remover em producao.
"""

from fastapi import APIRouter, HTTPException

from app.services.supabase import supabase

router = APIRouter(prefix="/test", tags=["Test"])


@router.get("/db/connection")
async def test_db_connection():
    """Testa conexao com Supabase."""
    try:
        response = supabase.table("especialidades").select("count", count="exact").execute()
        return {
            "status": "connected",
            "message": "Conexao com Supabase OK",
            "especialidades_count": response.count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro de conexao: {str(e)}")


@router.get("/db/medicos/count")
async def count_medicos():
    """Conta medicos na base."""
    try:
        response = supabase.table("clientes").select("id", count="exact").execute()
        return {
            "total_medicos": response.count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/db/medicos/piloto")
async def get_medicos_piloto():
    """Lista medicos do grupo piloto."""
    try:
        response = (
            supabase.table("clientes")
            .select("id, primeiro_nome, sobrenome, crm, telefone")
            .eq("grupo_piloto", True)
            .limit(10)
            .execute()
        )
        return {
            "count": len(response.data),
            "sample": response.data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.get("/db/vagas/count")
async def count_vagas():
    """Conta vagas na base."""
    try:
        total = supabase.table("vagas").select("id", count="exact").execute()
        abertas = (
            supabase.table("vagas").select("id", count="exact").eq("status", "aberta").execute()
        )
        return {
            "total_vagas": total.count,
            "vagas_abertas": abertas.count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
