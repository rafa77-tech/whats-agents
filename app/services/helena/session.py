"""
Gerenciamento de sessão para Helena.

Sprint 47: Adaptado de app/services/slack/session.py com ajustes para Helena.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

SESSION_TTL_MINUTES = 30
MAX_MESSAGES = 20


@dataclass
class HelenaSession:
    """Sessão de conversa com Helena."""

    user_id: str
    channel_id: str
    mensagens: list = field(default_factory=list)
    contexto: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def adicionar_mensagem(self, role: str, content: Any) -> None:
        """Adiciona mensagem ao histórico."""
        self.mensagens.append({"role": role, "content": content})
        # Manter apenas últimas MAX_MESSAGES
        if len(self.mensagens) > MAX_MESSAGES:
            self.mensagens = self.mensagens[-MAX_MESSAGES:]
        self.updated_at = datetime.now(timezone.utc)

    def atualizar_contexto(self, key: str, value: Any) -> None:
        """Atualiza contexto da sessão."""
        self.contexto[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def limpar_contexto(self) -> None:
        """Limpa contexto da sessão."""
        self.contexto = {}
        self.updated_at = datetime.now(timezone.utc)


class SessionManager:
    """Gerencia sessões de Helena no banco de dados."""

    def __init__(self, user_id: str, channel_id: str):
        self.user_id = user_id
        self.channel_id = channel_id
        self.session: Optional[HelenaSession] = None

    async def carregar(self) -> HelenaSession:
        """Carrega sessão existente ou cria nova."""
        try:
            # Buscar sessão ativa
            result = (
                supabase.table("helena_sessoes")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("channel_id", self.channel_id)
                .gte("expires_at", datetime.now(timezone.utc).isoformat())
                .limit(1)
                .execute()
            )

            if result.data and len(result.data) > 0:
                data = result.data[0]
                self.session = HelenaSession(
                    user_id=self.user_id,
                    channel_id=self.channel_id,
                    mensagens=data.get("mensagens", []),
                    contexto=data.get("contexto", {}),
                    created_at=datetime.fromisoformat(
                        data["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        data["updated_at"].replace("Z", "+00:00")
                    ),
                )
                logger.debug(f"Sessão Helena carregada: {self.user_id}")
            else:
                self.session = HelenaSession(
                    user_id=self.user_id,
                    channel_id=self.channel_id,
                )
                logger.debug(f"Nova sessão Helena criada: {self.user_id}")

        except Exception as e:
            logger.warning(f"Erro ao carregar sessão Helena: {e}")
            self.session = HelenaSession(
                user_id=self.user_id,
                channel_id=self.channel_id,
            )

        return self.session

    async def salvar(self) -> None:
        """Persiste sessão no banco."""
        if not self.session:
            return

        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_TTL_MINUTES)

            supabase.table("helena_sessoes").upsert(
                {
                    "user_id": self.user_id,
                    "channel_id": self.channel_id,
                    "mensagens": self.session.mensagens,
                    "contexto": self.session.contexto,
                    "created_at": self.session.created_at.isoformat(),
                    "updated_at": self.session.updated_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                },
                on_conflict="user_id,channel_id",
            ).execute()

            logger.debug(f"Sessão Helena salva: {self.user_id}")

        except Exception as e:
            logger.error(f"Erro ao salvar sessão Helena: {e}")

    @property
    def mensagens(self) -> list:
        """Retorna mensagens da sessão."""
        return self.session.mensagens if self.session else []

    def adicionar_mensagem(self, role: str, content: Any) -> None:
        """Adiciona mensagem via proxy."""
        if self.session:
            self.session.adicionar_mensagem(role, content)

    def atualizar_contexto(self, key: str, value: Any) -> None:
        """Atualiza contexto via proxy."""
        if self.session:
            self.session.atualizar_contexto(key, value)
