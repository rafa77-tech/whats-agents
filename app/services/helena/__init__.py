"""
Helena - Agente de Gestão e Analytics.

Sprint 47: Agente exclusivo para Slack com capacidade de SQL dinâmico.
Helena NÃO é acionável via WhatsApp por segurança.
"""
from app.services.helena.agent import AgenteHelena
from app.services.helena.session import SessionManager

__all__ = ["AgenteHelena", "SessionManager"]
