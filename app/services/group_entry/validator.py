"""
Validador de links de grupos.

Sprint 25 - E12 - S12.2

Verifica se o link é válido antes de tentar entrar.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC

from app.services.supabase import supabase
from app.services.whatsapp import EvolutionClient

logger = logging.getLogger(__name__)


async def validar_link(
    invite_code: str,
    chip_id: Optional[str] = None,
) -> dict:
    """
    Valida se um link de grupo é válido.

    Args:
        invite_code: Código de convite
        chip_id: ID do chip a usar (opcional, usa qualquer ativo)

    Returns:
        {
            "valido": bool,
            "grupo_nome": str,
            "grupo_tamanho": int,
            "erro": str (se inválido)
        }
    """
    # Buscar chip para validação
    if chip_id:
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        chip = result.data
    else:
        # Usar qualquer chip listener ativo
        result = (
            supabase.table("chips")
            .select("*")
            .eq("tipo", "listener")
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        chip = result.data[0] if result.data else None

        # Se não tiver listener, tenta julia
        if not chip:
            result = supabase.table("chips").select("*").eq("status", "active").limit(1).execute()
            chip = result.data[0] if result.data else None

    if not chip:
        return {"valido": False, "erro": "Nenhum chip disponível para validação"}

    # Buscar info do grupo via Evolution API
    client = EvolutionClient(instance=chip["instance_name"])

    try:
        info = await client.buscar_info_grupo_por_invite(invite_code)

        if info:
            return {
                "valido": True,
                "grupo_nome": info.get("subject", ""),
                "grupo_tamanho": info.get("size", 0),
                "grupo_descricao": info.get("desc", ""),
            }
        else:
            return {"valido": False, "erro": "Link inválido ou expirado"}

    except Exception as e:
        logger.warning(f"[GroupValidator] Erro ao validar {invite_code}: {e}")
        return {"valido": False, "erro": str(e)}


async def validar_links_pendentes(limite: int = 50) -> dict:
    """
    Valida batch de links pendentes.

    Args:
        limite: Quantidade máxima a validar

    Returns:
        {
            "validados": N,
            "invalidos": N,
            "erros": N
        }
    """
    # Buscar links pendentes
    result = (
        supabase.table("group_links").select("*").eq("status", "pendente").limit(limite).execute()
    )

    if not result.data:
        logger.info("[GroupValidator] Nenhum link pendente para validar")
        return {"validados": 0, "invalidos": 0, "erros": 0}

    links = result.data
    resultado = {"validados": 0, "invalidos": 0, "erros": 0}

    for link in links:
        try:
            validacao = await validar_link(link["invite_code"])

            if validacao.get("valido"):
                # Atualizar como validado
                supabase.table("group_links").update(
                    {
                        "status": "validado",
                        "nome": validacao.get("grupo_nome") or link.get("nome"),
                        "validado_em": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", link["id"]).execute()

                resultado["validados"] += 1
                logger.debug(f"[GroupValidator] Link validado: {link['invite_code']}")

            else:
                # Marcar como inválido
                supabase.table("group_links").update(
                    {
                        "status": "invalido",
                        "ultimo_erro": validacao.get("erro", "Link inválido"),
                        "validado_em": datetime.now(UTC).isoformat(),
                    }
                ).eq("id", link["id"]).execute()

                resultado["invalidos"] += 1
                logger.debug(
                    f"[GroupValidator] Link inválido: {link['invite_code']} - {validacao.get('erro')}"
                )

        except Exception as e:
            logger.error(f"[GroupValidator] Erro ao validar {link['invite_code']}: {e}")
            resultado["erros"] += 1

    logger.info(
        f"[GroupValidator] Batch concluído: "
        f"{resultado['validados']} validados, "
        f"{resultado['invalidos']} inválidos, "
        f"{resultado['erros']} erros"
    )

    return resultado


async def revalidar_link(link_id: str) -> dict:
    """
    Revalida um link específico (para links marcados como inválidos ou erro).

    Args:
        link_id: ID do link

    Returns:
        Resultado da validação
    """
    result = supabase.table("group_links").select("*").eq("id", link_id).single().execute()

    if not result.data:
        return {"erro": "Link não encontrado"}

    link = result.data
    validacao = await validar_link(link["invite_code"])

    if validacao.get("valido"):
        supabase.table("group_links").update(
            {
                "status": "validado",
                "nome": validacao.get("grupo_nome") or link.get("nome"),
                "validado_em": datetime.now(UTC).isoformat(),
                "ultimo_erro": None,
            }
        ).eq("id", link_id).execute()
    else:
        supabase.table("group_links").update(
            {
                "status": "invalido",
                "ultimo_erro": validacao.get("erro"),
                "validado_em": datetime.now(UTC).isoformat(),
            }
        ).eq("id", link_id).execute()

    return validacao


async def buscar_links_para_validar(limite: int = 100) -> List[dict]:
    """
    Busca links que precisam ser validados.

    Prioriza:
    1. Links pendentes (nunca validados)
    2. Links com erro (para retry)
    3. Links validados há mais de 7 dias (revalidação)

    Args:
        limite: Quantidade máxima

    Returns:
        Lista de links
    """
    # Primeiro: pendentes
    result = (
        supabase.table("group_links").select("*").eq("status", "pendente").limit(limite).execute()
    )

    links = result.data or []

    # Se ainda tem espaço, buscar com erro para retry
    if len(links) < limite:
        restante = limite - len(links)
        result = (
            supabase.table("group_links")
            .select("*")
            .eq("status", "erro")
            .lt("tentativas", 3)  # Max 3 tentativas
            .limit(restante)
            .execute()
        )
        links.extend(result.data or [])

    return links
