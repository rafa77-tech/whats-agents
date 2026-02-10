"""
Seletor de chips para entrada em grupos.

Sprint 25 - E12

Seleciona o chip ideal para entrar em um grupo, considerando:
- Tipo do chip (apenas listeners)
- Trust Score mínimo
- Limites por fase de warmup
- Distribuição de carga
- Circuit breaker
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# Limites por fase (backup caso não consiga ler config)
LIMITES_PADRAO = {
    "setup": {"dia": 0, "6h": 0, "delay": 0},
    "primeiros_contatos": {"dia": 0, "6h": 0, "delay": 0},
    "expansao": {"dia": 2, "6h": 2, "delay": 600},
    "pre_operacao": {"dia": 5, "6h": 3, "delay": 300},
    "operacao": {"dia": 10, "6h": 5, "delay": 180},
}


async def buscar_config() -> dict:
    """
    Busca configuração de limites do banco.

    Returns:
        Configuração de limites
    """
    result = supabase.table("group_entry_config").select("*").limit(1).execute()

    if not result.data:
        logger.warning("[ChipSelector] Config não encontrada, usando padrão")
        return {
            "trust_minimo": 70,
            "max_falhas": 3,
            "limites": LIMITES_PADRAO,
        }

    config = result.data[0]

    return {
        "trust_minimo": config.get("trust_minimo_grupos", 70),
        "max_falhas": config.get("max_falhas_consecutivas", 3),
        "limites": {
            "setup": {
                "dia": config.get("limite_setup", 0),
                "6h": 0,
                "delay": 0,
            },
            "primeiros_contatos": {
                "dia": config.get("limite_primeiros_contatos", 0),
                "6h": 0,
                "delay": 0,
            },
            "expansao": {
                "dia": config.get("limite_expansao", 2),
                "6h": config.get("limite_6h_expansao", 2),
                "delay": config.get("delay_min_expansao", 600),
            },
            "pre_operacao": {
                "dia": config.get("limite_pre_operacao", 5),
                "6h": config.get("limite_6h_pre_operacao", 3),
                "delay": config.get("delay_min_pre_operacao", 300),
            },
            "operacao": {
                "dia": config.get("limite_operacao", 10),
                "6h": config.get("limite_6h_operacao", 5),
                "delay": config.get("delay_min_operacao", 180),
            },
        },
        "janelas": {
            "expansao": {
                "inicio": config.get("hora_inicio_expansao", 12),
                "fim": config.get("hora_fim_expansao", 21),
            },
            "pre_operacao": {
                "inicio": config.get("hora_inicio_pre_op", 11),
                "fim": config.get("hora_fim_pre_op", 23),
            },
            "operacao": {
                "inicio": config.get("hora_inicio_op", 11),
                "fim": config.get("hora_fim_op", 24),
            },
        },
    }


async def listar_chips_disponiveis() -> List[dict]:
    """
    Lista chips disponíveis para entrada em grupos.

    Critérios:
    - tipo = 'listener'
    - status em (warming, ready, active)
    - circuit_breaker_ativo = false
    - trust_score >= mínimo configurado
    - fase permite entrada em grupos

    Returns:
        Lista de chips com slots disponíveis
    """
    config = await buscar_config()
    trust_minimo = config["trust_minimo"]
    limites = config["limites"]

    # Buscar chips listeners elegíveis
    result = (
        supabase.table("chips")
        .select("*")
        .eq("tipo", "listener")
        .in_("status", ["warming", "ready", "active"])
        .eq("circuit_breaker_ativo", False)
        .gte("trust_score", trust_minimo)
        .in_("fase_warmup", ["expansao", "pre_operacao", "operacao"])
        .execute()
    )

    if not result.data:
        return []

    chips_disponiveis = []

    for chip in result.data:
        fase = chip["fase_warmup"]
        limite_fase = limites.get(fase, {"dia": 0, "6h": 0})

        grupos_hoje = chip.get("grupos_hoje", 0)
        grupos_6h = chip.get("grupos_ultimas_6h", 0)

        slots_dia = limite_fase["dia"] - grupos_hoje
        slots_6h = limite_fase["6h"] - grupos_6h

        # Só inclui se tem slots disponíveis
        if slots_dia > 0 and slots_6h > 0:
            chips_disponiveis.append(
                {
                    **chip,
                    "slots_dia": slots_dia,
                    "slots_6h": slots_6h,
                    "delay_minimo": limite_fase.get("delay", 180),
                }
            )

    # Ordenar por:
    # 1. Maior trust score
    # 2. Menos grupos total (distribuir carga)
    # 3. Menos falhas recentes
    chips_disponiveis.sort(
        key=lambda c: (
            -c["trust_score"],
            c.get("grupos_count", 0),
            c.get("grupos_falhas_consecutivas", 0),
        )
    )

    return chips_disponiveis


async def selecionar_chip_para_grupo() -> Optional[dict]:
    """
    Seleciona o melhor chip para entrar em um grupo.

    Returns:
        Chip selecionado ou None se nenhum disponível
    """
    chips = await listar_chips_disponiveis()

    if not chips:
        logger.warning("[ChipSelector] Nenhum chip disponível para entrada em grupo")
        return None

    # Selecionar o primeiro (já ordenado por prioridade)
    chip = chips[0]

    # Verificar delay mínimo desde última entrada
    ultimo_grupo = chip.get("ultimo_grupo_entrada")
    if ultimo_grupo:
        ultimo = datetime.fromisoformat(ultimo_grupo.replace("Z", "+00:00"))
        delay_minimo = chip.get("delay_minimo", 180)
        proximo_permitido = ultimo + timedelta(seconds=delay_minimo)

        if datetime.now(UTC) < proximo_permitido:
            # Tentar próximo chip
            for alt_chip in chips[1:]:
                ultimo_alt = alt_chip.get("ultimo_grupo_entrada")
                if not ultimo_alt:
                    return alt_chip

                ultimo_alt_dt = datetime.fromisoformat(ultimo_alt.replace("Z", "+00:00"))
                delay_alt = alt_chip.get("delay_minimo", 180)
                proximo_alt = ultimo_alt_dt + timedelta(seconds=delay_alt)

                if datetime.now(UTC) >= proximo_alt:
                    return alt_chip

            # Nenhum chip respeitando delay
            logger.info(
                f"[ChipSelector] Todos os chips em cooldown de delay. "
                f"Próximo disponível em {(proximo_permitido - datetime.now(UTC)).seconds}s"
            )
            return None

    logger.info(
        f"[ChipSelector] Chip selecionado: {chip['telefone']} "
        f"(trust={chip['trust_score']}, fase={chip['fase_warmup']}, "
        f"slots_dia={chip['slots_dia']}, slots_6h={chip['slots_6h']})"
    )

    return chip


async def verificar_janela_horaria(fase: str) -> bool:
    """
    Verifica se estamos na janela horária permitida para a fase.

    Args:
        fase: Fase de warmup

    Returns:
        True se dentro da janela
    """
    config = await buscar_config()
    janelas = config.get("janelas", {})

    janela = janelas.get(fase)
    if not janela:
        return False

    hora_atual = datetime.now(UTC).hour

    # Ajustar para BRT (UTC-3)
    hora_brt = (hora_atual - 3) % 24

    return janela["inicio"] <= hora_brt < janela["fim"]


async def registrar_entrada_sucesso(chip_id: str, grupo_jid: str) -> None:
    """
    Registra entrada bem-sucedida em grupo.

    Args:
        chip_id: ID do chip
        grupo_jid: JID do grupo
    """
    # Atualizar contadores do chip
    supabase.rpc(
        "incrementar_grupos_chip",
        {"p_chip_id": chip_id},
    ).execute()

    # Ou fazer manualmente se a função não existir
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if result.data:
        chip = result.data
        supabase.table("chips").update(
            {
                "grupos_count": (chip.get("grupos_count") or 0) + 1,
                "grupos_hoje": (chip.get("grupos_hoje") or 0) + 1,
                "grupos_ultimas_6h": (chip.get("grupos_ultimas_6h") or 0) + 1,
                "ultimo_grupo_entrada": datetime.now(UTC).isoformat(),
                "grupos_falhas_consecutivas": 0,  # Reset falhas
            }
        ).eq("id", chip_id).execute()

    # Registrar métrica diária
    hoje = datetime.now(UTC).date().isoformat()
    supabase.table("chip_group_metrics").upsert(
        {
            "chip_id": chip_id,
            "data": hoje,
            "sucessos": 1,
        },
        on_conflict="chip_id,data",
    ).execute()

    logger.info(f"[ChipSelector] Entrada registrada: chip={chip_id}, grupo={grupo_jid}")


async def registrar_entrada_falha(chip_id: str, erro: str) -> None:
    """
    Registra falha na entrada em grupo.

    Args:
        chip_id: ID do chip
        erro: Mensagem de erro
    """
    result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

    if not result.data:
        return

    chip = result.data
    falhas = (chip.get("grupos_falhas_consecutivas") or 0) + 1

    # Buscar config para max falhas
    config = await buscar_config()
    max_falhas = config.get("max_falhas", 3)

    update_data = {
        "grupos_falhas_consecutivas": falhas,
    }

    # Ativar circuit breaker se excedeu limite
    if falhas >= max_falhas:
        update_data["circuit_breaker_ativo"] = True
        update_data["circuit_breaker_desde"] = datetime.now(UTC).isoformat()
        logger.warning(
            f"[ChipSelector] Circuit breaker ativado para chip {chip_id} "
            f"após {falhas} falhas consecutivas"
        )

    supabase.table("chips").update(update_data).eq("id", chip_id).execute()

    # Registrar métrica diária
    hoje = datetime.now(UTC).date().isoformat()
    supabase.table("chip_group_metrics").upsert(
        {
            "chip_id": chip_id,
            "data": hoje,
            "erros": 1,
        },
        on_conflict="chip_id,data",
    ).execute()

    logger.info(f"[ChipSelector] Falha registrada: chip={chip_id}, erro={erro}")


async def capacidade_total_disponivel() -> dict:
    """
    Calcula capacidade total disponível para entrada em grupos.

    Returns:
        {
            "chips_disponiveis": N,
            "slots_dia_total": N,
            "slots_6h_total": N,
        }
    """
    chips = await listar_chips_disponiveis()

    return {
        "chips_disponiveis": len(chips),
        "slots_dia_total": sum(c["slots_dia"] for c in chips),
        "slots_6h_total": sum(c["slots_6h"] for c in chips),
    }
