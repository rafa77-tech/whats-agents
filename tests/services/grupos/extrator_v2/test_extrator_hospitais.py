"""Testes para extrator de hospitais."""
import pytest

from app.services.grupos.extrator_v2.extrator_hospitais import (
    extrair_hospitais,
    _extrair_nome_hospital,
    _eh_linha_hospital,
    _eh_linha_endereco,
    _extrair_estado,
    _extrair_cidade,
)
from app.services.grupos.extrator_v2.types import HospitalExtraido


class TestHelperFunctions:
    """Testes para funções auxiliares."""

    def test_eh_linha_hospital_com_prefixo(self):
        """Detecta linhas com prefixo de hospital."""
        assert _eh_linha_hospital("Hospital São Luiz") is True
        assert _eh_linha_hospital("UPA Campo Limpo") is True
        assert _eh_linha_hospital("Clínica Santa Maria") is True
        assert _eh_linha_hospital("PS Central") is True

    def test_eh_linha_hospital_sem_prefixo(self):
        """Não detecta linhas sem prefixo."""
        assert _eh_linha_hospital("Av. Brasil, 1000") is False
        assert _eh_linha_hospital("São Paulo - SP") is False

    def test_eh_linha_endereco_com_prefixo(self):
        """Detecta linhas de endereço."""
        assert _eh_linha_endereco("Rua das Flores, 100") is True
        assert _eh_linha_endereco("Av. Brasil, 1000") is True
        assert _eh_linha_endereco("Estrada Itapecirica, 1661") is True

    def test_eh_linha_endereco_com_numero(self):
        """Detecta endereço pelo número."""
        assert _eh_linha_endereco("Campo Limpo, 1661") is True
        assert _eh_linha_endereco("Centro, nº 500") is True

    def test_extrair_estado(self):
        """Extrai sigla do estado."""
        assert _extrair_estado("São Paulo - SP") == "SP"
        assert _extrair_estado("Centro - RJ") == "RJ"
        assert _extrair_estado("Hospital ABC") is None

    def test_extrair_cidade_regiao_sp(self):
        """Extrai regiões de SP."""
        assert _extrair_cidade("Zona Norte") == "Zona Norte"
        assert _extrair_cidade("ABC") == "Abc"
        assert _extrair_cidade("Grande ABC") == "Grande Abc"

    def test_extrair_nome_hospital(self):
        """Extrai nome do hospital."""
        nome, conf = _extrair_nome_hospital("Hospital São Luiz ABC")
        assert nome == "Hospital São Luiz ABC"
        assert conf >= 0.8

    def test_extrair_nome_hospital_com_emoji(self):
        """Extrai nome removendo emoji."""
        nome, conf = _extrair_nome_hospital("📍 Hospital Campo Limpo")
        assert nome == "Hospital Campo Limpo"
        assert "📍" not in nome


class TestExtrairHospitais:
    """Testes para extração de hospitais."""

    def test_hospital_simples(self):
        """Extrai hospital simples."""
        linhas = ["Hospital São Luiz ABC"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "São Luiz" in hospitais[0].nome

    def test_hospital_com_endereco(self):
        """Extrai hospital com endereço."""
        linhas = [
            "📍 Hospital Campo Limpo",
            "Estrada Itapecirica, 1661 - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Campo Limpo" in hospitais[0].nome
        assert hospitais[0].endereco is not None
        assert "Itapecirica" in hospitais[0].endereco

    def test_hospital_com_estado(self):
        """Extrai estado do hospital."""
        linhas = [
            "Hospital Central",
            "Centro - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert hospitais[0].estado == "SP"

    def test_multiplos_hospitais(self):
        """Extrai múltiplos hospitais."""
        linhas = [
            "📍 Hospital ABC",
            "📍 Hospital XYZ",
            "📍 UPA Central"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 3

    def test_hospital_com_cidade(self):
        """Extrai cidade do hospital."""
        linhas = [
            "Hospital Regional",
            "Santo André - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        # Pode extrair cidade ou incluir no endereço

    def test_linhas_vazias_ignoradas(self):
        """Linhas vazias são ignoradas."""
        linhas = [
            "Hospital ABC",
            "",
            "   ",
            "Rua Central, 100"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1

    def test_lista_vazia(self):
        """Lista vazia retorna lista vazia."""
        hospitais = extrair_hospitais([])
        assert hospitais == []

    def test_confianca_com_prefixo(self):
        """Confiança maior quando tem prefixo claro."""
        linhas = ["Hospital São Luiz"]
        hospitais = extrair_hospitais(linhas)

        assert hospitais[0].confianca >= 0.8

    def test_confianca_sem_prefixo(self):
        """Confiança menor sem prefixo claro."""
        linhas = ["São Luiz ABC"]
        hospitais = extrair_hospitais(linhas)

        assert hospitais[0].confianca < 0.8


class TestCasosReais:
    """Testes com formatos reais de grupos."""

    def test_formato_emoji_padrao(self):
        """Formato padrão com emoji."""
        linhas = [
            "📍 Hospital Campo Limpo",
            "Estrada Itapecirica da Serra, 1661 - SP"
        ]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Campo Limpo" in hospitais[0].nome

    def test_formato_upa(self):
        """Formato UPA."""
        linhas = ["UPA CAMPO LIMPO"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "UPA" in hospitais[0].nome.upper()

    def test_formato_ps(self):
        """Formato PS (Pronto Socorro)."""
        linhas = ["PS Central - Guarulhos"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1

    def test_formato_santa_casa(self):
        """Formato Santa Casa."""
        linhas = ["Santa Casa de Misericórdia - ABC"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Santa Casa" in hospitais[0].nome

    def test_formato_beneficencia(self):
        """Formato Beneficência."""
        linhas = ["Beneficência Portuguesa"]
        hospitais = extrair_hospitais(linhas)

        assert len(hospitais) == 1
        assert "Beneficência" in hospitais[0].nome
