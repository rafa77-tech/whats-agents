"""
Distributed Lock - Lock distribuído via Redis.

Sprint 44 T03.1

Implementa lock distribuído para evitar que múltiplos processos/workers
executem operações críticas simultaneamente.

Uso:
    async with DistributedLock("meu_recurso"):
        # Código protegido pelo lock
        await operacao_critica()
"""
import uuid
import logging
from typing import Optional

from app.services.redis import redis_client

logger = logging.getLogger(__name__)


class LockNotAcquiredError(Exception):
    """Raised when lock cannot be acquired."""
    pass


class DistributedLock:
    """
    Lock distribuído usando Redis.

    Implementa o padrão Redlock simplificado:
    - SET NX (set if not exists) para adquirir
    - Lua script para liberar de forma segura

    Attributes:
        key: Nome do recurso sendo bloqueado
        timeout: TTL do lock em segundos (previne locks órfãos)
        token: Token único para identificar este lock holder
    """

    def __init__(
        self,
        key: str,
        timeout: int = 300,
        blocking: bool = False,
        blocking_timeout: int = 30,
    ):
        """
        Args:
            key: Nome do recurso a bloquear
            timeout: TTL do lock em segundos (default 5 min)
            blocking: Se True, espera até conseguir o lock
            blocking_timeout: Tempo máximo de espera se blocking=True
        """
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.token = str(uuid.uuid4())
        self._acquired = False

    async def acquire(self) -> bool:
        """
        Tenta adquirir o lock.

        Returns:
            True se adquiriu, False se não conseguiu
        """
        import asyncio

        if self.blocking:
            # Tentar repetidamente até timeout
            deadline = asyncio.get_event_loop().time() + self.blocking_timeout
            while asyncio.get_event_loop().time() < deadline:
                if await self._try_acquire():
                    return True
                await asyncio.sleep(0.1)  # 100ms entre tentativas
            return False
        else:
            return await self._try_acquire()

    async def _try_acquire(self) -> bool:
        """Tenta adquirir o lock uma vez."""
        try:
            result = await redis_client.set(
                self.key,
                self.token,
                nx=True,  # SET if Not eXists
                ex=self.timeout
            )
            self._acquired = result is not None
            if self._acquired:
                logger.debug(f"[DistributedLock] Lock adquirido: {self.key}")
            return self._acquired
        except Exception as e:
            logger.error(f"[DistributedLock] Erro ao adquirir lock: {e}")
            return False

    async def release(self) -> bool:
        """
        Libera o lock de forma segura.

        Usa Lua script para garantir que só libera se ainda for o dono.

        Returns:
            True se liberou, False se já tinha expirado ou não era dono
        """
        if not self._acquired:
            return True

        # Lua script: só deleta se o valor ainda for nosso token
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await redis_client.eval(lua_script, 1, self.key, self.token)
            released = result == 1
            if released:
                logger.debug(f"[DistributedLock] Lock liberado: {self.key}")
            else:
                logger.warning(f"[DistributedLock] Lock expirou antes de liberar: {self.key}")
            self._acquired = False
            return released
        except Exception as e:
            logger.error(f"[DistributedLock] Erro ao liberar lock: {e}")
            self._acquired = False
            return False

    async def extend(self, additional_time: int = None) -> bool:
        """
        Estende o TTL do lock se ainda for dono.

        Args:
            additional_time: Segundos adicionais (default: timeout original)

        Returns:
            True se estendeu, False se não é mais dono
        """
        if not self._acquired:
            return False

        ttl = additional_time or self.timeout

        # Lua script: só estende se ainda for dono
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        try:
            result = await redis_client.eval(lua_script, 1, self.key, self.token, ttl)
            return result == 1
        except Exception as e:
            logger.error(f"[DistributedLock] Erro ao estender lock: {e}")
            return False

    async def __aenter__(self):
        """Context manager: adquire lock."""
        acquired = await self.acquire()
        if not acquired:
            raise LockNotAcquiredError(f"Could not acquire lock: {self.key}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager: libera lock."""
        await self.release()
        return False  # Não suprime exceções


async def with_lock(
    key: str,
    timeout: int = 300,
    blocking: bool = False,
    blocking_timeout: int = 30,
) -> DistributedLock:
    """
    Factory function para criar e adquirir lock.

    Uso:
        lock = await with_lock("meu_recurso")
        if lock._acquired:
            try:
                await operacao()
            finally:
                await lock.release()
    """
    lock = DistributedLock(key, timeout, blocking, blocking_timeout)
    await lock.acquire()
    return lock
