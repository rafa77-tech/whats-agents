# Epic 03: Webhook Router

## Objetivo

Implementar **roteamento de webhooks** para multiplas instancias Evolution:
- Identificar chip pela instancia
- Adicionar contexto do chip ao pipeline
- Atualizar contadores em tempo real
- Detectar desconexoes

## Contexto

Com N chips em producao, cada um tem sua propria instancia Evolution. O Webhook Router:
1. Recebe webhook de qualquer instancia
2. Identifica qual chip recebeu
3. Adiciona contexto ao pipeline existente

---

## Story 3.1: Router Basico

### Objetivo
Implementar roteamento por instance_name.

### Implementacao

**Arquivo:** `app/api/routes/webhook_router.py`

```python
"""
Webhook Router - Roteamento multi-chip.

Recebe webhooks de multiplas instancias Evolution
e roteia para o processamento correto.
"""
from fastapi import APIRouter, Request, HTTPException
import logging
from datetime import datetime, timezone

from app.services.supabase import supabase
from app.services.chips.selector import chip_selector
from app.pipeline.manager import pipeline_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/evolution", tags=["evolution"])


@router.post("/{instance_name}")
async def webhook_evolution(instance_name: str, request: Request):
    """
    Recebe webhook de uma instancia Evolution.

    O instance_name identifica qual chip recebeu a mensagem.

    Args:
        instance_name: Nome da instancia (ex: julia-99999999)
        request: Request com payload do evento

    Returns:
        {"status": "ok"} ou erro
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[WebhookRouter] Erro ao parsear JSON: {e}")
        raise HTTPException(400, "Invalid JSON")

    event_type = payload.get("event")

    logger.debug(f"[WebhookRouter] {instance_name}: {event_type}")

    # Buscar chip pelo instance_name
    result = supabase.table("chips").select(
        "id, telefone, instance_name, status, trust_score, trust_level, "
        "pode_prospectar, pode_followup, pode_responder"
    ).eq(
        "instance_name", instance_name
    ).single().execute()

    if not result.data:
        logger.warning(f"[WebhookRouter] Instancia desconhecida: {instance_name}")
        # Nao retornar erro para nao quebrar Evolution
        return {"status": "ignored", "reason": "unknown_instance"}

    chip = result.data

    # Verificar se chip esta em status valido
    if chip["status"] not in ["active", "warming"]:
        logger.warning(
            f"[WebhookRouter] Chip {instance_name} nao esta ativo "
            f"(status={chip['status']}). Evento sera ignorado para processamento."
        )
        # Ainda atualiza metricas mas nao processa para Julia
        chip["_ignore_processing"] = True

    # Rotear por tipo de evento
    if event_type == "messages.upsert":
        return await processar_mensagem_recebida(chip, payload)

    elif event_type == "connection.update":
        return await processar_conexao(chip, payload)

    elif event_type == "messages.update":
        return await processar_status_mensagem(chip, payload)

    elif event_type == "qrcode.updated":
        return await processar_qr_code(chip, payload)

    else:
        logger.debug(f"[WebhookRouter] Evento ignorado: {event_type}")
        return {"status": "ignored", "event": event_type}


async def processar_mensagem_recebida(chip: dict, payload: dict) -> dict:
    """
    Processa mensagem recebida no chip.

    Fluxo:
    1. Extrair dados da mensagem
    2. Atualizar metricas do chip
    3. Registrar interacao
    4. Se chip ativo, enviar para pipeline Julia
    """
    data = payload.get("data", {})
    message = data.get("message", {})
    key = data.get("key", {})

    # Ignorar mensagens proprias
    if key.get("fromMe"):
        return {"status": "ignored", "reason": "from_me"}

    # Extrair telefone
    remote_jid = key.get("remoteJid", "")
    telefone = remote_jid.split("@")[0]

    # Ignorar grupos e broadcasts
    if "@g.us" in remote_jid or "@broadcast" in remote_jid:
        return {"status": "ignored", "reason": "group_or_broadcast"}

    # Extrair tipo de mensagem
    tipo_midia = "text"
    if message.get("imageMessage"):
        tipo_midia = "image"
    elif message.get("audioMessage"):
        tipo_midia = "audio"
    elif message.get("videoMessage"):
        tipo_midia = "video"
    elif message.get("documentMessage"):
        tipo_midia = "document"
    elif message.get("stickerMessage"):
        tipo_midia = "sticker"

    # Registrar interacao
    supabase.table("chip_interactions").insert({
        "chip_id": chip["id"],
        "tipo": "msg_recebida",
        "destinatario": telefone,
        "midia_tipo": tipo_midia,
    }).execute()

    # Atualizar contadores
    supabase.table("chips").update({
        "msgs_recebidas_total": supabase.sql("msgs_recebidas_total + 1"),
        "msgs_recebidas_hoje": supabase.sql("msgs_recebidas_hoje + 1"),
    }).eq("id", chip["id"]).execute()

    # Registrar resposta (para taxa de resposta)
    await chip_selector.registrar_resposta_recebida(
        chip_id=chip["id"],
        telefone_origem=telefone,
    )

    # Se chip nao deve processar, parar aqui
    if chip.get("_ignore_processing"):
        return {"status": "ok", "processed": False}

    # Enviar para pipeline Julia
    # Adicionar contexto do chip ao payload
    payload["_chip"] = {
        "id": chip["id"],
        "telefone": chip["telefone"],
        "instance_name": chip["instance_name"],
        "trust_score": chip["trust_score"],
        "trust_level": chip["trust_level"],
    }

    await pipeline_manager.processar(payload)

    return {"status": "ok", "processed": True}


async def processar_conexao(chip: dict, payload: dict) -> dict:
    """
    Atualiza status de conexao do chip.
    """
    state = payload.get("data", {}).get("state")
    connected = state == "open"

    supabase.table("chips").update({
        "evolution_connected": connected,
    }).eq("id", chip["id"]).execute()

    if not connected:
        logger.warning(f"[WebhookRouter] Chip desconectado: {chip['telefone']}")

        # Criar alerta se ficou desconectado
        supabase.table("chip_alerts").insert({
            "chip_id": chip["id"],
            "severity": "warning",
            "tipo": "connection_lost",
            "message": f"Chip {chip['telefone']} desconectado",
        }).execute()

    else:
        logger.info(f"[WebhookRouter] Chip conectado: {chip['telefone']}")

        # Resolver alertas de conexao
        supabase.table("chip_alerts").update({
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": "auto",
        }).eq(
            "chip_id", chip["id"]
        ).eq(
            "tipo", "connection_lost"
        ).eq(
            "resolved", False
        ).execute()

    return {"status": "ok", "connected": connected}


async def processar_status_mensagem(chip: dict, payload: dict) -> dict:
    """
    Processa atualizacao de status de mensagem (entregue, lido, etc).
    """
    data = payload.get("data", {})
    status = data.get("status")

    # Atualizar metricas de delivery se necessario
    if status == "DELIVERY_ACK":
        # Mensagem entregue
        pass
    elif status == "READ":
        # Mensagem lida
        pass
    elif status == "PLAYED":
        # Audio/video reproduzido
        pass

    return {"status": "ok"}


async def processar_qr_code(chip: dict, payload: dict) -> dict:
    """
    Processa QR Code atualizado (para conexao inicial).
    """
    qr = payload.get("data", {}).get("qrcode", {}).get("base64")

    if qr:
        supabase.table("chips").update({
            "evolution_qr_code": qr,
        }).eq("id", chip["id"]).execute()

        logger.info(f"[WebhookRouter] QR Code atualizado para {chip['telefone']}")

    return {"status": "ok"}
```

### DoD

- [ ] Roteamento por instance_name
- [ ] Processar mensagem recebida
- [ ] Processar conexao
- [ ] Atualizar contadores

---

## Story 3.2: Integracao com Pipeline

### Objetivo
Integrar contexto do chip no pipeline existente.

### Implementacao

O pipeline existente precisa ser adaptado para usar o contexto do chip:

**Arquivo:** `app/pipeline/manager.py` (adicoes)

```python
async def processar(self, payload: dict):
    """
    Processa payload de mensagem.

    Se payload tem _chip, usar para envio de resposta.
    """
    # Extrair contexto do chip se existir
    chip_context = payload.pop("_chip", None)

    # ... processamento existente ...

    # Ao enviar resposta, usar chip_context
    if chip_context and resposta:
        await enviar_mensagem(
            telefone=telefone_cliente,
            texto=resposta,
            instance=chip_context["instance_name"],
        )
```

### DoD

- [ ] Pipeline usando contexto do chip
- [ ] Resposta enviada pelo chip correto

---

## Story 3.3: Endpoint Unificado (Opcional)

### Objetivo
Endpoint unico que identifica instancia pelo header.

### Implementacao

```python
@router.post("/")
async def webhook_evolution_unified(
    request: Request,
    x_instance_name: str = Header(None),
):
    """
    Endpoint unificado que recebe de qualquer instancia.

    A instancia e identificada pelo header X-Instance-Name.
    """
    if not x_instance_name:
        raise HTTPException(400, "Missing X-Instance-Name header")

    # Reutilizar logica do endpoint com path
    return await webhook_evolution(x_instance_name, request)
```

### DoD

- [ ] Endpoint unificado funcionando
- [ ] Header obrigatorio

---

## Checklist do Epico

- [ ] **E03.1** - Router basico
- [ ] **E03.2** - Integracao com pipeline
- [ ] **E03.3** - Endpoint unificado (opcional)
- [ ] Testes de integracao
- [ ] Documentacao atualizada

---

## Diagrama: Fluxo de Webhook

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEBHOOK ROUTER FLOW                           │
└─────────────────────────────────────────────────────────────────┘

  Evolution API                    Webhook Router              Julia Pipeline
       │                                │                            │
       │  POST /webhooks/evolution/     │                            │
       │       julia-99999999           │                            │
       │  {event: "messages.upsert",    │                            │
       │   data: {...}}                 │                            │
       │ ──────────────────────────────>│                            │
       │                                │                            │
       │                                │ 1. Buscar chip por         │
       │                                │    instance_name           │
       │                                │                            │
       │                                │ 2. Verificar status        │
       │                                │    (active/warming)        │
       │                                │                            │
       │                                │ 3. Registrar interacao     │
       │                                │    chip_interactions       │
       │                                │                            │
       │                                │ 4. Atualizar contadores    │
       │                                │    msgs_recebidas_*        │
       │                                │                            │
       │                                │ 5. Se active, adicionar    │
       │                                │    _chip context           │
       │                                │ ──────────────────────────>│
       │                                │                            │
       │                                │                            │ 6. Processar
       │                                │                            │    mensagem
       │                                │                            │
       │                                │                            │ 7. Gerar
       │                                │                            │    resposta
       │                                │                            │
       │                                │<────────────────────────── │
       │                                │    resposta + chip_context │
       │                                │                            │
       │<────────────────────────────── │ 8. Enviar via instance     │
       │    POST /message/send          │    do chip                 │
       │                                │                            │

EVENTOS PROCESSADOS:

  messages.upsert     → processar_mensagem_recebida()
  connection.update   → processar_conexao()
  messages.update     → processar_status_mensagem()
  qrcode.updated      → processar_qr_code()
```
