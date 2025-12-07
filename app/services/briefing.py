"""
Servico de sincronizacao de briefing com Google Docs.

Sincroniza diretrizes do gestor a partir de um documento
Google Docs, atualizando o banco de dados com as configuracoes.
"""
from datetime import datetime, timezone
from typing import Optional
import logging
import json

from app.services.google_docs import buscar_documento_briefing, verificar_configuracao
from app.services.briefing_parser import parsear_briefing, validar_briefing
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)

# Cache do ultimo hash processado
_ultimo_hash: Optional[str] = None


async def sincronizar_briefing() -> dict:
    """
    Sincroniza briefing do Google Docs com o banco.

    Executado a cada 60 minutos pelo scheduler.

    Returns:
        dict com status da sincronizacao
    """
    global _ultimo_hash

    # 0. Verificar configuracao
    config = verificar_configuracao()
    if not config["configurado"]:
        logger.warning(f"Google Docs nao configurado: {config['erros']}")
        return {
            "success": False,
            "error": "Google Docs nao configurado",
            "detalhes": config["erros"]
        }

    # 1. Buscar documento
    doc = await buscar_documento_briefing()
    if not doc.get("success"):
        return {"success": False, "error": doc.get("error")}

    # 2. Verificar se mudou
    if doc["hash"] == _ultimo_hash:
        logger.debug("Briefing nao mudou desde ultima verificacao")
        return {"success": True, "changed": False}

    logger.info(f"Briefing mudou! Hash anterior: {_ultimo_hash}, novo: {doc['hash']}")

    # 3. Parsear conteudo
    briefing = parsear_briefing(doc["content"])

    # 4. Validar estrutura
    validacao = validar_briefing(briefing)
    if validacao["avisos"]:
        logger.warning(f"Avisos no briefing: {validacao['avisos']}")

    # 5. Atualizar diretrizes no banco
    await _atualizar_diretrizes(briefing)

    # 6. Atualizar medicos VIP/bloqueados
    await _atualizar_medicos_vip(briefing.get("medicos_vip", []))
    await _atualizar_medicos_bloqueados(briefing.get("medicos_bloqueados", []))

    # 7. Atualizar vagas prioritarias
    await _atualizar_vagas_prioritarias(briefing.get("vagas_prioritarias", []))

    # 8. Salvar registro de sincronizacao
    try:
        supabase.table("briefing_sync_log").insert({
            "doc_hash": doc["hash"],
            "doc_title": doc["title"],
            "conteudo_raw": doc["content"][:5000],  # Limitar tamanho
            "parseado": json.dumps(briefing, ensure_ascii=False, default=str),
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao salvar log de sincronizacao: {e}")

    # 9. Notificar no Slack
    await _notificar_atualizacao(briefing)

    # 10. Atualizar cache
    _ultimo_hash = doc["hash"]

    return {
        "success": True,
        "changed": True,
        "hash": doc["hash"],
        "titulo": briefing.get("titulo"),
        "secoes_atualizadas": validacao["secoes_encontradas"],
        "avisos": validacao["avisos"]
    }


async def _atualizar_diretrizes(briefing: dict):
    """Atualiza tabela de diretrizes com novo briefing."""
    try:
        # Foco da semana
        if briefing.get("foco_semana"):
            await _upsert_diretriz(
                tipo="foco_semana",
                conteudo="\n".join(briefing["foco_semana"]),
                prioridade=10
            )

        # Tom da semana
        if briefing.get("tom_semana"):
            await _upsert_diretriz(
                tipo="tom_semana",
                conteudo="\n".join(briefing["tom_semana"]),
                prioridade=9
            )

        # Margem de negociacao
        if briefing.get("margem_negociacao"):
            await _upsert_diretriz(
                tipo="margem_negociacao",
                conteudo=str(briefing["margem_negociacao"]),
                prioridade=8
            )

        # Observacoes
        if briefing.get("observacoes"):
            await _upsert_diretriz(
                tipo="observacoes",
                conteudo="\n".join(briefing["observacoes"]),
                prioridade=5
            )

        logger.info("Diretrizes atualizadas com sucesso")

    except Exception as e:
        logger.error(f"Erro ao atualizar diretrizes: {e}")


async def _upsert_diretriz(tipo: str, conteudo: str, prioridade: int):
    """Insere ou atualiza diretriz."""
    try:
        # Verificar se existe
        existing = supabase.table("diretrizes").select("id").eq("tipo", tipo).execute()

        if existing.data:
            supabase.table("diretrizes").update({
                "conteudo": conteudo,
                "prioridade": prioridade,
                "ativo": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("tipo", tipo).execute()
        else:
            supabase.table("diretrizes").insert({
                "tipo": tipo,
                "conteudo": conteudo,
                "prioridade": prioridade,
                "ativo": True
            }).execute()

    except Exception as e:
        logger.error(f"Erro ao upsert diretriz {tipo}: {e}")


async def _atualizar_medicos_vip(medicos: list):
    """Marca medicos como VIP baseado no briefing."""
    for med in medicos:
        crm = med.get("crm")
        if crm:
            try:
                supabase.table("clientes").update({
                    "vip": True,
                    "notas_vip": med.get("observacao", "")
                }).eq("crm", crm).execute()
                logger.debug(f"Medico CRM {crm} marcado como VIP")
            except Exception as e:
                logger.error(f"Erro ao marcar medico {crm} como VIP: {e}")


async def _atualizar_medicos_bloqueados(medicos: list):
    """Marca medicos como bloqueados baseado no briefing."""
    for med in medicos:
        crm = med.get("crm")
        if crm:
            try:
                supabase.table("clientes").update({
                    "bloqueado": True,
                    "motivo_bloqueio": med.get("observacao", "Via briefing")
                }).eq("crm", crm).execute()
                logger.debug(f"Medico CRM {crm} marcado como bloqueado")
            except Exception as e:
                logger.error(f"Erro ao marcar medico {crm} como bloqueado: {e}")


async def _atualizar_vagas_prioritarias(vagas: list):
    """Atualiza prioridade de vagas baseado no briefing."""
    for vaga in vagas:
        hospital = vaga.get("hospital")
        if hospital:
            try:
                # Buscar hospital pelo nome
                hospital_resp = supabase.table("hospitais").select("id").ilike(
                    "nome", f"%{hospital}%"
                ).limit(1).execute()

                if hospital_resp.data:
                    hospital_id = hospital_resp.data[0]["id"]

                    # Marcar vagas do hospital como urgente
                    supabase.table("vagas").update({
                        "prioridade": "urgente"
                    }).eq("hospital_id", hospital_id).eq(
                        "status", "aberta"
                    ).execute()

                    logger.debug(f"Vagas do hospital {hospital} marcadas como urgente")

            except Exception as e:
                logger.error(f"Erro ao atualizar vagas do hospital {hospital}: {e}")


async def _notificar_atualizacao(briefing: dict):
    """Notifica no Slack que briefing foi atualizado."""
    try:
        foco = briefing.get("foco_semana", ["N/A"])
        primeiro_foco = foco[0][:50] if foco else "N/A"

        await enviar_slack({
            "text": "Briefing atualizado!",
            "attachments": [{
                "color": "#36a64f",
                "fields": [
                    {
                        "title": "Foco",
                        "value": primeiro_foco,
                        "short": False
                    },
                    {
                        "title": "Vagas Prioritarias",
                        "value": str(len(briefing.get("vagas_prioritarias", []))),
                        "short": True
                    },
                    {
                        "title": "Medicos VIP",
                        "value": str(len(briefing.get("medicos_vip", []))),
                        "short": True
                    },
                    {
                        "title": "Medicos Bloqueados",
                        "value": str(len(briefing.get("medicos_bloqueados", []))),
                        "short": True
                    },
                    {
                        "title": "Margem Negociacao",
                        "value": f"{briefing.get('margem_negociacao', 0)}%" if briefing.get("margem_negociacao") else "N/A",
                        "short": True
                    }
                ]
            }]
        })
        logger.info("Notificacao de briefing enviada para Slack")

    except Exception as e:
        logger.error(f"Erro ao notificar atualizacao de briefing: {e}")


async def obter_ultimo_briefing() -> Optional[dict]:
    """
    Retorna o ultimo briefing sincronizado.

    Returns:
        dict com briefing parseado ou None
    """
    try:
        response = supabase.table("briefing_sync_log").select(
            "parseado, doc_title, created_at"
        ).order("created_at", desc=True).limit(1).execute()

        if response.data:
            item = response.data[0]
            parseado = item.get("parseado")

            # Se for string JSON, fazer parse
            if isinstance(parseado, str):
                parseado = json.loads(parseado)

            return {
                "titulo": item.get("doc_title"),
                "sincronizado_em": item.get("created_at"),
                **parseado
            }

        return None

    except Exception as e:
        logger.error(f"Erro ao obter ultimo briefing: {e}")
        return None


async def carregar_diretrizes_ativas() -> dict:
    """
    Carrega diretrizes ativas do banco.

    Returns:
        dict com diretrizes por tipo
    """
    try:
        response = supabase.table("diretrizes").select(
            "tipo, conteudo"
        ).eq("ativo", True).order("prioridade", desc=True).execute()

        diretrizes = {}
        for d in response.data or []:
            diretrizes[d["tipo"]] = d["conteudo"]

        return diretrizes

    except Exception as e:
        logger.error(f"Erro ao carregar diretrizes: {e}")
        return {}
