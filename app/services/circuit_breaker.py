"""
Circuit breaker para serviços externos.
Previne falhas em cascata e permite recuperação automática.
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"        # Normal, chamadas passam
    OPEN = "open"            # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação


class CircuitOpenError(Exception):
    """Exceção quando circuit breaker está aberto."""
    pass


@dataclass
class CircuitBreaker:
    """
    Circuit breaker para um serviço específico.

    Estados:
    - CLOSED: Normal, todas as chamadas passam
    - OPEN: Muitas falhas, bloqueia chamadas
    - HALF_OPEN: Testando se serviço recuperou
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

    def reset(self):
        """Reseta o circuit breaker manualmente."""
        self.estado = CircuitState.CLOSED
        self.falhas_consecutivas = 0
        logger.info(f"Circuit {self.nome}: reset manual para CLOSED")


# Instâncias globais para cada serviço
circuit_evolution = CircuitBreaker(
    nome="evolution",
    falhas_para_abrir=5,          # Aumentado: 5 falhas (era 3)
    timeout_segundos=30.0,        # Aumentado: 30s (era 10s)
    tempo_reset_segundos=15       # Reduzido: 15s (era 30s) - recupera mais rápido
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
