"""
Tool para agendar lembretes.
"""

from datetime import datetime, timezone
from typing import Any
import logging

from app.services.fila import enfileirar_mensagem

logger = logging.getLogger(__name__)


TOOL_AGENDAR_LEMBRETE = {
    "name": "agendar_lembrete",
    "description": """Agenda lembrete para entrar em contato com o medico em data/hora especifica.

Use quando o medico pedir para falar depois, amanha, em outro horario, etc.
Exemplos de quando usar:
- "me manda msg amanha as 10h"
- "fala comigo a noite"
- "segunda-feira de manha"
- "depois das 18h"
- "semana que vem"

IMPORTANTE: Converta a solicitacao para data/hora ISO considerando a data atual.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_hora": {
                "type": "string",
                "description": "Data e hora para o lembrete no formato ISO (YYYY-MM-DDTHH:MM). Considere a data/hora atual para calcular datas relativas como 'amanha' ou 'segunda-feira'.",
            },
            "contexto": {
                "type": "string",
                "description": "Breve descricao do que estava sendo discutido (ex: 'vaga no Hospital Brasil', 'interesse em plantao noturno')",
            },
            "mensagem_retorno": {
                "type": "string",
                "description": "Mensagem personalizada para enviar no momento do lembrete. Deve ser natural e retomar o contexto.",
            },
        },
        "required": ["data_hora", "contexto"],
    },
}


async def handle_agendar_lembrete(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
    """
    Processa chamada da tool agendar_lembrete.

    1. Valida data/hora (nao pode ser no passado)
    2. Gera mensagem de retorno se nao fornecida
    3. Enfileira na fila de mensagens

    Args:
        tool_input: Input da tool
        medico: Dados do medico
        conversa: Dados da conversa

    Returns:
        Dict com resultado da operacao
    """
    data_hora_str = tool_input.get("data_hora")
    contexto = tool_input.get("contexto", "")
    mensagem = tool_input.get("mensagem_retorno")

    if not data_hora_str:
        return {"success": False, "error": "Data/hora nao informada"}

    # Parsear data/hora
    try:
        # Tentar varios formatos
        for fmt in ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
            try:
                data_hora = datetime.strptime(data_hora_str, fmt)
                # Adicionar timezone se nao tiver
                if data_hora.tzinfo is None:
                    data_hora = data_hora.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        else:
            return {
                "success": False,
                "error": "Formato de data/hora invalido. Use YYYY-MM-DDTHH:MM",
            }
    except Exception as e:
        return {"success": False, "error": f"Erro ao parsear data: {e}"}

    # Validar que nao e no passado
    agora = datetime.now(timezone.utc)
    if data_hora < agora:
        return {"success": False, "error": "Data/hora no passado"}

    # Mensagem de retorno padrao
    primeiro_nome = medico.get("primeiro_nome", "")
    if not mensagem:
        mensagem = (
            f"Oi {primeiro_nome}! Conforme combinamos, "
            f"to passando pra gente continuar sobre {contexto}. "
            f"Agora ta melhor pra vc?"
        )

    # Enfileirar
    try:
        resultado = await enfileirar_mensagem(
            cliente_id=medico["id"],
            conversa_id=conversa["id"],
            conteudo=mensagem,
            tipo="lembrete_solicitado",
            prioridade=7,  # Prioridade alta (medico pediu!)
            agendar_para=data_hora,
            metadata={"contexto": contexto, "solicitado_em": agora.isoformat()},
        )

        if resultado:
            # Formatar data para exibicao
            data_formatada = data_hora.strftime("%d/%m as %H:%M")

            logger.info(f"Lembrete agendado para {medico['id']}: {data_formatada}")

            return {
                "success": True,
                "agendado_para": data_formatada,
                "mensagem": f"Lembrete agendado para {data_formatada}",
            }
        else:
            return {"success": False, "error": "Erro ao salvar lembrete"}

    except Exception as e:
        logger.error(f"Erro ao agendar lembrete: {e}")
        return {"success": False, "error": "Erro ao processar lembrete"}


# Lista de tools de lembrete
TOOLS_LEMBRETE = [
    TOOL_AGENDAR_LEMBRETE,
]
