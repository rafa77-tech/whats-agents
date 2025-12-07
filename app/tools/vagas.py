"""
Tools relacionadas a vagas e plantoes.
"""
import logging
from typing import Any

from app.services.vaga import (
    buscar_vaga_por_id,
    reservar_vaga,
    formatar_vaga_para_mensagem,
)

logger = logging.getLogger(__name__)


TOOL_RESERVAR_PLANTAO = {
    "name": "reservar_plantao",
    "description": """Reserva um plantao/vaga para o medico.

Use quando o medico aceitar uma vaga que voce ofereceu.
Exemplos de aceite:
- "Pode reservar"
- "Quero essa"
- "Fechado"
- "Aceito"
- "Pode ser"
- "Vou querer"

IMPORTANTE: Antes de usar, confirme qual vaga o medico esta aceitando.
Use o ID da vaga que foi oferecida no contexto.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "vaga_id": {
                "type": "string",
                "description": "ID da vaga a ser reservada (formato UUID, ex: abc12345-6789-...)"
            },
            "confirmacao": {
                "type": "string",
                "description": "Breve descricao da confirmacao do medico (ex: 'medico disse pode reservar')"
            }
        },
        "required": ["vaga_id", "confirmacao"]
    }
}


async def handle_reservar_plantao(
    tool_input: dict,
    medico: dict,
    conversa: dict
) -> dict[str, Any]:
    """
    Processa chamada da tool reservar_plantao.

    Args:
        tool_input: Input da tool (vaga_id, confirmacao)
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Dict com resultado da operacao
    """
    vaga_id = tool_input.get("vaga_id")
    confirmacao = tool_input.get("confirmacao", "")

    if not vaga_id:
        return {
            "success": False,
            "error": "ID da vaga nao informado"
        }

    # Verificar se vaga existe
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        return {
            "success": False,
            "error": "Vaga nao encontrada. Verifique o ID."
        }

    try:
        # Reservar vaga
        vaga_atualizada = await reservar_vaga(
            vaga_id=vaga_id,
            cliente_id=medico["id"],
            medico=medico,
            notificar_gestor=True
        )

        # Formatar mensagem de confirmacao
        vaga_formatada = formatar_vaga_para_mensagem(vaga)

        logger.info(f"Plantao reservado: {vaga_id} para medico {medico['id']}")

        return {
            "success": True,
            "message": f"Plantao reservado com sucesso: {vaga_formatada}",
            "vaga": {
                "id": vaga_atualizada["id"],
                "hospital": vaga.get("hospitais", {}).get("nome"),
                "data": vaga_atualizada.get("data"),
                "status": vaga_atualizada.get("status")
            }
        }

    except ValueError as e:
        logger.warning(f"Erro ao reservar plantao: {e}")
        return {
            "success": False,
            "error": str(e)
        }

    except Exception as e:
        logger.error(f"Erro inesperado ao reservar plantao: {e}")
        return {
            "success": False,
            "error": "Erro ao processar reserva. Tente novamente."
        }


# Lista de todas as tools de vagas
TOOLS_VAGAS = [
    TOOL_RESERVAR_PLANTAO,
]
