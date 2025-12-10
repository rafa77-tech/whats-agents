"""
Servico de processamento de comandos via Slack.

Comandos suportados:
- @julia contata <telefone/CRM> - Envia primeira mensagem para medico
- @julia bloqueia <telefone/CRM> - Bloqueia medico (nao contatar mais)
- @julia desbloqueia <telefone/CRM> - Remove bloqueio
- @julia status - Retorna status atual da Julia
- @julia pausa - Pausa envios automaticos
- @julia retoma - Retoma envios automaticos
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def processar_comando(texto: str, channel: str, user: str):
    """
    Processa comando recebido do Slack.

    Args:
        texto: Texto da mensagem (inclui mencao ao bot)
        channel: ID do canal
        user: ID do usuario que enviou
    """
    # Remover mencao ao bot do texto
    # Formato: <@U123ABC> comando args
    texto_limpo = re.sub(r'<@[A-Z0-9]+>', '', texto).strip().lower()

    logger.info(f"Comando recebido: '{texto_limpo}' de {user} em {channel}")

    # Salvar comando no banco
    comando_id = await _salvar_comando(texto, texto_limpo, user, channel)

    # Parsear comando
    comando, args = _parsear_comando(texto_limpo)

    if not comando:
        await _responder_slack(
            channel,
            "Nao entendi o comando. Comandos disponiveis:\n"
            "• `contata <telefone ou CRM>` - Envia primeira mensagem\n"
            "• `bloqueia <telefone ou CRM>` - Bloqueia medico\n"
            "• `desbloqueia <telefone ou CRM>` - Remove bloqueio\n"
            "• `status` - Mostra status atual\n"
            "• `pausa` - Pausa envios automaticos\n"
            "• `retoma` - Retoma envios automaticos"
        )
        return

    # Executar comando
    try:
        if comando == "contata":
            resultado = await _cmd_contata(args)
        elif comando == "bloqueia":
            resultado = await _cmd_bloqueia(args)
        elif comando == "desbloqueia":
            resultado = await _cmd_desbloqueia(args)
        elif comando == "status":
            resultado = await _cmd_status()
        elif comando == "pausa":
            resultado = await _cmd_pausa(user)
        elif comando == "retoma":
            resultado = await _cmd_retoma(user)
        else:
            resultado = f"Comando '{comando}' nao implementado ainda."

        await _responder_slack(channel, resultado)
        await _atualizar_comando(comando_id, resultado, sucesso=True)

    except Exception as e:
        logger.error(f"Erro ao executar comando {comando}: {e}")
        erro = f"Erro ao executar comando: {str(e)}"
        await _responder_slack(channel, erro)
        await _atualizar_comando(comando_id, erro, sucesso=False)


def _parsear_comando(texto: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai comando e argumentos do texto.

    Returns:
        Tupla (comando, argumentos) ou (None, None) se invalido
    """
    partes = texto.split(maxsplit=1)

    if not partes:
        return None, None

    comando = partes[0].lower()
    args = partes[1] if len(partes) > 1 else None

    # Comandos validos
    comandos_validos = ["contata", "bloqueia", "desbloqueia", "status", "pausa", "retoma"]

    if comando not in comandos_validos:
        return None, None

    return comando, args


async def _cmd_contata(args: Optional[str]) -> str:
    """
    Comando: contata <telefone ou CRM>

    Envia primeira mensagem para um medico especifico.
    """
    if not args:
        return "Uso: `contata <telefone ou CRM>`\nExemplo: `contata 11999998888` ou `contata CRM123456`"

    # Identificar se e telefone ou CRM
    identificador = args.strip()

    # Buscar medico
    medico = await _buscar_medico(identificador)

    if not medico:
        return f"Medico nao encontrado: {identificador}"

    if medico.get("opt_out") or medico.get("opted_out"):
        return f"Medico {medico.get('primeiro_nome')} esta em opt-out. Nao e possivel contatar."

    # Chamar endpoint de primeira mensagem
    try:
        telefone = medico.get("telefone")
        if not telefone:
            return f"Medico {medico.get('primeiro_nome')} nao tem telefone cadastrado."

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.JULIA_API_URL}/jobs/primeira-mensagem",
                json={"telefone": telefone},
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    return f"Mensagem enviada para {medico.get('primeiro_nome')} ({telefone})"
                else:
                    return f"Erro ao enviar: {data.get('error', 'desconhecido')}"
            else:
                return f"Erro na API: {response.status_code}"

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        return f"Erro ao enviar mensagem: {str(e)}"


async def _cmd_bloqueia(args: Optional[str]) -> str:
    """
    Comando: bloqueia <telefone ou CRM>

    Marca medico como bloqueado (nao sera contatado).
    """
    if not args:
        return "Uso: `bloqueia <telefone ou CRM>`"

    medico = await _buscar_medico(args.strip())

    if not medico:
        return f"Medico nao encontrado: {args}"

    # Atualizar no banco
    try:
        supabase.table("clientes").update({
            "opt_out": True,
            "opted_out": True,
            "opted_out_at": datetime.now(timezone.utc).isoformat(),
            "opted_out_reason": "Bloqueado via Slack",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", medico["id"]).execute()

        return f"Medico {medico.get('primeiro_nome')} bloqueado com sucesso."

    except Exception as e:
        logger.error(f"Erro ao bloquear medico: {e}")
        return f"Erro ao bloquear: {str(e)}"


async def _cmd_desbloqueia(args: Optional[str]) -> str:
    """
    Comando: desbloqueia <telefone ou CRM>

    Remove bloqueio do medico.
    """
    if not args:
        return "Uso: `desbloqueia <telefone ou CRM>`"

    medico = await _buscar_medico(args.strip())

    if not medico:
        return f"Medico nao encontrado: {args}"

    # Atualizar no banco
    try:
        supabase.table("clientes").update({
            "opt_out": False,
            "opted_out": False,
            "opted_out_at": None,
            "opted_out_reason": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", medico["id"]).execute()

        return f"Bloqueio removido de {medico.get('primeiro_nome')}."

    except Exception as e:
        logger.error(f"Erro ao desbloquear medico: {e}")
        return f"Erro ao desbloquear: {str(e)}"


async def _cmd_status() -> str:
    """
    Comando: status

    Retorna status atual da Julia.
    """
    try:
        # Buscar status atual
        status_result = supabase.table("julia_status").select("*").order(
            "created_at", desc=True
        ).limit(1).execute()

        status_atual = "ativo"
        if status_result.data:
            status_atual = status_result.data[0].get("status", "ativo")

        # Contar conversas ativas
        conversas = supabase.table("conversations").select(
            "id", count="exact"
        ).eq("status", "active").execute()
        total_conversas = conversas.count or 0

        # Contar handoffs pendentes
        handoffs = supabase.table("handoffs").select(
            "id", count="exact"
        ).eq("status", "pendente").execute()
        total_handoffs = handoffs.count or 0

        # Vagas abertas
        vagas = supabase.table("vagas").select(
            "id", count="exact"
        ).eq("status", "aberta").execute()
        total_vagas = vagas.count or 0

        # Mensagens enviadas hoje
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        msgs = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "enviada").gte("enviada_em", f"{hoje}T00:00:00").execute()
        msgs_hoje = msgs.count or 0

        return (
            f"*Status da Julia*\n"
            f"• Status: {status_atual}\n"
            f"• Conversas ativas: {total_conversas}\n"
            f"• Handoffs pendentes: {total_handoffs}\n"
            f"• Vagas abertas: {total_vagas}\n"
            f"• Mensagens enviadas hoje: {msgs_hoje}"
        )

    except Exception as e:
        logger.error(f"Erro ao buscar status: {e}")
        return f"Erro ao buscar status: {str(e)}"


async def _cmd_pausa(user: str) -> str:
    """
    Comando: pausa

    Pausa envios automaticos da Julia.
    """
    try:
        supabase.table("julia_status").insert({
            "status": "pausado",
            "motivo": "Pausado via Slack",
            "alterado_por": user,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return "Julia pausada. Envios automaticos suspensos."

    except Exception as e:
        logger.error(f"Erro ao pausar: {e}")
        return f"Erro ao pausar: {str(e)}"


async def _cmd_retoma(user: str) -> str:
    """
    Comando: retoma

    Retoma envios automaticos da Julia.
    """
    try:
        supabase.table("julia_status").insert({
            "status": "ativo",
            "motivo": "Retomado via Slack",
            "alterado_por": user,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return "Julia retomada. Envios automaticos ativos."

    except Exception as e:
        logger.error(f"Erro ao retomar: {e}")
        return f"Erro ao retomar: {str(e)}"


async def _buscar_medico(identificador: str) -> Optional[dict]:
    """
    Busca medico por telefone ou CRM.
    """
    identificador = identificador.strip()

    # Limpar telefone (remover caracteres especiais)
    telefone_limpo = re.sub(r'\D', '', identificador)

    # Tentar por telefone
    if telefone_limpo and len(telefone_limpo) >= 8:
        result = supabase.table("clientes").select("*").or_(
            f"telefone.like.%{telefone_limpo[-8:]}",  # Ultimos 8 digitos
        ).limit(1).execute()

        if result.data:
            return result.data[0]

    # Tentar por CRM
    crm_limpo = re.sub(r'[^0-9]', '', identificador)
    if crm_limpo:
        result = supabase.table("clientes").select("*").or_(
            f"crm.eq.{crm_limpo},crm.ilike.%{crm_limpo}%"
        ).limit(1).execute()

        if result.data:
            return result.data[0]

    return None


async def _responder_slack(channel: str, mensagem: str):
    """
    Envia resposta para o canal do Slack.
    """
    if not settings.SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN nao configurado")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "text": mensagem,
                    "unfurl_links": False
                },
                timeout=10.0
            )

            data = response.json()
            if not data.get("ok"):
                logger.error(f"Erro ao responder Slack: {data.get('error')}")

    except Exception as e:
        logger.error(f"Erro ao enviar resposta Slack: {e}")


async def _salvar_comando(texto_original: str, texto_limpo: str, user: str, channel: str) -> Optional[str]:
    """
    Salva comando no banco para historico.
    """
    try:
        partes = texto_limpo.split(maxsplit=1)
        comando = partes[0] if partes else ""
        args = partes[1].split() if len(partes) > 1 else []

        result = supabase.table("slack_comandos").insert({
            "texto_original": texto_original,
            "comando": comando,
            "argumentos": args,
            "user_id": user,
            "channel_id": channel,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        if result.data:
            return result.data[0].get("id")

    except Exception as e:
        logger.error(f"Erro ao salvar comando: {e}")

    return None


async def _atualizar_comando(comando_id: Optional[str], resposta: str, sucesso: bool):
    """
    Atualiza comando com resposta.
    """
    if not comando_id:
        return

    try:
        supabase.table("slack_comandos").update({
            "resposta": resposta,
            "respondido": True,
            "respondido_em": datetime.now(timezone.utc).isoformat(),
            "erro": None if sucesso else resposta
        }).eq("id", comando_id).execute()

    except Exception as e:
        logger.error(f"Erro ao atualizar comando: {e}")
