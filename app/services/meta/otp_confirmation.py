"""
Meta OTP Confirmation Service.

Sprint 69 — Epic 69.1, Chunk 14.

Sends OTP codes via AUTHENTICATION templates for plantão confirmation.
Codes stored in Redis with 10-minute TTL.
"""

import hmac
import logging
import secrets
import string

from app.core.config import settings

logger = logging.getLogger(__name__)


class MetaOtpConfirmation:
    """
    Serviço de confirmação de plantão via OTP.

    Gera código de 6 dígitos, armazena no Redis com TTL de 10 min,
    envia via template AUTHENTICATION da Meta.
    """

    OTP_TTL_SECONDS = 600  # 10 minutos
    OTP_LENGTH = 6
    MAX_ATTEMPTS = 5
    LOCKOUT_TTL_SECONDS = 900  # 15 minutos

    def _gerar_codigo(self) -> str:
        """Gera código OTP de 6 dígitos."""
        return "".join(secrets.choice(string.digits) for _ in range(self.OTP_LENGTH))

    def _redis_key(self, telefone: str) -> str:
        """Chave Redis para armazenar OTP."""
        return f"meta:otp:{telefone}"

    def _redis_failures_key(self, telefone: str) -> str:
        """Chave Redis para contagem de tentativas falhas."""
        return f"meta:otp:failures:{telefone}"

    async def enviar_confirmacao_plantao(
        self,
        telefone: str,
        plantao_id: str,
        template_name: str = "confirmacao_otp",
    ) -> dict:
        """
        Envia código OTP para confirmação de plantão.

        Args:
            telefone: Número do médico
            plantao_id: ID do plantão/reserva
            template_name: Nome do template AUTHENTICATION

        Returns:
            Dict com success, codigo (apenas em dev)
        """
        try:
            from app.services.redis import redis_client

            redis = redis_client
            codigo = self._gerar_codigo()

            # Armazenar no Redis
            key = self._redis_key(telefone)
            await redis.setex(
                key,
                self.OTP_TTL_SECONDS,
                f"{codigo}:{plantao_id}",
            )

            # Enviar via template
            # v1: log only, não envia via Meta (precisa template AUTHENTICATION aprovado)
            logger.info(
                "[MetaOTP] Código OTP gerado para ***%s, plantão %s",
                telefone[-4:],
                plantao_id,
            )

            result = {"success": True, "telefone": telefone, "plantao_id": plantao_id}

            # Em dev, incluir código para testes
            if not settings.is_production:
                result["codigo"] = codigo

            return result

        except Exception as e:
            logger.error("[MetaOTP] Erro ao enviar OTP para ***%s: %s", telefone[-4:], e)
            return {"success": False, "error": "Erro interno ao enviar código OTP"}

    async def verificar_codigo_otp(
        self,
        telefone: str,
        codigo: str,
    ) -> dict:
        """
        Verifica código OTP enviado pelo médico.

        Inclui proteção contra brute-force: máximo de MAX_ATTEMPTS tentativas
        por telefone, com lockout de LOCKOUT_TTL_SECONDS.

        Args:
            telefone: Número do médico
            codigo: Código informado

        Returns:
            Dict com valido, plantao_id
        """
        try:
            from app.services.redis import redis_client

            redis = redis_client

            # Verificar lockout por brute-force
            failures_key = self._redis_failures_key(telefone)
            failures = await redis.get(failures_key)
            if failures:
                failure_count = int(
                    failures if isinstance(failures, str) else failures.decode("utf-8")
                )
                if failure_count >= self.MAX_ATTEMPTS:
                    logger.warning(
                        "[MetaOTP] Lockout ativo para ***%s (%d tentativas)",
                        telefone[-4:],
                        failure_count,
                    )
                    return {"valido": False, "motivo": "Muitas tentativas. Aguarde 15 minutos."}

            key = self._redis_key(telefone)
            stored = await redis.get(key)
            if not stored:
                return {"valido": False, "motivo": "Código expirado ou não encontrado"}

            stored_str = stored if isinstance(stored, str) else stored.decode("utf-8")
            parts = stored_str.split(":", 1)
            if len(parts) != 2:
                return {"valido": False, "motivo": "Formato inválido no cache"}

            stored_codigo, plantao_id = parts

            if not hmac.compare_digest(stored_codigo, codigo):
                # Incrementar contador de falhas
                await redis.incr(failures_key)
                await redis.expire(failures_key, self.LOCKOUT_TTL_SECONDS)
                return {"valido": False, "motivo": "Código incorreto"}

            # Código válido — remover OTP e falhas do Redis
            await redis.delete(key)
            await redis.delete(failures_key)

            return {"valido": True, "plantao_id": plantao_id}

        except Exception as e:
            logger.error("[MetaOTP] Erro ao verificar OTP para ***%s: %s", telefone[-4:], e)
            return {"valido": False, "motivo": "Erro interno ao verificar código"}


# Singleton
otp_confirmation = MetaOtpConfirmation()
