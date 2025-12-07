"""
Servico principal do agente Julia.
"""
import logging
from typing import Optional

from app.core.prompts import montar_prompt_julia
from app.services.llm import gerar_resposta
from app.services.interacao import converter_historico_para_messages

logger = logging.getLogger(__name__)


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    incluir_historico: bool = True
) -> str:
    """
    Gera resposta da Julia para uma mensagem.

    Args:
        mensagem: Mensagem do medico
        contexto: Contexto montado (medico, historico, vagas, etc)
        incluir_historico: Se deve passar historico como messages

    Returns:
        Texto da resposta gerada
    """
    # Montar system prompt
    system_prompt = montar_prompt_julia(
        contexto_medico=contexto.get("medico", ""),
        contexto_vagas=contexto.get("vagas", ""),
        historico=contexto.get("historico", ""),
        primeira_msg=contexto.get("primeira_msg", False)
    )

    # Montar historico como messages (para o Claude ter contexto da conversa)
    historico_messages = []
    if incluir_historico and contexto.get("historico_raw"):
        historico_messages = converter_historico_para_messages(
            contexto["historico_raw"]
        )

    # Gerar resposta
    logger.info(f"Gerando resposta para: {mensagem[:50]}...")

    resposta = await gerar_resposta(
        mensagem=mensagem,
        historico=historico_messages,
        system_prompt=system_prompt,
        max_tokens=300,  # Respostas curtas
    )

    logger.info(f"Resposta gerada: {resposta[:50]}...")

    return resposta


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa: monta contexto e gera resposta.

    Args:
        mensagem_texto: Texto da mensagem do medico
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Vagas disponiveis (opcional)

    Returns:
        Texto da resposta ou None se erro
    """
    from app.services.contexto import montar_contexto_completo

    try:
        # Verificar se conversa esta sob controle da IA
        if conversa.get("controlled_by") != "ai":
            logger.info("Conversa sob controle humano, nao processando")
            return None

        # Montar contexto
        contexto = await montar_contexto_completo(medico, conversa, vagas)

        # Gerar resposta
        resposta = await gerar_resposta_julia(mensagem_texto, contexto)

        return resposta

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        return None
