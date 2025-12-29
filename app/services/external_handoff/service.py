"""
Service principal para External Handoff.

Sprint 20 - E03 - Ponte automatica medico-divulgador.
Sprint 21 - E01 - Canary flag para rollout gradual.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.supabase import supabase
from app.services.external_handoff.repository import criar_handoff
from app.services.external_handoff.tokens import gerar_par_links
from app.services.external_handoff.guardrails import (
    pode_contatar_divulgador,
    registrar_contato_externo,
)
from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent
from app.services.slack import enviar_slack
from app.services.policy.flags import is_external_handoff_enabled, get_external_handoff_flags

logger = logging.getLogger(__name__)

# Configuracoes
HANDOFF_EXPIRY_HOURS = 48


async def buscar_divulgador_por_vaga_grupo(source_id: str) -> Optional[dict]:
    """
    Busca dados do divulgador a partir do vagas_grupo.id.

    Path: vagas_grupo → mensagem_id → mensagens_grupo.contato_id → contatos_grupo

    Args:
        source_id: UUID do vagas_grupo

    Returns:
        Dict com nome, telefone, empresa ou None
    """
    try:
        # Buscar vagas_grupo com mensagem e contato
        response = supabase.table("vagas_grupo") \
            .select(
                "id, "
                "mensagens_grupo!inner(contato_id, "
                "contatos_grupo!inner(id, nome, telefone, empresa))"
            ) \
            .eq("id", source_id) \
            .execute()

        if not response.data:
            logger.warning(f"vagas_grupo {source_id} nao encontrado")
            return None

        vaga_grupo = response.data[0]

        # Extrair contato
        mensagem = vaga_grupo.get("mensagens_grupo")
        if not mensagem:
            logger.warning(f"vagas_grupo {source_id} sem mensagem vinculada")
            return None

        contato = mensagem.get("contatos_grupo")
        if not contato:
            logger.warning(f"mensagem de vagas_grupo {source_id} sem contato")
            return None

        divulgador = {
            "id": contato.get("id"),
            "nome": contato.get("nome") or "Divulgador",
            "telefone": contato.get("telefone"),
            "empresa": contato.get("empresa"),
        }

        if not divulgador["telefone"]:
            logger.error(f"Contato {contato.get('id')} sem telefone")
            return None

        logger.info(
            f"Divulgador encontrado para vagas_grupo {source_id[:8]}: "
            f"{divulgador['nome']} ({divulgador['telefone'][-4:]})"
        )

        return divulgador

    except Exception as e:
        logger.error(f"Erro ao buscar divulgador: {e}")
        return None


async def criar_ponte_externa(
    vaga_id: str,
    cliente_id: str,
    medico: dict,
    vaga: dict,
) -> dict[str, Any]:
    """
    Cria ponte externa entre medico e divulgador.

    Fluxo:
    1. Busca divulgador via vagas_grupo
    2. Cria registro em external_handoffs
    3. Gera par de links JWT
    4. Envia mensagem para medico (contato do divulgador)
    5. Envia mensagem para divulgador (contato do medico + links)
    6. Emite evento HANDOFF_CREATED
    7. Notifica Slack

    Args:
        vaga_id: UUID da vaga
        cliente_id: UUID do medico
        medico: Dados do medico (nome, telefone)
        vaga: Dados da vaga (source_id, hospital, data, periodo, etc)

    Returns:
        Dict com resultado da operacao
    """
    source_id = vaga.get("source_id")
    if not source_id:
        logger.error(f"Vaga {vaga_id} sem source_id")
        return {"success": False, "error": "Vaga sem origem de grupo"}

    # 0. Verificar canary flag
    if not await is_external_handoff_enabled(cliente_id):
        flags = await get_external_handoff_flags()
        logger.info(
            f"Ponte externa desabilitada para cliente {cliente_id[:8]} "
            f"(enabled={flags.enabled}, canary_pct={flags.canary_pct})"
        )

        # Notificar Slack se for por canary (flag enabled mas cliente fora do %)
        if flags.enabled and flags.canary_pct < 100:
            try:
                await enviar_slack({
                    "text": ":test_tube: Ponte externa bloqueada (canary)",
                    "attachments": [{
                        "color": "#FCD34D",  # Amarelo
                        "fields": [
                            {"title": "Cliente", "value": cliente_id[:8], "short": True},
                            {"title": "Canary %", "value": f"{flags.canary_pct}%", "short": True},
                        ],
                        "footer": "Sprint 21 - Canary Flag",
                    }]
                })
            except Exception:
                pass  # Não falhar por erro de notificação

        return {
            "success": False,
            "error": "Ponte externa temporariamente indisponivel",
            "reason": "canary_blocked" if flags.enabled else "feature_disabled",
        }

    # 1. Buscar divulgador
    divulgador = await buscar_divulgador_por_vaga_grupo(source_id)
    if not divulgador:
        logger.error(f"Divulgador nao encontrado para vaga {vaga_id}")
        return {"success": False, "error": "Divulgador nao encontrado"}

    # 1.5 Verificar guardrails (opt-out + horario comercial)
    pode_contatar, motivo, agendar_para = await pode_contatar_divulgador(
        telefone=divulgador["telefone"]
    )

    if not pode_contatar:
        if motivo == "opted_out":
            logger.info(
                f"Divulgador {divulgador['telefone'][-4:]} opted-out, "
                f"criando handoff manual_required"
            )
            # Notificar Slack para intervencao manual
            try:
                await enviar_slack({
                    "text": ":no_entry_sign: Divulgador opted-out",
                    "attachments": [{
                        "color": "#EF4444",
                        "fields": [
                            {"title": "Divulgador", "value": divulgador["nome"], "short": True},
                            {"title": "Empresa", "value": divulgador.get("empresa", "N/A"), "short": True},
                            {"title": "Medico", "value": medico.get("nome", "N/A"), "short": True},
                        ],
                        "footer": "Sprint 21 - Guardrails",
                    }]
                })
            except Exception:
                pass

            return {
                "success": False,
                "error": "Divulgador nao aceita contato automatizado",
                "reason": "opted_out",
                "requires_manual": True,
            }

        elif motivo == "outside_business_hours":
            logger.info(
                f"Fora do horario comercial, ponte seria agendada para {agendar_para}"
            )
            # Por enquanto, retornar erro
            # TODO: Implementar agendamento real
            return {
                "success": False,
                "error": "Fora do horario comercial",
                "reason": "outside_business_hours",
                "schedule_for": agendar_para.isoformat() if agendar_para else None,
            }

    # Registrar/atualizar contato externo
    await registrar_contato_externo(
        telefone=divulgador["telefone"],
        nome=divulgador.get("nome"),
        empresa=divulgador.get("empresa"),
    )

    # 2. Criar registro
    reserved_until = datetime.now(timezone.utc) + timedelta(hours=HANDOFF_EXPIRY_HOURS)

    try:
        handoff = await criar_handoff(
            vaga_id=vaga_id,
            cliente_id=cliente_id,
            divulgador_nome=divulgador["nome"],
            divulgador_telefone=divulgador["telefone"],
            divulgador_empresa=divulgador.get("empresa"),
            reserved_until=reserved_until,
        )
    except Exception as e:
        logger.error(f"Erro ao criar handoff: {e}")
        return {"success": False, "error": str(e)}

    handoff_id = handoff["id"]

    # 3. Gerar links
    link_confirmar, link_nao_confirmar = gerar_par_links(handoff_id)

    # 4 & 5. Enviar mensagens
    from app.services.external_handoff.messaging import (
        enviar_mensagem_medico,
        enviar_mensagem_divulgador,
    )

    msg_medico_enviada = False
    msg_divulgador_enviada = False

    try:
        # Mensagem para medico
        await enviar_mensagem_medico(
            cliente_id=cliente_id,
            divulgador=divulgador,
            vaga=vaga,
        )
        msg_medico_enviada = True

        # Mensagem para divulgador
        await enviar_mensagem_divulgador(
            telefone=divulgador["telefone"],
            medico=medico,
            vaga=vaga,
            link_confirmar=link_confirmar,
            link_nao_confirmar=link_nao_confirmar,
        )
        msg_divulgador_enviada = True

        # Atualizar status para contacted
        supabase.table("external_handoffs") \
            .update({"status": "contacted"}) \
            .eq("id", handoff_id) \
            .execute()

    except Exception as e:
        logger.error(f"Erro ao enviar mensagens: {e}")

    # 6. Emitir evento
    event = BusinessEvent(
        event_type=EventType.HANDOFF_CREATED,
        source=EventSource.BACKEND,
        cliente_id=cliente_id,
        vaga_id=vaga_id,
        event_props={
            "handoff_id": handoff_id,
            "divulgador_telefone": divulgador["telefone"][-4:],  # Ultimos 4 digitos
            "msg_medico_enviada": msg_medico_enviada,
            "msg_divulgador_enviada": msg_divulgador_enviada,
        },
        dedupe_key=f"handoff_created:{handoff_id}",
    )
    await emit_event(event)

    # Se mensagem ao divulgador foi enviada, emitir evento CONTACTED
    if msg_divulgador_enviada:
        event_contacted = BusinessEvent(
            event_type=EventType.HANDOFF_CONTACTED,
            source=EventSource.BACKEND,
            cliente_id=cliente_id,
            vaga_id=vaga_id,
            event_props={
                "handoff_id": handoff_id,
                "channel": "whatsapp",
            },
            dedupe_key=f"handoff_contacted:{handoff_id}",
        )
        await emit_event(event_contacted)

    # 7. Notificar Slack
    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data_plantao = vaga.get("data", "")

    slack_msg = {
        "text": "Nova Ponte Externa",
        "attachments": [{
            "color": "#9333EA",  # Roxo
            "title": "Ponte Medico-Divulgador",
            "fields": [
                {"title": "Medico", "value": medico.get("nome", "N/A"), "short": True},
                {"title": "Divulgador", "value": divulgador["nome"], "short": True},
                {"title": "Hospital", "value": hospital, "short": True},
                {"title": "Data", "value": data_plantao, "short": True},
                {"title": "Expira em", "value": f"{HANDOFF_EXPIRY_HOURS}h", "short": True},
            ],
            "footer": "Agente Julia - Sprint 20",
        }]
    }

    try:
        await enviar_slack(slack_msg)
    except Exception as e:
        logger.warning(f"Erro ao notificar Slack: {e}")

    logger.info(
        f"Ponte externa criada: handoff={handoff_id}, "
        f"medico={cliente_id[:8]}, divulgador={divulgador['telefone'][-4:]}"
    )

    return {
        "success": True,
        "handoff_id": handoff_id,
        "divulgador": {
            "nome": divulgador["nome"],
            "telefone": divulgador["telefone"],
            "empresa": divulgador.get("empresa"),
        },
        "links": {
            "confirmar": link_confirmar,
            "nao_confirmar": link_nao_confirmar,
        },
        "msg_medico_enviada": msg_medico_enviada,
        "msg_divulgador_enviada": msg_divulgador_enviada,
        "reserved_until": reserved_until.isoformat(),
    }
