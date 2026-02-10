"""
Testes para normalizar_telefone().
"""

import pytest

from app.services.telefone import normalizar_telefone


class TestNormalizarTelefone:
    """Testes de normalizacao de telefone."""

    def test_com_prefixo_mais(self):
        """Remove '+' e mantem digitos."""
        assert normalizar_telefone("+5511942023377") == "5511942023377"

    def test_ja_normalizado(self):
        """Retorna igual se ja esta no formato correto."""
        assert normalizar_telefone("5511942023377") == "5511942023377"

    def test_com_espacos_e_hifen(self):
        """Remove espacos e hifens."""
        assert normalizar_telefone("55 11 94202-3377") == "5511942023377"

    def test_sem_ddi_11_digitos(self):
        """Adiciona DDI 55 para numero com DDD + 9 digitos."""
        assert normalizar_telefone("11942023377") == "5511942023377"

    def test_sem_ddi_10_digitos(self):
        """Adiciona DDI 55 para numero com DDD + 8 digitos (fixo)."""
        assert normalizar_telefone("1134567890") == "551134567890"

    def test_vazio(self):
        """Retorna string vazia para input vazio."""
        assert normalizar_telefone("") == ""

    def test_none_like(self):
        """Retorna string vazia para None-like input."""
        assert normalizar_telefone("") == ""

    def test_com_parenteses(self):
        """Remove parenteses do DDD."""
        assert normalizar_telefone("+55 (11) 94202-3377") == "5511942023377"

    def test_13_digitos_preserva(self):
        """Mantem 13 digitos (DDI+DDD+celular) sem alteracao."""
        assert normalizar_telefone("5511942023377") == "5511942023377"

    def test_12_digitos_preserva(self):
        """Mantem 12 digitos (DDI+DDD+fixo) sem alteracao."""
        assert normalizar_telefone("551134567890") == "551134567890"

    def test_apenas_caracteres_especiais(self):
        """Retorna vazio se nao ha digitos."""
        assert normalizar_telefone("+-() ") == ""

    def test_numero_curto_preserva(self):
        """Numeros curtos (< 10 digitos) sao preservados sem adicionar DDI."""
        assert normalizar_telefone("12345") == "12345"

    def test_numero_com_ddi_diferente(self):
        """Numeros com DDI != 55 mas 13+ digitos sao preservados."""
        assert normalizar_telefone("+5534999724725") == "5534999724725"
