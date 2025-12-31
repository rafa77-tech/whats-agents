# Epic 08: Early Warning System

## Objetivo

Detectar problemas precocemente e tomar acoes automaticas (pausar, reduzir velocidade) para proteger os chips de banimento.

## Contexto

O Early Warning System e a linha de defesa contra ban:
- **Critico**: Pausa imediata do chip
- **Warning**: Reduz velocidade e alerta
- **Info**: Apenas registro para analise

### Sinais de Perigo

1. **Erro de Spam (131048)**: Pausa imediata
2. **Health Drop Rapido**: Queda de 20+ pontos em 1h
3. **Taxa de Erro Alta**: 50%+ de erros em 1h
4. **Taxa de Resposta Baixa**: <20% em 24h
5. **Msgs Sem Resposta**: 5+ consecutivas
6. **Inatividade Prolongada**: 3+ dias sem atividade

---

## Story 8.1: Thresholds de Alerta

### Objetivo
Definir thresholds para deteccao de problemas.

### Implementacao

**Arquivo:** `app/services/warmer/early_warning.py`

```python
"""
Early Warning System - Detecta problemas e pausa chips.

Thresholds:
- Critico: pausa imediata
- Warning: reduz velocidade e alerta
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional, List

from app.services.supabase import supabase
from app.services.slack import enviar_slack
from app.services.redis import redis_client

logger = logging.getLogger(__name__)


# Thresholds de alerta
THRESHOLDS = {
    "critico": {
        "taxa_erro_1h": 0.5,       # 50% de erros em 1h = critico
        "health_drop_1h": 20,      # Health caiu 20+ pontos em 1h
        "spam_error": 1,           # Qualquer erro 131048
        "conexao_perdida": 1,      # Instancia desconectada
    },
    "warning": {
        "taxa_resposta_24h": 0.2,  # Taxa resposta < 20% em 24h
        "health_drop_24h": 10,     # Health caiu 10+ pontos em 24h
        "msgs_sem_resposta": 5,    # 5 msgs consecutivas sem resposta
        "inatividade_dias": 3,     # 3+ dias sem atividade
    },
}


# Codigos de erro criticos do WhatsApp
ERROS_CRITICOS = [
    131048,  # Spam detected
    131047,  # Rate limit exceeded
    131051,  # Unsupported message type
    131000,  # Something went wrong
]
```

### DoD

- [ ] Thresholds criticos definidos
- [ ] Thresholds de warning definidos
- [ ] Erros criticos listados

---

## Story 8.2: Monitoramento de Chip

### Objetivo
Implementar funcao principal de monitoramento.

### Implementacao

```python
async def monitorar_chip(chip_id: str) -> Tuple[str, str]:
    """
    Monitora saude do chip em tempo real.

    Executa todos os checks e toma acao se necessario.

    Args:
        chip_id: UUID do chip

    Returns:
        Tupla (status, motivo) - status: 'ok', 'warning', 'critico'
    """
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return "ok", ""

    c = chip.data
    now = datetime.now(timezone.utc)

    # ══════════════════════════════════════════
    # CHECKS CRITICOS (prioridade maxima)
    # ══════════════════════════════════════════

    # Check 1: Erro de spam
    status, motivo = await check_erro_spam(chip_id, now)
    if status == "critico":
        return status, motivo

    # Check 2: Health drop 1h
    status, motivo = await check_health_drop_1h(chip_id, c["health_score"], now)
    if status == "critico":
        return status, motivo

    # Check 3: Taxa de erro 1h
    status, motivo = await check_taxa_erro_1h(chip_id, now)
    if status == "critico":
        return status, motivo

    # Check 4: Conexao perdida
    status, motivo = await check_conexao(c)
    if status == "critico":
        return status, motivo

    # ══════════════════════════════════════════
    # CHECKS WARNING (prioridade media)
    # ══════════════════════════════════════════

    # Check 5: Taxa de resposta 24h
    taxa_resposta = float(c.get("taxa_resposta", 0))
    if taxa_resposta < THRESHOLDS["warning"]["taxa_resposta_24h"]:
        await criar_alerta(
            chip_id, "warning", "low_response",
            f"Taxa resposta baixa: {taxa_resposta:.0%}"
        )
        await reduzir_velocidade(chip_id, 0.5)
        return "warning", "low_response"

    # Check 6: Health drop 24h
    status, motivo = await check_health_drop_24h(chip_id, c["health_score"], now)
    if status == "warning":
        return status, motivo

    # Check 7: Msgs sem resposta consecutivas
    status, motivo = await check_msgs_sem_resposta(chip_id)
    if status == "warning":
        return status, motivo

    # Check 8: Inatividade
    status, motivo = await check_inatividade(c, now)
    if status == "warning":
        return status, motivo

    return "ok", ""
```

### DoD

- [ ] Funcao `monitorar_chip` implementada
- [ ] Checks criticos priorizados
- [ ] Checks warning implementados
- [ ] Retorno claro de status

---

## Story 8.3: Checks Criticos

### Objetivo
Implementar verificacoes criticas que pausam chip.

### Implementacao

```python
async def check_erro_spam(chip_id: str, now: datetime) -> Tuple[str, str]:
    """
    Verifica erros de spam na ultima hora.
    """
    erros = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "spam_error") \
        .gte("created_at", (now - timedelta(hours=1)).isoformat()) \
        .execute()

    if (erros.count or 0) >= THRESHOLDS["critico"]["spam_error"]:
        await pausar_chip(chip_id, "CRITICO: Erro de spam detectado")
        return "critico", "spam_error"

    return "ok", ""


async def check_health_drop_1h(
    chip_id: str,
    health_atual: int,
    now: datetime
) -> Tuple[str, str]:
    """
    Verifica queda de health na ultima hora.
    """
    health_1h = await obter_health_em(chip_id, now - timedelta(hours=1))

    if health_1h and (health_1h - health_atual) > THRESHOLDS["critico"]["health_drop_1h"]:
        diferenca = health_1h - health_atual
        await pausar_chip(chip_id, f"CRITICO: Health caiu {diferenca} pontos em 1h")
        return "critico", "health_drop_1h"

    return "ok", ""


async def check_taxa_erro_1h(chip_id: str, now: datetime) -> Tuple[str, str]:
    """
    Verifica taxa de erro na ultima hora.
    """
    # Contar mensagens enviadas
    msgs = supabase.table("warmup_interactions") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "msg_enviada") \
        .gte("created_at", (now - timedelta(hours=1)).isoformat()) \
        .execute()

    total = msgs.count or 0
    if total < 5:
        return "ok", ""  # Amostra muito pequena

    # Contar erros
    erros = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("chip_id", chip_id) \
        .gte("created_at", (now - timedelta(hours=1)).isoformat()) \
        .execute()

    erros_count = erros.count or 0
    taxa = erros_count / total

    if taxa > THRESHOLDS["critico"]["taxa_erro_1h"]:
        await pausar_chip(chip_id, f"CRITICO: {taxa:.0%} de erros em 1h")
        return "critico", "taxa_erro"

    return "ok", ""


async def check_conexao(chip: dict) -> Tuple[str, str]:
    """
    Verifica se instancia esta conectada.
    """
    # Verificar via Redis ou Evolution API
    key = f"warmer:conexao:{chip['instance_name']}"
    status = await redis_client.get(key)

    if status and status.decode() == "disconnected":
        await pausar_chip(chip["id"], "CRITICO: Instancia desconectada")
        return "critico", "conexao_perdida"

    return "ok", ""
```

### DoD

- [ ] `check_erro_spam` implementado
- [ ] `check_health_drop_1h` implementado
- [ ] `check_taxa_erro_1h` implementado
- [ ] `check_conexao` implementado

---

## Story 8.4: Checks Warning

### Objetivo
Implementar verificacoes de warning que reduzem velocidade.

### Implementacao

```python
async def check_health_drop_24h(
    chip_id: str,
    health_atual: int,
    now: datetime
) -> Tuple[str, str]:
    """
    Verifica queda de health nas ultimas 24h.
    """
    health_24h = await obter_health_em(chip_id, now - timedelta(hours=24))

    if health_24h and (health_24h - health_atual) > THRESHOLDS["warning"]["health_drop_24h"]:
        diferenca = health_24h - health_atual
        await criar_alerta(
            chip_id, "warning", "health_drop",
            f"Health caiu {diferenca} pontos em 24h"
        )
        await reduzir_velocidade(chip_id, 0.7)
        return "warning", "health_drop_24h"

    return "ok", ""


async def check_msgs_sem_resposta(chip_id: str) -> Tuple[str, str]:
    """
    Verifica mensagens consecutivas sem resposta.
    """
    # Buscar ultimas N mensagens enviadas
    msgs = supabase.table("warmup_interactions") \
        .select("obteve_resposta") \
        .eq("chip_id", chip_id) \
        .eq("tipo", "msg_enviada") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()

    if not msgs.data:
        return "ok", ""

    # Contar consecutivas sem resposta
    sem_resposta = 0
    for msg in msgs.data:
        if msg.get("obteve_resposta") is False:
            sem_resposta += 1
        else:
            break  # Interrompe na primeira com resposta

    if sem_resposta >= THRESHOLDS["warning"]["msgs_sem_resposta"]:
        await criar_alerta(
            chip_id, "warning", "no_response",
            f"{sem_resposta} msgs consecutivas sem resposta"
        )
        await reduzir_velocidade(chip_id, 0.5)
        return "warning", "msgs_sem_resposta"

    return "ok", ""


async def check_inatividade(chip: dict, now: datetime) -> Tuple[str, str]:
    """
    Verifica inatividade prolongada.
    """
    last_activity = chip.get("last_activity_at")

    if not last_activity:
        return "ok", ""

    last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
    dias_inativo = (now - last_dt).days

    if dias_inativo >= THRESHOLDS["warning"]["inatividade_dias"]:
        await criar_alerta(
            chip["id"], "warning", "inactivity",
            f"Chip inativo ha {dias_inativo} dias"
        )
        return "warning", "inatividade"

    return "ok", ""
```

### DoD

- [ ] `check_health_drop_24h` implementado
- [ ] `check_msgs_sem_resposta` implementado
- [ ] `check_inatividade` implementado
- [ ] Reducao de velocidade aplicada

---

## Story 8.5: Acoes de Resposta

### Objetivo
Implementar acoes automaticas em resposta a problemas.

### Implementacao

```python
async def pausar_chip(chip_id: str, motivo: str):
    """
    Pausa chip imediatamente.

    Args:
        chip_id: UUID do chip
        motivo: Motivo da pausa
    """
    # Atualizar status
    supabase.table("warmup_chips") \
        .update({"status": "paused"}) \
        .eq("id", chip_id) \
        .execute()

    # Criar alerta critico
    await criar_alerta(chip_id, "critical", "paused", motivo)

    # Buscar dados para notificacao
    chip = supabase.table("warmup_chips") \
        .select("telefone, health_score, fase_warmup") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    # Notificar no Slack
    if chip.data:
        await enviar_slack({
            "text": f":octagonal_sign: *CHIP PAUSADO*",
            "attachments": [{
                "color": "#EF4444",  # Vermelho
                "fields": [
                    {"title": "Telefone", "value": chip.data["telefone"][-4:], "short": True},
                    {"title": "Health", "value": str(chip.data["health_score"]), "short": True},
                    {"title": "Fase", "value": chip.data["fase_warmup"], "short": True},
                    {"title": "Motivo", "value": motivo, "short": False},
                ],
            }]
        })

    logger.warning(f"[EarlyWarning] Chip {chip_id} pausado: {motivo}")


async def reduzir_velocidade(chip_id: str, fator: float):
    """
    Reduz velocidade de envio do chip.

    Args:
        chip_id: UUID do chip
        fator: Fator de 0.0 a 1.0 (0.5 = 50% das msgs)
    """
    key = f"warmer:velocidade:{chip_id}"
    await redis_client.set(key, str(fator))
    await redis_client.expire(key, 86400)  # 24h

    logger.info(f"[EarlyWarning] Velocidade reduzida: {chip_id[:8]} = {fator}")


async def restaurar_velocidade(chip_id: str):
    """
    Restaura velocidade normal do chip.

    Args:
        chip_id: UUID do chip
    """
    key = f"warmer:velocidade:{chip_id}"
    await redis_client.delete(key)

    logger.info(f"[EarlyWarning] Velocidade restaurada: {chip_id[:8]}")


async def criar_alerta(chip_id: str, severity: str, tipo: str, message: str):
    """
    Cria registro de alerta no banco.

    Args:
        chip_id: UUID do chip
        severity: 'critical', 'warning', 'info'
        tipo: Tipo do alerta
        message: Mensagem descritiva
    """
    supabase.table("warmup_alerts") \
        .insert({
            "chip_id": chip_id,
            "severity": severity,
            "tipo": tipo,
            "message": message,
        }) \
        .execute()

    logger.info(f"[EarlyWarning] Alerta criado: {chip_id[:8]} - {severity} - {tipo}")
```

### DoD

- [ ] `pausar_chip` implementada
- [ ] `reduzir_velocidade` implementada
- [ ] `restaurar_velocidade` implementada
- [ ] `criar_alerta` implementada
- [ ] Notificacao Slack funcionando

---

## Story 8.6: Funcoes Auxiliares

### Objetivo
Implementar funcoes auxiliares para o sistema.

### Implementacao

```python
async def obter_health_em(chip_id: str, momento: datetime) -> Optional[int]:
    """
    Obtem health score mais proximo de um momento.

    Args:
        chip_id: UUID do chip
        momento: Datetime de referencia

    Returns:
        Health score ou None
    """
    # Buscar registro mais proximo (ate 1h de diferenca)
    resultado = supabase.table("warmup_health_log") \
        .select("score") \
        .eq("chip_id", chip_id) \
        .gte("recorded_at", (momento - timedelta(hours=1)).isoformat()) \
        .lte("recorded_at", (momento + timedelta(hours=1)).isoformat()) \
        .order("recorded_at", desc=True) \
        .limit(1) \
        .execute()

    if resultado.data:
        return resultado.data[0]["score"]
    return None


async def listar_alertas_ativos(chip_id: Optional[str] = None) -> List[dict]:
    """
    Lista alertas nao resolvidos.

    Args:
        chip_id: UUID do chip (opcional, se None lista todos)

    Returns:
        Lista de alertas
    """
    query = supabase.table("warmup_alerts") \
        .select("*, warmup_chips(telefone)") \
        .eq("resolved", False) \
        .order("created_at", desc=True)

    if chip_id:
        query = query.eq("chip_id", chip_id)

    resultado = query.execute()
    return resultado.data or []


async def resolver_alerta(alerta_id: str, resolved_by: str = "sistema"):
    """
    Marca alerta como resolvido.

    Args:
        alerta_id: UUID do alerta
        resolved_by: Quem resolveu
    """
    supabase.table("warmup_alerts") \
        .update({
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": resolved_by,
        }) \
        .eq("id", alerta_id) \
        .execute()

    logger.info(f"[EarlyWarning] Alerta resolvido: {alerta_id}")


async def retomar_chip(chip_id: str, retomado_por: str = "sistema"):
    """
    Retoma chip pausado.

    Args:
        chip_id: UUID do chip
        retomado_por: Quem retomou
    """
    # Verificar se chip existe e esta pausado
    chip = supabase.table("warmup_chips") \
        .select("status, telefone") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data or chip.data["status"] != "paused":
        logger.warning(f"[EarlyWarning] Chip {chip_id[:8]} nao esta pausado")
        return

    # Retomar
    supabase.table("warmup_chips") \
        .update({"status": "warming"}) \
        .eq("id", chip_id) \
        .execute()

    # Restaurar velocidade
    await restaurar_velocidade(chip_id)

    # Criar registro
    await criar_alerta(chip_id, "info", "resumed", f"Retomado por {retomado_por}")

    # Notificar
    await enviar_slack({
        "text": f":arrow_forward: Chip retomado: {chip.data['telefone'][-4:]}",
    })

    logger.info(f"[EarlyWarning] Chip {chip_id[:8]} retomado por {retomado_por}")
```

### DoD

- [ ] `obter_health_em` implementada
- [ ] `listar_alertas_ativos` implementada
- [ ] `resolver_alerta` implementada
- [ ] `retomar_chip` implementada

---

## Checklist do Epico

- [ ] **S25.E08.1** - Thresholds definidos
- [ ] **S25.E08.2** - Monitoramento de chip
- [ ] **S25.E08.3** - Checks criticos
- [ ] **S25.E08.4** - Checks warning
- [ ] **S25.E08.5** - Acoes de resposta
- [ ] **S25.E08.6** - Funcoes auxiliares
- [ ] Pausa automatica funcionando
- [ ] Reducao de velocidade funcionando
- [ ] Alertas sendo criados
- [ ] Notificacoes Slack chegando

---

## Validacao

```python
import pytest
from app.services.warmer.early_warning import (
    THRESHOLDS,
    monitorar_chip,
)


def test_thresholds_criticos():
    """Testa que thresholds criticos estao definidos."""
    assert THRESHOLDS["critico"]["spam_error"] == 1
    assert THRESHOLDS["critico"]["health_drop_1h"] == 20
    assert THRESHOLDS["critico"]["taxa_erro_1h"] == 0.5


def test_thresholds_warning():
    """Testa que thresholds warning estao definidos."""
    assert THRESHOLDS["warning"]["taxa_resposta_24h"] == 0.2
    assert THRESHOLDS["warning"]["msgs_sem_resposta"] == 5
    assert THRESHOLDS["warning"]["inatividade_dias"] == 3


@pytest.mark.asyncio
async def test_monitorar_chip_ok():
    """Testa monitoramento de chip saudavel."""
    # Mock de chip saudavel
    # status, motivo = await monitorar_chip(chip_id)
    # assert status == "ok"
    pass
```

---

## Diagrama: Fluxo de Early Warning

```
┌─────────────────────────────────────────────────────────┐
│                   monitorar_chip()                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │       CHECKS CRITICOS          │
         │         (prioridade 1)         │
         ├────────────────────────────────┤
         │ ❌ Erro de spam?               │──► PAUSA IMEDIATA
         │ ❌ Health drop 20pts/1h?       │──► PAUSA IMEDIATA
         │ ❌ Taxa erro >50%/1h?          │──► PAUSA IMEDIATA
         │ ❌ Conexao perdida?            │──► PAUSA IMEDIATA
         └────────────────────────────────┘
                          │
                          ▼ (se passou)
         ┌────────────────────────────────┐
         │       CHECKS WARNING           │
         │         (prioridade 2)         │
         ├────────────────────────────────┤
         │ ⚠️ Taxa resposta <20%/24h?    │──► Reduz 50%
         │ ⚠️ Health drop 10pts/24h?     │──► Reduz 30%
         │ ⚠️ 5 msgs sem resposta?       │──► Reduz 50%
         │ ⚠️ Inativo 3+ dias?           │──► Alerta
         └────────────────────────────────┘
                          │
                          ▼ (se passou)
                    ┌─────────┐
                    │   OK    │
                    └─────────┘


          ACOES AUTOMATICAS
          ═════════════════

          CRITICO → pausar_chip()
                    ├── status = "paused"
                    ├── Alerta critico
                    └── Slack: 🛑 CHIP PAUSADO

          WARNING → reduzir_velocidade()
                    ├── Redis: fator velocidade
                    └── Alerta warning
```

---

## Tabela de Thresholds

| Check | Threshold | Acao | Severidade |
|-------|-----------|------|------------|
| Erro spam | 1 ocorrencia | Pausa | Critico |
| Health drop 1h | -20 pts | Pausa | Critico |
| Taxa erro 1h | >50% | Pausa | Critico |
| Conexao | Desconectada | Pausa | Critico |
| Taxa resposta 24h | <20% | Reduz 50% | Warning |
| Health drop 24h | -10 pts | Reduz 30% | Warning |
| Msgs sem resposta | 5 consecutivas | Reduz 50% | Warning |
| Inatividade | 3+ dias | Alerta | Warning |

