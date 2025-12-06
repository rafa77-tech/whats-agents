"""
Cliente Supabase para persistencia
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    # === MEDICOS (clientes) ===

    async def get_medico_by_phone(self, telefone: str) -> Optional[dict]:
        """Busca medico pelo telefone."""
        response = self.client.table("clientes").select("*").eq("telefone", telefone).execute()
        return response.data[0] if response.data else None

    async def create_medico(self, telefone: str, primeiro_nome: Optional[str] = None) -> dict:
        """Cria novo medico."""
        data = {
            "telefone": telefone,
            "primeiro_nome": primeiro_nome,
            "stage_jornada": "novo",
            "status": "novo"
        }
        response = self.client.table("clientes").insert(data).execute()
        logger.info(f"Novo medico criado: {telefone[:8]}...")
        return response.data[0]

    async def get_or_create_medico(self, telefone: str) -> dict:
        """Busca ou cria medico."""
        medico = await self.get_medico_by_phone(telefone)
        if not medico:
            medico = await self.create_medico(telefone)
        return medico

    async def update_medico(self, medico_id: str, data: dict) -> dict:
        """Atualiza dados do medico."""
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self.client.table("clientes").update(data).eq("id", medico_id).execute()
        return response.data[0] if response.data else None

    # === CONVERSAS ===

    async def get_conversa_ativa(self, cliente_id: str) -> Optional[dict]:
        """Busca conversa ativa do cliente."""
        response = (
            self.client.table("conversations")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    async def create_conversa(self, cliente_id: str) -> dict:
        """Cria nova conversa."""
        data = {
            "cliente_id": cliente_id,
            "status": "active",
            "controlled_by": "ai",
            "instance_id": settings.evolution_instance
        }
        response = self.client.table("conversations").insert(data).execute()
        logger.info(f"Nova conversa criada para cliente {cliente_id}")
        return response.data[0]

    async def get_or_create_conversa(self, cliente_id: str) -> dict:
        """Busca ou cria conversa ativa."""
        conversa = await self.get_conversa_ativa(cliente_id)
        if not conversa:
            conversa = await self.create_conversa(cliente_id)
        return conversa

    async def update_conversa(self, conversa_id: str, data: dict) -> dict:
        """Atualiza conversa."""
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        response = self.client.table("conversations").update(data).eq("id", conversa_id).execute()
        return response.data[0] if response.data else None

    # === INTERACOES (mensagens) ===

    async def save_interacao(
        self,
        conversa_id: str,
        cliente_id: str,
        direcao: str,  # 'entrada' ou 'saida'
        conteudo: str,
        tipo: str = "texto"
    ) -> dict:
        """Salva mensagem no historico."""
        # Mapear direcao para origem/autor_tipo
        origem = "medico" if direcao == "entrada" else "julia"
        autor_tipo = "medico" if direcao == "entrada" else "ai"

        data = {
            "conversation_id": conversa_id,
            "cliente_id": cliente_id,
            "origem": origem,
            "tipo": tipo,
            "conteudo": conteudo,
            "canal": "whatsapp",
            "autor_tipo": autor_tipo
        }
        response = self.client.table("interacoes").insert(data).execute()
        return response.data[0]

    async def get_historico(self, conversa_id: str, limit: int = 20) -> list:
        """Busca historico de mensagens da conversa."""
        response = (
            self.client.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Retorna em ordem cronologica
        return list(reversed(response.data)) if response.data else []

    # === VAGAS ===

    async def get_vagas_disponiveis(
        self,
        especialidade_id: Optional[str] = None,
        limit: int = 5
    ) -> list:
        """Busca vagas disponiveis."""
        query = (
            self.client.table("vagas")
            .select("*, hospitais(nome, cidade), especialidades(nome)")
            .eq("status", "aberta")
            .gte("data", datetime.now(timezone.utc).date().isoformat())
            .order("data")
            .limit(limit)
        )

        if especialidade_id:
            query = query.eq("especialidade_id", especialidade_id)

        response = query.execute()
        return response.data if response.data else []

    # === HANDOFFS ===

    async def create_handoff(
        self,
        conversa_id: str,
        motivo: str
    ) -> dict:
        """Registra handoff para humano."""
        data = {
            "conversation_id": conversa_id,
            "from_controller": "ai",
            "to_controller": "human",
            "reason": motivo
        }
        response = self.client.table("handoffs").insert(data).execute()

        # Atualizar conversa para controle humano
        await self.update_conversa(conversa_id, {"controlled_by": "human"})

        logger.warning(f"Handoff criado: {motivo}")
        return response.data[0]


# Singleton
db = DatabaseClient()
