"""
Guardrails para external handoff.

Sprint 21 - E04 - Proteções para divulgadores:
- Opt-out (divulgador pode recusar receber mensagens)
- Horário comercial (08:00-20:00 seg-sex)
"""
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Timezone de São Paulo
SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

# Horário comercial
BUSINESS_HOUR_START = time(8, 0)   # 08:00
BUSINESS_HOUR_END = time(20, 0)    # 20:00
BUSINESS_DAYS = (0, 1, 2, 3, 4)    # Segunda a sexta (0=segunda)


async def buscar_contato_externo(telefone: str) -> Optional[dict]:
    """
    Busca um contato externo pelo telefone.

    Args:
        telefone: Número de telefone

    Returns:
        Dict com dados do contato ou None
    """
    try:
        response = supabase.table("external_contacts") \
            .select("*") \
            .eq("telefone", telefone) \
            .limit(1) \
            .execute()

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar contato externo: {e}")
        return None


async def registrar_contato_externo(
    telefone: str,
    nome: Optional[str] = None,
    empresa: Optional[str] = None,
) -> dict:
    """
    Registra ou atualiza um contato externo.

    Args:
        telefone: Número de telefone
        nome: Nome do contato
        empresa: Empresa do contato

    Returns:
        Dict com dados do contato
    """
    try:
        # Upsert: insere ou atualiza se existir
        data = {
            "telefone": telefone,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if nome:
            data["nome"] = nome
        if empresa:
            data["empresa"] = empresa

        response = supabase.table("external_contacts") \
            .upsert(data, on_conflict="telefone") \
            .execute()

        return response.data[0] if response.data else data

    except Exception as e:
        logger.error(f"Erro ao registrar contato externo: {e}")
        return {"telefone": telefone}


async def registrar_optout(
    telefone: str,
    reason: Optional[str] = None,
) -> bool:
    """
    Registra opt-out de um contato.

    Args:
        telefone: Número de telefone
        reason: Motivo do opt-out

    Returns:
        True se sucesso
    """
    try:
        now = datetime.now(timezone.utc).isoformat()

        response = supabase.table("external_contacts") \
            .upsert({
                "telefone": telefone,
                "permission_state": "opted_out",
                "opted_out_at": now,
                "opted_out_reason": reason,
                "updated_at": now,
            }, on_conflict="telefone") \
            .execute()

        logger.info(f"Opt-out registrado para {telefone[-4:]}: {reason}")
        return True

    except Exception as e:
        logger.error(f"Erro ao registrar opt-out: {e}")
        return False


async def esta_opted_out(telefone: str) -> bool:
    """
    Verifica se um contato está opted-out.

    Args:
        telefone: Número de telefone

    Returns:
        True se contato está opted-out
    """
    contato = await buscar_contato_externo(telefone)

    if not contato:
        return False

    return contato.get("permission_state") == "opted_out"


def esta_em_horario_comercial(agora: Optional[datetime] = None) -> bool:
    """
    Verifica se o horário atual é comercial.

    Args:
        agora: Datetime para verificar (default: agora)

    Returns:
        True se está em horário comercial
    """
    if agora is None:
        agora = datetime.now(SAO_PAULO_TZ)
    else:
        # Converter para timezone de São Paulo
        agora = agora.astimezone(SAO_PAULO_TZ)

    # Verificar dia da semana (0=segunda, 6=domingo)
    if agora.weekday() not in BUSINESS_DAYS:
        return False

    # Verificar horário
    hora_atual = agora.time()
    return BUSINESS_HOUR_START <= hora_atual <= BUSINESS_HOUR_END


def calcular_proximo_horario_comercial(agora: Optional[datetime] = None) -> datetime:
    """
    Calcula o próximo horário comercial disponível.

    Args:
        agora: Datetime de referência (default: agora)

    Returns:
        Datetime do próximo horário comercial
    """
    if agora is None:
        agora = datetime.now(SAO_PAULO_TZ)
    else:
        agora = agora.astimezone(SAO_PAULO_TZ)

    # Se já está em horário comercial, retornar agora
    if esta_em_horario_comercial(agora):
        return agora

    # Calcular próximo horário comercial
    proximo = agora

    # Se passou do horário de fim, ir para o próximo dia
    if proximo.time() > BUSINESS_HOUR_END:
        proximo = proximo.replace(
            hour=BUSINESS_HOUR_START.hour,
            minute=BUSINESS_HOUR_START.minute,
            second=0,
            microsecond=0,
        )
        proximo = proximo + timedelta(days=1)
    elif proximo.time() < BUSINESS_HOUR_START:
        # Antes do horário de início, ajustar para hoje
        proximo = proximo.replace(
            hour=BUSINESS_HOUR_START.hour,
            minute=BUSINESS_HOUR_START.minute,
            second=0,
            microsecond=0,
        )

    # Pular fins de semana
    while proximo.weekday() not in BUSINESS_DAYS:
        proximo = proximo + timedelta(days=1)
        proximo = proximo.replace(
            hour=BUSINESS_HOUR_START.hour,
            minute=BUSINESS_HOUR_START.minute,
            second=0,
            microsecond=0,
        )

    return proximo


async def pode_contatar_divulgador(
    telefone: str,
) -> Tuple[bool, str, Optional[datetime]]:
    """
    Verifica se um divulgador pode ser contatado.

    Args:
        telefone: Número de telefone do divulgador

    Returns:
        Tuple de (pode_contatar: bool, motivo: str, agendar_para: Optional[datetime])
        - pode_contatar: True se pode contatar agora
        - motivo: Motivo do bloqueio se não pode
        - agendar_para: Se fora do horário, quando agendar
    """
    # 1. Verificar opt-out
    if await esta_opted_out(telefone):
        logger.info(f"Divulgador {telefone[-4:]} está opted-out")
        return False, "opted_out", None

    # 2. Verificar horário comercial
    if not esta_em_horario_comercial():
        proximo_horario = calcular_proximo_horario_comercial()
        logger.info(
            f"Fora do horário comercial, agendar para {proximo_horario}"
        )
        return False, "outside_business_hours", proximo_horario

    return True, "", None
