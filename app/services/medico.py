"""
Servico para gerenciamento de medicos.
"""

from typing import Optional
import logging

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json, cache_delete
from app.core.config import DatabaseConfig
from app.services.telefone import normalizar_telefone

logger = logging.getLogger(__name__)


async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca medico pelo numero de telefone (com cache).

    Args:
        telefone: Numero no formato 5511999999999

    Returns:
        Dados do medico ou None se nao encontrado
    """
    telefone = normalizar_telefone(telefone)
    cache_key = f"medico:telefone:{telefone}"

    # Tentar cache primeiro
    cached = await cache_get_json(cache_key)
    if cached:
        logger.debug(f"Cache hit para médico: {telefone[:8]}...")
        return cached

    try:
        # Buscar no banco (query otimizada - apenas campos necessários)
        response = (
            supabase.table("clientes")
            .select(
                "id, primeiro_nome, sobrenome, telefone, especialidade, crm, status, tags, preferencias_detectadas, stage_jornada"
            )
            .eq("telefone", telefone)
            .limit(1)
            .execute()
        )

        medico = response.data[0] if response.data else None

        # Salvar no cache se encontrado
        if medico:
            await cache_set_json(cache_key, medico, DatabaseConfig.CACHE_TTL_MEDICO)

        return medico
    except Exception as e:
        logger.error(f"Erro ao buscar medico: {e}")
        return None


async def criar_medico(telefone: str, nome: Optional[str] = None, **kwargs) -> Optional[dict]:
    """
    Cria novo registro de medico.

    Args:
        telefone: Numero obrigatorio
        nome: Nome do contato (do WhatsApp)
        **kwargs: Outros campos opcionais

    Returns:
        Dados do medico criado
    """
    telefone = normalizar_telefone(telefone)
    try:
        dados = {
            "telefone": telefone,
            "stage_jornada": "novo",
            "origem": "whatsapp_inbound",
        }

        if nome:
            # Tentar separar primeiro nome e sobrenome
            partes = nome.split(" ", 1)
            dados["primeiro_nome"] = partes[0]
            if len(partes) > 1:
                dados["sobrenome"] = partes[1]

        dados.update(kwargs)

        response = supabase.table("clientes").insert(dados).execute()
        logger.info(f"Medico criado: {telefone}")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao criar medico: {e}")
        return None


async def buscar_ou_criar_medico(
    telefone: str, nome_whatsapp: Optional[str] = None
) -> Optional[dict]:
    """
    Busca medico existente ou cria novo.

    Args:
        telefone: Numero do telefone
        nome_whatsapp: Nome vindo do WhatsApp (pushName)

    Returns:
        Dados do medico (existente ou novo)
    """
    # Tentar buscar existente
    medico = await buscar_medico_por_telefone(telefone)

    if medico:
        logger.debug(f"Medico encontrado: {medico.get('primeiro_nome', telefone)}")

        # Atualizar nome se nao tinha
        if nome_whatsapp and not medico.get("primeiro_nome"):
            await atualizar_medico(medico["id"], primeiro_nome=nome_whatsapp.split()[0])

        return medico

    # Criar novo
    logger.info(f"Criando novo medico: {telefone}")
    return await criar_medico(telefone, nome=nome_whatsapp)


async def atualizar_medico(medico_id: str, **campos) -> Optional[dict]:
    """Atualiza campos do medico e invalida cache."""
    try:
        response = supabase.table("clientes").update(campos).eq("id", medico_id).execute()

        medico = response.data[0] if response.data else None

        # Invalidar cache após atualização
        if medico:
            telefone = medico.get("telefone")
            if telefone:
                await cache_delete(f"medico:telefone:{telefone}")
            await cache_delete(f"medico:id:{medico_id}")

        return medico
    except Exception as e:
        logger.error(f"Erro ao atualizar medico: {e}")
        return None


async def atualizar_stage(medico_id: str, novo_stage: str) -> bool:
    """Atualiza stage da jornada do medico."""
    result = await atualizar_medico(medico_id, stage_jornada=novo_stage)
    return result is not None


async def marcar_opt_out(medico_id: str) -> bool:
    """Marca medico como opt-out (nao quer mais receber mensagens)."""
    result = await atualizar_medico(medico_id, opt_out=True)
    return result is not None
