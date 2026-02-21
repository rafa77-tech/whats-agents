"""
Repository para campanhas.

Acesso ao banco de dados com nomes de colunas corretos.

Sprint 35 - Epic 03
"""

import logging
from datetime import datetime
from typing import List, Optional

from app.core.timezone import agora_utc
from app.services.campanhas.types import (
    AudienceFilters,
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class CampanhaRepository:
    """Repository para operacoes de campanhas no banco."""

    TABLE = "campanhas"

    async def buscar_por_id(self, campanha_id: int) -> Optional[CampanhaData]:
        """
        Busca campanha por ID.

        Args:
            campanha_id: ID da campanha

        Returns:
            CampanhaData ou None se nao encontrada
        """
        try:
            response = (
                supabase.table(self.TABLE).select("*").eq("id", campanha_id).single().execute()
            )

            if not response.data:
                return None

            return CampanhaData.from_db_row(response.data)

        except Exception as e:
            logger.error(f"Erro ao buscar campanha {campanha_id}: {e}")
            return None

    async def listar_agendadas(self, agora: datetime = None) -> List[CampanhaData]:
        """
        Lista campanhas agendadas para execucao.

        Args:
            agora: Datetime atual (default: utcnow)

        Returns:
            Lista de campanhas agendadas
        """
        agora = agora or agora_utc()

        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("status", StatusCampanha.AGENDADA.value)
                .lte("agendar_para", agora.isoformat())
                .execute()
            )

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas agendadas: {e}")
            return []

    async def listar_ativas(self) -> List[CampanhaData]:
        """
        Lista campanhas ativas.

        Returns:
            Lista de campanhas ativas
        """
        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("status", StatusCampanha.ATIVA.value)
                .execute()
            )

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas ativas: {e}")
            return []

    async def listar(
        self,
        status: Optional[str] = None,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> List[CampanhaData]:
        """
        Lista campanhas com filtros opcionais.

        Args:
            status: Filtrar por status (valor string do enum)
            tipo: Filtrar por tipo de campanha (valor string do enum)
            limit: Limite de resultados

        Returns:
            Lista de CampanhaData
        """
        try:
            query = supabase.table(self.TABLE).select("*")

            if status:
                query = query.eq("status", status)
            if tipo:
                query = query.eq("tipo_campanha", tipo)

            query = query.order("created_at", desc=True).limit(limit)

            response = query.execute()

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas: {e}")
            return []

    async def buscar_envios_da_fila(self, campanha_id: int) -> List[dict]:
        """
        Busca envios de uma campanha na fila_mensagens.

        Args:
            campanha_id: ID da campanha

        Returns:
            Lista de dicts com campo 'status' de cada envio
        """
        try:
            response = (
                supabase.table("fila_mensagens")
                .select("status")
                .eq("metadata->>campanha_id", str(campanha_id))
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Erro ao buscar envios da fila para campanha {campanha_id}: {e}")
            return []

    async def listar_por_status(self, status: StatusCampanha) -> List[CampanhaData]:
        """
        Lista campanhas por status.

        Args:
            status: Status desejado

        Returns:
            Lista de campanhas com o status
        """
        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("status", status.value)
                .order("created_at", desc=True)
                .execute()
            )

            return [CampanhaData.from_db_row(row) for row in (response.data or [])]

        except Exception as e:
            logger.error(f"Erro ao listar campanhas por status {status}: {e}")
            return []

    async def criar(
        self,
        nome_template: str,
        tipo_campanha: TipoCampanha,
        corpo: Optional[str] = None,
        tom: Optional[str] = None,
        agendar_para: Optional[datetime] = None,
        audience_filters: Optional[AudienceFilters] = None,
        pode_ofertar: bool = False,
        objetivo: Optional[str] = None,
        regras: Optional[dict] = None,
        escopo_vagas: Optional[dict] = None,
        created_by: str = "sistema",
    ) -> Optional[CampanhaData]:
        """
        Cria nova campanha.

        Args:
            nome_template: Nome da campanha
            tipo_campanha: Tipo (discovery, oferta, etc)
            corpo: Template da mensagem
            tom: Tom a usar
            agendar_para: Quando iniciar
            audience_filters: Filtros de audiencia
            pode_ofertar: Se pode ofertar vagas
            objetivo: Objetivo da campanha
            regras: Regras de envio
            escopo_vagas: Vagas relacionadas
            created_by: Quem criou

        Returns:
            CampanhaData criada ou None se erro
        """
        status = StatusCampanha.AGENDADA if agendar_para else StatusCampanha.RASCUNHO

        data = {
            "nome_template": nome_template,
            "tipo_campanha": tipo_campanha.value,
            "corpo": corpo,
            "tom": tom,
            "status": status.value,
            "agendar_para": agendar_para.isoformat() if agendar_para else None,
            "audience_filters": audience_filters.to_dict() if audience_filters else {},
            "pode_ofertar": pode_ofertar,
            "objetivo": objetivo,
            "regras": regras,
            "escopo_vagas": escopo_vagas,
            "created_by": created_by,
        }

        try:
            response = supabase.table(self.TABLE).insert(data).execute()

            if not response.data:
                return None

            return CampanhaData.from_db_row(response.data[0])

        except Exception as e:
            logger.error(f"Erro ao criar campanha: {e}")
            return None

    async def atualizar_status(
        self,
        campanha_id: int,
        novo_status: StatusCampanha,
    ) -> bool:
        """
        Atualiza status da campanha.

        Args:
            campanha_id: ID da campanha
            novo_status: Novo status

        Returns:
            True se atualizado com sucesso
        """
        data = {
            "status": novo_status.value,
            "updated_at": agora_utc().isoformat(),
        }

        # Adicionar timestamps especificos
        if novo_status == StatusCampanha.ATIVA:
            data["iniciada_em"] = agora_utc().isoformat()
            data["started_at"] = data["iniciada_em"]
        elif novo_status == StatusCampanha.CONCLUIDA:
            data["concluida_em"] = agora_utc().isoformat()
            data["completed_at"] = data["concluida_em"]

        try:
            supabase.table(self.TABLE).update(data).eq("id", campanha_id).execute()
            logger.info(f"Campanha {campanha_id} atualizada para status {novo_status.value}")

            # Invalidar cache de contexto de campanha
            try:
                from app.services.redis import cache_delete

                await cache_delete(f"campanha:contexto:{campanha_id}")
            except Exception as cache_err:
                logger.debug(f"Erro ao invalidar cache campanha {campanha_id}: {cache_err}")

            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar status da campanha {campanha_id}: {e}")
            return False

    async def incrementar_enviados(self, campanha_id: int, quantidade: int = 1) -> bool:
        """
        Incrementa contador de enviados.

        Args:
            campanha_id: ID da campanha
            quantidade: Quantidade a incrementar

        Returns:
            True se incrementado com sucesso
        """
        try:
            # Buscar valor atual
            response = (
                supabase.table(self.TABLE)
                .select("enviados")
                .eq("id", campanha_id)
                .single()
                .execute()
            )

            if not response.data:
                return False

            atual = response.data.get("enviados", 0) or 0

            # Atualizar
            supabase.table(self.TABLE).update(
                {
                    "enviados": atual + quantidade,
                    "updated_at": agora_utc().isoformat(),
                }
            ).eq("id", campanha_id).execute()

            return True

        except Exception as e:
            logger.error(f"Erro ao incrementar enviados da campanha {campanha_id}: {e}")
            return False

    async def atualizar_total_destinatarios(
        self,
        campanha_id: int,
        total: int,
    ) -> bool:
        """
        Atualiza total de destinatarios.

        Args:
            campanha_id: ID da campanha
            total: Total de destinatarios

        Returns:
            True se atualizado com sucesso
        """
        try:
            supabase.table(self.TABLE).update(
                {
                    "total_destinatarios": total,
                    "updated_at": agora_utc().isoformat(),
                }
            ).eq("id", campanha_id).execute()

            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar total_destinatarios da campanha {campanha_id}: {e}")
            return False

    async def atualizar_contadores(
        self,
        campanha_id: int,
        enviados: Optional[int] = None,
        entregues: Optional[int] = None,
        respondidos: Optional[int] = None,
    ) -> bool:
        """
        Atualiza contadores da campanha.

        Args:
            campanha_id: ID da campanha
            enviados: Novo valor de enviados (opcional)
            entregues: Novo valor de entregues (opcional)
            respondidos: Novo valor de respondidos (opcional)

        Returns:
            True se atualizado com sucesso
        """
        data = {"updated_at": agora_utc().isoformat()}

        if enviados is not None:
            data["enviados"] = enviados
        if entregues is not None:
            data["entregues"] = entregues
        if respondidos is not None:
            data["respondidos"] = respondidos

        if len(data) == 1:  # Só tem updated_at
            return True

        try:
            supabase.table(self.TABLE).update(data).eq("id", campanha_id).execute()
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar contadores da campanha {campanha_id}: {e}")
            return False

    async def listar(
        self,
        status: Optional[str] = None,
        tipo: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Lista campanhas com filtros opcionais.

        Sprint 72 - Epic 04: Mover query de rota para repository.

        Args:
            status: Filtrar por status
            tipo: Filtrar por tipo_campanha
            limit: Maximo de resultados

        Returns:
            Lista de campanhas (dicts)
        """
        try:
            query = supabase.table(self.TABLE).select("*")

            if status:
                query = query.eq("status", status)
            if tipo:
                query = query.eq("tipo_campanha", tipo)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Erro ao listar campanhas: {e}")
            return []

    async def buscar_stats_fila(self, campanha_id: int) -> dict:
        """
        Busca estatisticas de fila para uma campanha.

        Sprint 72 - Epic 04: Mover query de rota para repository.

        Args:
            campanha_id: ID da campanha

        Returns:
            Dict com total, enviados, erros, pendentes
        """
        try:
            response = (
                supabase.table("fila_mensagens")
                .select("status")
                .eq("metadata->>campanha_id", str(campanha_id))
                .execute()
            )

            envios = response.data or []
            enviados = len([e for e in envios if e["status"] == "enviada"])
            erros = len([e for e in envios if e["status"] == "erro"])
            pendentes = len([e for e in envios if e["status"] == "pendente"])

            return {
                "total": len(envios),
                "enviados": enviados,
                "erros": erros,
                "pendentes": pendentes,
                "taxa_entrega": enviados / len(envios) if envios else 0,
            }

        except Exception as e:
            logger.error(f"Erro ao buscar stats de fila da campanha {campanha_id}: {e}")
            return {"total": 0, "enviados": 0, "erros": 0, "pendentes": 0, "taxa_entrega": 0}


# Instancia singleton
campanha_repository = CampanhaRepository()
