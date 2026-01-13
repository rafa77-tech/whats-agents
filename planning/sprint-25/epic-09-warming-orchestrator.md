# Epic 09: Warming Orchestrator

**Status:** ✅ Completo

**Arquivos criados:**
- `app/services/warmer/orchestrator.py`

---

## Objetivo

Coordenar todo o fluxo de warm-up, gerenciando fases, disparando conversas e monitorando saude dos chips de forma autonoma.

## Contexto

O Orchestrator e o "cerebro" do Julia Warmer:
- Executa ciclos a cada 5 minutos
- Avalia progressao de fases automaticamente
- Dispara conversas entre pares
- Monitora health e responde a alertas
- Notifica eventos importantes via Slack

### Responsabilidades

1. **Ciclo de Warm-up**: Executar acoes para cada chip ativo
2. **Progressao de Fases**: Avaliar criterios e promover chips
3. **Conversas**: Orquestrar dialogos entre pares
4. **Monitoramento**: Verificar saude e gerar alertas
5. **Notificacoes**: Comunicar eventos ao time

---

## Story 7.1: Ciclo Principal

### Objetivo
Implementar ciclo principal que executa a cada 5 minutos.

### Implementacao

**Arquivo:** `app/services/warmer/orchestrator.py`

```python
"""
Orchestrator - Coordena o fluxo de warm-up.

Responsabilidades:
- Avaliar progressao de fases
- Disparar conversas entre pares
- Monitorar saude dos chips
- Responder a alertas
"""
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional

from app.services.warmer.health_score import calcular_health_score, registrar_health_score
from app.services.warmer.pairing_engine import obter_pareamentos_dia, registrar_interacao, obter_par_id
from app.services.warmer.conversation_generator import gerar_dialogo
from app.services.warmer.human_simulator import enviar_mensagem_humanizada, calcular_delay_entre_turnos
from app.services.warmer.scheduler import pode_enviar_mensagem, registrar_envio
from app.services.warmer.early_warning import monitorar_chip
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


async def executar_ciclo_warmup():
    """
    Executa um ciclo de warm-up para todos os chips ativos.
    Deve ser chamado a cada 5 minutos via scheduler.

    Fluxo:
    1. Buscar todos os chips em warming
    2. Para cada chip, processar de forma async
    3. Atualizar health scores
    4. Gerar alertas se necessario
    """
    logger.info("[Orchestrator] Iniciando ciclo de warm-up")
    inicio = datetime.now(timezone.utc)

    # Buscar chips em warm-up
    chips = supabase.table("warmup_chips") \
        .select("*") \
        .eq("status", "warming") \
        .execute()

    if not chips.data:
        logger.info("[Orchestrator] Nenhum chip em warming")
        return

    logger.info(f"[Orchestrator] Processando {len(chips.data)} chips")

    # Processar chips em paralelo (com limite de concorrencia)
    semaforo = asyncio.Semaphore(5)  # Max 5 chips simultaneos

    async def processar_com_semaforo(chip):
        async with semaforo:
            await processar_chip(chip)

    tarefas = [processar_com_semaforo(chip) for chip in chips.data]
    await asyncio.gather(*tarefas, return_exceptions=True)

    duracao = (datetime.now(timezone.utc) - inicio).total_seconds()
    logger.info(f"[Orchestrator] Ciclo finalizado em {duracao:.1f}s")


async def processar_chip(chip: dict):
    """
    Processa um chip individual no ciclo.

    Args:
        chip: Dados do chip
    """
    chip_id = chip["id"]

    try:
        # 1. Verificar se pode enviar
        pode, motivo = await pode_enviar_mensagem(chip_id)
        if not pode:
            logger.debug(f"[Orchestrator] Chip {chip_id[:8]} nao pode enviar: {motivo}")
            return

        # 2. Avaliar progressao de fase
        await avaliar_progressao_fase(chip_id)

        # 3. Verificar saude (early warning)
        status_saude, _ = await monitorar_chip(chip_id)
        if status_saude == "critico":
            logger.warning(f"[Orchestrator] Chip {chip_id[:8]} em estado critico")
            return

        # 4. Se nao esta em setup, executar conversa
        if chip["fase_warmup"] != "setup":
            await executar_conversa_warmup(chip_id)

        # 5. Atualizar health score
        await registrar_health_score(chip_id)

    except Exception as e:
        logger.error(f"[Orchestrator] Erro processando chip {chip_id[:8]}: {e}")
```

### DoD

- [x] Funcao `executar_ciclo_warmup` implementada
- [x] Funcao `processar_chip` implementada
- [x] Concorrencia limitada (semaforo)
- [x] Logging adequado

---

## Story 7.2: Criterios de Progressao

### Objetivo
Definir e implementar criterios para progressao entre fases.

### Implementacao

```python
# Criterios de progressao por fase
CRITERIOS_FASE = {
    "setup": {
        "dias_min": 3,
        "health_min": 45,
        "proxima": "primeiros_contatos",
        "descricao": "Configuracao inicial, sem envio de msgs",
    },
    "primeiros_contatos": {
        "dias_min": 4,
        "health_min": 55,
        "taxa_resposta_min": 0.5,
        "proxima": "expansao",
        "descricao": "Primeiras conversas, max 10 msgs/dia",
    },
    "expansao": {
        "dias_min": 7,
        "health_min": 70,
        "taxa_resposta_min": 0.4,
        "proxima": "pre_operacao",
        "descricao": "Aumento gradual, max 30 msgs/dia",
    },
    "pre_operacao": {
        "dias_min": 7,
        "health_min": 85,
        "taxa_resposta_min": 0.35,
        "proxima": "operacao",
        "descricao": "Quase pronto, max 50 msgs/dia",
    },
    "operacao": {
        "proxima": None,
        "descricao": "Chip pronto para producao",
    },
}


def verificar_criterios_fase(
    fase: str,
    dias_fase: int,
    health: int,
    taxa_resposta: float
) -> tuple[bool, list[str]]:
    """
    Verifica se criterios de progressao foram atingidos.

    Args:
        fase: Fase atual
        dias_fase: Dias na fase atual
        health: Health score atual
        taxa_resposta: Taxa de resposta atual

    Returns:
        Tupla (criterios_ok, lista_de_pendencias)
    """
    criterio = CRITERIOS_FASE.get(fase)
    if not criterio or not criterio.get("proxima"):
        return False, ["fase_final"]

    pendencias = []

    # Verificar dias minimos
    dias_min = criterio.get("dias_min", 0)
    if dias_fase < dias_min:
        pendencias.append(f"dias: {dias_fase}/{dias_min}")

    # Verificar health minimo
    health_min = criterio.get("health_min", 0)
    if health < health_min:
        pendencias.append(f"health: {health}/{health_min}")

    # Verificar taxa de resposta
    taxa_min = criterio.get("taxa_resposta_min", 0)
    if taxa_resposta < taxa_min:
        pendencias.append(f"taxa_resposta: {taxa_resposta:.0%}/{taxa_min:.0%}")

    return len(pendencias) == 0, pendencias
```

### DoD

- [x] Constantes `CRITERIOS_FASE` definidas
- [x] Funcao `verificar_criterios_fase`
- [x] Todos os criterios considerados
- [x] Lista de pendencias retornada

---

## Story 7.3: Avaliacao de Progressao

### Objetivo
Avaliar e aplicar progressao de fase automaticamente.

### Implementacao

```python
async def avaliar_progressao_fase(chip_id: str) -> Optional[str]:
    """
    Avalia se o chip pode avancar para proxima fase.

    Args:
        chip_id: UUID do chip

    Returns:
        Nova fase se houve progressao, None caso contrario
    """
    # Buscar dados do chip
    chip = supabase.table("warmup_chips") \
        .select("*") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return None

    c = chip.data
    fase_atual = c["fase_warmup"]

    criterio = CRITERIOS_FASE.get(fase_atual)
    if not criterio or not criterio.get("proxima"):
        return None  # Ja em operacao

    # Calcular metricas
    fase_iniciada = datetime.fromisoformat(c["fase_iniciada_em"].replace("Z", "+00:00"))
    dias_fase = (datetime.now(timezone.utc) - fase_iniciada).days
    health = c["health_score"]
    taxa_resposta = float(c.get("taxa_resposta", 0))

    # Verificar criterios
    criterios_ok, pendencias = verificar_criterios_fase(
        fase_atual, dias_fase, health, taxa_resposta
    )

    if not criterios_ok:
        logger.debug(
            f"[Orchestrator] Chip {chip_id[:8]} pendencias: {', '.join(pendencias)}"
        )
        return None

    # PROGRESSAO!
    nova_fase = criterio["proxima"]

    # Atualizar fase
    supabase.table("warmup_chips") \
        .update({
            "fase_warmup": nova_fase,
            "fase_iniciada_em": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", chip_id) \
        .execute()

    # Notificar
    await notificar_progressao(c, fase_atual, nova_fase, health, taxa_resposta)

    # Se chegou em operacao, marcar como ready
    if nova_fase == "operacao":
        await marcar_chip_ready(chip_id)

    logger.info(f"[Orchestrator] Chip {chip_id[:8]} avancou: {fase_atual} -> {nova_fase}")

    return nova_fase


async def marcar_chip_ready(chip_id: str):
    """
    Marca chip como pronto para producao.

    Args:
        chip_id: UUID do chip
    """
    supabase.table("warmup_chips") \
        .update({
            "status": "ready",
            "ready_at": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", chip_id) \
        .execute()

    # Buscar dados para notificacao
    chip = supabase.table("warmup_chips") \
        .select("telefone, health_score") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if chip.data:
        await enviar_slack({
            "text": f":white_check_mark: CHIP PRONTO PARA PRODUCAO!",
            "attachments": [{
                "color": "#22C55E",
                "fields": [
                    {"title": "Telefone", "value": chip.data["telefone"][-4:], "short": True},
                    {"title": "Health", "value": str(chip.data["health_score"]), "short": True},
                ],
            }]
        })
```

### DoD

- [x] Funcao `avaliar_progressao_fase`
- [x] Funcao `marcar_chip_ready`
- [x] Progressao automatica funcionando
- [x] Notificacao ao atingir "ready"

---

## Story 7.4: Execucao de Conversas

### Objetivo
Orquestrar conversa completa entre dois chips pareados.

### Implementacao

```python
async def executar_conversa_warmup(chip_id: str) -> bool:
    """
    Executa uma conversa de warm-up com um par.

    Args:
        chip_id: UUID do chip

    Returns:
        True se conversa foi executada
    """
    # Obter parceiros disponiveis
    parceiros = await obter_pareamentos_dia(chip_id)
    if not parceiros:
        logger.debug(f"[Orchestrator] Chip {chip_id[:8]} sem parceiros disponiveis")
        return False

    # Escolher parceiro aleatorio
    parceiro_id = random.choice(parceiros)

    # Buscar dados dos chips
    chip = await buscar_chip_com_instance(chip_id)
    parceiro = await buscar_chip_com_instance(parceiro_id)

    if not chip or not parceiro:
        logger.warning(f"[Orchestrator] Chips nao encontrados: {chip_id[:8]} ou {parceiro_id[:8]}")
        return False

    # Gerar dialogo
    mensagens = await gerar_dialogo()

    logger.info(
        f"[Orchestrator] Iniciando conversa: {chip['telefone'][-4:]} <-> {parceiro['telefone'][-4:]} "
        f"({len(mensagens)} msgs)"
    )

    # Registrar conversa no banco
    par_id = await obter_par_id(chip_id, parceiro_id)
    conversa_id = await criar_registro_conversa(par_id, mensagens)

    # Executar conversa
    try:
        for i, msg in enumerate(mensagens):
            # Determinar quem envia
            if msg["from"] == "A":
                remetente = chip
                destinatario = parceiro
            else:
                remetente = parceiro
                destinatario = chip

            # Enviar com simulacao humana
            sucesso = await enviar_mensagem_humanizada(
                instance=remetente["instance_name"],
                destinatario=destinatario["telefone"],
                texto=msg["text"],
                simular_leitura=(i > 0),  # Simula leitura a partir da 2a msg
            )

            if not sucesso:
                logger.warning(f"[Orchestrator] Falha ao enviar msg {i+1}")
                break

            # Registrar envio
            await registrar_envio(remetente["id"])

            # Registrar interacao
            await registrar_interacao_detalhada(
                remetente["id"],
                destinatario["telefone"],
                msg["text"],
            )

            # Delay entre turnos (exceto no ultimo)
            if i < len(mensagens) - 1:
                delay = calcular_delay_entre_turnos()
                logger.debug(f"[Orchestrator] Aguardando {delay:.0f}s ate proximo turno")
                await asyncio.sleep(delay)

        # Finalizar conversa
        await finalizar_registro_conversa(conversa_id)

        # Registrar interacao no par
        await registrar_interacao(chip_id, parceiro_id)

        logger.info(f"[Orchestrator] Conversa finalizada: {chip['telefone'][-4:]} <-> {parceiro['telefone'][-4:]}")
        return True

    except Exception as e:
        logger.error(f"[Orchestrator] Erro na conversa: {e}")
        return False


async def buscar_chip_com_instance(chip_id: str) -> Optional[dict]:
    """Busca chip com dados de instancia."""
    result = supabase.table("warmup_chips") \
        .select("id, telefone, instance_name, fase_warmup") \
        .eq("id", chip_id) \
        .single() \
        .execute()
    return result.data


async def criar_registro_conversa(par_id: str, mensagens: list) -> str:
    """Cria registro de conversa no banco."""
    result = supabase.table("warmup_conversations") \
        .insert({
            "pair_id": par_id,
            "tema": "warmup",
            "messages": mensagens,
            "turnos": len(mensagens),
        }) \
        .execute()
    return result.data[0]["id"]


async def finalizar_registro_conversa(conversa_id: str):
    """Marca conversa como finalizada."""
    supabase.table("warmup_conversations") \
        .update({
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }) \
        .eq("id", conversa_id) \
        .execute()


async def registrar_interacao_detalhada(chip_id: str, destinatario: str, texto: str):
    """Registra interacao detalhada no tracking."""
    supabase.table("warmup_interactions") \
        .insert({
            "chip_id": chip_id,
            "tipo": "msg_enviada",
            "destinatario": destinatario,
            "midia_tipo": "text",
            "metadata": {"texto_tamanho": len(texto)},
        }) \
        .execute()
```

### DoD

- [x] Funcao `executar_conversa_warmup`
- [x] Funcoes auxiliares implementadas
- [x] Registro de conversa no banco
- [x] Delays entre turnos
- [x] Tratamento de erros

---

## Story 7.5: Notificacoes

### Objetivo
Implementar sistema de notificacoes para eventos importantes.

### Implementacao

```python
async def notificar_progressao(
    chip: dict,
    fase_anterior: str,
    nova_fase: str,
    health: int,
    taxa_resposta: float
):
    """
    Notifica progressao de fase via Slack.

    Args:
        chip: Dados do chip
        fase_anterior: Fase anterior
        nova_fase: Nova fase
        health: Health score atual
        taxa_resposta: Taxa de resposta atual
    """
    emoji = {
        "primeiros_contatos": ":seedling:",
        "expansao": ":herb:",
        "pre_operacao": ":deciduous_tree:",
        "operacao": ":evergreen_tree:",
    }.get(nova_fase, ":rocket:")

    await enviar_slack({
        "text": f"{emoji} Chip avancou de fase!",
        "attachments": [{
            "color": "#22C55E",
            "fields": [
                {"title": "Telefone", "value": chip["telefone"][-4:], "short": True},
                {"title": "Progressao", "value": f"{fase_anterior} → {nova_fase}", "short": True},
                {"title": "Health", "value": str(health), "short": True},
                {"title": "Taxa Resposta", "value": f"{taxa_resposta:.0%}", "short": True},
            ],
        }]
    })


async def notificar_resumo_diario():
    """
    Envia resumo diario do warm-up via Slack.
    Executar 1x por dia via scheduler.
    """
    # Estatisticas gerais
    warming = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .eq("status", "warming") \
        .execute()

    ready = supabase.table("warmup_chips") \
        .select("*", count="exact") \
        .eq("status", "ready") \
        .execute()

    # Health medio
    chips = supabase.table("warmup_chips") \
        .select("health_score") \
        .eq("status", "warming") \
        .execute()

    health_medio = 0
    if chips.data:
        health_medio = sum(c["health_score"] for c in chips.data) / len(chips.data)

    # Alertas nao resolvidos
    alertas = supabase.table("warmup_alerts") \
        .select("*", count="exact") \
        .eq("resolved", False) \
        .execute()

    await enviar_slack({
        "text": ":bar_chart: *Resumo Diario - Julia Warmer*",
        "attachments": [{
            "color": "#3B82F6",
            "fields": [
                {"title": "Em Warm-up", "value": str(warming.count or 0), "short": True},
                {"title": "Prontos", "value": str(ready.count or 0), "short": True},
                {"title": "Health Medio", "value": f"{health_medio:.0f}", "short": True},
                {"title": "Alertas Ativos", "value": str(alertas.count or 0), "short": True},
            ],
        }]
    })
```

### DoD

- [x] Funcao `notificar_progressao`
- [x] Funcao `notificar_resumo_diario`
- [x] Mensagens formatadas para Slack
- [x] Emojis por fase

---

## Story 7.6: Integracao com Scheduler

### Objetivo
Configurar jobs periodicos para o orchestrator.

### Implementacao

```python
# Em app/workers/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.warmer.orchestrator import (
    executar_ciclo_warmup,
    notificar_resumo_diario,
)
from app.services.warmer.pairing_engine import rotacionar_pareamentos


def configurar_jobs_warmer(scheduler: AsyncIOScheduler):
    """
    Configura jobs do Julia Warmer no scheduler.

    Args:
        scheduler: Instancia do APScheduler
    """
    # Ciclo principal - a cada 5 minutos
    scheduler.add_job(
        executar_ciclo_warmup,
        'interval',
        minutes=5,
        id='warmer_ciclo',
        name='Julia Warmer - Ciclo Principal',
        replace_existing=True,
    )

    # Resumo diario - todos os dias as 18h
    scheduler.add_job(
        notificar_resumo_diario,
        'cron',
        hour=18,
        minute=0,
        id='warmer_resumo_diario',
        name='Julia Warmer - Resumo Diario',
        replace_existing=True,
    )

    # Rotacao de pares - toda segunda as 3h
    scheduler.add_job(
        rotacionar_pareamentos,
        'cron',
        day_of_week='mon',
        hour=3,
        minute=0,
        id='warmer_rotacao_pares',
        name='Julia Warmer - Rotacao de Pares',
        replace_existing=True,
    )

    logger.info("[Scheduler] Jobs do Julia Warmer configurados")
```

### DoD

- [x] Job de ciclo a cada 5 min
- [x] Job de resumo diario
- [x] Job de rotacao semanal
- [x] Integracao com APScheduler

---

## Checklist do Epico

- [x] **S25.E07.1** - Ciclo principal
- [x] **S25.E07.2** - Criterios de progressao
- [x] **S25.E07.3** - Avaliacao de progressao
- [x] **S25.E07.4** - Execucao de conversas
- [x] **S25.E07.5** - Notificacoes
- [x] **S25.E07.6** - Integracao com scheduler
- [x] Progressao automatica funcionando
- [x] Conversas executando corretamente
- [x] Notificacoes chegando
- [x] Jobs configurados

---

## Validacao

```python
import pytest
from app.services.warmer.orchestrator import (
    verificar_criterios_fase,
    CRITERIOS_FASE,
)


def test_criterios_fase_setup():
    """Testa criterios da fase setup."""
    # Nao cumpre dias
    ok, pendencias = verificar_criterios_fase("setup", 2, 50, 0)
    assert not ok
    assert "dias" in pendencias[0]

    # Nao cumpre health
    ok, pendencias = verificar_criterios_fase("setup", 3, 40, 0)
    assert not ok
    assert "health" in pendencias[0]

    # Cumpre todos
    ok, pendencias = verificar_criterios_fase("setup", 3, 45, 0)
    assert ok
    assert len(pendencias) == 0


def test_criterios_fase_expansao():
    """Testa criterios da fase expansao."""
    # Precisa de taxa de resposta
    ok, pendencias = verificar_criterios_fase("expansao", 7, 70, 0.3)
    assert not ok
    assert "taxa_resposta" in pendencias[0]

    # Cumpre todos
    ok, pendencias = verificar_criterios_fase("expansao", 7, 70, 0.4)
    assert ok


def test_criterios_fase_operacao():
    """Fase operacao nao tem progressao."""
    ok, pendencias = verificar_criterios_fase("operacao", 100, 100, 1.0)
    assert not ok
    assert "fase_final" in pendencias
```

---

## Diagrama: Fluxo do Orchestrator

```
┌─────────────────────────────────────────────────────────┐
│              executar_ciclo_warmup()                    │
│                  [a cada 5 min]                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Buscar chips warming  │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Para cada chip:     │
              │   processar_chip()    │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ pode_enviar │  │  avaliar_   │  │  monitorar_ │
│ _mensagem() │  │ progressao  │  │    chip()   │
└─────────────┘  └─────────────┘  └─────────────┘
         │                │                │
         │                ▼                │
         │       ┌─────────────┐          │
         │       │ Progressao? │          │
         │       └─────────────┘          │
         │              │                 │
         │        Sim   │   Nao           │
         │         │    │    │            │
         │         ▼    │    │            │
         │   ┌──────────┴─┐  │            │
         │   │ Atualizar  │  │            │
         │   │   fase     │  │            │
         │   └────────────┘  │            │
         │         │         │            │
         │         ▼         │            │
         │   ┌────────────┐  │            │
         │   │ Notificar  │  │            │
         │   │   Slack    │  │            │
         │   └────────────┘  │            │
         │                   │            │
         └─────────┬─────────┘            │
                   │                      │
                   ▼                      │
          ┌─────────────┐                 │
          │ Se pode     │                 │
          │ enviar:     │                 │
          │ executar_   │                 │
          │ conversa()  │                 │
          └─────────────┘                 │
                   │                      │
                   ▼                      │
          ┌─────────────┐                 │
          │ registrar_  │                 │
          │ health_     │◄────────────────┘
          │ score()     │
          └─────────────┘
```

---

## Timeline de Fases

```
Dia 0                                                    Dia 21+
│                                                        │
├──────┬────────────┬──────────────┬──────────────┬─────►
│      │            │              │              │
│ SETUP│ PRIMEIROS  │   EXPANSAO   │ PRE-OPERACAO │ OPERACAO
│      │  CONTATOS  │              │              │
│      │            │              │              │
│ 3d   │     4d     │      7d      │      7d      │  ∞
│      │            │              │              │
│ 0msg │   10/dia   │    30/dia    │    50/dia    │ 100/dia
│      │            │              │              │
│ H≥45 │    H≥55    │     H≥70     │     H≥85     │  READY
│      │   TR≥50%   │    TR≥40%    │    TR≥35%    │
│                                                        │
└────────────────────────────────────────────────────────┘

Legenda:
- H = Health Score minimo
- TR = Taxa de Resposta minima
- msg = Mensagens por dia
```

