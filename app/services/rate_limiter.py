"""
Rate limiter para controle de envio de mensagens.
Usa Redis para persistência e contagem distribuída.

Sprint 36 - Melhorias:
- T04.1: Rate limiting por cliente (não só global)
- T04.2: Rate limiting por tipo de mensagem
- T04.3: Jitter nos intervalos
- T04.4: Fallback para Supabase se Redis cair
"""
import logging
import random
from datetime import datetime, timezone
from typing import Tuple, Optional
from enum import Enum

from app.services.redis import redis_client
from app.core.config import settings, DatabaseConfig

logger = logging.getLogger(__name__)

# Constantes de limite (centralizadas em config.py)
LIMITE_POR_HORA = settings.MAX_MSGS_POR_HORA
LIMITE_POR_DIA = settings.MAX_MSGS_POR_DIA
INTERVALO_MIN_SEGUNDOS = DatabaseConfig.INTERVALO_MIN_SEGUNDOS
INTERVALO_MAX_SEGUNDOS = DatabaseConfig.INTERVALO_MAX_SEGUNDOS
HORA_INICIO = DatabaseConfig.HORA_INICIO
HORA_FIM = DatabaseConfig.HORA_FIM
DIAS_PERMITIDOS = [0, 1, 2, 3, 4]  # Seg-Sex (0=Segunda)


class TipoMensagem(Enum):
    """Sprint 36 - T04.2: Tipos de mensagem para rate limiting diferenciado."""
    PROSPECCAO = "prospeccao"      # Mensagem fria - limite mais restrito
    FOLLOWUP = "followup"          # Follow-up - limite médio
    RESPOSTA = "resposta"          # Resposta a médico - limite alto
    CAMPANHA = "campanha"          # Campanha - limite específico
    SISTEMA = "sistema"            # Sistema - sem limite


# Sprint 36 - T04.2: Limites por tipo de mensagem (por hora)
LIMITES_POR_TIPO = {
    TipoMensagem.PROSPECCAO: 10,   # Máximo 10 prospecções/hora
    TipoMensagem.FOLLOWUP: 15,     # Máximo 15 follow-ups/hora
    TipoMensagem.RESPOSTA: 50,     # Respostas têm limite alto
    TipoMensagem.CAMPANHA: 20,     # Campanhas têm limite próprio
    TipoMensagem.SISTEMA: 1000,    # Sistema praticamente sem limite
}

# Sprint 36 - T04.1: Limites por cliente (mensagens/hora)
LIMITE_POR_CLIENTE_HORA = 3  # Máximo 3 msgs/hora para mesmo cliente


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


# ============================================================
# Sprint 36 - T04.1: Rate limiting por cliente
# ============================================================

async def verificar_limite_cliente(cliente_id: str) -> Tuple[bool, int]:
    """
    Sprint 36 - T04.1: Verifica limite de mensagens por cliente.

    Evita spam para o mesmo cliente.

    Args:
        cliente_id: ID do cliente

    Returns:
        (dentro_limite, msgs_enviadas)
    """
    chave = f"rate:cliente:{cliente_id}:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        count = await redis_client.get(chave)
        count = int(count) if count else 0

        return count < LIMITE_POR_CLIENTE_HORA, count
    except Exception as e:
        logger.error(f"Erro ao verificar limite cliente: {e}")
        # Sprint 36 - T04.4: Tentar fallback Supabase
        return await _fallback_verificar_limite_cliente(cliente_id)


async def _fallback_verificar_limite_cliente(cliente_id: str) -> Tuple[bool, int]:
    """
    Sprint 36 - T04.4: Fallback para Supabase quando Redis cai.
    """
    try:
        from app.services.supabase import supabase
        from datetime import timedelta

        agora = datetime.now(timezone.utc)
        uma_hora_atras = (agora - timedelta(hours=1)).isoformat()

        result = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq(
            "cliente_id", cliente_id
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        count = result.count or 0
        return count < LIMITE_POR_CLIENTE_HORA, count

    except Exception as e:
        logger.warning(f"[rate_limiter] Fallback Supabase também falhou: {e}")
        return True, 0  # Em caso de falha total, permitir


async def registrar_envio_cliente(cliente_id: str) -> None:
    """
    Sprint 36 - T04.1: Registra envio para rate limiting por cliente.
    """
    chave = f"rate:cliente:{cliente_id}:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        await redis_client.incr(chave)
        await redis_client.expire(chave, 7200)  # 2 horas
    except Exception as e:
        logger.error(f"Erro ao registrar envio cliente: {e}")


# ============================================================
# Sprint 36 - T04.2: Rate limiting por tipo de mensagem
# ============================================================

async def verificar_limite_tipo(
    tipo: TipoMensagem = TipoMensagem.RESPOSTA
) -> Tuple[bool, int, int]:
    """
    Sprint 36 - T04.2: Verifica limite por tipo de mensagem.

    Args:
        tipo: Tipo de mensagem (prospeccao, followup, resposta, etc)

    Returns:
        (dentro_limite, msgs_enviadas, limite_tipo)
    """
    limite = LIMITES_POR_TIPO.get(tipo, LIMITE_POR_HORA)
    chave = f"rate:tipo:{tipo.value}:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        count = await redis_client.get(chave)
        count = int(count) if count else 0

        return count < limite, count, limite
    except Exception as e:
        logger.error(f"Erro ao verificar limite tipo: {e}")
        return True, 0, limite


async def registrar_envio_tipo(tipo: TipoMensagem) -> None:
    """
    Sprint 36 - T04.2: Registra envio para rate limiting por tipo.
    """
    chave = f"rate:tipo:{tipo.value}:{datetime.now().strftime('%Y%m%d%H')}"

    try:
        await redis_client.incr(chave)
        await redis_client.expire(chave, 7200)
    except Exception as e:
        logger.error(f"Erro ao registrar envio tipo: {e}")


# ============================================================
# Sprint 36 - T04.3: Jitter nos intervalos
# ============================================================

def calcular_delay_com_jitter(
    base_min: int = None,
    base_max: int = None,
    jitter_pct: float = 0.2
) -> int:
    """
    Sprint 36 - T04.3: Calcula delay com jitter para parecer mais humano.

    Adiciona variação aleatória ao delay base para evitar padrões
    detectáveis.

    Args:
        base_min: Intervalo mínimo (default: config)
        base_max: Intervalo máximo (default: config)
        jitter_pct: Percentual de variação (default: 20%)

    Returns:
        Delay em segundos com jitter aplicado
    """
    base_min = base_min or INTERVALO_MIN_SEGUNDOS
    base_max = base_max or INTERVALO_MAX_SEGUNDOS

    # Delay base
    base = random.randint(base_min, base_max)

    # Jitter: +/- jitter_pct do valor base
    jitter_range = int(base * jitter_pct)
    jitter = random.randint(-jitter_range, jitter_range)

    # Adicionar variação extra para alguns envios (parecer "distraída")
    if random.random() < 0.1:  # 10% das vezes
        jitter += random.randint(30, 90)  # Delay extra de 30-90s

    resultado = base + jitter
    return max(base_min, resultado)  # Nunca menor que o mínimo


def calcular_delay_por_tipo(tipo: TipoMensagem) -> int:
    """
    Sprint 36 - T04.3: Calcula delay baseado no tipo de mensagem.

    Prospecção e follow-up têm delays maiores que respostas.
    """
    if tipo == TipoMensagem.PROSPECCAO:
        # Prospecção: delays maiores (mais cuidadoso)
        return calcular_delay_com_jitter(60, 180, jitter_pct=0.25)

    elif tipo == TipoMensagem.FOLLOWUP:
        # Follow-up: delays médios
        return calcular_delay_com_jitter(45, 120, jitter_pct=0.2)

    elif tipo == TipoMensagem.RESPOSTA:
        # Resposta: delays curtos (engajamento)
        return calcular_delay_com_jitter(30, 90, jitter_pct=0.15)

    elif tipo == TipoMensagem.CAMPANHA:
        # Campanha: delays configuráveis
        return calcular_delay_com_jitter(45, 150, jitter_pct=0.2)

    else:
        # Sistema: delays mínimos
        return calcular_delay_com_jitter(5, 15, jitter_pct=0.1)


# ============================================================
# Sprint 36 - T04.4: Fallback para Supabase
# ============================================================

async def _fallback_verificar_limite_hora() -> Tuple[bool, int]:
    """
    Sprint 36 - T04.4: Fallback para Supabase quando Redis cai.

    Conta mensagens da última hora no banco.
    """
    try:
        from app.services.supabase import supabase
        from datetime import timedelta

        agora = datetime.now(timezone.utc)
        uma_hora_atras = (agora - timedelta(hours=1)).isoformat()

        result = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).in_(
            "status", ["enviada", "processando"]
        ).gte(
            "created_at", uma_hora_atras
        ).execute()

        count = result.count or 0
        logger.info(f"[rate_limiter] Fallback Supabase: {count} msgs/hora")

        return count < LIMITE_POR_HORA, count

    except Exception as e:
        logger.error(f"[rate_limiter] Fallback Supabase falhou: {e}")
        return True, 0


async def _fallback_verificar_limite_dia() -> Tuple[bool, int]:
    """
    Sprint 36 - T04.4: Fallback para Supabase quando Redis cai.

    Conta mensagens do dia no banco.
    """
    try:
        from app.services.supabase import supabase
        from datetime import timedelta

        agora = datetime.now(timezone.utc)
        inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

        result = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).in_(
            "status", ["enviada", "processando"]
        ).gte(
            "created_at", inicio_dia.isoformat()
        ).execute()

        count = result.count or 0
        logger.info(f"[rate_limiter] Fallback Supabase: {count} msgs/dia")

        return count < LIMITE_POR_DIA, count

    except Exception as e:
        logger.error(f"[rate_limiter] Fallback Supabase falhou: {e}")
        return True, 0


# ============================================================
# Função principal com todas as verificações Sprint 36
# ============================================================

async def pode_enviar_completo(
    telefone: str,
    cliente_id: Optional[str] = None,
    tipo: TipoMensagem = TipoMensagem.RESPOSTA
) -> Tuple[bool, str]:
    """
    Sprint 36: Verificação completa de rate limiting.

    Verifica:
    1. Horário comercial
    2. Limite global por hora
    3. Limite global por dia
    4. Limite por cliente (T04.1)
    5. Limite por tipo de mensagem (T04.2)
    6. Intervalo mínimo por telefone

    Args:
        telefone: Número do destinatário
        cliente_id: ID do cliente (opcional)
        tipo: Tipo de mensagem

    Returns:
        (pode_enviar, motivo)
    """
    # 1. Verificar horário comercial
    ok, motivo = await verificar_horario_permitido()
    if not ok:
        return False, motivo

    # 2. Verificar limite global por hora
    ok, count = await verificar_limite_hora()
    if not ok:
        return False, f"Limite por hora atingido ({count}/{LIMITE_POR_HORA})"

    # 3. Verificar limite global por dia
    ok, count = await verificar_limite_dia()
    if not ok:
        return False, f"Limite por dia atingido ({count}/{LIMITE_POR_DIA})"

    # 4. Sprint 36 - T04.1: Verificar limite por cliente
    if cliente_id:
        ok, count = await verificar_limite_cliente(cliente_id)
        if not ok:
            return False, f"Limite por cliente atingido ({count}/{LIMITE_POR_CLIENTE_HORA})"

    # 5. Sprint 36 - T04.2: Verificar limite por tipo
    ok, count, limite = await verificar_limite_tipo(tipo)
    if not ok:
        return False, f"Limite de {tipo.value} atingido ({count}/{limite})"

    # 6. Verificar intervalo mínimo
    ok, segundos = await verificar_intervalo_minimo(telefone)
    if not ok:
        return False, f"Aguardar {segundos}s antes de enviar novamente"

    return True, "OK"


async def registrar_envio_completo(
    telefone: str,
    cliente_id: Optional[str] = None,
    tipo: TipoMensagem = TipoMensagem.RESPOSTA
) -> None:
    """
    Sprint 36: Registra envio em todos os contadores.
    """
    # Registro global
    await registrar_envio(telefone)

    # Sprint 36 - T04.1: Registro por cliente
    if cliente_id:
        await registrar_envio_cliente(cliente_id)

    # Sprint 36 - T04.2: Registro por tipo
    await registrar_envio_tipo(tipo)
