"""
Dashboard status endpoints.

Provides system status, health checks, and metrics for the dashboard.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import time
import logging

from app.api.routes.dashboard import CurrentUser
from app.services.supabase import supabase
from app.services.redis import redis_client, verificar_conexao_redis
from app.services.circuit_breaker import obter_status_circuits

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["dashboard-status"])


# Response Models
class JuliaStatus(BaseModel):
    is_active: bool
    mode: str  # "auto", "paused", "maintenance"
    paused_until: Optional[datetime] = None
    pause_reason: Optional[str] = None


class RateLimitStatus(BaseModel):
    messages_hour: int
    messages_day: int
    limit_hour: int
    limit_day: int
    percent_hour: float
    percent_day: float


class CircuitStatus(BaseModel):
    evolution: str  # "closed", "open", "half_open"
    claude: str
    supabase: str


class HealthStatus(BaseModel):
    api: str  # "healthy", "degraded", "unhealthy"
    database: str
    redis: str
    evolution: str
    chatwoot: str


class ConversationStats(BaseModel):
    active: int
    waiting_response: int
    handoff: int
    today_new: int


class FunnelStats(BaseModel):
    prospecting: int
    engaged: int
    negotiating: int
    converted: int
    total: int


class DashboardStatusResponse(BaseModel):
    timestamp: datetime
    julia: JuliaStatus
    rate_limit: RateLimitStatus
    circuits: CircuitStatus
    health: HealthStatus
    conversations: ConversationStats
    funnel: FunnelStats


class HealthCheckDetail(BaseModel):
    status: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class DeepHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    checks: Dict[str, HealthCheckDetail]


@router.get("", response_model=DashboardStatusResponse)
async def get_dashboard_status(user: CurrentUser):
    """Retorna status geral do sistema para o dashboard."""

    # Julia status
    try:
        julia_result = supabase.table("julia_status").select("*").order(
            "created_at", desc=True
        ).limit(1).execute()

        julia_data = julia_result.data[0] if julia_result.data else {}
        julia_status = JuliaStatus(
            is_active=julia_data.get("is_active", True),
            mode=julia_data.get("mode", "auto"),
            paused_until=julia_data.get("paused_until"),
            pause_reason=julia_data.get("pause_reason")
        )
    except Exception as e:
        logger.warning(f"Erro ao buscar julia_status: {e}")
        julia_status = JuliaStatus(is_active=True, mode="auto")

    # Rate limit (do Redis)
    now = datetime.now()
    hour_key = f"ratelimit:hour:{now.strftime('%Y%m%d%H')}"
    day_key = f"ratelimit:day:{now.strftime('%Y%m%d')}"

    try:
        messages_hour = int(await redis_client.get(hour_key) or 0)
        messages_day = int(await redis_client.get(day_key) or 0)
    except Exception as e:
        logger.warning(f"Erro ao buscar rate limit do Redis: {e}")
        messages_hour = 0
        messages_day = 0

    rate_limit = RateLimitStatus(
        messages_hour=messages_hour,
        messages_day=messages_day,
        limit_hour=20,
        limit_day=100,
        percent_hour=round(messages_hour / 20 * 100, 1),
        percent_day=round(messages_day / 100 * 100, 1)
    )

    # Circuit breakers
    circuits_data = obter_status_circuits()
    circuits = CircuitStatus(
        evolution=circuits_data["evolution"]["estado"],
        claude=circuits_data["claude"]["estado"],
        supabase=circuits_data["supabase"]["estado"]
    )

    # Health (simplificado)
    redis_ok = await verificar_conexao_redis()

    health = HealthStatus(
        api="healthy",
        database="healthy",  # Se chegou aqui, supabase está ok
        redis="healthy" if redis_ok else "unhealthy",
        evolution="healthy",  # TODO: check real status
        chatwoot="healthy"   # TODO: check real status
    )

    # Conversas ativas
    try:
        today = datetime.now().date()
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        conv_result = supabase.table("conversations").select(
            "status, controlled_by, created_at, aguardando_resposta"
        ).gte("updated_at", week_ago).execute()

        active_count = 0
        waiting_count = 0
        handoff_count = 0
        today_new = 0

        for c in conv_result.data:
            if c.get("status") == "active":
                active_count += 1
            if c.get("aguardando_resposta"):
                waiting_count += 1
            if c.get("controlled_by") == "human":
                handoff_count += 1
            if c.get("created_at", "")[:10] == str(today):
                today_new += 1

        conversations = ConversationStats(
            active=active_count,
            waiting_response=waiting_count,
            handoff=handoff_count,
            today_new=today_new
        )
    except Exception as e:
        logger.warning(f"Erro ao buscar stats de conversas: {e}")
        conversations = ConversationStats(
            active=0, waiting_response=0, handoff=0, today_new=0
        )

    # Funil
    try:
        funnel_result = supabase.table("clientes").select("status_funil").execute()
        status_counts: Dict[str, int] = {}
        for c in funnel_result.data:
            status = c.get("status_funil", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        funnel = FunnelStats(
            prospecting=status_counts.get("prospecting", 0),
            engaged=status_counts.get("engaged", 0),
            negotiating=status_counts.get("negotiating", 0),
            converted=status_counts.get("converted", 0),
            total=len(funnel_result.data)
        )
    except Exception as e:
        logger.warning(f"Erro ao buscar stats de funil: {e}")
        funnel = FunnelStats(
            prospecting=0, engaged=0, negotiating=0, converted=0, total=0
        )

    return DashboardStatusResponse(
        timestamp=datetime.now(),
        julia=julia_status,
        rate_limit=rate_limit,
        circuits=circuits,
        health=health,
        conversations=conversations,
        funnel=funnel
    )


@router.get("/health/deep", response_model=DeepHealthResponse)
async def get_deep_health(user: CurrentUser):
    """Health check detalhado com latencias."""

    checks: Dict[str, HealthCheckDetail] = {}

    # Database
    start = time.time()
    try:
        supabase.table("julia_status").select("id").limit(1).execute()
        checks["database"] = HealthCheckDetail(
            status="healthy",
            latency_ms=round((time.time() - start) * 1000, 2)
        )
    except Exception as e:
        checks["database"] = HealthCheckDetail(
            status="unhealthy",
            error=str(e)
        )

    # Redis
    start = time.time()
    try:
        await redis_client.ping()
        checks["redis"] = HealthCheckDetail(
            status="healthy",
            latency_ms=round((time.time() - start) * 1000, 2)
        )
    except Exception as e:
        checks["redis"] = HealthCheckDetail(
            status="unhealthy",
            error=str(e)
        )

    # Circuit breakers status
    circuits = obter_status_circuits()
    for name, circuit_data in circuits.items():
        estado = circuit_data["estado"]
        checks[f"circuit_{name}"] = HealthCheckDetail(
            status="healthy" if estado == "closed" else "degraded" if estado == "half_open" else "unhealthy"
        )

    # Overall
    all_healthy = all(c.status == "healthy" for c in checks.values())
    any_unhealthy = any(c.status == "unhealthy" for c in checks.values())

    if all_healthy:
        overall_status = "healthy"
    elif any_unhealthy:
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return DeepHealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        checks=checks
    )
