"""
Repositório para persistência de vagas atômicas.

Sprint 40 - E08: Integração e Pipeline
"""

from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.extrator_v2.types import VagaAtomica

logger = get_logger(__name__)


async def salvar_vagas_atomicas(
    vagas: List[VagaAtomica],
    mensagem_id: Optional[UUID] = None,
) -> List[UUID]:
    """
    Salva lista de vagas atômicas no banco.

    Args:
        vagas: Lista de vagas a salvar
        mensagem_id: ID da mensagem origem (para atualizar status)

    Returns:
        Lista de UUIDs das vagas criadas
    """
    if not vagas:
        return []

    ids_criados = []

    for vaga in vagas:
        try:
            dados = vaga.to_dict()

            # Campos adicionais para compatibilidade
            dados["status"] = "nova"
            dados["dados_minimos_ok"] = True
            dados["data_valida"] = True
            dados["valor_tipo"] = "fixo" if vaga.valor > 0 else "a_combinar"

            result = supabase.table("vagas_grupo").insert(dados).execute()

            if result.data:
                ids_criados.append(UUID(result.data[0]["id"]))

        except Exception as e:
            logger.error(f"Erro ao salvar vaga: {e}")
            continue

    logger.info(f"Salvas {len(ids_criados)}/{len(vagas)} vagas")
    return ids_criados


async def atualizar_mensagem_processada(
    mensagem_id: UUID, qtd_vagas: int, sucesso: bool, erro: Optional[str] = None
) -> None:
    """
    Atualiza status da mensagem após processamento.

    Args:
        mensagem_id: ID da mensagem
        qtd_vagas: Quantidade de vagas extraídas
        sucesso: Se extração foi bem-sucedida
        erro: Mensagem de erro se houver
    """
    try:
        status = "extraida_v2" if sucesso and qtd_vagas > 0 else "extracao_v2_falhou"

        supabase.table("mensagens_grupo").update(
            {
                "status": status,
                "qtd_vagas_extraidas": qtd_vagas,
                "processado_em": datetime.now(UTC).isoformat(),
                "erro_extracao": erro,
            }
        ).eq("id", str(mensagem_id)).execute()

    except Exception as e:
        logger.error(f"Erro ao atualizar mensagem {mensagem_id}: {e}")
