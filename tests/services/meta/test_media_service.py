"""
Testes para MetaMediaService.

Sprint 68 — Epic 68.3, Chunk 8.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMetaMediaService:

    @pytest.mark.asyncio
    async def test_upload_media_sucesso(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"meta_access_token": "token_abc"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = resp

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "media_123"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with (
            patch("app.services.meta.media_service.supabase", mock_sb),
            patch("app.services.http_client.get_http_client", return_value=mock_client),
        ):
            from app.services.meta.media_service import MetaMediaService

            service = MetaMediaService()
            result = await service.upload_media(
                "waba_1", "phone_1", b"image_data", "image/jpeg", "photo.jpg"
            )
            assert result["success"] is True
            assert result["media_id"] == "media_123"

    @pytest.mark.asyncio
    async def test_upload_media_sem_token(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.media_service.supabase", mock_sb):
            from app.services.meta.media_service import MetaMediaService

            service = MetaMediaService()
            result = await service.upload_media("waba_1", "phone_1", b"data", "image/jpeg", "img.jpg")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_upload_media_mime_invalido(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"meta_access_token": "token_abc"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.media_service.supabase", mock_sb):
            from app.services.meta.media_service import MetaMediaService

            service = MetaMediaService()
            result = await service.upload_media("waba_1", "phone_1", b"data", "text/plain", "file.txt")
            assert result["success"] is False
            assert "não suportado" in result["error"]

    def test_detectar_tipo_midia_image(self):
        from app.services.meta.media_service import MetaMediaService

        service = MetaMediaService()
        assert service._detectar_tipo_midia("image/jpeg") == "image"
        assert service._detectar_tipo_midia("image/png") == "image"

    def test_detectar_tipo_midia_video(self):
        from app.services.meta.media_service import MetaMediaService

        service = MetaMediaService()
        assert service._detectar_tipo_midia("video/mp4") == "video"

    def test_detectar_tipo_midia_document(self):
        from app.services.meta.media_service import MetaMediaService

        service = MetaMediaService()
        assert service._detectar_tipo_midia("application/pdf") == "document"
