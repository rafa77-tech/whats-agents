"""
Serviço de ingestão de mensagens de grupos WhatsApp.

Sprint 14 - E02 - Ingestão de Mensagens
"""

from datetime import datetime, UTC
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.whatsapp import evolution
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
    result = supabase.table("grupos_whatsapp").select("id, nome").eq("jid", jid).execute()

    if result.data:
        grupo_id = result.data[0]["id"]
        nome_atual = result.data[0].get("nome")

        # Se não tem nome ainda, buscar na API
        if not nome_atual:
            nome_api = await _buscar_nome_grupo_api(jid)
            if nome_api:
                supabase.table("grupos_whatsapp").update({
                    "nome": nome_api
                }).eq("id", grupo_id).execute()
                logger.info(f"Nome do grupo atualizado: {nome_api}")

        logger.debug(f"Grupo existente: {grupo_id}")
        return UUID(grupo_id)

    # Buscar nome na API se não veio no webhook
    if not nome:
        nome = await _buscar_nome_grupo_api(jid)

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

    logger.info(f"Novo grupo criado: {grupo_id} ({jid}) - {nome or 'sem nome'}")
    return UUID(grupo_id)


async def _buscar_nome_grupo_api(jid: str) -> Optional[str]:
    """
    Busca nome do grupo na Evolution API.

    Args:
        jid: JID do grupo

    Returns:
        Nome do grupo ou None
    """
    try:
        info = await evolution.buscar_info_grupo(jid)
        if info:
            # Evolution API retorna 'subject' como nome do grupo
            nome = info.get("subject") or info.get("name")
            if nome:
                logger.debug(f"Nome do grupo obtido da API: {nome}")
                return nome
    except Exception as e:
        logger.warning(f"Erro ao buscar nome do grupo {jid}: {e}")

    return None


async def obter_ou_criar_contato(
    jid: str,
    nome: Optional[str] = None,
    telefone: Optional[str] = None,
    grupo_jid: Optional[str] = None
) -> UUID:
    """
    Obtém ou cria registro de contato.

    Args:
        jid: JID do contato (ex: "5511999999999@s.whatsapp.net" ou LID)
        nome: Nome do contato (pushName)
        telefone: Número de telefone extraído
        grupo_jid: JID do grupo (para resolver LID)

    Returns:
        UUID do contato
    """
    # Tentar buscar existente
    result = supabase.table("contatos_grupo").select("id, telefone").eq("jid", jid).execute()

    if result.data:
        contato_id = result.data[0]["id"]
        telefone_atual = result.data[0].get("telefone")

        updates = {"ultimo_contato": datetime.now(UTC).isoformat()}

        # Atualizar nome e empresa se veio novo
        if nome:
            nome_separado, empresa = separar_nome_empresa(nome)
            updates["nome"] = nome_separado
            if empresa:
                updates["empresa"] = empresa

        # Se telefone atual parece ser LID, tentar resolver
        if telefone_atual and "@lid" in jid and grupo_jid:
            telefone_real = await _resolver_telefone_real(jid, grupo_jid)
            if telefone_real and telefone_real != telefone_atual:
                updates["telefone"] = telefone_real
                logger.info(f"Telefone atualizado: {telefone_atual} -> {telefone_real}")

        supabase.table("contatos_grupo").update(updates).eq("id", contato_id).execute()
        return UUID(contato_id)

    # Se é LID, tentar resolver telefone real antes de criar
    if "@lid" in jid and grupo_jid:
        telefone_real = await _resolver_telefone_real(jid, grupo_jid)
        if telefone_real:
            telefone = telefone_real

    # Separar nome e empresa
    nome_separado, empresa = separar_nome_empresa(nome) if nome else (nome, None)

    # Criar novo
    novo_contato = {
        "jid": jid,
        "nome": nome_separado,
        "empresa": empresa,
        "telefone": telefone,
        "tipo": "desconhecido",
        "primeiro_contato": datetime.now(UTC).isoformat(),
        "ultimo_contato": datetime.now(UTC).isoformat(),
    }

    result = supabase.table("contatos_grupo").insert(novo_contato).execute()
    contato_id = result.data[0]["id"]

    logger.info(f"Novo contato criado: {contato_id} - {nome_separado} ({empresa or 'sem empresa'})")
    return UUID(contato_id)


async def _resolver_telefone_real(lid: str, grupo_jid: str) -> Optional[str]:
    """
    Resolve LID para telefone real via participantes do grupo.

    Args:
        lid: LID do contato
        grupo_jid: JID do grupo

    Returns:
        Telefone real ou None
    """
    try:
        return await evolution.resolver_lid_para_telefone_via_grupo(lid, grupo_jid)
    except Exception as e:
        logger.warning(f"Erro ao resolver LID {lid}: {e}")
        return None


def extrair_telefone_do_jid(jid: str) -> Optional[str]:
    """Extrai número de telefone do JID."""
    if not jid or "@" not in jid:
        return None
    return jid.split("@")[0]


def separar_nome_empresa(nome_completo: str) -> tuple[str, Optional[str]]:
    """
    Separa nome e empresa do pushName do WhatsApp.

    Padrões comuns:
    - "Eloisa - SMPV" → ("Eloisa", "SMPV")
    - "Time de Escalas - ACIONAMENTOS" → ("Time de Escalas", "ACIONAMENTOS")
    - "Andressa Santos Adm Jr Quero Plantão" → ("Andressa Santos", "Quero Plantão")
    - "João Silva" → ("João Silva", None)

    Args:
        nome_completo: Nome completo do contato (pushName)

    Returns:
        Tuple (nome, empresa) - empresa pode ser None
    """
    if not nome_completo:
        return ("", None)

    nome_completo = nome_completo.strip()

    # Padrão 1: Separador " - "
    if " - " in nome_completo:
        partes = nome_completo.split(" - ", 1)
        nome = partes[0].strip()
        empresa = partes[1].strip() if len(partes) > 1 else None
        return (nome, empresa)

    # Padrão 2: Separador " | "
    if " | " in nome_completo:
        partes = nome_completo.split(" | ", 1)
        nome = partes[0].strip()
        empresa = partes[1].strip() if len(partes) > 1 else None
        return (nome, empresa)

    # Padrão 3: Empresas conhecidas no final
    empresas_conhecidas = [
        "Quero Plantão", "SMPV", "SERGES", "Medtrust", "Hapvida",
        "Medscalle", "Medopen", "mpdoctor", "MP Doctor",
    ]

    for emp in empresas_conhecidas:
        if nome_completo.endswith(emp) or f" {emp}" in nome_completo:
            idx = nome_completo.lower().find(emp.lower())
            if idx > 0:
                nome = nome_completo[:idx].strip()
                # Remover sufixos comuns como "Adm Jr", "Adm", etc
                for sufixo in [" Adm Jr", " Adm", " Jr", " -"]:
                    if nome.endswith(sufixo):
                        nome = nome[:-len(sufixo)].strip()
                return (nome, emp)

    # Sem empresa identificada
    return (nome_completo, None)


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

        # Extrair telefone do sender (pode ser LID, será resolvido depois)
        telefone = extrair_telefone_do_jid(sender_jid)

        # Obter/criar contato (passa grupo_jid para resolver LID)
        contato_id = await obter_ou_criar_contato(
            jid=sender_jid,
            nome=mensagem.nome_contato,
            telefone=telefone,
            grupo_jid=grupo_jid  # Para resolver LID -> telefone real
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

        # Enfileirar para processamento (apenas mensagens válidas)
        # Mensagens ignoradas (mídia, curtas) não vão para o pipeline
        from app.services.grupos.fila import enfileirar_mensagem
        try:
            # Verificar se mensagem foi salva como pendente
            msg_status = supabase.table("mensagens_grupo") \
                .select("status") \
                .eq("id", str(mensagem_id)) \
                .single() \
                .execute()

            if msg_status.data and msg_status.data.get("status") == "pendente":
                await enfileirar_mensagem(mensagem_id)
                logger.debug(f"Mensagem {mensagem_id} enfileirada para processamento")
        except Exception as e:
            logger.warning(f"Erro ao enfileirar mensagem {mensagem_id}: {e}")

        logger.info(f"Mensagem de grupo ingerida: {mensagem_id}")
        return mensagem_id

    except Exception as e:
        logger.error(f"Erro ao ingerir mensagem de grupo: {e}", exc_info=True)
        return None
