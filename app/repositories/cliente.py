"""
Repository para Clientes (Medicos).

Sprint 30 - S30.E3.2
"""

import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from .base import BaseRepository

logger = logging.getLogger(__name__)


@dataclass
class Cliente:
    """
    Entidade Cliente (Medico).

    Representa um medico no sistema Julia.
    """

    id: str
    telefone: str
    primeiro_nome: Optional[str] = None
    sobrenome: Optional[str] = None
    email: Optional[str] = None
    crm: Optional[str] = None
    especialidade_id: Optional[str] = None
    status: str = "novo"
    stage_jornada: str = "novo"
    opt_out: bool = False
    optout_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Cliente":
        """Cria Cliente a partir de dict do banco."""
        return cls(
            id=data.get("id", ""),
            telefone=data.get("telefone", ""),
            primeiro_nome=data.get("primeiro_nome"),
            sobrenome=data.get("sobrenome"),
            email=data.get("email"),
            crm=data.get("crm"),
            especialidade_id=data.get("especialidade_id"),
            status=data.get("status", "novo"),
            stage_jornada=data.get("stage_jornada", "novo"),
            opt_out=data.get("opt_out", False),
            optout_at=data.get("optout_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """Converte para dict (para updates)."""
        return {
            k: v
            for k, v in {
                "telefone": self.telefone,
                "primeiro_nome": self.primeiro_nome,
                "sobrenome": self.sobrenome,
                "email": self.email,
                "crm": self.crm,
                "especialidade_id": self.especialidade_id,
                "status": self.status,
                "stage_jornada": self.stage_jornada,
                "opt_out": self.opt_out,
                "optout_at": self.optout_at,
            }.items()
            if v is not None
        }


class ClienteRepository(BaseRepository[Cliente]):
    """
    Repository para operacoes de Cliente.

    Uso:
        repo = ClienteRepository(supabase)
        cliente = await repo.buscar_por_telefone("5511999999999")

    Com dependency injection:
        async def endpoint(repo: ClienteRepository = Depends(get_cliente_repo)):
            cliente = await repo.buscar_por_id("123")
    """

    @property
    def table_name(self) -> str:
        return "clientes"

    async def buscar_por_id(self, id: str) -> Optional[Cliente]:
        """Busca cliente por ID."""
        try:
            response = self.db.table(self.table_name).select("*").eq("id", id).execute()
            if response.data:
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente {id}: {e}")
            return None

    async def buscar_por_telefone(self, telefone: str) -> Optional[Cliente]:
        """
        Busca cliente por telefone.

        Args:
            telefone: Numero do telefone (sera normalizado)

        Returns:
            Cliente ou None
        """
        telefone_limpo = "".join(filter(str.isdigit, telefone))
        try:
            response = (
                self.db.table(self.table_name).select("*").eq("telefone", telefone_limpo).execute()
            )
            if response.data:
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente por telefone: {e}")
            return None

    async def listar(self, limit: int = 100, offset: int = 0, **filters) -> List[Cliente]:
        """Lista clientes com filtros."""
        try:
            query = self.db.table(self.table_name).select("*")

            # Aplicar filtros
            if "status" in filters:
                query = query.eq("status", filters["status"])
            if "opt_out" in filters:
                query = query.eq("opt_out", filters["opt_out"])
            if "especialidade_id" in filters:
                query = query.eq("especialidade_id", filters["especialidade_id"])
            if "stage_jornada" in filters:
                query = query.eq("stage_jornada", filters["stage_jornada"])

            response = query.range(offset, offset + limit - 1).execute()
            return [Cliente.from_dict(item) for item in response.data or []]
        except Exception as e:
            logger.error(f"Erro ao listar clientes: {e}")
            return []

    async def criar(self, data: dict) -> Cliente:
        """Cria novo cliente."""
        # Normalizar telefone
        if "telefone" in data:
            data["telefone"] = "".join(filter(str.isdigit, data["telefone"]))

        try:
            response = self.db.table(self.table_name).insert(data).execute()
            if response.data:
                logger.info(f"Cliente criado: {response.data[0].get('id')}")
                return Cliente.from_dict(response.data[0])
            raise ValueError("Falha ao criar cliente")
        except Exception as e:
            logger.error(f"Erro ao criar cliente: {e}")
            raise

    async def atualizar(self, id: str, data: dict) -> Optional[Cliente]:
        """Atualiza cliente existente."""
        try:
            response = self.db.table(self.table_name).update(data).eq("id", id).execute()
            if response.data:
                logger.info(f"Cliente atualizado: {id}")
                return Cliente.from_dict(response.data[0])
            return None
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente {id}: {e}")
            return None

    async def deletar(self, id: str) -> bool:
        """Deleta cliente (soft delete via status)."""
        try:
            response = (
                self.db.table(self.table_name).update({"status": "deletado"}).eq("id", id).execute()
            )
            if response.data:
                logger.info(f"Cliente deletado: {id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao deletar cliente {id}: {e}")
            return False

    # Metodos especificos de negocio

    async def buscar_ou_criar(self, telefone: str, primeiro_nome: Optional[str] = None) -> Cliente:
        """
        Busca cliente ou cria se nao existir.

        Args:
            telefone: Numero do telefone
            primeiro_nome: Nome do medico (opcional)

        Returns:
            Cliente existente ou recem-criado
        """
        cliente = await self.buscar_por_telefone(telefone)
        if cliente:
            return cliente

        data = {
            "telefone": telefone,
            "primeiro_nome": primeiro_nome,
            "stage_jornada": "novo",
            "status": "novo",
        }
        return await self.criar(data)

    async def marcar_optout(self, id: str) -> Optional[Cliente]:
        """
        Marca cliente como opted-out.

        Args:
            id: UUID do cliente

        Returns:
            Cliente atualizado ou None
        """
        from datetime import timezone

        return await self.atualizar(
            id,
            {
                "status": "opted_out",
                "opt_out": True,
                "optout_at": datetime.now(timezone.utc).isoformat(),
            },
        )
