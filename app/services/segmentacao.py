"""
Serviço de segmentação de médicos.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class SegmentacaoService:
    """Gerencia segmentação de médicos para campanhas."""

    CRITERIOS = {
        "especialidade": {
            "campo": "especialidade_nome",
            "operador": "eq"
        },
        "regiao": {
            "campo": "regiao",
            "operador": "eq"
        },
        "status": {
            "campo": "status",
            "operador": "eq"
        },
        "tag": {
            "campo": "tags",
            "operador": "contains"
        },
    }

    async def contar_segmento(self, filtros: Dict) -> int:
        """Conta médicos que atendem aos filtros."""
        query = supabase.table("clientes").select("id", count="exact")

        for criterio, valor in filtros.items():
            config = self.CRITERIOS.get(criterio)
            if not config:
                continue

            if config["operador"] == "eq":
                query = query.eq(config["campo"], valor)
            elif config["operador"] == "contains":
                query = query.contains(config["campo"], [valor])

        # Sempre excluir optout
        query = query.neq("status", "optout")

        response = query.execute()
        return response.count or 0

    async def buscar_segmento(self, filtros: Dict, limite: int = 1000) -> List[Dict]:
        """Busca médicos que atendem aos filtros."""
        query = supabase.table("clientes").select("*")

        for criterio, valor in filtros.items():
            config = self.CRITERIOS.get(criterio)
            if not config:
                continue

            if config["operador"] == "eq":
                query = query.eq(config["campo"], valor)
            elif config["operador"] == "contains":
                query = query.contains(config["campo"], [valor])

        query = query.neq("status", "optout").limit(limite)
        
        response = query.execute()
        return response.data or []


segmentacao_service = SegmentacaoService()


# Segmentos pré-definidos
SEGMENTOS_PREDEFINIDOS = {
    "novos_7_dias": {
        "nome": "Novos últimos 7 dias",
        "filtros": {
            # TODO: implementar filtro por data de criação
        }
    },
    "anestesistas_abc": {
        "nome": "Anestesistas do ABC",
        "filtros": {
            "especialidade": "Anestesiologia",
            "regiao": "abc"
        }
    },
}

