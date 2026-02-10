"""
Circuit Breaker por Chip.

Sprint 36 - E09: Isolamento de falhas por chip.

Cada chip tem seu próprio circuit breaker para que falhas em um
não afetem os outros.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal, chamadas passam
    OPEN = "open"  # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação


class ChipCircuitOpenError(Exception):
    """Exceção quando circuit breaker do chip está aberto."""

    def __init__(self, chip_id: str, telefone: str = ""):
        self.chip_id = chip_id
        self.telefone = telefone
        super().__init__(f"Circuit breaker do chip {telefone or chip_id[:8]} está aberto")


@dataclass
class ChipCircuit:
    """Circuit breaker para um chip específico."""

    chip_id: str
    telefone: str = ""
    falhas_para_abrir: int = 3  # Menos tolerante que global
    tempo_reset_segundos: int = 300  # 5 minutos

    # Estado interno
    estado: CircuitState = field(default=CircuitState.CLOSED)
    falhas_consecutivas: int = field(default=0)
    ultima_falha: Optional[datetime] = field(default=None)
    ultimo_sucesso: Optional[datetime] = field(default=None)
    ultimo_erro_codigo: Optional[int] = field(default=None)
    ultimo_erro_msg: Optional[str] = field(default=None)

    def _verificar_transicao_half_open(self) -> bool:
        """Verifica se deve transicionar para half-open."""
        if self.estado != CircuitState.OPEN:
            return False

        if self.ultima_falha is None:
            return False

        tempo_desde_falha = datetime.now(timezone.utc) - self.ultima_falha
        if tempo_desde_falha.total_seconds() >= self.tempo_reset_segundos:
            logger.info(
                f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: "
                f"OPEN -> HALF_OPEN após {self.tempo_reset_segundos}s"
            )
            self.estado = CircuitState.HALF_OPEN
            return True

        return False

    def registrar_sucesso(self) -> None:
        """Registra uma chamada bem-sucedida."""
        self.falhas_consecutivas = 0
        self.ultimo_sucesso = datetime.now(timezone.utc)

        if self.estado == CircuitState.HALF_OPEN:
            logger.info(
                f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: "
                f"HALF_OPEN -> CLOSED (recuperado)"
            )
            self.estado = CircuitState.CLOSED

    def registrar_falha(
        self,
        error_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Registra uma falha."""
        self.falhas_consecutivas += 1
        self.ultima_falha = datetime.now(timezone.utc)
        self.ultimo_erro_codigo = error_code
        self.ultimo_erro_msg = error_message

        logger.warning(
            f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: "
            f"falha {self.falhas_consecutivas}/{self.falhas_para_abrir} "
            f"- code={error_code}"
        )

        if self.estado == CircuitState.HALF_OPEN:
            logger.info(
                f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: "
                f"HALF_OPEN -> OPEN (falha na recuperação)"
            )
            self.estado = CircuitState.OPEN

        elif self.falhas_consecutivas >= self.falhas_para_abrir:
            logger.warning(
                f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: CLOSED -> OPEN (muitas falhas)"
            )
            self.estado = CircuitState.OPEN

    def pode_executar(self) -> bool:
        """Verifica se pode executar chamada."""
        # Verificar transição para half-open
        self._verificar_transicao_half_open()

        return self.estado != CircuitState.OPEN

    def status(self) -> dict:
        """Retorna status atual do circuit."""
        return {
            "chip_id": self.chip_id,
            "telefone": self.telefone,
            "estado": self.estado.value,
            "falhas_consecutivas": self.falhas_consecutivas,
            "ultima_falha": self.ultima_falha.isoformat() if self.ultima_falha else None,
            "ultimo_sucesso": self.ultimo_sucesso.isoformat() if self.ultimo_sucesso else None,
            "ultimo_erro_codigo": self.ultimo_erro_codigo,
        }

    def reset(self) -> None:
        """Reseta o circuit breaker manualmente."""
        self.estado = CircuitState.CLOSED
        self.falhas_consecutivas = 0
        logger.info(f"[ChipCircuit] {self.telefone or self.chip_id[:8]}: reset manual para CLOSED")


class ChipCircuitBreaker:
    """
    Gerenciador de circuit breakers por chip.

    Sprint 36 - E09: Cada chip tem seu próprio circuit breaker.
    """

    _circuits: Dict[str, ChipCircuit] = {}

    @classmethod
    def get_circuit(cls, chip_id: str, telefone: str = "") -> ChipCircuit:
        """
        Obtém ou cria circuit breaker para um chip.

        Args:
            chip_id: ID do chip
            telefone: Telefone do chip (para logs)

        Returns:
            ChipCircuit para o chip
        """
        if chip_id not in cls._circuits:
            cls._circuits[chip_id] = ChipCircuit(
                chip_id=chip_id,
                telefone=telefone,
                falhas_para_abrir=3,  # 3 falhas consecutivas
                tempo_reset_segundos=300,  # 5 minutos
            )
        elif telefone and not cls._circuits[chip_id].telefone:
            # Atualizar telefone se não tinha
            cls._circuits[chip_id].telefone = telefone

        return cls._circuits[chip_id]

    @classmethod
    def registrar_sucesso(cls, chip_id: str) -> None:
        """Registra sucesso no circuit do chip."""
        circuit = cls.get_circuit(chip_id)
        circuit.registrar_sucesso()

    @classmethod
    def registrar_falha(
        cls,
        chip_id: str,
        error_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Registra falha no circuit do chip."""
        circuit = cls.get_circuit(chip_id)
        circuit.registrar_falha(error_code, error_message)

    @classmethod
    def pode_usar_chip(cls, chip_id: str) -> bool:
        """Verifica se chip pode ser usado (circuit não está OPEN)."""
        circuit = cls.get_circuit(chip_id)
        return circuit.pode_executar()

    @classmethod
    def obter_status_todos(cls) -> Dict[str, dict]:
        """Retorna status de todos os circuits."""
        return {chip_id: circuit.status() for chip_id, circuit in cls._circuits.items()}

    @classmethod
    def obter_chips_com_circuit_aberto(cls) -> list:
        """Retorna lista de chip_ids com circuit aberto."""
        return [
            chip_id
            for chip_id, circuit in cls._circuits.items()
            if circuit.estado == CircuitState.OPEN
        ]

    @classmethod
    def reset_chip(cls, chip_id: str) -> bool:
        """Reseta circuit de um chip específico."""
        if chip_id in cls._circuits:
            cls._circuits[chip_id].reset()
            return True
        return False

    @classmethod
    def reset_todos(cls) -> int:
        """Reseta todos os circuits."""
        count = 0
        for circuit in cls._circuits.values():
            circuit.reset()
            count += 1
        return count


# Singleton para acesso global
chip_circuit_breaker = ChipCircuitBreaker()
