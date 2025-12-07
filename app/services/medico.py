"""
Servico para gerenciamento de medicos.
"""
from typing import Optional
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca medico pelo numero de telefone.

    Args:
        telefone: Numero no formato 5511999999999

    Returns:
        Dados do medico ou None se nao encontrado
    """
    try:
        response = (
            supabase.table("clientes")
            .select("*")
            .eq("telefone", telefone)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar medico: {e}")
        return None


async def criar_medico(
    telefone: str,
    nome: Optional[str] = None,
    **kwargs
) -> Optional[dict]:
    """
    Cria novo registro de medico.

    Args:
        telefone: Numero obrigatorio
        nome: Nome do contato (do WhatsApp)
        **kwargs: Outros campos opcionais

    Returns:
        Dados do medico criado
    """
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
    telefone: str,
    nome_whatsapp: Optional[str] = None
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
    """Atualiza campos do medico."""
    try:
        response = (
            supabase.table("clientes")
            .update(campos)
            .eq("id", medico_id)
            .execute()
        )
        return response.data[0] if response.data else None
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
