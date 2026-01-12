"""
Worker de entrada em grupos.

Sprint 25 - E12 - S12.4

Processa a fila de entrada em grupos:
- Seleciona chip adequado
- Simula comportamento humano
- Entra no grupo via Evolution API
- Registra métricas e telemetria
"""

import logging
import asyncio
from typing import Optional
from datetime import datetime, UTC

from app.services.supabase import supabase
from app.services.whatsapp import EvolutionClient
from app.services.group_entry.chip_selector import (
    selecionar_chip_para_grupo,
    registrar_entrada_sucesso,
    registrar_entrada_falha,
    verificar_janela_horaria,
)
from app.services.group_entry.scheduler import reagendar_com_erro
from app.services.warmer.human_simulator import HumanSimulator

logger = logging.getLogger(__name__)


async def processar_fila(limite: int = 5) -> dict:
    """
    Processa entradas pendentes na fila.

    Args:
        limite: Quantidade máxima a processar

    Returns:
        {
            "processados": N,
            "sucesso": N,
            "aguardando": N,
            "erros": N,
        }
    """
    agora = datetime.now(UTC)

    # Buscar entradas pendentes cujo horário já passou
    result = (
        supabase.table("group_entry_queue")
        .select("*, group_links(*)")
        .eq("status", "pendente")
        .lte("agendado_para", agora.isoformat())
        .order("prioridade", desc=True)
        .order("agendado_para")
        .limit(limite)
        .execute()
    )

    if not result.data:
        logger.debug("[Worker] Nenhuma entrada pendente para processar")
        return {"processados": 0, "sucesso": 0, "aguardando": 0, "erros": 0}

    entradas = result.data
    resultado = {"processados": 0, "sucesso": 0, "aguardando": 0, "erros": 0}

    for entrada in entradas:
        try:
            status = await processar_entrada(entrada["id"])
            resultado["processados"] += 1

            if status == "sucesso":
                resultado["sucesso"] += 1
            elif status == "aguardando":
                resultado["aguardando"] += 1
            else:
                resultado["erros"] += 1

        except Exception as e:
            logger.error(f"[Worker] Erro ao processar entrada {entrada['id']}: {e}")
            resultado["erros"] += 1

    logger.info(
        f"[Worker] Processamento concluído: "
        f"{resultado['sucesso']} sucesso, "
        f"{resultado['aguardando']} aguardando, "
        f"{resultado['erros']} erros"
    )

    return resultado


async def processar_entrada(queue_id: str) -> str:
    """
    Processa uma entrada específica.

    Args:
        queue_id: ID na fila

    Returns:
        Status: 'sucesso', 'aguardando', 'erro'
    """
    # Buscar entrada
    result = (
        supabase.table("group_entry_queue")
        .select("*, group_links(*)")
        .eq("id", queue_id)
        .single()
        .execute()
    )

    if not result.data:
        logger.warning(f"[Worker] Entrada não encontrada: {queue_id}")
        return "erro"

    entrada = result.data
    link = entrada.get("group_links", {})
    invite_code = link.get("invite_code")

    if not invite_code:
        logger.warning(f"[Worker] Link sem invite_code: {queue_id}")
        return "erro"

    # Marcar como processando
    supabase.table("group_entry_queue").update(
        {"status": "processando"}
    ).eq("id", queue_id).execute()

    supabase.table("group_links").update(
        {"status": "em_progresso"}
    ).eq("id", link["id"]).execute()

    # Selecionar chip
    chip_id = entrada.get("chip_id")

    if chip_id:
        # Usar chip específico
        chip_result = (
            supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        )
        chip = chip_result.data
    else:
        # Selecionar melhor chip disponível
        chip = await selecionar_chip_para_grupo()

    if not chip:
        logger.warning(f"[Worker] Nenhum chip disponível para {queue_id}")
        await reagendar_com_erro(queue_id, "Nenhum chip disponível")
        return "erro"

    # Verificar janela horária
    if not await verificar_janela_horaria(chip["fase_warmup"]):
        logger.info(f"[Worker] Fora da janela horária para fase {chip['fase_warmup']}")
        await reagendar_com_erro(queue_id, "Fora da janela horária")
        return "erro"

    # Simular comportamento humano antes de entrar
    simulator = HumanSimulator()
    await simulator.simular_delay_pre_acao()

    # Tentar entrar no grupo
    inicio = datetime.now(UTC)
    client = EvolutionClient(instance=chip["instance_name"])

    try:
        resultado = await client.entrar_grupo_por_invite(invite_code)

        latencia = (datetime.now(UTC) - inicio).total_seconds()

        # Registrar telemetria
        await _registrar_telemetria(chip["id"], latencia, True, None)

        if resultado.get("sucesso"):
            # Entrada bem-sucedida
            grupo_jid = resultado.get("jid")

            await registrar_entrada_sucesso(chip["id"], grupo_jid)

            supabase.table("group_entry_queue").update(
                {
                    "status": "concluido",
                    "resultado": "sucesso",
                    "processado_em": datetime.now(UTC).isoformat(),
                    "chip_id": chip["id"],
                }
            ).eq("id", queue_id).execute()

            supabase.table("group_links").update(
                {
                    "status": "sucesso",
                    "grupo_jid": grupo_jid,
                    "chip_id": chip["id"],
                    "processado_em": datetime.now(UTC).isoformat(),
                }
            ).eq("id", link["id"]).execute()

            logger.info(
                f"[Worker] Entrada bem-sucedida: {invite_code} -> {grupo_jid} "
                f"(chip={chip['telefone']}, latência={latencia:.2f}s)"
            )

            return "sucesso"

        elif resultado.get("aguardando_aprovacao"):
            # Precisa aprovação do admin
            supabase.table("group_entry_queue").update(
                {
                    "status": "concluido",
                    "resultado": "aguardando_aprovacao",
                    "processado_em": datetime.now(UTC).isoformat(),
                    "chip_id": chip["id"],
                }
            ).eq("id", queue_id).execute()

            supabase.table("group_links").update(
                {
                    "status": "aguardando",
                    "chip_id": chip["id"],
                    "processado_em": datetime.now(UTC).isoformat(),
                }
            ).eq("id", link["id"]).execute()

            logger.info(
                f"[Worker] Aguardando aprovação: {invite_code} "
                f"(chip={chip['telefone']})"
            )

            return "aguardando"

        else:
            # Erro na entrada
            erro = resultado.get("erro", "Erro desconhecido")
            await registrar_entrada_falha(chip["id"], erro)
            await _registrar_telemetria(chip["id"], latencia, False, erro)

            reagendado = await reagendar_com_erro(queue_id, erro)

            if not reagendado:
                logger.warning(f"[Worker] Entrada falhou definitivamente: {invite_code}")

            return "erro"

    except Exception as e:
        latencia = (datetime.now(UTC) - inicio).total_seconds()
        erro = str(e)

        await registrar_entrada_falha(chip["id"], erro)
        await _registrar_telemetria(chip["id"], latencia, False, erro)

        logger.error(f"[Worker] Exceção ao entrar em {invite_code}: {e}")

        await reagendar_com_erro(queue_id, erro)

        return "erro"


async def _registrar_telemetria(
    chip_id: str,
    latencia: float,
    sucesso: bool,
    erro: Optional[str],
) -> None:
    """
    Registra telemetria de entrada.

    Args:
        chip_id: ID do chip
        latencia: Latência em segundos
        sucesso: Se foi bem-sucedido
        erro: Mensagem de erro (se houver)
    """
    try:
        supabase.table("group_entry_telemetry").insert(
            {
                "chip_id": chip_id,
                "latencia_segundos": round(latencia, 2),
                "sucesso": sucesso,
                "erro": erro,
            }
        ).execute()
    except Exception as e:
        logger.warning(f"[Worker] Erro ao registrar telemetria: {e}")


async def verificar_entradas_aguardando() -> dict:
    """
    Verifica status de entradas aguardando aprovação.

    Consulta a Evolution API para ver se a aprovação foi concedida.

    Returns:
        {
            "verificados": N,
            "aprovados": N,
            "rejeitados": N,
            "ainda_aguardando": N,
        }
    """
    result = (
        supabase.table("group_links")
        .select("*, chips(*)")
        .eq("status", "aguardando")
        .execute()
    )

    if not result.data:
        return {
            "verificados": 0,
            "aprovados": 0,
            "rejeitados": 0,
            "ainda_aguardando": 0,
        }

    links = result.data
    resultado = {
        "verificados": 0,
        "aprovados": 0,
        "rejeitados": 0,
        "ainda_aguardando": 0,
    }

    for link in links:
        chip = link.get("chips")
        if not chip:
            continue

        resultado["verificados"] += 1

        try:
            client = EvolutionClient(instance=chip["instance_name"])

            # Verificar se estamos no grupo
            grupos = await client.listar_grupos()

            # Procurar pelo grupo com o invite code
            grupo_encontrado = None
            for grupo in grupos:
                if link.get("grupo_jid") and grupo.get("id") == link["grupo_jid"]:
                    grupo_encontrado = grupo
                    break

            if grupo_encontrado:
                # Aprovação concedida!
                supabase.table("group_links").update(
                    {
                        "status": "sucesso",
                        "grupo_jid": grupo_encontrado["id"],
                    }
                ).eq("id", link["id"]).execute()

                await registrar_entrada_sucesso(chip["id"], grupo_encontrado["id"])
                resultado["aprovados"] += 1

                logger.info(
                    f"[Worker] Aprovação concedida: {link['invite_code']} -> "
                    f"{grupo_encontrado['id']}"
                )
            else:
                resultado["ainda_aguardando"] += 1

        except Exception as e:
            logger.warning(
                f"[Worker] Erro ao verificar aprovação {link['invite_code']}: {e}"
            )
            resultado["ainda_aguardando"] += 1

    return resultado


async def executar_ciclo_worker() -> dict:
    """
    Executa um ciclo completo do worker.

    Usado pelo scheduler (APScheduler) para rodar periodicamente.

    Returns:
        Resultado consolidado
    """
    # 1. Processar fila principal
    resultado_fila = await processar_fila(limite=5)

    # 2. Verificar entradas aguardando aprovação
    resultado_aguardando = await verificar_entradas_aguardando()

    return {
        "fila": resultado_fila,
        "aguardando": resultado_aguardando,
    }
