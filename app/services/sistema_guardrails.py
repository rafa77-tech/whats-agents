"""
Sistema de guardrails para controle operacional.

Sprint 36 - Resiliência e Observabilidade:
- T06.1: Feature flags para desabilitar funcionalidades
- T06.2: Audit trail de ações críticas
- T06.3: Endpoint para desbloquear clientes/chips
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from app.services.supabase import supabase
from app.services.redis import redis_client

logger = logging.getLogger(__name__)


# ============================================================
# Sprint 36 - T06.1: Feature Flags
# ============================================================

class FeatureFlag(Enum):
    """Feature flags disponíveis no sistema."""
    # Envio de mensagens
    ENVIO_PROSPECCAO = "envio_prospeccao"
    ENVIO_FOLLOWUP = "envio_followup"
    ENVIO_RESPOSTA = "envio_resposta"
    ENVIO_CAMPANHA = "envio_campanha"

    # Chips
    CHIP_AUTO_REPLACE = "chip_auto_replace"
    CHIP_AUTO_PROVISION = "chip_auto_provision"
    CHIP_AFFINITY = "chip_affinity"

    # Workers
    WORKER_FILA = "worker_fila"
    WORKER_CAMPANHAS = "worker_campanhas"
    WORKER_GRUPOS = "worker_grupos"

    # Integrações
    INTEGRATION_EVOLUTION = "integration_evolution"
    INTEGRATION_CHATWOOT = "integration_chatwoot"
    INTEGRATION_SLACK = "integration_slack"


# Cache em memória para feature flags (TTL: 60s)
_feature_flag_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 60


async def obter_feature_flag(flag: FeatureFlag) -> bool:
    """
    Sprint 36 - T06.1: Verifica se uma feature flag está habilitada.

    Hierarquia de verificação:
    1. Redis (para alterações em tempo real)
    2. Banco de dados (tabela app_settings)
    3. Default: True (fail-open para não quebrar sistema)

    Args:
        flag: Feature flag a verificar

    Returns:
        True se habilitada, False se desabilitada
    """
    flag_key = f"feature_flag:{flag.value}"
    now = datetime.now(timezone.utc).timestamp()

    # 1. Verificar cache em memória
    if flag_key in _feature_flag_cache:
        cached_value, cached_at = _feature_flag_cache[flag_key]
        if now - cached_at < CACHE_TTL_SECONDS:
            return cached_value

    # 2. Verificar Redis
    try:
        redis_value = await redis_client.get(flag_key)
        if redis_value is not None:
            value = redis_value.lower() == "true"
            _feature_flag_cache[flag_key] = (value, now)
            return value
    except Exception as e:
        logger.debug(f"[guardrails] Redis não disponível para flag: {e}")

    # 3. Verificar banco de dados
    try:
        result = supabase.table("app_settings").select("value").eq(
            "key", flag_key
        ).single().execute()

        if result.data:
            value = result.data.get("value", "true").lower() == "true"
            _feature_flag_cache[flag_key] = (value, now)
            return value
    except Exception as e:
        logger.debug(f"[guardrails] Flag não encontrada no banco: {e}")

    # 4. Default: habilitado
    _feature_flag_cache[flag_key] = (True, now)
    return True


async def definir_feature_flag(
    flag: FeatureFlag,
    habilitada: bool,
    motivo: str,
    usuario: str = "sistema"
) -> bool:
    """
    Sprint 36 - T06.1: Define valor de uma feature flag.

    Args:
        flag: Feature flag a definir
        habilitada: True para habilitar, False para desabilitar
        motivo: Motivo da alteração
        usuario: Usuário que fez a alteração

    Returns:
        True se sucesso
    """
    flag_key = f"feature_flag:{flag.value}"
    valor = "true" if habilitada else "false"

    try:
        # 1. Atualizar Redis (propagação imediata)
        try:
            await redis_client.set(flag_key, valor)
        except Exception as e:
            logger.warning(f"[guardrails] Erro ao atualizar Redis: {e}")

        # 2. Atualizar banco de dados (persistência)
        supabase.table("app_settings").upsert({
            "key": flag_key,
            "value": valor,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="key").execute()

        # 3. Registrar no audit trail
        await registrar_audit_trail(
            acao="feature_flag_change",
            entidade=flag.value,
            detalhes={
                "habilitada": habilitada,
                "motivo": motivo,
                "valor_anterior": _feature_flag_cache.get(flag_key, (None, 0))[0],
            },
            usuario=usuario
        )

        # 4. Limpar cache
        if flag_key in _feature_flag_cache:
            del _feature_flag_cache[flag_key]

        logger.info(f"[guardrails] Feature flag {flag.value} = {habilitada} ({motivo})")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao definir feature flag: {e}")
        return False


async def listar_feature_flags() -> Dict[str, bool]:
    """
    Sprint 36 - T06.1: Lista todas as feature flags e seus estados.

    Returns:
        Dict com flag: habilitada
    """
    flags = {}
    for flag in FeatureFlag:
        flags[flag.value] = await obter_feature_flag(flag)
    return flags


# ============================================================
# Sprint 36 - T06.2: Audit Trail
# ============================================================

class AcaoAuditoria(Enum):
    """Tipos de ações auditáveis."""
    # Feature flags
    FEATURE_FLAG_CHANGE = "feature_flag_change"

    # Chips
    CHIP_BLOQUEADO = "chip_bloqueado"
    CHIP_DESBLOQUEADO = "chip_desbloqueado"
    CHIP_REMOVIDO = "chip_removido"
    CHIP_ADICIONADO = "chip_adicionado"

    # Clientes
    CLIENTE_BLOQUEADO = "cliente_bloqueado"
    CLIENTE_DESBLOQUEADO = "cliente_desbloqueado"
    CLIENTE_OPTOUT = "cliente_optout"

    # Sistema
    CIRCUIT_BREAKER_RESET = "circuit_breaker_reset"
    FILA_LIMPA = "fila_limpa"
    EMERGENCIA_ATIVADA = "emergencia_ativada"

    # Campanhas
    CAMPANHA_PAUSADA = "campanha_pausada"
    CAMPANHA_RETOMADA = "campanha_retomada"
    CAMPANHA_CANCELADA = "campanha_cancelada"


async def registrar_audit_trail(
    acao: str,
    entidade: str,
    detalhes: Optional[Dict[str, Any]] = None,
    usuario: str = "sistema",
    entidade_id: Optional[str] = None,
) -> Optional[str]:
    """
    Sprint 36 - T06.2: Registra ação no audit trail.

    Args:
        acao: Tipo de ação (use AcaoAuditoria.value)
        entidade: Tipo de entidade afetada
        detalhes: Detalhes adicionais da ação
        usuario: Usuário que executou a ação
        entidade_id: ID da entidade afetada (opcional)

    Returns:
        ID do registro de auditoria ou None se falhou
    """
    try:
        registro = {
            "acao": acao,
            "entidade": entidade,
            "entidade_id": entidade_id,
            "detalhes": detalhes or {},
            "usuario": usuario,
            "ip_address": None,  # Preenchido pelo handler HTTP se disponível
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = supabase.table("audit_trail").insert(registro).execute()

        if result.data:
            logger.info(
                f"[audit] {acao} em {entidade} por {usuario}",
                extra={"audit_id": result.data[0].get("id")}
            )
            return result.data[0].get("id")

        return None

    except Exception as e:
        # Audit trail não pode falhar silenciosamente em produção
        logger.error(f"[audit] FALHA ao registrar: {acao} - {e}")
        return None


async def buscar_audit_trail(
    acao: Optional[str] = None,
    entidade: Optional[str] = None,
    entidade_id: Optional[str] = None,
    usuario: Optional[str] = None,
    horas: int = 24,
    limite: int = 100,
) -> List[Dict]:
    """
    Sprint 36 - T06.2: Busca registros no audit trail.

    Args:
        acao: Filtrar por tipo de ação
        entidade: Filtrar por tipo de entidade
        entidade_id: Filtrar por ID da entidade
        usuario: Filtrar por usuário
        horas: Período em horas (default 24)
        limite: Máximo de registros (default 100)

    Returns:
        Lista de registros de auditoria
    """
    try:
        from datetime import timedelta

        inicio = (
            datetime.now(timezone.utc) - timedelta(hours=horas)
        ).isoformat()

        query = supabase.table("audit_trail").select("*").gte(
            "created_at", inicio
        ).order("created_at", desc=True).limit(limite)

        if acao:
            query = query.eq("acao", acao)
        if entidade:
            query = query.eq("entidade", entidade)
        if entidade_id:
            query = query.eq("entidade_id", entidade_id)
        if usuario:
            query = query.eq("usuario", usuario)

        result = query.execute()
        return result.data or []

    except Exception as e:
        logger.error(f"[audit] Erro ao buscar audit trail: {e}")
        return []


# ============================================================
# Sprint 36 - T06.3: Desbloqueio de Entidades
# ============================================================

async def desbloquear_chip(
    chip_id: str,
    motivo: str,
    usuario: str = "sistema"
) -> bool:
    """
    Sprint 36 - T06.3: Desbloqueia um chip manualmente.

    Reseta:
    - Circuit breaker do chip
    - Cooldown do chip
    - Contadores de erro

    Args:
        chip_id: ID do chip
        motivo: Motivo do desbloqueio
        usuario: Usuário que desbloqueou

    Returns:
        True se sucesso
    """
    try:
        # 1. Buscar chip
        chip_result = supabase.table("chips").select(
            "id, telefone, status, trust_score"
        ).eq("id", chip_id).single().execute()

        if not chip_result.data:
            logger.warning(f"[guardrails] Chip não encontrado: {chip_id}")
            return False

        chip = chip_result.data
        estado_anterior = {
            "status": chip.get("status"),
            "trust_score": chip.get("trust_score"),
        }

        # 2. Resetar circuit breaker do chip
        try:
            from app.services.chips.circuit_breaker import chip_circuit_breaker
            chip_circuit_breaker.reset_circuit(chip_id)
        except Exception as e:
            logger.warning(f"[guardrails] Erro ao resetar circuit: {e}")

        # 3. Limpar cooldown do chip
        try:
            from app.services.chips.cooldown import limpar_cooldown
            await limpar_cooldown(chip_id)
        except Exception as e:
            logger.warning(f"[guardrails] Erro ao limpar cooldown: {e}")

        # 4. Atualizar chip no banco
        supabase.table("chips").update({
            "status": "active",
            "erros_ultimas_24h": 0,
            "ultimo_erro": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", chip_id).execute()

        # 5. Registrar no audit trail
        await registrar_audit_trail(
            acao=AcaoAuditoria.CHIP_DESBLOQUEADO.value,
            entidade="chip",
            entidade_id=chip_id,
            detalhes={
                "motivo": motivo,
                "telefone": chip.get("telefone", "")[-4:],
                "estado_anterior": estado_anterior,
            },
            usuario=usuario
        )

        logger.info(f"[guardrails] Chip {chip_id} desbloqueado por {usuario}: {motivo}")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao desbloquear chip: {e}")
        return False


async def desbloquear_cliente(
    cliente_id: str,
    motivo: str,
    usuario: str = "sistema"
) -> bool:
    """
    Sprint 36 - T06.3: Desbloqueia um cliente manualmente.

    Reseta:
    - Rate limit do cliente
    - Flags de bloqueio
    - Contadores de erro

    Args:
        cliente_id: ID do cliente
        motivo: Motivo do desbloqueio
        usuario: Usuário que desbloqueou

    Returns:
        True se sucesso
    """
    try:
        # 1. Buscar cliente
        cliente_result = supabase.table("clientes").select(
            "id, telefone, status, bloqueado"
        ).eq("id", cliente_id).single().execute()

        if not cliente_result.data:
            logger.warning(f"[guardrails] Cliente não encontrado: {cliente_id}")
            return False

        cliente = cliente_result.data
        estado_anterior = {
            "status": cliente.get("status"),
            "bloqueado": cliente.get("bloqueado"),
        }

        # 2. Limpar rate limit do cliente no Redis
        try:
            hora = datetime.now().strftime('%Y%m%d%H')
            chave = f"rate:cliente:{cliente_id}:{hora}"
            await redis_client.delete(chave)
        except Exception as e:
            logger.warning(f"[guardrails] Erro ao limpar rate limit: {e}")

        # 3. Atualizar cliente no banco
        supabase.table("clientes").update({
            "bloqueado": False,
            "motivo_bloqueio": None,
            "status": "ativo",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", cliente_id).execute()

        # 4. Registrar no audit trail
        await registrar_audit_trail(
            acao=AcaoAuditoria.CLIENTE_DESBLOQUEADO.value,
            entidade="cliente",
            entidade_id=cliente_id,
            detalhes={
                "motivo": motivo,
                "telefone": cliente.get("telefone", "")[-4:],
                "estado_anterior": estado_anterior,
            },
            usuario=usuario
        )

        logger.info(f"[guardrails] Cliente {cliente_id} desbloqueado por {usuario}: {motivo}")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao desbloquear cliente: {e}")
        return False


async def resetar_circuit_breaker_global(
    circuit_name: str,
    motivo: str,
    usuario: str = "sistema"
) -> bool:
    """
    Sprint 36 - T06.3: Reseta um circuit breaker global.

    Args:
        circuit_name: Nome do circuit (evolution, claude, supabase)
        motivo: Motivo do reset
        usuario: Usuário que resetou

    Returns:
        True se sucesso
    """
    try:
        from app.services.circuit_breaker import (
            circuit_evolution,
            circuit_claude,
            circuit_supabase,
        )

        circuits = {
            "evolution": circuit_evolution,
            "claude": circuit_claude,
            "supabase": circuit_supabase,
        }

        circuit = circuits.get(circuit_name)
        if not circuit:
            logger.warning(f"[guardrails] Circuit não encontrado: {circuit_name}")
            return False

        estado_anterior = circuit.status()
        circuit.reset()

        await registrar_audit_trail(
            acao=AcaoAuditoria.CIRCUIT_BREAKER_RESET.value,
            entidade="circuit_breaker",
            entidade_id=circuit_name,
            detalhes={
                "motivo": motivo,
                "estado_anterior": estado_anterior,
            },
            usuario=usuario
        )

        logger.info(f"[guardrails] Circuit {circuit_name} resetado por {usuario}: {motivo}")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao resetar circuit breaker: {e}")
        return False


# ============================================================
# Modo Emergência
# ============================================================

async def ativar_modo_emergencia(
    motivo: str,
    usuario: str = "sistema",
    desabilitar_flags: Optional[List[FeatureFlag]] = None
) -> bool:
    """
    Sprint 36 - T06.1: Ativa modo de emergência.

    Desabilita todas as flags de envio por padrão.

    Args:
        motivo: Motivo da emergência
        usuario: Usuário que ativou
        desabilitar_flags: Flags específicas a desabilitar (default: envios)

    Returns:
        True se sucesso
    """
    if desabilitar_flags is None:
        desabilitar_flags = [
            FeatureFlag.ENVIO_PROSPECCAO,
            FeatureFlag.ENVIO_FOLLOWUP,
            FeatureFlag.ENVIO_CAMPANHA,
        ]

    try:
        for flag in desabilitar_flags:
            await definir_feature_flag(
                flag=flag,
                habilitada=False,
                motivo=f"EMERGÊNCIA: {motivo}",
                usuario=usuario
            )

        await registrar_audit_trail(
            acao=AcaoAuditoria.EMERGENCIA_ATIVADA.value,
            entidade="sistema",
            detalhes={
                "motivo": motivo,
                "flags_desabilitadas": [f.value for f in desabilitar_flags],
            },
            usuario=usuario
        )

        logger.critical(f"[guardrails] MODO EMERGÊNCIA ATIVADO por {usuario}: {motivo}")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao ativar modo emergência: {e}")
        return False


async def desativar_modo_emergencia(
    motivo: str,
    usuario: str = "sistema"
) -> bool:
    """
    Sprint 36 - T06.1: Desativa modo de emergência.

    Reabilita todas as flags de envio.

    Args:
        motivo: Motivo da desativação
        usuario: Usuário que desativou

    Returns:
        True se sucesso
    """
    flags_envio = [
        FeatureFlag.ENVIO_PROSPECCAO,
        FeatureFlag.ENVIO_FOLLOWUP,
        FeatureFlag.ENVIO_RESPOSTA,
        FeatureFlag.ENVIO_CAMPANHA,
    ]

    try:
        for flag in flags_envio:
            await definir_feature_flag(
                flag=flag,
                habilitada=True,
                motivo=f"Emergência desativada: {motivo}",
                usuario=usuario
            )

        logger.info(f"[guardrails] Modo emergência DESATIVADO por {usuario}: {motivo}")
        return True

    except Exception as e:
        logger.error(f"[guardrails] Erro ao desativar modo emergência: {e}")
        return False
