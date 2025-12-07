# Epic 3: Segurança e Resiliência

## Objetivo do Epic

> **Garantir que o sistema seja seguro, resiliente e respeite limites críticos.**

Este epic protege contra:
- Ban do WhatsApp (rate limiting)
- Falhas em cascata (circuit breaker)
- Reclamações legais (opt-out)

---

## Stories

1. [S1.E3.1 - Rate Limiting](#s1e31---rate-limiting)
2. [S1.E3.2 - Circuit Breaker](#s1e32---circuit-breaker)
3. [S1.E3.3 - Opt-out Imediato](#s1e33---opt-out-imediato)

---

# S1.E3.1 - Rate Limiting

## Objetivo

> **Implementar limites de envio de mensagens para evitar ban do WhatsApp.**

WhatsApp bane números que enviam muitas mensagens rapidamente. Precisamos controlar o volume.

**Resultado esperado:** Sistema respeita limites de 20 msg/hora, 100 msg/dia, com intervalos mínimos entre mensagens.

---

## Contexto

Limites definidos no CLAUDE.md:

| Limite | Valor | Motivo |
|--------|-------|--------|
| Mensagens/hora | 20 | Evitar ban |
| Mensagens/dia | 100 | Evitar ban |
| Intervalo entre msgs | 45-180s | Parecer humano |
| Horário | 08h-20h | Horário comercial |
| Dias | Seg-Sex | Horário comercial |

---

## Responsável

**Dev**

---

## Pré-requisitos

- [ ] Redis rodando (já está no Docker Compose)

---

## Tarefas

### 1. Criar serviço de rate limiting

```python
# app/services/rate_limiter.py

"""
Rate limiter para controle de envio de mensagens.
Usa Redis para persistência e contagem distribuída.
"""
import logging
from datetime import datetime, timedelta
from typing import Tuple
import random

from app.services.redis import redis_client

logger = logging.getLogger(__name__)

# Constantes de limite
LIMITE_POR_HORA = 20
LIMITE_POR_DIA = 100
INTERVALO_MIN_SEGUNDOS = 45
INTERVALO_MAX_SEGUNDOS = 180
HORA_INICIO = 8  # 08:00
HORA_FIM = 20    # 20:00
DIAS_PERMITIDOS = [0, 1, 2, 3, 4]  # Seg-Sex (0=Segunda)


class RateLimitExceeded(Exception):
    """Exceção quando limite de rate é excedido."""
    def __init__(self, motivo: str, retry_after: int = None):
        self.motivo = motivo
        self.retry_after = retry_after
        super().__init__(motivo)


async def verificar_horario_permitido() -> Tuple[bool, str]:
    """
    Verifica se estamos em horário comercial.

    Returns:
        (permitido, motivo)
    """
    agora = datetime.now()

    # Verificar dia da semana
    if agora.weekday() not in DIAS_PERMITIDOS:
        return False, "Fora do horário comercial (fim de semana)"

    # Verificar hora
    if agora.hour < HORA_INICIO:
        return False, f"Antes do horário comercial ({HORA_INICIO}h)"

    if agora.hour >= HORA_FIM:
        return False, f"Após horário comercial ({HORA_FIM}h)"

    return True, "OK"


async def verificar_limite_hora() -> Tuple[bool, int]:
    """
    Verifica limite de mensagens por hora.

    Returns:
        (dentro_limite, msgs_enviadas)
    """
    chave = f"rate:hora:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        count = await redis_client.get(chave)
        count = int(count) if count else 0

        return count < LIMITE_POR_HORA, count
    except Exception as e:
        logger.error(f"Erro ao verificar limite hora: {e}")
        return True, 0  # Em caso de erro, permitir


async def verificar_limite_dia() -> Tuple[bool, int]:
    """
    Verifica limite de mensagens por dia.

    Returns:
        (dentro_limite, msgs_enviadas)
    """
    chave = f"rate:dia:{datetime.now().strftime('%Y%m%d')}"

    try:
        count = await redis_client.get(chave)
        count = int(count) if count else 0

        return count < LIMITE_POR_DIA, count
    except Exception as e:
        logger.error(f"Erro ao verificar limite dia: {e}")
        return True, 0


async def verificar_intervalo_minimo(telefone: str) -> Tuple[bool, int]:
    """
    Verifica se passou tempo suficiente desde última mensagem para este número.

    Returns:
        (pode_enviar, segundos_restantes)
    """
    chave = f"rate:ultimo:{telefone}"

    try:
        ultimo = await redis_client.get(chave)
        if not ultimo:
            return True, 0

        ultimo_ts = float(ultimo)
        agora = datetime.now().timestamp()
        diferenca = agora - ultimo_ts

        if diferenca < INTERVALO_MIN_SEGUNDOS:
            segundos_restantes = int(INTERVALO_MIN_SEGUNDOS - diferenca)
            return False, segundos_restantes

        return True, 0
    except Exception as e:
        logger.error(f"Erro ao verificar intervalo: {e}")
        return True, 0


async def registrar_envio(telefone: str) -> None:
    """
    Registra que uma mensagem foi enviada.
    Incrementa contadores e registra timestamp.
    """
    try:
        agora = datetime.now()

        # Incrementar contador por hora (expira em 2 horas)
        chave_hora = f"rate:hora:{agora.strftime('%Y%m%d%H')}"
        await redis_client.incr(chave_hora)
        await redis_client.expire(chave_hora, 7200)

        # Incrementar contador por dia (expira em 25 horas)
        chave_dia = f"rate:dia:{agora.strftime('%Y%m%d')}"
        await redis_client.incr(chave_dia)
        await redis_client.expire(chave_dia, 90000)

        # Registrar timestamp da última mensagem para este telefone
        chave_ultimo = f"rate:ultimo:{telefone}"
        await redis_client.set(chave_ultimo, str(agora.timestamp()))
        await redis_client.expire(chave_ultimo, 3600)

        logger.debug(f"Envio registrado para {telefone}")

    except Exception as e:
        logger.error(f"Erro ao registrar envio: {e}")


async def pode_enviar(telefone: str) -> Tuple[bool, str]:
    """
    Verifica se pode enviar mensagem agora.

    Args:
        telefone: Número do destinatário

    Returns:
        (pode_enviar, motivo)
    """
    # 1. Verificar horário comercial
    ok, motivo = await verificar_horario_permitido()
    if not ok:
        return False, motivo

    # 2. Verificar limite por hora
    ok, count = await verificar_limite_hora()
    if not ok:
        return False, f"Limite por hora atingido ({count}/{LIMITE_POR_HORA})"

    # 3. Verificar limite por dia
    ok, count = await verificar_limite_dia()
    if not ok:
        return False, f"Limite por dia atingido ({count}/{LIMITE_POR_DIA})"

    # 4. Verificar intervalo mínimo
    ok, segundos = await verificar_intervalo_minimo(telefone)
    if not ok:
        return False, f"Aguardar {segundos}s antes de enviar novamente"

    return True, "OK"


def calcular_delay_humanizado() -> int:
    """
    Calcula delay variável para parecer humano.

    Returns:
        Segundos para aguardar antes de enviar
    """
    # Distribuição não-uniforme: mais provável delays menores
    # mas ocasionalmente delays maiores
    base = random.randint(INTERVALO_MIN_SEGUNDOS, INTERVALO_MAX_SEGUNDOS)
    variacao = random.randint(-10, 20)

    return max(INTERVALO_MIN_SEGUNDOS, base + variacao)


async def obter_estatisticas() -> dict:
    """
    Retorna estatísticas de uso atual.
    """
    try:
        agora = datetime.now()

        chave_hora = f"rate:hora:{agora.strftime('%Y%m%d%H')}"
        chave_dia = f"rate:dia:{agora.strftime('%Y%m%d')}"

        msgs_hora = await redis_client.get(chave_hora)
        msgs_dia = await redis_client.get(chave_dia)

        return {
            "msgs_hora": int(msgs_hora) if msgs_hora else 0,
            "limite_hora": LIMITE_POR_HORA,
            "msgs_dia": int(msgs_dia) if msgs_dia else 0,
            "limite_dia": LIMITE_POR_DIA,
            "horario_permitido": (await verificar_horario_permitido())[0],
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}
```

### 2. Criar cliente Redis

```python
# app/services/redis.py

"""
Cliente Redis para rate limiting e cache.
"""
import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)


async def verificar_conexao_redis() -> bool:
    """Verifica se Redis está acessível."""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis não acessível: {e}")
        return False
```

### 3. Adicionar configuração Redis

```python
# Adicionar em app/core/config.py

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

### 4. Integrar rate limiting no envio de mensagens

```python
# Atualizar app/services/whatsapp.py

from app.services.rate_limiter import pode_enviar, registrar_envio, RateLimitExceeded

async def enviar_whatsapp(telefone: str, texto: str) -> bool:
    """
    Envia mensagem via WhatsApp com rate limiting.
    """
    # Verificar rate limit antes de enviar
    permitido, motivo = await pode_enviar(telefone)
    if not permitido:
        logger.warning(f"Rate limit: {motivo}")
        raise RateLimitExceeded(motivo)

    # Enviar mensagem
    resultado = await evolution.enviar_texto(telefone, texto)

    # Registrar envio
    if resultado:
        await registrar_envio(telefone)

    return resultado
```

### 5. Criar testes

```python
# tests/test_rate_limiter.py

import pytest
from datetime import datetime
from app.services.rate_limiter import (
    verificar_horario_permitido,
    pode_enviar,
    calcular_delay_humanizado,
    INTERVALO_MIN_SEGUNDOS,
    INTERVALO_MAX_SEGUNDOS,
)


class TestHorarioPermitido:
    def test_horario_comercial(self, mocker):
        # Mock datetime para 10h de segunda
        mock_dt = datetime(2025, 12, 8, 10, 0)  # Segunda-feira
        mocker.patch('app.services.rate_limiter.datetime')
        # ... implementar mock

    def test_fora_horario(self):
        # Testar antes das 8h, depois das 20h, fim de semana
        pass


class TestDelayHumanizado:
    def test_delay_dentro_limites(self):
        for _ in range(100):
            delay = calcular_delay_humanizado()
            assert delay >= INTERVALO_MIN_SEGUNDOS
            assert delay <= INTERVALO_MAX_SEGUNDOS + 20


class TestPodeEnviar:
    @pytest.mark.asyncio
    async def test_pode_enviar_normal(self):
        # Em condições normais, deve permitir
        pass

    @pytest.mark.asyncio
    async def test_bloqueia_apos_limite_hora(self):
        # Após 20 msgs na hora, deve bloquear
        pass
```

---

## Como Testar

```bash
# 1. Verificar Redis está rodando
docker compose ps | grep redis

# 2. Testar estatísticas
curl http://localhost:8000/test/rate-limit/stats

# 3. Testar envio (deve funcionar)
curl -X POST http://localhost:8000/test/rate-limit/enviar \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999"}'

# 4. Enviar 21 mensagens rápidas - a 21ª deve falhar
for i in {1..21}; do
  echo "Tentativa $i:"
  curl -X POST http://localhost:8000/test/rate-limit/enviar \
    -H "Content-Type: application/json" \
    -d '{"telefone": "5511999999999"}'
  echo ""
done
```

---

## DoD (Definition of Done)

- [x] Cliente Redis configurado ✅ Testado em 2025-12-07
- [x] `verificar_horario_permitido()` implementada ✅ Testado em 2025-12-07
- [x] `verificar_limite_hora()` implementada ✅ Testado em 2025-12-07
- [x] `verificar_limite_dia()` implementada ✅ Testado em 2025-12-07
- [x] `verificar_intervalo_minimo()` implementada ✅ Testado em 2025-12-07
- [x] `pode_enviar()` integra todas as verificações ✅ Testado em 2025-12-07
- [x] `registrar_envio()` incrementa contadores ✅ Testado em 2025-12-07
- [x] Envio de WhatsApp usa rate limiting ✅ Integrado em 2025-12-07
- [x] Testes unitários passando (19/19) ✅ 2025-12-07
- [ ] 21ª mensagem na hora é bloqueada (teste E2E pendente)
- [x] Mensagem fora do horário comercial é bloqueada ✅ Testado em 2025-12-07

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| Redis connection refused | Redis não rodando | `docker compose up redis` |
| Rate limit não persiste | Chaves expirando | Verificar TTL |
| Mensagens passando do limite | Redis não sendo usado | Verificar integração |

---
---

# S1.E3.2 - Circuit Breaker

## Objetivo

> **Implementar circuit breaker para lidar com falhas em serviços externos.**

Quando Evolution API, Claude ou Supabase falham, precisamos:
1. Não derrubar todo o sistema
2. Parar de tentar chamadas que vão falhar
3. Recuperar automaticamente quando voltar

**Resultado esperado:** Sistema degrada graciosamente quando serviços externos falham.

---

## Contexto

Serviços que podem falhar:
- **Evolution API** - WhatsApp indisponível
- **Claude API** - LLM indisponível
- **Supabase** - Banco indisponível

Estados do circuit breaker:
- **CLOSED** - Normal, chamadas passam
- **OPEN** - Falhas demais, bloqueia chamadas
- **HALF-OPEN** - Testando se recuperou

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar circuit breaker

```python
# app/services/circuit_breaker.py

"""
Circuit breaker para serviços externos.
Previne falhas em cascata e permite recuperação automática.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal, chamadas passam
    OPEN = "open"          # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação


@dataclass
class CircuitBreaker:
    """
    Circuit breaker para um serviço específico.
    """
    nome: str
    falhas_para_abrir: int = 5           # Falhas consecutivas para abrir
    timeout_segundos: float = 30.0       # Timeout para chamadas
    tempo_reset_segundos: int = 60       # Tempo antes de tentar half-open

    # Estado interno
    estado: CircuitState = field(default=CircuitState.CLOSED)
    falhas_consecutivas: int = field(default=0)
    ultima_falha: Optional[datetime] = field(default=None)
    ultimo_sucesso: Optional[datetime] = field(default=None)

    def _verificar_transicao_half_open(self):
        """Verifica se deve transicionar para half-open."""
        if self.estado != CircuitState.OPEN:
            return

        if self.ultima_falha is None:
            return

        tempo_desde_falha = datetime.now() - self.ultima_falha
        if tempo_desde_falha.total_seconds() >= self.tempo_reset_segundos:
            logger.info(f"Circuit {self.nome}: OPEN -> HALF_OPEN")
            self.estado = CircuitState.HALF_OPEN

    def _registrar_sucesso(self):
        """Registra uma chamada bem-sucedida."""
        self.falhas_consecutivas = 0
        self.ultimo_sucesso = datetime.now()

        if self.estado == CircuitState.HALF_OPEN:
            logger.info(f"Circuit {self.nome}: HALF_OPEN -> CLOSED (recuperado)")
            self.estado = CircuitState.CLOSED

    def _registrar_falha(self, erro: Exception):
        """Registra uma falha."""
        self.falhas_consecutivas += 1
        self.ultima_falha = datetime.now()

        logger.warning(
            f"Circuit {self.nome}: falha {self.falhas_consecutivas}/{self.falhas_para_abrir} - {erro}"
        )

        if self.estado == CircuitState.HALF_OPEN:
            logger.info(f"Circuit {self.nome}: HALF_OPEN -> OPEN (falha na recuperação)")
            self.estado = CircuitState.OPEN

        elif self.falhas_consecutivas >= self.falhas_para_abrir:
            logger.warning(f"Circuit {self.nome}: CLOSED -> OPEN (muitas falhas)")
            self.estado = CircuitState.OPEN

    async def executar(
        self,
        func: Callable,
        *args,
        fallback: Callable = None,
        **kwargs
    ) -> Any:
        """
        Executa função com proteção do circuit breaker.

        Args:
            func: Função async a executar
            *args: Argumentos para a função
            fallback: Função a chamar se circuit estiver aberto
            **kwargs: Kwargs para a função

        Returns:
            Resultado da função ou do fallback

        Raises:
            CircuitOpenError: Se circuit está aberto e não há fallback
        """
        # Verificar transição para half-open
        self._verificar_transicao_half_open()

        # Se aberto, usar fallback ou falhar
        if self.estado == CircuitState.OPEN:
            if fallback:
                logger.debug(f"Circuit {self.nome} aberto, usando fallback")
                return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit {self.nome} está aberto")

        # Tentar executar
        try:
            resultado = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_segundos
            )
            self._registrar_sucesso()
            return resultado

        except asyncio.TimeoutError as e:
            self._registrar_falha(e)
            raise

        except Exception as e:
            self._registrar_falha(e)
            raise

    def status(self) -> dict:
        """Retorna status atual do circuit."""
        return {
            "nome": self.nome,
            "estado": self.estado.value,
            "falhas_consecutivas": self.falhas_consecutivas,
            "ultima_falha": self.ultima_falha.isoformat() if self.ultima_falha else None,
            "ultimo_sucesso": self.ultimo_sucesso.isoformat() if self.ultimo_sucesso else None,
        }


class CircuitOpenError(Exception):
    """Exceção quando circuit breaker está aberto."""
    pass


# Instâncias globais para cada serviço
circuit_evolution = CircuitBreaker(
    nome="evolution",
    falhas_para_abrir=3,
    timeout_segundos=10.0,
    tempo_reset_segundos=30
)

circuit_claude = CircuitBreaker(
    nome="claude",
    falhas_para_abrir=3,
    timeout_segundos=30.0,
    tempo_reset_segundos=60
)

circuit_supabase = CircuitBreaker(
    nome="supabase",
    falhas_para_abrir=5,
    timeout_segundos=10.0,
    tempo_reset_segundos=30
)


def obter_status_circuits() -> dict:
    """Retorna status de todos os circuits."""
    return {
        "evolution": circuit_evolution.status(),
        "claude": circuit_claude.status(),
        "supabase": circuit_supabase.status(),
    }
```

### 2. Integrar com serviços

```python
# Atualizar app/services/llm.py

from app.services.circuit_breaker import circuit_claude

async def gerar_resposta(mensagem: str, **kwargs) -> str:
    """Gera resposta com proteção de circuit breaker."""

    async def _chamar_claude():
        # Código existente de chamada ao Claude
        response = await client.messages.create(...)
        return response.content[0].text

    async def _fallback_claude():
        # Mensagem genérica quando Claude está indisponível
        return "Oi! To com um probleminha aqui, me manda msg de novo daqui a pouco? 😅"

    return await circuit_claude.executar(
        _chamar_claude,
        fallback=_fallback_claude
    )
```

```python
# Atualizar app/services/whatsapp.py

from app.services.circuit_breaker import circuit_evolution

async def enviar_whatsapp(telefone: str, texto: str) -> bool:
    """Envia mensagem com proteção de circuit breaker."""

    async def _enviar():
        return await evolution.enviar_texto(telefone, texto)

    # Sem fallback - se Evolution falhar, não podemos enviar
    return await circuit_evolution.executar(_enviar)
```

### 3. Criar endpoint de status

```python
# app/api/routes/health.py

from app.services.circuit_breaker import obter_status_circuits

@router.get("/health/circuits")
async def circuit_status():
    """Retorna status dos circuit breakers."""
    return obter_status_circuits()
```

### 4. Criar testes

```python
# tests/test_circuit_breaker.py

import pytest
from app.services.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_circuit_abre_apos_falhas(self):
        cb = CircuitBreaker(nome="test", falhas_para_abrir=3)

        async def funcao_falha():
            raise Exception("Erro simulado")

        # 3 falhas devem abrir o circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_usa_fallback_quando_aberto(self):
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1)

        async def funcao_falha():
            raise Exception("Erro")

        async def fallback():
            return "fallback"

        # Primeira falha abre o circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Segunda chamada usa fallback
        resultado = await cb.executar(funcao_falha, fallback=fallback)
        assert resultado == "fallback"

    @pytest.mark.asyncio
    async def test_circuit_recupera(self):
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1, tempo_reset_segundos=0)

        async def funcao_falha():
            raise Exception("Erro")

        async def funcao_sucesso():
            return "ok"

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Forçar half-open (tempo_reset=0)
        cb._verificar_transicao_half_open()

        # Sucesso deve fechar
        resultado = await cb.executar(funcao_sucesso)
        assert resultado == "ok"
        assert cb.estado == CircuitState.CLOSED
```

---

## Como Testar

```bash
# 1. Ver status dos circuits
curl http://localhost:8000/health/circuits

# 2. Parar Evolution e ver circuit abrir
docker compose stop evolution-api
# Fazer algumas requisições...
curl http://localhost:8000/health/circuits
# Estado deve ser "open"

# 3. Reiniciar e ver recuperação
docker compose start evolution-api
# Aguardar tempo_reset_segundos...
curl http://localhost:8000/health/circuits
# Estado deve voltar para "closed"
```

---

## DoD (Definition of Done)

- [x] Classe `CircuitBreaker` implementada ✅ Testado em 2025-12-07
- [x] Estados CLOSED, OPEN, HALF_OPEN funcionam ✅ Testado em 2025-12-07
- [x] Transição automática para HALF_OPEN após timeout ✅ Testado em 2025-12-07
- [x] Recuperação automática após sucesso em HALF_OPEN ✅ Testado em 2025-12-07
- [x] Integrado com Evolution API ✅ Integrado em 2025-12-07
- [x] Integrado com Claude API ✅ Integrado em 2025-12-07
- [x] Integrado com Supabase ✅ Integrado em 2025-12-07
- [x] Endpoint `/health/circuits` funcionando ✅ Testado em 2025-12-07
- [x] Fallback funciona quando circuit está aberto ✅ Testado em 2025-12-07
- [x] Testes unitários passando (14/14) ✅ 2025-12-07

---

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Circuit não abre | Falhas não estão sendo registradas | Verificar try/catch |
| Circuit não recupera | tempo_reset muito alto | Ajustar configuração |
| Todas as chamadas falham | Circuit aberto sem fallback | Adicionar fallback |

---
---

# S1.E3.3 - Opt-out Imediato

## Objetivo

> **Detectar e respeitar imediatamente quando médico pede para parar de receber mensagens.**

Opt-out é **obrigatório** por lei (LGPD) e boas práticas. Quando médico diz "para de me mandar mensagem", devemos:
1. Parar imediatamente
2. Confirmar que paramos
3. Nunca mais enviar proativamente

**Resultado esperado:** Médico que pede opt-out nunca mais recebe mensagens proativas.

---

## Contexto

Frases comuns de opt-out:
- "Para de me mandar mensagem"
- "Não quero mais receber"
- "Me remove dessa lista"
- "Sai fora"
- "Não me mande mais nada"
- "STOP"

Ações necessárias:
1. Detectar intenção de opt-out
2. Atualizar status do médico no banco
3. Enviar confirmação respeitosa
4. Bloquear futuros envios proativos

**Importante:** Médico pode ainda nos enviar mensagem (inbound). Só bloqueamos outbound.

---

## Responsável

**Dev**

---

## Tarefas

### 1. Criar detector de opt-out

```python
# app/services/optout.py

"""
Serviço de detecção e processamento de opt-out.
"""
import logging
import re
from typing import Tuple

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Padrões de opt-out (case insensitive)
PADROES_OPTOUT = [
    r'\bpara\b.*\bmensag',        # "para de mandar mensagem"
    r'\bnao\b.*\bquer.*\breceb',  # "não quero receber"
    r'\bremov.*\blista',          # "remove da lista"
    r'\bsai\s*fora\b',            # "sai fora"
    r'\bnao\b.*\bmand.*\bmais',   # "não me mande mais"
    r'\bpare\b',                  # "pare"
    r'\bstop\b',                  # "STOP"
    r'\bdesinscrever\b',          # "desinscrever"
    r'\bcancelar?\b.*\benvio',    # "cancelar envio"
    r'\bbloque(ar|ia)?\b',        # "bloquear"
    r'\bnao\b.*\binteress',       # "não tenho interesse"
    r'\bchega\b',                 # "chega"
]


def detectar_optout(texto: str) -> Tuple[bool, str]:
    """
    Detecta se mensagem indica desejo de opt-out.

    Args:
        texto: Texto da mensagem

    Returns:
        (is_optout, padrao_detectado)
    """
    if not texto:
        return False, ""

    texto_lower = texto.lower()
    # Remover acentos para matching mais robusto
    texto_normalizado = (
        texto_lower
        .replace('ã', 'a').replace('á', 'a').replace('â', 'a')
        .replace('é', 'e').replace('ê', 'e')
        .replace('í', 'i')
        .replace('ó', 'o').replace('ô', 'o')
        .replace('ú', 'u')
        .replace('ç', 'c')
    )

    for padrao in PADROES_OPTOUT:
        if re.search(padrao, texto_normalizado):
            logger.info(f"Opt-out detectado: padrão '{padrao}' em '{texto[:50]}'")
            return True, padrao

    return False, ""


async def processar_optout(cliente_id: str, telefone: str) -> bool:
    """
    Processa opt-out: atualiza banco e prepara confirmação.

    Args:
        cliente_id: ID do médico
        telefone: Telefone do médico

    Returns:
        True se processado com sucesso
    """
    try:
        # Atualizar status do médico
        response = (
            supabase.table("clientes")
            .update({
                "opted_out": True,
                "opted_out_at": "now()",
                "stage_jornada": "optout",
            })
            .eq("id", cliente_id)
            .execute()
        )

        logger.info(f"Opt-out processado para cliente {cliente_id}")
        return True

    except Exception as e:
        logger.error(f"Erro ao processar opt-out: {e}")
        return False


async def verificar_opted_out(cliente_id: str) -> bool:
    """
    Verifica se cliente fez opt-out.

    Args:
        cliente_id: ID do médico

    Returns:
        True se fez opt-out
    """
    try:
        response = (
            supabase.table("clientes")
            .select("opted_out")
            .eq("id", cliente_id)
            .execute()
        )

        if response.data:
            return response.data[0].get("opted_out", False)
        return False

    except Exception as e:
        logger.error(f"Erro ao verificar opt-out: {e}")
        return False


MENSAGEM_CONFIRMACAO_OPTOUT = """Entendi! Removido da lista ✓

Não vou mais te enviar mensagens.

Se mudar de ideia, é só me chamar aqui! 👋"""


async def pode_enviar_proativo(cliente_id: str) -> Tuple[bool, str]:
    """
    Verifica se pode enviar mensagem proativa para cliente.

    Args:
        cliente_id: ID do médico

    Returns:
        (pode_enviar, motivo)
    """
    if await verificar_opted_out(cliente_id):
        return False, "Cliente fez opt-out"

    return True, "OK"
```

### 2. Integrar no fluxo de processamento

```python
# Atualizar app/api/routes/webhook.py

from app.services.optout import detectar_optout, processar_optout, MENSAGEM_CONFIRMACAO_OPTOUT

async def processar_mensagem(data: dict):
    # ... código existente até ter mensagem parseada ...

    # NOVO: Verificar opt-out ANTES de qualquer processamento
    is_optout, _ = detectar_optout(mensagem.texto)

    if is_optout:
        logger.info(f"Opt-out detectado de {mensagem.telefone}")

        # Buscar/criar médico para ter o ID
        medico = await buscar_ou_criar_medico(mensagem.telefone)

        # Processar opt-out
        await processar_optout(medico["id"], mensagem.telefone)

        # Enviar confirmação
        await enviar_whatsapp(mensagem.telefone, MENSAGEM_CONFIRMACAO_OPTOUT)

        # Não continuar processamento normal
        return

    # ... resto do código existente ...
```

### 3. Bloquear envios proativos

```python
# Atualizar app/services/fila.py (sistema de fila de mensagens)

from app.services.optout import pode_enviar_proativo

async def processar_fila():
    """Processa mensagens na fila."""

    for item in fila:
        # Verificar opt-out antes de enviar
        pode, motivo = await pode_enviar_proativo(item.cliente_id)

        if not pode:
            logger.info(f"Mensagem bloqueada para {item.cliente_id}: {motivo}")
            await marcar_como_cancelada(item.id, motivo)
            continue

        # ... resto do envio ...
```

### 4. Adicionar coluna no banco (se não existir)

```sql
-- Adicionar via migration
ALTER TABLE clientes
ADD COLUMN IF NOT EXISTS opted_out BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS opted_out_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_clientes_opted_out
ON clientes(opted_out) WHERE opted_out = TRUE;
```

### 5. Criar testes

```python
# tests/test_optout.py

import pytest
from app.services.optout import detectar_optout


class TestDetectarOptout:
    def test_detecta_para_de_mandar(self):
        assert detectar_optout("Para de me mandar mensagem")[0] == True

    def test_detecta_nao_quero(self):
        assert detectar_optout("não quero mais receber isso")[0] == True

    def test_detecta_stop(self):
        assert detectar_optout("STOP")[0] == True

    def test_detecta_remove_lista(self):
        assert detectar_optout("me remove dessa lista por favor")[0] == True

    def test_nao_detecta_mensagem_normal(self):
        assert detectar_optout("Oi, tudo bem?")[0] == False

    def test_nao_detecta_interesse(self):
        assert detectar_optout("Tenho interesse em plantão")[0] == False

    def test_nao_detecta_parar_de_trabalhar(self):
        # "Parar" em contexto diferente não é opt-out
        assert detectar_optout("Quando vou parar de trabalhar?")[0] == False


class TestProcessarOptout:
    @pytest.mark.asyncio
    async def test_processa_optout(self):
        # Criar médico de teste
        # Processar opt-out
        # Verificar que opted_out = True
        pass

    @pytest.mark.asyncio
    async def test_bloqueia_envio_apos_optout(self):
        # Cliente com opt-out não pode receber proativo
        pass
```

---

## Como Testar

```bash
# 1. Enviar mensagem de opt-out
# Via WhatsApp, enviar: "Para de me mandar mensagem"

# 2. Verificar resposta de confirmação chegou

# 3. Verificar no banco
# SELECT opted_out, opted_out_at FROM clientes WHERE telefone = 'xxx'

# 4. Tentar envio proativo (deve ser bloqueado)
curl -X POST http://localhost:8000/test/enviar-proativo \
  -H "Content-Type: application/json" \
  -d '{"cliente_id": "xxx"}'
# Resposta deve indicar bloqueio
```

---

## DoD (Definition of Done)

- [x] Padrões de opt-out definidos e testados ✅ Testado em 2025-12-07
- [x] `detectar_optout()` funciona com variações comuns ✅ Testado em 2025-12-07
- [x] `processar_optout()` atualiza banco ✅ Testado em 2025-12-07
- [x] Mensagem de confirmação é enviada ✅ Testado em 2025-12-07
- [x] `pode_enviar_proativo()` bloqueia envios ✅ Testado em 2025-12-07
- [x] Coluna `opted_out` existe no banco ✅ (já existe no schema)
- [x] Integrado no webhook de mensagens ✅ Integrado em 2025-12-07
- [ ] Integrado no sistema de fila (pendente - fila não implementada ainda)
- [x] Testes unitários passando (27 total) ✅ 2025-12-07
- [ ] 5 cenários de opt-out testados manualmente (pendente)

---

## Casos de Teste

| Mensagem | Esperado |
|----------|----------|
| "Para de me mandar mensagem" | Opt-out ✓ |
| "Não quero mais receber" | Opt-out ✓ |
| "STOP" | Opt-out ✓ |
| "Me remove da lista" | Opt-out ✓ |
| "Sai fora" | Opt-out ✓ |
| "Oi, tudo bem?" | Não é opt-out |
| "Para quando é o plantão?" | Não é opt-out |
| "Vou parar de trabalhar amanhã" | Não é opt-out |

---

## Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| Opt-out não detectado | Padrão não coberto | Adicionar novo padrão |
| Falso positivo | Padrão muito amplo | Refinar regex |
| Médico continua recebendo | Fila não verifica opt-out | Integrar verificação |
