"""
Tools de Intermediacao - Sprint 29.

Julia e INTERMEDIARIA:
- Nao negocia valores
- Nao confirma reservas diretamente
- Conecta medico com responsavel da vaga
- Acompanha status da intermediacao

Estas tools implementam o papel de intermediaria da Julia.
"""

import logging
from typing import Any

from app.services.supabase import supabase
from app.services.external_handoff.service import criar_ponte_externa
from app.services.external_handoff.repository import (
    atualizar_status_handoff,
    buscar_handoff_existente,
)
from app.services.business_events import (
    emit_event,
    EventType,
    EventSource,
    BusinessEvent,
)

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL: CRIAR HANDOFF EXTERNO
# =============================================================================

TOOL_CRIAR_HANDOFF_EXTERNO = {
    "name": "criar_handoff_externo",
    "description": """Coloca o medico em contato com o responsavel pela vaga.

QUANDO USAR:
- Medico demonstra interesse em uma vaga especifica
- Medico quer saber mais detalhes sobre uma vaga
- Medico pergunta sobre valor/condicoes (Julia DEVE conectar, nao responder)
- Medico pede para reservar/fechar vaga ('fechou', 'quero essa', 'pode ser')

O QUE FAZ:
1. Identifica o divulgador/responsavel pela vaga
2. Envia mensagem ao medico com contato do responsavel
3. Envia mensagem ao responsavel com dados do medico interessado
4. Cria registro para acompanhamento

IMPORTANTE:
- Julia NAO negocia valores - conecta as partes
- Julia NAO confirma reservas - repassa o interesse
- O fechamento e feito entre medico e responsavel

CRITICO - VAGA_ID:
- O vaga_id DEVE ser o UUID EXATO retornado por buscar_vagas
- Formato: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" (UUID)
- NAO invente IDs como "vaga_hospital_data" - use o ID real!
- Se nao tiver o ID, chame buscar_vagas primeiro

PARAMETROS:
- vaga_id: UUID da vaga (copie EXATAMENTE do resultado de buscar_vagas)
- motivo: Breve descricao do interesse do medico""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {
                "type": "string",
                "description": "UUID da vaga - DEVE ser o ID exato retornado por buscar_vagas (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx). NAO invente IDs!",
            },
            "motivo": {
                "type": "string",
                "description": "Breve descricao do interesse (ex: 'medico quer saber valor', 'medico quer reservar')",
            },
        },
        "required": ["vaga_id", "motivo"],
    },
}


async def handle_criar_handoff_externo(
    tool_input: dict, medico: dict, conversa: dict
) -> dict[str, Any]:
    """
    Cria ponte entre medico e responsavel da vaga.

    Esta e a funcao central de intermediacao da Julia.
    Ao inves de negociar ou confirmar, Julia conecta as partes.

    Args:
        tool_input: Input da tool (vaga_id, motivo)
        medico: Dados do medico interessado
        conversa: Dados da conversa atual

    Returns:
        Dict com resultado da ponte criada
    """
    vaga_id = tool_input.get("vaga_id")
    motivo = tool_input.get("motivo", "interesse em vaga")

    if not vaga_id:
        return {
            "success": False,
            "error": "ID da vaga nao informado",
            "mensagem_sugerida": "Qual vaga voce tem interesse? Me conta mais que eu te conecto com o responsavel",
        }

    cliente_id = medico.get("id")
    if not cliente_id:
        logger.error("handle_criar_handoff_externo: medico sem ID")
        return {
            "success": False,
            "error": "Dados do medico incompletos",
            "mensagem_sugerida": "Tive um probleminha aqui. Pode repetir qual vaga te interessou?",
        }

    # Verificar se ja existe handoff para essa vaga/medico
    handoff_existente = await buscar_handoff_existente(vaga_id, cliente_id)
    if handoff_existente:
        status = handoff_existente.get("status")
        divulgador_nome = handoff_existente.get("divulgador_nome", "o responsavel")

        if status in ["pending", "contacted"]:
            logger.info(
                f"Handoff existente para vaga={vaga_id[:8]}, "
                f"cliente={cliente_id[:8]}, status={status}"
            )
            return {
                "success": True,
                "handoff_existente": True,
                "handoff_id": handoff_existente.get("id"),
                "status": status,
                "divulgador_nome": divulgador_nome,
                "instrucao": (
                    f"Ja contatamos {divulgador_nome} sobre essa vaga. "
                    f"Ele ja tem seus dados e deve entrar em contato. "
                    f"Quer que eu tente de novo ou prefere aguardar?"
                ),
                "mensagem_sugerida": (
                    f"Ja passei seu interesse pro {divulgador_nome}! "
                    f"Ele deve te ligar em breve. Se nao der retorno hoje, me avisa que eu cobro ele"
                ),
            }

    # Buscar dados da vaga
    try:
        response = (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*), setores(*), source, source_id")
            .eq("id", vaga_id)
            .execute()
        )

        if not response.data:
            logger.warning(f"Vaga {vaga_id} nao encontrada")
            return {
                "success": False,
                "error": "Vaga nao encontrada",
                "mensagem_sugerida": "Nao encontrei essa vaga. Quer que eu veja as disponiveis?",
            }

        vaga = response.data[0]

    except Exception as e:
        logger.error(f"Erro ao buscar vaga: {e}")
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha. Me conta de novo qual vaga te interessou",
        }

    # Verificar se e vaga de grupo (tem divulgador)
    source = vaga.get("source")
    source_id = vaga.get("source_id")

    if source != "grupo" or not source_id:
        # Vaga interna - nao tem divulgador externo
        logger.info(f"Vaga {vaga_id} e interna (source={source}), sem divulgador externo")

        hospital = vaga.get("hospitais", {}).get("nome", "o hospital")
        return {
            "success": True,
            "tipo": "vaga_interna",
            "instrucao": (
                f"Esta vaga e direta com {hospital}. "
                f"Informe ao medico que voce vai passar os dados dele pro hospital "
                f"e que eles vao entrar em contato pra confirmar os detalhes."
            ),
            "mensagem_sugerida": (
                f"Essa vaga e direto com {hospital}! "
                f"Vou passar seus dados pra eles te ligarem e confirmar tudo, blz?"
            ),
        }

    # Criar ponte externa (vaga de grupo)
    logger.info(f"Criando ponte externa: vaga={vaga_id[:8]}, medico={cliente_id[:8]}")

    try:
        resultado = await criar_ponte_externa(
            vaga_id=vaga_id,
            cliente_id=cliente_id,
            medico=medico,
            vaga=vaga,
        )
    except Exception as e:
        logger.error(f"Erro ao criar ponte externa: {e}")
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha pra te conectar. Tenta de novo daqui a pouco?",
        }

    if not resultado.get("success"):
        error = resultado.get("error", "Erro desconhecido")
        reason = resultado.get("reason")

        if reason == "opted_out":
            return {
                "success": False,
                "error": error,
                "reason": reason,
                "mensagem_sugerida": (
                    "O responsavel por essa vaga nao aceita contato automatizado. "
                    "Vou pedir pra minha supervisora te ajudar com essa, blz?"
                ),
            }
        elif reason == "outside_business_hours":
            return {
                "success": False,
                "error": error,
                "reason": reason,
                "mensagem_sugerida": (
                    "To fora do horario comercial agora, entao nao consigo contatar o responsavel. "
                    "Amanha cedo te aviso, pode ser?"
                ),
            }
        else:
            return {
                "success": False,
                "error": error,
                "mensagem_sugerida": "Tive um problema pra te conectar. Vou tentar de novo depois, tudo bem?",
            }

    # Ponte criada com sucesso
    divulgador = resultado.get("divulgador", {})
    divulgador_nome = divulgador.get("nome", "o responsavel")
    divulgador_telefone = divulgador.get("telefone", "")
    handoff_id = resultado.get("handoff_id")

    logger.info(
        f"Ponte criada: handoff={handoff_id}, medico={cliente_id[:8]}, divulgador={divulgador_nome}"
    )

    # Emitir evento de intermediacao
    event = BusinessEvent(
        event_type=EventType.HANDOFF_CREATED,
        source=EventSource.BACKEND,
        cliente_id=cliente_id,
        vaga_id=vaga_id,
        event_props={
            "handoff_id": handoff_id,
            "motivo": motivo,
            "tool": "criar_handoff_externo",
        },
        dedupe_key=f"intermediacao:{handoff_id}",
    )
    await emit_event(event)

    return {
        "success": True,
        "handoff_id": handoff_id,
        "divulgador": {
            "nome": divulgador_nome,
            "telefone": divulgador_telefone,
            "empresa": divulgador.get("empresa"),
        },
        "msg_medico_enviada": resultado.get("msg_medico_enviada", False),
        "msg_divulgador_enviada": resultado.get("msg_divulgador_enviada", False),
        "instrucao": (
            f"Ponte criada! {divulgador_nome} ja tem os dados do medico. "
            f"Informe ao medico que o contato foi feito e que deve receber retorno em breve. "
            f"Julia NAO deve prometer valores ou confirmar a reserva - o fechamento e entre eles."
        ),
        "mensagem_sugerida": (
            f"Pronto! Passei seu interesse pro {divulgador_nome}. "
            f"Ele ja tem seu contato e deve te ligar em breve pra combinar os detalhes. "
            f"Me avisa depois se deu certo?"
        ),
    }


# =============================================================================
# TOOL: REGISTRAR STATUS INTERMEDIACAO
# =============================================================================

TOOL_REGISTRAR_STATUS_INTERMEDIACAO = {
    "name": "registrar_status_intermediacao",
    "description": """Registra o status de uma intermediacao (ponte medico-responsavel).

QUANDO USAR:
- Medico informa que fechou o plantao
- Medico diz que nao conseguiu falar com responsavel
- Medico informa que desistiu da vaga
- Medico confirma que o responsavel entrou em contato

STATUS POSSIVEIS:
- interessado: Medico demonstrou interesse (automatico ao criar handoff)
- contatado: Responsavel ja foi contatado (automatico)
- fechado: Medico confirmou que fechou o plantao
- sem_resposta: Medico nao conseguiu contato com responsavel
- desistiu: Medico desistiu da vaga

PARAMETROS:
- vaga_id: ID da vaga da intermediacao
- status: Novo status (fechado, sem_resposta, desistiu)
- observacao: Detalhes adicionais""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {"type": "string", "description": "UUID da vaga"},
            "status": {
                "type": "string",
                "enum": ["fechado", "sem_resposta", "desistiu"],
                "description": "Novo status da intermediacao",
            },
            "observacao": {
                "type": "string",
                "description": "Detalhes sobre o status (ex: 'medico disse que fechou por R$ 2.500')",
            },
        },
        "required": ["vaga_id", "status"],
    },
}


async def handle_registrar_status_intermediacao(
    tool_input: dict, medico: dict, conversa: dict
) -> dict[str, Any]:
    """
    Registra status de uma intermediacao existente.

    Usado para acompanhamento do funil de conversao.

    Args:
        tool_input: Input da tool (vaga_id, status, observacao)
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Dict com resultado da atualizacao
    """
    vaga_id = tool_input.get("vaga_id")
    novo_status = tool_input.get("status")
    observacao = tool_input.get("observacao", "")

    if not vaga_id:
        return {
            "success": False,
            "error": "ID da vaga nao informado",
            "mensagem_sugerida": "Qual vaga voce ta me falando?",
        }

    if not novo_status:
        return {
            "success": False,
            "error": "Status nao informado",
            "mensagem_sugerida": "O que aconteceu? Fechou a vaga ou ta tendo problema?",
        }

    cliente_id = medico.get("id")
    if not cliente_id:
        logger.error("handle_registrar_status_intermediacao: medico sem ID")
        return {"success": False, "error": "Dados do medico incompletos"}

    # Mapear status para o formato do banco
    status_map = {
        "fechado": "confirmed",
        "sem_resposta": "no_response",
        "desistiu": "cancelled",
    }
    status_banco = status_map.get(novo_status, novo_status)

    # Buscar handoff existente
    handoff = await buscar_handoff_existente(vaga_id, cliente_id)

    if not handoff:
        logger.warning(f"Handoff nao encontrado para vaga={vaga_id}, cliente={cliente_id[:8]}")
        return {
            "success": False,
            "error": "Intermediacao nao encontrada",
            "mensagem_sugerida": "Nao achei registro dessa vaga pra voce. Qual vaga ta falando?",
        }

    handoff_id = handoff.get("id")
    status_atual = handoff.get("status")

    # Validar transicao de status
    if status_atual == "confirmed":
        return {
            "success": False,
            "error": "Intermediacao ja confirmada",
            "mensagem_sugerida": "Essa vaga ja ta confirmada! Ta tudo certo?",
        }

    if status_atual in ["expired", "cancelled"]:
        return {
            "success": False,
            "error": f"Intermediacao {status_atual}",
            "mensagem_sugerida": "Essa intermediacao ja foi encerrada. Quer ver outras vagas?",
        }

    # Atualizar status
    from datetime import datetime, timezone

    confirmed_at = datetime.now(timezone.utc) if novo_status == "fechado" else None

    try:
        sucesso = await atualizar_status_handoff(
            handoff_id=handoff_id,
            novo_status=status_banco,
            confirmed_at=confirmed_at,
            confirmed_by="keyword" if novo_status == "fechado" else None,
            confirmation_source=observacao or None,
        )
    except Exception as e:
        logger.error(f"Erro ao atualizar status handoff: {e}")
        return {
            "success": False,
            "error": str(e),
            "mensagem_sugerida": "Tive um probleminha. Pode repetir?",
        }

    if not sucesso:
        return {
            "success": False,
            "error": "Falha ao atualizar status",
            "mensagem_sugerida": "Nao consegui atualizar. Pode tentar de novo?",
        }

    logger.info(
        f"Status intermediacao atualizado: handoff={handoff_id[:8]}, "
        f"status={status_atual} -> {status_banco}"
    )

    # Emitir evento baseado no status
    if novo_status == "fechado":
        event = BusinessEvent(
            event_type=EventType.HANDOFF_CONFIRMED,
            source=EventSource.BACKEND,
            cliente_id=cliente_id,
            vaga_id=vaga_id,
            event_props={
                "handoff_id": handoff_id,
                "confirmation_source": "conversa",
                "observacao": observacao,
            },
            dedupe_key=f"handoff_confirmed:{handoff_id}",
        )
        await emit_event(event)

        return {
            "success": True,
            "handoff_id": handoff_id,
            "status_anterior": status_atual,
            "status_novo": status_banco,
            "instrucao": (
                "Medico confirmou que fechou o plantao! "
                "Parabenize e pergunte se pode ajudar com algo mais."
            ),
            "mensagem_sugerida": (
                "Show! Fico feliz que deu certo! Qualquer coisa que precisar, me chama aqui"
            ),
        }

    elif novo_status == "sem_resposta":
        return {
            "success": True,
            "handoff_id": handoff_id,
            "status_anterior": status_atual,
            "status_novo": status_banco,
            "instrucao": (
                "Medico nao conseguiu contato com responsavel. "
                "Oferecer para tentar de novo ou mostrar outras vagas."
            ),
            "mensagem_sugerida": (
                "Poxa, vou cobrar ele aqui. Quer que eu tente de novo ou prefere ver outras vagas?"
            ),
        }

    else:  # desistiu
        return {
            "success": True,
            "handoff_id": handoff_id,
            "status_anterior": status_atual,
            "status_novo": status_banco,
            "instrucao": ("Medico desistiu da vaga. Agradecer e oferecer ajuda futura."),
            "mensagem_sugerida": (
                "Tudo bem! Quando surgir outra oportunidade te aviso. "
                "Se precisar de algo, me chama!"
            ),
        }


# Lista de todas as tools de intermediacao
TOOLS_INTERMEDIACAO = [
    TOOL_CRIAR_HANDOFF_EXTERNO,
    TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
]
