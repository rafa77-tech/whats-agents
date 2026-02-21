"""
Repository para group_entry (links e config).

Sprint 72 - Epic 03
Encapsula acesso ao banco de dados para links de grupo e configuracao.
"""

import logging
from datetime import datetime, UTC
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class GroupEntryRepository:
    """Repository para operacoes de group entry no banco."""

    LINKS_TABLE = "group_links"
    CONFIG_TABLE = "group_entry_config"

    async def buscar_link_por_id(self, link_id: str) -> Optional[dict]:
        """
        Busca um link de grupo por ID.

        Args:
            link_id: ID do link

        Returns:
            Dados do link ou None
        """
        try:
            result = (
                supabase.table(self.LINKS_TABLE)
                .select("*")
                .eq("id", link_id)
                .single()
                .execute()
            )
            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Erro ao buscar link {link_id}: {e}")
            return None

    async def buscar_invite_code(self, link_id: str) -> Optional[str]:
        """
        Busca apenas o invite_code de um link.

        Args:
            link_id: ID do link

        Returns:
            invite_code ou None
        """
        try:
            result = (
                supabase.table(self.LINKS_TABLE)
                .select("invite_code")
                .eq("id", link_id)
                .single()
                .execute()
            )
            if result.data:
                return result.data.get("invite_code")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar invite_code do link {link_id}: {e}")
            return None

    async def buscar_config(self) -> Optional[dict]:
        """
        Retorna configuracao atual do group entry.

        Returns:
            Dados de configuracao ou None
        """
        try:
            result = (
                supabase.table(self.CONFIG_TABLE)
                .select("*")
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Erro ao buscar config de group entry: {e}")
            return None

    async def atualizar_config(self, update_data: dict) -> bool:
        """
        Atualiza configuracao de limites do group entry.

        Args:
            update_data: Campos a atualizar

        Returns:
            True se atualizado com sucesso
        """
        try:
            update_data["updated_at"] = datetime.now(UTC).isoformat()
            supabase.table(self.CONFIG_TABLE).update(update_data).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar config de group entry: {e}")
            return False


# Singleton
group_entry_repository = GroupEntryRepository()
