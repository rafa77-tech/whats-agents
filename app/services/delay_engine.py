"""
Motor de delay inteligente.

Calcula delay apropriado baseado no contexto da mensagem.

Sprint 22 - Responsividade Inteligente

Delays por Tipo:
- reply_direta: 0-3s (resposta a pergunta)
- aceite_vaga: 0-2s (confirmacao urgente)
- confirmacao: 2-5s (confirmar detalhes)
- oferta_ativa: 15-45s (oferta proativa)
- followup: 30-120s (follow-up)
- campanha_fria: 60-180s (prospeccao fria)
"""
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.services.message_context_classifier import (
    ContextType,
    ContextClassification,
    classificar_contexto,
)
from app.services.guardrails.types import OutboundContext

logger = logging.getLogger(__name__)

# Timezone Brasil
TZ_BRASIL = ZoneInfo("America/Sao_Paulo")


@dataclass
class DelayConfig:
    """Configuracao de delay para um tipo de contexto."""
    min_ms: int
    max_ms: int
    prioridade: int
    descricao: str


# Configuracao de delays por tipo de contexto
DELAY_CONFIG = {
    ContextType.REPLY_DIRETA: DelayConfig(
        min_ms=0,
        max_ms=3000,
        prioridade=1,
        descricao="Resposta a pergunta direta"
    ),
    ContextType.ACEITE_VAGA: DelayConfig(
        min_ms=0,
        max_ms=2000,
        prioridade=1,
        descricao="Aceite/confirmacao de vaga"
    ),
    ContextType.CONFIRMACAO: DelayConfig(
        min_ms=2000,
        max_ms=5000,
        prioridade=2,
        descricao="Confirmacao de dados/detalhes"
    ),
    ContextType.OFERTA_ATIVA: DelayConfig(
        min_ms=15000,
        max_ms=45000,
        prioridade=3,
        descricao="Oferta proativa de vaga"
    ),
    ContextType.FOLLOWUP: DelayConfig(
        min_ms=30000,
        max_ms=120000,
        prioridade=4,
        descricao="Follow-up de conversa"
    ),
    ContextType.CAMPANHA_FRIA: DelayConfig(
        min_ms=60000,
        max_ms=180000,
        prioridade=5,
        descricao="Prospeccao fria/campanha"
    ),
}


@dataclass
class DelayResult:
    """Resultado do calculo de delay."""
    delay_ms: int
    delay_s: float
    tipo: ContextType
    prioridade: int
    razao: str
    config: DelayConfig


def _aplicar_variacao(base_ms: int, variacao_pct: float = 0.2) -> int:
    """Aplica variacao aleatoria ao delay."""
    variacao = random.uniform(1 - variacao_pct, 1 + variacao_pct)
    return int(base_ms * variacao)


def _ajustar_por_hora(delay_ms: int, hora: int) -> int:
    """
    Ajusta delay baseado na hora do dia.

    - Manha cedo (6-9h): +10% (pessoa acordando)
    - Almoco (12-14h): +20% (pessoa ocupada)
    - Fim do dia (18-20h): +10% (pessoa ocupada)
    - Noite (20h+): sem ajuste (fora do horario batch)
    """
    if 6 <= hora < 9:
        return int(delay_ms * 1.1)
    elif 12 <= hora < 14:
        return int(delay_ms * 1.2)
    elif 18 <= hora < 20:
        return int(delay_ms * 1.1)
    return delay_ms


def calcular_delay(
    classificacao: ContextClassification,
    tempo_processamento_ms: int = 0,
) -> DelayResult:
    """
    Calcula delay baseado na classificacao de contexto.

    Args:
        classificacao: Resultado da classificacao de contexto
        tempo_processamento_ms: Tempo ja gasto em processamento (sera descontado)

    Returns:
        DelayResult com delay calculado
    """
    config = DELAY_CONFIG.get(classificacao.tipo)
    if not config:
        # Fallback para reply_direta
        config = DELAY_CONFIG[ContextType.REPLY_DIRETA]

    # Calcular delay base (media entre min e max)
    delay_base = (config.min_ms + config.max_ms) // 2

    # Aplicar variacao aleatoria
    delay_ms = _aplicar_variacao(delay_base)

    # Ajustar por hora do dia
    hora = datetime.now(TZ_BRASIL).hour
    delay_ms = _ajustar_por_hora(delay_ms, hora)

    # Garantir limites
    delay_ms = max(config.min_ms, min(config.max_ms, delay_ms))

    # Descontar tempo de processamento
    delay_ms = max(0, delay_ms - tempo_processamento_ms)

    delay_s = delay_ms / 1000.0

    return DelayResult(
        delay_ms=delay_ms,
        delay_s=delay_s,
        tipo=classificacao.tipo,
        prioridade=classificacao.prioridade,
        razao=classificacao.razao,
        config=config,
    )


async def calcular_delay_para_resposta(
    mensagem: Optional[str] = None,
    outbound_ctx: Optional[OutboundContext] = None,
    tempo_processamento_ms: int = 0,
) -> DelayResult:
    """
    Calcula delay completo para resposta.

    Fluxo:
    1. Classifica contexto (mensagem ou OutboundContext)
    2. Busca config de delay
    3. Aplica variacoes
    4. Retorna resultado

    Args:
        mensagem: Texto da mensagem recebida
        outbound_ctx: Contexto de outbound
        tempo_processamento_ms: Tempo ja gasto

    Returns:
        DelayResult com delay calculado
    """
    # Classificar contexto
    classificacao = await classificar_contexto(
        mensagem=mensagem,
        outbound_ctx=outbound_ctx,
    )

    # Calcular delay
    resultado = calcular_delay(classificacao, tempo_processamento_ms)

    logger.info(
        f"Delay calculado: {resultado.delay_ms}ms para {resultado.tipo.value} "
        f"(prioridade: {resultado.prioridade})"
    )

    return resultado


def has_valid_inbound_proof(ctx: OutboundContext, max_age_minutes: int = 30) -> bool:
    """
    Verifica se OutboundContext tem prova valida de inbound.

    Ajuste A do Sprint 22:
    - Reply 24/7 SOMENTE com inbound_proof valido
    - inbound_proof = inbound_interaction_id + last_inbound_at recente

    Args:
        ctx: Contexto de outbound
        max_age_minutes: Idade maxima do last_inbound_at em minutos

    Returns:
        True se tem prova valida de inbound recente
    """
    # Precisa ter interaction_id
    if not ctx.inbound_interaction_id:
        return False

    # Precisa ter timestamp
    if not ctx.last_inbound_at:
        return False

    # Timestamp precisa ser recente
    try:
        last_inbound = datetime.fromisoformat(ctx.last_inbound_at.replace('Z', '+00:00'))

        # Normalizar timezone - usar o mesmo timezone do last_inbound
        if last_inbound.tzinfo is None:
            # Se nao tem timezone, assumir Brasilia
            last_inbound = last_inbound.replace(tzinfo=TZ_BRASIL)
            now = datetime.now(TZ_BRASIL)
        else:
            now = datetime.now(last_inbound.tzinfo)

        age = now - last_inbound

        if age > timedelta(minutes=max_age_minutes):
            logger.debug(
                f"Inbound proof expirado: {age.total_seconds() / 60:.1f} min "
                f"(max: {max_age_minutes} min)"
            )
            return False

        return True

    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao parsear last_inbound_at: {e}")
        return False


def deve_aplicar_delay(
    ctx: Optional[OutboundContext],
    classificacao: ContextClassification,
) -> bool:
    """
    Determina se deve aplicar delay para esta mensagem.

    Regras:
    - REPLY com inbound_proof valido: delay minimo (0-3s)
    - Proativo: delay normal por tipo
    - Campanha: delay longo (60-180s)

    Args:
        ctx: Contexto de outbound
        classificacao: Classificacao do contexto

    Returns:
        True se deve aplicar delay
    """
    # Sempre aplicar delay (mas delay pode ser 0)
    return True


# =============================================================================
# Funcoes de conveniencia para TimingProcessor
# =============================================================================

async def get_delay_seconds(
    mensagem: str,
    outbound_ctx: Optional[OutboundContext] = None,
    tempo_processamento_s: float = 0,
) -> float:
    """
    Funcao de conveniencia que retorna delay em segundos.

    Substitui calcular_delay_resposta() do timing.py antigo.

    Args:
        mensagem: Texto da mensagem
        outbound_ctx: Contexto de outbound
        tempo_processamento_s: Tempo de processamento em segundos

    Returns:
        Delay em segundos
    """
    resultado = await calcular_delay_para_resposta(
        mensagem=mensagem,
        outbound_ctx=outbound_ctx,
        tempo_processamento_ms=int(tempo_processamento_s * 1000),
    )
    return resultado.delay_s
