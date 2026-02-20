"""
Warmup Executor - Executa atividades de warmup agendadas.

Sprint 39 - Scheduler de Warmup.
Sprint 56 - Usa ChipSender para capturar erros corretamente.

Responsável por executar cada tipo de atividade:
- conversa_par: Conversa entre dois chips
- marcar_lido: Marcar mensagens como lidas
- entrar_grupo: Entrar em grupo WhatsApp
- mensagem_grupo: Enviar mensagem em grupo
- atualizar_perfil: Atualizar foto/status
- enviar_midia: Enviar mídia (imagem/áudio)
"""

import logging
import random
from typing import Optional

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.warmer.scheduler import AtividadeAgendada, TipoAtividade
from app.services.warmer.conversation_generator import gerar_mensagem_inicial
from app.services.warmer.pairing_engine import encontrar_par
from app.services.chips.sender import enviar_via_chip

logger = logging.getLogger(__name__)


async def executar_atividade(atividade: AtividadeAgendada) -> bool:
    """
    Executa uma atividade de warmup.

    Args:
        atividade: Atividade a ser executada

    Returns:
        True se executada com sucesso, False caso contrário
    """
    try:
        logger.info(
            f"[WarmupExecutor] Executando {atividade.tipo.value} "
            f"para chip {atividade.chip_id[:8]}..."
        )

        # Buscar dados do chip
        chip = await _buscar_chip(atividade.chip_id)
        if not chip:
            logger.error(f"[WarmupExecutor] Chip {atividade.chip_id} não encontrado")
            return False

        # Executar baseado no tipo
        match atividade.tipo:
            case TipoAtividade.CONVERSA_PAR:
                return await _executar_conversa_par(chip, atividade)

            case TipoAtividade.MARCAR_LIDO:
                return await _executar_marcar_lido(chip)

            case TipoAtividade.ENTRAR_GRUPO:
                return await _executar_entrar_grupo(chip)

            case TipoAtividade.MENSAGEM_GRUPO:
                return await _executar_mensagem_grupo(chip)

            case TipoAtividade.ATUALIZAR_PERFIL:
                return await _executar_atualizar_perfil(chip)

            case TipoAtividade.ENVIAR_MIDIA:
                return await _executar_enviar_midia(chip, atividade)

            case _:
                logger.warning(f"[WarmupExecutor] Tipo desconhecido: {atividade.tipo}")
                return False

    except Exception as e:
        logger.error(f"[WarmupExecutor] Erro ao executar atividade: {e}")
        return False


async def _buscar_chip(chip_id: str) -> Optional[dict]:
    """Busca dados completos de um chip."""
    result = (
        supabase.table("chips")
        .select("id, telefone, instance_name, evolution_connected, fase_warmup, provider")
        .eq("id", chip_id)
        .single()
        .execute()
    )

    return result.data


async def _executar_conversa_par(chip: dict, atividade: AtividadeAgendada) -> bool:
    """
    Executa conversa entre dois chips.

    Seleciona um par, gera mensagem contextual e envia.
    Sprint 56: Usa enviar_via_chip para capturar erros corretamente.
    """
    try:
        # Verificar conexão (para Evolution)
        # Para Z-API, não verifica evolution_connected
        provider_tipo = chip.get("provider") or "evolution"
        if provider_tipo == "evolution" and not chip.get("evolution_connected"):
            logger.warning(f"[WarmupExecutor] Chip {chip['telefone']} desconectado")
            return False

        # Selecionar par para conversa
        par_info = await encontrar_par(chip["id"])
        if not par_info:
            logger.warning(f"[WarmupExecutor] Nenhum par disponível para {chip['telefone']}")
            # Fallback: marcar como lido
            return await _executar_marcar_lido(chip)

        par_telefone = par_info.chip_b.telefone

        # Gerar mensagem de warmup
        msg_gerada = gerar_mensagem_inicial(fase_warmup=chip.get("fase_warmup", "setup"))
        mensagem = msg_gerada.texto if msg_gerada else _gerar_mensagem_simples()

        # Sprint 56: Usar enviar_via_chip para capturar erros corretamente
        # Isso garante que erros são registrados via chip_registrar_envio_erro
        resultado = await enviar_via_chip(chip, par_telefone, mensagem)

        if resultado.success:
            logger.info(
                f"[WarmupExecutor] Conversa par: {chip['telefone'][-4:]} -> {par_telefone[-4:]}"
            )
            return True

        # Erro já foi registrado pelo enviar_via_chip
        logger.warning(f"[WarmupExecutor] Falha ao enviar conversa_par: {resultado.error}")
        return False

    except Exception as e:
        logger.error(f"[WarmupExecutor] Erro em conversa_par: {e}")
        return False


async def _executar_marcar_lido(chip: dict) -> bool:
    """
    Marca mensagens como lidas.

    Simula comportamento humano de verificar WhatsApp.
    Na prática, apenas registra a atividade (WhatsApp não tem API para "marcar lido").
    """
    try:
        provider_tipo = chip.get("provider") or "evolution"
        if provider_tipo == "evolution" and not chip.get("evolution_connected"):
            return False

        # Registrar atividade de "verificação"
        await _registrar_interacao(chip["id"], "marcar_lido", sucesso=True)
        logger.debug(f"[WarmupExecutor] Leitura marcada: {chip['telefone'][-4:]}")
        return True

    except Exception as e:
        logger.error(f"[WarmupExecutor] Erro em marcar_lido: {e}")
        return False


async def _executar_entrar_grupo(chip: dict) -> bool:
    """
    Entra em um grupo WhatsApp.

    Nota: Stub — requer link de convite válido. Retorna False para não
    inflar métricas de progresso enquanto não estiver implementado.
    """
    logger.debug(f"[WarmupExecutor] entrar_grupo não implementado, skip {chip['telefone'][-4:]}")
    return False


async def _executar_mensagem_grupo(chip: dict) -> bool:
    """
    Envia mensagem em grupo.

    Nota: Stub — requer grupo ativo. Retorna False para não
    inflar métricas de progresso enquanto não estiver implementado.
    """
    logger.debug(f"[WarmupExecutor] mensagem_grupo não implementado, skip {chip['telefone'][-4:]}")
    return False


async def _executar_atualizar_perfil(chip: dict) -> bool:
    """
    Atualiza perfil do WhatsApp (foto, status, nome).

    Nota: Stub — requer integração com Evolution API. Retorna False para não
    inflar métricas de progresso enquanto não estiver implementado.
    """
    logger.debug(
        f"[WarmupExecutor] atualizar_perfil não implementado, skip {chip['telefone'][-4:]}"
    )
    return False


async def _executar_enviar_midia(chip: dict, atividade: AtividadeAgendada) -> bool:
    """
    Envia mídia (imagem/áudio).

    Nota: Requer mídia disponível. Por enquanto, faz fallback para conversa_par.
    """
    try:
        # Fallback: enviar conversa_par (mais seguro)
        logger.info(
            f"[WarmupExecutor] enviar_midia -> fallback conversa_par para {chip['telefone'][-4:]}"
        )
        return await _executar_conversa_par(chip, atividade)

    except Exception as e:
        logger.error(f"[WarmupExecutor] Erro em enviar_midia: {e}")
        return False


async def _registrar_interacao(
    chip_id: str,
    tipo: str,
    destinatario: str = None,
    sucesso: bool = True,
    simulada: bool = False,
) -> None:
    """Registra interação na tabela chip_interactions."""
    try:
        supabase.table("chip_interactions").insert(
            {
                "chip_id": chip_id,
                "tipo": "msg_enviada"
                if tipo in ["conversa_par", "mensagem_grupo"]
                else "status_criado",
                "destinatario": destinatario,
                "metadata": {
                    "tipo_warmup": tipo,
                    "sucesso": sucesso,
                    "simulada": simulada,
                    "timestamp": agora_brasilia().isoformat(),
                },
                "created_at": agora_brasilia().isoformat(),
            }
        ).execute()
    except Exception as e:
        logger.warning(f"[WarmupExecutor] Erro ao registrar interação: {e}")


def _gerar_mensagem_simples() -> str:
    """Gera mensagem simples de warmup para fallback."""
    mensagens = [
        "oi, tudo bem?",
        "bom dia!",
        "opa, como vai?",
        "e aí, tranquilo?",
        "oi! como está?",
        "olá, tudo certo?",
        "boa tarde!",
        "hey, blz?",
    ]
    return random.choice(mensagens)
