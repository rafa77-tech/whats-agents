"""
Service para envio de primeira mensagem de prospecao.

Sprint 10 - S10.E3.1
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase
from app.services.agente import gerar_resposta_julia, enviar_resposta
from app.services.contexto import montar_contexto_completo
from app.services.interacao import salvar_interacao
from app.services.optout import verificar_opted_out
from app.services.chatwoot import sincronizar_ids_chatwoot
from app.services.guardrails import (
    check_outbound_guardrails,
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
)

logger = logging.getLogger(__name__)


@dataclass
class ResultadoPrimeiraMensagem:
    """Resultado do envio de primeira mensagem."""
    sucesso: bool
    cliente_nome: Optional[str] = None
    cliente_id: Optional[str] = None
    conversa_id: Optional[str] = None
    mensagem_enviada: Optional[str] = None
    resultado_envio: Optional[dict] = None
    erro: Optional[str] = None
    opted_out: bool = False


async def enviar_primeira_mensagem(telefone: str) -> ResultadoPrimeiraMensagem:
    """
    Envia primeira mensagem de prospecao para um medico.

    Args:
        telefone: Numero do medico (ex: 5511999999999)

    Returns:
        ResultadoPrimeiraMensagem com status e detalhes
    """
    try:
        # 1. Buscar ou criar cliente
        cliente = await _obter_ou_criar_cliente(telefone)
        logger.info(f"Cliente: {cliente.get('primeiro_nome', 'N/A')} ({cliente['id']})")

        # 2. GUARDRAIL: Verificar ANTES de gerar texto
        ctx = OutboundContext(
            cliente_id=cliente["id"],
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.SLACK,  # Vem de comando Slack
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        guardrail_result = await check_outbound_guardrails(ctx)

        if guardrail_result.is_blocked:
            logger.info(f"Cliente {cliente['id']} bloqueado: {guardrail_result.reason_code}")
            return ResultadoPrimeiraMensagem(
                sucesso=False,
                cliente_nome=cliente.get("primeiro_nome"),
                cliente_id=cliente["id"],
                erro=f"Guardrail: {guardrail_result.reason_code}",
                opted_out=guardrail_result.reason_code == "opted_out"
            )

        # 3. Criar ou buscar conversa ativa
        conversa = await _obter_ou_criar_conversa(cliente["id"])
        logger.info(f"Conversa: {conversa['id']}")

        # 4. Montar contexto
        contexto = await montar_contexto_completo(cliente, conversa)

        # 5. Gerar primeira mensagem
        resposta = await gerar_resposta_julia(
            mensagem="[INICIO_PROSPECCAO]",
            contexto=contexto,
            medico=cliente,
            conversa=conversa,
            incluir_historico=False,
            usar_tools=False
        )
        logger.info(f"Resposta gerada: {resposta[:100]}...")

        # 6. Enviar via WhatsApp
        # Sprint 18.1 P0: Usar wrapper com guardrails (reusar ctx do check)
        from app.services.outbound import criar_contexto_campanha
        envio_ctx = criar_contexto_campanha(
            cliente_id=cliente["id"],
            campaign_id="primeira_mensagem_slack",
            conversation_id=conversa["id"],
        )
        resultado_envio = await enviar_resposta(telefone, resposta, ctx=envio_ctx)

        # 7. Sincronizar com Chatwoot
        await _sincronizar_chatwoot(cliente["id"], telefone)

        # 8. Salvar interacao
        await salvar_interacao(
            conversa_id=conversa["id"],
            cliente_id=cliente["id"],
            tipo="saida",
            conteudo=resposta,
            autor_tipo="julia"
        )

        # 9. Atualizar cliente
        await _atualizar_cliente_apos_envio(cliente["id"])

        return ResultadoPrimeiraMensagem(
            sucesso=True,
            cliente_nome=cliente.get("primeiro_nome"),
            cliente_id=cliente["id"],
            conversa_id=conversa["id"],
            mensagem_enviada=resposta,
            resultado_envio=resultado_envio
        )

    except Exception as e:
        logger.error(f"Erro ao enviar primeira mensagem: {e}", exc_info=True)
        return ResultadoPrimeiraMensagem(
            sucesso=False,
            erro=str(e)
        )


async def _obter_ou_criar_cliente(telefone: str) -> dict:
    """Busca cliente existente ou cria novo."""
    cliente_resp = (
        supabase.table("clientes")
        .select("*")
        .eq("telefone", telefone)
        .execute()
    )

    if cliente_resp.data:
        return cliente_resp.data[0]

    # Criar novo cliente
    logger.info(f"Cliente nao encontrado, criando novo: {telefone}")
    novo_cliente = (
        supabase.table("clientes")
        .insert({
            "telefone": telefone,
            "primeiro_nome": "Doutor(a)",
            "status": "novo",
            "origem": "slack_comando",
            "stage_jornada": "novo"
        })
        .execute()
    )
    logger.info(f"Novo cliente criado: {novo_cliente.data[0]['id']}")
    return novo_cliente.data[0]


async def _obter_ou_criar_conversa(cliente_id: str) -> dict:
    """Busca conversa ativa ou cria nova."""
    conversa_resp = (
        supabase.table("conversations")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if conversa_resp.data:
        return conversa_resp.data[0]

    # Criar nova conversa
    nova_conversa = (
        supabase.table("conversations")
        .insert({
            "cliente_id": cliente_id,
            "status": "active",
            "controlled_by": "ai",
            "stage": "novo"
        })
        .execute()
    )
    logger.info(f"Nova conversa criada: {nova_conversa.data[0]['id']}")
    return nova_conversa.data[0]


async def _sincronizar_chatwoot(cliente_id: str, telefone: str) -> None:
    """Sincroniza IDs com Chatwoot apos envio."""
    await asyncio.sleep(2)  # Dar tempo pro Chatwoot processar
    try:
        ids_chatwoot = await sincronizar_ids_chatwoot(cliente_id, telefone)
        logger.info(f"IDs Chatwoot sincronizados: {ids_chatwoot}")
    except Exception as e:
        logger.warning(f"Erro ao sincronizar Chatwoot (nao critico): {e}")


async def _atualizar_cliente_apos_envio(cliente_id: str) -> None:
    """Atualiza dados do cliente apos envio."""
    supabase.table("clientes").update({
        "ultima_mensagem_data": datetime.utcnow().isoformat(),
        "ultima_mensagem_tipo": "outbound",
        "stage_jornada": "prospectado"
    }).eq("id", cliente_id).execute()
