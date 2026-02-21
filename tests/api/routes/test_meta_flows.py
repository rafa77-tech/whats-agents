"""
Testes para API routes WhatsApp Flows.

Sprint 68 — Epic 68.2, Chunk 7.
"""

import pytest


class TestMetaFlowsRoutes:

    def test_flows_router_has_crud_routes(self):
        """Router tem rotas CRUD."""
        from app.api.routes.meta_flows import router

        paths = [r.path for r in router.routes]
        assert "/meta/flows" in paths  # POST create / GET list
        assert "/meta/flows/{flow_id}" in paths  # GET detail / DELETE
        assert "/meta/flows/{flow_id}/publish" in paths  # POST publish
        assert "/meta/flows/{flow_id}/send" in paths  # POST send

    def test_flows_router_prefix(self):
        """Router usa prefix correto."""
        from app.api.routes.meta_flows import router

        assert router.prefix == "/meta/flows"

    def test_create_flow_request_model(self):
        """Model de request para criação de flow."""
        from app.api.routes.meta_flows import CreateFlowRequest

        req = CreateFlowRequest(waba_id="w1", name="test_flow")
        assert req.flow_type == "FLOW"

    def test_send_flow_request_model(self):
        """Model de request para envio de flow."""
        from app.api.routes.meta_flows import SendFlowRequest

        req = SendFlowRequest(waba_id="w1", phone="5511999", flow_id="f1", flow_token="t1")
        assert req.flow_cta == "Abrir"

    def test_flows_router_tags(self):
        """Router tem tags corretas."""
        from app.api.routes.meta_flows import router

        assert "meta-flows" in router.tags
