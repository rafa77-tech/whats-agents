"""
Repositórios do Bounded Context: Campanhas Outbound

Este módulo é a ÚNICA camada que deve conhecer e acessar o Supabase
dentro do contexto de Campanhas. Toda lógica de persistência deve
residir aqui, isolada da lógica de negócio e da camada de interface.

Princípio: ADR-007 — Sem SQL direto em rotas ou serviços de domínio.

Ao substituir o banco de dados (ex: Supabase -> PostgreSQL direto),
apenas este arquivo precisa ser alterado.
"""
import logging
from typing import List, Optional

from app.core.timezone import agora_utc
from app.services.campanhas.types import (
    CampanhaData,
    StatusCampanha,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class CampanhaRepository:
    """
    Repositório de acesso a dados do contexto de Campanhas.

    Encapsula todas as queries ao banco de dados relacionadas a campanhas
    e à fila de mensagens associada a elas. Nenhum outro módulo do contexto
    deve acessar o Supabase diretamente.
    """

    TABLE_CAMPANHAS = "campanhas"
    TABLE_FILA = "fila_mensagens"

    async def buscar_por_id(self, campanha_id: int) -> Optional[CampanhaData]:
        """
        Busca uma campanha pelo seu ID.

        Args:
            campanha_id: O identificador único da campanha.

        Returns:
            Um objeto CampanhaData se encontrado, ou None.
        """
        try:
            response = (
                supabase.table(self.TABLE_CAMPANHAS)
                .select("*")
                .eq("id", campanha_id)
                .single()
                .execute()
            )
            if not response.data:
                return None
            return CampanhaData.from_db_row(response.data)
        except Exception as e:
            logger.error(f"[CampanhaRepository] Erro ao buscar campanha {campanha_id}: {e}")
            return None

    async def listar(
        self,
        status: Optional[str] = None,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> List[CampanhaData]:
        """
        Lista campanhas com filtros opcionais.

        Este método substitui o acesso direto ao Supabase que existia
        no endpoint GET /campanhas/ da rota.

        Args:
            status: Filtro opcional por status da campanha.
            tipo: Filtro opcional por tipo de campanha.
            limit: Número máximo de resultados a retornar.

        Returns:
            Uma lista de objetos CampanhaData.
        """
        try:
            query = supabase.table(self.TABLE_CAMPANHAS).select("*")
            if status:
                query = query.eq("status", status)
            if tipo:
                query = query.eq("tipo_campanha", tipo)
            query = query.order("created_at", desc=True).limit(limit)
            resp = query.execute()
            return [CampanhaData.from_db_row(row) for row in (resp.data or [])]
        except Exception as e:
            logger.error(f"[CampanhaRepository] Erro ao listar campanhas: {e}")
            return []

    async def buscar_envios_da_fila(self, campanha_id: int) -> List[dict]:
        """
        Busca os registros de envio de uma campanha na tabela fila_mensagens.

        Este método substitui o acesso direto ao Supabase que existia
        no endpoint GET /campanhas/{id}/relatorio da rota.

        Args:
            campanha_id: O identificador único da campanha.

        Returns:
            Uma lista de dicionários com os dados dos envios (status, etc.).
        """
        try:
            response = (
                supabase.table(self.TABLE_FILA)
                .select("status")
                .eq("metadata->>campanha_id", str(campanha_id))
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(
                f"[CampanhaRepository] Erro ao buscar envios da fila para campanha {campanha_id}: {e}"
            )
            return []

    async def atualizar_status(
        self,
        campanha_id: int,
        novo_status: StatusCampanha,
    ) -> bool:
        """
        Atualiza o status de uma campanha.

        Args:
            campanha_id: O identificador único da campanha.
            novo_status: O novo status a ser aplicado.

        Returns:
            True se a atualização foi bem-sucedida, False caso contrário.
        """
        data = {
            "status": novo_status.value,
            "updated_at": agora_utc().isoformat(),
        }
        if novo_status == StatusCampanha.ATIVA:
            data["iniciada_em"] = agora_utc().isoformat()
        elif novo_status == StatusCampanha.CONCLUIDA:
            data["concluida_em"] = agora_utc().isoformat()

        try:
            supabase.table(self.TABLE_CAMPANHAS).update(data).eq("id", campanha_id).execute()
            logger.info(
                f"[CampanhaRepository] Campanha {campanha_id} atualizada para '{novo_status.value}'"
            )
            return True
        except Exception as e:
            logger.error(
                f"[CampanhaRepository] Erro ao atualizar status da campanha {campanha_id}: {e}"
            )
            return False


# Instância singleton para uso nos Application Services
campanha_repository = CampanhaRepository()
