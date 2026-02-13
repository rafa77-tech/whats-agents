"""
Tool handler: reservar_plantao.

Processa reserva de vaga/plantao para o medico.

Sprint 58 - E5: Extraido de vagas.py monolitico.
"""

import logging
import re
from typing import Any

from app.tools.vagas._helpers import (
    _buscar_especialidade_id_por_nome,
    _construir_instrucao_confirmacao,
    _construir_instrucao_ponte_externa,
    _formatar_valor_display,
)

logger = logging.getLogger(__name__)


async def _buscar_vaga_por_data(data: str, especialidade_id: str) -> dict | None:
    """
    Busca vaga pela data e especialidade.

    Args:
        data: Data no formato YYYY-MM-DD
        especialidade_id: ID da especialidade do medico

    Returns:
        Vaga encontrada ou None
    """
    # Import lazy para manter patch path via app.tools.vagas (package __init__)
    from app.tools.vagas import supabase

    logger.info(f"_buscar_vaga_por_data: data={data}, especialidade_id={especialidade_id}")

    try:
        response = (
            supabase.table("vagas")
            .select("*, hospitais(*), periodos(*), setores(*), source, source_id")
            .eq("data", data)
            .eq("especialidade_id", especialidade_id)
            .eq("status", "aberta")
            .limit(1)
            .execute()
        )

        logger.info(
            f"_buscar_vaga_por_data: encontradas {len(response.data) if response.data else 0} vagas"
        )

        if response.data:
            vaga = response.data[0]
            logger.info(
                f"_buscar_vaga_por_data: vaga encontrada id={vaga.get('id')}, "
                f"valor_tipo={vaga.get('valor_tipo')}"
            )
            return vaga

        logger.warning(
            f"_buscar_vaga_por_data: nenhuma vaga encontrada para data={data}, especialidade_id={especialidade_id}"
        )
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar vaga por data: {e}", exc_info=True)
        return None


async def handle_reservar_plantao(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
    """
    Processa chamada da tool reservar_plantao.

    Args:
        tool_input: Input da tool (data_plantao, confirmacao)
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Dict com resultado da operacao
    """
    # Import lazy para manter patch path via app.tools.vagas (package __init__)
    from app.tools.vagas import formatar_vaga_para_mensagem, reservar_vaga

    from app.core.timezone import agora_brasilia

    data_plantao = tool_input.get("data_plantao")
    tool_input.get("confirmacao", "")

    logger.info(f"handle_reservar_plantao: tool_input={tool_input}, medico_id={medico.get('id')}")

    if not data_plantao:
        return {
            "success": False,
            "error": "Data do plantao nao informada",
            "mensagem_sugerida": "Qual a data do plantao que vc quer? Me fala no formato dia/mes",
        }

    # Normalizar data (aceitar formatos variados)
    data_normalizada = data_plantao

    # Se vier como DD/MM/YYYY, converter para YYYY-MM-DD
    if re.match(r"^\d{2}/\d{2}/\d{4}$", data_plantao):
        partes = data_plantao.split("/")
        data_normalizada = f"{partes[2]}-{partes[1]}-{partes[0]}"
    # Se vier como DD/MM, assumir ano atual
    elif re.match(r"^\d{2}/\d{2}$", data_plantao):
        partes = data_plantao.split("/")
        ano = agora_brasilia().year
        data_normalizada = f"{ano}-{partes[1]}-{partes[0]}"

    logger.info(f"handle_reservar_plantao: data_normalizada={data_normalizada}")

    # Verificar especialidade do medico
    especialidade_id = medico.get("especialidade_id")
    logger.info(f"handle_reservar_plantao: especialidade_id do medico={especialidade_id}")

    if not especialidade_id:
        especialidade_nome = medico.get("especialidade")
        logger.info(
            f"handle_reservar_plantao: especialidade_nome={especialidade_nome}, buscando ID..."
        )
        if especialidade_nome:
            especialidade_id = await _buscar_especialidade_id_por_nome(especialidade_nome)
            logger.info(f"handle_reservar_plantao: especialidade_id resolvido={especialidade_id}")

    if not especialidade_id:
        return {
            "success": False,
            "error": "Especialidade do medico nao identificada",
            "mensagem_sugerida": "Qual sua especialidade?",
        }

    # Buscar vaga pela data
    vaga = await _buscar_vaga_por_data(data_normalizada, especialidade_id)
    if not vaga:
        return {
            "success": False,
            "error": f"Nao encontrei vaga para a data {data_normalizada}",
            "mensagem_sugerida": "Nao achei vaga pra essa data. Quer que eu veja as vagas disponiveis?",
        }

    vaga_id = vaga["id"]
    logger.info(
        f"Vaga encontrada por data: {vaga_id} - {vaga.get('hospitais', {}).get('nome')} em {data_normalizada}"
    )

    try:
        # Reservar vaga
        vaga_atualizada = await reservar_vaga(
            vaga_id=vaga_id, cliente_id=medico["id"], medico=medico, notificar_gestor=True
        )

        # Formatar mensagem de confirmacao
        vaga_formatada = formatar_vaga_para_mensagem(vaga)

        logger.info(f"Plantao reservado: {vaga_id} para medico {medico['id']}")

        # Extrair dados completos do hospital
        hospital_data = vaga.get("hospitais", {})

        # Sprint 20: Verificar se vaga tem origem externa (grupo)
        ponte_externa = None
        if vaga.get("source") == "grupo" and vaga.get("source_id"):
            logger.info(f"Vaga {vaga_id} tem origem de grupo, iniciando ponte externa")

            from app.services.external_handoff.service import criar_ponte_externa

            try:
                ponte_externa = await criar_ponte_externa(
                    vaga_id=vaga_id,
                    cliente_id=medico["id"],
                    medico=medico,
                    vaga=vaga,
                )
            except Exception as e:
                logger.error(f"Erro ao criar ponte externa: {e}")
                ponte_externa = {"success": False, "error": str(e)}

        # Construir resposta
        resultado: dict[str, Any] = {
            "success": True,
            "message": f"Plantao reservado com sucesso: {vaga_formatada}",
            "vaga": {
                "id": vaga_atualizada["id"],
                "hospital": hospital_data.get("nome"),
                "endereco": hospital_data.get("endereco_formatado"),
                "bairro": hospital_data.get("bairro"),
                "cidade": hospital_data.get("cidade"),
                "data": vaga_atualizada.get("data"),
                "periodo": (vaga.get("periodos") or {}).get("nome"),
                # Campos de valor expandidos (Sprint 19)
                "valor": vaga.get("valor"),
                "valor_minimo": vaga.get("valor_minimo"),
                "valor_maximo": vaga.get("valor_maximo"),
                "valor_tipo": vaga.get("valor_tipo", "fixo"),
                "valor_display": _formatar_valor_display(vaga),
                "status": vaga_atualizada.get("status"),
            },
        }

        # Sprint 20: Se teve ponte externa, adaptar instrucoes
        if ponte_externa and ponte_externa.get("success"):
            divulgador = ponte_externa.get("divulgador", {})
            resultado["ponte_externa"] = {
                "handoff_id": ponte_externa.get("handoff_id"),
                "divulgador_nome": divulgador.get("nome"),
                "divulgador_telefone": divulgador.get("telefone"),
                "divulgador_empresa": divulgador.get("empresa"),
                "msg_enviada": ponte_externa.get("msg_divulgador_enviada", False),
            }
            resultado["instrucao"] = _construir_instrucao_ponte_externa(
                vaga, hospital_data, ponte_externa, medico
            )
        else:
            resultado["instrucao"] = _construir_instrucao_confirmacao(vaga, hospital_data)

        return resultado

    except ValueError as e:
        logger.warning(f"Erro ao reservar plantao: {e}")
        return {"success": False, "error": str(e)}

    except Exception as e:
        logger.error(f"Erro inesperado ao reservar plantao: {e}")
        return {"success": False, "error": "Erro ao processar reserva. Tente novamente."}
