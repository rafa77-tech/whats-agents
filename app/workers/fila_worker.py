"""
Worker para processar fila de mensagens.

Sprint 23 E01 - Registra outcome detalhado para cada envio.
Sprint 36 - T01.3: Circuit breaker no fila_worker.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.fila import fila_service
from app.services.rate_limiter import pode_enviar
from app.services.outbound import send_outbound_message, criar_contexto_followup, criar_contexto_campanha
from app.services.guardrails import SendOutcome
from app.services.circuit_breaker import circuit_evolution, CircuitState

logger = logging.getLogger(__name__)

# Sprint 36 - T01.3: Controle de alertas
_ultimo_alerta_circuit: Optional[datetime] = None
_ALERTA_COOLDOWN_SEGUNDOS = 300  # 5 minutos entre alertas


async def _alertar_circuit_aberto():
    """
    Sprint 36 - T01.3: Alerta via Slack quando circuit abre.

    Envia alerta com cooldown para evitar spam.
    """
    global _ultimo_alerta_circuit

    agora = datetime.now(timezone.utc)

    # Verificar cooldown
    if _ultimo_alerta_circuit:
        delta = (agora - _ultimo_alerta_circuit).total_seconds()
        if delta < _ALERTA_COOLDOWN_SEGUNDOS:
            return

    _ultimo_alerta_circuit = agora

    try:
        from app.services.slack import enviar_mensagem_slack

        status = circuit_evolution.status()
        await enviar_mensagem_slack(
            canal="alertas",
            texto=(
                f":rotating_light: *Circuit Breaker Aberto - Fila Worker*\n\n"
                f"O circuit breaker do Evolution API está aberto!\n"
                f"- Estado: `{status['estado']}`\n"
                f"- Falhas consecutivas: `{status['falhas_consecutivas']}`\n"
                f"- Última falha: `{status['ultima_falha'] or 'N/A'}`\n\n"
                f"O worker está pausado e tentará novamente em "
                f"`{circuit_evolution.tempo_reset_segundos}s`.\n"
                f"Verifique a Evolution API e os logs do sistema."
            ),
        )
    except Exception as e:
        logger.error(f"[FilaWorker] Erro ao enviar alerta Slack: {e}")


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
                logger.warning(
                    "[FilaWorker] Circuit breaker ABERTO - pausando processamento"
                )
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

            # Verificar rate limiting
            cliente_id = mensagem.get("cliente_id")
            if cliente_id and not await pode_enviar(cliente_id):
                # Reagendar para depois
                await fila_service.marcar_erro(
                    mensagem["id"],
                    "Rate limit atingido"
                )
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
                continue

            # Criar contexto apropriado baseado no tipo e metadata
            metadata = mensagem.get("metadata", {})
            campaign_id = metadata.get("campanha_id")

            if campaign_id:
                # Envio de campanha
                ctx = criar_contexto_campanha(
                    cliente_id=cliente_id,
                    campaign_id=campaign_id,
                    conversation_id=mensagem.get("conversa_id"),
                )
            else:
                # Followup ou outro tipo
                ctx = criar_contexto_followup(
                    cliente_id=cliente_id,
                    conversation_id=mensagem.get("conversa_id"),
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
                    f"Mensagem enviada: {mensagem['id']} "
                    f"(provider_id={result.provider_message_id})"
                )
            elif result.outcome.is_blocked:
                logger.info(
                    f"Mensagem {mensagem['id']} bloqueada: "
                    f"{result.outcome.value} - {result.outcome_reason_code}"
                )
            elif result.outcome.is_deduped:
                logger.info(
                    f"Mensagem {mensagem['id']} deduplicada: "
                    f"{result.outcome_reason_code}"
                )
            elif result.outcome == SendOutcome.FAILED_CIRCUIT_OPEN:
                # Sprint 36 - T01.3: Alertar quando circuit abre
                logger.warning(
                    f"Mensagem {mensagem['id']} falhou por circuit open"
                )
                await _alertar_circuit_aberto()
            else:
                logger.warning(
                    f"Mensagem {mensagem['id']} falhou: "
                    f"{result.outcome.value} - {result.error}"
                )

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
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(processar_fila())
