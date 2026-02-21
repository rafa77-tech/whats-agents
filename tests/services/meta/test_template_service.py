"""
Testes para Meta Template Service.

Sprint 66 — CRUD de templates com Graph API + banco local.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.meta.template_service import MetaTemplateService


@pytest.fixture
def service():
    return MetaTemplateService()


@pytest.fixture
def mock_supabase():
    with patch("app.services.meta.template_service.supabase") as mock:
        yield mock


@pytest.fixture
def mock_http():
    client = AsyncMock()
    with patch(
        "app.services.meta.template_service.get_http_client",
        return_value=client,
    ) as p:
        yield client


class TestObterAccessToken:
    """Testes para busca de access_token do banco."""

    @pytest.mark.asyncio
    async def test_encontra_token(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"meta_access_token": "token_abc"}]
        )
        token = await service._obter_access_token("waba_123")
        assert token == "token_abc"

    @pytest.mark.asyncio
    async def test_token_nao_encontrado(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        token = await service._obter_access_token("waba_inexistente")
        assert token is None

    @pytest.mark.asyncio
    async def test_token_erro_retorna_none(self, service, mock_supabase):
        mock_supabase.table.side_effect = Exception("DB error")
        token = await service._obter_access_token("waba_123")
        assert token is None


class TestCriarTemplate:
    """Testes para criação de templates."""

    @pytest.mark.asyncio
    async def test_criar_sucesso(self, service):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "tmpl_123", "status": "PENDING"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_upsert_result = MagicMock(data=[{"id": "local-1"}])

        with (
            patch.object(service, "_obter_access_token", return_value="token_abc"),
            patch(
                "app.services.http_client.get_http_client",
                return_value=mock_client,
            ),
            patch("app.services.meta.template_service.supabase") as mock_sb,
        ):
            mock_sb.table.return_value.upsert.return_value.execute.return_value = (
                mock_upsert_result
            )

            result = await service.criar_template(
                waba_id="waba_123",
                name="julia_test",
                category="MARKETING",
                language="pt_BR",
                components=[{"type": "BODY", "text": "Oi {{1}}"}],
            )

        assert result["success"] is True
        assert result["meta_status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_criar_sem_access_token(self, service):
        with patch.object(service, "_obter_access_token", return_value=None):
            result = await service.criar_template(
                waba_id="waba_123",
                name="julia_test",
                category="MARKETING",
                language="pt_BR",
                components=[],
            )

        assert result["success"] is False
        assert "Access token" in result["error"]

    @pytest.mark.asyncio
    async def test_criar_erro_meta_salva_local(self, service):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Meta API error"))

        mock_upsert_result = MagicMock(data=[{"id": "local-1"}])

        with (
            patch.object(service, "_obter_access_token", return_value="token_abc"),
            patch(
                "app.services.http_client.get_http_client",
                return_value=mock_client,
            ),
            patch("app.services.meta.template_service.supabase") as mock_sb,
        ):
            mock_sb.table.return_value.upsert.return_value.execute.return_value = (
                mock_upsert_result
            )

            result = await service.criar_template(
                waba_id="waba_123",
                name="julia_test",
                category="MARKETING",
                language="pt_BR",
                components=[],
            )

        # Deve salvar localmente mesmo com erro da Meta
        assert result["success"] is True
        assert result["meta_status"] == "SUBMIT_ERROR"


class TestListarTemplates:
    """Testes para listagem de templates."""

    @pytest.mark.asyncio
    async def test_listar_todos(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"template_name": "t1"}, {"template_name": "t2"}]
        )
        result = await service.listar_templates("waba_123")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_listar_com_filtro_status(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{"template_name": "t1", "status": "APPROVED"}]
        )
        result = await service.listar_templates("waba_123", status="APPROVED")
        assert len(result) == 1


class TestBuscarTemplatePorNome:
    """Testes para busca por nome."""

    @pytest.mark.asyncio
    async def test_buscar_approved(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"template_name": "julia_discovery_v1", "status": "APPROVED"}]
        )
        result = await service.buscar_template_por_nome("julia_discovery_v1")
        assert result is not None
        assert result["status"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_buscar_nao_encontrado(self, service, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result = await service.buscar_template_por_nome("inexistente")
        assert result is None


class TestSincronizarTemplates:
    """Testes para sincronização com Meta."""

    @pytest.mark.asyncio
    async def test_sync_sucesso(self, service):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "t1", "status": "APPROVED", "components": []},
                {"id": "2", "name": "t2", "status": "PENDING", "components": []},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(service, "_obter_access_token", return_value="token_abc"),
            patch(
                "app.services.http_client.get_http_client",
                return_value=mock_client,
            ),
            patch("app.services.meta.template_service.supabase") as mock_sb,
        ):
            mock_sb.table.return_value.upsert.return_value.execute = MagicMock()

            result = await service.sincronizar_templates("waba_123")

        assert result["success"] is True
        assert result["total"] == 2
        assert result["synced"] == 2

    @pytest.mark.asyncio
    async def test_sync_sem_token(self, service):
        with patch.object(service, "_obter_access_token", return_value=None):
            result = await service.sincronizar_templates("waba_123")

        assert result["success"] is False
        assert "Access token" in result["error"]


class TestDeletarTemplate:
    """Testes para deleção de templates."""

    @pytest.mark.asyncio
    async def test_deletar_sucesso(self, service):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)

        with (
            patch.object(service, "_obter_access_token", return_value="token_abc"),
            patch(
                "app.services.http_client.get_http_client",
                return_value=mock_client,
            ),
            patch("app.services.meta.template_service.supabase") as mock_sb,
        ):
            mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute = MagicMock()

            result = await service.deletar_template("waba_123", "julia_test")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_deletar_sem_token_remove_local(self, service):
        with (
            patch.object(service, "_obter_access_token", return_value=None),
            patch("app.services.meta.template_service.supabase") as mock_sb,
        ):
            mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute = MagicMock()

            result = await service.deletar_template("waba_123", "julia_test")

        # Remove localmente mesmo sem token
        assert result["success"] is True
