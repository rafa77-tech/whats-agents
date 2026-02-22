"""
Repository para health_incidents.

Sprint 72 - Epic 01
Encapsula acesso ao banco de dados para incidentes de saude.
"""

import logging
from datetime import timedelta
from typing import Optional

from app.core.timezone import agora_utc
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class IncidentsRepository:
    """Repository para operacoes de incidentes de saude no banco."""

    TABLE = "health_incidents"

    async def registrar(self, data: dict) -> Optional[dict]:
        """
        Registra um novo incidente.

        Args:
            data: Dados do incidente (from_status, to_status, etc)

        Returns:
            Incidente criado ou None se erro
        """
        try:
            data["started_at"] = agora_utc().isoformat()
            result = supabase.table(self.TABLE).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Erro ao registrar incidente: {e}")
            return None

    async def listar(
        self,
        limit: int = 20,
        status: Optional[str] = None,
        since: Optional[str] = None,
    ) -> list[dict]:
        """
        Lista incidentes com filtros opcionais.

        Args:
            limit: Maximo de resultados
            status: Filtrar por to_status
            since: Data minima (ISO format)

        Returns:
            Lista de incidentes
        """
        try:
            query = supabase.table(self.TABLE).select("*")

            if status:
                query = query.eq("to_status", status)
            if since:
                query = query.gte("started_at", since)

            result = query.order("started_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Erro ao listar incidentes: {e}")
            return []

    async def buscar_estatisticas(self, dias: int = 30) -> list[dict]:
        """
        Busca dados de incidentes para calculo de estatisticas.

        Args:
            dias: Janela de tempo em dias

        Returns:
            Lista de incidentes com to_status e duration_seconds
        """
        try:
            since = (agora_utc() - timedelta(days=dias)).isoformat()
            result = (
                supabase.table(self.TABLE)
                .select("to_status, duration_seconds")
                .gte("started_at", since)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Erro ao buscar estatisticas de incidentes: {e}")
            return []

    async def buscar_incidente_ativo_critico(self) -> Optional[dict]:
        """
        Busca incidente critico nao resolvido mais recente.

        Returns:
            Incidente ativo ou None
        """
        try:
            result = (
                supabase.table(self.TABLE)
                .select("id, started_at")
                .eq("to_status", "critical")
                .is_("resolved_at", "null")
                .order("started_at", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Erro ao buscar incidente ativo critico: {e}")
            return None

    async def resolver(
        self,
        incident_id: str,
        resolved_at: str,
        duration_seconds: int,
    ) -> bool:
        """
        Marca um incidente como resolvido.

        Args:
            incident_id: ID do incidente
            resolved_at: Timestamp de resolucao (ISO format)
            duration_seconds: Duracao do incidente em segundos

        Returns:
            True se atualizado com sucesso
        """
        try:
            supabase.table(self.TABLE).update(
                {
                    "resolved_at": resolved_at,
                    "duration_seconds": duration_seconds,
                }
            ).eq("id", incident_id).execute()
            logger.info(f"Incidente {incident_id} resolvido apos {duration_seconds}s")
            return True
        except Exception as e:
            logger.error(f"Erro ao resolver incidente {incident_id}: {e}")
            return False


# Singleton
incidents_repository = IncidentsRepository()
