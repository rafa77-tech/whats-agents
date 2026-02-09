"""
Persistencia de dados extraidos.

Sprint 53: Discovery Intelligence Pipeline.

Salva insights em conversation_insights e memorias em doctor_context.
"""

import logging
from typing import Optional, Dict, Any, List

from app.services.supabase import supabase
from app.services.embedding import gerar_embedding
from .schemas import ExtractionResult

logger = logging.getLogger(__name__)

# Threshold para auto-update de dados do cliente
AUTO_UPDATE_THRESHOLD = 0.7

# Campos permitidos para atualizacao automatica
CAMPOS_PERMITIDOS = {
    "especialidade",
    "cidade",
    "estado",
    "regiao",
}


async def salvar_insight(
    conversation_id: str,
    interaction_id: Optional[int],
    campaign_id: Optional[int],
    cliente_id: str,
    extraction: ExtractionResult,
) -> Optional[dict]:
    """
    Salva extracao na tabela conversation_insights.

    Args:
        conversation_id: ID da conversa
        interaction_id: ID da interacao (opcional)
        campaign_id: ID da campanha (opcional)
        cliente_id: ID do cliente/medico
        extraction: Resultado da extracao

    Returns:
        Dados inseridos ou None se erro
    """
    try:
        data = {
            "conversation_id": conversation_id,
            "interaction_id": interaction_id,
            "campaign_id": campaign_id,
            "cliente_id": cliente_id,
            "interesse": extraction.interesse.value,
            "interesse_score": extraction.interesse_score,
            "especialidade_mencionada": extraction.especialidade_mencionada,
            "regiao_mencionada": extraction.regiao_mencionada,
            "disponibilidade_mencionada": extraction.disponibilidade_mencionada,
            "preferencias": extraction.preferencias,
            "restricoes": extraction.restricoes,
            "dados_corrigidos": extraction.dados_corrigidos,
            "proximo_passo": extraction.proximo_passo.value,
            "modelo_extracao": "haiku",
            "confianca": extraction.confianca,
            "tokens_input": extraction.tokens_input,
            "tokens_output": extraction.tokens_output,
            "latencia_ms": extraction.latencia_ms,
            "raw_extraction": extraction.raw_json,
        }

        # Objecao (se houver)
        if extraction.objecao:
            data["objecao_tipo"] = extraction.objecao.tipo.value
            data["objecao_descricao"] = extraction.objecao.descricao
            data["objecao_severidade"] = extraction.objecao.severidade.value

        result = supabase.table("conversation_insights").insert(data).execute()

        if result.data:
            logger.debug(f"[Persistence] Insight salvo: {result.data[0]['id']}")
            return result.data[0]

    except Exception as e:
        logger.error(f"[Persistence] Erro ao salvar insight: {e}")

    return None


async def salvar_memorias_extraidas(
    cliente_id: str,
    extraction: ExtractionResult,
    conversa_id: str,
) -> int:
    """
    Salva preferencias e restricoes como memorias RAG em doctor_context.

    Args:
        cliente_id: ID do cliente/medico
        extraction: Resultado da extracao
        conversa_id: ID da conversa (para source_id)

    Returns:
        Numero de memorias salvas
    """
    memorias_salvas = 0

    # Preferencias
    for pref in extraction.preferencias:
        if await _salvar_memoria(
            cliente_id=cliente_id,
            conteudo=pref,
            tipo="preferencia",
            conversa_id=conversa_id,
        ):
            memorias_salvas += 1

    # Restricoes
    for rest in extraction.restricoes:
        if await _salvar_memoria(
            cliente_id=cliente_id,
            conteudo=rest,
            tipo="restricao",
            conversa_id=conversa_id,
        ):
            memorias_salvas += 1

    # Disponibilidade
    if extraction.disponibilidade_mencionada:
        if await _salvar_memoria(
            cliente_id=cliente_id,
            conteudo=f"Disponibilidade: {extraction.disponibilidade_mencionada}",
            tipo="preferencia",
            conversa_id=conversa_id,
        ):
            memorias_salvas += 1

    # Regiao (se diferente do cadastro)
    if extraction.regiao_mencionada:
        if await _salvar_memoria(
            cliente_id=cliente_id,
            conteudo=f"Regiao de atuacao: {extraction.regiao_mencionada}",
            tipo="info_pessoal",
            conversa_id=conversa_id,
        ):
            memorias_salvas += 1

    if memorias_salvas > 0:
        logger.info(f"[Persistence] {memorias_salvas} memorias salvas para cliente {cliente_id[:8]}")

    return memorias_salvas


async def _salvar_memoria(
    cliente_id: str,
    conteudo: str,
    tipo: str,
    conversa_id: str,
) -> bool:
    """
    Salva uma memoria individual com embedding.

    Args:
        cliente_id: ID do cliente
        conteudo: Texto da memoria
        tipo: Tipo (preferencia, restricao, info_pessoal)
        conversa_id: ID da conversa origem

    Returns:
        True se salvou, False se erro ou duplicata
    """
    try:
        # Gerar embedding
        embedding = await gerar_embedding(conteudo)

        if not embedding:
            logger.warning(f"[Persistence] Nao foi possivel gerar embedding para: {conteudo[:30]}...")
            # Salvar mesmo sem embedding
            supabase.table("doctor_context").insert({
                "cliente_id": cliente_id,
                "content": conteudo,
                "tipo": tipo,
                "source": "extraction",
                "source_id": conversa_id,
                "valido": True,
                "confianca": "alta",
            }).execute()
            return True

        # Verificar duplicata (similaridade > 0.95)
        # Busca por embedding similar
        try:
            check = supabase.rpc(
                "buscar_memorias_similares",
                {
                    "p_cliente_id": cliente_id,
                    "p_embedding": embedding,
                    "p_threshold": 0.95,
                    "p_limit": 1,
                }
            ).execute()

            if check.data and len(check.data) > 0:
                logger.debug(f"[Persistence] Memoria duplicada ignorada: {conteudo[:30]}...")
                return False
        except Exception as e:
            # RPC pode nao existir ainda, continuar
            logger.debug(f"[Persistence] RPC buscar_memorias_similares nao disponivel: {e}")

        # Inserir nova memoria
        supabase.table("doctor_context").insert({
            "cliente_id": cliente_id,
            "content": conteudo,
            "tipo": tipo,
            "source": "extraction",
            "source_id": conversa_id,
            "embedding": embedding,
            "valido": True,
            "confianca": "alta",
        }).execute()

        return True

    except Exception as e:
        logger.warning(f"[Persistence] Erro ao salvar memoria: {e}")
        return False


async def atualizar_dados_cliente(
    cliente_id: str,
    dados: Dict[str, Any],
    confianca: float,
) -> bool:
    """
    Atualiza dados do cliente com informacoes extraidas.

    So atualiza se confianca >= threshold (0.7 por padrao).

    Args:
        cliente_id: ID do cliente
        dados: Dados a atualizar
        confianca: Nivel de confianca da extracao

    Returns:
        True se atualizou, False caso contrario
    """
    if confianca < AUTO_UPDATE_THRESHOLD:
        logger.debug(
            f"[Persistence] Confianca {confianca:.2f} abaixo do threshold "
            f"{AUTO_UPDATE_THRESHOLD}, nao atualizando cliente"
        )
        return False

    try:
        # Filtrar apenas campos permitidos
        dados_filtrados = {
            k: v for k, v in dados.items()
            if k in CAMPOS_PERMITIDOS and v
        }

        if not dados_filtrados:
            return False

        # Log antes de atualizar
        logger.info(
            f"[Persistence] Atualizando cliente {cliente_id[:8]}: "
            f"{dados_filtrados} (confianca: {confianca:.2f})"
        )

        # Buscar preferencias_detectadas atuais
        result = supabase.table("clientes").select(
            "preferencias_detectadas"
        ).eq("id", cliente_id).single().execute()

        prefs = result.data.get("preferencias_detectadas") or {}
        prefs["ultima_extracao"] = dados_filtrados
        prefs["ultima_extracao_confianca"] = confianca

        dados_filtrados["preferencias_detectadas"] = prefs

        # Atualizar cliente
        supabase.table("clientes").update(dados_filtrados).eq("id", cliente_id).execute()

        return True

    except Exception as e:
        logger.error(f"[Persistence] Erro ao atualizar cliente: {e}")
        return False


async def buscar_insights_conversa(
    conversation_id: str,
    limit: int = 10
) -> List[dict]:
    """
    Busca insights de uma conversa.

    Args:
        conversation_id: ID da conversa
        limit: Numero maximo de resultados

    Returns:
        Lista de insights
    """
    try:
        result = supabase.table("conversation_insights").select(
            "*"
        ).eq("conversation_id", conversation_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return result.data or []

    except Exception as e:
        logger.error(f"[Persistence] Erro ao buscar insights: {e}")
        return []


async def buscar_insights_cliente(
    cliente_id: str,
    limit: int = 20
) -> List[dict]:
    """
    Busca insights de um cliente.

    Args:
        cliente_id: ID do cliente
        limit: Numero maximo de resultados

    Returns:
        Lista de insights
    """
    try:
        result = supabase.table("conversation_insights").select(
            "*"
        ).eq("cliente_id", cliente_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return result.data or []

    except Exception as e:
        logger.error(f"[Persistence] Erro ao buscar insights: {e}")
        return []


async def buscar_insights_campanha(
    campaign_id: int,
    limit: int = 100
) -> List[dict]:
    """
    Busca insights de uma campanha.

    Args:
        campaign_id: ID da campanha
        limit: Numero maximo de resultados

    Returns:
        Lista de insights
    """
    try:
        result = supabase.table("conversation_insights").select(
            "*"
        ).eq("campaign_id", campaign_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return result.data or []

    except Exception as e:
        logger.error(f"[Persistence] Erro ao buscar insights: {e}")
        return []
