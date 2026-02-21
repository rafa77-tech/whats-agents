"""
Testes para OtpTemplateBuilder.

Sprint 69 — Epic 69.1, Chunk 13.
"""

import pytest


class TestOtpTemplateBuilder:

    def test_build_one_tap_components(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        components = builder.build_one_tap_components("com.revoluna.app", "abc123hash")
        assert len(components) == 3
        assert components[2]["otp_type"] == "ONE_TAP"
        assert components[2]["package_name"] == "com.revoluna.app"

    def test_build_zero_tap_components(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        components = builder.build_zero_tap_components("com.revoluna.app", "abc123", 5)
        assert components[2]["otp_type"] == "ZERO_TAP"
        assert components[2]["code_expiration_minutes"] == 5

    def test_build_copy_code_components(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        components = builder.build_copy_code_components()
        assert len(components) == 3
        assert components[2]["otp_type"] == "COPY_CODE"

    def test_build_template_creation_payload_copy_code(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        payload = builder.build_template_creation_payload("otp_confirm")
        assert payload["category"] == "AUTHENTICATION"
        assert payload["name"] == "otp_confirm"
        assert len(payload["components"]) == 3

    def test_build_template_creation_payload_one_tap(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        payload = builder.build_template_creation_payload(
            "otp_one_tap", otp_type="ONE_TAP",
            package_name="com.app", signature_hash="hash123"
        )
        buttons = payload["components"][-1]["buttons"]
        assert buttons[0]["otp_type"] == "ONE_TAP"
        assert buttons[0]["package_name"] == "com.app"

    def test_build_template_creation_payload_zero_tap(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        payload = builder.build_template_creation_payload(
            "otp_zero", otp_type="ZERO_TAP",
            package_name="com.app", signature_hash="hash456",
            code_expiration_minutes=5
        )
        buttons = payload["components"][-1]["buttons"]
        assert buttons[0]["otp_type"] == "ZERO_TAP"
        assert buttons[0]["code_expiration_minutes"] == 5

    def test_build_template_payload_has_body_example(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        payload = builder.build_template_creation_payload("otp_test")
        body = payload["components"][0]
        assert body["type"] == "BODY"
        assert "example" in body
        assert "123456" in body["example"]["body_text"][0]

    def test_build_template_payload_has_footer(self):
        from app.services.meta.otp_template_builder import OtpTemplateBuilder

        builder = OtpTemplateBuilder()
        payload = builder.build_template_creation_payload("otp_test")
        footer = payload["components"][1]
        assert footer["type"] == "FOOTER"
