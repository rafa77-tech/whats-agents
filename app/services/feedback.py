"""
Serviço para processamento de feedback do gestor e melhoria do prompt.
"""
from typing import Dict, List
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def obter_interacoes(conversa_id: str) -> List[Dict]:
    """Busca interações de uma conversa."""
    try:
        response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao obter interações: {e}")
        return []


async def agregar_sugestoes() -> Dict:
    """
    Agrupa sugestões similares para facilitar análise.

    Retorna sugestões agrupadas por tipo e frequência.
    """
    try:
        response = (
            supabase.table("sugestoes_prompt")
            .select("*")
            .eq("status", "pendente")
            .execute()
        )
        sugestoes = response.data or []

        # Agrupar por tipo
        por_tipo = {}
        for s in sugestoes:
            tipo = s.get("tipo", "outro")
            if tipo not in por_tipo:
                por_tipo[tipo] = []
            por_tipo[tipo].append(s)

        # Ordenar por frequência
        resumo = {}
        for tipo, lista in por_tipo.items():
            resumo[tipo] = {
                "total": len(lista),
                "exemplos": lista[:5]  # 5 exemplos mais recentes
            }

        return resumo
    except Exception as e:
        logger.error(f"Erro ao agregar sugestões: {e}")
        return {}


async def extrair_exemplos_treinamento() -> Dict:
    """
    Extrai exemplos bons e ruins das avaliações do gestor.

    Returns:
        dict com exemplos categorizados
    """
    try:
        # Buscar avaliações do gestor com score alto e baixo
        response = (
            supabase.table("avaliacoes_qualidade")
            .select("*, conversations(id)")
            .eq("avaliador", "gestor")
            .execute()
        )
        avaliacoes = response.data or []

        exemplos_bons = []
        exemplos_ruins = []

        for av in avaliacoes:
            score = av.get("score_geral", 0)
            conversa_id = av.get("conversa_id") or (av.get("conversations", {}) or {}).get("id")
            
            if not conversa_id:
                continue

            if score >= 8:
                # Buscar interações desta conversa
                interacoes = await obter_interacoes(conversa_id)
                exemplos_bons.append({
                    "conversa_id": conversa_id,
                    "score": score,
                    "interacoes": interacoes,
                    "porque_bom": av.get("notas")
                })
            elif score <= 4:
                interacoes = await obter_interacoes(conversa_id)
                exemplos_ruins.append({
                    "conversa_id": conversa_id,
                    "score": score,
                    "interacoes": interacoes,
                    "porque_ruim": av.get("notas")
                })

        # Ordenar por score (melhores primeiro para bons, piores primeiro para ruins)
        exemplos_bons.sort(key=lambda x: x["score"], reverse=True)
        exemplos_ruins.sort(key=lambda x: x["score"])

        return {
            "bons": exemplos_bons[:10],  # Top 10
            "ruins": exemplos_ruins[:10]
        }
    except Exception as e:
        logger.error(f"Erro ao extrair exemplos de treinamento: {e}")
        return {"bons": [], "ruins": []}


async def gerar_exemplos_prompt() -> str:
    """
    Gera seção de exemplos para adicionar ao prompt.
    """
    try:
        exemplos = await extrair_exemplos_treinamento()

        texto = "## Exemplos de Conversas\n\n"

        # Exemplos bons
        texto += "### ✅ Respostas que funcionaram bem:\n\n"
        for ex in exemplos["bons"][:5]:
            # Pegar última troca (pergunta + resposta)
            msgs = ex["interacoes"][-4:] if len(ex["interacoes"]) >= 4 else ex["interacoes"]
            texto += "```\n"
            for m in msgs:
                quem = "Médico" if m.get("direcao") == "entrada" or m.get("autor_tipo") == "medico" else "Júlia"
                texto += f"{quem}: {m.get('conteudo', '')}\n"
            texto += "```\n"
            if ex.get("porque_bom"):
                texto += f"_Por que funciona: {ex['porque_bom']}_\n\n"
            texto += "\n"

        # Exemplos ruins
        texto += "### ❌ Evitar respostas assim:\n\n"
        for ex in exemplos["ruins"][:5]:
            msgs = ex["interacoes"][-4:] if len(ex["interacoes"]) >= 4 else ex["interacoes"]
            texto += "```\n"
            for m in msgs:
                quem = "Médico" if m.get("direcao") == "entrada" or m.get("autor_tipo") == "medico" else "Júlia"
                texto += f"{quem}: {m.get('conteudo', '')}\n"
            texto += "```\n"
            if ex.get("porque_ruim"):
                texto += f"_Problema: {ex['porque_ruim']}_\n\n"
            texto += "\n"

        return texto
    except Exception as e:
        logger.error(f"Erro ao gerar exemplos para prompt: {e}")
        return "## Exemplos de Conversas\n\n(Nenhum exemplo disponível ainda)\n\n"


async def atualizar_prompt_com_feedback():
    """
    Atualiza exemplos de prompt no banco de dados.

    Executar semanalmente ou após N novas avaliações.
    Salva na tabela 'prompts' com tipo 'exemplos_feedback'.
    """
    try:
        exemplos_texto = await gerar_exemplos_prompt()
        exemplos_data = await extrair_exemplos_treinamento()

        # Verificar se já existe registro de exemplos
        response = (
            supabase.table("prompts")
            .select("id")
            .eq("tipo", "exemplos_feedback")
            .eq("nome", "exemplos_conversas")
            .execute()
        )

        metadata = {
            "total_bons": len(exemplos_data.get("bons", [])),
            "total_ruins": len(exemplos_data.get("ruins", [])),
            "exemplos_bons": exemplos_data.get("bons", [])[:5],
            "exemplos_ruins": exemplos_data.get("ruins", [])[:5],
        }

        if response.data:
            # Atualizar registro existente
            supabase.table("prompts").update({
                "conteudo": exemplos_texto,
                "metadata": metadata,
                "updated_at": "now()",
            }).eq("id", response.data[0]["id"]).execute()
            logger.info(f"Exemplos de feedback atualizados no banco (id={response.data[0]['id']})")
        else:
            # Criar novo registro
            supabase.table("prompts").insert({
                "nome": "exemplos_conversas",
                "versao": "1.0",
                "tipo": "exemplos_feedback",
                "conteudo": exemplos_texto,
                "descricao": "Exemplos de conversas boas e ruins extraídos do feedback do gestor",
                "ativo": True,
                "metadata": metadata,
                "created_by": "job_atualizar_prompt_feedback",
            }).execute()
            logger.info("Novo registro de exemplos de feedback criado no banco")

        # Marcar sugestões processadas como aplicadas
        supabase.table("sugestoes_prompt").update({
            "status": "aplicada"
        }).eq("status", "pendente").execute()

        logger.info(f"Prompt atualizado com {metadata['total_bons']} exemplos bons e {metadata['total_ruins']} ruins")

        return {
            "status": "ok",
            "exemplos_bons": metadata["total_bons"],
            "exemplos_ruins": metadata["total_ruins"],
        }
    except Exception as e:
        logger.error(f"Erro ao atualizar prompt com feedback: {e}")
        raise  # Re-raise para que o job reporte o erro corretamente

