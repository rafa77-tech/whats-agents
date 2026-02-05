"""
Servico de tratamento de mensagens fora do horario.

Sprint 22 - Responsividade Inteligente

Ajuste B: Ack idempotente - max 1 ack por conversa por 6 horas
"""
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from app.services.supabase import supabase
from app.services.message_context_classifier import ContextClassification, ContextType
from app.services.delay_engine import has_valid_inbound_proof

logger = logging.getLogger(__name__)

# Timezone Brasil
TZ_BRASIL = ZoneInfo("America/Sao_Paulo")

# Configuracao de horario comercial
HORARIO_INICIO = time(8, 0)   # 08:00
HORARIO_FIM = time(20, 0)     # 20:00
DIAS_UTEIS = [0, 1, 2, 3, 4]  # Segunda a Sexta (0=Monday)

# Ajuste B: Ceiling de ack - max 1 a cada 6 horas por conversa
ACK_CEILING_HOURS = 6


@dataclass
class AckTemplate:
    """Template de ack para fora do horario."""
    tipo: str
    mensagem: str


ACK_TEMPLATES = {
    "generico": AckTemplate(
        tipo="generico",
        mensagem="""Oi Dr(a) {nome}! Recebi sua mensagem.

To fora do horario agora, mas ja anoto aqui e te retorno assim que voltar, tudo bem?"""
    ),
    "vaga": AckTemplate(
        tipo="vaga",
        mensagem="""Oi Dr(a) {nome}! Vi sua msg sobre vaga.

To fora do horario agora, mas ja anoto aqui. Te retorno assim que voltar pra ver a disponibilidade, ok?"""
    ),
    "aceite_vaga": AckTemplate(
        tipo="aceite_vaga",
        mensagem="""Oi Dr(a) {nome}! Recebi seu interesse.

To fora do horario agora. Vou verificar a disponibilidade assim que voltar e te aviso, ok?

Nao consigo garantir a reserva ate la, mas faco o possivel!"""
    ),
    "confirmacao": AckTemplate(
        tipo="confirmacao",
        mensagem="""Oi Dr(a) {nome}! Anotei aqui.

Te retorno assim que o horario operacional voltar!"""
    ),
}


def eh_horario_comercial(dt: Optional[datetime] = None) -> bool:
    """
    Verifica se um datetime esta dentro do horario comercial.

    Args:
        dt: Datetime a verificar (default: agora em Brasilia)

    Returns:
        True se dentro do horario comercial
    """
    dt = dt or datetime.now(TZ_BRASIL)

    # Normalizar para horario de Brasilia
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_BRASIL)
    else:
        dt = dt.astimezone(TZ_BRASIL)

    # Verificar dia da semana
    if dt.weekday() not in DIAS_UTEIS:
        return False

    # Verificar hora
    hora_atual = dt.time()
    return HORARIO_INICIO <= hora_atual <= HORARIO_FIM


def proximo_horario_comercial(dt: Optional[datetime] = None) -> datetime:
    """
    Calcula o proximo horario comercial.

    Args:
        dt: Datetime de referencia (default: agora)

    Returns:
        Proximo datetime em horario comercial
    """
    dt = dt or datetime.now(TZ_BRASIL)

    # Normalizar timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_BRASIL)
    else:
        dt = dt.astimezone(TZ_BRASIL)

    # Se ja esta em horario comercial, retorna agora
    if eh_horario_comercial(dt):
        return dt

    # Comecar do proximo dia as 08:00
    proximo = datetime.combine(dt.date(), HORARIO_INICIO, tzinfo=TZ_BRASIL)

    # Se ainda nao passou das 08:00 hoje e eh dia util
    if dt.time() < HORARIO_INICIO and dt.weekday() in DIAS_UTEIS:
        return proximo

    # Avancar para proximo dia util
    proximo = proximo + timedelta(days=1)
    while proximo.weekday() not in DIAS_UTEIS:
        proximo = proximo + timedelta(days=1)

    return proximo


def selecionar_template_ack(
    classificacao: ContextClassification,
    contexto: Optional[dict] = None
) -> AckTemplate:
    """
    Seleciona template de ack apropriado.

    Args:
        classificacao: Classificacao de contexto
        contexto: Contexto adicional da conversa

    Returns:
        AckTemplate apropriado
    """
    contexto = contexto or {}

    # Se eh aceite de vaga - template especial que NAO promete reserva
    if classificacao.tipo == ContextType.ACEITE_VAGA:
        return ACK_TEMPLATES["aceite_vaga"]

    # Se eh sobre vaga (busca/interesse geral)
    if contexto.get("oferta_pendente") or contexto.get("busca_vaga"):
        return ACK_TEMPLATES["vaga"]

    # Se eh confirmacao de outra coisa (nao vaga)
    if classificacao.tipo == ContextType.CONFIRMACAO:
        return ACK_TEMPLATES["confirmacao"]

    # Default
    return ACK_TEMPLATES["generico"]


async def verificar_ack_recente(
    cliente_id: str,
    conversa_id: Optional[str] = None,
    horas: int = ACK_CEILING_HOURS
) -> bool:
    """
    Verifica se ja enviou ack recentemente para esta conversa.

    Ajuste B: Max 1 ack por conversa por 6 horas.

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa (opcional)
        horas: Janela de tempo em horas

    Returns:
        True se ja enviou ack recente (deve pular)
    """
    try:
        cutoff = (datetime.now(TZ_BRASIL) - timedelta(hours=horas)).isoformat()

        query = supabase.table("mensagens_fora_horario").select(
            "id, ack_enviado_em"
        ).eq("cliente_id", cliente_id).eq("ack_enviado", True).gte(
            "ack_enviado_em", cutoff
        )

        # Filtrar por conversa se disponivel
        if conversa_id:
            query = query.eq("conversa_id", conversa_id)

        result = query.limit(1).execute()

        if result.data:
            logger.info(
                f"Ack recente encontrado para cliente {cliente_id[:8]} "
                f"(dentro de {horas}h) - pulando novo ack"
            )
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao verificar ack recente: {e}")
        # Em caso de erro, permite ack (fail open)
        return False


async def salvar_mensagem_fora_horario(
    cliente_id: str,
    mensagem: str,
    conversa_id: Optional[str] = None,
    contexto: Optional[dict] = None,
    inbound_message_id: Optional[str] = None
) -> str:
    """
    Salva mensagem para processamento posterior.

    Args:
        cliente_id: ID do cliente
        mensagem: Texto da mensagem
        conversa_id: ID da conversa (opcional)
        contexto: Contexto para retomada
        inbound_message_id: ID da mensagem no WhatsApp (para idempotência)

    Returns:
        ID do registro criado
    """
    try:
        dados = {
            "cliente_id": cliente_id,
            "conversa_id": conversa_id,
            "mensagem": mensagem,
            "recebida_em": datetime.now(TZ_BRASIL).isoformat(),
            "contexto": contexto or {},
        }

        # Adicionar inbound_message_id se disponível (para idempotência)
        if inbound_message_id:
            dados["inbound_message_id"] = inbound_message_id

        result = supabase.table("mensagens_fora_horario").insert(dados).execute()

        registro_id = result.data[0]["id"]
        logger.info(f"Mensagem fora horario salva: {registro_id}")
        return registro_id

    except Exception as e:
        # Verificar se é erro de duplicata (idempotência)
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            logger.info(f"Mensagem já existe (idempotência): {inbound_message_id}")
            # Buscar registro existente
            existing = supabase.table("mensagens_fora_horario").select(
                "id"
            ).eq("inbound_message_id", inbound_message_id).limit(1).execute()
            if existing.data:
                return existing.data[0]["id"]
        logger.error(f"Erro ao salvar mensagem fora horario: {e}")
        raise


async def marcar_ack_enviado(
    registro_id: str,
    mensagem_id: str,
    template_tipo: str
) -> None:
    """
    Marca que o ack foi enviado.

    Args:
        registro_id: ID do registro em mensagens_fora_horario
        mensagem_id: ID da mensagem no WhatsApp
        template_tipo: Tipo de template usado
    """
    try:
        supabase.table("mensagens_fora_horario").update({
            "ack_enviado": True,
            "ack_enviado_em": datetime.now(TZ_BRASIL).isoformat(),
            "ack_mensagem_id": mensagem_id,
            "ack_template_tipo": template_tipo,
        }).eq("id", registro_id).execute()

        logger.debug(f"Ack marcado como enviado: {registro_id}")

    except Exception as e:
        logger.error(f"Erro ao marcar ack: {e}")


async def buscar_mensagens_pendentes() -> list[dict]:
    """
    Busca mensagens fora do horario pendentes de processamento.

    Returns:
        Lista de registros pendentes
    """
    try:
        result = supabase.table("mensagens_fora_horario").select(
            "*, clientes(primeiro_nome, telefone)"
        ).eq(
            "processada", False
        ).order(
            "recebida_em"
        ).execute()

        return result.data

    except Exception as e:
        logger.error(f"Erro ao buscar mensagens pendentes: {e}")
        return []


async def marcar_processada(
    registro_id: str,
    resultado: str = "sucesso"
) -> None:
    """
    Marca mensagem como processada.

    Args:
        registro_id: ID do registro
        resultado: Resultado do processamento
    """
    try:
        supabase.table("mensagens_fora_horario").update({
            "processada": True,
            "processada_em": datetime.now(TZ_BRASIL).isoformat(),
            "processada_resultado": resultado,
        }).eq("id", registro_id).execute()

        logger.info(f"Mensagem processada: {registro_id} ({resultado})")

    except Exception as e:
        logger.error(f"Erro ao marcar processada: {e}")


async def processar_mensagem_fora_horario(
    cliente_id: str,
    mensagem: str,
    classificacao: ContextClassification,
    nome_cliente: str,
    conversa_id: Optional[str] = None,
    contexto: Optional[dict] = None,
    inbound_message_id: Optional[str] = None
) -> dict:
    """
    Processa mensagem recebida fora do horario.

    Fluxo:
    1. Verifica ceiling de ack (Ajuste B)
    2. Salva para processamento posterior
    3. Seleciona template de ack
    4. Retorna ack para envio imediato

    Args:
        cliente_id: ID do cliente
        mensagem: Texto recebido
        classificacao: Classificacao de contexto
        nome_cliente: Nome do cliente para personalizacao
        conversa_id: ID da conversa (opcional)
        contexto: Contexto da conversa
        inbound_message_id: ID da mensagem no WhatsApp (para idempotência)

    Returns:
        Dict com ack_mensagem, registro_id e template_tipo
    """
    # 1. Verificar ceiling de ack (Ajuste B: max 1 por 6h)
    ja_tem_ack = await verificar_ack_recente(cliente_id, conversa_id)
    if ja_tem_ack:
        logger.info(f"Ack recente existe para {cliente_id[:8]}, salvando sem novo ack")

        # Salvar mensagem mas sem enviar novo ack
        registro_id = await salvar_mensagem_fora_horario(
            cliente_id=cliente_id,
            mensagem=mensagem,
            conversa_id=conversa_id,
            contexto=contexto,
            inbound_message_id=inbound_message_id
        )

        return {
            "ack_mensagem": None,
            "registro_id": registro_id,
            "template_tipo": None,
            "motivo_sem_ack": "ceiling_6h",
        }

    # 2. Salvar para processamento posterior
    registro_id = await salvar_mensagem_fora_horario(
        cliente_id=cliente_id,
        mensagem=mensagem,
        conversa_id=conversa_id,
        contexto=contexto,
        inbound_message_id=inbound_message_id
    )

    # 3. Selecionar template
    template = selecionar_template_ack(classificacao, contexto)

    # 4. Formatar mensagem
    primeiro_nome = nome_cliente.split()[0] if nome_cliente else ""
    ack_mensagem = template.mensagem.format(nome=primeiro_nome)

    logger.info(f"Ack preparado para cliente {cliente_id[:8]} (template={template.tipo})")

    return {
        "ack_mensagem": ack_mensagem,
        "registro_id": registro_id,
        "template_tipo": template.tipo,
    }


def pode_responder_fora_horario(classificacao: ContextClassification) -> bool:
    """
    Verifica se pode enviar ack para este tipo de mensagem fora do horario.

    Args:
        classificacao: Classificacao de contexto

    Returns:
        True se deve enviar ack
    """
    # Ack para replies diretas e aceites
    tipos_com_ack = [
        ContextType.REPLY_DIRETA,
        ContextType.ACEITE_VAGA,
        ContextType.CONFIRMACAO,
    ]

    return classificacao.tipo in tipos_com_ack
