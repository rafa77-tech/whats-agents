"""
Serviço de ingestão de mensagens de grupos WhatsApp.

Sprint 14 - E02 - Ingestão de Mensagens
"""

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.schemas.mensagem import MensagemRecebida

logger = get_logger(__name__)


async def obter_ou_criar_grupo(jid: str, nome: Optional[str] = None) -> UUID:
    """
    Obtém ou cria registro de grupo.

    Args:
        jid: JID do grupo (ex: "123456@g.us")
        nome: Nome do grupo (opcional, do webhook)

    Returns:
        UUID do grupo
    """
    # Tentar buscar existente
    result = supabase.table("grupos_whatsapp").select("id").eq("jid", jid).execute()

    if result.data:
        grupo_id = result.data[0]["id"]
        logger.debug(f"Grupo existente: {grupo_id}")
        return UUID(grupo_id)

    # Criar novo
    novo_grupo = {
        "jid": jid,
        "nome": nome,
        "tipo": "vagas",  # Default
        "ativo": True,
        "monitorar_ofertas": True,
    }

    result = supabase.table("grupos_whatsapp").insert(novo_grupo).execute()
    grupo_id = result.data[0]["id"]

    logger.info(f"Novo grupo criado: {grupo_id} ({jid})")
    return UUID(grupo_id)


async def obter_ou_criar_contato(
    jid: str,
    nome: Optional[str] = None,
    telefone: Optional[str] = None
) -> UUID:
    """
    Obtém ou cria registro de contato.

    Args:
        jid: JID do contato (ex: "5511999999999@s.whatsapp.net")
        nome: Nome do contato (pushName)
        telefone: Número de telefone extraído

    Returns:
        UUID do contato
    """
    # Tentar buscar existente
    result = supabase.table("contatos_grupo").select("id").eq("jid", jid).execute()

    if result.data:
        contato_id = result.data[0]["id"]

        # Atualizar nome se veio novo
        if nome:
            supabase.table("contatos_grupo").update({
                "nome": nome,
                "ultimo_contato": datetime.now(UTC).isoformat()
            }).eq("id", contato_id).execute()

        return UUID(contato_id)

    # Criar novo
    novo_contato = {
        "jid": jid,
        "nome": nome,
        "telefone": telefone,
        "tipo": "desconhecido",
        "primeiro_contato": datetime.now(UTC).isoformat(),
        "ultimo_contato": datetime.now(UTC).isoformat(),
    }

    result = supabase.table("contatos_grupo").insert(novo_contato).execute()
    contato_id = result.data[0]["id"]

    logger.info(f"Novo contato criado: {contato_id} ({jid})")
    return UUID(contato_id)


def extrair_telefone_do_jid(jid: str) -> Optional[str]:
    """Extrai número de telefone do JID."""
    if not jid or "@" not in jid:
        return None
    return jid.split("@")[0]


async def salvar_mensagem_grupo(
    grupo_id: UUID,
    contato_id: UUID,
    mensagem: MensagemRecebida,
    dados_raw: dict
) -> UUID:
    """
    Salva mensagem de grupo no banco.

    Args:
        grupo_id: UUID do grupo
        contato_id: UUID do contato
        mensagem: Mensagem parseada
        dados_raw: Dados originais do webhook

    Returns:
        UUID da mensagem salva
    """
    # Determinar tipo de mídia
    tipo_midia = "texto"
    tem_midia = False

    tipo_msg = mensagem.tipo.lower() if mensagem.tipo else "texto"

    if tipo_msg in ("image", "imagem"):
        tipo_midia = "imagem"
        tem_midia = True
    elif tipo_msg == "audio":
        tipo_midia = "audio"
        tem_midia = True
    elif tipo_msg == "video":
        tipo_midia = "video"
        tem_midia = True
    elif tipo_msg in ("document", "documento"):
        tipo_midia = "documento"
        tem_midia = True
    elif tipo_msg == "sticker":
        tipo_midia = "sticker"
        tem_midia = True

    # Determinar status inicial
    status = "pendente"
    if tem_midia:
        status = "ignorada_midia"
    elif not mensagem.texto or len(mensagem.texto.strip()) < 5:
        status = "ignorada_curta"

    # Extrair sender_jid
    key = dados_raw.get("key", {})
    sender_jid = key.get("participant", "")

    nova_mensagem = {
        "grupo_id": str(grupo_id),
        "contato_id": str(contato_id),
        "message_id": mensagem.message_id,
        "sender_jid": sender_jid,
        "sender_nome": mensagem.nome_contato,
        "texto": mensagem.texto,
        "tipo_midia": tipo_midia,
        "tem_midia": tem_midia,
        "timestamp_msg": mensagem.timestamp.isoformat() if mensagem.timestamp else datetime.now(UTC).isoformat(),
        "is_forwarded": dados_raw.get("message", {}).get("extendedTextMessage", {}).get("contextInfo", {}).get("isForwarded", False),
        "status": status,
    }

    result = supabase.table("mensagens_grupo").insert(nova_mensagem).execute()
    mensagem_id = result.data[0]["id"]

    logger.debug(f"Mensagem salva: {mensagem_id} (status: {status})")
    return UUID(mensagem_id)


async def atualizar_contadores(grupo_id: UUID, contato_id: UUID) -> None:
    """Incrementa contadores de grupo e contato."""
    try:
        supabase.rpc("incrementar_mensagens_grupo", {"p_grupo_id": str(grupo_id)}).execute()
        supabase.rpc("incrementar_mensagens_contato", {"p_contato_id": str(contato_id)}).execute()
        supabase.rpc("registrar_primeira_mensagem_grupo", {"p_grupo_id": str(grupo_id)}).execute()
    except Exception as e:
        logger.warning(f"Erro ao atualizar contadores: {e}")


async def ingerir_mensagem_grupo(
    mensagem: MensagemRecebida,
    dados_raw: dict
) -> Optional[UUID]:
    """
    Função principal de ingestão.

    Orquestra todo o processo de ingestão de uma mensagem de grupo.

    Args:
        mensagem: Mensagem parseada
        dados_raw: Dados originais do webhook

    Returns:
        UUID da mensagem salva, ou None se não salvou
    """
    try:
        # Extrair JIDs
        key = dados_raw.get("key", {})
        grupo_jid = key.get("remoteJid", "")
        sender_jid = key.get("participant", "")

        if not grupo_jid:
            logger.warning("JID do grupo ausente na mensagem")
            return None

        # Se não tem participant, pode ser mensagem do próprio número no grupo
        if not sender_jid:
            sender_jid = grupo_jid  # Fallback

        # Obter/criar grupo
        grupo_id = await obter_ou_criar_grupo(
            jid=grupo_jid,
            nome=dados_raw.get("groupName")  # Nem sempre vem
        )

        # Extrair telefone do sender
        telefone = extrair_telefone_do_jid(sender_jid)

        # Obter/criar contato
        contato_id = await obter_ou_criar_contato(
            jid=sender_jid,
            nome=mensagem.nome_contato,
            telefone=telefone
        )

        # Salvar mensagem
        mensagem_id = await salvar_mensagem_grupo(
            grupo_id=grupo_id,
            contato_id=contato_id,
            mensagem=mensagem,
            dados_raw=dados_raw
        )

        # Atualizar contadores
        await atualizar_contadores(grupo_id, contato_id)

        logger.info(f"Mensagem de grupo ingerida: {mensagem_id}")
        return mensagem_id

    except Exception as e:
        logger.error(f"Erro ao ingerir mensagem de grupo: {e}", exc_info=True)
        return None
