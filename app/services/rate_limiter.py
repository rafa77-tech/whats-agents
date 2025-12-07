"""
Rate limiter para controle de envio de mensagens.
Usa Redis para persistência e contagem distribuída.
"""
import logging
import random
from datetime import datetime
from typing import Tuple

from app.services.redis import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Constantes de limite (do config.py)
LIMITE_POR_HORA = settings.MAX_MSGS_POR_HORA
LIMITE_POR_DIA = settings.MAX_MSGS_POR_DIA
INTERVALO_MIN_SEGUNDOS = 45
INTERVALO_MAX_SEGUNDOS = 180
HORA_INICIO = 8   # 08:00
HORA_FIM = 20     # 20:00
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

        horario_ok, _ = await verificar_horario_permitido()

        return {
            "msgs_hora": int(msgs_hora) if msgs_hora else 0,
            "limite_hora": LIMITE_POR_HORA,
            "msgs_dia": int(msgs_dia) if msgs_dia else 0,
            "limite_dia": LIMITE_POR_DIA,
            "horario_permitido": horario_ok,
            "hora_atual": agora.strftime("%H:%M"),
            "dia_semana": agora.strftime("%A"),
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}
