"""
Dependency Injection para Repositories.

Sprint 30 - S30.E3.3

Este modulo fornece funcoes de dependencia para uso com FastAPI Depends.

Uso em endpoints:
    from app.repositories.deps import get_cliente_repo
    from app.repositories.cliente import ClienteRepository

    @router.get("/clientes/{id}")
    async def get_cliente(
        id: str,
        repo: ClienteRepository = Depends(get_cliente_repo)
    ):
        return await repo.buscar_por_id(id)

Uso em testes:
    from app.repositories.cliente import ClienteRepository

    def test_buscar_cliente():
        mock_db = MockDatabase()
        repo = ClienteRepository(mock_db)
        # Testar sem patches!
"""
from functools import lru_cache
from typing import Generator

from app.services.supabase import supabase
from .cliente import ClienteRepository


@lru_cache()
def get_cliente_repo() -> ClienteRepository:
    """
    Retorna instancia singleton do ClienteRepository.

    Uso:
        @router.get("/clientes/{id}")
        async def get_cliente(
            id: str,
            repo: ClienteRepository = Depends(get_cliente_repo)
        ):
            return await repo.buscar_por_id(id)
    """
    return ClienteRepository(supabase)


# Factory functions para testes
def create_cliente_repo(db_client) -> ClienteRepository:
    """
    Cria ClienteRepository com cliente de banco customizado.

    Util para testes:
        mock_db = MockDatabase()
        repo = create_cliente_repo(mock_db)
    """
    return ClienteRepository(db_client)
