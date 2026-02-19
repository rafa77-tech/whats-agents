"""
Agente de Recuperação de Vagas Incompletas.

Sprint 63 - Épico D: Envia DM ao anunciante pedindo campos faltantes.

Vagas em status 'aguardando_revisao' com motivo_status 'match_incompleto:...'
recebem uma mensagem do agente Ana pedindo as informações faltantes.
"""

from datetime import datetime, timezone
from typing import Optional

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.whatsapp import enviar_whatsapp
from app.services.chips.selector import chip_selector
from app.services.chips.sender import enviar_via_chip

logger = get_logger(__name__)


# =============================================================================
# Mapeamento de campos → texto amigável
# =============================================================================

CAMPO_PARA_TEXTO = {
    "setor": "o setor (PS, UTI, CC, enfermaria...)",
    "especialidade": "a especialidade da vaga",
    "hospital": "o hospital/local do plantão",
    "data": "a data do plantão",
    "horario": "o horário ou período do plantão (diurno, noturno, manhã, tarde...)",
    "valor": "o valor do plantão",
}


# =============================================================================
# Busca de vagas incompletas
# =============================================================================


async def listar_vagas_incompletas(limite: int = 20) -> list[dict]:
    """
    Busca vagas em aguardando_revisao com match_incompleto e sem DM enviado.

    Returns:
        Lista de dicts com dados da vaga
    """
    try:
        result = (
            supabase.table("vagas_grupo")
            .select("id, motivo_status, hospital_raw, grupo_origem_id, contato_whatsapp")
            .eq("status", "aguardando_revisao")
            .like("motivo_status", "match_incompleto:%")
            .is_("dm_recovery_sent_at", "null")
            .limit(limite)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Erro ao listar vagas incompletas: {e}")
        return []


# =============================================================================
# Resolução de telefone do anunciante
# =============================================================================


async def resolver_telefone_anunciante(vaga: dict) -> Optional[str]:
    """
    Resolve telefone do anunciante via join vagas_grupo → mensagens_grupo → contatos_grupo.

    Fallback: usa contato_whatsapp direto da vaga (caso LID).
    """
    vaga_id = vaga["id"]
    try:
        from app.services.external_handoff.service import buscar_divulgador_por_vaga_grupo

        divulgador = await buscar_divulgador_por_vaga_grupo(vaga_id)
        if divulgador and divulgador.get("telefone"):
            return divulgador["telefone"]
    except Exception as e:
        logger.warning(f"Erro ao buscar divulgador para vaga {vaga_id}: {e}")

    # Fallback: contato_whatsapp direto da vaga
    telefone = vaga.get("contato_whatsapp")
    if telefone:
        logger.info(f"Usando contato_whatsapp fallback para vaga {vaga_id}")
        return telefone

    logger.warning(f"Nenhum telefone encontrado para vaga {vaga_id}")
    return None


# =============================================================================
# Nome do grupo
# =============================================================================


async def buscar_nome_grupo(grupo_id: Optional[str]) -> str:
    """Busca nome do grupo pelo ID."""
    if not grupo_id:
        return "grupo"
    try:
        result = (
            supabase.table("grupos_whatsapp")
            .select("nome")
            .eq("id", grupo_id)
            .single()
            .execute()
        )
        return result.data.get("nome", "grupo") if result.data else "grupo"
    except Exception:
        return "grupo"


# =============================================================================
# Montagem de mensagem
# =============================================================================


def extrair_campos_faltando(motivo_status: str) -> list[str]:
    """Extrai lista de campos faltando do motivo_status."""
    if not motivo_status or ":" not in motivo_status:
        return []
    # "match_incompleto:setor,valor" → ["setor", "valor"]
    campos_str = motivo_status.split(":", 1)[1]
    return [c.strip() for c in campos_str.split(",") if c.strip()]


def montar_mensagem_recovery(
    campos_faltando: list[str],
    nome_grupo: str,
    hospital_raw: Optional[str] = None,
) -> str:
    """
    Monta mensagem personalizada pedindo campos faltantes.

    Persona: Ana (profissional, amigável, objetiva).
    """
    # Descrever o que falta
    descricoes = []
    for campo in campos_faltando:
        texto = CAMPO_PARA_TEXTO.get(campo)
        if texto:
            descricoes.append(texto)

    if not descricoes:
        return ""

    # Construir frase de contexto
    contexto = f"no grupo {nome_grupo}"
    if hospital_raw:
        contexto = f"no {hospital_raw} ({nome_grupo})"

    if len(descricoes) == 1:
        faltou = f"faltou informar {descricoes[0]}"
    else:
        ultimo = descricoes[-1]
        anteriores = ", ".join(descricoes[:-1])
        faltou = f"faltou informar {anteriores} e {ultimo}"

    return (
        f"Oi! Vi sua vaga {contexto}, mas {faltou}. "
        f"Pode me passar? Assim consigo divulgar melhor 😊"
    )


# =============================================================================
# Envio e atualização
# =============================================================================


async def enviar_dm_recovery(vaga_id: str, telefone: str, mensagem: str) -> bool:
    """Envia DM de recuperação e atualiza controle."""
    try:
        # Usar multi-chip para não enviar pela instância Revoluna (listener)
        chip = await chip_selector.selecionar_chip(
            tipo_mensagem="prospeccao",
            telefone_destino=telefone,
        )
        if chip:
            result = await enviar_via_chip(chip, telefone, mensagem)
            if not result.success:
                raise Exception(f"Falha envio via chip: {result.error}")
        else:
            # Fallback: enviar via instância padrão
            await enviar_whatsapp(telefone, mensagem, verificar_rate_limit=False)

        # Atualizar controle
        supabase.table("vagas_grupo").update(
            {
                "dm_recovery_sent_at": datetime.now(timezone.utc).isoformat(),
                "dm_recovery_status": "enviado",
            }
        ).eq("id", vaga_id).execute()

        logger.info(f"DM recovery enviado para vaga {vaga_id} → {telefone[-4:]}")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar DM recovery para vaga {vaga_id}: {e}")

        # Marcar como falhou para não retentar indefinidamente
        try:
            supabase.table("vagas_grupo").update(
                {
                    "dm_recovery_sent_at": datetime.now(timezone.utc).isoformat(),
                    "dm_recovery_status": "falhou",
                }
            ).eq("id", vaga_id).execute()
        except Exception:
            pass

        return False


# =============================================================================
# Execução principal
# =============================================================================


async def executar_recovery(limite: int = 20) -> dict:
    """
    Executa ciclo de recuperação de vagas incompletas.

    Returns:
        Estatísticas de execução
    """
    stats = {
        "vagas_encontradas": 0,
        "dms_enviados": 0,
        "sem_telefone": 0,
        "erros": 0,
    }

    vagas = await listar_vagas_incompletas(limite)
    stats["vagas_encontradas"] = len(vagas)

    if not vagas:
        logger.info("Recovery: nenhuma vaga incompleta pendente")
        return stats

    for vaga in vagas:
        vaga_id = vaga["id"]

        # Resolver telefone
        telefone = await resolver_telefone_anunciante(vaga)
        if not telefone:
            stats["sem_telefone"] += 1
            continue

        # Extrair campos faltando
        campos = extrair_campos_faltando(vaga.get("motivo_status", ""))
        if not campos:
            continue

        # Buscar nome do grupo
        nome_grupo = await buscar_nome_grupo(vaga.get("grupo_origem_id"))

        # Montar mensagem
        mensagem = montar_mensagem_recovery(
            campos_faltando=campos,
            nome_grupo=nome_grupo,
            hospital_raw=vaga.get("hospital_raw"),
        )
        if not mensagem:
            continue

        # Enviar
        sucesso = await enviar_dm_recovery(vaga_id, telefone, mensagem)
        if sucesso:
            stats["dms_enviados"] += 1
        else:
            stats["erros"] += 1

    logger.info(
        f"Recovery concluído: {stats['vagas_encontradas']} vagas, "
        f"{stats['dms_enviados']} DMs enviados, "
        f"{stats['sem_telefone']} sem telefone, "
        f"{stats['erros']} erros"
    )

    return stats
