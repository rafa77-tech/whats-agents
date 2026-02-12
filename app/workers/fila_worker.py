"""
Worker para processar fila de mensagens.

Sprint 23 E01 - Registra outcome detalhado para cada envio.
Sprint 36 - T01.3: Circuit breaker no fila_worker.
Sprint 44 T03.4: Idempotência via Redis SETNX.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.fila import fila_service
from app.services.rate_limiter import pode_enviar
from app.services.outbound import (
    send_outbound_message,
    criar_contexto_followup,
    criar_contexto_campanha,
)
from app.services.guardrails import SendOutcome
from app.services.circuit_breaker import circuit_evolution, CircuitState
from app.services.redis import redis_client
from app.services.conversa import buscar_ou_criar_conversa
from app.services.interacao import salvar_interacao
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Sprint 44 T03.4: TTL para lock de idempotência (5 minutos)
_IDEMPOTENCY_TTL_SEGUNDOS = 300

# Sprint 36 - T01.3: Controle de alertas
_ultimo_alerta_circuit: Optional[datetime] = None
_ALERTA_COOLDOWN_SEGUNDOS = 300  # 5 minutos entre alertas


async def _adquirir_lock_idempotencia(mensagem_id: str) -> bool:
    """
    Sprint 44 T03.4: Adquire lock de idempotência para mensagem.

    Usa Redis SETNX para garantir que apenas um worker processe
    cada mensagem, mesmo em cenário de múltiplas instâncias.

    Args:
        mensagem_id: ID da mensagem na fila

    Returns:
        True se adquiriu lock, False se já está sendo processada
    """
    key = f"fila:processing:{mensagem_id}"

    try:
        # SETNX com TTL - retorna True se setou, False se já existe
        acquired = await redis_client.set(
            key,
            "processing",
            nx=True,  # Only set if not exists
            ex=_IDEMPOTENCY_TTL_SEGUNDOS,
        )
        return bool(acquired)

    except Exception as e:
        logger.warning(f"[FilaWorker] T03.4: Erro Redis idempotência, prosseguindo: {e}")
        # Em caso de erro Redis, prossegue (fallback graceful)
        return True


async def _liberar_lock_idempotencia(mensagem_id: str) -> None:
    """
    Sprint 44 T03.4: Libera lock de idempotência após processamento.

    Args:
        mensagem_id: ID da mensagem na fila
    """
    key = f"fila:processing:{mensagem_id}"

    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.warning(f"[FilaWorker] T03.4: Erro ao liberar lock: {e}")


async def _alertar_circuit_aberto():
    """
    Sprint 36 - T01.3: Alerta quando circuit abre.
    Sprint 47: Removida notificação Slack - apenas log.
    """
    global _ultimo_alerta_circuit

    agora = datetime.now(timezone.utc)

    # Verificar cooldown
    if _ultimo_alerta_circuit:
        delta = (agora - _ultimo_alerta_circuit).total_seconds()
        if delta < _ALERTA_COOLDOWN_SEGUNDOS:
            return

    _ultimo_alerta_circuit = agora

    status = circuit_evolution.status()
    logger.critical(
        "[FilaWorker] Circuit Breaker Aberto",
        extra={
            "estado": status["estado"],
            "falhas_consecutivas": status["falhas_consecutivas"],
            "ultima_falha": status["ultima_falha"],
            "tempo_reset": circuit_evolution.tempo_reset_segundos,
        },
    )


async def processar_fila():
    """
    Worker que processa fila de mensagens.

    Roda continuamente, processando uma mensagem por vez
    respeitando rate limiting.

    Sprint 23 E01: Registra outcome detalhado em fila_mensagens.
    Sprint 36 T01.3: Integração com circuit breaker.
    """
    logger.info("Worker de fila iniciado")

    while True:
        mensagem: Optional[dict] = None
        try:
            # Sprint 36 - T01.3: Verificar circuit breaker antes de processar
            if circuit_evolution.estado == CircuitState.OPEN:
                logger.warning("[FilaWorker] Circuit breaker ABERTO - pausando processamento")
                await _alertar_circuit_aberto()

                # Aguardar tempo de reset antes de tentar novamente
                await asyncio.sleep(circuit_evolution.tempo_reset_segundos)
                continue

            # Obter próxima mensagem
            mensagem = await fila_service.obter_proxima()

            if not mensagem:
                # Fila vazia, aguardar
                await asyncio.sleep(5)
                continue

            # Sprint 44 T03.4: Verificar idempotência antes de processar
            if not await _adquirir_lock_idempotencia(mensagem["id"]):
                logger.info(f"[FilaWorker] T03.4: Mensagem {mensagem['id']} já em processamento")
                await asyncio.sleep(1)
                continue

            # Verificar rate limiting
            cliente_id = mensagem.get("cliente_id")
            if cliente_id and not await pode_enviar(cliente_id):
                # Issue #87: Rate limit é temporário, reagendar sem penalidade
                await fila_service.reagendar_sem_penalidade(mensagem["id"])
                # Sprint 44 T03.4: Liberar lock antes de continue
                await _liberar_lock_idempotencia(mensagem["id"])
                await asyncio.sleep(10)
                continue

            # Enviar mensagem
            cliente = mensagem.get("clientes", {})
            telefone = cliente.get("telefone")

            if not telefone:
                logger.error(f"Mensagem {mensagem['id']} sem telefone")
                # Registrar outcome de validacao
                await fila_service.registrar_outcome(
                    mensagem_id=mensagem["id"],
                    outcome=SendOutcome.FAILED_VALIDATION,
                    outcome_reason_code="telefone_nao_encontrado",
                )
                # Sprint 44 T03.4: Liberar lock antes de continue
                await _liberar_lock_idempotencia(mensagem["id"])
                continue

            # Resolver conversa ANTES do contexto para garantir attribution
            metadata = mensagem.get("metadata", {})
            campaign_id = metadata.get("campanha_id")
            conversa_id = mensagem.get("conversa_id")

            if not conversa_id:
                conversa = await buscar_ou_criar_conversa(cliente_id)
                if conversa:
                    conversa_id = conversa["id"]
                    # Atualizar fila_mensagens com conversa_id resolvido
                    supabase.table("fila_mensagens").update(
                        {"conversa_id": conversa_id}
                    ).eq("id", mensagem["id"]).execute()

            # Criar contexto com conversa_id já resolvido
            if campaign_id:
                # Envio de campanha
                ctx = criar_contexto_campanha(
                    cliente_id=cliente_id,
                    campaign_id=campaign_id,
                    conversation_id=conversa_id,
                )
            else:
                # Followup ou outro tipo
                ctx = criar_contexto_followup(
                    cliente_id=cliente_id,
                    conversation_id=conversa_id,
                )

            # Enviar mensagem (inclui guardrails e deduplicacao)
            result = await send_outbound_message(
                telefone=telefone,
                texto=mensagem["conteudo"],
                ctx=ctx,
                simular_digitacao=True,
            )

            # Registrar outcome detalhado (Sprint 23 E01)
            await fila_service.registrar_outcome(
                mensagem_id=mensagem["id"],
                outcome=result.outcome,
                outcome_reason_code=result.outcome_reason_code,
                provider_message_id=result.provider_message_id,
            )

            if result.outcome.is_success:
                logger.info(
                    f"Mensagem enviada: {mensagem['id']} (provider_id={result.provider_message_id})"
                )

                # Salvar interação (conversa_id já resolvido antes do envio)
                if conversa_id:
                    chip_id = getattr(result, "chip_id", None)
                    await salvar_interacao(
                        conversa_id=conversa_id,
                        cliente_id=cliente_id,
                        tipo="saida",
                        conteudo=mensagem["conteudo"],
                        autor_tipo="julia",
                        message_id=result.provider_message_id,
                        chip_id=chip_id,
                    )
            elif result.outcome.is_blocked:
                logger.info(
                    f"Mensagem {mensagem['id']} bloqueada: "
                    f"{result.outcome.value} - {result.outcome_reason_code}"
                )
            elif result.outcome.is_deduped:
                logger.info(f"Mensagem {mensagem['id']} deduplicada: {result.outcome_reason_code}")
            elif result.outcome in (
                SendOutcome.FAILED_CIRCUIT_OPEN,
                SendOutcome.FAILED_RATE_LIMIT,
                SendOutcome.FAILED_NO_CAPACITY,
            ):
                # Issue #87: Falhas temporárias → reagendar sem penalidade
                logger.warning(
                    f"Mensagem {mensagem['id']} temporária: {result.outcome.value}, reagendando"
                )
                if result.outcome == SendOutcome.FAILED_CIRCUIT_OPEN:
                    await _alertar_circuit_aberto()
                await fila_service.reagendar_sem_penalidade(mensagem["id"])
            else:
                logger.warning(
                    f"Mensagem {mensagem['id']} falhou: {result.outcome.value} - {result.error}"
                )
                await fila_service.marcar_erro(
                    mensagem["id"],
                    f"{result.outcome.value}: {result.error or 'unknown'}",
                )

            # Sprint 44 T03.4: Liberar lock após processamento
            await _liberar_lock_idempotencia(mensagem["id"])

            # Delay entre envios
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no worker: {e}", exc_info=True)
            if mensagem:
                # Registrar outcome de erro generico
                await fila_service.registrar_outcome(
                    mensagem_id=mensagem["id"],
                    outcome=SendOutcome.FAILED_PROVIDER,
                    outcome_reason_code=f"worker_exception:{str(e)[:100]}",
                )
                # Sprint 44 T03.4: Liberar lock em caso de exceção
                await _liberar_lock_idempotencia(mensagem["id"])
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(processar_fila())
