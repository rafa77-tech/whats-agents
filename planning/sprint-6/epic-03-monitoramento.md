# Epic 3: Monitoramento

## Objetivo do Epic

> **Monitorar saúde e uso das instâncias em tempo real.**

Este epic fornece visibilidade sobre o estado do sistema multi-instância.

---

## Stories

1. [S6.E3.1 - Dashboard de Status](#s6e31---dashboard-de-status)
2. [S6.E3.2 - Alertas](#s6e32---alertas)

---

# S6.E3.1 - Dashboard de Status

## Objetivo

> **Endpoint que mostra status consolidado de todas as instâncias.**

---

## Tarefas

### 1. Criar endpoint de dashboard

```python
# app/api/routes/dashboard.py

from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/instances")
async def dashboard_instancias():
    """
    Dashboard completo das instâncias.
    """
    from app.services.instance_manager import instance_manager

    instancias = await instance_manager.listar_instancias(apenas_ativas=False)

    # Calcular métricas
    total = len(instancias)
    online = sum(1 for i in instancias if i.status == "connected")
    banidas = sum(1 for i in instancias if i.status == "banned")

    capacidade_total = sum(i.capacidade_dia for i in instancias if i.status == "connected")
    enviadas_hoje = sum(i.msgs_enviadas_dia for i in instancias)
    capacidade_usada = (enviadas_hoje / capacidade_total * 100) if capacidade_total > 0 else 0

    # Determinar status geral
    if online == 0:
        status_geral = "critical"
    elif online < total / 2:
        status_geral = "degraded"
    elif capacidade_usada > 80:
        status_geral = "warning"
    else:
        status_geral = "healthy"

    return {
        "status": status_geral,
        "timestamp": datetime.now().isoformat(),
        "resumo": {
            "total_instancias": total,
            "online": online,
            "offline": total - online - banidas,
            "banidas": banidas,
            "capacidade_dia": capacidade_total,
            "enviadas_hoje": enviadas_hoje,
            "capacidade_usada_pct": f"{capacidade_usada:.1f}%",
        },
        "instancias": [
            {
                "nome": i.nome,
                "numero": i.numero_telefone,
                "status": i.status,
                "status_emoji": _status_emoji(i.status),
                "msgs_hora": f"{i.msgs_enviadas_hora}/{i.capacidade_hora}",
                "msgs_dia": f"{i.msgs_enviadas_dia}/{i.capacidade_dia}",
                "carga": f"{i.carga_percentual:.1f}%",
                "ultima_msg": i.ultima_msg_at.isoformat() if i.ultima_msg_at else None,
            }
            for i in instancias
        ]
    }


def _status_emoji(status: str) -> str:
    """Retorna emoji para status."""
    return {
        "connected": "🟢",
        "disconnected": "🔴",
        "banned": "⛔",
        "connecting": "🟡",
    }.get(status, "❓")


@router.get("/instances/{nome}")
async def detalhe_instancia(nome: str):
    """
    Detalhes de uma instância específica.
    """
    from app.services.instance_manager import instance_manager

    instancia = await instance_manager.obter_instancia(nome)

    if not instancia:
        raise HTTPException(404, "Instância não encontrada")

    # Buscar médicos atribuídos
    response = (
        supabase.table("clientes")
        .select("id", count="exact")
        .eq("instancia_preferida", nome)
        .execute()
    )
    medicos_atribuidos = response.count or 0

    # Histórico de uso (últimas 24h)
    # ... (implementar se necessário)

    return {
        "nome": instancia.nome,
        "numero": instancia.numero_telefone,
        "status": instancia.status,
        "capacidade": {
            "hora": instancia.capacidade_hora,
            "dia": instancia.capacidade_dia,
        },
        "uso": {
            "msgs_hora": instancia.msgs_enviadas_hora,
            "msgs_dia": instancia.msgs_enviadas_dia,
            "carga_pct": instancia.carga_percentual,
        },
        "medicos_atribuidos": medicos_atribuidos,
        "ultima_msg": instancia.ultima_msg_at.isoformat() if instancia.ultima_msg_at else None,
    }
```

### 2. Endpoint de health agregado

```python
@router.get("/health")
async def health_geral():
    """
    Health check geral do sistema.
    """
    from app.services.instance_manager import instance_manager
    from app.services.circuit_breaker import obter_status_circuits

    # Status instâncias
    instancias = await instance_manager.listar_instancias()
    instancias_online = sum(1 for i in instancias if i.status == "connected")

    # Status circuits
    circuits = obter_status_circuits()
    circuits_ok = sum(1 for c in circuits.values() if c["estado"] == "closed")

    # Redis
    redis_ok = await verificar_conexao_redis()

    # Supabase
    try:
        supabase.table("clientes").select("id").limit(1).execute()
        supabase_ok = True
    except:
        supabase_ok = False

    # Determinar status
    checks = {
        "instancias": instancias_online > 0,
        "circuits": circuits_ok == len(circuits),
        "redis": redis_ok,
        "supabase": supabase_ok,
    }

    all_ok = all(checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "details": {
            "instancias": f"{instancias_online}/{len(instancias)} online",
            "circuits": f"{circuits_ok}/{len(circuits)} closed",
        }
    }
```

---

## DoD

- [ ] GET /dashboard/instances retorna visão geral
- [ ] GET /dashboard/instances/{nome} retorna detalhes
- [ ] GET /dashboard/health mostra status agregado
- [ ] Emojis indicam status visual
- [ ] Percentual de capacidade calculado

---

# S6.E3.2 - Alertas

## Objetivo

> **Notificar quando algo está errado com instâncias.**

---

## Alertas a Implementar

| Alerta | Trigger | Ação |
|--------|---------|------|
| Instância offline | status != connected | Slack + log |
| Instância banida | status = banned | Slack + email |
| Capacidade > 80% | carga > 80% | Slack |
| Todas offline | online = 0 | Slack urgente |
| Falhas consecutivas | erros > 5 | Log + investigar |

---

## Tarefas

### 1. Criar serviço de alertas

```python
# app/services/alertas.py

"""
Sistema de alertas para monitoramento.
"""
import logging
from enum import Enum
from datetime import datetime
from typing import Optional

from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


class Severidade(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


async def alertar(
    titulo: str,
    mensagem: str,
    severidade: Severidade = Severidade.WARNING,
    canal: Optional[str] = None
) -> None:
    """
    Envia alerta para canais configurados.
    """
    timestamp = datetime.now().isoformat()

    # Log sempre
    log_func = {
        Severidade.INFO: logger.info,
        Severidade.WARNING: logger.warning,
        Severidade.ERROR: logger.error,
        Severidade.CRITICAL: logger.critical,
    }.get(severidade, logger.warning)

    log_func(f"[ALERTA] {titulo}: {mensagem}")

    # Slack para WARNING+
    if severidade in [Severidade.WARNING, Severidade.ERROR, Severidade.CRITICAL]:
        emoji = {
            Severidade.WARNING: "⚠️",
            Severidade.ERROR: "🔴",
            Severidade.CRITICAL: "🚨",
        }.get(severidade, "ℹ️")

        await enviar_slack(
            f"{emoji} *{titulo}*\n{mensagem}\n_({timestamp})_",
            canal=canal or "#julia-alertas"
        )


async def alertar_instancia_offline(nome: str) -> None:
    """Alerta que instância ficou offline."""
    await alertar(
        titulo=f"Instância {nome} offline",
        mensagem=f"A instância WhatsApp '{nome}' perdeu conexão. Verifique o QR Code.",
        severidade=Severidade.ERROR
    )


async def alertar_instancia_banida(nome: str) -> None:
    """Alerta que instância foi banida."""
    await alertar(
        titulo=f"Instância {nome} BANIDA",
        mensagem=f"A instância '{nome}' foi banida pelo WhatsApp. Médicos estão sendo migrados.",
        severidade=Severidade.CRITICAL
    )


async def alertar_capacidade_alta(nome: str, percentual: float) -> None:
    """Alerta que instância está com capacidade alta."""
    await alertar(
        titulo=f"Capacidade alta: {nome}",
        mensagem=f"Instância '{nome}' está com {percentual:.0f}% de capacidade usada.",
        severidade=Severidade.WARNING
    )


async def alertar_sistema_critico() -> None:
    """Alerta que sistema está em estado crítico."""
    await alertar(
        titulo="SISTEMA CRÍTICO",
        mensagem="Nenhuma instância WhatsApp está online! Mensagens não serão enviadas.",
        severidade=Severidade.CRITICAL
    )
```

### 2. Integrar no health check

```python
# Adicionar em instance_manager.py

async def verificar_e_alertar(self) -> None:
    """Verifica instâncias e dispara alertas se necessário."""
    instancias = await self.listar_instancias(apenas_ativas=False)

    online = 0
    for inst in instancias:
        # Verificar status atual
        status_atual = await self.verificar_saude(inst.nome)

        if status_atual["status"] == "connected":
            online += 1

        # Status mudou para offline?
        if inst.status == "connected" and status_atual["status"] != "connected":
            await alertar_instancia_offline(inst.nome)

        # Status mudou para banido?
        if status_atual["status"] == "banned" and inst.status != "banned":
            await alertar_instancia_banida(inst.nome)
            await self.marcar_banida(inst.nome)

        # Capacidade alta?
        if inst.carga_percentual > 80:
            await alertar_capacidade_alta(inst.nome, inst.carga_percentual)

    # Nenhuma online?
    if online == 0:
        await alertar_sistema_critico()
```

### 3. Background task de monitoramento

```python
# app/main.py

async def monitoramento_loop():
    """Loop de monitoramento contínuo."""
    from app.services.instance_manager import instance_manager

    while True:
        try:
            await instance_manager.verificar_e_alertar()
        except Exception as e:
            logger.error(f"Erro no monitoramento: {e}")

        await asyncio.sleep(60)  # Verificar a cada minuto


@app.on_event("startup")
async def startup():
    # ... outras inicializações ...
    asyncio.create_task(monitoramento_loop())
```

---

## DoD

- [ ] Alerta disparado quando instância fica offline
- [ ] Alerta disparado quando instância é banida
- [ ] Alerta disparado quando capacidade > 80%
- [ ] Alerta crítico quando todas offline
- [ ] Alertas chegam no Slack
- [ ] Background task monitora a cada minuto
- [ ] Log registra todos os alertas
