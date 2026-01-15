"""
Testes do EspecialidadeService.

Sprint 31 - S31.E5.5
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.vagas.especialidade_service import (
    EspecialidadeService,
    get_especialidade_service,
)


class TestEspecialidadeServiceNormalizar:
    """Testes da normalização de nomes."""

    def test_normalizar_nome_basico(self):
        """Deve normalizar nome básico."""
        result = EspecialidadeService.normalizar_nome("Cardiologia")
        assert result == "cardiologia"

    def test_normalizar_nome_com_espacos(self):
        """Deve remover espaços extras."""
        result = EspecialidadeService.normalizar_nome("  Cardiologia  ")
        assert result == "cardiologia"

    def test_normalizar_nome_maiusculas(self):
        """Deve converter para minúsculas."""
        result = EspecialidadeService.normalizar_nome("CARDIOLOGIA")
        assert result == "cardiologia"


class TestEspecialidadeServiceBuscar:
    """Testes da busca de especialidades."""

    @pytest.fixture
    def service(self):
        """Fixture para o service."""
        return EspecialidadeService()

    @pytest.mark.asyncio
    async def test_buscar_por_nome_vazio(self, service):
        """Deve retornar None para nome vazio."""
        result = await service.buscar_por_nome("")
        assert result is None

    @pytest.mark.asyncio
    async def test_buscar_por_nome_none(self, service):
        """Deve retornar None para nome None."""
        result = await service.buscar_por_nome(None)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.vagas.especialidade_service.cache_get_json")
    async def test_buscar_por_nome_cached(self, mock_cache, service):
        """Deve retornar do cache quando disponível."""
        mock_cache.return_value = {"id": "uuid-123"}

        result = await service.buscar_por_nome("Cardiologia")

        assert result == "uuid-123"
        mock_cache.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.vagas.especialidade_service.cache_get_json")
    @patch("app.services.vagas.especialidade_service.cache_set_json")
    @patch("app.services.vagas.especialidade_service.supabase")
    async def test_buscar_por_nome_do_banco(
        self, mock_supabase, mock_cache_set, mock_cache_get, service
    ):
        """Deve buscar do banco quando não está em cache."""
        mock_cache_get.return_value = None

        # Mock da query do Supabase
        mock_response = MagicMock()
        mock_response.data = [{"id": "uuid-456", "nome": "Cardiologia"}]
        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = await service.buscar_por_nome("Cardiologia")

        assert result == "uuid-456"
        mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.vagas.especialidade_service.cache_get_json")
    @patch("app.services.vagas.especialidade_service.supabase")
    async def test_buscar_por_nome_nao_encontrada(
        self, mock_supabase, mock_cache_get, service
    ):
        """Deve retornar None quando não encontrada."""
        mock_cache_get.return_value = None

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response

        result = await service.buscar_por_nome("EspecialidadeInexistente")

        assert result is None


class TestEspecialidadeServiceResolver:
    """Testes da resolução de especialidade do médico."""

    @pytest.fixture
    def service(self):
        """Fixture para o service."""
        return EspecialidadeService()

    @pytest.mark.asyncio
    @patch.object(EspecialidadeService, "buscar_por_nome")
    async def test_resolver_especialidade_solicitada(self, mock_buscar, service):
        """Deve usar especialidade solicitada quando fornecida."""
        mock_buscar.return_value = "uuid-solicitada"
        medico = {"especialidade": "Cardiologia", "especialidade_id": "uuid-cadastrada"}

        esp_id, esp_nome, diferente = await service.resolver_especialidade_medico(
            "Ortopedia", medico
        )

        assert esp_id == "uuid-solicitada"
        assert esp_nome == "Ortopedia"
        assert diferente is True  # Diferente da cadastrada

    @pytest.mark.asyncio
    @patch.object(EspecialidadeService, "buscar_por_nome")
    async def test_resolver_especialidade_cadastrada(self, mock_buscar, service):
        """Deve usar especialidade cadastrada quando não solicitada."""
        medico = {
            "especialidade": "Cardiologia",
            "especialidade_id": "uuid-cadastrada"
        }

        esp_id, esp_nome, diferente = await service.resolver_especialidade_medico(
            None, medico
        )

        assert esp_id == "uuid-cadastrada"
        assert esp_nome == "Cardiologia"
        assert diferente is False

    @pytest.mark.asyncio
    @patch.object(EspecialidadeService, "buscar_por_nome")
    async def test_resolver_especialidade_buscar_por_nome(self, mock_buscar, service):
        """Deve buscar por nome quando não tem especialidade_id."""
        mock_buscar.return_value = "uuid-buscado"
        medico = {"especialidade": "Cardiologia"}  # Sem especialidade_id

        esp_id, esp_nome, diferente = await service.resolver_especialidade_medico(
            None, medico
        )

        assert esp_id == "uuid-buscado"
        mock_buscar.assert_called_once_with("Cardiologia")

    @pytest.mark.asyncio
    @patch.object(EspecialidadeService, "buscar_por_nome")
    async def test_resolver_especialidade_solicitada_igual(self, mock_buscar, service):
        """Não deve marcar como diferente se é a mesma."""
        mock_buscar.return_value = "uuid-123"
        medico = {"especialidade": "cardiologia"}  # Lowercase

        esp_id, esp_nome, diferente = await service.resolver_especialidade_medico(
            "Cardiologia", medico  # Title case
        )

        assert diferente is False

    @pytest.mark.asyncio
    @patch.object(EspecialidadeService, "buscar_por_nome")
    async def test_resolver_especialidade_nao_encontrada(self, mock_buscar, service):
        """Deve retornar None quando especialidade não encontrada."""
        mock_buscar.return_value = None
        medico = {}

        esp_id, esp_nome, diferente = await service.resolver_especialidade_medico(
            "EspecialidadeInexistente", medico
        )

        assert esp_id is None
        assert esp_nome == "EspecialidadeInexistente"


class TestSingleton:
    """Testes da factory singleton."""

    def test_get_especialidade_service_singleton(self):
        """Deve retornar a mesma instância."""
        # Reset singleton para teste
        import app.services.vagas.especialidade_service as module
        module._instance = None

        s1 = get_especialidade_service()
        s2 = get_especialidade_service()

        assert s1 is s2
