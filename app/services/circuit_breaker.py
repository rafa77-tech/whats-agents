"""
Circuit breaker para serviços externos.
Previne falhas em cascata e permite recuperação automática.

Sprint 36 - T02.1: Log de transições de estado
Sprint 36 - T02.2: Backoff exponencial no reset
Sprint 36 - T02.3: Diferenciar tipos de erro
Sprint 44 - T06.5: Distributed circuit breaker via Redis
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Sprint 44 T06.5: Lazy import do Redis
def _get_redis():
    """Lazy import para evitar circular import."""
    from app.services.redis import redis_client

    return redis_client


def _get_supabase():
    """Lazy import para evitar circular import com supabase.py."""
    from app.services.supabase import supabase

    return supabase


class CircuitState(Enum):
    CLOSED = "closed"  # Normal, chamadas passam
    OPEN = "open"  # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação


class ErrorType(Enum):
    """Sprint 36 - T02.3: Tipos de erro para diferenciação."""

    TIMEOUT = "timeout"  # Não conta para abrir circuit
    CLIENT_ERROR = "client_4xx"  # Conta - erro do cliente
    SERVER_ERROR = "server_5xx"  # Conta - erro do servidor
    NETWORK = "network"  # Conta - erro de rede
    UNKNOWN = "unknown"  # Conta - erro desconhecido


class CircuitOpenError(Exception):
    """Exceção quando circuit breaker está aberto."""

    pass


def _classificar_erro(erro: Exception) -> ErrorType:
    """Sprint 36 - T02.3: Classifica o tipo de erro."""
    erro_str = str(erro).lower()

    if isinstance(erro, asyncio.TimeoutError):
        return ErrorType.TIMEOUT

    # Verificar códigos HTTP
    if "400" in erro_str or "401" in erro_str or "403" in erro_str or "404" in erro_str:
        return ErrorType.CLIENT_ERROR

    if "500" in erro_str or "502" in erro_str or "503" in erro_str or "504" in erro_str:
        return ErrorType.SERVER_ERROR

    if "connection" in erro_str or "network" in erro_str or "refused" in erro_str:
        return ErrorType.NETWORK

    return ErrorType.UNKNOWN


@dataclass
class CircuitBreaker:
    """
    Circuit breaker para um serviço específico.

    Estados:
    - CLOSED: Normal, todas as chamadas passam
    - OPEN: Muitas falhas, bloqueia chamadas
    - HALF_OPEN: Testando se serviço recuperou

    Sprint 36:
    - T02.1: Registra transições em tabela
    - T02.2: Backoff exponencial no tempo de reset
    - T02.3: Timeout não conta como falha

    Sprint 44 T01.3: Thread-safe com asyncio.Lock
    """

    nome: str
    falhas_para_abrir: int = 5  # Falhas consecutivas para abrir
    timeout_segundos: float = 30.0  # Timeout para chamadas
    tempo_reset_inicial: int = 60  # Primeiro reset (segundos)
    tempo_reset_max: int = 600  # Máximo 10 minutos
    multiplicador_backoff: float = 2.0  # Dobra a cada falha no half-open

    # Estado interno
    estado: CircuitState = field(default=CircuitState.CLOSED)
    falhas_consecutivas: int = field(default=0)
    ultima_falha: Optional[datetime] = field(default=None)
    ultimo_sucesso: Optional[datetime] = field(default=None)
    tentativas_half_open: int = field(default=0)  # Sprint 36 - T02.2
    ultimo_erro_tipo: Optional[ErrorType] = field(default=None)

    # Retrocompatibilidade
    tempo_reset_segundos: int = field(default=60)

    # Sprint 44 T01.3: Lock para thread-safety
    _lock: asyncio.Lock = field(default=None, repr=False)

    def __post_init__(self):
        """Inicialização após dataclass."""
        # Se tempo_reset_segundos foi setado mas não tempo_reset_inicial
        if self.tempo_reset_segundos != 60:
            self.tempo_reset_inicial = self.tempo_reset_segundos
        # Sprint 44 T01.3: Inicializar lock
        if self._lock is None:
            self._lock = asyncio.Lock()

    def _calcular_tempo_reset(self) -> int:
        """Sprint 36 - T02.2: Calcula tempo de reset com backoff exponencial."""
        tempo = self.tempo_reset_inicial * (self.multiplicador_backoff**self.tentativas_half_open)
        return min(int(tempo), self.tempo_reset_max)

    def _verificar_transicao_half_open(self):
        """Verifica se deve transicionar para half-open."""
        if self.estado != CircuitState.OPEN:
            return

        if self.ultima_falha is None:
            return

        tempo_reset = self._calcular_tempo_reset()
        tempo_desde_falha = datetime.now(timezone.utc) - self.ultima_falha

        if tempo_desde_falha.total_seconds() >= tempo_reset:
            self._transicionar(CircuitState.HALF_OPEN, f"timeout_reset_{tempo_reset}s")

    def _transicionar(self, novo_estado: CircuitState, motivo: str):
        """Sprint 36 - T02.1: Transiciona e registra no banco."""
        estado_anterior = self.estado

        if estado_anterior == novo_estado:
            return

        self.estado = novo_estado

        logger.info(
            f"Circuit {self.nome}: {estado_anterior.value} -> {novo_estado.value} ({motivo})"
        )

        # Registrar transição no banco (async em background)
        try:
            _get_supabase().table("circuit_transitions").insert(
                {
                    "circuit_name": self.nome,
                    "from_state": estado_anterior.value,
                    "to_state": novo_estado.value,
                    "reason": motivo,
                    "falhas_consecutivas": self.falhas_consecutivas,
                    "tentativas_half_open": self.tentativas_half_open,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as e:
            # Não falhar se não conseguir registrar
            logger.debug(f"[CircuitBreaker] Erro ao registrar transição: {e}")

    async def _registrar_sucesso(self):
        """
        Registra uma chamada bem-sucedida.

        Sprint 44 T01.3: Thread-safe com asyncio.Lock.
        """
        async with self._lock:
            self.falhas_consecutivas = 0
            self.ultimo_sucesso = datetime.now(timezone.utc)

            if self.estado == CircuitState.HALF_OPEN:
                # Sprint 36 - T02.2: Reset do backoff após recuperação
                self.tentativas_half_open = 0
                self._transicionar(CircuitState.CLOSED, "recuperado")

    async def _registrar_falha(self, erro: Exception, tipo_erro: ErrorType):
        """
        Registra uma falha.

        Sprint 44 T01.3: Thread-safe com asyncio.Lock.
        """
        async with self._lock:
            self.ultima_falha = datetime.now(timezone.utc)
            self.ultimo_erro_tipo = tipo_erro

            # Sprint 36 - T02.3: Timeout não conta como falha para abrir circuit
            if tipo_erro == ErrorType.TIMEOUT:
                logger.warning(f"Circuit {self.nome}: timeout (não conta como falha) - {erro}")
                return

            self.falhas_consecutivas += 1

            logger.warning(
                f"Circuit {self.nome}: falha {self.falhas_consecutivas}/{self.falhas_para_abrir} "
                f"[{tipo_erro.value}] - {erro}"
            )

            if self.estado == CircuitState.HALF_OPEN:
                # Sprint 36 - T02.2: Incrementa backoff
                self.tentativas_half_open += 1
                self._transicionar(
                    CircuitState.OPEN, f"falha_half_open_tentativa_{self.tentativas_half_open}"
                )

            elif self.falhas_consecutivas >= self.falhas_para_abrir:
                self._transicionar(CircuitState.OPEN, f"muitas_falhas_{self.falhas_consecutivas}")

    async def executar(self, func: Callable, *args, fallback: Callable = None, **kwargs) -> Any:
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
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit {self.nome} está aberto")

        # Tentar executar
        try:
            resultado = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout_segundos)
            # Sprint 44 T01.3: Métodos agora são async
            await self._registrar_sucesso()
            return resultado

        except asyncio.TimeoutError as e:
            tipo_erro = _classificar_erro(e)
            await self._registrar_falha(e, tipo_erro)
            raise

        except Exception as e:
            tipo_erro = _classificar_erro(e)
            await self._registrar_falha(e, tipo_erro)
            raise

    def status(self) -> dict:
        """Retorna status atual do circuit."""
        return {
            "nome": self.nome,
            "estado": self.estado.value,
            "falhas_consecutivas": self.falhas_consecutivas,
            "ultima_falha": self.ultima_falha.isoformat() if self.ultima_falha else None,
            "ultimo_sucesso": self.ultimo_sucesso.isoformat() if self.ultimo_sucesso else None,
            "tentativas_half_open": self.tentativas_half_open,
            "tempo_reset_atual": self._calcular_tempo_reset(),
            "ultimo_erro_tipo": self.ultimo_erro_tipo.value if self.ultimo_erro_tipo else None,
        }

    def reset(self):
        """Reseta o circuit breaker manualmente."""
        estado_anterior = self.estado
        self.estado = CircuitState.CLOSED
        self.falhas_consecutivas = 0
        self.tentativas_half_open = 0
        logger.info(f"Circuit {self.nome}: reset manual para CLOSED")

        # Registrar reset
        try:
            _get_supabase().table("circuit_transitions").insert(
                {
                    "circuit_name": self.nome,
                    "from_state": estado_anterior.value,
                    "to_state": "closed",
                    "reason": "reset_manual",
                    "falhas_consecutivas": 0,
                    "tentativas_half_open": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception:
            pass


class DistributedCircuitBreaker:
    """
    Sprint 44 T06.5: Circuit breaker com estado distribuído via Redis.

    Permite que múltiplas instâncias da aplicação compartilhem o estado
    do circuit breaker, evitando que uma instância fique em estado
    diferente das outras.

    Estados são armazenados em Redis com estrutura:
    - circuit:{nome}:state -> estado atual
    - circuit:{nome}:failures -> contagem de falhas
    - circuit:{nome}:last_failure -> timestamp última falha
    - circuit:{nome}:half_open_attempts -> tentativas em half-open
    """

    def __init__(
        self,
        nome: str,
        falhas_para_abrir: int = 5,
        timeout_segundos: float = 30.0,
        tempo_reset_inicial: int = 60,
        tempo_reset_max: int = 600,
        multiplicador_backoff: float = 2.0,
    ):
        self.nome = nome
        self.falhas_para_abrir = falhas_para_abrir
        self.timeout_segundos = timeout_segundos
        self.tempo_reset_inicial = tempo_reset_inicial
        self.tempo_reset_max = tempo_reset_max
        self.multiplicador_backoff = multiplicador_backoff
        self.tempo_reset_segundos = tempo_reset_inicial  # Retrocompatibilidade

        self._redis_prefix = f"circuit:{nome}"
        self._local_lock = asyncio.Lock()
        self._redis_available = True  # Fallback para local se Redis falhar

        # Estado local (fallback)
        self._local_state = CircuitState.CLOSED
        self._local_failures = 0
        self._local_last_failure = None
        self._local_half_open_attempts = 0

    @property
    def estado(self) -> CircuitState:
        """Obtém estado atual (tenta Redis, fallback local)."""
        try:
            _get_redis()
            # Operação síncrona - usar em contextos onde async não é possível
            # Para uso async, usar _get_state_async
            return self._local_state
        except Exception:
            return self._local_state

    async def _get_state_async(self) -> CircuitState:
        """Obtém estado do Redis de forma assíncrona."""
        try:
            redis = _get_redis()
            state_str = await redis.get(f"{self._redis_prefix}:state")
            if state_str:
                return CircuitState(
                    state_str.decode() if isinstance(state_str, bytes) else state_str
                )
            return CircuitState.CLOSED
        except Exception as e:
            logger.warning(f"[DistributedCB] Erro ao ler estado Redis: {e}")
            self._redis_available = False
            return self._local_state

    async def _set_state_async(self, state: CircuitState, motivo: str) -> bool:
        """Define estado no Redis de forma assíncrona."""
        try:
            redis = _get_redis()
            estado_anterior = await self._get_state_async()

            if estado_anterior == state:
                return True

            await redis.set(f"{self._redis_prefix}:state", state.value, ex=86400)  # TTL 24h

            logger.info(
                f"Circuit {self.nome}: {estado_anterior.value} -> {state.value} "
                f"({motivo}) [distributed]"
            )

            # Registrar transição no banco
            self._registrar_transicao_db(estado_anterior, state, motivo)

            return True
        except Exception as e:
            logger.warning(f"[DistributedCB] Erro ao definir estado Redis: {e}")
            self._redis_available = False
            self._local_state = state
            return False

    async def _get_failures_async(self) -> int:
        """Obtém contagem de falhas do Redis."""
        try:
            redis = _get_redis()
            failures = await redis.get(f"{self._redis_prefix}:failures")
            return int(failures) if failures else 0
        except Exception:
            return self._local_failures

    async def _incr_failures_async(self) -> int:
        """Incrementa falhas atomicamente no Redis."""
        try:
            redis = _get_redis()
            return await redis.incr(f"{self._redis_prefix}:failures")
        except Exception:
            self._local_failures += 1
            return self._local_failures

    async def _reset_failures_async(self) -> bool:
        """Reseta contagem de falhas."""
        try:
            redis = _get_redis()
            await redis.set(f"{self._redis_prefix}:failures", "0", ex=86400)
            self._local_failures = 0
            return True
        except Exception:
            self._local_failures = 0
            return False

    async def _get_half_open_attempts_async(self) -> int:
        """Obtém tentativas de half-open."""
        try:
            redis = _get_redis()
            attempts = await redis.get(f"{self._redis_prefix}:half_open_attempts")
            return int(attempts) if attempts else 0
        except Exception:
            return self._local_half_open_attempts

    async def _incr_half_open_attempts_async(self) -> int:
        """Incrementa tentativas de half-open."""
        try:
            redis = _get_redis()
            return await redis.incr(f"{self._redis_prefix}:half_open_attempts")
        except Exception:
            self._local_half_open_attempts += 1
            return self._local_half_open_attempts

    async def _reset_half_open_attempts_async(self) -> bool:
        """Reseta tentativas de half-open."""
        try:
            redis = _get_redis()
            await redis.set(f"{self._redis_prefix}:half_open_attempts", "0", ex=86400)
            self._local_half_open_attempts = 0
            return True
        except Exception:
            self._local_half_open_attempts = 0
            return False

    async def _set_last_failure_async(self) -> bool:
        """Define timestamp da última falha."""
        try:
            redis = _get_redis()
            now = datetime.now(timezone.utc).isoformat()
            await redis.set(f"{self._redis_prefix}:last_failure", now, ex=86400)
            self._local_last_failure = datetime.now(timezone.utc)
            return True
        except Exception:
            self._local_last_failure = datetime.now(timezone.utc)
            return False

    async def _get_last_failure_async(self) -> Optional[datetime]:
        """Obtém timestamp da última falha."""
        try:
            redis = _get_redis()
            ts = await redis.get(f"{self._redis_prefix}:last_failure")
            if ts:
                ts_str = ts.decode() if isinstance(ts, bytes) else ts
                return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            return None
        except Exception:
            return self._local_last_failure

    def _calcular_tempo_reset(self, tentativas: int = 0) -> int:
        """Calcula tempo de reset com backoff exponencial."""
        tempo = self.tempo_reset_inicial * (self.multiplicador_backoff**tentativas)
        return min(int(tempo), self.tempo_reset_max)

    async def _verificar_transicao_half_open(self):
        """Verifica se deve transicionar para half-open."""
        estado = await self._get_state_async()
        if estado != CircuitState.OPEN:
            return

        ultima_falha = await self._get_last_failure_async()
        if ultima_falha is None:
            return

        tentativas = await self._get_half_open_attempts_async()
        tempo_reset = self._calcular_tempo_reset(tentativas)
        tempo_desde_falha = datetime.now(timezone.utc) - ultima_falha

        if tempo_desde_falha.total_seconds() >= tempo_reset:
            await self._set_state_async(CircuitState.HALF_OPEN, f"timeout_reset_{tempo_reset}s")

    def _registrar_transicao_db(
        self, estado_anterior: CircuitState, novo_estado: CircuitState, motivo: str
    ):
        """Registra transição no banco de dados."""
        try:
            _get_supabase().table("circuit_transitions").insert(
                {
                    "circuit_name": self.nome,
                    "from_state": estado_anterior.value,
                    "to_state": novo_estado.value,
                    "reason": motivo,
                    "falhas_consecutivas": self._local_failures,
                    "tentativas_half_open": self._local_half_open_attempts,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as e:
            logger.debug(f"[DistributedCB] Erro ao registrar transição: {e}")

    async def _registrar_sucesso(self):
        """Registra uma chamada bem-sucedida."""
        async with self._local_lock:
            await self._reset_failures_async()

            estado = await self._get_state_async()
            if estado == CircuitState.HALF_OPEN:
                await self._reset_half_open_attempts_async()
                await self._set_state_async(CircuitState.CLOSED, "recuperado")

    async def _registrar_falha(self, erro: Exception, tipo_erro: ErrorType):
        """Registra uma falha."""
        async with self._local_lock:
            await self._set_last_failure_async()

            # Timeout não conta como falha
            if tipo_erro == ErrorType.TIMEOUT:
                logger.warning(f"Circuit {self.nome}: timeout (não conta como falha) - {erro}")
                return

            failures = await self._incr_failures_async()
            estado = await self._get_state_async()

            logger.warning(
                f"Circuit {self.nome}: falha {failures}/{self.falhas_para_abrir} "
                f"[{tipo_erro.value}] - {erro}"
            )

            if estado == CircuitState.HALF_OPEN:
                await self._incr_half_open_attempts_async()
                tentativas = await self._get_half_open_attempts_async()
                await self._set_state_async(
                    CircuitState.OPEN, f"falha_half_open_tentativa_{tentativas}"
                )

            elif failures >= self.falhas_para_abrir:
                await self._set_state_async(CircuitState.OPEN, f"muitas_falhas_{failures}")

    async def executar(self, func: Callable, *args, fallback: Callable = None, **kwargs) -> Any:
        """Executa função com proteção do circuit breaker."""
        await self._verificar_transicao_half_open()

        estado = await self._get_state_async()
        if estado == CircuitState.OPEN:
            if fallback:
                logger.debug(f"Circuit {self.nome} aberto, usando fallback")
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit {self.nome} está aberto")

        try:
            resultado = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout_segundos)
            await self._registrar_sucesso()
            return resultado

        except asyncio.TimeoutError as e:
            tipo_erro = _classificar_erro(e)
            await self._registrar_falha(e, tipo_erro)
            raise

        except Exception as e:
            tipo_erro = _classificar_erro(e)
            await self._registrar_falha(e, tipo_erro)
            raise

    async def status_async(self) -> dict:
        """Retorna status atual do circuit (async)."""
        estado = await self._get_state_async()
        failures = await self._get_failures_async()
        ultima_falha = await self._get_last_failure_async()
        tentativas = await self._get_half_open_attempts_async()

        return {
            "nome": self.nome,
            "estado": estado.value,
            "falhas_consecutivas": failures,
            "ultima_falha": ultima_falha.isoformat() if ultima_falha else None,
            "tentativas_half_open": tentativas,
            "tempo_reset_atual": self._calcular_tempo_reset(tentativas),
            "distributed": True,
        }

    def status(self) -> dict:
        """Retorna status atual (versão síncrona para retrocompatibilidade)."""
        return {
            "nome": self.nome,
            "estado": self._local_state.value,
            "falhas_consecutivas": self._local_failures,
            "ultima_falha": self._local_last_failure.isoformat()
            if self._local_last_failure
            else None,
            "tentativas_half_open": self._local_half_open_attempts,
            "tempo_reset_atual": self._calcular_tempo_reset(self._local_half_open_attempts),
            "distributed": True,
        }

    async def reset_async(self):
        """Reseta o circuit breaker manualmente (async)."""
        await self._get_state_async()
        await self._reset_failures_async()
        await self._reset_half_open_attempts_async()
        await self._set_state_async(CircuitState.CLOSED, "reset_manual")
        logger.info(f"Circuit {self.nome}: reset manual para CLOSED [distributed]")

    def reset(self):
        """Reseta o circuit breaker manualmente (sync - para retrocompatibilidade)."""
        self._local_state = CircuitState.CLOSED
        self._local_failures = 0
        self._local_half_open_attempts = 0
        logger.info(f"Circuit {self.nome}: reset manual para CLOSED [local only]")


# Instâncias globais para cada serviço
circuit_evolution = CircuitBreaker(
    nome="evolution",
    falhas_para_abrir=5,  # 5 falhas consecutivas para abrir
    timeout_segundos=30.0,  # Timeout de 30s por chamada
    tempo_reset_inicial=300,  # 5 minutos - erros WhatsApp não se resolvem rápido
    tempo_reset_max=1800,  # Máximo 30 minutos
)

circuit_claude = CircuitBreaker(
    nome="claude",
    falhas_para_abrir=3,
    timeout_segundos=30.0,
    tempo_reset_inicial=60,
    tempo_reset_max=300,
)

circuit_supabase = CircuitBreaker(
    nome="supabase",
    falhas_para_abrir=5,
    timeout_segundos=10.0,
    tempo_reset_inicial=30,
    tempo_reset_max=120,
)


# Sprint 44 T06.5: Instâncias distribuídas (para migração gradual)
# Use estas em multi-instância quando precisar de estado compartilhado
distributed_circuit_evolution = DistributedCircuitBreaker(
    nome="evolution",
    falhas_para_abrir=5,
    timeout_segundos=30.0,
    tempo_reset_inicial=300,
    tempo_reset_max=1800,
)

distributed_circuit_claude = DistributedCircuitBreaker(
    nome="claude",
    falhas_para_abrir=3,
    timeout_segundos=30.0,
    tempo_reset_inicial=60,
    tempo_reset_max=300,
)

distributed_circuit_supabase = DistributedCircuitBreaker(
    nome="supabase",
    falhas_para_abrir=5,
    timeout_segundos=10.0,
    tempo_reset_inicial=30,
    tempo_reset_max=120,
)


def obter_status_circuits() -> dict:
    """Retorna status de todos os circuits."""
    return {
        "evolution": circuit_evolution.status(),
        "claude": circuit_claude.status(),
        "supabase": circuit_supabase.status(),
    }


async def obter_historico_transicoes(circuit_name: str = None, horas: int = 24) -> list:
    """
    Sprint 36 - T02.5: Obtém histórico de transições.

    Args:
        circuit_name: Nome do circuit (opcional, todos se None)
        horas: Período em horas (default 24)

    Returns:
        Lista de transições
    """
    from datetime import timedelta

    limite = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()

    query = (
        _get_supabase()
        .table("circuit_transitions")
        .select("*")
        .gte("created_at", limite)
        .order("created_at", desc=True)
    )

    if circuit_name:
        query = query.eq("circuit_name", circuit_name)

    result = query.limit(100).execute()

    return result.data or []
