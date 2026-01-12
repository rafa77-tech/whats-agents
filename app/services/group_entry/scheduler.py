"""
Scheduler de entrada em grupos.

Sprint 25 - E12 - S12.3

Agenda entradas em grupos respeitando:
- Limites por fase de warmup
- Janelas horárias
- Delays mínimos entre entradas
- Distribuição entre chips
"""

import logging
import random
from typing import Optional, List
from datetime import datetime, UTC, timedelta

from app.services.supabase import supabase
from app.services.group_entry.chip_selector import (
    buscar_config,
    listar_chips_disponiveis,
    verificar_janela_horaria,
    capacidade_total_disponivel,
)

logger = logging.getLogger(__name__)


async def agendar_entrada(
    link_id: str,
    prioridade: int = 50,
    chip_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Agenda entrada em um grupo específico.

    Args:
        link_id: ID do link na tabela group_links
        prioridade: Prioridade (1-100, maior = mais urgente)
        chip_id: ID do chip específico (opcional)

    Returns:
        Entrada agendada ou None se não foi possível
    """
    # Verificar se link existe e está validado
    result = (
        supabase.table("group_links").select("*").eq("id", link_id).single().execute()
    )

    if not result.data:
        logger.warning(f"[Scheduler] Link não encontrado: {link_id}")
        return None

    link = result.data

    if link["status"] not in ("validado", "erro"):
        logger.warning(
            f"[Scheduler] Link {link_id} não está validado (status={link['status']})"
        )
        return None

    # Verificar se já está na fila
    fila_result = (
        supabase.table("group_entry_queue")
        .select("id")
        .eq("link_id", link_id)
        .in_("status", ["pendente", "processando"])
        .execute()
    )

    if fila_result.data:
        logger.info(f"[Scheduler] Link {link_id} já está na fila")
        return None

    # Calcular próximo horário disponível
    proximo_horario = await _calcular_proximo_horario(chip_id)

    if not proximo_horario:
        logger.warning("[Scheduler] Não foi possível calcular próximo horário")
        return None

    # Criar entrada na fila
    entrada = {
        "link_id": link_id,
        "chip_id": chip_id,
        "prioridade": prioridade,
        "agendado_para": proximo_horario.isoformat(),
        "status": "pendente",
    }

    result = supabase.table("group_entry_queue").insert(entrada).execute()

    if result.data:
        # Atualizar status do link
        supabase.table("group_links").update(
            {
                "status": "agendado",
                "agendado_em": datetime.now(UTC).isoformat(),
            }
        ).eq("id", link_id).execute()

        logger.info(
            f"[Scheduler] Entrada agendada: link={link_id}, "
            f"horário={proximo_horario.isoformat()}"
        )

        return result.data[0]

    return None


async def agendar_lote(
    limite: int = 10,
    categoria: Optional[str] = None,
) -> dict:
    """
    Agenda lote de links validados para entrada.

    Args:
        limite: Quantidade máxima a agendar
        categoria: Filtrar por categoria (opcional)

    Returns:
        {
            "agendados": N,
            "ja_na_fila": N,
            "sem_capacidade": N,
        }
    """
    # Verificar capacidade disponível
    capacidade = await capacidade_total_disponivel()

    if capacidade["slots_6h_total"] == 0:
        logger.info("[Scheduler] Sem capacidade disponível no momento")
        return {"agendados": 0, "ja_na_fila": 0, "sem_capacidade": limite}

    # Ajustar limite pela capacidade
    limite_real = min(limite, capacidade["slots_6h_total"])

    # Buscar links validados
    query = (
        supabase.table("group_links")
        .select("*")
        .eq("status", "validado")
    )

    if categoria:
        query = query.eq("categoria", categoria)

    result = query.order("created_at").limit(limite_real).execute()

    if not result.data:
        logger.info("[Scheduler] Nenhum link validado para agendar")
        return {"agendados": 0, "ja_na_fila": 0, "sem_capacidade": 0}

    links = result.data
    resultado = {"agendados": 0, "ja_na_fila": 0, "sem_capacidade": 0}

    for link in links:
        entrada = await agendar_entrada(link["id"])

        if entrada:
            resultado["agendados"] += 1
        else:
            # Verificar se já está na fila
            fila_check = (
                supabase.table("group_entry_queue")
                .select("id")
                .eq("link_id", link["id"])
                .in_("status", ["pendente", "processando"])
                .execute()
            )

            if fila_check.data:
                resultado["ja_na_fila"] += 1
            else:
                resultado["sem_capacidade"] += 1

    logger.info(
        f"[Scheduler] Lote agendado: {resultado['agendados']} entradas, "
        f"{resultado['ja_na_fila']} já na fila, "
        f"{resultado['sem_capacidade']} sem capacidade"
    )

    return resultado


async def _calcular_proximo_horario(chip_id: Optional[str] = None) -> Optional[datetime]:
    """
    Calcula próximo horário disponível para entrada.

    Considera:
    - Janela horária da fase
    - Delay mínimo desde última entrada
    - Randomização para parecer humano

    Args:
        chip_id: ID do chip específico (opcional)

    Returns:
        Próximo horário ou None
    """
    config = await buscar_config()

    # Buscar chips disponíveis
    if chip_id:
        result = (
            supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        )
        chips = [result.data] if result.data else []
    else:
        chips = await listar_chips_disponiveis()

    if not chips:
        return None

    # Pegar o primeiro chip disponível
    chip = chips[0]
    fase = chip["fase_warmup"]

    # Buscar delay mínimo da config
    limites = config.get("limites", {}).get(fase, {})
    delay_minimo = limites.get("delay", 180)

    # Adicionar randomização (10-50% extra)
    delay_random = delay_minimo + random.randint(
        int(delay_minimo * 0.1), int(delay_minimo * 0.5)
    )

    # Calcular horário base
    agora = datetime.now(UTC)
    proximo = agora + timedelta(seconds=delay_random)

    # Verificar última entrada do chip
    ultimo_grupo = chip.get("ultimo_grupo_entrada")
    if ultimo_grupo:
        ultimo = datetime.fromisoformat(ultimo_grupo.replace("Z", "+00:00"))
        minimo_desde_ultimo = ultimo + timedelta(seconds=delay_random)

        if minimo_desde_ultimo > proximo:
            proximo = minimo_desde_ultimo

    # Verificar janela horária
    janelas = config.get("janelas", {}).get(fase, {})
    hora_inicio = janelas.get("inicio", 11)
    hora_fim = janelas.get("fim", 23)

    # Ajustar para janela (considerando UTC-3 para BRT)
    hora_proximo_brt = (proximo.hour - 3) % 24

    if hora_proximo_brt < hora_inicio:
        # Aguardar início da janela
        horas_ate_inicio = hora_inicio - hora_proximo_brt
        proximo = proximo + timedelta(hours=horas_ate_inicio)

    elif hora_proximo_brt >= hora_fim:
        # Agendar para próximo dia
        horas_ate_proximo_inicio = (24 - hora_proximo_brt) + hora_inicio
        proximo = proximo + timedelta(hours=horas_ate_proximo_inicio)

    return proximo


async def buscar_proximas_entradas(limite: int = 10) -> List[dict]:
    """
    Busca próximas entradas agendadas.

    Args:
        limite: Quantidade máxima

    Returns:
        Lista de entradas pendentes
    """
    result = (
        supabase.table("group_entry_queue")
        .select("*, group_links(*), chips(*)")
        .eq("status", "pendente")
        .order("agendado_para")
        .limit(limite)
        .execute()
    )

    return result.data or []


async def cancelar_agendamento(queue_id: str) -> bool:
    """
    Cancela um agendamento específico.

    Args:
        queue_id: ID na fila

    Returns:
        True se cancelado
    """
    result = (
        supabase.table("group_entry_queue")
        .select("*, link_id")
        .eq("id", queue_id)
        .single()
        .execute()
    )

    if not result.data:
        return False

    entrada = result.data

    # Atualizar fila
    supabase.table("group_entry_queue").update(
        {"status": "cancelado"}
    ).eq("id", queue_id).execute()

    # Reverter status do link
    supabase.table("group_links").update(
        {"status": "validado", "agendado_em": None}
    ).eq("id", entrada["link_id"]).execute()

    logger.info(f"[Scheduler] Agendamento cancelado: {queue_id}")

    return True


async def reagendar_com_erro(queue_id: str, erro: str) -> bool:
    """
    Reagenda entrada que falhou.

    Args:
        queue_id: ID na fila
        erro: Mensagem de erro

    Returns:
        True se reagendado, False se desistiu
    """
    result = (
        supabase.table("group_entry_queue")
        .select("*, group_links(tentativas, max_tentativas)")
        .eq("id", queue_id)
        .single()
        .execute()
    )

    if not result.data:
        return False

    entrada = result.data
    link_info = entrada.get("group_links", {})
    tentativas = link_info.get("tentativas", 0) + 1
    max_tentativas = link_info.get("max_tentativas", 3)

    if tentativas >= max_tentativas:
        # Desistir
        supabase.table("group_entry_queue").update(
            {"status": "erro", "erro": erro}
        ).eq("id", queue_id).execute()

        supabase.table("group_links").update(
            {
                "status": "desistido",
                "tentativas": tentativas,
                "ultimo_erro": erro,
            }
        ).eq("id", entrada["link_id"]).execute()

        logger.warning(
            f"[Scheduler] Desistindo após {tentativas} tentativas: {entrada['link_id']}"
        )
        return False

    # Reagendar com backoff exponencial
    delay_base = 300  # 5 minutos
    delay_backoff = delay_base * (2 ** tentativas)  # 5min, 10min, 20min...
    proximo = datetime.now(UTC) + timedelta(seconds=delay_backoff)

    supabase.table("group_entry_queue").update(
        {
            "status": "pendente",
            "agendado_para": proximo.isoformat(),
            "erro": erro,
        }
    ).eq("id", queue_id).execute()

    supabase.table("group_links").update(
        {
            "status": "erro",
            "tentativas": tentativas,
            "ultimo_erro": erro,
            "proxima_tentativa": proximo.isoformat(),
        }
    ).eq("id", entrada["link_id"]).execute()

    logger.info(
        f"[Scheduler] Reagendado para {proximo.isoformat()} "
        f"(tentativa {tentativas}/{max_tentativas})"
    )

    return True


async def estatisticas_fila() -> dict:
    """
    Retorna estatísticas da fila de entrada.

    Returns:
        Estatísticas consolidadas
    """
    # Contar por status
    result = supabase.table("group_entry_queue").select("status").execute()

    if not result.data:
        return {
            "total": 0,
            "pendentes": 0,
            "processando": 0,
            "concluidos": 0,
            "erros": 0,
            "cancelados": 0,
        }

    contagem = {
        "pendente": 0,
        "processando": 0,
        "concluido": 0,
        "erro": 0,
        "cancelado": 0,
    }

    for row in result.data:
        status = row["status"]
        contagem[status] = contagem.get(status, 0) + 1

    return {
        "total": len(result.data),
        "pendentes": contagem["pendente"],
        "processando": contagem["processando"],
        "concluidos": contagem["concluido"],
        "erros": contagem["erro"],
        "cancelados": contagem["cancelado"],
    }
