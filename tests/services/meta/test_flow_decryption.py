"""
Testes de decriptação de respostas de WhatsApp Flows.

Sprint 70 — Epic 70.4: AES-128-GCM decryption.
"""

import base64
import json
import pytest
from unittest.mock import patch, AsyncMock

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _encrypt_payload(key_hex: str, plaintext_dict: dict) -> str:
    """Helper: criptografa payload para testar decriptação."""
    import os

    key = bytes.fromhex(key_hex)
    iv = os.urandom(12)  # 12 bytes nonce
    aesgcm = AESGCM(key)
    plaintext = json.dumps(plaintext_dict).encode("utf-8")

    # AESGCM.encrypt retorna ciphertext + tag (16 bytes)
    ct_with_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]

    # Formato: IV (12) + ciphertext + tag (16)
    raw = iv + ciphertext + tag
    return base64.b64encode(raw).decode("utf-8")


# Chave fixa para testes (16 bytes = AES-128)
_TEST_KEY_HEX = "00112233445566778899aabbccddeeff"


class TestFlowDecryption:
    """Testa decriptar_resposta_flow."""

    @pytest.mark.asyncio
    async def test_payload_conhecido_decripta(self):
        """Payload criptografado com chave conhecida é decriptado."""
        original = {"screen": "CONFIRMATION", "data": {"accepted": True}}
        encrypted = _encrypt_payload(_TEST_KEY_HEX, original)

        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", _TEST_KEY_HEX):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(
                {"encrypted_flow_data": encrypted}
            )

            assert result is not None
            assert result["screen"] == "CONFIRMATION"
            assert result["data"]["accepted"] is True

    @pytest.mark.asyncio
    async def test_chave_ausente_retorna_raw(self):
        """Sem FLOW_PRIVATE_KEY, retorna dados raw (sem decriptar)."""
        raw_data = {"encrypted_flow_data": "abc123", "extra": "info"}

        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", ""):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(raw_data)

            assert result == raw_data

    @pytest.mark.asyncio
    async def test_sem_encrypted_flow_data_retorna_input(self):
        """Sem campo encrypted_flow_data, retorna input inalterado."""
        input_data = {"some_field": "value"}

        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", _TEST_KEY_HEX):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(input_data)

            assert result == input_data

    @pytest.mark.asyncio
    async def test_dados_invalidos_retorna_none(self):
        """Dados inválidos (base64 corrompido) retorna None."""
        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", _TEST_KEY_HEX):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(
                {"encrypted_flow_data": "not_valid_base64!!!"}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_chave_errada_retorna_none(self):
        """Chave errada não decripta — retorna None."""
        original = {"screen": "TEST"}
        encrypted = _encrypt_payload(_TEST_KEY_HEX, original)

        wrong_key = "ffeeddccbbaa99887766554433221100"

        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", wrong_key):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(
                {"encrypted_flow_data": encrypted}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_payload_grande_decripta(self):
        """Payload maior (formulário completo) decripta corretamente."""
        original = {
            "screen": "DOCTOR_FORM",
            "data": {
                "nome": "Dr. Carlos Silva",
                "crm": "123456-SP",
                "especialidade": "Cardiologia",
                "disponibilidade": ["seg", "qua", "sex"],
                "valor_minimo": 2500.00,
            },
        }
        encrypted = _encrypt_payload(_TEST_KEY_HEX, original)

        with patch("app.core.config.settings.META_FLOW_PRIVATE_KEY", _TEST_KEY_HEX):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.decriptar_resposta_flow(
                {"encrypted_flow_data": encrypted}
            )

            assert result is not None
            assert result["data"]["crm"] == "123456-SP"
            assert len(result["data"]["disponibilidade"]) == 3
