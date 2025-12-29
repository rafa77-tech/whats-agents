# Epic 03: Service de Ponte

## Objetivo

Criar servico principal que orquestra a criacao da ponte entre medico e divulgador.

## Contexto

Este e o coracao do feature. O service deve:
1. Buscar dados do divulgador via join com vagas_grupo
2. Criar registro de external_handoff
3. Gerar links de confirmacao
4. Enviar mensagens para ambas as partes
5. Emitir eventos de auditoria
6. Notificar gestor no Slack

---

## Story 3.1: Repository de Handoff

### Objetivo
Criar camada de acesso a dados para external_handoffs.

### Arquivo: `app/services/external_handoff/repository.py`

```python
"""
Repository para external_handoffs.

Sprint 20 - E03 - CRUD de handoffs.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Tempo padrao de reserva
DEFAULT_RESERVATION_HOURS = 48


async def criar_handoff(
    vaga_id: str,
    cliente_id: str,
    divulgador_nome: str,
    divulgador_telefone: str,
    divulgador_empresa: str = None,
    reservation_hours: int = DEFAULT_RESERVATION_HOURS,
) -> Optional[dict]:
    """
    Cria novo handoff.

    Args:
        vaga_id: UUID da vaga
        cliente_id: UUID do medico
        divulgador_nome: Nome do divulgador
        divulgador_telefone: Telefone do divulgador
        divulgador_empresa: Empresa do divulgador (opcional)
        reservation_hours: Horas ate expiracao

    Returns:
        Dict com dados do handoff criado ou None se falhar
    """
    reserved_until = datetime.now(timezone.utc) + timedelta(hours=reservation_hours)

    try:
        response = supabase.table("external_handoffs").insert({
            "vaga_id": vaga_id,
            "cliente_id": cliente_id,
            "divulgador_nome": divulgador_nome,
            "divulgador_telefone": divulgador_telefone,
            "divulgador_empresa": divulgador_empresa,
            "status": "pending",
            "reserved_until": reserved_until.isoformat(),
        }).execute()

        if response.data:
            handoff = response.data[0]
            logger.info(f"Handoff criado: {handoff['id'][:8]} para vaga {vaga_id[:8]}")
            return handoff

        return None

    except Exception as e:
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str:
            logger.warning(f"Handoff duplicado para vaga {vaga_id[:8]}")
            return None

        logger.error(f"Erro ao criar handoff: {e}")
        raise


async def buscar_handoff(handoff_id: str) -> Optional[dict]:
    """Busca handoff por ID."""
    try:
        response = supabase.table("external_handoffs") \
            .select("*") \
            .eq("id", handoff_id) \
            .execute()

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff: {e}")
        return None


async def buscar_handoff_por_vaga(vaga_id: str) -> Optional[dict]:
    """Busca handoff ativo para uma vaga."""
    try:
        response = supabase.table("external_handoffs") \
            .select("*") \
            .eq("vaga_id", vaga_id) \
            .in_("status", ["pending", "contacted"]) \
            .execute()

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff por vaga: {e}")
        return None


async def buscar_handoff_por_telefone(telefone: str) -> Optional[dict]:
    """
    Busca handoff pendente para um telefone de divulgador.

    Usado para detectar respostas via keyword.
    """
    try:
        response = supabase.table("external_handoffs") \
            .select("*") \
            .eq("divulgador_telefone", telefone) \
            .in_("status", ["pending", "contacted"]) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao buscar handoff por telefone: {e}")
        return None


async def atualizar_status(
    handoff_id: str,
    novo_status: str,
    confirmed_by: str = None,
    confirmation_source: str = None,
) -> bool:
    """
    Atualiza status do handoff.

    Args:
        handoff_id: UUID do handoff
        novo_status: Novo status
        confirmed_by: 'link' ou 'keyword' (se confirmando)
        confirmation_source: Detalhes adicionais

    Returns:
        True se atualizado com sucesso
    """
    update_data = {
        "status": novo_status,
    }

    if novo_status in ("confirmed", "not_confirmed"):
        update_data["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        if confirmed_by:
            update_data["confirmed_by"] = confirmed_by
        if confirmation_source:
            update_data["confirmation_source"] = confirmation_source

    if novo_status == "expired":
        update_data["expired_at"] = datetime.now(timezone.utc).isoformat()

    try:
        response = supabase.table("external_handoffs") \
            .update(update_data) \
            .eq("id", handoff_id) \
            .execute()

        if response.data:
            logger.info(f"Handoff {handoff_id[:8]} atualizado para {novo_status}")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao atualizar handoff: {e}")
        return False


async def registrar_followup(handoff_id: str) -> bool:
    """Registra que um follow-up foi enviado."""
    try:
        # Usar RPC para incremento atomico
        supabase.table("external_handoffs") \
            .update({
                "last_followup_at": datetime.now(timezone.utc).isoformat(),
                "followup_count": supabase.rpc("increment_followup", {"h_id": handoff_id}),
            }) \
            .eq("id", handoff_id) \
            .execute()

        # Fallback se RPC nao existir: buscar e incrementar
        response = supabase.table("external_handoffs") \
            .select("followup_count") \
            .eq("id", handoff_id) \
            .execute()

        if response.data:
            count = (response.data[0].get("followup_count") or 0) + 1
            supabase.table("external_handoffs") \
                .update({
                    "last_followup_at": datetime.now(timezone.utc).isoformat(),
                    "followup_count": count,
                }) \
                .eq("id", handoff_id) \
                .execute()

        return True

    except Exception as e:
        logger.error(f"Erro ao registrar followup: {e}")
        return False


async def listar_pendentes_expiracao() -> List[dict]:
    """Lista handoffs que passaram do prazo."""
    try:
        now = datetime.now(timezone.utc).isoformat()

        response = supabase.table("external_handoffs") \
            .select("*") \
            .in_("status", ["pending", "contacted"]) \
            .lt("reserved_until", now) \
            .execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar pendentes expiracao: {e}")
        return []


async def listar_para_followup(horas_desde_ultimo: int = 2) -> List[dict]:
    """Lista handoffs que precisam de follow-up."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=horas_desde_ultimo)
        now = datetime.now(timezone.utc)

        response = supabase.table("external_handoffs") \
            .select("*") \
            .in_("status", ["pending", "contacted"]) \
            .gt("reserved_until", now.isoformat()) \
            .or_(
                f"last_followup_at.is.null,last_followup_at.lt.{cutoff.isoformat()}"
            ) \
            .lt("followup_count", 3) \
            .execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar para followup: {e}")
        return []
```

### DoD

- [ ] Funcao `criar_handoff` criada
- [ ] Funcao `buscar_handoff` criada
- [ ] Funcao `buscar_handoff_por_telefone` criada
- [ ] Funcao `atualizar_status` criada
- [ ] Funcao `listar_pendentes_expiracao` criada
- [ ] Funcao `listar_para_followup` criada

---

## Story 3.2: Buscar Divulgador

### Objetivo
Funcao para buscar dados do divulgador a partir da vaga.

### Arquivo: `app/services/external_handoff/divulgador.py`

```python
"""
Busca dados do divulgador a partir da vaga.

Sprint 20 - E03 - Resolver origem da vaga.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class DadosDivulgador:
    """Dados do divulgador da vaga."""
    nome: str
    telefone: str
    empresa: Optional[str] = None
    contato_id: Optional[str] = None


async def buscar_divulgador_da_vaga(vaga_id: str) -> Optional[DadosDivulgador]:
    """
    Busca dados do divulgador que postou a vaga.

    Segue o caminho:
    vagas.source_id -> vagas_grupo -> mensagens_grupo -> contatos_grupo

    Args:
        vaga_id: UUID da vaga

    Returns:
        DadosDivulgador ou None se nao encontrar
    """
    try:
        # 1. Buscar source_id da vaga
        vaga_response = supabase.table("vagas") \
            .select("source, source_id") \
            .eq("id", vaga_id) \
            .execute()

        if not vaga_response.data:
            logger.warning(f"Vaga {vaga_id[:8]} nao encontrada")
            return None

        vaga = vaga_response.data[0]

        if vaga.get("source") != "grupo" or not vaga.get("source_id"):
            logger.info(f"Vaga {vaga_id[:8]} nao veio de grupo (source={vaga.get('source')})")
            return None

        vaga_grupo_id = vaga["source_id"]

        # 2. Buscar mensagem da vaga_grupo
        vg_response = supabase.table("vagas_grupo") \
            .select("mensagem_id") \
            .eq("id", vaga_grupo_id) \
            .execute()

        if not vg_response.data or not vg_response.data[0].get("mensagem_id"):
            logger.warning(f"vagas_grupo {vaga_grupo_id[:8]} sem mensagem_id")
            return None

        mensagem_id = vg_response.data[0]["mensagem_id"]

        # 3. Buscar contato da mensagem
        msg_response = supabase.table("mensagens_grupo") \
            .select("contato_id") \
            .eq("id", mensagem_id) \
            .execute()

        if not msg_response.data or not msg_response.data[0].get("contato_id"):
            logger.warning(f"mensagens_grupo {mensagem_id[:8]} sem contato_id")
            return None

        contato_id = msg_response.data[0]["contato_id"]

        # 4. Buscar dados do contato
        contato_response = supabase.table("contatos_grupo") \
            .select("nome, telefone, empresa") \
            .eq("id", contato_id) \
            .execute()

        if not contato_response.data:
            logger.warning(f"contatos_grupo {contato_id[:8]} nao encontrado")
            return None

        contato = contato_response.data[0]

        if not contato.get("telefone"):
            logger.warning(f"Contato {contato_id[:8]} sem telefone")
            return None

        return DadosDivulgador(
            nome=contato.get("nome") or "Divulgador",
            telefone=contato["telefone"],
            empresa=contato.get("empresa"),
            contato_id=contato_id,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar divulgador: {e}")
        return None


async def buscar_divulgador_query_unica(vaga_id: str) -> Optional[DadosDivulgador]:
    """
    Versao otimizada com uma unica query (RPC).

    Requer funcao SQL:
    CREATE FUNCTION get_divulgador_by_vaga(p_vaga_id UUID)
    RETURNS TABLE (nome TEXT, telefone TEXT, empresa TEXT, contato_id UUID)
    """
    try:
        response = supabase.rpc("get_divulgador_by_vaga", {"p_vaga_id": vaga_id}).execute()

        if response.data and response.data[0].get("telefone"):
            d = response.data[0]
            return DadosDivulgador(
                nome=d.get("nome") or "Divulgador",
                telefone=d["telefone"],
                empresa=d.get("empresa"),
                contato_id=d.get("contato_id"),
            )

        return None

    except Exception as e:
        # Fallback para versao com multiplas queries
        logger.debug(f"RPC falhou, usando fallback: {e}")
        return await buscar_divulgador_da_vaga(vaga_id)
```

### DoD

- [ ] Funcao `buscar_divulgador_da_vaga` criada
- [ ] Trata casos de vaga sem origem de grupo
- [ ] Trata casos de contato sem telefone
- [ ] Logs informativos

---

## Story 3.3: Service Principal

### Objetivo
Orquestrar toda a criacao da ponte.

### Arquivo: `app/services/external_handoff/service.py`

```python
"""
Service principal de external handoff.

Sprint 20 - E03 - Orquestracao da ponte automatica.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase
from app.services.business_events import emit_event, BusinessEvent, EventType, EventSource
from app.services.outbound import send_outbound_message, OutboundContext, ActorType, OutboundChannel, OutboundMethod
from app.services.slack import notificar_handoff_criado

from .repository import criar_handoff, atualizar_status
from .divulgador import buscar_divulgador_da_vaga, DadosDivulgador
from .tokens import gerar_par_links

logger = logging.getLogger(__name__)


@dataclass
class ResultadoPonte:
    """Resultado da criacao da ponte."""
    sucesso: bool
    handoff_id: Optional[str] = None
    erro: Optional[str] = None
    divulgador: Optional[DadosDivulgador] = None


async def criar_ponte_externa(
    vaga_id: str,
    cliente_id: str,
    telefone_medico: str,
    nome_medico: str,
    vaga_resumo: str,  # Ex: "15/01 - Noturno - Hospital ABC"
) -> ResultadoPonte:
    """
    Cria ponte automatica entre medico e divulgador.

    Args:
        vaga_id: UUID da vaga aceita
        cliente_id: UUID do medico
        telefone_medico: Telefone do medico
        nome_medico: Nome do medico
        vaga_resumo: Resumo da vaga para mensagens

    Returns:
        ResultadoPonte com status e dados
    """
    # 1. Buscar divulgador
    divulgador = await buscar_divulgador_da_vaga(vaga_id)

    if not divulgador:
        logger.warning(f"Vaga {vaga_id[:8]} sem divulgador identificado")
        return ResultadoPonte(
            sucesso=False,
            erro="divulgador_nao_encontrado",
        )

    # 2. Criar handoff
    handoff = await criar_handoff(
        vaga_id=vaga_id,
        cliente_id=cliente_id,
        divulgador_nome=divulgador.nome,
        divulgador_telefone=divulgador.telefone,
        divulgador_empresa=divulgador.empresa,
    )

    if not handoff:
        return ResultadoPonte(
            sucesso=False,
            erro="handoff_duplicado_ou_erro",
        )

    handoff_id = handoff["id"]

    # 3. Emitir evento de criacao
    await emit_event(BusinessEvent(
        event_type=EventType.HANDOFF_CREATED,
        source=EventSource.BACKEND,
        cliente_id=cliente_id,
        vaga_id=vaga_id,
        event_props={
            "handoff_id": handoff_id,
            "divulgador_telefone": divulgador.telefone,
        },
    ))

    # 4. Gerar links de confirmacao
    link_confirmar, link_nao_confirmar = gerar_par_links(handoff_id)

    # 5. Enviar mensagens (em paralelo)
    msg_medico = _formatar_msg_medico(divulgador)
    msg_divulgador = _formatar_msg_divulgador(
        nome_medico=nome_medico,
        telefone_medico=telefone_medico,
        vaga_resumo=vaga_resumo,
        link_confirmar=link_confirmar,
        link_nao_confirmar=link_nao_confirmar,
    )

    # Enviar para ambos
    resultados = await asyncio.gather(
        _enviar_para_medico(telefone_medico, msg_medico, cliente_id, vaga_id),
        _enviar_para_divulgador(divulgador.telefone, msg_divulgador, cliente_id, vaga_id),
        return_exceptions=True,
    )

    # Verificar se pelo menos a msg ao divulgador foi enviada
    divulgador_ok = not isinstance(resultados[1], Exception) and resultados[1]

    if divulgador_ok:
        # Atualizar status para 'contacted'
        await atualizar_status(handoff_id, "contacted")

        # Emitir evento
        await emit_event(BusinessEvent(
            event_type=EventType.HANDOFF_CONTACTED,
            source=EventSource.BACKEND,
            cliente_id=cliente_id,
            vaga_id=vaga_id,
            event_props={
                "handoff_id": handoff_id,
                "channel": "whatsapp",
            },
        ))

    # 6. Notificar Slack
    await notificar_handoff_criado(
        handoff_id=handoff_id,
        vaga_resumo=vaga_resumo,
        nome_medico=nome_medico,
        divulgador_nome=divulgador.nome,
        divulgador_empresa=divulgador.empresa,
    )

    return ResultadoPonte(
        sucesso=True,
        handoff_id=handoff_id,
        divulgador=divulgador,
    )


def _formatar_msg_medico(divulgador: DadosDivulgador) -> str:
    """Formata mensagem para o medico."""
    empresa_texto = f" ({divulgador.empresa})" if divulgador.empresa else ""

    return f"""Perfeito! Reservei essa vaga pra voce.

Para confirmar na escala, fala direto com {divulgador.nome}{empresa_texto}: {divulgador.telefone}

Me avisa aqui quando fechar!"""


def _formatar_msg_divulgador(
    nome_medico: str,
    telefone_medico: str,
    vaga_resumo: str,
    link_confirmar: str,
    link_nao_confirmar: str,
) -> str:
    """Formata mensagem para o divulgador."""
    return f"""Oi, tudo bem?
Tenho um medico interessado na vaga de {vaga_resumo}.

Contato: Dr(a). {nome_medico} - {telefone_medico}

Para eu registrar corretamente no sistema:
- Confirmar: {link_confirmar}
- Nao fechou: {link_nao_confirmar}

Ou responda CONFIRMADO ou NAO FECHOU aqui."""


async def _enviar_para_medico(
    telefone: str,
    mensagem: str,
    cliente_id: str,
    vaga_id: str,
) -> bool:
    """Envia mensagem para o medico."""
    ctx = OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,
    )

    try:
        result = await send_outbound_message(telefone, mensagem, ctx)
        return result.success
    except Exception as e:
        logger.error(f"Erro ao enviar para medico: {e}")
        return False


async def _enviar_para_divulgador(
    telefone: str,
    mensagem: str,
    cliente_id: str,
    vaga_id: str,
) -> bool:
    """Envia mensagem para o divulgador."""
    # Usar contexto de sistema (nao associado ao cliente)
    ctx = OutboundContext(
        cliente_id=cliente_id,  # Para rastreabilidade
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,  # Tratado como campanha para guardrails
        is_proactive=True,
    )

    try:
        result = await send_outbound_message(telefone, mensagem, ctx)
        return result.success
    except Exception as e:
        logger.error(f"Erro ao enviar para divulgador: {e}")
        return False
```

### DoD

- [ ] Funcao `criar_ponte_externa` implementada
- [ ] Busca divulgador funcionando
- [ ] Cria handoff no banco
- [ ] Gera links de confirmacao
- [ ] Envia mensagens para ambas as partes
- [ ] Emite eventos de auditoria
- [ ] Notifica Slack

---

## Story 3.4: Notificacao Slack

### Objetivo
Adicionar funcao de notificacao de handoff ao Slack.

### Arquivo: `app/services/slack.py` (adicionar funcao)

```python
async def notificar_handoff_criado(
    handoff_id: str,
    vaga_resumo: str,
    nome_medico: str,
    divulgador_nome: str,
    divulgador_empresa: str = None,
) -> bool:
    """
    Notifica sobre nova ponte medico-divulgador.

    Args:
        handoff_id: ID do handoff
        vaga_resumo: Resumo da vaga
        nome_medico: Nome do medico
        divulgador_nome: Nome do divulgador
        divulgador_empresa: Empresa do divulgador

    Returns:
        True se notificou com sucesso
    """
    empresa = f" ({divulgador_empresa})" if divulgador_empresa else ""

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Ponte Criada",
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Vaga:*\n{vaga_resumo}"},
                {"type": "mrkdwn", "text": f"*Medico:*\n{nome_medico}"},
                {"type": "mrkdwn", "text": f"*Divulgador:*\n{divulgador_nome}{empresa}"},
                {"type": "mrkdwn", "text": f"*Status:*\nAguardando confirmacao"},
            ]
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Handoff ID: `{handoff_id[:8]}...`"}
            ]
        }
    ]

    return await _enviar_mensagem_slack(blocks=blocks, color="#FFA500")  # Laranja = pendente
```

### DoD

- [ ] Funcao `notificar_handoff_criado` criada
- [ ] Formato de mensagem claro
- [ ] Cor laranja para indicar pendente

---

## Checklist do Epico

- [ ] **S20.E03.1** - Repository criado
- [ ] **S20.E03.2** - Busca divulgador funcionando
- [ ] **S20.E03.3** - Service principal implementado
- [ ] **S20.E03.4** - Notificacao Slack
- [ ] Integracao end-to-end testavel
- [ ] Logs em todas as operacoes
