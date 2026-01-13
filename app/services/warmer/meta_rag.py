"""
RAG de Politicas Meta.

Armazena e consulta politicas do WhatsApp Business
para informar decisoes do Trust Score e Warmer.
"""
import logging
from typing import List, Optional
from datetime import date

from app.services.supabase import supabase
from app.services.embedding import gerar_embedding

logger = logging.getLogger(__name__)


# Politicas iniciais para seed
POLITICAS_SEED = [
    # Limites
    {
        "categoria": "limites",
        "titulo": "Tiers de Limite de Mensagens",
        "conteudo": """
        Limites de mensagens por dia (desde Outubro 2025):
        - Tier 1: 1.000 destinatarios/dia (inicial)
        - Tier 2: 10.000 destinatarios/dia
        - Tier 3: 100.000 destinatarios/dia
        - Unlimited: Sem limite (empresas verificadas)

        IMPORTANTE: Desde Outubro 2025, o limite e compartilhado por todo o Portfolio
        (todos os numeros da empresa), nao mais por numero individual.

        Para subir de tier:
        - Quality rating media ou alta
        - Usar pelo menos 50% do limite atual por 7 dias
        - Enviar mensagens de alta qualidade
        """,
        "fonte_url": "https://docs.360dialog.com/docs/waba-management/capacity-quality-rating-and-messaging-limits",
        "fonte_nome": "360Dialog Docs",
    },
    {
        "categoria": "limites",
        "titulo": "Mensagens Iniciadas vs Respostas",
        "conteudo": """
        Os limites se aplicam apenas a mensagens INICIADAS pelo negocio (outbound).

        Respostas a mensagens de clientes (inbound) NAO contam para o limite.
        Desde 2024, conversas iniciadas pelo usuario sao gratuitas.

        Implicacao: Priorizar respostas sobre prospeccao quando proximo do limite.
        """,
        "fonte_url": "https://learn.turn.io/l/en/article/uvdz8tz40l-quality-ratings-and-messaging-limits",
        "fonte_nome": "Turn.io Learn",
    },

    # Quality Rating
    {
        "categoria": "quality_rating",
        "titulo": "Sistema de Quality Rating",
        "conteudo": """
        Quality Rating determina se voce pode subir de tier:

        - Verde (Alta): Pode subir de tier
        - Amarelo (Media): Mantem tier atual
        - Vermelho (Baixa): Nao sobe de tier

        MUDANCA OUTUBRO 2025: Qualidade baixa NAO causa mais downgrade de tier.
        Apenas impede subir para o proximo tier.

        Fatores que afetam qualidade:
        - Bloqueios por usuarios
        - Denuncias de spam
        - Taxa de leitura
        - Feedback negativo nos ultimos 7 dias (peso maior para recentes)
        """,
        "fonte_url": "https://docs.360dialog.com/partner/messaging-and-calling/messaging-health-and-troubleshooting/messaging-limits-and-quality-rating",
        "fonte_nome": "360Dialog Partner Docs",
    },

    # Motivos de Ban
    {
        "categoria": "motivos_ban",
        "titulo": "Principais Motivos de Ban",
        "conteudo": """
        Motivos que levam a ban/restricao:

        1. SPAM: Mensagens em massa nao solicitadas
        2. AUTOMACAO NAO AUTORIZADA: Bots sem API oficial, mods (GB WhatsApp)
        3. FEEDBACK NEGATIVO: Muitos usuarios bloqueando/denunciando
        4. CONTEUDO PROIBIDO: Armas, drogas, adulto, jogos de azar
        5. TERCEIROS NAO AUTORIZADOS: Apps modificados
        6. SEM CONSENTIMENTO: Enviar sem opt-in explicito
        7. VOLUME SUSPEITO: Muitas mensagens em curto periodo

        Estatistica: 6.8 milhoes de contas banidas no 1o semestre de 2025.
        """,
        "fonte_url": "https://support.wati.io/en/articles/11463217",
        "fonte_nome": "Wati.io Help Center",
    },
    {
        "categoria": "motivos_ban",
        "titulo": "Sinais de Automacao Detectados",
        "conteudo": """
        WhatsApp usa machine learning para detectar automacao:

        - Mensagens muito rapidas (sem delay humano)
        - Padroes repetitivos de texto
        - Horarios nao humanos (3h da manha)
        - Ausencia de indicador 'digitando'
        - Proporcao muito alta de enviadas vs recebidas
        - Muitos contatos novos em pouco tempo

        Solucao: Simular comportamento humano (delays, digitando, variedade).
        """,
        "fonte_url": "https://whautomate.com/top-reasons-why-whatsapp-accounts-get-banned-in-2025-and-how-to-avoid-them/",
        "fonte_nome": "WhAutomate Blog",
    },

    # Boas Praticas
    {
        "categoria": "boas_praticas",
        "titulo": "Boas Praticas de Messaging",
        "conteudo": """
        Recomendacoes oficiais da Meta:

        1. CONSENTIMENTO: Obter opt-in explicito antes de enviar
        2. UNSUBSCRIBE: Incluir opcao de descadastro em templates
        3. PERSONALIZACAO: Mensagens relevantes e personalizadas
        4. FREQUENCIA: Nao bombardear (max 1-2 msgs/dia por contato)
        5. HORARIO: Enviar em horario comercial (8h-20h)
        6. RESPOSTA RAPIDA: Responder dentro de 24h
        7. HUMANO DISPONIVEL: Oferecer encaminhamento para atendente
        8. PERFIL COMPLETO: Manter dados de contato atualizados
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
    {
        "categoria": "boas_praticas",
        "titulo": "Aquecimento de Conta Nova",
        "conteudo": """
        Para contas novas, seguir processo de aquecimento:

        SEMANA 1 (Dias 1-7):
        - Apenas conversas pessoais
        - Max 5-10 mensagens/dia
        - Receber mais do que enviar
        - Nao entrar em grupos

        SEMANA 2 (Dias 8-14):
        - Aumentar para 20-30 msgs/dia
        - Entrar em 2-3 grupos
        - Enviar midias variadas

        SEMANA 3 (Dias 15-21):
        - 30-50 msgs/dia
        - Mais grupos
        - Iniciar conversas comerciais leves

        APOS 21 DIAS:
        - Conta considerada "madura"
        - Menor risco de ban
        - Pode aumentar volume gradualmente
        """,
        "fonte_url": "Internal Best Practices",
        "fonte_nome": "Julia Warmer Docs",
    },

    # Proibicoes
    {
        "categoria": "proibicoes",
        "titulo": "Conteudo Absolutamente Proibido",
        "conteudo": """
        NAO enviar mensagens sobre:

        - Armas de fogo e municao
        - Drogas e substancias controladas
        - Produtos medicos restritos
        - Animais vivos (exceto gado)
        - Especies ameacadas
        - Jogos de azar com dinheiro real
        - Conteudo adulto/sexual
        - Servicos de encontros
        - Marketing multinivel
        - Credito consignado/adiantamento salario
        - Conteudo discriminatorio
        - Informacoes falsas/enganosas

        Violacao = ban permanente.
        """,
        "fonte_url": "https://business.whatsapp.com/policy",
        "fonte_nome": "WhatsApp Business Policy",
    },
]


async def seed_politicas():
    """Popula banco com politicas iniciais."""
    count = 0

    for politica in POLITICAS_SEED:
        try:
            # Gerar embedding
            embedding = await gerar_embedding(politica["conteudo"])

            # Inserir no banco
            supabase.table("meta_policies").upsert({
                "categoria": politica["categoria"],
                "titulo": politica["titulo"],
                "conteudo": politica["conteudo"],
                "fonte_url": politica.get("fonte_url"),
                "fonte_nome": politica.get("fonte_nome"),
                "embedding": embedding,
            }, on_conflict="titulo").execute()

            count += 1

        except Exception as e:
            logger.error(f"[MetaRAG] Erro ao inserir politica '{politica['titulo']}': {e}")

    logger.info(f"[MetaRAG] {count}/{len(POLITICAS_SEED)} politicas inseridas/atualizadas")
    return count


async def consultar_politicas(
    pergunta: str,
    categoria: Optional[str] = None,
    limite: int = 5,
) -> List[dict]:
    """
    Consulta politicas relevantes via RAG.

    Args:
        pergunta: Texto da consulta
        categoria: Filtrar por categoria (opcional)
        limite: Max resultados

    Returns:
        Lista de politicas relevantes
    """
    try:
        # Gerar embedding da pergunta
        query_embedding = await gerar_embedding(pergunta)

        # Buscar similares via funcao RPC
        params = {
            "query_embedding": query_embedding,
            "match_threshold": 0.7,
            "match_count": limite,
        }

        if categoria:
            params["filter_categoria"] = categoria

        result = supabase.rpc("match_meta_policies", params).execute()

        return result.data or []

    except Exception as e:
        logger.error(f"[MetaRAG] Erro ao consultar politicas: {e}")

        # Fallback: busca simples por categoria
        if categoria:
            result = supabase.table("meta_policies").select(
                "id, categoria, titulo, conteudo, fonte_url"
            ).eq("categoria", categoria).limit(limite).execute()
            return result.data or []

        return []


async def verificar_conformidade(acao: str) -> dict:
    """
    Verifica se uma acao esta em conformidade com politicas.

    Args:
        acao: Descricao da acao a verificar

    Returns:
        {
            "permitido": bool,
            "riscos": ["..."],
            "recomendacoes": ["..."],
            "politicas_relacionadas": [...]
        }
    """
    # Buscar politicas relacionadas
    politicas = await consultar_politicas(acao, limite=3)

    # Analise basica de riscos
    riscos = []
    recomendacoes = []

    acao_lower = acao.lower()

    # Detectar padroes de risco
    if any(word in acao_lower for word in ["spam", "massa", "broadcast", "bulk"]):
        riscos.append("Risco de ser classificado como spam")
        recomendacoes.append("Limitar volume e personalizar mensagens")

    if any(word in acao_lower for word in ["rapido", "automatico", "bot"]):
        riscos.append("Risco de deteccao de automacao")
        recomendacoes.append("Adicionar delays humanos e indicador 'digitando'")

    if any(word in acao_lower for word in ["noite", "madrugada", "3h", "4h"]):
        riscos.append("Horario fora do comercial")
        recomendacoes.append("Enviar apenas entre 8h-20h")

    if any(word in acao_lower for word in ["novo contato", "prospeccao", "cold"]):
        riscos.append("Contato frio pode gerar bloqueios")
        recomendacoes.append("Obter consentimento antes de enviar")

    return {
        "permitido": len(riscos) == 0,
        "riscos": riscos,
        "recomendacoes": recomendacoes,
        "politicas_relacionadas": politicas,
    }


async def listar_categorias() -> List[str]:
    """Lista categorias de politicas disponiveis."""
    result = supabase.table("meta_policies").select("categoria").execute()

    categorias = list(set(p["categoria"] for p in result.data or []))
    return sorted(categorias)


async def buscar_por_categoria(categoria: str) -> List[dict]:
    """Busca todas as politicas de uma categoria."""
    result = supabase.table("meta_policies").select(
        "id, titulo, conteudo, fonte_url, fonte_nome"
    ).eq("categoria", categoria).order("titulo").execute()

    return result.data or []
