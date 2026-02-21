"""
Testes para Rich Media Templates.

Sprint 68 — Epic 68.3, Chunk 9.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRichMediaTemplates:

    @pytest.mark.asyncio
    async def test_criar_template_com_media_image(self):
        mock_sb = MagicMock()
        resp_token = MagicMock()
        resp_token.data = [{"meta_access_token": "token_abc"}]
        resp_upsert = MagicMock()
        resp_upsert.data = [{"template_name": "rich_promo"}]

        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = resp_token
        mock_sb.table.return_value.upsert.return_value.execute.return_value = resp_upsert

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "tmpl_123", "status": "PENDING"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with (
            patch("app.services.meta.template_service.supabase", mock_sb),
            patch("app.services.http_client.get_http_client", return_value=mock_client),
        ):
            from app.services.meta.template_service import MetaTemplateService

            service = MetaTemplateService()
            result = await service.criar_template_com_media(
                waba_id="waba_1",
                name="rich_promo",
                category="MARKETING",
                language="pt_BR",
                body_text="Confira: {{1}}",
                header_format="IMAGE",
                header_media_url="https://example.com/image.jpg",
            )
            assert result["success"] is True

    def test_mapear_variaveis_com_media(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        template = {"variable_mapping": {"1": "nome"}, "header_format": "IMAGE"}
        destinatario = {"nome": "Dr Carlos"}

        components = mapper.mapear_variaveis_com_media(
            template, destinatario, media_id="media_123"
        )
        assert len(components) == 2
        assert components[0]["type"] == "header"
        assert components[0]["parameters"][0]["type"] == "image"

    def test_mapear_variaveis_sem_media(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        template = {"variable_mapping": {"1": "nome"}}
        destinatario = {"nome": "Dr Carlos"}

        components = mapper.mapear_variaveis_com_media(template, destinatario)
        assert len(components) == 1
        assert components[0]["type"] == "body"

    def test_construir_header_parameter_image(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        header = mapper._construir_header_parameter("IMAGE", "media_123")
        assert header["type"] == "header"
        assert header["parameters"][0]["image"]["id"] == "media_123"

    def test_construir_header_parameter_video(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        header = mapper._construir_header_parameter("VIDEO", "media_456")
        assert header["parameters"][0]["type"] == "video"

    def test_construir_header_parameter_document(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        header = mapper._construir_header_parameter("DOCUMENT", "media_789")
        assert header["parameters"][0]["type"] == "document"

    def test_construir_header_parameter_invalido(self):
        from app.services.meta.template_mapper import TemplateMapper

        mapper = TemplateMapper()
        result = mapper._construir_header_parameter("INVALID", "media_0")
        assert result is None
