# Epic 08: Warming Scheduler

**Status:** ✅ Completo

**Arquivos criados:**
- `app/services/warmer/scheduler.py`

---

## Objetivo

Agendar mensagens com distribuicao anti-padrao para evitar deteccao de automacao. Cada chip tem janela de atividade unica baseada em hash deterministico.

## Contexto

O WhatsApp detecta automacao por padroes:
- Todos os chips enviando no mesmo horario
- Intervalos fixos entre mensagens
- Atividade fora de horario comercial

Solucao:
- **Janela de atividade**: 6h por chip, dentro de 8h-22h
- **Hash deterministico**: Mesmo chip = mesma janela (consistencia)
- **Limites por fase**: Fase inicial = menos msgs
- **Delay minimo**: 2 min entre msgs do mesmo chip

---

## Story 6.1: Calculo de Janela de Atividade

### Objetivo
Calcular janela de atividade unica para cada chip baseado em hash.

### Implementacao

**Arquivo:** `app/services/warmer/scheduler.py`

```python
"""
Message Scheduler - Agenda mensagens com distribuicao anti-padrao.

Cada chip tem janela de atividade unica baseada em hash do ID.
Previne que todos os chips enviem no mesmo horario.
"""
import hashlib
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Tuple, Optional

from app.services.redis import redis_client
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# Constantes
JANELA_HORAS = 6           # Duracao da janela de atividade
HORARIO_INICIO = 8         # 8h da manha
HORARIO_FIM = 22           # 22h da noite
DELAY_MINIMO_SEGUNDOS = 120  # 2 minutos entre msgs


def calcular_janela_atividade(chip_id: str, dia: date) -> Tuple[int, int, int, int]:
    """
    Calcula janela de atividade unica para o chip neste dia.

    Baseado em hash deterministico do chip_id + dia.
    Cada chip tem janela de 6 horas dentro do periodo 8h-22h.

    O hash garante que:
    - Mesmo chip = mesma janela (consistencia)
    - Chips diferentes = janelas diferentes (distribuicao)
    - Dia diferente = variacao sutil (naturalidade)

    Args:
        chip_id: UUID do chip
        dia: Data

    Returns:
        Tupla (hora_inicio, minuto_inicio, hora_fim, minuto_fim)
    """
    # Hash deterministico
    seed = f"{chip_id}{dia}".encode()
    hash_int = int(hashlib.md5(seed).hexdigest(), 16)

    # Janela de 6 horas dentro de 8h-22h (14h disponiveis)
    # Inicio pode ser de 8h ate 16h (para terminar antes das 22h)
    inicio_possivel = HORARIO_INICIO  # 8h
    fim_possivel = HORARIO_FIM - JANELA_HORAS  # 16h

    hora_inicio = inicio_possivel + (hash_int % (fim_possivel - inicio_possivel + 1))
    minuto_inicio = hash_int % 30  # Variacao de 0-29 min

    hora_fim = hora_inicio + JANELA_HORAS
    minuto_fim = (hash_int >> 8) % 30  # Outra parte do hash

    return (hora_inicio, minuto_inicio, hora_fim, minuto_fim)


def formatar_janela(janela: Tuple[int, int, int, int]) -> str:
    """
    Formata janela para exibicao.

    Args:
        janela: Tupla (hora_inicio, minuto_inicio, hora_fim, minuto_fim)

    Returns:
        String formatada ex: "08:15 - 14:15"
    """
    h1, m1, h2, m2 = janela
    return f"{h1:02d}:{m1:02d} - {h2:02d}:{m2:02d}"
```

### DoD

- [x] Funcao `calcular_janela_atividade` implementada
- [x] Hash deterministico funcionando
- [x] Janela de 6h dentro de 8h-22h
- [x] Funcao `formatar_janela`

---

## Story 6.2: Verificacao de Janela

### Objetivo
Verificar se chip esta dentro da sua janela de atividade.

### Implementacao

```python
def esta_na_janela(chip_id: str, agora: Optional[datetime] = None) -> bool:
    """
    Verifica se o chip esta na sua janela de atividade.

    Args:
        chip_id: UUID do chip
        agora: Datetime atual (opcional, para testes)

    Returns:
        True se esta na janela
    """
    if agora is None:
        agora = datetime.now(timezone.utc)

    # Ajustar para horario de Brasilia (UTC-3)
    agora_br = agora - timedelta(hours=3)

    janela = calcular_janela_atividade(chip_id, agora_br.date())
    hora_inicio, min_inicio, hora_fim, min_fim = janela

    inicio = time(hora_inicio, min_inicio)
    fim = time(hora_fim, min_fim)
    atual = agora_br.time()

    na_janela = inicio <= atual <= fim

    logger.debug(
        f"[Scheduler] Chip {chip_id[:8]} janela {formatar_janela(janela)}, "
        f"agora {atual.strftime('%H:%M')}, na_janela={na_janela}"
    )

    return na_janela


def proxima_janela(chip_id: str) -> datetime:
    """
    Calcula quando sera a proxima janela de atividade.

    Args:
        chip_id: UUID do chip

    Returns:
        Datetime do inicio da proxima janela
    """
    agora = datetime.now(timezone.utc)
    agora_br = agora - timedelta(hours=3)

    # Verificar janela de hoje
    janela_hoje = calcular_janela_atividade(chip_id, agora_br.date())
    hora_inicio, min_inicio, _, _ = janela_hoje

    inicio_hoje = datetime.combine(
        agora_br.date(),
        time(hora_inicio, min_inicio)
    ).replace(tzinfo=timezone.utc) + timedelta(hours=3)  # Volta pra UTC

    if agora < inicio_hoje:
        return inicio_hoje

    # Janela de amanha
    amanha = agora_br.date() + timedelta(days=1)
    janela_amanha = calcular_janela_atividade(chip_id, amanha)
    hora_inicio, min_inicio, _, _ = janela_amanha

    return datetime.combine(
        amanha,
        time(hora_inicio, min_inicio)
    ).replace(tzinfo=timezone.utc) + timedelta(hours=3)
```

### DoD

- [x] Funcao `esta_na_janela`
- [x] Conversao para horario de Brasilia
- [x] Funcao `proxima_janela`

---

## Story 6.3: Limites por Fase

### Objetivo
Definir e aplicar limites de mensagens por fase de warm-up.

### Implementacao

```python
# Limites de mensagens por fase
LIMITES_FASE = {
    "setup": 0,               # Fase setup nao envia msgs
    "primeiros_contatos": 10, # 10 msgs/dia
    "expansao": 30,           # 30 msgs/dia
    "pre_operacao": 50,       # 50 msgs/dia
    "operacao": 100,          # 100 msgs/dia (chip pronto)
}

# Limites de entrada em grupos por fase (ver E12: Group Entry Engine)
LIMITES_GRUPOS_FASE = {
    "setup": 0,                # Sem entrada em grupos
    "primeiros_contatos": 0,   # Sem entrada em grupos
    "expansao": 2,             # 2 grupos/dia (delay 10 min)
    "pre_operacao": 5,         # 5 grupos/dia (delay 5 min)
    "operacao": 10,            # 10 grupos/dia (delay 3 min)
}

# Delay entre entradas em grupos (segundos)
DELAY_GRUPOS_FASE = {
    "expansao": 600,           # 10 min
    "pre_operacao": 300,       # 5 min
    "operacao": 180,           # 3 min
}


async def obter_limite_diario(chip_id: str) -> int:
    """
    Obtem limite diario de mensagens baseado na fase.

    Args:
        chip_id: UUID do chip

    Returns:
        Limite de mensagens
    """
    chip = supabase.table("warmup_chips") \
        .select("fase_warmup") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return 0

    fase = chip.data.get("fase_warmup", "setup")
    limite = LIMITES_FASE.get(fase, 10)

    logger.debug(f"[Scheduler] Chip {chip_id[:8]} fase={fase} limite={limite}")

    return limite


async def contar_msgs_hoje(chip_id: str) -> int:
    """
    Conta mensagens enviadas hoje pelo chip.

    Args:
        chip_id: UUID do chip

    Returns:
        Quantidade de mensagens
    """
    hoje = date.today().isoformat()
    key = f"warmer:msgs_dia:{chip_id}:{hoje}"

    count = await redis_client.get(key)
    return int(count or 0)


async def atingiu_limite_diario(chip_id: str) -> bool:
    """
    Verifica se chip atingiu limite diario.

    Args:
        chip_id: UUID do chip

    Returns:
        True se atingiu limite
    """
    limite = await obter_limite_diario(chip_id)
    enviadas = await contar_msgs_hoje(chip_id)

    return enviadas >= limite
```

### DoD

- [x] Constantes `LIMITES_FASE` definidas
- [x] Funcao `obter_limite_diario`
- [x] Funcao `contar_msgs_hoje`
- [x] Funcao `atingiu_limite_diario`

---

## Story 6.4: Delay Minimo entre Mensagens

### Objetivo
Garantir delay minimo de 2 minutos entre mensagens do mesmo chip.

### Implementacao

```python
async def verificar_delay_minimo(chip_id: str) -> Tuple[bool, int]:
    """
    Verifica se passou tempo suficiente desde ultima mensagem.

    Args:
        chip_id: UUID do chip

    Returns:
        Tupla (pode_enviar, segundos_restantes)
    """
    key = f"warmer:ultima_msg:{chip_id}"
    ultima = await redis_client.get(key)

    if not ultima:
        return True, 0

    ultima_dt = datetime.fromisoformat(ultima.decode())
    agora = datetime.now(timezone.utc)
    diferenca = (agora - ultima_dt).total_seconds()

    if diferenca >= DELAY_MINIMO_SEGUNDOS:
        return True, 0

    restante = int(DELAY_MINIMO_SEGUNDOS - diferenca)
    return False, restante


async def registrar_envio(chip_id: str):
    """
    Registra que uma mensagem foi enviada.

    Args:
        chip_id: UUID do chip
    """
    agora = datetime.now(timezone.utc)
    hoje = date.today().isoformat()

    # Incrementar contador diario
    key_dia = f"warmer:msgs_dia:{chip_id}:{hoje}"
    await redis_client.incr(key_dia)
    await redis_client.expire(key_dia, 86400 * 2)  # Expira em 2 dias

    # Registrar timestamp
    key_ultima = f"warmer:ultima_msg:{chip_id}"
    await redis_client.set(key_ultima, agora.isoformat())
    await redis_client.expire(key_ultima, 86400)  # Expira em 1 dia

    logger.debug(f"[Scheduler] Envio registrado: {chip_id[:8]}")
```

### DoD

- [x] Funcao `verificar_delay_minimo`
- [x] Funcao `registrar_envio`
- [x] Delay de 2 minutos respeitado
- [x] TTL correto no Redis

---

## Story 6.5: Verificacao Completa

### Objetivo
Funcao principal que verifica todos os criterios de envio.

### Implementacao

```python
async def pode_enviar_mensagem(chip_id: str) -> Tuple[bool, str]:
    """
    Verifica se o chip pode enviar mensagem agora.

    Checks:
    1. Chip existe e esta em warming
    2. Esta na janela de atividade
    3. Nao excedeu limite diario
    4. Respeitou delay minimo desde ultima msg

    Args:
        chip_id: UUID do chip

    Returns:
        Tupla (pode_enviar, motivo)
    """
    # Check 0: Chip existe e esta ativo
    chip = supabase.table("warmup_chips") \
        .select("status, fase_warmup") \
        .eq("id", chip_id) \
        .single() \
        .execute()

    if not chip.data:
        return False, "chip_nao_encontrado"

    if chip.data["status"] != "warming":
        return False, f"status_invalido:{chip.data['status']}"

    # Check 1: Janela de atividade
    if not esta_na_janela(chip_id):
        return False, "fora_janela"

    # Check 2: Limite diario
    if await atingiu_limite_diario(chip_id):
        return False, "limite_diario"

    # Check 3: Delay minimo
    pode, restante = await verificar_delay_minimo(chip_id)
    if not pode:
        return False, f"delay_minimo:{restante}s"

    # Check 4: Verificar fator de velocidade (reducao por warning)
    fator = await obter_fator_velocidade(chip_id)
    if fator < 1.0:
        # Chance de nao enviar baseado no fator
        import random
        if random.random() > fator:
            return False, f"velocidade_reduzida:{fator}"

    return True, "ok"


async def obter_fator_velocidade(chip_id: str) -> float:
    """
    Obtem fator de velocidade do chip.
    1.0 = normal, 0.5 = 50% das msgs, etc.

    Args:
        chip_id: UUID do chip

    Returns:
        Fator de velocidade (0.0 a 1.0)
    """
    key = f"warmer:velocidade:{chip_id}"
    fator = await redis_client.get(key)

    if fator:
        return float(fator.decode())
    return 1.0


async def definir_fator_velocidade(chip_id: str, fator: float):
    """
    Define fator de velocidade do chip.

    Args:
        chip_id: UUID do chip
        fator: Fator de 0.0 a 1.0
    """
    key = f"warmer:velocidade:{chip_id}"
    await redis_client.set(key, str(fator))
    await redis_client.expire(key, 86400)  # 24h

    logger.info(f"[Scheduler] Velocidade definida: {chip_id[:8]} = {fator}")
```

### DoD

- [x] Funcao `pode_enviar_mensagem` com todos os checks
- [x] Funcao `obter_fator_velocidade`
- [x] Funcao `definir_fator_velocidade`
- [x] Logs claros para debug

---

## Story 6.6: Utilidades de Agendamento

### Objetivo
Funcoes auxiliares para visualizacao e debug.

### Implementacao

```python
async def obter_status_agendamento(chip_id: str) -> dict:
    """
    Obtem status completo de agendamento do chip.

    Args:
        chip_id: UUID do chip

    Returns:
        Dict com status detalhado
    """
    agora = datetime.now(timezone.utc)
    agora_br = agora - timedelta(hours=3)

    janela = calcular_janela_atividade(chip_id, agora_br.date())
    na_janela = esta_na_janela(chip_id, agora)
    limite = await obter_limite_diario(chip_id)
    enviadas = await contar_msgs_hoje(chip_id)
    pode_delay, delay_restante = await verificar_delay_minimo(chip_id)
    fator = await obter_fator_velocidade(chip_id)
    pode, motivo = await pode_enviar_mensagem(chip_id)

    return {
        "chip_id": chip_id,
        "horario_br": agora_br.strftime("%H:%M"),
        "janela": formatar_janela(janela),
        "na_janela": na_janela,
        "limite_diario": limite,
        "msgs_enviadas_hoje": enviadas,
        "msgs_restantes": max(0, limite - enviadas),
        "delay_ok": pode_delay,
        "delay_restante_segundos": delay_restante,
        "fator_velocidade": fator,
        "pode_enviar": pode,
        "motivo": motivo,
    }


async def listar_janelas_todos_chips() -> list[dict]:
    """
    Lista janelas de atividade de todos os chips em warming.

    Returns:
        Lista de chips com suas janelas
    """
    chips = supabase.table("warmup_chips") \
        .select("id, telefone, fase_warmup") \
        .eq("status", "warming") \
        .execute()

    hoje = date.today()
    resultado = []

    for chip in chips.data or []:
        janela = calcular_janela_atividade(chip["id"], hoje)
        resultado.append({
            "chip_id": chip["id"],
            "telefone": chip["telefone"][-4:],
            "fase": chip["fase_warmup"],
            "janela": formatar_janela(janela),
        })

    # Ordenar por hora de inicio
    resultado.sort(key=lambda x: x["janela"])

    return resultado
```

### DoD

- [x] Funcao `obter_status_agendamento`
- [x] Funcao `listar_janelas_todos_chips`
- [x] Informacoes completas para debug

---

## Checklist do Epico

- [x] **S25.E06.1** - Calculo de janela de atividade
- [x] **S25.E06.2** - Verificacao de janela
- [x] **S25.E06.3** - Limites por fase
- [x] **S25.E06.4** - Delay minimo
- [x] **S25.E06.5** - Verificacao completa
- [x] **S25.E06.6** - Utilidades
- [x] Hash deterministico funcionando
- [x] Distribuicao anti-padrao verificada
- [x] Testes completos

---

## Validacao

```python
import pytest
from datetime import date, time
from app.services.warmer.scheduler import (
    calcular_janela_atividade,
    esta_na_janela,
    formatar_janela,
    LIMITES_FASE,
)


def test_janela_deterministica():
    """Testa que mesmo chip = mesma janela."""
    chip_id = "test-chip-123"
    dia = date(2025, 12, 30)

    janela1 = calcular_janela_atividade(chip_id, dia)
    janela2 = calcular_janela_atividade(chip_id, dia)

    assert janela1 == janela2


def test_janela_diferente_por_chip():
    """Testa que chips diferentes = janelas diferentes."""
    dia = date(2025, 12, 30)

    janelas = set()
    for i in range(20):
        chip_id = f"chip-{i}"
        janela = calcular_janela_atividade(chip_id, dia)
        janelas.add(janela)

    # Deve ter variedade (nao todas iguais)
    assert len(janelas) > 5


def test_janela_dentro_horario():
    """Testa que janela esta dentro de 8h-22h."""
    chip_id = "test-chip"
    dia = date(2025, 12, 30)

    for _ in range(100):
        chip_id = f"chip-{_}"
        h1, m1, h2, m2 = calcular_janela_atividade(chip_id, dia)

        assert h1 >= 8
        assert h2 <= 22
        assert h2 - h1 == 6  # Janela de 6h


def test_formatar_janela():
    """Testa formatacao de janela."""
    janela = (8, 15, 14, 30)
    assert formatar_janela(janela) == "08:15 - 14:30"


def test_limites_fase():
    """Testa que limites estao corretos."""
    assert LIMITES_FASE["setup"] == 0
    assert LIMITES_FASE["primeiros_contatos"] == 10
    assert LIMITES_FASE["operacao"] == 100
```

---

## Diagrama: Distribuicao de Janelas

```
Horario    08h   10h   12h   14h   16h   18h   20h   22h
           │     │     │     │     │     │     │     │
CHIP_001   ├─────────────┤
           [08:15 - 14:15]

CHIP_002         ├─────────────┤
                 [10:22 - 16:22]

CHIP_003               ├─────────────┤
                       [12:05 - 18:05]

CHIP_004                     ├─────────────┤
                             [14:18 - 20:18]

CHIP_005   ├─────────────┤
           [08:45 - 14:45]

CHIP_006                           ├─────────────┤
                                   [16:00 - 22:00]

Resultado: Distribuicao uniforme ao longo do dia
           Sem concentracao em horarios especificos
```

---

## Fluxo de Verificacao

```
┌─────────────────────────────────────────────────────────┐
│             pode_enviar_mensagem(chip_id)               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Chip existe e ativo?  │
              └───────────────────────┘
                    │           │
                   Nao         Sim
                    │           │
                    ▼           ▼
              "chip_nao_     ┌───────────────────────┐
               encontrado"   │ Esta na janela?       │
                             └───────────────────────┘
                                   │           │
                                  Nao         Sim
                                   │           │
                                   ▼           ▼
                             "fora_janela"  ┌───────────────────────┐
                                            │ Limite diario ok?     │
                                            └───────────────────────┘
                                                  │           │
                                                 Nao         Sim
                                                  │           │
                                                  ▼           ▼
                                            "limite_       ┌───────────────────────┐
                                             diario"       │ Delay minimo ok?      │
                                                           └───────────────────────┘
                                                                 │           │
                                                                Nao         Sim
                                                                 │           │
                                                                 ▼           ▼
                                                           "delay_        ┌───────────────────────┐
                                                            minimo"       │ Fator velocidade ok?  │
                                                                          └───────────────────────┘
                                                                                │           │
                                                                               Nao         Sim
                                                                                │           │
                                                                                ▼           ▼
                                                                          "velocidade_   "ok" ✓
                                                                           reduzida"
```

