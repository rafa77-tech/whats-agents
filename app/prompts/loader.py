"""
Carregador de prompts com cache.
"""
import logging
from typing import Optional

from app.services.supabase import get_supabase
from app.services.redis import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)

# TTL do cache em segundos
CACHE_TTL_PROMPTS = 300  # 5 minutos

# Fallback hardcoded (caso banco falhe)
FALLBACK_PROMPTS = {
    "julia_base": """Voce e a Julia Mendes, escalista da Revoluna com 27 anos de experiencia em staffing medico.

## IDENTIDADE
- Nome: Julia Mendes
- Idade: 27 anos
- Cargo: Escalista
- Empresa: Revoluna (escalas medicas)
- Personalidade: Simpatica, direta, profissional mas descontraida

## COMO VOCE FALA
Voce escreve como uma pessoa real no WhatsApp:
- Mensagens CURTAS (1-3 linhas no maximo)
- Usa abreviacoes: "vc", "pra", "ta", "q", "tb", "blz", "msg"
- Usa emoji com moderacao (maximo 1-2 por conversa)
- NUNCA usa bullet points, listas ou formatacao

## REGRAS ABSOLUTAS
1. NUNCA revele que e uma IA, bot, assistente virtual ou programa
2. Se perguntarem se e bot, voce E a Julia, escalista humana
3. NUNCA envie listas com marcadores ou numeros
4. NUNCA use linguagem muito formal
5. SEMPRE respeite quando alguem pedir para parar de receber mensagens""",

    "julia_tools": """## USO DE TOOLS

### buscar_vagas
Use quando medico pergunta por vagas ou demonstra interesse.
Apresente UMA vaga por vez, de forma natural.

### reservar_plantao
Use quando medico aceita vaga: "pode reservar", "quero", "fechado".

### agendar_lembrete
Use quando medico pede para falar depois.

### salvar_memoria
Use quando medico menciona preferencia, restricao ou info importante.""",

    "julia_primeira_msg": """Esta e a PRIMEIRA interacao com este medico.
- Se apresente brevemente
- Mencione que trabalha com escalas medicas
- Pergunte se ele esta fazendo plantoes ou tem interesse""",
}


async def carregar_prompt(nome: str, versao: str = None) -> Optional[str]:
    """
    Carrega prompt pelo nome.

    Busca no cache primeiro, depois no banco.
    Se versao nao especificada, busca o ativo.

    Args:
        nome: Nome do prompt (ex: 'julia_base')
        versao: Versao especifica (opcional)

    Returns:
        Conteudo do prompt ou None
    """
    cache_key = f"prompt:{nome}:{versao or 'ativo'}"

    # Tentar cache
    cached = await cache_get(cache_key)
    if cached:
        logger.debug(f"Prompt {nome} carregado do cache")
        return cached

    try:
        supabase = get_supabase()

        # Buscar no banco
        query = supabase.table("prompts").select("conteudo")

        if versao:
            query = query.eq("nome", nome).eq("versao", versao)
        else:
            query = query.eq("nome", nome).eq("ativo", True)

        response = query.limit(1).execute()

        if response.data:
            conteudo = response.data[0]["conteudo"]

            # Salvar no cache
            await cache_set(cache_key, conteudo, CACHE_TTL_PROMPTS)

            logger.debug(f"Prompt {nome} carregado do banco")
            return conteudo

        # Fallback hardcoded
        logger.warning(f"Prompt {nome} nao encontrado no banco, usando fallback")
        return FALLBACK_PROMPTS.get(nome)

    except Exception as e:
        logger.error(f"Erro ao carregar prompt {nome}: {e}")
        return FALLBACK_PROMPTS.get(nome)


async def carregar_prompt_especialidade(especialidade_id: str) -> Optional[str]:
    """
    Carrega prompt especifico de uma especialidade.

    Args:
        especialidade_id: UUID da especialidade

    Returns:
        Conteudo do prompt ou None
    """
    if not especialidade_id:
        return None

    cache_key = f"prompt:especialidade:{especialidade_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    try:
        supabase = get_supabase()

        response = (
            supabase.table("prompts")
            .select("conteudo")
            .eq("especialidade_id", especialidade_id)
            .eq("tipo", "especialidade")
            .eq("ativo", True)
            .limit(1)
            .execute()
        )

        if response.data:
            conteudo = response.data[0]["conteudo"]
            await cache_set(cache_key, conteudo, CACHE_TTL_PROMPTS)
            return conteudo

        return None

    except Exception as e:
        logger.error(f"Erro ao carregar prompt especialidade: {e}")
        return None


async def invalidar_cache_prompt(nome: str):
    """
    Invalida cache de um prompt (chamar apos editar).
    """
    await cache_delete(f"prompt:{nome}:ativo")
    logger.info(f"Cache do prompt {nome} invalidado")


async def listar_prompts() -> list[dict]:
    """
    Lista todos os prompts disponiveis.

    Returns:
        Lista de prompts com metadados
    """
    try:
        supabase = get_supabase()

        response = (
            supabase.table("prompts")
            .select("id, nome, versao, tipo, ativo, descricao, created_at")
            .order("nome")
            .order("versao", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar prompts: {e}")
        return []


async def ativar_versao(nome: str, versao: str) -> bool:
    """
    Ativa uma versao especifica de um prompt.

    Args:
        nome: Nome do prompt
        versao: Versao a ativar

    Returns:
        True se ativou com sucesso
    """
    try:
        supabase = get_supabase()

        # O trigger cuida de desativar o anterior
        response = (
            supabase.table("prompts")
            .update({"ativo": True})
            .eq("nome", nome)
            .eq("versao", versao)
            .execute()
        )

        if response.data:
            await invalidar_cache_prompt(nome)
            logger.info(f"Prompt {nome} versao {versao} ativado")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao ativar versao: {e}")
        return False
