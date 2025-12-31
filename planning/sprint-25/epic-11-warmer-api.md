# Epic 09: API Endpoints

## Objetivo

Expor endpoints REST para gerenciamento completo dos chips de warm-up, permitindo operacoes CRUD e acoes de controle.

## Contexto

A API permite:
- Gerenciar ciclo de vida dos chips
- Monitorar status e health
- Controlar warm-up (start/stop/pause)
- Consultar estatisticas

### Endpoints Planejados

| Metodo | Path | Descricao |
|--------|------|-----------|
| GET | /warmer/chips | Lista todos os chips |
| POST | /warmer/chips | Adiciona novo chip |
| GET | /warmer/chips/{id} | Detalhes do chip |
| DELETE | /warmer/chips/{id} | Remove chip |
| POST | /warmer/chips/{id}/start | Inicia warm-up |
| POST | /warmer/chips/{id}/pause | Pausa warm-up |
| POST | /warmer/chips/{id}/resume | Retoma warm-up |
| GET | /warmer/chips/{id}/health | Historico de health |
| GET | /warmer/chips/{id}/alerts | Alertas do chip |
| GET | /warmer/stats | Estatisticas gerais |
| GET | /warmer/alerts | Todos os alertas |
| POST | /warmer/alerts/{id}/resolve | Resolve alerta |

---

## Story 9.1: Router e Schemas

### Objetivo
Criar router e schemas Pydantic para a API.

### Implementacao

**Arquivo:** `app/api/routes/warmer.py`

```python
"""
API Endpoints do Julia Warmer.

Gerenciamento de chips de warm-up.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

router = APIRouter(prefix="/warmer", tags=["warmer"])


# ══════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════

class ChipStatus(str, Enum):
    PENDING = "pending"
    WARMING = "warming"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    BANNED = "banned"


class FaseWarmup(str, Enum):
    SETUP = "setup"
    PRIMEIROS_CONTATOS = "primeiros_contatos"
    EXPANSAO = "expansao"
    PRE_OPERACAO = "pre_operacao"
    OPERACAO = "operacao"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# ══════════════════════════════════════════
# SCHEMAS DE REQUEST
# ══════════════════════════════════════════

class ChipCreate(BaseModel):
    """Schema para criar chip."""
    telefone: str = Field(..., description="Numero com DDI, ex: 5511999999999")
    instance_name: str = Field(..., description="Nome da instancia Evolution")

    class Config:
        json_schema_extra = {
            "example": {
                "telefone": "5511999999999",
                "instance_name": "warmer-001",
            }
        }


class ChipUpdate(BaseModel):
    """Schema para atualizar chip."""
    status: Optional[ChipStatus] = None
    fase_warmup: Optional[FaseWarmup] = None


# ══════════════════════════════════════════
# SCHEMAS DE RESPONSE
# ══════════════════════════════════════════

class ChipResponse(BaseModel):
    """Response de chip."""
    id: str
    telefone: str
    instance_name: str
    status: ChipStatus
    fase_warmup: FaseWarmup
    health_score: int
    taxa_resposta: float
    msgs_enviadas: int
    msgs_recebidas: int
    grupos_count: int
    warming_started_at: Optional[datetime]
    ready_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ChipListResponse(BaseModel):
    """Response de lista de chips."""
    chips: List[ChipResponse]
    total: int


class HealthHistoryResponse(BaseModel):
    """Response de historico de health."""
    chip_id: str
    history: List[dict]  # [{score, factors, recorded_at}]


class AlertResponse(BaseModel):
    """Response de alerta."""
    id: str
    chip_id: str
    severity: AlertSeverity
    tipo: str
    message: str
    resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime


class AlertListResponse(BaseModel):
    """Response de lista de alertas."""
    alerts: List[AlertResponse]
    total: int


class StatsResponse(BaseModel):
    """Response de estatisticas."""
    chips_total: int
    chips_warming: int
    chips_ready: int
    chips_paused: int
    health_medio: float
    alertas_ativos: int
    conversas_hoje: int
```

### DoD

- [ ] Router criado
- [ ] Enums definidos
- [ ] Schemas de request
- [ ] Schemas de response

---

## Story 9.2: Endpoints de Listagem e Criacao

### Objetivo
Implementar GET /chips e POST /chips.

### Implementacao

```python
from app.services.supabase import supabase


@router.get("/chips", response_model=ChipListResponse)
async def listar_chips(
    status: Optional[ChipStatus] = Query(None, description="Filtrar por status"),
    fase: Optional[FaseWarmup] = Query(None, description="Filtrar por fase"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Lista todos os chips de warm-up.

    Filtros opcionais por status e fase.
    """
    query = supabase.table("warmup_chips").select("*", count="exact")

    if status:
        query = query.eq("status", status.value)

    if fase:
        query = query.eq("fase_warmup", fase.value)

    query = query.order("created_at", desc=True)
    query = query.range(offset, offset + limit - 1)

    result = query.execute()

    return ChipListResponse(
        chips=[ChipResponse(**c) for c in result.data or []],
        total=result.count or 0,
    )


@router.post("/chips", response_model=ChipResponse, status_code=201)
async def criar_chip(chip: ChipCreate):
    """
    Adiciona novo chip ao warm-up.

    O chip inicia com status 'pending'.
    Use POST /chips/{id}/start para iniciar o warm-up.
    """
    # Verificar se ja existe
    existente = supabase.table("warmup_chips") \
        .select("id") \
        .or_(f"telefone.eq.{chip.telefone},instance_name.eq.{chip.instance_name}") \
        .execute()

    if existente.data:
        raise HTTPException(
            status_code=400,
            detail="Telefone ou instance_name ja cadastrado"
        )

    # Criar
    result = supabase.table("warmup_chips") \
        .insert({
            "telefone": chip.telefone,
            "instance_name": chip.instance_name,
            "status": "pending",
            "fase_warmup": "setup",
            "health_score": 40,
        }) \
        .execute()

    return ChipResponse(**result.data[0])
```

### DoD

- [ ] GET /chips com filtros
- [ ] POST /chips com validacao
- [ ] Paginacao funcionando

---

## Story 9.3: Endpoints de Detalhes

### Objetivo
Implementar GET /chips/{id} e DELETE /chips/{id}.

### Implementacao

```python
@router.get("/chips/{chip_id}", response_model=ChipResponse)
async def obter_chip(chip_id: str):
    """
    Obtem detalhes de um chip.
    """
    result = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    return ChipResponse(**result.data)


@router.delete("/chips/{chip_id}", status_code=204)
async def remover_chip(chip_id: str):
    """
    Remove um chip do warm-up.

    Cuidado: Esta acao e irreversivel!
    """
    # Verificar se existe
    chip = supabase.table("warmup_chips") \
        .select("id, status") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    # Nao permitir remover se estiver em warming ativo
    if chip.data["status"] == "warming":
        raise HTTPException(
            status_code=400,
            detail="Pause o chip antes de remover"
        )

    # Remover (cascade deleta pares, conversas, etc)
    supabase.table("warmup_chips") \
        .delete() \
        .eq("id", chip_id) \
        .execute()

    return None


@router.patch("/chips/{chip_id}", response_model=ChipResponse)
async def atualizar_chip(chip_id: str, dados: ChipUpdate):
    """
    Atualiza dados de um chip.
    """
    # Verificar se existe
    chip = supabase.table("warmup_chips") \
        .select("id") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    # Preparar update
    update_data = {}
    if dados.status:
        update_data["status"] = dados.status.value
    if dados.fase_warmup:
        update_data["fase_warmup"] = dados.fase_warmup.value

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")

    result = supabase.table("warmup_chips") \
        .update(update_data) \
        .eq("id", chip_id) \
        .execute()

    return ChipResponse(**result.data[0])
```

### DoD

- [ ] GET /chips/{id}
- [ ] DELETE /chips/{id}
- [ ] PATCH /chips/{id}
- [ ] Validacoes de negocio

---

## Story 9.4: Endpoints de Controle

### Objetivo
Implementar start, pause e resume do warm-up.

### Implementacao

```python
from app.services.warmer.early_warning import retomar_chip
from datetime import datetime, timezone


@router.post("/chips/{chip_id}/start", response_model=ChipResponse)
async def iniciar_warmup(chip_id: str):
    """
    Inicia o warm-up de um chip.

    Requisitos:
    - Chip deve estar com status 'pending' ou 'paused'
    - Instance deve estar conectada
    """
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    if chip.data["status"] not in ["pending", "paused"]:
        raise HTTPException(
            status_code=400,
            detail=f"Status atual ({chip.data['status']}) nao permite inicio"
        )

    # TODO: Verificar se instance esta conectada via Evolution API

    # Atualizar status
    result = supabase.table("warmup_chips") \
        .update({
            "status": "warming",
            "warming_started_at": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", chip_id) \
        .execute()

    return ChipResponse(**result.data[0])


@router.post("/chips/{chip_id}/pause", response_model=ChipResponse)
async def pausar_warmup(chip_id: str):
    """
    Pausa o warm-up de um chip.

    O chip mantem seu progresso e pode ser retomado.
    """
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    if chip.data["status"] != "warming":
        raise HTTPException(
            status_code=400,
            detail=f"Chip nao esta em warming (status: {chip.data['status']})"
        )

    result = supabase.table("warmup_chips") \
        .update({"status": "paused"}) \
        .eq("id", chip_id) \
        .execute()

    return ChipResponse(**result.data[0])


@router.post("/chips/{chip_id}/resume", response_model=ChipResponse)
async def retomar_warmup(chip_id: str):
    """
    Retoma o warm-up de um chip pausado.
    """
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    if chip.data["status"] != "paused":
        raise HTTPException(
            status_code=400,
            detail=f"Chip nao esta pausado (status: {chip.data['status']})"
        )

    # Usar funcao do early_warning que tambem restaura velocidade
    await retomar_chip(chip_id, retomado_por="api")

    # Buscar atualizado
    result = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    return ChipResponse(**result.data[0])
```

### DoD

- [ ] POST /chips/{id}/start
- [ ] POST /chips/{id}/pause
- [ ] POST /chips/{id}/resume
- [ ] Validacoes de estado

---

## Story 9.5: Endpoints de Health e Alertas

### Objetivo
Implementar endpoints para health e alertas.

### Implementacao

```python
from app.services.warmer.health_score import obter_historico_health
from app.services.warmer.early_warning import listar_alertas_ativos, resolver_alerta


@router.get("/chips/{chip_id}/health", response_model=HealthHistoryResponse)
async def obter_health_chip(
    chip_id: str,
    dias: int = Query(7, ge=1, le=30, description="Dias de historico"),
):
    """
    Obtem historico de health score de um chip.
    """
    # Verificar se chip existe
    chip = supabase.table("warmup_chips") \
        .select("id") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        raise HTTPException(status_code=404, detail="Chip nao encontrado")

    historico = await obter_historico_health(chip_id, dias)

    return HealthHistoryResponse(
        chip_id=chip_id,
        history=historico,
    )


@router.get("/chips/{chip_id}/alerts", response_model=AlertListResponse)
async def obter_alertas_chip(
    chip_id: str,
    resolved: Optional[bool] = Query(None, description="Filtrar por resolvido"),
):
    """
    Obtem alertas de um chip.
    """
    query = supabase.table("warmup_alerts") \
        .select("*") \
        .eq("chip_id", chip_id) \
        .order("created_at", desc=True)

    if resolved is not None:
        query = query.eq("resolved", resolved)

    result = query.execute()

    return AlertListResponse(
        alerts=[AlertResponse(**a) for a in result.data or []],
        total=len(result.data or []),
    )


@router.get("/alerts", response_model=AlertListResponse)
async def listar_alertas(
    severity: Optional[AlertSeverity] = Query(None),
    resolved: bool = Query(False, description="Incluir resolvidos"),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Lista todos os alertas do sistema.
    """
    query = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .order("created_at", desc=True)

    if not resolved:
        query = query.eq("resolved", False)

    if severity:
        query = query.eq("severity", severity.value)

    query = query.limit(limit)
    result = query.execute()

    return AlertListResponse(
        alerts=[AlertResponse(**a) for a in result.data or []],
        total=result.count or 0,
    )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolver_alerta_endpoint(alert_id: str):
    """
    Marca um alerta como resolvido.
    """
    # Verificar se existe
    alerta = supabase.table("warmup_alerts") \
        .select("*") \
        .eq("id", alert_id) \
        .single() \
        .execute()

    if not alerta.data:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado")

    if alerta.data["resolved"]:
        raise HTTPException(status_code=400, detail="Alerta ja resolvido")

    await resolver_alerta(alert_id, resolved_by="api")

    # Buscar atualizado
    result = supabase.table("warmup_alerts") \
        .select("*") \
        .eq("id", alert_id) \
        .single() \
        .execute()

    return AlertResponse(**result.data)
```

### DoD

- [ ] GET /chips/{id}/health
- [ ] GET /chips/{id}/alerts
- [ ] GET /alerts
- [ ] POST /alerts/{id}/resolve

---

## Story 9.6: Endpoint de Estatisticas

### Objetivo
Implementar GET /stats com metricas agregadas.

### Implementacao

```python
@router.get("/stats", response_model=StatsResponse)
async def obter_estatisticas():
    """
    Obtem estatisticas gerais do Julia Warmer.
    """
    from datetime import date

    # Total de chips
    total = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .execute()

    # Por status
    warming = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .eq("status", "warming") \
        .execute()

    ready = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .eq("status", "ready") \
        .execute()

    paused = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .eq("status", "paused") \
        .execute()

    # Health medio
    chips_health = supabase.table("warmup_chips") \
        .select("health_score") \
        .eq("status", "warming") \
        .execute()

    health_medio = 0.0
    if chips_health.data:
        health_medio = sum(c["health_score"] for c in chips_health.data) / len(chips_health.data)

    # Alertas ativos
    alertas = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("resolved", False) \
        .execute()

    # Conversas hoje
    hoje = date.today().isoformat()
    conversas = supabase.table("warmup_conversations") \
        .select("*", count="exact") \
        .gte("started_at", f"{hoje}T00:00:00") \
        .execute()

    return StatsResponse(
        chips_total=total.count or 0,
        chips_warming=warming.count or 0,
        chips_ready=ready.count or 0,
        chips_paused=paused.count or 0,
        health_medio=round(health_medio, 1),
        alertas_ativos=alertas.count or 0,
        conversas_hoje=conversas.count or 0,
    )
```

### DoD

- [ ] GET /stats implementado
- [ ] Todas as metricas calculadas
- [ ] Performance aceitavel

---

## Checklist do Epico

- [ ] **S25.E09.1** - Router e schemas
- [ ] **S25.E09.2** - Listagem e criacao
- [ ] **S25.E09.3** - Detalhes
- [ ] **S25.E09.4** - Controle (start/pause/resume)
- [ ] **S25.E09.5** - Health e alertas
- [ ] **S25.E09.6** - Estatisticas
- [ ] Documentacao OpenAPI gerada
- [ ] Validacao de entrada
- [ ] Tratamento de erros
- [ ] Testes de endpoints

---

## Validacao

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_listar_chips():
    """Testa listagem de chips."""
    response = client.get("/warmer/chips")
    assert response.status_code == 200
    assert "chips" in response.json()
    assert "total" in response.json()


def test_criar_chip():
    """Testa criacao de chip."""
    response = client.post("/warmer/chips", json={
        "telefone": "5511999999999",
        "instance_name": "test-instance",
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_obter_stats():
    """Testa estatisticas."""
    response = client.get("/warmer/stats")
    assert response.status_code == 200
    assert "chips_total" in response.json()
    assert "health_medio" in response.json()
```

---

## Documentacao OpenAPI

A API gera documentacao automatica via FastAPI:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Exemplo de Uso

```bash
# Listar chips em warming
curl -X GET "http://localhost:8000/warmer/chips?status=warming"

# Criar chip
curl -X POST "http://localhost:8000/warmer/chips" \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "instance_name": "warmer-001"}'

# Iniciar warm-up
curl -X POST "http://localhost:8000/warmer/chips/{id}/start"

# Obter estatisticas
curl -X GET "http://localhost:8000/warmer/stats"
```

