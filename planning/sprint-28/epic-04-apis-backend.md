# E04: APIs Backend Base

**Épico:** Endpoints FastAPI para Dashboard
**Estimativa:** 8h
**Prioridade:** P0 (Bloqueante)
**Dependências:** Nenhuma (pode ser feito em paralelo com frontend)

---

## Objetivo

Criar os endpoints REST no backend FastAPI para servir dados ao dashboard:
- Status geral da Julia
- Métricas agregadas
- Dados operacionais
- Ações de controle

---

## Arquitetura

```
/app/api/routes/
├── dashboard/
│   ├── __init__.py
│   ├── status.py          # Status geral + health
│   ├── metrics.py         # Métricas agregadas
│   ├── conversations.py   # Listagem conversas
│   ├── doctors.py         # Gestão médicos
│   ├── shifts.py          # Gestão vagas
│   ├── campaigns.py       # Campanhas
│   ├── controls.py        # Controles operacionais
│   ├── notifications.py   # Notificações
│   └── audit.py           # Logs de auditoria
```

---

## Stories

### S04.1: Router Base + Auth Middleware

**Arquivo:** `app/api/routes/dashboard/__init__.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated

from app.core.auth import get_current_user, require_role
from app.models.dashboard import DashboardUser, UserRole

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Dependency para usuário autenticado
CurrentUser = Annotated[DashboardUser, Depends(get_current_user)]

# Dependencies para roles específicas
def require_viewer():
    return Depends(require_role(UserRole.VIEWER))

def require_operator():
    return Depends(require_role(UserRole.OPERATOR))

def require_manager():
    return Depends(require_role(UserRole.MANAGER))

def require_admin():
    return Depends(require_role(UserRole.ADMIN))
```

**Arquivo:** `app/core/auth.py` (adicionar)

```python
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from enum import Enum

from app.services.supabase import supabase

security = HTTPBearer()

class UserRole(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    MANAGER = "manager"
    ADMIN = "admin"

ROLE_HIERARCHY = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}

class DashboardUser:
    def __init__(self, id: str, email: str, role: UserRole, name: str):
        self.id = id
        self.email = email
        self.role = role
        self.name = name

    def has_permission(self, required_role: UserRole) -> bool:
        return ROLE_HIERARCHY[self.role] >= ROLE_HIERARCHY[required_role]

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> DashboardUser:
    """Valida JWT do Supabase e retorna usuário do dashboard."""
    token = credentials.credentials

    try:
        # Verificar token com Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        auth_user = user_response.user

        # Buscar dados do dashboard_users
        result = supabase.table("dashboard_users").select("*").eq(
            "auth_user_id", auth_user.id
        ).single().execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não tem acesso ao dashboard"
            )

        return DashboardUser(
            id=result.data["id"],
            email=auth_user.email,
            role=UserRole(result.data["role"]),
            name=result.data["name"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro de autenticação: {str(e)}"
        )

def require_role(required_role: UserRole):
    """Dependency factory para verificar role mínima."""
    async def check_role(user: DashboardUser = Depends(get_current_user)):
        if not user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requer permissão: {required_role.value}"
            )
        return user
    return check_role
```

**DoD:**
- [ ] Router base criado
- [ ] Auth middleware funcionando
- [ ] Verificação de roles implementada

---

### S04.2: Endpoint de Status Geral

**Arquivo:** `app/api/routes/dashboard/status.py`

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from app.api.routes.dashboard import CurrentUser
from app.services.supabase import supabase
from app.services.redis_client import redis_client
from app.services.circuit_breaker import get_circuit_status

router = APIRouter(prefix="/status", tags=["dashboard-status"])

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
    evolution: str  # "closed", "open", "half-open"
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

class DashboardStatus(BaseModel):
    timestamp: datetime
    julia: JuliaStatus
    rate_limit: RateLimitStatus
    circuits: CircuitStatus
    health: HealthStatus
    conversations: ConversationStats
    funnel: FunnelStats

@router.get("", response_model=DashboardStatus)
async def get_dashboard_status(user: CurrentUser):
    """Retorna status geral do sistema para o dashboard."""

    # Julia status
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

    # Rate limit (do Redis)
    now = datetime.now()
    hour_key = f"ratelimit:hour:{now.strftime('%Y%m%d%H')}"
    day_key = f"ratelimit:day:{now.strftime('%Y%m%d')}"

    messages_hour = int(redis_client.get(hour_key) or 0)
    messages_day = int(redis_client.get(day_key) or 0)

    rate_limit = RateLimitStatus(
        messages_hour=messages_hour,
        messages_day=messages_day,
        limit_hour=20,
        limit_day=100,
        percent_hour=round(messages_hour / 20 * 100, 1),
        percent_day=round(messages_day / 100 * 100, 1)
    )

    # Circuit breakers
    circuits = CircuitStatus(
        evolution=get_circuit_status("evolution"),
        claude=get_circuit_status("claude"),
        supabase=get_circuit_status("supabase")
    )

    # Health (simplificado)
    health = HealthStatus(
        api="healthy",
        database="healthy" if supabase else "unhealthy",
        redis="healthy" if redis_client.ping() else "unhealthy",
        evolution="healthy",  # TODO: check real status
        chatwoot="healthy"   # TODO: check real status
    )

    # Conversas ativas
    today = datetime.now().date()
    conv_result = supabase.table("conversations").select(
        "status", "controlled_by", "created_at"
    ).gte("updated_at", (datetime.now() - timedelta(days=7)).isoformat()).execute()

    conversations = ConversationStats(
        active=len([c for c in conv_result.data if c["status"] == "active"]),
        waiting_response=len([c for c in conv_result.data
                             if c["status"] == "active" and c.get("waiting_response")]),
        handoff=len([c for c in conv_result.data if c["controlled_by"] == "human"]),
        today_new=len([c for c in conv_result.data
                      if c["created_at"][:10] == str(today)])
    )

    # Funil
    funnel_result = supabase.table("clientes").select("status_funil").execute()
    status_counts = {}
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

    return DashboardStatus(
        timestamp=datetime.now(),
        julia=julia_status,
        rate_limit=rate_limit,
        circuits=circuits,
        health=health,
        conversations=conversations,
        funnel=funnel
    )

@router.get("/health/deep")
async def get_deep_health(user: CurrentUser):
    """Health check detalhado com latências."""
    import time

    checks = {}

    # Database
    start = time.time()
    try:
        supabase.table("julia_status").select("id").limit(1).execute()
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    start = time.time()
    try:
        redis_client.ping()
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # Overall
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    }
```

**DoD:**
- [ ] Endpoint `/dashboard/status` funcionando
- [ ] Retorna status Julia, rate limit, circuits, health
- [ ] Retorna métricas de conversas e funil

---

### S04.3: Endpoints de Controles

**Arquivo:** `app/api/routes/dashboard/controls.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from app.api.routes.dashboard import CurrentUser, require_operator, require_manager, require_admin
from app.services.supabase import supabase
from app.core.auth import DashboardUser, UserRole

router = APIRouter(prefix="/controls", tags=["dashboard-controls"])

# Models
class JuliaToggleRequest(BaseModel):
    active: bool
    reason: Optional[str] = None

class JuliaPauseRequest(BaseModel):
    duration_minutes: int
    reason: str

class FeatureFlagUpdate(BaseModel):
    enabled: bool

class RateLimitUpdate(BaseModel):
    messages_per_hour: int
    messages_per_day: int

# Endpoints

@router.post("/julia/toggle")
async def toggle_julia(
    request: JuliaToggleRequest,
    user: DashboardUser = Depends(require_operator())
):
    """Liga/desliga Julia. Requer role operator+."""

    result = supabase.table("julia_status").insert({
        "is_active": request.active,
        "mode": "auto" if request.active else "paused",
        "pause_reason": request.reason if not request.active else None,
        "changed_by": user.email,
        "created_at": datetime.now().isoformat()
    }).execute()

    # Log de auditoria
    supabase.table("audit_logs").insert({
        "action": "julia_toggle",
        "actor_email": user.email,
        "actor_role": user.role.value,
        "details": {
            "active": request.active,
            "reason": request.reason
        },
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "is_active": request.active}

@router.post("/julia/pause")
async def pause_julia(
    request: JuliaPauseRequest,
    user: DashboardUser = Depends(require_operator())
):
    """Pausa Julia por tempo determinado."""

    paused_until = datetime.now() + timedelta(minutes=request.duration_minutes)

    result = supabase.table("julia_status").insert({
        "is_active": False,
        "mode": "paused",
        "paused_until": paused_until.isoformat(),
        "pause_reason": request.reason,
        "changed_by": user.email,
        "created_at": datetime.now().isoformat()
    }).execute()

    # Log
    supabase.table("audit_logs").insert({
        "action": "julia_pause",
        "actor_email": user.email,
        "actor_role": user.role.value,
        "details": {
            "duration_minutes": request.duration_minutes,
            "paused_until": paused_until.isoformat(),
            "reason": request.reason
        },
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "paused_until": paused_until}

@router.get("/flags")
async def list_feature_flags(user: CurrentUser):
    """Lista feature flags. Viewer+."""

    result = supabase.table("feature_flags").select("*").execute()
    return {"flags": result.data}

@router.put("/flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagUpdate,
    user: DashboardUser = Depends(require_manager())
):
    """Atualiza feature flag. Requer manager+."""

    # Verificar se existe
    existing = supabase.table("feature_flags").select("*").eq(
        "name", flag_name
    ).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Flag não encontrada")

    result = supabase.table("feature_flags").update({
        "enabled": request.enabled,
        "updated_by": user.email,
        "updated_at": datetime.now().isoformat()
    }).eq("name", flag_name).execute()

    # Log
    supabase.table("audit_logs").insert({
        "action": "feature_flag_update",
        "actor_email": user.email,
        "actor_role": user.role.value,
        "details": {
            "flag": flag_name,
            "enabled": request.enabled
        },
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "flag": flag_name, "enabled": request.enabled}

@router.put("/rate-limit")
async def update_rate_limit(
    request: RateLimitUpdate,
    user: DashboardUser = Depends(require_admin())
):
    """Atualiza limites de rate. Requer admin."""

    # Validações
    if request.messages_per_hour < 1 or request.messages_per_hour > 50:
        raise HTTPException(400, "Limite por hora deve ser entre 1 e 50")
    if request.messages_per_day < 10 or request.messages_per_day > 200:
        raise HTTPException(400, "Limite por dia deve ser entre 10 e 200")

    result = supabase.table("system_config").upsert({
        "key": "rate_limit",
        "value": {
            "messages_per_hour": request.messages_per_hour,
            "messages_per_day": request.messages_per_day
        },
        "updated_by": user.email,
        "updated_at": datetime.now().isoformat()
    }).execute()

    # Log
    supabase.table("audit_logs").insert({
        "action": "rate_limit_update",
        "actor_email": user.email,
        "actor_role": user.role.value,
        "details": {
            "messages_per_hour": request.messages_per_hour,
            "messages_per_day": request.messages_per_day
        },
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "new_limits": request.model_dump()}

@router.post("/circuit/{service}/reset")
async def reset_circuit_breaker(
    service: str,
    user: DashboardUser = Depends(require_manager())
):
    """Reset circuit breaker. Requer manager+."""
    from app.services.circuit_breaker import reset_circuit

    valid_services = ["evolution", "claude", "supabase", "chatwoot"]
    if service not in valid_services:
        raise HTTPException(400, f"Serviço inválido. Use: {valid_services}")

    reset_circuit(service)

    # Log
    supabase.table("audit_logs").insert({
        "action": "circuit_reset",
        "actor_email": user.email,
        "actor_role": user.role.value,
        "details": {"service": service},
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "service": service, "status": "closed"}
```

**DoD:**
- [ ] Toggle Julia funcionando
- [ ] Pause com tempo funcionando
- [ ] Feature flags CRUD
- [ ] Rate limit configurável (admin only)
- [ ] Reset de circuit breakers
- [ ] Logs de auditoria para todas ações

---

### S04.4: Endpoints de Conversas

**Arquivo:** `app/api/routes/dashboard/conversations.py`

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.api.routes.dashboard import CurrentUser, require_operator
from app.services.supabase import supabase
from app.core.auth import DashboardUser

router = APIRouter(prefix="/conversations", tags=["dashboard-conversations"])

class ConversationSummary(BaseModel):
    id: str
    cliente_id: str
    cliente_nome: str
    cliente_telefone: str
    status: str
    controlled_by: str
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int
    created_at: datetime

class ConversationDetail(BaseModel):
    id: str
    cliente: dict
    messages: List[dict]
    status: str
    controlled_by: str
    handoff_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

class PaginatedResponse(BaseModel):
    data: List[ConversationSummary]
    total: int
    page: int
    per_page: int
    pages: int

@router.get("", response_model=PaginatedResponse)
async def list_conversations(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    controlled_by: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista conversas com filtros e paginação."""

    query = supabase.table("conversations").select(
        "*, clientes(nome, telefone)"
    )

    if status:
        query = query.eq("status", status)
    if controlled_by:
        query = query.eq("controlled_by", controlled_by)
    if search:
        # Busca por nome ou telefone (via join)
        query = query.or_(f"clientes.nome.ilike.%{search}%,clientes.telefone.ilike.%{search}%")

    # Count total
    count_result = query.execute()
    total = len(count_result.data)

    # Paginar
    offset = (page - 1) * per_page
    query = query.order("updated_at", desc=True).range(offset, offset + per_page - 1)
    result = query.execute()

    # Mapear para response
    conversations = []
    for conv in result.data:
        cliente = conv.get("clientes", {})
        conversations.append(ConversationSummary(
            id=conv["id"],
            cliente_id=conv["cliente_id"],
            cliente_nome=cliente.get("nome", "Desconhecido"),
            cliente_telefone=cliente.get("telefone", ""),
            status=conv["status"],
            controlled_by=conv["controlled_by"],
            last_message=conv.get("last_message"),
            last_message_at=conv.get("last_message_at"),
            unread_count=conv.get("unread_count", 0),
            created_at=conv["created_at"]
        ))

    return PaginatedResponse(
        data=conversations,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, user: CurrentUser):
    """Detalhes de uma conversa com mensagens."""

    # Conversa
    conv_result = supabase.table("conversations").select(
        "*, clientes(*)"
    ).eq("id", conversation_id).single().execute()

    if not conv_result.data:
        raise HTTPException(404, "Conversa não encontrada")

    conv = conv_result.data

    # Mensagens (últimas 100)
    msgs_result = supabase.table("interacoes").select("*").eq(
        "conversa_id", conversation_id
    ).order("created_at", desc=True).limit(100).execute()

    return ConversationDetail(
        id=conv["id"],
        cliente=conv.get("clientes", {}),
        messages=list(reversed(msgs_result.data)),  # Ordem cronológica
        status=conv["status"],
        controlled_by=conv["controlled_by"],
        handoff_reason=conv.get("handoff_reason"),
        created_at=conv["created_at"],
        updated_at=conv["updated_at"]
    )

@router.post("/{conversation_id}/handoff")
async def trigger_handoff(
    conversation_id: str,
    user: DashboardUser = Depends(require_operator())
):
    """Força handoff para humano."""

    result = supabase.table("conversations").update({
        "controlled_by": "human",
        "handoff_reason": f"Manual via dashboard por {user.email}",
        "updated_at": datetime.now().isoformat()
    }).eq("id", conversation_id).execute()

    # Log
    supabase.table("audit_logs").insert({
        "action": "manual_handoff",
        "actor_email": user.email,
        "details": {"conversation_id": conversation_id},
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "controlled_by": "human"}

@router.post("/{conversation_id}/return-to-julia")
async def return_to_julia(
    conversation_id: str,
    user: DashboardUser = Depends(require_operator())
):
    """Retorna conversa para Julia."""

    result = supabase.table("conversations").update({
        "controlled_by": "julia",
        "handoff_reason": None,
        "updated_at": datetime.now().isoformat()
    }).eq("id", conversation_id).execute()

    # Log
    supabase.table("audit_logs").insert({
        "action": "return_to_julia",
        "actor_email": user.email,
        "details": {"conversation_id": conversation_id},
        "created_at": datetime.now().isoformat()
    }).execute()

    return {"success": True, "controlled_by": "julia"}
```

**DoD:**
- [ ] Listagem com paginação
- [ ] Filtros por status, controlled_by, search
- [ ] Detalhes com mensagens
- [ ] Ações de handoff/return

---

### S04.5: Registrar Routers no Main

**Arquivo:** `app/main.py` (adicionar)

```python
# Importar routers do dashboard
from app.api.routes.dashboard import status as dashboard_status
from app.api.routes.dashboard import controls as dashboard_controls
from app.api.routes.dashboard import conversations as dashboard_conversations

# ... após criar app ...

# Dashboard routes
app.include_router(dashboard_status.router)
app.include_router(dashboard_controls.router)
app.include_router(dashboard_conversations.router)
```

**DoD:**
- [ ] Todos os routers registrados
- [ ] Swagger mostrando endpoints
- [ ] Testes manuais passando

---

## Checklist Final

- [ ] Auth middleware com JWT Supabase
- [ ] RBAC funcionando (viewer → admin)
- [ ] Endpoint status geral
- [ ] Endpoints de controle (toggle, pause, flags, rate limit)
- [ ] Endpoints de conversas (list, detail, handoff)
- [ ] Logs de auditoria em todas ações
- [ ] Routers registrados no main.py
- [ ] Testes manuais via Swagger
