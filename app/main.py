"""
Agente Júlia - API Principal
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import health, test_db, test_llm, test_whatsapp, webhook, chatwoot, jobs, metricas, metricas_grupos, admin, piloto, campanhas, integridade
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


app = FastAPI(
    title=settings.APP_NAME,
    description="Agente Júlia - Escalista Virtual para Staffing Médico",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router, tags=["Health"])
app.include_router(test_db.router)
app.include_router(test_llm.router)
app.include_router(test_whatsapp.router)
app.include_router(webhook.router)
app.include_router(chatwoot.router)
app.include_router(jobs.router)
app.include_router(metricas.router)
app.include_router(metricas_grupos.router)
app.include_router(admin.router)
app.include_router(piloto.router)
app.include_router(campanhas.router)
app.include_router(integridade.router)

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
