"""
Testes para validação de payloads interativos do WhatsApp.

Sprint 67 (R3, Chunk 2) — 8 testes.
"""

import pytest
from app.tools.interactive_validation import (
    validar_payload_interactive,
    sanitizar_payload_interactive,
)


class TestValidarButtons:
    """Testes de validação de botões."""

    def test_buttons_valido(self):
        payload = {
            "buttons": [
                {"title": "Sim"},
                {"title": "Não"},
                {"title": "Talvez"},
            ]
        }
        valido, erro = validar_payload_interactive("buttons", payload)
        assert valido is True
        assert erro == ""

    def test_buttons_excede_limite_3(self):
        payload = {
            "buttons": [
                {"title": "A"},
                {"title": "B"},
                {"title": "C"},
                {"title": "D"},
            ]
        }
        valido, erro = validar_payload_interactive("buttons", payload)
        assert valido is False
        assert "Máximo de 3" in erro

    def test_buttons_titulo_excede_20_chars(self):
        payload = {
            "buttons": [
                {"title": "A" * 21},
            ]
        }
        valido, erro = validar_payload_interactive("buttons", payload)
        assert valido is False
        assert "excede 20" in erro


class TestValidarList:
    """Testes de validação de listas."""

    def test_list_valido(self):
        payload = {
            "button": "Ver opções",
            "sections": [
                {
                    "title": "Vagas",
                    "rows": [
                        {"title": "Vaga 1", "description": "Hospital ABC"},
                        {"title": "Vaga 2", "description": "Hospital XYZ"},
                    ],
                }
            ],
        }
        valido, erro = validar_payload_interactive("list", payload)
        assert valido is True
        assert erro == ""

    def test_list_excede_10_itens(self):
        rows = [{"title": f"Item {i}"} for i in range(11)]
        payload = {"sections": [{"rows": rows}]}
        valido, erro = validar_payload_interactive("list", payload)
        assert valido is False
        assert "excede 10" in erro


class TestValidarCtaUrl:
    """Testes de validação de CTA URL."""

    def test_cta_url_valido(self):
        payload = {
            "url": "https://revoluna.com/vaga/123",
            "display_text": "Ver vaga",
        }
        valido, erro = validar_payload_interactive("cta_url", payload)
        assert valido is True

    def test_cta_url_http_rejeitado(self):
        payload = {"url": "http://insecure.com"}
        valido, erro = validar_payload_interactive("cta_url", payload)
        assert valido is False
        assert "HTTPS" in erro


class TestSanitizar:
    """Testes de sanitização de payloads."""

    def test_sanitizar_trunca_titulo_botao(self):
        payload = {
            "buttons": [
                {"title": "Título muito longo demais"},
            ]
        }
        result = sanitizar_payload_interactive("buttons", payload)
        assert len(result["buttons"][0]["title"]) <= 20
        assert result["buttons"][0]["title"].endswith("…")

    def test_sanitizar_remove_botoes_excedentes(self):
        payload = {
            "buttons": [
                {"title": "A"},
                {"title": "B"},
                {"title": "C"},
                {"title": "D"},
            ]
        }
        result = sanitizar_payload_interactive("buttons", payload)
        assert len(result["buttons"]) == 3
