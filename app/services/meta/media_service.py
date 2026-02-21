"""
Meta Media Upload Service.

Sprint 68 — Epic 68.3, Chunk 8.

Upload de mídia (imagem, vídeo, documento) para Meta Cloud API.
Retorna media handle (h:...) para uso em templates com header de mídia.
"""

import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com"

# MIME types suportados por tipo de mídia
SUPPORTED_MIME_TYPES = {
    "image": ["image/jpeg", "image/png"],
    "video": ["video/mp4", "video/3gpp"],
    "document": [
        "application/pdf",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
}


class MetaMediaService:
    """
    Serviço de upload de mídia para Meta Cloud API.

    Usado para criar templates com header de imagem/vídeo/documento.
    """

    @property
    def api_version(self) -> str:
        return settings.META_GRAPH_API_VERSION or "v21.0"

    async def _obter_access_token(self, waba_id: str) -> Optional[str]:
        """Busca access_token do banco via waba_id."""
        try:
            result = (
                supabase.table("chips")
                .select("meta_access_token")
                .eq("meta_waba_id", waba_id)
                .not_.is_("meta_access_token", "null")
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0].get("meta_access_token")
            return None
        except Exception as e:
            logger.error("[MetaMedia] Erro ao buscar access_token: %s", e)
            return None

    async def upload_media(
        self,
        waba_id: str,
        phone_number_id: str,
        file_content: bytes,
        mime_type: str,
        filename: str,
    ) -> dict:
        """
        Upload de arquivo de mídia para Meta.

        Args:
            waba_id: WABA ID
            phone_number_id: Phone Number ID do chip
            file_content: Conteúdo do arquivo em bytes
            mime_type: MIME type (ex: image/jpeg)
            filename: Nome do arquivo

        Returns:
            Dict com media_id (handle) ou error
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": "Access token não encontrado"}

        # Validar MIME type
        media_type = self._detectar_tipo_midia(mime_type)
        if not media_type:
            return {"success": False, "error": f"MIME type não suportado: {mime_type}"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{phone_number_id}/media"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.post(
                url,
                headers=headers,
                files={"file": (filename, file_content, mime_type)},
                data={"messaging_product": "whatsapp", "type": mime_type},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            media_id = data.get("id")

            logger.info("[MetaMedia] Upload bem sucedido: media_id=%s", media_id)
            return {"success": True, "media_id": media_id, "media_type": media_type}

        except Exception as e:
            logger.error("[MetaMedia] Erro no upload: %s", e)
            return {"success": False, "error": "Erro ao fazer upload de mídia"}

    async def obter_media_url(self, media_id: str, waba_id: str) -> Optional[str]:
        """
        Obtém URL temporária de uma mídia.

        Args:
            media_id: ID da mídia
            waba_id: WABA ID (para obter access_token)

        Returns:
            URL da mídia ou None
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return None

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("url")

        except Exception as e:
            logger.error("[MetaMedia] Erro ao obter URL: %s", e)
            return None

    @staticmethod
    def _validar_url_midia(url: str) -> None:
        """
        Valida URL para prevenir SSRF.

        Permite apenas HTTPS e bloqueia IPs privados/reservados.

        Raises:
            ValidationError: Se a URL não for segura.
        """
        parsed = urlparse(url)

        if parsed.scheme != "https":
            raise ValidationError(f"Apenas URLs HTTPS são permitidas, recebido: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("URL sem hostname")

        # Bloquear IPs privados/reservados
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValidationError("URL aponta para endereço interno")
        except ValueError:
            # hostname não é IP literal — verificar padrões conhecidos
            blocked = ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "[::1]")
            if hostname.lower() in blocked:
                raise ValidationError("URL aponta para endereço interno")

    async def upload_media_from_url(
        self,
        waba_id: str,
        phone_number_id: str,
        source_url: str,
        mime_type: str,
    ) -> dict:
        """
        Upload de mídia a partir de uma URL externa.

        Faz download da URL e reuploads para Meta.
        Valida URL contra SSRF antes do download.

        Args:
            waba_id: WABA ID
            phone_number_id: Phone Number ID do chip
            source_url: URL da mídia fonte
            mime_type: MIME type esperado

        Returns:
            Dict com media_id ou error
        """
        from app.services.http_client import get_http_client

        try:
            self._validar_url_midia(source_url)
        except ValidationError as e:
            return {"success": False, "error": str(e)}

        try:
            client = await get_http_client()
            response = await client.get(source_url, timeout=30)
            response.raise_for_status()
            file_content = response.content

            filename = source_url.split("/")[-1].split("?")[0] or "media_file"

            return await self.upload_media(
                waba_id=waba_id,
                phone_number_id=phone_number_id,
                file_content=file_content,
                mime_type=mime_type,
                filename=filename,
            )

        except Exception as e:
            logger.error("[MetaMedia] Erro ao download de mídia: %s", e)
            return {"success": False, "error": "Erro ao fazer download da mídia"}

    def _detectar_tipo_midia(self, mime_type: str) -> Optional[str]:
        """
        Detecta tipo de mídia pelo MIME type.

        Returns:
            'image', 'video', 'document' ou None
        """
        for media_type, mimes in SUPPORTED_MIME_TYPES.items():
            if mime_type in mimes:
                return media_type
        return None


# Singleton
media_service = MetaMediaService()
