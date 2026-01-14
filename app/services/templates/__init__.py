"""
Templates de Mensagem - Sprint 30.

Este modulo fornece acesso a templates de mensagens
armazenados no banco de dados com cache Redis.

Uso simples:
    from app.services.templates import get_template

    msg = await get_template("optout_confirmacao")
    msg = await get_template("saudacao_inicial", nome="Dr. Carlos")

Uso avancado:
    from app.services.templates import TemplateRepository

    repo = TemplateRepository()
    template = await repo.buscar_por_slug("optout_confirmacao")
    templates = await repo.listar_por_categoria("confirmacao")
"""
from .repository import (
    MessageTemplate,
    TemplateRepository,
    get_template_repository,
    get_template,
    CACHE_TTL,
)

__all__ = [
    "MessageTemplate",
    "TemplateRepository",
    "get_template_repository",
    "get_template",
    "CACHE_TTL",
]
