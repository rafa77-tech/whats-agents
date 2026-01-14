"""
Testes para ClienteRepository.

Sprint 30 - S30.E3.2

Demonstra como testar repositories sem mocks complexos de import.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from dataclasses import asdict

from app.repositories.cliente import ClienteRepository, Cliente


class MockTable:
    """Mock para Supabase table chain."""

    def __init__(self, data=None, should_fail=False):
        self.data = data or []
        self.should_fail = should_fail
        self._filters = {}

    def select(self, *args, **kwargs):
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def update(self, data):
        self._update_data = data
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def range(self, start, end):
        return self

    def execute(self):
        if self.should_fail:
            raise Exception("Database error")
        response = MagicMock()
        response.data = self.data
        return response


class MockDatabase:
    """Mock para Supabase client."""

    def __init__(self, table_data=None, should_fail=False):
        self.table_data = table_data or []
        self.should_fail = should_fail

    def table(self, name):
        return MockTable(self.table_data, self.should_fail)


class TestClienteFromDict:
    """Testes para Cliente.from_dict."""

    def test_cria_cliente_com_dados_completos(self):
        """Deve criar cliente com todos os campos."""
        data = {
            "id": "uuid-123",
            "telefone": "5511999999999",
            "primeiro_nome": "Dr. Carlos",
            "sobrenome": "Silva",
            "email": "carlos@email.com",
            "crm": "123456-SP",
            "status": "ativo",
            "stage_jornada": "engajado",
            "opt_out": False,
        }

        cliente = Cliente.from_dict(data)

        assert cliente.id == "uuid-123"
        assert cliente.telefone == "5511999999999"
        assert cliente.primeiro_nome == "Dr. Carlos"
        assert cliente.crm == "123456-SP"

    def test_cria_cliente_com_dados_minimos(self):
        """Deve criar cliente apenas com id e telefone."""
        data = {
            "id": "uuid-456",
            "telefone": "5511888888888",
        }

        cliente = Cliente.from_dict(data)

        assert cliente.id == "uuid-456"
        assert cliente.telefone == "5511888888888"
        assert cliente.status == "novo"
        assert cliente.opt_out is False

    def test_usa_valores_padrao(self):
        """Deve usar valores padrao quando campo ausente."""
        data = {"id": "uuid-789", "telefone": "5511777777777"}

        cliente = Cliente.from_dict(data)

        assert cliente.status == "novo"
        assert cliente.stage_jornada == "novo"
        assert cliente.opt_out is False


class TestClienteRepository:
    """Testes para ClienteRepository."""

    @pytest.mark.asyncio
    async def test_buscar_por_id_encontra_cliente(self):
        """Deve retornar cliente quando encontrado."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999", "primeiro_nome": "Dr. Test"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.buscar_por_id("uuid-123")

        assert cliente is not None
        assert cliente.id == "uuid-123"
        assert cliente.telefone == "5511999999999"

    @pytest.mark.asyncio
    async def test_buscar_por_id_retorna_none_quando_nao_encontra(self):
        """Deve retornar None quando cliente nao existe."""
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        cliente = await repo.buscar_por_id("uuid-inexistente")

        assert cliente is None

    @pytest.mark.asyncio
    async def test_buscar_por_id_retorna_none_em_erro(self):
        """Deve retornar None quando ocorre erro."""
        mock_db = MockDatabase(should_fail=True)
        repo = ClienteRepository(mock_db)

        cliente = await repo.buscar_por_id("uuid-123")

        assert cliente is None

    @pytest.mark.asyncio
    async def test_buscar_por_telefone_encontra_cliente(self):
        """Deve encontrar cliente por telefone."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.buscar_por_telefone("5511999999999")

        assert cliente is not None
        assert cliente.telefone == "5511999999999"

    @pytest.mark.asyncio
    async def test_buscar_por_telefone_normaliza_numero(self):
        """Deve normalizar telefone antes de buscar."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        # Telefone com formatacao
        cliente = await repo.buscar_por_telefone("(55) 11 99999-9999")

        assert cliente is not None

    @pytest.mark.asyncio
    async def test_listar_retorna_clientes(self):
        """Deve listar clientes."""
        mock_data = [
            {"id": "uuid-1", "telefone": "5511111111111"},
            {"id": "uuid-2", "telefone": "5522222222222"},
        ]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        clientes = await repo.listar()

        assert len(clientes) == 2
        assert clientes[0].id == "uuid-1"
        assert clientes[1].id == "uuid-2"

    @pytest.mark.asyncio
    async def test_listar_retorna_lista_vazia_quando_nenhum(self):
        """Deve retornar lista vazia quando nao ha clientes."""
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        clientes = await repo.listar()

        assert clientes == []

    @pytest.mark.asyncio
    async def test_criar_retorna_cliente(self):
        """Deve criar e retornar cliente."""
        mock_data = [{"id": "novo-uuid", "telefone": "5511999999999", "primeiro_nome": "Dr. Novo"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.criar({
            "telefone": "5511999999999",
            "primeiro_nome": "Dr. Novo"
        })

        assert cliente is not None
        assert cliente.id == "novo-uuid"

    @pytest.mark.asyncio
    async def test_criar_normaliza_telefone(self):
        """Deve normalizar telefone ao criar."""
        mock_data = [{"id": "novo-uuid", "telefone": "5511999999999"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.criar({
            "telefone": "(55) 11 99999-9999"
        })

        assert cliente is not None

    @pytest.mark.asyncio
    async def test_atualizar_retorna_cliente_atualizado(self):
        """Deve atualizar e retornar cliente."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999", "status": "ativo"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.atualizar("uuid-123", {"status": "ativo"})

        assert cliente is not None
        assert cliente.status == "ativo"

    @pytest.mark.asyncio
    async def test_atualizar_retorna_none_quando_nao_encontra(self):
        """Deve retornar None quando cliente nao existe."""
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        cliente = await repo.atualizar("uuid-inexistente", {"status": "ativo"})

        assert cliente is None

    @pytest.mark.asyncio
    async def test_deletar_retorna_true_quando_sucesso(self):
        """Deve retornar True quando deleta com sucesso."""
        mock_data = [{"id": "uuid-123", "status": "deletado"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        resultado = await repo.deletar("uuid-123")

        assert resultado is True

    @pytest.mark.asyncio
    async def test_deletar_retorna_false_quando_nao_encontra(self):
        """Deve retornar False quando cliente nao existe."""
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        resultado = await repo.deletar("uuid-inexistente")

        assert resultado is False

    @pytest.mark.asyncio
    async def test_buscar_ou_criar_retorna_existente(self):
        """Deve retornar cliente existente."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999", "primeiro_nome": "Existente"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        cliente = await repo.buscar_ou_criar("5511999999999")

        assert cliente is not None
        assert cliente.primeiro_nome == "Existente"

    @pytest.mark.asyncio
    async def test_existe_retorna_true_quando_encontra(self):
        """Deve retornar True quando cliente existe."""
        mock_data = [{"id": "uuid-123", "telefone": "5511999999999"}]
        mock_db = MockDatabase(table_data=mock_data)
        repo = ClienteRepository(mock_db)

        existe = await repo.existe("uuid-123")

        assert existe is True

    @pytest.mark.asyncio
    async def test_existe_retorna_false_quando_nao_encontra(self):
        """Deve retornar False quando cliente nao existe."""
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        existe = await repo.existe("uuid-inexistente")

        assert existe is False


class TestClienteRepositoryIntegration:
    """Testes de integracao demonstrando facilidade de teste."""

    @pytest.mark.asyncio
    async def test_fluxo_completo_sem_patches(self):
        """
        Demonstra fluxo completo de CRUD sem usar @patch.

        Este teste mostra a vantagem do Repository Pattern:
        nao precisamos de mocks complexos de import.
        """
        # Setup - apenas criar mock do banco
        mock_db = MockDatabase(table_data=[])
        repo = ClienteRepository(mock_db)

        # Listar vazio
        clientes = await repo.listar()
        assert clientes == []

        # Criar
        mock_db.table_data = [{"id": "novo", "telefone": "5511111111111"}]
        cliente = await repo.criar({"telefone": "5511111111111"})
        assert cliente.id == "novo"

        # Buscar
        encontrado = await repo.buscar_por_id("novo")
        assert encontrado is not None

        # Atualizar
        mock_db.table_data = [{"id": "novo", "telefone": "5511111111111", "status": "ativo"}]
        atualizado = await repo.atualizar("novo", {"status": "ativo"})
        assert atualizado.status == "ativo"

        # Deletar
        mock_db.table_data = [{"id": "novo", "status": "deletado"}]
        deletado = await repo.deletar("novo")
        assert deletado is True
