"""
Gerenciador de sessoes do agente Slack.

Sprint 10 - S10.E2.2
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.core.config import DatabaseConfig
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class SessionManager:
    """Gerencia sessoes de conversa do agente Slack."""

    def __init__(self, user_id: str, channel_id: str):
        """
        Inicializa o gerenciador de sessao.

        Args:
            user_id: ID do usuario Slack
            channel_id: ID do canal Slack
        """
        self.user_id = user_id
        self.channel_id = channel_id
        self.sessao: Optional[dict] = None
        self.mensagens: list = []

    async def carregar(self) -> dict:
        """
        Carrega sessao existente ou cria nova.

        Returns:
            Dados da sessao
        """
        try:
            result = supabase.table("slack_sessoes").select("*").eq(
                "user_id", self.user_id
            ).eq("channel_id", self.channel_id).execute()

            if result.data:
                sessao = result.data[0]
                expires_at = datetime.fromisoformat(
                    sessao["expires_at"].replace("Z", "+00:00")
                )

                # Verificar se expirou
                if expires_at > datetime.now(timezone.utc):
                    self.sessao = sessao
                    self.mensagens = sessao.get("mensagens", [])
                    logger.info(f"Sessao carregada para {self.user_id}")
                else:
                    # Sessao expirada, criar nova
                    await self.criar()
            else:
                await self.criar()

        except Exception as e:
            logger.error(f"Erro ao carregar sessao: {e}")
            await self.criar()

        return self.sessao

    async def criar(self) -> dict:
        """
        Cria nova sessao.

        Returns:
            Nova sessao criada
        """
        self.sessao = {
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "mensagens": [],
            "contexto": {},
            "acao_pendente": None
        }
        self.mensagens = []
        logger.info(f"Nova sessao criada para {self.user_id}")
        return self.sessao

    async def salvar(self) -> None:
        """Salva sessao no banco."""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=DatabaseConfig.SESSION_TIMEOUT_MINUTES
            )

            # Limitar historico a ultimas 20 mensagens
            mensagens_limitadas = (
                self.mensagens[-20:] if len(self.mensagens) > 20 else self.mensagens
            )

            data = {
                "user_id": self.user_id,
                "channel_id": self.channel_id,
                "mensagens": mensagens_limitadas,
                "contexto": self.sessao.get("contexto", {}),
                "acao_pendente": self.sessao.get("acao_pendente"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat()
            }

            # Upsert
            supabase.table("slack_sessoes").upsert(
                data,
                on_conflict="user_id,channel_id"
            ).execute()

        except Exception as e:
            logger.error(f"Erro ao salvar sessao: {e}")

    def adicionar_mensagem(self, role: str, content) -> None:
        """
        Adiciona mensagem ao historico.

        Args:
            role: 'user' ou 'assistant'
            content: Conteudo da mensagem
        """
        self.mensagens.append({
            "role": role,
            "content": content
        })

    def get_acao_pendente(self) -> Optional[dict]:
        """Retorna acao pendente se houver."""
        return self.sessao.get("acao_pendente") if self.sessao else None

    def set_acao_pendente(self, acao: Optional[dict]) -> None:
        """Define acao pendente."""
        if self.sessao:
            self.sessao["acao_pendente"] = acao

    def get_contexto(self) -> dict:
        """Retorna contexto da sessao."""
        return self.sessao.get("contexto", {}) if self.sessao else {}

    def atualizar_contexto(self, chave: str, valor) -> None:
        """Atualiza valor no contexto."""
        if self.sessao:
            if "contexto" not in self.sessao:
                self.sessao["contexto"] = {}
            self.sessao["contexto"][chave] = valor
