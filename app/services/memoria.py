"""
Servico de memoria de longo prazo (RAG).

Busca e formata memorias relevantes sobre o medico
para enriquecer o contexto do agente.
"""
import logging
from typing import Optional
from datetime import datetime

from app.services.supabase import supabase
from app.services.embedding import gerar_embedding

logger = logging.getLogger(__name__)


async def buscar_memorias_relevantes(
    cliente_id: str,
    mensagem: str,
    limite: int = 5,
    threshold: float = 0.7
) -> list[dict]:
    """
    Busca memorias relevantes para uma mensagem usando RAG.

    Fluxo:
    1. Gera embedding da mensagem atual
    2. Busca memorias similares no banco (cosine similarity)
    3. Filtra por threshold minimo
    4. Retorna memorias ordenadas por relevancia

    Args:
        cliente_id: ID do medico
        mensagem: Mensagem atual para buscar contexto relevante
        limite: Maximo de memorias a retornar
        threshold: Similaridade minima (0-1)

    Returns:
        Lista de memorias relevantes com score de similaridade
    """
    if not cliente_id or not mensagem:
        return []

    try:
        # Gerar embedding da mensagem (como query)
        query_embedding = await gerar_embedding(mensagem, input_type="query")

        if not query_embedding:
            logger.warning("Falha ao gerar embedding - usando fallback de memorias recentes")
            return await _buscar_memorias_recentes(cliente_id, limite)

        # Buscar memorias similares via funcao SQL
        response = supabase.rpc(
            "buscar_memorias_similares",
            {
                "p_cliente_id": cliente_id,
                "p_embedding": query_embedding,
                "p_limite": limite,
                "p_threshold": threshold
            }
        ).execute()

        if not response.data:
            logger.debug(f"Nenhuma memoria relevante encontrada para cliente {cliente_id}")
            return []

        memorias = response.data
        logger.info(
            f"Encontradas {len(memorias)} memorias relevantes para cliente {cliente_id}"
        )

        return memorias

    except Exception as e:
        logger.error(f"Erro ao buscar memorias relevantes: {e}", exc_info=True)
        # Fallback para memorias recentes sem embedding
        return await _buscar_memorias_recentes(cliente_id, limite)


async def _buscar_memorias_recentes(
    cliente_id: str,
    limite: int = 5,
    tipo: str = None
) -> list[dict]:
    """
    Fallback: busca memorias mais recentes sem usar embeddings.

    Util quando:
    - Voyage API nao disponivel
    - Erro ao gerar embedding
    - Tabela sem embeddings

    Args:
        cliente_id: ID do medico
        limite: Maximo de memorias
        tipo: Filtrar por tipo especifico (opcional)

    Returns:
        Lista de memorias recentes
    """
    try:
        response = supabase.rpc(
            "buscar_memorias_recentes",
            {
                "p_cliente_id": cliente_id,
                "p_limite": limite,
                "p_tipo": tipo
            }
        ).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar memorias recentes: {e}")
        return []


def formatar_memorias_para_prompt(memorias: list[dict]) -> str:
    """
    Formata memorias para incluir no prompt do agente.

    Organiza por tipo e adiciona emojis para facilitar leitura.

    Args:
        memorias: Lista de memorias do banco

    Returns:
        Texto formatado para o prompt
    """
    if not memorias:
        return ""

    linhas = ["## Informacoes que voce ja sabe sobre este medico:"]

    # Emojis por tipo
    emoji_map = {
        "preferencia": "👍",
        "restricao": "🚫",
        "info_pessoal": "ℹ️",
        "historico": "📋",
        "comportamento": "🎯",
    }

    # Agrupar por tipo
    por_tipo = {}
    for m in memorias:
        tipo = m.get("tipo", "info_pessoal")
        similaridade = m.get("similaridade", 0)

        # So inclui se similaridade razoavel (threshold 0.7)
        if similaridade and similaridade < 0.7:
            continue

        if tipo not in por_tipo:
            por_tipo[tipo] = []
        por_tipo[tipo].append(m)

    # Ordem de prioridade
    ordem = ["restricao", "preferencia", "info_pessoal", "historico", "comportamento"]

    for tipo in ordem:
        if tipo not in por_tipo:
            continue

        emoji = emoji_map.get(tipo, "•")
        memorias_tipo = por_tipo[tipo]

        for m in memorias_tipo:
            content = m.get("content", "")
            # Remover prefixo [TIPO] se existir
            if content.startswith("["):
                content = content.split("]", 1)[-1].strip()

            confianca = m.get("confianca", "media")
            indicador = ""
            if confianca == "baixa":
                indicador = " (pode nao ser certo)"

            linhas.append(f"{emoji} {content}{indicador}")

    if len(linhas) == 1:
        # So tinha o titulo, nenhuma memoria passou o threshold
        return ""

    return "\n".join(linhas)


async def buscar_preferencias_rapidas(cliente_id: str) -> dict:
    """
    Busca preferencias do campo preferencias_detectadas (cache rapido).

    Usado para acesso rapido sem RAG.
    Complementa a busca semantica com dados estruturados.

    Args:
        cliente_id: ID do medico

    Returns:
        Dict com preferencias e restricoes
    """
    try:
        response = (
            supabase.table("clientes")
            .select("preferencias_detectadas, preferencias_conhecidas")
            .eq("id", cliente_id)
            .limit(1)
            .execute()
        )

        if not response.data:
            return {}

        cliente = response.data[0]
        preferencias = cliente.get("preferencias_detectadas") or {}
        conhecidas = cliente.get("preferencias_conhecidas") or {}

        # Merge das duas fontes
        resultado = {
            "preferencias": preferencias.get("preferencias", []),
            "restricoes": preferencias.get("restricoes", []),
            **conhecidas  # turnos, hospitais_preferidos, etc
        }

        return resultado

    except Exception as e:
        logger.error(f"Erro ao buscar preferencias rapidas: {e}")
        return {}


def formatar_preferencias_rapidas(prefs: dict) -> str:
    """
    Formata preferencias rapidas para o prompt.

    Args:
        prefs: Dict de preferencias

    Returns:
        Texto formatado
    """
    if not prefs:
        return ""

    linhas = []

    # Preferencias
    preferencias = prefs.get("preferencias", [])
    if preferencias:
        for p in preferencias[-5:]:  # Ultimas 5
            info = p.get("info") if isinstance(p, dict) else p
            if info:
                linhas.append(f"👍 {info}")

    # Restricoes
    restricoes = prefs.get("restricoes", [])
    if restricoes:
        for r in restricoes[-5:]:  # Ultimas 5
            info = r.get("info") if isinstance(r, dict) else r
            if info:
                linhas.append(f"🚫 {info}")

    # Turnos preferidos
    turnos = prefs.get("turnos", [])
    if turnos:
        linhas.append(f"⏰ Turnos preferidos: {', '.join(turnos)}")

    # Hospitais preferidos
    hospitais = prefs.get("hospitais_preferidos", [])
    if hospitais:
        linhas.append(f"🏥 Hospitais preferidos: {', '.join(hospitais[:3])}")

    if not linhas:
        return ""

    return "## Preferencias conhecidas:\n" + "\n".join(linhas)


async def enriquecer_contexto_com_memorias(
    cliente_id: str,
    mensagem_atual: str
) -> str:
    """
    Funcao principal para enriquecer contexto com memorias.

    Combina:
    1. Busca semantica (RAG) baseada na mensagem
    2. Preferencias rapidas (cache)

    Args:
        cliente_id: ID do medico
        mensagem_atual: Mensagem atual do medico

    Returns:
        Texto formatado com todas as memorias relevantes
    """
    partes = []

    # 1. Busca semantica
    memorias = await buscar_memorias_relevantes(
        cliente_id=cliente_id,
        mensagem=mensagem_atual,
        limite=5,
        threshold=0.7
    )

    memorias_formatadas = formatar_memorias_para_prompt(memorias)
    if memorias_formatadas:
        partes.append(memorias_formatadas)

    # 2. Preferencias rapidas (complementar)
    # So busca se nao encontrou muitas memorias semanticas
    if len(memorias) < 3:
        prefs = await buscar_preferencias_rapidas(cliente_id)
        prefs_formatadas = formatar_preferencias_rapidas(prefs)
        if prefs_formatadas:
            partes.append(prefs_formatadas)

    if not partes:
        return ""

    return "\n\n".join(partes)
