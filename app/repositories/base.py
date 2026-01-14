"""
Base Repository - Interface comum para todos os repositories.

Sprint 30 - S30.E3.1

Este modulo define a interface base que todos os repositories
devem implementar, garantindo consistencia e facilitando testes.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Any
from dataclasses import dataclass

# Type variable para entidades
T = TypeVar('T')


@dataclass
class QueryResult(Generic[T]):
    """Resultado padronizado de query."""
    data: Optional[T] = None
    success: bool = True
    error: Optional[str] = None
    count: Optional[int] = None


class BaseRepository(ABC, Generic[T]):
    """
    Interface base para repositories.

    Todos os repositories devem herdar desta classe e implementar
    os metodos abstratos.

    Attributes:
        db: Cliente de banco de dados (Supabase, Mock, etc.)
        table_name: Nome da tabela no banco de dados

    Example:
        class ClienteRepository(BaseRepository[Cliente]):
            @property
            def table_name(self) -> str:
                return "clientes"

            async def buscar_por_id(self, id: str) -> Optional[Cliente]:
                response = self.db.table(self.table_name).select("*").eq("id", id).execute()
                return Cliente.from_dict(response.data[0]) if response.data else None
    """

    def __init__(self, db_client: Any):
        """
        Inicializa o repository.

        Args:
            db_client: Cliente de banco de dados (Supabase, Mock, etc.)
        """
        self.db = db_client

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Nome da tabela no banco."""
        pass

    @abstractmethod
    async def buscar_por_id(self, id: str) -> Optional[T]:
        """
        Busca entidade por ID.

        Args:
            id: UUID da entidade

        Returns:
            Entidade ou None se nao encontrada
        """
        pass

    @abstractmethod
    async def listar(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[T]:
        """
        Lista entidades com filtros opcionais.

        Args:
            limit: Maximo de resultados
            offset: Pular N primeiros resultados
            **filters: Filtros adicionais (ex: status="ativa")

        Returns:
            Lista de entidades
        """
        pass

    @abstractmethod
    async def criar(self, data: dict) -> T:
        """
        Cria nova entidade.

        Args:
            data: Dados da entidade

        Returns:
            Entidade criada com ID
        """
        pass

    @abstractmethod
    async def atualizar(self, id: str, data: dict) -> Optional[T]:
        """
        Atualiza entidade existente.

        Args:
            id: UUID da entidade
            data: Campos a atualizar

        Returns:
            Entidade atualizada ou None se nao encontrada
        """
        pass

    @abstractmethod
    async def deletar(self, id: str) -> bool:
        """
        Deleta entidade.

        Args:
            id: UUID da entidade

        Returns:
            True se deletou, False se nao encontrada
        """
        pass

    # Metodos utilitarios (implementacao padrao)

    async def existe(self, id: str) -> bool:
        """Verifica se entidade existe."""
        return await self.buscar_por_id(id) is not None

    async def contar(self, **filters) -> int:
        """Conta entidades com filtros."""
        items = await self.listar(**filters)
        return len(items)
