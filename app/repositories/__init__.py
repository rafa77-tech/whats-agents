"""
Repositories - Camada de acesso a dados.

Sprint 30

Este modulo implementa o padrao Repository para desacoplar
a logica de negocio do banco de dados.

Vantagens:
- Testes unitarios sem mocks complexos de import
- Injecao de dependencia via FastAPI Depends
- Facilidade para trocar banco de dados no futuro
- Codigo mais limpo e testavel

Uso com dependency injection:
    from fastapi import Depends
    from app.repositories import ClienteRepository
    from app.repositories.deps import get_cliente_repo

    @router.get("/clientes/{id}")
    async def get_cliente(
        id: str,
        repo: ClienteRepository = Depends(get_cliente_repo)
    ):
        return await repo.buscar_por_id(id)

Uso em testes:
    from app.repositories import ClienteRepository

    def test_buscar_cliente():
        mock_db = MockDatabase()
        repo = ClienteRepository(mock_db)
        # Testar sem patches!

Entidades disponiveis:
- Cliente: Representa um medico no sistema
"""

from .base import BaseRepository, QueryResult
from .cliente import ClienteRepository, Cliente
from .deps import get_cliente_repo, create_cliente_repo

__all__ = [
    # Base
    "BaseRepository",
    "QueryResult",
    # Cliente
    "ClienteRepository",
    "Cliente",
    # Dependency injection
    "get_cliente_repo",
    "create_cliente_repo",
]
