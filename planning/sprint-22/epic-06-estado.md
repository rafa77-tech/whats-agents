# E06: Estado da Julia

**Epico:** Singleton de Estado em Tempo Real
**Estimativa:** 3h
**Dependencias:** E01 (Migrations)

---

## Objetivo

Criar sistema de estado em tempo real da Julia, permitindo visibilidade sobre o que ela esta fazendo a qualquer momento.

---

## Escopo

### Incluido

- [x] Servico `julia_estado.py`
- [x] Atualizacao automatica do estado
- [x] Metricas em tempo real
- [x] Historico de acoes

### Excluido

- [ ] Painel Slack (E07)
- [ ] Dashboard web

---

## Modelo de Estado

```python
@dataclass
class JuliaEstado:
    modo: str              # 'atendimento', 'comercial', 'batch', 'pausada'
    conversas_ativas: int
    replies_pendentes: int
    handoffs_abertos: int
    ultima_acao: str
    ultima_acao_at: datetime
    proxima_acao: str
    proxima_acao_at: datetime
```

---

## Tarefas

### T01: Servico julia_estado.py

**Arquivo:** `app/services/julia_estado.py`

```python
"""
Servico de estado em tempo real da Julia.

Singleton que mantem estado atualizado para visibilidade.

Sprint 22 - Responsividade Inteligente
"""
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# ID fixo do singleton
ESTADO_ID = "00000000-0000-0000-0000-000000000001"


class ModoOperacional:
    """Modos operacionais da Julia."""
    ATENDIMENTO = "atendimento"
    COMERCIAL = "comercial"
    BATCH = "batch"
    PAUSADA = "pausada"


@dataclass
class JuliaEstado:
    """Estado atual da Julia."""
    modo: str
    conversas_ativas: int
    replies_pendentes: int
    handoffs_abertos: int
    ultima_acao: Optional[str]
    ultima_acao_at: Optional[datetime]
    proxima_acao: Optional[str]
    proxima_acao_at: Optional[datetime]
    atualizado_em: datetime


async def buscar_estado() -> JuliaEstado:
    """
    Busca estado atual da Julia.

    Returns:
        JuliaEstado com dados atuais
    """
    try:
        result = supabase.table("julia_estado").select("*").eq(
            "id", ESTADO_ID
        ).single().execute()

        data = result.data

        return JuliaEstado(
            modo=data.get("modo", ModoOperacional.ATENDIMENTO),
            conversas_ativas=data.get("conversas_ativas", 0),
            replies_pendentes=data.get("replies_pendentes", 0),
            handoffs_abertos=data.get("handoffs_abertos", 0),
            ultima_acao=data.get("ultima_acao"),
            ultima_acao_at=datetime.fromisoformat(data["ultima_acao_at"]) if data.get("ultima_acao_at") else None,
            proxima_acao=data.get("proxima_acao"),
            proxima_acao_at=datetime.fromisoformat(data["proxima_acao_at"]) if data.get("proxima_acao_at") else None,
            atualizado_em=datetime.fromisoformat(data["atualizado_em"]) if data.get("atualizado_em") else datetime.now(),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar estado: {e}")
        # Retornar estado default
        return JuliaEstado(
            modo=ModoOperacional.ATENDIMENTO,
            conversas_ativas=0,
            replies_pendentes=0,
            handoffs_abertos=0,
            ultima_acao=None,
            ultima_acao_at=None,
            proxima_acao=None,
            proxima_acao_at=None,
            atualizado_em=datetime.now(),
        )


async def atualizar_modo(modo: str) -> None:
    """
    Atualiza modo operacional.

    Args:
        modo: Novo modo (atendimento, comercial, batch, pausada)
    """
    try:
        supabase.table("julia_estado").update({
            "modo": modo,
        }).eq("id", ESTADO_ID).execute()

        logger.info(f"Modo atualizado para: {modo}")

    except Exception as e:
        logger.error(f"Erro ao atualizar modo: {e}")


async def registrar_acao(acao: str) -> None:
    """
    Registra ultima acao realizada.

    Args:
        acao: Descricao da acao
    """
    try:
        supabase.table("julia_estado").update({
            "ultima_acao": acao,
            "ultima_acao_at": datetime.now().isoformat(),
        }).eq("id", ESTADO_ID).execute()

        logger.debug(f"Acao registrada: {acao}")

    except Exception as e:
        logger.error(f"Erro ao registrar acao: {e}")


async def agendar_proxima_acao(acao: str, quando: datetime) -> None:
    """
    Agenda proxima acao.

    Args:
        acao: Descricao da acao
        quando: Quando vai executar
    """
    try:
        supabase.table("julia_estado").update({
            "proxima_acao": acao,
            "proxima_acao_at": quando.isoformat(),
        }).eq("id", ESTADO_ID).execute()

        logger.debug(f"Proxima acao agendada: {acao} em {quando}")

    except Exception as e:
        logger.error(f"Erro ao agendar proxima acao: {e}")


async def atualizar_metricas() -> dict:
    """
    Atualiza metricas em tempo real.

    Busca dados atuais e atualiza o singleton.

    Returns:
        Dict com metricas atualizadas
    """
    try:
        # Buscar conversas ativas (ultima hora)
        conversas = supabase.table("conversations").select(
            "id", count="exact"
        ).eq(
            "status", "ativa"
        ).gte(
            "updated_at", (datetime.now() - timedelta(hours=1)).isoformat()
        ).execute()

        conversas_ativas = conversas.count or 0

        # Buscar replies pendentes
        fila = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq(
            "status", "pendente"
        ).execute()

        replies_pendentes = fila.count or 0

        # Buscar handoffs abertos
        handoffs = supabase.table("external_handoffs").select(
            "id", count="exact"
        ).eq(
            "status", "pending"
        ).execute()

        handoffs_abertos = handoffs.count or 0

        # Atualizar singleton
        supabase.table("julia_estado").update({
            "conversas_ativas": conversas_ativas,
            "replies_pendentes": replies_pendentes,
            "handoffs_abertos": handoffs_abertos,
        }).eq("id", ESTADO_ID).execute()

        metricas = {
            "conversas_ativas": conversas_ativas,
            "replies_pendentes": replies_pendentes,
            "handoffs_abertos": handoffs_abertos,
        }

        logger.debug(f"Metricas atualizadas: {metricas}")
        return metricas

    except Exception as e:
        logger.error(f"Erro ao atualizar metricas: {e}")
        return {}


async def formatar_status_texto() -> str:
    """
    Formata estado para exibicao em texto.

    Returns:
        Texto formatado do estado
    """
    estado = await buscar_estado()
    await atualizar_metricas()
    estado = await buscar_estado()  # Rebuscar com metricas

    modo_emoji = {
        ModoOperacional.ATENDIMENTO: "🟢",
        ModoOperacional.COMERCIAL: "🟡",
        ModoOperacional.BATCH: "🔵",
        ModoOperacional.PAUSADA: "🔴",
    }

    emoji = modo_emoji.get(estado.modo, "⚪")

    texto = f"""📊 Julia Status

Estado: {emoji} {estado.modo.title()}
Conversas ativas: {estado.conversas_ativas}
Replies pendentes: {estado.replies_pendentes}
Handoffs abertos: {estado.handoffs_abertos}
"""

    if estado.ultima_acao:
        hora = estado.ultima_acao_at.strftime("%H:%M") if estado.ultima_acao_at else "N/A"
        texto += f"\nUltima acao: {estado.ultima_acao} ({hora})"

    if estado.proxima_acao:
        hora = estado.proxima_acao_at.strftime("%H:%M") if estado.proxima_acao_at else "N/A"
        texto += f"\nProxima acao: {estado.proxima_acao} ({hora})"

    return texto


# ============================================================================
# Integracao com Pipeline
# ============================================================================

async def ao_iniciar_resposta(cliente_id: str, tipo: str) -> None:
    """Hook chamado ao iniciar resposta."""
    await registrar_acao(f"Respondendo {tipo} para {cliente_id[:8]}")


async def ao_finalizar_resposta(cliente_id: str, sucesso: bool) -> None:
    """Hook chamado ao finalizar resposta."""
    status = "sucesso" if sucesso else "erro"
    await registrar_acao(f"Resposta {status} para {cliente_id[:8]}")


async def ao_iniciar_campanha(campanha_nome: str, total: int) -> None:
    """Hook chamado ao iniciar campanha."""
    await atualizar_modo(ModoOperacional.COMERCIAL)
    await registrar_acao(f"Campanha {campanha_nome} ({total} envios)")


async def ao_finalizar_campanha(campanha_nome: str) -> None:
    """Hook chamado ao finalizar campanha."""
    await atualizar_modo(ModoOperacional.ATENDIMENTO)
    await registrar_acao(f"Campanha {campanha_nome} finalizada")
```

**DoD:**
- [ ] Servico criado
- [ ] CRUD de estado funcionando
- [ ] Metricas atualizando
- [ ] Hooks de integracao

---

### T02: Integracao com Agente

**Arquivo:** Modificar `app/services/agente.py`

```python
from app.services.julia_estado import (
    ao_iniciar_resposta,
    ao_finalizar_resposta,
)

# No processamento:
async def processar_mensagem(self, ...):
    await ao_iniciar_resposta(cliente_id, "reply")

    try:
        resposta = await self._gerar_resposta(...)
        await ao_finalizar_resposta(cliente_id, True)
        return resposta
    except Exception as e:
        await ao_finalizar_resposta(cliente_id, False)
        raise
```

**DoD:**
- [ ] Hooks chamados no agente
- [ ] Estado reflete acoes em tempo real

---

### T03: Job de Atualizacao

**Arquivo:** Adicionar em `app/api/routes/jobs.py`

```python
@router.post("/atualizar-estado-julia")
async def job_atualizar_estado():
    """Atualiza metricas do estado da Julia."""
    from app.services.julia_estado import atualizar_metricas

    metricas = await atualizar_metricas()
    return JSONResponse({"status": "ok", **metricas})
```

Adicionar no scheduler (a cada 5 min):

```python
{
    "name": "atualizar_estado_julia",
    "endpoint": "/jobs/atualizar-estado-julia",
    "schedule": "*/5 * * * *",
    "categoria": "estado",
}
```

**DoD:**
- [ ] Job criado
- [ ] Metricas atualizadas a cada 5 min

---

## Validacao

### Queries

```sql
-- Estado atual
SELECT * FROM julia_estado;

-- Historico de atualizacoes (se tiver log)
SELECT
    ultima_acao,
    ultima_acao_at,
    atualizado_em
FROM julia_estado;
```

### Teste Manual

```python
# Testar servico
from app.services.julia_estado import (
    buscar_estado,
    atualizar_metricas,
    formatar_status_texto,
)

import asyncio

async def test():
    estado = await buscar_estado()
    print(f"Modo: {estado.modo}")

    await atualizar_metricas()

    texto = await formatar_status_texto()
    print(texto)

asyncio.run(test())
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Servico `julia_estado.py` implementado
- [ ] Singleton funcionando
- [ ] Metricas atualizando
- [ ] Hooks de integracao

### Qualidade

- [ ] Estado reflete realidade
- [ ] Atualizacao < 100ms
- [ ] Logs estruturados

### Observabilidade

- [ ] Estado consultavel via API
- [ ] Metricas para dashboards

---

*Epico criado em 29/12/2025*
