"""
Serviço de Gestão de Hospitais Bloqueados.

Sprint 32 E12 - Bloquear/desbloquear hospitais.

Quando um hospital é bloqueado:
1. Registro criado em hospitais_bloqueados
2. Vagas do hospital movidas para vagas_hospitais_bloqueados
3. Julia não vê mais essas vagas (consulta tabela vagas normalmente)

Quando hospital é desbloqueado:
1. Registro atualizado
2. Vagas válidas restauradas para tabela vagas
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

STATUS_BLOQUEADO = "bloqueado"
STATUS_DESBLOQUEADO = "desbloqueado"


# =============================================================================
# FUNÇÕES PRINCIPAIS
# =============================================================================

async def bloquear_hospital(
    hospital_id: str,
    motivo: str,
    bloqueado_por: str,
    notificar_slack: bool = True,
) -> dict:
    """
    Bloqueia um hospital.

    1. Cria registro em hospitais_bloqueados
    2. Move vagas do hospital para vagas_hospitais_bloqueados
    3. Notifica no Slack

    Args:
        hospital_id: ID do hospital
        motivo: Motivo do bloqueio
        bloqueado_por: Quem bloqueou
        notificar_slack: Se deve notificar no Slack

    Returns:
        Dict com resultado do bloqueio
    """
    try:
        # Verificar se hospital existe
        hospital = await _buscar_hospital(hospital_id)
        if not hospital:
            return {"success": False, "error": "Hospital não encontrado"}

        # Verificar se já está bloqueado
        bloqueio_existente = await verificar_hospital_bloqueado(hospital_id)
        if bloqueio_existente:
            return {"success": False, "error": "Hospital já está bloqueado"}

        # Criar registro de bloqueio
        bloqueio_id = str(uuid4())
        supabase.table("hospitais_bloqueados").insert({
            "id": bloqueio_id,
            "hospital_id": hospital_id,
            "motivo": motivo,
            "bloqueado_por": bloqueado_por,
            "status": STATUS_BLOQUEADO,
        }).execute()

        # Mover vagas para tabela de bloqueados
        vagas_movidas = await _mover_vagas_para_bloqueados(
            hospital_id=hospital_id,
            motivo=motivo,
            movido_por=bloqueado_por,
        )

        logger.info(f"Hospital {hospital_id} bloqueado. {vagas_movidas} vagas movidas.")

        # Notificar no Slack
        if notificar_slack:
            await _notificar_bloqueio(
                hospital_nome=hospital.get("nome", "Hospital"),
                motivo=motivo,
                bloqueado_por=bloqueado_por,
                vagas_afetadas=vagas_movidas,
            )

        return {
            "success": True,
            "bloqueio_id": bloqueio_id,
            "hospital_id": hospital_id,
            "vagas_movidas": vagas_movidas,
        }

    except Exception as e:
        logger.error(f"Erro ao bloquear hospital: {e}")
        return {"success": False, "error": str(e)}


async def desbloquear_hospital(
    hospital_id: str,
    desbloqueado_por: str,
    restaurar_vagas: bool = True,
    notificar_slack: bool = True,
) -> dict:
    """
    Desbloqueia um hospital.

    1. Atualiza registro em hospitais_bloqueados
    2. Restaura vagas válidas de volta para tabela vagas
    3. Notifica no Slack

    Args:
        hospital_id: ID do hospital
        desbloqueado_por: Quem desbloqueou
        restaurar_vagas: Se deve restaurar vagas válidas
        notificar_slack: Se deve notificar no Slack

    Returns:
        Dict com resultado do desbloqueio
    """
    try:
        # Verificar se está bloqueado
        bloqueio = await verificar_hospital_bloqueado(hospital_id)
        if not bloqueio:
            return {"success": False, "error": "Hospital não está bloqueado"}

        # Atualizar registro
        supabase.table("hospitais_bloqueados").update({
            "status": STATUS_DESBLOQUEADO,
            "desbloqueado_por": desbloqueado_por,
            "desbloqueado_em": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("hospital_id", hospital_id).eq("status", STATUS_BLOQUEADO).execute()

        # Restaurar vagas válidas
        vagas_restauradas = 0
        if restaurar_vagas:
            vagas_restauradas = await _restaurar_vagas_de_bloqueados(
                hospital_id=hospital_id,
            )

        # Buscar nome do hospital
        hospital = await _buscar_hospital(hospital_id)
        hospital_nome = hospital.get("nome", "Hospital") if hospital else "Hospital"

        logger.info(f"Hospital {hospital_id} desbloqueado. {vagas_restauradas} vagas restauradas.")

        # Notificar no Slack
        if notificar_slack:
            await _notificar_desbloqueio(
                hospital_nome=hospital_nome,
                desbloqueado_por=desbloqueado_por,
                vagas_restauradas=vagas_restauradas,
            )

        return {
            "success": True,
            "hospital_id": hospital_id,
            "vagas_restauradas": vagas_restauradas,
        }

    except Exception as e:
        logger.error(f"Erro ao desbloquear hospital: {e}")
        return {"success": False, "error": str(e)}


async def verificar_hospital_bloqueado(hospital_id: str) -> Optional[dict]:
    """
    Verifica se hospital está bloqueado.

    Args:
        hospital_id: ID do hospital

    Returns:
        Dict com dados do bloqueio ou None
    """
    try:
        response = (
            supabase.table("hospitais_bloqueados")
            .select("*")
            .eq("hospital_id", hospital_id)
            .eq("status", STATUS_BLOQUEADO)
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao verificar bloqueio: {e}")
        return None


async def listar_hospitais_bloqueados() -> list[dict]:
    """
    Lista todos os hospitais atualmente bloqueados.

    Returns:
        Lista de bloqueios ativos com dados do hospital
    """
    try:
        response = (
            supabase.table("hospitais_bloqueados")
            .select("*, hospitais:hospital_id(id, nome, cidade, estado)")
            .eq("status", STATUS_BLOQUEADO)
            .order("bloqueado_em", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar hospitais bloqueados: {e}")
        return []


async def obter_historico_bloqueios(hospital_id: str) -> list[dict]:
    """
    Obtém histórico de bloqueios de um hospital.

    Args:
        hospital_id: ID do hospital

    Returns:
        Lista de bloqueios (ativos e inativos)
    """
    try:
        response = (
            supabase.table("hospitais_bloqueados")
            .select("*")
            .eq("hospital_id", hospital_id)
            .order("bloqueado_em", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao obter histórico: {e}")
        return []


async def contar_vagas_bloqueadas(hospital_id: Optional[str] = None) -> int:
    """
    Conta vagas em hospitais bloqueados.

    Args:
        hospital_id: Opcional - filtrar por hospital

    Returns:
        Número de vagas bloqueadas
    """
    try:
        query = (
            supabase.table("vagas_hospitais_bloqueados")
            .select("id", count="exact")
        )

        if hospital_id:
            query = query.eq("hospital_id", hospital_id)

        response = query.execute()

        return response.count or 0

    except Exception as e:
        logger.error(f"Erro ao contar vagas bloqueadas: {e}")
        return 0


# =============================================================================
# FUNÇÕES INTERNAS
# =============================================================================

async def _buscar_hospital(hospital_id: str) -> Optional[dict]:
    """Busca dados de um hospital."""
    try:
        response = (
            supabase.table("hospitais")
            .select("id, nome, cidade, estado")
            .eq("id", hospital_id)
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao buscar hospital: {e}")
        return None


async def _mover_vagas_para_bloqueados(
    hospital_id: str,
    motivo: str,
    movido_por: str,
) -> int:
    """Move vagas de um hospital para tabela de bloqueados."""
    try:
        # Buscar vagas do hospital
        response = (
            supabase.table("vagas")
            .select("*")
            .eq("hospital_id", hospital_id)
            .is_("deleted_at", "null")
            .execute()
        )

        vagas = response.data or []
        movidas = 0

        for vaga in vagas:
            try:
                # Inserir na tabela de bloqueados
                supabase.table("vagas_hospitais_bloqueados").insert({
                    "id": vaga["id"],
                    "hospital_id": vaga["hospital_id"],
                    "data": vaga.get("data"),
                    "valor": vaga.get("valor"),
                    "status": vaga.get("status"),
                    "especialidade_id": vaga.get("especialidade_id"),
                    "setor_id": vaga.get("setor_id"),
                    "periodo_id": vaga.get("periodo_id"),
                    "cliente_id": vaga.get("cliente_id"),
                    "tipo_vaga_id": vaga.get("tipo_vaga_id"),
                    "forma_recebimento_id": vaga.get("forma_recebimento_id"),
                    "observacoes": vaga.get("observacoes"),
                    "dados_originais": json.dumps(vaga),
                    "movido_por": movido_por,
                    "motivo_bloqueio": motivo,
                }).execute()

                # Soft delete na tabela original
                supabase.table("vagas").update({
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", vaga["id"]).execute()

                movidas += 1

            except Exception as e:
                logger.error(f"Erro ao mover vaga {vaga['id']}: {e}")

        return movidas

    except Exception as e:
        logger.error(f"Erro ao mover vagas: {e}")
        return 0


async def _restaurar_vagas_de_bloqueados(hospital_id: str) -> int:
    """Restaura vagas válidas de volta para tabela vagas."""
    hoje = datetime.now(timezone.utc).date()

    try:
        # Buscar vagas bloqueadas do hospital
        response = (
            supabase.table("vagas_hospitais_bloqueados")
            .select("*")
            .eq("hospital_id", hospital_id)
            .execute()
        )

        vagas = response.data or []
        restauradas = 0

        for vaga in vagas:
            try:
                # Verificar se vaga ainda é válida (data futura e status aberta)
                data_vaga = vaga.get("data")
                status = vaga.get("status")

                if data_vaga:
                    from datetime import datetime as dt
                    data_obj = dt.strptime(data_vaga, "%Y-%m-%d").date()
                    if data_obj < hoje:
                        # Vaga passada, não restaurar
                        continue

                # Restaurar dados originais
                dados_originais = json.loads(vaga.get("dados_originais", "{}"))

                if dados_originais:
                    # Remover deleted_at para restaurar
                    dados_originais["deleted_at"] = None
                    dados_originais["updated_at"] = datetime.now(timezone.utc).isoformat()

                    # Atualizar na tabela vagas (upsert)
                    supabase.table("vagas").upsert(dados_originais).execute()

                # Remover da tabela de bloqueados
                supabase.table("vagas_hospitais_bloqueados").delete().eq("id", vaga["id"]).execute()

                restauradas += 1

            except Exception as e:
                logger.error(f"Erro ao restaurar vaga {vaga['id']}: {e}")

        return restauradas

    except Exception as e:
        logger.error(f"Erro ao restaurar vagas: {e}")
        return 0


async def _notificar_bloqueio(
    hospital_nome: str,
    motivo: str,
    bloqueado_por: str,
    vagas_afetadas: int,
):
    """Notifica bloqueio no Slack."""
    mensagem = {
        "text": f"🚫 Hospital bloqueado: {hospital_nome}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚫 Hospital Bloqueado",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Hospital:*\n{hospital_nome}"},
                    {"type": "mrkdwn", "text": f"*Bloqueado por:*\n{bloqueado_por}"},
                    {"type": "mrkdwn", "text": f"*Motivo:*\n{motivo}"},
                    {"type": "mrkdwn", "text": f"*Vagas afetadas:*\n{vagas_afetadas}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Julia não oferecerá mais vagas deste hospital."}
                ]
            }
        ]
    }

    await enviar_slack(mensagem, force=True)


async def _notificar_desbloqueio(
    hospital_nome: str,
    desbloqueado_por: str,
    vagas_restauradas: int,
):
    """Notifica desbloqueio no Slack."""
    mensagem = {
        "text": f"✅ Hospital desbloqueado: {hospital_nome}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✅ Hospital Desbloqueado",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Hospital:*\n{hospital_nome}"},
                    {"type": "mrkdwn", "text": f"*Desbloqueado por:*\n{desbloqueado_por}"},
                    {"type": "mrkdwn", "text": f"*Vagas restauradas:*\n{vagas_restauradas}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Julia voltará a oferecer vagas deste hospital."}
                ]
            }
        ]
    }

    await enviar_slack(mensagem, force=True)


# =============================================================================
# FUNÇÃO PARA INTEGRAÇÃO COM JULIA
# =============================================================================

async def hospital_esta_bloqueado(hospital_id: str) -> bool:
    """
    Verifica rapidamente se hospital está bloqueado.

    Uso no agente:
    ```python
    if await hospital_esta_bloqueado(vaga["hospital_id"]):
        # Não oferecer esta vaga
        continue
    ```

    Args:
        hospital_id: ID do hospital

    Returns:
        True se bloqueado
    """
    bloqueio = await verificar_hospital_bloqueado(hospital_id)
    return bloqueio is not None
