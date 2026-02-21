"""
OTP Template Builder — Authentication templates for Meta.

Sprint 69 — Epic 69.1, Chunk 13.

Builds Meta AUTHENTICATION template components for:
- One-tap (Android): Auto-fill OTP
- Zero-tap (Android): Auto-verify, no user action
- Copy code: Universal fallback
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OtpTemplateBuilder:
    """
    Construtor de templates AUTHENTICATION para OTP.

    Meta suporta 3 tipos de templates de autenticação:
    - One-tap: Auto-preenchimento no Android
    - Zero-tap: Verificação automática no Android
    - Copy code: Cópia manual (universal)
    """

    def build_one_tap_components(
        self,
        package_name: str,
        signature_hash: str,
    ) -> list:
        """
        Constrói componentes para template one-tap (Android auto-fill).

        Args:
            package_name: Package name do app Android
            signature_hash: Hash de assinatura do app

        Returns:
            Lista de componentes Meta
        """
        return [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "otp",
                "otp_type": "ONE_TAP",
                "package_name": package_name,
                "signature_hash": signature_hash,
            },
        ]

    def build_zero_tap_components(
        self,
        package_name: str,
        signature_hash: str,
        code_expiration_minutes: int = 10,
    ) -> list:
        """
        Constrói componentes para template zero-tap (auto-verify).

        Args:
            package_name: Package name do app Android
            signature_hash: Hash de assinatura do app
            code_expiration_minutes: Minutos até expiração do código

        Returns:
            Lista de componentes Meta
        """
        return [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "otp",
                "otp_type": "ZERO_TAP",
                "package_name": package_name,
                "signature_hash": signature_hash,
                "code_expiration_minutes": code_expiration_minutes,
            },
        ]

    def build_copy_code_components(self) -> list:
        """
        Constrói componentes para template copy-code (universal).

        Returns:
            Lista de componentes Meta
        """
        return [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": "{{1}}"}],
            },
            {
                "type": "otp",
                "otp_type": "COPY_CODE",
            },
        ]

    def build_template_creation_payload(
        self,
        name: str,
        language: str = "pt_BR",
        otp_type: str = "COPY_CODE",
        code_expiration_minutes: int = 10,
        package_name: Optional[str] = None,
        signature_hash: Optional[str] = None,
    ) -> dict:
        """
        Constrói payload completo para criação de template AUTHENTICATION.

        Args:
            name: Nome do template
            language: Código do idioma
            otp_type: ONE_TAP, ZERO_TAP ou COPY_CODE
            code_expiration_minutes: Minutos até expiração
            package_name: Package name (necessário para ONE_TAP/ZERO_TAP)
            signature_hash: Hash de assinatura (necessário para ONE_TAP/ZERO_TAP)

        Returns:
            Dict com payload completo para Graph API
        """
        components = [
            {
                "type": "BODY",
                "text": "Seu código de verificação é {{1}}. Válido por {0} minutos.".format(
                    code_expiration_minutes
                ),
                "example": {"body_text": [["123456"]]},
            },
            {
                "type": "FOOTER",
                "text": "Este código expira em breve.",
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "OTP",
                        "otp_type": otp_type,
                    }
                ],
            },
        ]

        if otp_type in ("ONE_TAP", "ZERO_TAP") and package_name and signature_hash:
            components[-1]["buttons"][0]["package_name"] = package_name
            components[-1]["buttons"][0]["signature_hash"] = signature_hash

        if otp_type == "ZERO_TAP":
            components[-1]["buttons"][0]["code_expiration_minutes"] = code_expiration_minutes

        return {
            "name": name,
            "language": language,
            "category": "AUTHENTICATION",
            "components": components,
        }


# Singleton
otp_template_builder = OtpTemplateBuilder()
