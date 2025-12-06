"""
FastAPI - Servidor principal do Agente Julia
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from config import settings
from app.agent import julia
from app.evolution import evolution_client

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level_upper, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicacao."""
    logger.info(f"Iniciando {settings.app_name}...")
    logger.info(f"Ambiente: {settings.environment}")
    logger.info(f"Instancia Evolution: {settings.evolution_instance}")

    # Verificar conexao Evolution
    try:
        state = await evolution_client.get_connection_state()
        logger.info(f"Evolution API conectada: {state}")
    except Exception as e:
        logger.warning(f"Nao foi possivel verificar Evolution API: {e}")

    yield

    logger.info("Encerrando aplicacao...")


app = FastAPI(
    title=settings.app_name,
    description="Escalista virtual autonoma para staffing medico",
    version="0.1.0",
    lifespan=lifespan
)


# === MODELS ===

class EvolutionMessage(BaseModel):
    """Payload de mensagem do Evolution API."""
    event: str
    instance: str
    data: dict


class SendMessageRequest(BaseModel):
    """Request para envio manual de mensagem."""
    phone: str
    message: str


class WebhookConfigRequest(BaseModel):
    """Request para configurar webhook."""
    url: str
    events: Optional[list] = None


# === ENDPOINTS ===

@app.get("/")
async def root():
    """Health check basico."""
    return {
        "app": settings.app_name,
        "status": "running",
        "instance": settings.evolution_instance
    }


@app.get("/health")
async def health():
    """Health check detalhado."""
    evolution_ok = False
    try:
        state = await evolution_client.get_connection_state()
        # O estado vem em state.instance.state
        instance_state = state.get("instance", {}).get("state", "")
        evolution_ok = instance_state == "open"
    except Exception:
        pass

    return {
        "status": "healthy",
        "evolution": "connected" if evolution_ok else "disconnected",
        "environment": settings.environment
    }


@app.post("/webhook/evolution")
async def webhook_evolution(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook para receber mensagens do Evolution API.
    Processa mensagens em background para resposta rapida.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao parsear payload: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    event = payload.get("event", "")
    instance = payload.get("instance", "")
    data = payload.get("data", {})

    logger.debug(f"Webhook recebido: {event} de {instance}")

    # Ignorar eventos que nao sao mensagens
    if event != "messages.upsert":
        return {"status": "ignored", "reason": "not a message event"}

    # Ignorar mensagens enviadas por nos (fromMe=true)
    key = data.get("key", {})
    if key.get("fromMe", False):
        return {"status": "ignored", "reason": "outgoing message"}

    # Ignorar mensagens de grupo
    remote_jid = key.get("remoteJid", "")
    if "@g.us" in remote_jid:
        return {"status": "ignored", "reason": "group message"}

    # Extrair telefone e mensagem
    phone = remote_jid.replace("@s.whatsapp.net", "")
    message_id = key.get("id", "")

    # Extrair conteudo da mensagem
    message_data = data.get("message", {})
    content = (
        message_data.get("conversation") or
        message_data.get("extendedTextMessage", {}).get("text") or
        ""
    )

    if not content:
        return {"status": "ignored", "reason": "no text content"}

    logger.info(f"Mensagem recebida de {phone[:8]}...: {content[:50]}...")

    # Processar em background
    background_tasks.add_task(
        process_incoming_message,
        phone=phone,
        content=content,
        message_id=message_id
    )

    return {"status": "processing"}


async def process_incoming_message(phone: str, content: str, message_id: str):
    """Processa mensagem em background."""
    try:
        # 1. Marcar como lida
        try:
            await evolution_client.mark_as_read(phone, message_id)
        except Exception as e:
            logger.warning(f"Erro ao marcar como lida: {e}")

        # 2. Mostrar presenca online
        try:
            await evolution_client.send_presence(phone, "available")
        except Exception as e:
            logger.warning(f"Erro ao enviar presenca: {e}")

        # 3. Mostrar digitando
        try:
            await evolution_client.send_presence(phone, "composing")
        except Exception as e:
            logger.warning(f"Erro ao mostrar digitando: {e}")

        # 4. Processar com Julia
        resposta = await julia.processar_mensagem(
            telefone=phone,
            mensagem=content,
            message_id=message_id
        )

        if not resposta:
            logger.info(f"Sem resposta para {phone[:8]}... (controle humano ou erro)")
            return

        # 5. Simular delay humano (1-3 segundos por mensagem curta)
        delay = min(len(resposta) / 50, 5)  # Max 5 segundos
        await asyncio.sleep(max(1, delay))

        # 6. Enviar resposta
        await evolution_client.send_text(phone, resposta)

        logger.info(f"Resposta enviada para {phone[:8]}...")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem de {phone[:8]}...: {e}")


@app.post("/api/send")
async def send_message(req: SendMessageRequest):
    """Envia mensagem manualmente (para testes)."""
    try:
        result = await evolution_client.send_text(req.phone, req.message)
        return {"status": "sent", "result": result}
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/webhook/configure")
async def configure_webhook(req: WebhookConfigRequest):
    """Configura webhook do Evolution API."""
    try:
        result = await evolution_client.set_webhook(req.url, req.events)
        return {"status": "configured", "result": result}
    except Exception as e:
        logger.error(f"Erro ao configurar webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/webhook/current")
async def get_current_webhook():
    """Retorna configuracao atual do webhook."""
    try:
        result = await evolution_client.get_webhook()
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar webhook: {e}")
        return {"status": "error", "message": str(e)}


# Para rodar: uvicorn app.main:app --reload --port 8000
