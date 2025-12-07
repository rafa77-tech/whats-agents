"""
Serviço para avaliação automática de qualidade de conversas.
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic
from app.services.supabase import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


async def avaliar_qualidade_conversa(conversa_id: str) -> Optional[dict]:
    """
    Avalia qualidade de uma conversa usando LLM.

    Critérios:
    - Naturalidade das respostas
    - Consistência da persona
    - Resolução do objetivo
    - Satisfação aparente do médico

    Args:
        conversa_id: ID da conversa a avaliar

    Returns:
        Dicionário com avaliação ou None se erro
    """
    try:
        # Buscar interações
        response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at")
            .execute()
        )

        interacoes = response.data or []

        if not interacoes:
            logger.warning(f"Nenhuma interação encontrada para conversa {conversa_id}")
            return None

        # Montar conversa
        conversa_texto = "\n".join([
            f"{'MÉDICO' if i.get('direcao') == 'entrada' or i.get('autor_tipo') == 'medico' else 'JÚLIA'}: {i.get('conteudo', '')}"
            for i in interacoes
        ])

        prompt = f"""
Avalie esta conversa entre uma escalista (Júlia) e um médico.

CONVERSA:
{conversa_texto}

Avalie de 1 a 10 nos seguintes critérios:
1. Naturalidade - As respostas parecem de humano?
2. Persona - Manteve tom informal de escalista?
3. Objetivo - Progrediu em direção ao objetivo (oferecer vaga)?
4. Satisfação - O médico parece satisfeito?

Responda APENAS em JSON válido, sem markdown, sem explicações:
{{
    "naturalidade": 1-10,
    "persona": 1-10,
    "objetivo": 1-10,
    "satisfacao": 1-10,
    "score_geral": 1-10,
    "pontos_positivos": ["..."],
    "pontos_negativos": ["..."],
    "sugestoes": ["..."]
}}
"""

        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        texto_resposta = response.content[0].text.strip()
        
        # Remover markdown se houver
        if texto_resposta.startswith("```"):
            texto_resposta = texto_resposta.split("```")[1]
            if texto_resposta.startswith("json"):
                texto_resposta = texto_resposta[4:]

        avaliacao = json.loads(texto_resposta)
        return avaliacao

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON da avaliação: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao avaliar qualidade da conversa {conversa_id}: {e}")
        return None


async def salvar_avaliacao_qualidade(
    conversa_id: str,
    avaliacao: dict
) -> Optional[dict]:
    """Salva avaliação de qualidade no banco."""
    try:
        response = (
            supabase.table("avaliacoes_qualidade")
            .insert({
                "conversa_id": conversa_id,
                "naturalidade": avaliacao.get("naturalidade"),
                "persona": avaliacao.get("persona"),
                "objetivo": avaliacao.get("objetivo"),
                "satisfacao": avaliacao.get("satisfacao"),
                "score_geral": avaliacao.get("score_geral"),
                "pontos_positivos": avaliacao.get("pontos_positivos", []),
                "pontos_negativos": avaliacao.get("pontos_negativos", []),
                "sugestoes": avaliacao.get("sugestoes", []),
                "avaliador": "auto"
            })
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao salvar avaliação de qualidade: {e}")
        return None


async def avaliar_conversas_pendentes(limite: int = 50):
    """
    Avalia conversas que foram encerradas mas não avaliadas.
    Executar via cron diariamente.

    Args:
        limite: Número máximo de conversas a avaliar por execução
    """
    try:
        # Buscar conversas encerradas sem avaliação
        # Primeiro, buscar conversas encerradas
        conversas_response = (
            supabase.table("conversations")
            .select("id")
            .in_("status", ["encerrada", "finalizada", "closed"])
            .execute()
        )

        conversas_ids = [c["id"] for c in (conversas_response.data or [])]

        if not conversas_ids:
            logger.info("Nenhuma conversa encerrada para avaliar")
            return

        # Buscar conversas que já têm avaliação
        avaliacoes_response = (
            supabase.table("avaliacoes_qualidade")
            .select("conversa_id")
            .in_("conversa_id", conversas_ids)
            .execute()
        )

        avaliadas_ids = {a["conversa_id"] for a in (avaliacoes_response.data or [])}

        # Filtrar conversas sem avaliação
        pendentes_ids = [cid for cid in conversas_ids if cid not in avaliadas_ids][:limite]

        logger.info(f"Avaliando {len(pendentes_ids)} conversas pendentes")

        for conversa_id in pendentes_ids:
            try:
                avaliacao = await avaliar_qualidade_conversa(conversa_id)
                if avaliacao:
                    await salvar_avaliacao_qualidade(conversa_id, avaliacao)
                    logger.info(f"Avaliação salva para conversa {conversa_id}")
            except Exception as e:
                logger.error(f"Erro ao avaliar conversa {conversa_id}: {e}")

    except Exception as e:
        logger.error(f"Erro ao avaliar conversas pendentes: {e}")

