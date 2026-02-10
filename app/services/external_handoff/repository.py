"""
Repository para external_handoffs.

Sprint 20 - E03 - Operacoes de banco.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def criar_handoff(
    vaga_id: str,
    cliente_id: str,
    divulgador_nome: str,
    divulgador_telefone: str,
    divulgador_empresa: str,
    reserved_until: datetime,
) -> dict:
    """
    Cria registro de external handoff.

    Args:
        vaga_id: UUID da vaga
        cliente_id: UUID do medico
        divulgador_nome: Nome do divulgador
        divulgador_telefone: Telefone do divulgador
        divulgador_empresa: Empresa do divulgador
        reserved_until: Prazo para confirmacao

    Returns:
        Dict com dados do handoff criado
    """
    dados = {
        "vaga_id": vaga_id,
        "cliente_id": cliente_id,
        "divulgador_nome": divulgador_nome,
        "divulgador_telefone": divulgador_telefone,
        "divulgador_empresa": divulgador_empresa,
        "status": "pending",
        "reserved_until": reserved_until.isoformat(),
    }

    try:
        response = supabase.table("external_handoffs").insert(dados).execute()

        if response.data:
            handoff = response.data[0]
            logger.info(f"Handoff criado: {handoff['id']}")
            return handoff

        raise Exception("Falha ao criar handoff")

    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            logger.warning(f"Handoff duplicado para vaga={vaga_id}, cliente={cliente_id}")
            # Buscar existente
            return await buscar_handoff_existente(vaga_id, cliente_id)

        logger.error(f"Erro ao criar handoff: {e}")
        raise


async def buscar_handoff_por_id(handoff_id: str) -> Optional[dict]:
    """
    Busca handoff por ID.

    Args:
        handoff_id: UUID do handoff

    Returns:
        Dict com dados do handoff ou None
    """
    try:
        response = supabase.table("external_handoffs").select("*").eq("id", handoff_id).execute()

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff {handoff_id}: {e}")
        return None


async def buscar_handoff_existente(vaga_id: str, cliente_id: str) -> Optional[dict]:
    """
    Busca handoff existente para vaga e cliente.

    Args:
        vaga_id: UUID da vaga
        cliente_id: UUID do medico

    Returns:
        Dict com dados do handoff ou None
    """
    try:
        response = (
            supabase.table("external_handoffs")
            .select("*")
            .eq("vaga_id", vaga_id)
            .eq("cliente_id", cliente_id)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff existente: {e}")
        return None


async def buscar_handoff_pendente_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca handoff pendente pelo telefone do divulgador.

    Args:
        telefone: Telefone do divulgador (com ou sem formatacao)

    Returns:
        Handoff pendente ou None
    """
    # Normalizar telefone (remover formatacao)
    telefone_normalizado = re.sub(r"\D", "", telefone)

    # Buscar apenas os ultimos 8-9 digitos para flexibilidade
    if len(telefone_normalizado) > 9:
        telefone_sufixo = telefone_normalizado[-9:]
    else:
        telefone_sufixo = telefone_normalizado

    try:
        response = (
            supabase.table("external_handoffs")
            .select("*")
            .in_("status", ["pending", "contacted"])
            .like("divulgador_telefone", f"%{telefone_sufixo}")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff por telefone: {e}")
        return None


async def atualizar_status_handoff(
    handoff_id: str,
    novo_status: str,
    confirmed_at: datetime = None,
    confirmed_by: str = None,
    confirmation_source: str = None,
    expired_at: datetime = None,
) -> bool:
    """
    Atualiza status do handoff.

    Args:
        handoff_id: UUID do handoff
        novo_status: Novo status
        confirmed_at: Timestamp de confirmacao
        confirmed_by: 'link' ou 'keyword'
        confirmation_source: Detalhes adicionais
        expired_at: Timestamp de expiracao

    Returns:
        True se atualizado com sucesso
    """
    dados = {"status": novo_status}

    if confirmed_at:
        dados["confirmed_at"] = confirmed_at.isoformat()
    if confirmed_by:
        dados["confirmed_by"] = confirmed_by
    if confirmation_source:
        dados["confirmation_source"] = confirmation_source
    if expired_at:
        dados["expired_at"] = expired_at.isoformat()

    try:
        supabase.table("external_handoffs").update(dados).eq("id", handoff_id).execute()

        logger.info(f"Handoff {handoff_id[:8]} atualizado para {novo_status}")
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar handoff {handoff_id}: {e}")
        return False


async def listar_handoffs_pendentes() -> List[dict]:
    """
    Lista todos os handoffs com status pendente ou contacted.

    Returns:
        Lista de handoffs
    """
    try:
        response = (
            supabase.table("external_handoffs")
            .select("*")
            .in_("status", ["pending", "contacted"])
            .order("created_at", desc=False)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar handoffs pendentes: {e}")
        return []


async def atualizar_followup(handoff_id: str, followup_count: int) -> bool:
    """
    Atualiza contador de follow-up.

    Args:
        handoff_id: UUID do handoff
        followup_count: Novo contador

    Returns:
        True se atualizado com sucesso
    """
    try:
        supabase.table("external_handoffs").update(
            {
                "followup_count": followup_count,
                "last_followup_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", handoff_id).execute()

        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar follow-up: {e}")
        return False
