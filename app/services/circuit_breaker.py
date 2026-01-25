"""
Circuit breaker para serviços externos.
Previne falhas em cascata e permite recuperação automática.

Sprint 36 - T02.1: Log de transições de estado
Sprint 36 - T02.2: Backoff exponencial no reset
Sprint 36 - T02.3: Diferenciar tipos de erro
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _get_supabase():
    """Lazy import para evitar circular import com supabase.py."""
    from app.services.supabase import supabase
    return supabase


class CircuitState(Enum):
    CLOSED = "closed"        # Normal, chamadas passam
    OPEN = "open"            # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação


class ErrorType(Enum):
    """Sprint 36 - T02.3: Tipos de erro para diferenciação."""
    TIMEOUT = "timeout"           # Não conta para abrir circuit
    CLIENT_ERROR = "client_4xx"   # Conta - erro do cliente
    SERVER_ERROR = "server_5xx"   # Conta - erro do servidor
    NETWORK = "network"           # Conta - erro de rede
    UNKNOWN = "unknown"           # Conta - erro desconhecido


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
    """
    nome: str
    falhas_para_abrir: int = 5           # Falhas consecutivas para abrir
    timeout_segundos: float = 30.0       # Timeout para chamadas
    tempo_reset_inicial: int = 60        # Primeiro reset (segundos)
    tempo_reset_max: int = 600           # Máximo 10 minutos
    multiplicador_backoff: float = 2.0   # Dobra a cada falha no half-open

    # Estado interno
    estado: CircuitState = field(default=CircuitState.CLOSED)
    falhas_consecutivas: int = field(default=0)
    ultima_falha: Optional[datetime] = field(default=None)
    ultimo_sucesso: Optional[datetime] = field(default=None)
    tentativas_half_open: int = field(default=0)  # Sprint 36 - T02.2
    ultimo_erro_tipo: Optional[ErrorType] = field(default=None)

    # Retrocompatibilidade
    tempo_reset_segundos: int = field(default=60)

    def __post_init__(self):
        """Inicialização após dataclass."""
        # Se tempo_reset_segundos foi setado mas não tempo_reset_inicial
        if self.tempo_reset_segundos != 60:
            self.tempo_reset_inicial = self.tempo_reset_segundos

    def _calcular_tempo_reset(self) -> int:
        """Sprint 36 - T02.2: Calcula tempo de reset com backoff exponencial."""
        tempo = self.tempo_reset_inicial * (
            self.multiplicador_backoff ** self.tentativas_half_open
        )
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
            f"Circuit {self.nome}: {estado_anterior.value} -> {novo_estado.value} "
            f"({motivo})"
        )

        # Registrar transição no banco (async em background)
        try:
            _get_supabase().table("circuit_transitions").insert({
                "circuit_name": self.nome,
                "from_state": estado_anterior.value,
                "to_state": novo_estado.value,
                "reason": motivo,
                "falhas_consecutivas": self.falhas_consecutivas,
                "tentativas_half_open": self.tentativas_half_open,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            # Não falhar se não conseguir registrar
            logger.debug(f"[CircuitBreaker] Erro ao registrar transição: {e}")

    def _registrar_sucesso(self):
        """Registra uma chamada bem-sucedida."""
        self.falhas_consecutivas = 0
        self.ultimo_sucesso = datetime.now(timezone.utc)

        if self.estado == CircuitState.HALF_OPEN:
            # Sprint 36 - T02.2: Reset do backoff após recuperação
            self.tentativas_half_open = 0
            self._transicionar(CircuitState.CLOSED, "recuperado")

    def _registrar_falha(self, erro: Exception, tipo_erro: ErrorType):
        """Registra uma falha."""
        self.ultima_falha = datetime.now(timezone.utc)
        self.ultimo_erro_tipo = tipo_erro

        # Sprint 36 - T02.3: Timeout não conta como falha para abrir circuit
        if tipo_erro == ErrorType.TIMEOUT:
            logger.warning(
                f"Circuit {self.nome}: timeout (não conta como falha) - {erro}"
            )
            return

        self.falhas_consecutivas += 1

        logger.warning(
            f"Circuit {self.nome}: falha {self.falhas_consecutivas}/{self.falhas_para_abrir} "
            f"[{tipo_erro.value}] - {erro}"
        )

        if self.estado == CircuitState.HALF_OPEN:
            # Sprint 36 - T02.2: Incrementa backoff
            self.tentativas_half_open += 1
            self._transicionar(CircuitState.OPEN, f"falha_half_open_tentativa_{self.tentativas_half_open}")

        elif self.falhas_consecutivas >= self.falhas_para_abrir:
            self._transicionar(CircuitState.OPEN, f"muitas_falhas_{self.falhas_consecutivas}")

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
                if asyncio.iscoroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
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
            tipo_erro = _classificar_erro(e)
            self._registrar_falha(e, tipo_erro)
            raise

        except Exception as e:
            tipo_erro = _classificar_erro(e)
            self._registrar_falha(e, tipo_erro)
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
            _get_supabase().table("circuit_transitions").insert({
                "circuit_name": self.nome,
                "from_state": estado_anterior.value,
                "to_state": "closed",
                "reason": "reset_manual",
                "falhas_consecutivas": 0,
                "tentativas_half_open": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass


# Instâncias globais para cada serviço
circuit_evolution = CircuitBreaker(
    nome="evolution",
    falhas_para_abrir=5,          # 5 falhas consecutivas para abrir
    timeout_segundos=30.0,        # Timeout de 30s por chamada
    tempo_reset_inicial=300,      # 5 minutos - erros WhatsApp não se resolvem rápido
    tempo_reset_max=1800,         # Máximo 30 minutos
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

    query = _get_supabase().table("circuit_transitions").select("*").gte(
        "created_at", limite
    ).order("created_at", desc=True)

    if circuit_name:
        query = query.eq("circuit_name", circuit_name)

    result = query.limit(100).execute()

    return result.data or []
