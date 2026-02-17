"""
Lookup de hospitais na base CNES local.

Sprint 61 - Épico 1: Busca por similaridade na tabela cnes_estabelecimentos.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)

SCORE_MINIMO_CNES = 0.4


@dataclass
class InfoCNES:
    """Dados de um estabelecimento CNES."""

    cnes_codigo: str
    nome_oficial: str
    cidade: str
    estado: str
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cep: Optional[str] = None
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    score: float = 0.0


async def buscar_hospital_cnes(
    nome: str,
    cidade: Optional[str] = None,
    estado: str = "SP",
) -> Optional[InfoCNES]:
    """
    Busca hospital na tabela CNES local.

    Tenta primeiro com filtro de cidade. Se não encontrar, busca sem filtro.
    Retorna melhor match com score >= SCORE_MINIMO_CNES.
    """
    # Tentativa 1: com cidade
    if cidade and cidade != "Não informada":
        info = await _buscar_cnes_rpc(nome, cidade, estado)
        if info:
            return info

    # Tentativa 2: sem cidade
    info = await _buscar_cnes_rpc(nome, None, estado)
    return info


async def _buscar_cnes_rpc(
    nome: str,
    cidade: Optional[str],
    estado: str,
) -> Optional[InfoCNES]:
    """Chama RPC buscar_cnes_por_nome e retorna melhor match."""
    try:
        result = supabase.rpc(
            "buscar_cnes_por_nome",
            {
                "p_nome": nome,
                "p_cidade": cidade,
                "p_uf": estado,
                "p_limite": 1,
            },
        ).execute()

        if not result.data:
            return None

        row = result.data[0]
        if row["score"] < SCORE_MINIMO_CNES:
            return None

        return InfoCNES(
            cnes_codigo=row["cnes_codigo"],
            nome_oficial=row["nome_fantasia"] or row["razao_social"],
            cidade=row["cidade"],
            estado=row["uf"],
            logradouro=row.get("logradouro"),
            numero=row.get("numero"),
            bairro=row.get("bairro"),
            cep=row.get("cep"),
            telefone=row.get("telefone"),
            latitude=float(row["latitude"]) if row.get("latitude") else None,
            longitude=float(row["longitude"]) if row.get("longitude") else None,
            score=row["score"],
        )

    except Exception as e:
        logger.warning(f"Erro ao buscar CNES: {e}", extra={"nome": nome})
        return None
