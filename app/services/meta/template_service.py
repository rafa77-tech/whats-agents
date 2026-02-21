"""
Meta Template Service — CRUD de templates com approval workflow.

Sprint 66 — Gerenciamento de templates Meta via Graph API + banco local.
Access token buscado internamente do banco (tabela chips) via waba_id.
"""

import logging
from typing import Optional, List

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com"


class MetaTemplateService:
    """Serviço de gerenciamento de templates Meta."""

    @property
    def api_version(self) -> str:
        return settings.META_GRAPH_API_VERSION or "v21.0"

    async def _obter_access_token(self, waba_id: str) -> Optional[str]:
        """
        Busca access_token do banco via waba_id.

        Procura em chips com meta_waba_id correspondente.

        Args:
            waba_id: WABA ID

        Returns:
            Access token ou None
        """
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
            logger.error(f"[MetaTemplate] Erro ao buscar access_token: {e}")
            return None

    async def criar_template(
        self,
        waba_id: str,
        name: str,
        category: str,
        language: str,
        components: list,
        variable_mapping: Optional[dict] = None,
        campanha_tipo: Optional[str] = None,
    ) -> dict:
        """
        Cria template na Meta e insere no banco local.

        Args:
            waba_id: WABA ID
            name: Nome do template
            category: MARKETING, UTILITY, ou AUTHENTICATION
            language: Código do idioma (ex: pt_BR)
            components: Lista de componentes do template
            variable_mapping: Mapeamento de variáveis
            campanha_tipo: Tipo de campanha associado

        Returns:
            Dict com resultado da criação
        """
        from app.services.http_client import get_http_client
        from datetime import datetime, timezone

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": f"Access token não encontrado para WABA {waba_id}"}

        # 1. Submeter para Meta via Graph API
        url = f"{_GRAPH_API_BASE}/{self.api_version}/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": name,
            "language": language,
            "category": category,
            "components": components,
        }

        meta_template_id = None
        status = "PENDING"

        try:
            client = await get_http_client()
            response = await client.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            meta_template_id = str(data.get("id", ""))
            status = data.get("status", "PENDING")
            logger.info(f"[MetaTemplate] Template '{name}' submetido: id={meta_template_id}")
        except Exception as e:
            logger.error(f"[MetaTemplate] Erro ao submeter '{name}': {e}")
            status = "SUBMIT_ERROR"

        # 2. Inserir no banco local
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "waba_id": waba_id,
            "template_name": name,
            "language": language,
            "category": category,
            "status": status,
            "components": components,
            "variable_mapping": variable_mapping or {},
            "campanha_tipo": campanha_tipo,
            "meta_template_id": meta_template_id,
            "submitted_at": now,
            "created_at": now,
            "updated_at": now,
        }

        try:
            result = (
                supabase.table("meta_templates")
                .upsert(
                    row,
                    on_conflict="waba_id,template_name,language",
                )
                .execute()
            )
            return {
                "success": True,
                "template": result.data[0] if result.data else row,
                "meta_status": status,
            }
        except Exception as e:
            logger.error(f"[MetaTemplate] Erro ao inserir no banco: {e}")
            return {"success": False, "error": str(e)}

    async def listar_templates(
        self,
        waba_id: str,
        status: Optional[str] = None,
    ) -> List[dict]:
        """
        Lista templates do banco local.

        Args:
            waba_id: WABA ID
            status: Filtrar por status (APPROVED, PENDING, REJECTED)

        Returns:
            Lista de templates
        """
        query = supabase.table("meta_templates").select("*").eq("waba_id", waba_id)
        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()
        return result.data or []

    async def buscar_template(
        self,
        waba_id: str,
        template_name: str,
        language: str = "pt_BR",
    ) -> Optional[dict]:
        """
        Busca template específico.

        Args:
            waba_id: WABA ID
            template_name: Nome do template
            language: Código do idioma

        Returns:
            Template ou None
        """
        result = (
            supabase.table("meta_templates")
            .select("*")
            .eq("waba_id", waba_id)
            .eq("template_name", template_name)
            .eq("language", language)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def buscar_template_por_nome(
        self,
        template_name: str,
    ) -> Optional[dict]:
        """
        Busca template aprovado pelo nome (qualquer WABA).

        Args:
            template_name: Nome do template

        Returns:
            Template APPROVED ou None
        """
        result = (
            supabase.table("meta_templates")
            .select("*")
            .eq("template_name", template_name)
            .eq("status", "APPROVED")
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def atualizar_template(
        self,
        waba_id: str,
        template_name: str,
        components: list,
    ) -> dict:
        """
        Atualiza template (resubmete para aprovação).

        Args:
            waba_id: WABA ID
            template_name: Nome do template
            components: Novos componentes

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client
        from datetime import datetime, timezone

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": f"Access token não encontrado para WABA {waba_id}"}

        # Buscar template local para obter meta_template_id
        template = await self.buscar_template(waba_id, template_name)
        if not template:
            return {"success": False, "error": "Template não encontrado"}

        meta_template_id = template.get("meta_template_id")
        if not meta_template_id:
            return {"success": False, "error": "Template sem ID Meta"}

        # Atualizar via Graph API
        url = f"{_GRAPH_API_BASE}/{self.api_version}/{meta_template_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            client = await get_http_client()
            response = await client.post(
                url,
                headers=headers,
                json={"components": components},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"[MetaTemplate] Erro ao atualizar '{template_name}': {e}")
            return {"success": False, "error": str(e)}

        # Atualizar banco local
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("meta_templates").update(
            {
                "components": components,
                "status": "PENDING",
                "submitted_at": now,
                "updated_at": now,
            }
        ).eq("id", template["id"]).execute()

        return {"success": True}

    async def deletar_template(
        self,
        waba_id: str,
        template_name: str,
    ) -> dict:
        """
        Deleta template na Meta e no banco local.

        Args:
            waba_id: WABA ID
            template_name: Nome do template

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)

        # Deletar na Meta (se tem access_token)
        if access_token:
            url = (
                f"{_GRAPH_API_BASE}/{self.api_version}/{waba_id}"
                f"/message_templates?name={template_name}"
            )
            headers = {"Authorization": f"Bearer {access_token}"}

            try:
                client = await get_http_client()
                response = await client.delete(url, headers=headers, timeout=30)
                response.raise_for_status()
            except Exception as e:
                logger.warning(f"[MetaTemplate] Erro ao deletar na Meta: {e}")
                # Continuar para remover localmente

        # Deletar do banco local
        try:
            supabase.table("meta_templates").delete().eq("waba_id", waba_id).eq(
                "template_name", template_name
            ).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def sincronizar_templates(
        self,
        waba_id: str,
    ) -> dict:
        """
        Sincroniza templates da Meta para o banco local.

        GET all templates from Graph API, upsert locally.

        Args:
            waba_id: WABA ID

        Returns:
            Dict com estatísticas de sync
        """
        from app.services.http_client import get_http_client
        from datetime import datetime, timezone

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": f"Access token não encontrado para WABA {waba_id}"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{waba_id}/message_templates"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"[MetaTemplate] Erro ao sincronizar: {e}")
            return {"success": False, "error": str(e)}

        templates = data.get("data", [])
        now = datetime.now(timezone.utc).isoformat()
        synced = 0

        for t in templates:
            row = {
                "waba_id": waba_id,
                "template_name": t.get("name"),
                "language": t.get("language", "pt_BR"),
                "category": t.get("category", "MARKETING"),
                "status": t.get("status", "PENDING"),
                "components": t.get("components", []),
                "meta_template_id": str(t.get("id", "")),
                "quality_score": t.get("quality_score", {}).get("score"),
                "updated_at": now,
            }
            try:
                supabase.table("meta_templates").upsert(
                    row,
                    on_conflict="waba_id,template_name,language",
                ).execute()
                synced += 1
            except Exception as e:
                logger.warning(f"[MetaTemplate] Erro ao upsert '{t.get('name')}': {e}")

        logger.info(f"[MetaTemplate] Sincronizados {synced}/{len(templates)} templates")
        return {"success": True, "total": len(templates), "synced": synced}


    async def criar_template_com_media(
        self,
        waba_id: str,
        name: str,
        category: str,
        language: str,
        body_text: str,
        body_variables: Optional[List[str]] = None,
        header_format: str = "IMAGE",
        header_media_url: Optional[str] = None,
        buttons: Optional[List[dict]] = None,
    ) -> dict:
        """
        Cria template com header de mídia (imagem/vídeo/documento).

        Args:
            waba_id: WABA ID
            name: Nome do template
            category: MARKETING, UTILITY, AUTHENTICATION
            language: Código do idioma
            body_text: Texto do body
            body_variables: Variáveis do body (ex: ["{{1}}", "{{2}}"])
            header_format: IMAGE, VIDEO ou DOCUMENT
            header_media_url: URL do exemplo de mídia (para aprovação)
            buttons: Botões opcionais

        Returns:
            Dict com resultado da criação
        """
        components = []

        # Header com mídia
        header_component = {
            "type": "HEADER",
            "format": header_format.upper(),
        }
        if header_media_url:
            media_key = header_format.lower()
            header_component["example"] = {
                "header_handle": [header_media_url],
            }
        components.append(header_component)

        # Body
        body_component = {"type": "BODY", "text": body_text}
        if body_variables:
            body_component["example"] = {
                "body_text": [body_variables],
            }
        components.append(body_component)

        # Buttons
        if buttons:
            components.append({"type": "BUTTONS", "buttons": buttons})

        return await self.criar_template(
            waba_id=waba_id,
            name=name,
            category=category,
            language=language,
            components=components,
        )


# Singleton
template_service = MetaTemplateService()
