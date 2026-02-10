"""
Tool para salvar memorias sobre o medico durante conversas.

Permite que Julia aprenda e lembre informacoes importantes
sobre cada medico ao longo do tempo.
"""

import logging
from typing import Any
from datetime import datetime, timezone

from app.services.supabase import supabase
from app.services.embedding import gerar_embedding

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL: SALVAR MEMORIA
# =============================================================================

TOOL_SALVAR_MEMORIA = {
    "name": "salvar_memoria",
    "description": """SALVA informacoes importantes sobre o medico para lembrar no futuro.

QUANDO USAR - Use esta tool quando o medico mencionar:

PREFERENCIAS DE TRABALHO:
- "Prefiro plantao noturno" → salvar como preferencia
- "Nao trabalho aos domingos" → salvar como restricao
- "So pego vaga acima de 2000" → salvar como preferencia
- "Gosto de trabalhar no ABC" → salvar como preferencia
- "Nao quero ir pra zona norte" → salvar como restricao

INFORMACOES PESSOAIS RELEVANTES:
- "Tenho filhos pequenos" → salvar como info_pessoal
- "Moro em Santo Andre" → salvar como info_pessoal
- "Trabalho no Hospital X durante a semana" → salvar como info_pessoal

HISTORICO COM VAGAS:
- "Ja trabalhei no Salvalus, gostei" → salvar como historico
- "Tive problema no Hospital Y" → salvar como historico
- "Fiz plantao la mes passado" → salvar como historico

COMPORTAMENTO:
- Se o medico sempre responde rapido → pode registrar
- Se pediu para nao ligar, so mensagem → salvar como restricao
- Se prefere receber vagas de manha → salvar como preferencia

NAO USE ESTA TOOL PARA:
- Informacoes que mudam constantemente (ex: "to ocupado agora")
- Dados basicos ja no cadastro (nome, CRM, especialidade)
- Conversas triviais sem informacao util

IMPORTANTE - APOS SALVAR:
Voce DEVE SEMPRE enviar uma mensagem de resposta ao medico apos usar esta tool.
Nunca use esta tool silenciosamente. Sempre responda reconhecendo o que o medico disse.
Exemplo: Se medico diz "nao gosto do Hospital X", salve a restricao E responda algo como "Entendi, vou lembrar disso! Deixa eu ver outras opcoes pra vc"

DICA: Sempre que ouvir "prefiro", "gosto de", "nao quero", "sempre", "nunca" - provavelmente vale salvar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "informacao": {
                "type": "string",
                "description": "A informacao a ser salva. Escreva de forma clara e objetiva. Ex: 'Prefere plantoes noturnos', 'Nao trabalha aos domingos', 'Mora em Santo Andre'",
            },
            "tipo": {
                "type": "string",
                "enum": ["preferencia", "restricao", "info_pessoal", "historico", "comportamento"],
                "description": "Categoria da informacao: preferencia (gosta/quer), restricao (nao quer/evita), info_pessoal (sobre a vida), historico (experiencias passadas), comportamento (padrao de acao)",
            },
            "confianca": {
                "type": "string",
                "enum": ["alta", "media", "baixa"],
                "description": "Nivel de certeza sobre a informacao. Alta = medico disse explicitamente. Media = inferido da conversa. Baixa = suposicao.",
            },
            "contexto": {
                "type": "string",
                "description": "Contexto em que a informacao foi mencionada (opcional). Ex: 'Ao oferecer vaga no ABC, medico disse que mora longe'",
            },
        },
        "required": ["informacao", "tipo"],
    },
}


async def handle_salvar_memoria(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
    """
    Processa chamada da tool salvar_memoria.

    Fluxo:
    1. Valida input
    2. Gera embedding do conteudo
    3. Salva na tabela doctor_context
    4. Atualiza preferencias_detectadas se for preferencia/restricao

    Args:
        tool_input: Input da tool (informacao, tipo, confianca, contexto)
        medico: Dados do medico
        conversa: Dados da conversa atual

    Returns:
        Dict com resultado da operacao
    """
    informacao = tool_input.get("informacao", "").strip()
    tipo = tool_input.get("tipo", "info_pessoal")
    confianca = tool_input.get("confianca", "media")
    contexto = tool_input.get("contexto", "")

    cliente_id = medico.get("id")

    if not informacao:
        return {
            "success": False,
            "error": "Informacao vazia",
            "mensagem_sugerida": None,  # Nao precisa dizer nada ao medico
        }

    if not cliente_id:
        logger.error("Medico sem ID ao tentar salvar memoria")
        return {"success": False, "error": "ID do medico nao encontrado"}

    logger.info(
        f"Salvando memoria para medico {cliente_id}: "
        f"tipo={tipo}, confianca={confianca}, info={informacao[:50]}..."
    )

    try:
        # Montar conteudo completo para embedding
        conteudo_completo = f"[{tipo.upper()}] {informacao}"
        if contexto:
            conteudo_completo += f" (Contexto: {contexto})"

        # Gerar embedding
        embedding = await gerar_embedding(conteudo_completo, input_type="document")

        # Preparar dados para inserir
        dados_insert = {
            "cliente_id": cliente_id,
            "content": conteudo_completo,
            "source": "conversation",
            "source_id": conversa.get("id") if conversa else None,
        }

        # Adicionar embedding se gerado com sucesso
        if embedding:
            dados_insert["embedding"] = embedding

        # Inserir na tabela doctor_context
        response = supabase.table("doctor_context").insert(dados_insert).execute()

        if not response.data:
            logger.error("Falha ao inserir memoria no banco")
            return {"success": False, "error": "Erro ao salvar no banco"}

        memoria_id = response.data[0].get("id")
        logger.info(f"Memoria salva com sucesso: {memoria_id}")

        # Se for preferencia ou restricao, atualizar campo preferencias_detectadas
        if tipo in ("preferencia", "restricao"):
            await _atualizar_preferencias_detectadas(
                cliente_id=cliente_id, tipo=tipo, informacao=informacao
            )

        return {
            "success": True,
            "memoria_id": memoria_id,
            "tipo": tipo,
            "mensagem": f"Memoria salva: {informacao[:50]}...",
            # Nao precisa responder nada ao medico sobre isso
            "instrucao": "Memoria salva. Continue a conversa naturalmente sem mencionar que salvou a informacao.",
        }

    except Exception as e:
        logger.error(f"Erro ao salvar memoria: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _atualizar_preferencias_detectadas(cliente_id: str, tipo: str, informacao: str) -> None:
    """
    Atualiza o campo preferencias_detectadas do cliente.

    Mantém um JSON com as preferências/restrições mais recentes
    para acesso rápido (sem necessidade de RAG).

    Args:
        cliente_id: ID do cliente
        tipo: 'preferencia' ou 'restricao'
        informacao: Texto da informação
    """
    try:
        # Buscar preferencias atuais
        response = (
            supabase.table("clientes")
            .select("preferencias_detectadas")
            .eq("id", cliente_id)
            .limit(1)
            .execute()
        )

        preferencias_atuais = {}
        if response.data and response.data[0].get("preferencias_detectadas"):
            preferencias_atuais = response.data[0]["preferencias_detectadas"]

        # Adicionar nova preferencia/restricao
        timestamp = datetime.now(timezone.utc).isoformat()

        if tipo == "preferencia":
            if "preferencias" not in preferencias_atuais:
                preferencias_atuais["preferencias"] = []
            preferencias_atuais["preferencias"].append({"info": informacao, "data": timestamp})
            # Manter apenas as 10 mais recentes
            preferencias_atuais["preferencias"] = preferencias_atuais["preferencias"][-10:]

        elif tipo == "restricao":
            if "restricoes" not in preferencias_atuais:
                preferencias_atuais["restricoes"] = []
            preferencias_atuais["restricoes"].append({"info": informacao, "data": timestamp})
            # Manter apenas as 10 mais recentes
            preferencias_atuais["restricoes"] = preferencias_atuais["restricoes"][-10:]

        # Atualizar no banco
        supabase.table("clientes").update(
            {"preferencias_detectadas": preferencias_atuais, "updated_at": timestamp}
        ).eq("id", cliente_id).execute()

        logger.debug(f"Preferencias detectadas atualizadas para cliente {cliente_id}")

    except Exception as e:
        logger.warning(f"Erro ao atualizar preferencias_detectadas: {e}")
        # Nao propaga erro - salvar memoria principal é mais importante


# Lista de tools de memoria
TOOLS_MEMORIA = [
    TOOL_SALVAR_MEMORIA,
]
