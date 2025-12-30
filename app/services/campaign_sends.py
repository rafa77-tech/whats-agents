"""
Repository unificado para envios de campanha.

Sprint 23 E03 - Fonte unica de verdade via views.

Este modulo fornece acesso unificado aos envios de campanha,
combinando dados de fila_mensagens (novo) e envios (legado).

USO:
    from app.services.campaign_sends import campaign_sends_repo

    # Buscar envios de uma campanha
    envios = await campaign_sends_repo.listar_por_campanha(campaign_id)

    # Buscar metricas
    metricas = await campaign_sends_repo.buscar_metricas(campaign_id)

DEPRECATION:
    NAO use diretamente as tabelas `envios` ou `fila_mensagens` para
    queries de campanha. Use sempre este repository.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class CampaignSend:
    """Representa um envio de campanha (unificado)."""
    send_id: str
    cliente_id: str
    campaign_id: int
    send_type: str
    queue_status: str
    outcome: Optional[str]
    outcome_reason_code: Optional[str]
    provider_message_id: Optional[str]
    queued_at: datetime
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    outcome_at: Optional[datetime]
    source_table: str  # 'fila_mensagens' ou 'envios'


@dataclass
class CampaignMetrics:
    """
    Metricas agregadas de uma campanha.

    Sprint 24 E07: Adicionado bypassed, delivered_total, e breakdown por origem.
    Sprint 23 Prod: Adicionado breakdown de falhas para diagnóstico.
    """
    campaign_id: int
    total_sends: int
    delivered: int
    bypassed: int
    delivered_total: int
    blocked: int
    deduped: int
    failed: int
    pending: int
    delivery_rate: float
    delivery_rate_total: float
    block_rate: float
    first_send_at: Optional[datetime]
    last_send_at: Optional[datetime]
    # Breakdown por origem (monitorar migração legado → novo)
    from_fila_mensagens: int = 0
    from_envios_legado: int = 0
    # Breakdown de falhas para diagnóstico operacional
    failed_validation: int = 0   # Número inválido/inexistente
    failed_banned: int = 0       # Número banido/bloqueado
    failed_provider: int = 0     # Erro de infra (timeout, 5xx)
    validation_fail_rate: float = 0.0  # % de validação falha
    banned_rate: float = 0.0           # % de banidos (risco reputacional)

    @property
    def fail_rate(self) -> float:
        """Taxa de falha total."""
        if self.total_sends == 0:
            return 0.0
        return round(self.failed / self.total_sends * 100, 2)

    @property
    def legado_ratio(self) -> float:
        """Percentual de envios ainda vindo do legado."""
        if self.total_sends == 0:
            return 0.0
        return round(self.from_envios_legado / self.total_sends * 100, 2)

    @property
    def target_quality_score(self) -> float:
        """
        Score de qualidade do target set (0-100).
        100 = nenhum número inválido ou banido.
        """
        if self.total_sends == 0:
            return 100.0
        bad_targets = self.failed_validation + self.failed_banned
        return round((1 - bad_targets / self.total_sends) * 100, 2)


class CampaignSendsRepository:
    """
    Repository para envios de campanha.

    Usa as views `campaign_sends` e `campaign_metrics` para
    fornecer acesso unificado aos dados.
    """

    async def listar_por_campanha(
        self,
        campaign_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CampaignSend]:
        """
        Lista envios de uma campanha.

        Args:
            campaign_id: ID da campanha
            limit: Maximo de registros
            offset: Offset para paginacao

        Returns:
            Lista de CampaignSend
        """
        response = (
            supabase.table("campaign_sends")
            .select("*")
            .eq("campaign_id", campaign_id)
            .order("queued_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        if not response.data:
            return []

        return [self._parse_send(row) for row in response.data]

    async def buscar_metricas(
        self,
        campaign_id: int,
    ) -> Optional[CampaignMetrics]:
        """
        Busca metricas agregadas de uma campanha.

        Args:
            campaign_id: ID da campanha

        Returns:
            CampaignMetrics ou None se campanha nao encontrada
        """
        response = (
            supabase.table("campaign_metrics")
            .select("*")
            .eq("campaign_id", campaign_id)
            .single()
            .execute()
        )

        if not response.data:
            return None

        return self._parse_metrics(response.data)

    async def listar_metricas_todas(
        self,
        limit: int = 50,
    ) -> List[CampaignMetrics]:
        """
        Lista metricas de todas as campanhas.

        Args:
            limit: Maximo de campanhas

        Returns:
            Lista de CampaignMetrics ordenada por total_sends desc
        """
        response = (
            supabase.table("campaign_metrics")
            .select("*")
            .order("total_sends", desc=True)
            .limit(limit)
            .execute()
        )

        if not response.data:
            return []

        return [self._parse_metrics(row) for row in response.data]

    async def contar_por_outcome(
        self,
        campaign_id: int,
    ) -> dict:
        """
        Conta envios agrupados por outcome.

        Args:
            campaign_id: ID da campanha

        Returns:
            Dict com contagem por outcome
        """
        response = (
            supabase.table("campaign_sends")
            .select("outcome")
            .eq("campaign_id", campaign_id)
            .execute()
        )

        if not response.data:
            return {}

        contagem = {}
        for row in response.data:
            outcome = row.get("outcome") or "PENDING"
            contagem[outcome] = contagem.get(outcome, 0) + 1

        return contagem

    async def buscar_envios_recentes(
        self,
        campaign_id: int,
        horas: int = 24,
    ) -> List[CampaignSend]:
        """
        Busca envios recentes de uma campanha.

        Args:
            campaign_id: ID da campanha
            horas: Janela de tempo em horas

        Returns:
            Lista de envios nas ultimas X horas
        """
        desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()

        response = (
            supabase.table("campaign_sends")
            .select("*")
            .eq("campaign_id", campaign_id)
            .gte("queued_at", desde)
            .order("queued_at", desc=True)
            .execute()
        )

        if not response.data:
            return []

        return [self._parse_send(row) for row in response.data]

    async def buscar_por_cliente(
        self,
        cliente_id: str,
        limit: int = 20,
    ) -> List[CampaignSend]:
        """
        Busca envios de campanha para um cliente.

        Args:
            cliente_id: ID do cliente
            limit: Maximo de registros

        Returns:
            Lista de envios para o cliente
        """
        response = (
            supabase.table("campaign_sends")
            .select("*")
            .eq("cliente_id", cliente_id)
            .order("queued_at", desc=True)
            .limit(limit)
            .execute()
        )

        if not response.data:
            return []

        return [self._parse_send(row) for row in response.data]

    def _parse_send(self, row: dict) -> CampaignSend:
        """Converte row do banco para CampaignSend."""
        return CampaignSend(
            send_id=row["send_id"],
            cliente_id=row["cliente_id"],
            campaign_id=row["campaign_id"],
            send_type=row.get("send_type", ""),
            queue_status=row.get("queue_status", ""),
            outcome=row.get("outcome"),
            outcome_reason_code=row.get("outcome_reason_code"),
            provider_message_id=row.get("provider_message_id"),
            queued_at=self._parse_datetime(row.get("queued_at")),
            scheduled_for=self._parse_datetime(row.get("scheduled_for")),
            sent_at=self._parse_datetime(row.get("sent_at")),
            outcome_at=self._parse_datetime(row.get("outcome_at")),
            source_table=row.get("source_table", "unknown"),
        )

    def _parse_metrics(self, row: dict) -> CampaignMetrics:
        """Converte row do banco para CampaignMetrics."""
        return CampaignMetrics(
            campaign_id=row["campaign_id"],
            total_sends=row.get("total_sends", 0),
            delivered=row.get("delivered", 0),
            bypassed=row.get("bypassed", 0),
            delivered_total=row.get("delivered_total", 0),
            blocked=row.get("blocked", 0),
            deduped=row.get("deduped", 0),
            failed=row.get("failed", 0),
            pending=row.get("pending", 0),
            delivery_rate=float(row.get("delivery_rate") or 0),
            delivery_rate_total=float(row.get("delivery_rate_total") or 0),
            block_rate=float(row.get("block_rate") or 0),
            first_send_at=self._parse_datetime(row.get("first_send_at")),
            last_send_at=self._parse_datetime(row.get("last_send_at")),
            from_fila_mensagens=row.get("from_fila_mensagens", 0),
            from_envios_legado=row.get("from_envios_legado", 0),
            # Breakdown de falhas para diagnóstico
            failed_validation=row.get("failed_validation", 0),
            failed_banned=row.get("failed_banned", 0),
            failed_provider=row.get("failed_provider", 0),
            validation_fail_rate=float(row.get("validation_fail_rate") or 0),
            banned_rate=float(row.get("banned_rate") or 0),
        )

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime string para objeto."""
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


# Singleton para uso global
campaign_sends_repo = CampaignSendsRepository()
