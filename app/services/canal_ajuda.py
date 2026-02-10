"""
Serviço de Canal de Ajuda Julia.

Sprint 32 E08 - Julia pede ajuda ao gestor quando não sabe algo.

Fluxo:
1. Julia não sabe responder pergunta factual
2. Pausa conversa
3. Pergunta ao gestor no Slack
4. Aguarda resposta (timeout 5 min)
5. Se timeout: responde "vou confirmar" + envia lembrete
6. Quando gestor responde: retoma conversa com info correta
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

TIMEOUT_MINUTOS = 5  # Timeout para resposta do gestor
INTERVALO_LEMBRETE_MINUTOS = 30  # Intervalo entre lembretes
MAX_LEMBRETES = 6  # Máximo de lembretes (3 horas)

# Categorias de perguntas
CATEGORIA_HOSPITAL = "hospital"
CATEGORIA_VAGA = "vaga"
CATEGORIA_NEGOCIACAO = "negociacao"
CATEGORIA_PROCESSO = "processo"
CATEGORIA_OUTRO = "outro"

# Status do pedido
STATUS_PENDENTE = "pendente"
STATUS_RESPONDIDO = "respondido"
STATUS_TIMEOUT = "timeout"
STATUS_CANCELADO = "cancelado"


# =============================================================================
# FUNÇÕES DE CRIAÇÃO E GESTÃO
# =============================================================================


async def criar_pedido_ajuda(
    conversa_id: str,
    cliente_id: str,
    pergunta: str,
    categoria: str = CATEGORIA_OUTRO,
    contexto: Optional[dict] = None,
) -> dict:
    """
    Cria pedido de ajuda para o gestor.

    Args:
        conversa_id: ID da conversa
        cliente_id: ID do cliente/médico
        pergunta: Pergunta que Julia não sabe responder
        categoria: Categoria da pergunta
        contexto: Contexto adicional (hospital_id, vaga_id, etc)

    Returns:
        Dict com dados do pedido criado
    """
    pedido_id = str(uuid4())
    timeout_em = datetime.now(timezone.utc) + timedelta(minutes=TIMEOUT_MINUTOS)

    try:
        # Buscar dados do cliente para contexto
        cliente_response = (
            supabase.table("clientes")
            .select("primeiro_nome, telefone")
            .eq("id", cliente_id)
            .limit(1)
            .execute()
        )
        cliente = cliente_response.data[0] if cliente_response.data else {}
        nome_medico = cliente.get("primeiro_nome", "Médico")
        telefone = cliente.get("telefone", "")

        # Criar pedido no banco
        pedido_data = {
            "id": pedido_id,
            "conversa_id": conversa_id,
            "cliente_id": cliente_id,
            "pergunta": pergunta,
            "categoria": categoria,
            "contexto": contexto or {},
            "status": STATUS_PENDENTE,
            "timeout_em": timeout_em.isoformat(),
            "lembrete_enviado": False,
            "lembretes_count": 0,
        }

        response = supabase.table("pedidos_ajuda").insert(pedido_data).execute()

        pedido = response.data[0] if response.data else pedido_data

        # Enviar notificação no Slack
        await _enviar_notificacao_ajuda(
            pedido_id=pedido_id,
            nome_medico=nome_medico,
            telefone=telefone,
            pergunta=pergunta,
            categoria=categoria,
            contexto=contexto,
        )

        # Pausar conversa
        await _pausar_conversa(conversa_id, pedido_id)

        logger.info(f"Pedido de ajuda criado: {pedido_id}")
        return pedido

    except Exception as e:
        logger.error(f"Erro ao criar pedido de ajuda: {e}")
        raise


async def processar_resposta_gestor(
    pedido_id: str,
    resposta: str,
    respondido_por: str,
) -> dict:
    """
    Processa resposta do gestor para um pedido de ajuda.

    Args:
        pedido_id: ID do pedido de ajuda
        resposta: Resposta do gestor
        respondido_por: ID/nome do gestor

    Returns:
        Dict com resultado do processamento
    """
    try:
        # Buscar pedido
        response = (
            supabase.table("pedidos_ajuda")
            .select("*, conversations:conversa_id(id, cliente_id)")
            .eq("id", pedido_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {"success": False, "error": "Pedido não encontrado"}

        pedido = response.data[0]

        if pedido["status"] != STATUS_PENDENTE:
            return {"success": False, "error": f"Pedido já está em status: {pedido['status']}"}

        # Atualizar pedido
        (
            supabase.table("pedidos_ajuda")
            .update(
                {
                    "resposta": resposta,
                    "respondido_por": respondido_por,
                    "respondido_em": datetime.now(timezone.utc).isoformat(),
                    "status": STATUS_RESPONDIDO,
                }
            )
            .eq("id", pedido_id)
            .execute()
        )

        # Retomar conversa
        await _retomar_conversa(pedido["conversa_id"], pedido_id)

        # Verificar se deve salvar como conhecimento
        if pedido.get("categoria") == CATEGORIA_HOSPITAL and pedido.get("contexto", {}).get(
            "hospital_id"
        ):
            await _salvar_conhecimento_hospital(
                hospital_id=pedido["contexto"]["hospital_id"],
                atributo=pedido["contexto"].get("atributo", "informacao_geral"),
                valor=resposta,
                pedido_ajuda_id=pedido_id,
                criado_por=respondido_por,
            )

        logger.info(f"Resposta processada para pedido {pedido_id}")

        return {
            "success": True,
            "pedido_id": pedido_id,
            "conversa_id": pedido["conversa_id"],
            "resposta": resposta,
        }

    except Exception as e:
        logger.error(f"Erro ao processar resposta: {e}")
        return {"success": False, "error": str(e)}


async def verificar_timeouts() -> dict:
    """
    Verifica pedidos que deram timeout e processa.

    Returns:
        Dict com estatísticas de processamento
    """
    agora = datetime.now(timezone.utc)

    try:
        # Buscar pedidos pendentes com timeout expirado
        response = (
            supabase.table("pedidos_ajuda")
            .select("*, conversations:conversa_id(id, cliente_id)")
            .eq("status", STATUS_PENDENTE)
            .lt("timeout_em", agora.isoformat())
            .execute()
        )

        pedidos = response.data or []
        processados = 0
        erros = 0

        for pedido in pedidos:
            try:
                # Marcar como timeout
                await _processar_timeout(pedido)
                processados += 1
            except Exception as e:
                logger.error(f"Erro ao processar timeout {pedido['id']}: {e}")
                erros += 1

        return {
            "encontrados": len(pedidos),
            "processados": processados,
            "erros": erros,
        }

    except Exception as e:
        logger.error(f"Erro ao verificar timeouts: {e}")
        return {"error": str(e)}


async def enviar_lembretes() -> dict:
    """
    Envia lembretes para pedidos pendentes.

    Returns:
        Dict com estatísticas de envio
    """
    agora = datetime.now(timezone.utc)
    agora - timedelta(minutes=INTERVALO_LEMBRETE_MINUTOS)

    try:
        # Buscar pedidos em timeout que precisam de lembrete
        response = (
            supabase.table("pedidos_ajuda")
            .select("*")
            .eq("status", STATUS_TIMEOUT)
            .lt("lembretes_count", MAX_LEMBRETES)
            .execute()
        )

        pedidos = response.data or []
        enviados = 0
        erros = 0

        for pedido in pedidos:
            try:
                # Verificar intervalo desde último lembrete
                ultimo_lembrete = pedido.get("updated_at")
                if ultimo_lembrete:
                    ultimo = datetime.fromisoformat(ultimo_lembrete.replace("Z", "+00:00"))
                    if agora - ultimo < timedelta(minutes=INTERVALO_LEMBRETE_MINUTOS):
                        continue

                await _enviar_lembrete(pedido)
                enviados += 1

            except Exception as e:
                logger.error(f"Erro ao enviar lembrete {pedido['id']}: {e}")
                erros += 1

        return {
            "encontrados": len(pedidos),
            "enviados": enviados,
            "erros": erros,
        }

    except Exception as e:
        logger.error(f"Erro ao enviar lembretes: {e}")
        return {"error": str(e)}


async def buscar_pedido_pendente(conversa_id: str) -> Optional[dict]:
    """
    Busca pedido pendente para uma conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        Dict com dados do pedido ou None
    """
    try:
        response = (
            supabase.table("pedidos_ajuda")
            .select("*")
            .eq("conversa_id", conversa_id)
            .in_("status", [STATUS_PENDENTE, STATUS_TIMEOUT])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao buscar pedido pendente: {e}")
        return None


async def cancelar_pedido(pedido_id: str, motivo: str = "cancelado") -> dict:
    """
    Cancela um pedido de ajuda.

    Args:
        pedido_id: ID do pedido
        motivo: Motivo do cancelamento

    Returns:
        Dict com resultado
    """
    try:
        response = (
            supabase.table("pedidos_ajuda")
            .update(
                {
                    "status": STATUS_CANCELADO,
                    "motivo_cancelamento": motivo,
                }
            )
            .eq("id", pedido_id)
            .execute()
        )

        if response.data:
            # Retomar conversa
            await _retomar_conversa(response.data[0]["conversa_id"], pedido_id)
            return {"success": True, "pedido_id": pedido_id}

        return {"success": False, "error": "Pedido não encontrado"}

    except Exception as e:
        logger.error(f"Erro ao cancelar pedido: {e}")
        return {"success": False, "error": str(e)}


async def obter_estatisticas() -> dict:
    """
    Obtém estatísticas do canal de ajuda.

    Returns:
        Dict com estatísticas
    """
    try:
        # Contar por status
        supabase.rpc(
            "count_pedidos_ajuda_by_status",
        ).execute()

        # Fallback se RPC não existir
        pendentes = (
            supabase.table("pedidos_ajuda")
            .select("id", count="exact")
            .eq("status", STATUS_PENDENTE)
            .execute()
        )

        timeout = (
            supabase.table("pedidos_ajuda")
            .select("id", count="exact")
            .eq("status", STATUS_TIMEOUT)
            .execute()
        )

        respondidos = (
            supabase.table("pedidos_ajuda")
            .select("id", count="exact")
            .eq("status", STATUS_RESPONDIDO)
            .execute()
        )

        return {
            "pendentes": pendentes.count or 0,
            "aguardando_resposta": timeout.count or 0,
            "respondidos": respondidos.count or 0,
        }

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {"error": str(e)}


# =============================================================================
# FUNÇÕES INTERNAS
# =============================================================================


async def _enviar_notificacao_ajuda(
    pedido_id: str,
    nome_medico: str,
    telefone: str,
    pergunta: str,
    categoria: str,
    contexto: Optional[dict],
) -> bool:
    """Envia notificação de pedido de ajuda no Slack."""
    emoji_categoria = {
        CATEGORIA_HOSPITAL: "🏥",
        CATEGORIA_VAGA: "📅",
        CATEGORIA_NEGOCIACAO: "💰",
        CATEGORIA_PROCESSO: "📋",
        CATEGORIA_OUTRO: "❓",
    }

    emoji = emoji_categoria.get(categoria, "❓")

    # Extrair contexto relevante
    contexto_str = ""
    if contexto:
        if contexto.get("hospital_nome"):
            contexto_str += f"\n• Hospital: {contexto['hospital_nome']}"
        if contexto.get("vaga_data"):
            contexto_str += f"\n• Vaga: {contexto['vaga_data']}"
        if contexto.get("atributo"):
            contexto_str += f"\n• Sobre: {contexto['atributo']}"

    mensagem = {
        "text": "🔔 Julia precisa de ajuda!",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Julia precisa de ajuda!",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Médico:*\n{nome_medico}"},
                    {"type": "mrkdwn", "text": f"*Telefone:*\n{telefone}"},
                    {"type": "mrkdwn", "text": f"*Categoria:*\n{categoria.capitalize()}"},
                ],
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Pergunta:*\n_{pergunta}_"}},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Conversa pausada aguardando resposta.{contexto_str}",
                    }
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "Responda com: `/julia responder [resposta]`"},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Pedido ID: `{pedido_id[:8]}...` | Timeout: 5 min"}
                ],
            },
        ],
    }

    return await enviar_slack(mensagem, force=True)


async def _pausar_conversa(conversa_id: str, pedido_id: str):
    """Pausa conversa aguardando resposta do gestor."""
    try:
        supabase.table("conversations").update(
            {
                "status": "aguardando_gestor",
                "pedido_ajuda_id": pedido_id,
                "pausada_em": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} pausada aguardando gestor")

    except Exception as e:
        logger.error(f"Erro ao pausar conversa: {e}")


async def _retomar_conversa(conversa_id: str, pedido_id: str):
    """Retoma conversa após resposta do gestor."""
    try:
        supabase.table("conversations").update(
            {
                "status": "active",
                "pedido_ajuda_id": None,
                "retomada_em": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", conversa_id).execute()

        logger.info(f"Conversa {conversa_id} retomada")

    except Exception as e:
        logger.error(f"Erro ao retomar conversa: {e}")


async def _processar_timeout(pedido: dict):
    """Processa timeout de um pedido."""
    try:
        # Atualizar status para timeout
        supabase.table("pedidos_ajuda").update(
            {
                "status": STATUS_TIMEOUT,
            }
        ).eq("id", pedido["id"]).execute()

        # Enviar primeiro lembrete
        await _enviar_lembrete(pedido)

        logger.info(f"Timeout processado para pedido {pedido['id']}")

    except Exception as e:
        logger.error(f"Erro ao processar timeout: {e}")
        raise


async def _enviar_lembrete(pedido: dict):
    """Envia lembrete no Slack."""
    lembretes_count = (pedido.get("lembretes_count") or 0) + 1

    # Buscar dados do cliente
    cliente_response = (
        supabase.table("clientes")
        .select("primeiro_nome")
        .eq("id", pedido["cliente_id"])
        .limit(1)
        .execute()
    )
    nome_medico = cliente_response.data[0]["primeiro_nome"] if cliente_response.data else "Médico"

    mensagem = {
        "text": "🔔 Lembrete: Julia ainda aguarda resposta",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔔 *Lembrete #{lembretes_count}*\n\nAinda preciso da resposta sobre:\n_{pedido['pergunta']}_",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Médico: {nome_medico} | Pedido: `{pedido['id'][:8]}...`",
                    }
                ],
            },
        ],
    }

    await enviar_slack(mensagem, force=True)

    # Atualizar contador de lembretes
    supabase.table("pedidos_ajuda").update(
        {
            "lembretes_count": lembretes_count,
            "lembrete_enviado": True,
        }
    ).eq("id", pedido["id"]).execute()


async def _salvar_conhecimento_hospital(
    hospital_id: str,
    atributo: str,
    valor: str,
    pedido_ajuda_id: str,
    criado_por: str,
):
    """Salva conhecimento aprendido sobre hospital."""
    try:
        # Verificar se já existe
        existing = (
            supabase.table("conhecimento_hospitais")
            .select("id")
            .eq("hospital_id", hospital_id)
            .eq("atributo", atributo)
            .limit(1)
            .execute()
        )

        if existing.data:
            # Atualizar
            supabase.table("conhecimento_hospitais").update(
                {
                    "valor": valor,
                    "criado_por": criado_por,
                    "pedido_ajuda_id": pedido_ajuda_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", existing.data[0]["id"]).execute()
        else:
            # Criar novo
            supabase.table("conhecimento_hospitais").insert(
                {
                    "hospital_id": hospital_id,
                    "atributo": atributo,
                    "valor": valor,
                    "fonte": "gestor",
                    "criado_por": criado_por,
                    "pedido_ajuda_id": pedido_ajuda_id,
                }
            ).execute()

        logger.info(f"Conhecimento salvo: {atributo} para hospital {hospital_id}")

    except Exception as e:
        logger.error(f"Erro ao salvar conhecimento: {e}")


# =============================================================================
# FUNÇÕES PARA INTEGRAÇÃO COM JULIA
# =============================================================================


async def julia_precisa_ajuda(
    conversa_id: str,
    cliente_id: str,
    pergunta_medico: str,
    categoria: str = CATEGORIA_OUTRO,
    contexto: Optional[dict] = None,
) -> dict:
    """
    Função chamada quando Julia não sabe responder.

    Uso no agente:
    ```python
    if not tem_resposta:
        resultado = await julia_precisa_ajuda(
            conversa_id=conversa.id,
            cliente_id=medico.id,
            pergunta_medico="Hospital tem estacionamento?",
            categoria="hospital",
            contexto={"hospital_id": "...", "hospital_nome": "São Luiz"}
        )
        return "Vou confirmar essa informação e já te falo!"
    ```

    Args:
        conversa_id: ID da conversa
        cliente_id: ID do cliente/médico
        pergunta_medico: Pergunta original do médico
        categoria: Categoria da pergunta
        contexto: Contexto adicional

    Returns:
        Dict com resultado
    """
    pedido = await criar_pedido_ajuda(
        conversa_id=conversa_id,
        cliente_id=cliente_id,
        pergunta=pergunta_medico,
        categoria=categoria,
        contexto=contexto,
    )

    return {
        "pedido_id": pedido["id"],
        "status": "aguardando_gestor",
        "mensagem_sugerida": "Vou confirmar essa informação e já te falo!",
    }


async def verificar_resposta_pendente(conversa_id: str) -> Optional[str]:
    """
    Verifica se há resposta pendente do gestor para retomar.

    Args:
        conversa_id: ID da conversa

    Returns:
        Resposta do gestor ou None
    """
    try:
        response = (
            supabase.table("pedidos_ajuda")
            .select("resposta")
            .eq("conversa_id", conversa_id)
            .eq("status", STATUS_RESPONDIDO)
            .order("respondido_em", desc=True)
            .limit(1)
            .execute()
        )

        if response.data and response.data[0].get("resposta"):
            return response.data[0]["resposta"]

        return None

    except Exception as e:
        logger.error(f"Erro ao verificar resposta pendente: {e}")
        return None
