"""
Testes para API routes Rich Media Templates.

Sprint 68 — Epic 68.3, Chunk 10.
"""

import pytest


class TestMetaRichTemplateRoutes:

    def test_rich_template_endpoint_exists(self):
        """Endpoint /rich existe no router de templates."""
        from app.api.routes.meta_templates import router

        paths = [r.path for r in router.routes]
        assert "/meta/templates/rich" in paths

    def test_create_rich_template_request_model(self):
        """Model de request para rich template."""
        from app.api.routes.meta_templates import CreateRichTemplateRequest

        req = CreateRichTemplateRequest(
            waba_id="w1", name="rich_promo", category="MARKETING",
            body_text="Confira {{1}}", header_format="IMAGE"
        )
        assert req.header_format == "IMAGE"
        assert req.language == "pt_BR"

    def test_otp_send_endpoint_exists(self):
        """Endpoint /otp/send existe."""
        from app.api.routes.meta_templates import router

        paths = [r.path for r in router.routes]
        assert "/meta/templates/otp/send" in paths

    def test_otp_verify_endpoint_exists(self):
        """Endpoint /otp/verify existe."""
        from app.api.routes.meta_templates import router

        paths = [r.path for r in router.routes]
        assert "/meta/templates/otp/verify" in paths
