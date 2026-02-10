"""
Agente Júlia - API Principal
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import (
    health,
    test_db,
    debug_llm,
    debug_whatsapp,
    webhook,
    chatwoot,
    jobs,
    metricas,
    metricas_grupos,
    admin,
    piloto,
    campanhas,
    integridade,
    handoff,
    warmer,
    group_entry,
    webhook_router,
    webhook_zapi,
    chips_dashboard,
    sistema,
    guardrails,
    policy,
    dashboard_conversations,
    extraction,
    supervisor_channel,
    sse,
    incidents,
)
from app.api.error_handlers import register_exception_handlers
from app.api.middleware import TracingMiddleware
from fastapi.staticfiles import StaticFiles

# Configurar logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia startup e shutdown da aplicação."""
    # Startup
    print(f"🚀 Iniciando {settings.APP_NAME}...")
    yield
    # Shutdown
    print(f"👋 Encerrando {settings.APP_NAME}...")
    # Sprint 44 T06.2: Fechar HTTP client singleton
    try:
        from app.services.http_client import close_http_client

        await close_http_client()
    except Exception as e:
        print(f"Erro ao fechar HTTP client: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    description="Agente Júlia - Escalista Virtual para Staffing Médico",
    version="0.1.0",
    lifespan=lifespan,
)

# Registrar exception handlers para respostas de erro consistentes
register_exception_handlers(app)

# Sprint 31: Tracing middleware para correlation ID
app.add_middleware(TracingMiddleware)

# CORS - configurável via CORS_ORIGINS no .env
# Desenvolvimento: CORS_ORIGINS="*" (padrão)
# Produção: CORS_ORIGINS="https://app.revoluna.com,https://admin.revoluna.com"
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True
    if settings.CORS_ORIGINS != "*"
    else False,  # Credentials só com origens específicas
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router, tags=["Health"])
app.include_router(test_db.router)
app.include_router(debug_llm.router)
app.include_router(debug_whatsapp.router)
app.include_router(webhook.router)
app.include_router(chatwoot.router)
app.include_router(jobs.router)
app.include_router(metricas.router)
app.include_router(metricas_grupos.router)
app.include_router(admin.router)
app.include_router(piloto.router)
app.include_router(campanhas.router)
app.include_router(integridade.router)
app.include_router(handoff.router)  # Sprint 20 - External Handoff
app.include_router(warmer.router)  # Sprint 25 - Julia Warmer
app.include_router(group_entry.router)  # Sprint 25 - Group Entry Engine
app.include_router(webhook_router.router)  # Sprint 26 - Multi-chip Webhook Router
app.include_router(webhook_zapi.router)  # Sprint 27 - Z-API Webhook
app.include_router(chips_dashboard.router)  # Sprint 26 - Chips Dashboard
app.include_router(sistema.router)  # Sprint 32 - Sistema Config (Modo Piloto)
app.include_router(guardrails.router)  # Sprint 43 - Guardrails API
app.include_router(policy.router)  # Sprint 43 - Policy Engine API
app.include_router(dashboard_conversations.router)  # Sprint 43 - Dashboard Conversations
app.include_router(extraction.router)  # Sprint 53 - Extraction Pipeline
app.include_router(supervisor_channel.router)  # Sprint 54 - Supervisor Channel
app.include_router(sse.router)  # Sprint 54 - SSE Real-Time
app.include_router(incidents.router)  # Sprint 55 - Health Incidents

# Arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }
