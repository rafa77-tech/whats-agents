"""
Testes para API routes Meta Catalog.

Sprint 68 — Epic 68.4, Chunk 12.
"""

import pytest


class TestMetaCatalogRoutes:

    def test_catalog_router_has_routes(self):
        """Router tem rotas de catálogo."""
        from app.api.routes.meta_catalog import router

        paths = [r.path for r in router.routes]
        assert "/meta/catalog/sync" in paths
        assert "/meta/catalog/products" in paths
        assert "/meta/catalog/send-product" in paths
        assert "/meta/catalog/send-product-list" in paths

    def test_catalog_router_prefix(self):
        """Router usa prefix correto."""
        from app.api.routes.meta_catalog import router

        assert router.prefix == "/meta/catalog"

    def test_sync_catalog_request_model(self):
        """Model de request para sync."""
        from app.api.routes.meta_catalog import SyncCatalogRequest

        req = SyncCatalogRequest(waba_id="w1", catalog_id="cat_1")
        assert req.catalog_id == "cat_1"

    def test_send_product_request_model(self):
        """Model de request para envio de produto."""
        from app.api.routes.meta_catalog import SendProductRequest

        req = SendProductRequest(waba_id="w1", phone="5511999", catalog_id="c1", product_retailer_id="vaga_1")
        assert req.body_text == ""

    def test_catalog_job_endpoint_exists(self):
        """Endpoint do job de sync existe."""
        from app.api.routes.jobs.meta_catalog import router

        paths = [r.path for r in router.routes]
        assert "/meta-catalog-sync" in paths
