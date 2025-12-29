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
        """
        Busca médicos que atendem aos filtros (método legado).

        DEPRECATED: Para campanhas, use buscar_alvos_campanha() que já filtra
        por elegibilidade operacional (contact_cap, cooling_off, etc).
        """
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

    async def buscar_alvos_campanha(
        self,
        filtros: Optional[Dict] = None,
        dias_sem_contato: int = 14,
        excluir_cooling: bool = True,
        excluir_em_atendimento: bool = True,
        contact_cap: int = 5,
        limite: int = 1000,
    ) -> List[Dict]:
        """
        Busca médicos elegíveis para campanha.

        Sprint 24 E01: Já filtra por elegibilidade operacional:
        - Não atingiu contact_cap (default 5)
        - Não foi tocado recentemente (default 14 dias)
        - Não está em cooling_off
        - Não tem conversa ativa com humano
        - Não está em atendimento ativo (inbound < 30min)

        Ordem determinística: prioriza nunca tocados, depois por antiguidade.

        Args:
            filtros: Filtros demográficos (especialidade, regiao)
            dias_sem_contato: Mínimo de dias desde último contato
            excluir_cooling: Excluir médicos em cooling_off
            excluir_em_atendimento: Excluir se inbound < 30min
            contact_cap: Limite de contatos em 7 dias
            limite: Máximo de resultados

        Returns:
            Lista de médicos elegíveis com campos:
            - id, nome, telefone, especialidade_nome, regiao
            - last_outbound_at, contact_count_7d
        """
        try:
            response = supabase.rpc("buscar_alvos_campanha", {
                "p_filtros": filtros or {},
                "p_dias_sem_contato": dias_sem_contato,
                "p_excluir_cooling": excluir_cooling,
                "p_excluir_em_atendimento": excluir_em_atendimento,
                "p_contact_cap": contact_cap,
                "p_limite": limite,
            }).execute()

            alvos = response.data or []

            logger.info(
                f"Target set qualificado: {len(alvos)} médicos elegíveis "
                f"(filtros={filtros}, dias_sem_contato={dias_sem_contato}, "
                f"contact_cap={contact_cap}, limite={limite})"
            )

            return alvos

        except Exception as e:
            logger.error(f"Erro ao buscar alvos de campanha: {e}")
            raise


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

