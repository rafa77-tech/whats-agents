"""
Testes E2E: Discovery nunca deve ofertar vagas.

Sprint 32 - Cenário: Campanha de Discovery
Comportamento esperado: Julia NUNCA menciona vagas.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestDiscoveryNaoOferta:
    """Testes para garantir que discovery não oferta."""

    def test_campanha_discovery_tem_pode_ofertar_false(self, campanha_discovery_data):
        """Campanha discovery deve ter pode_ofertar=False."""
        assert campanha_discovery_data["pode_ofertar"] is False

    def test_campanha_discovery_tem_regra_nao_mencionar_vagas(self, campanha_discovery_data):
        """Campanha discovery deve ter regra de não mencionar vagas."""
        regras = campanha_discovery_data["regras"]
        regras_lower = [r.lower() for r in regras]

        tem_regra_vaga = any("vaga" in r for r in regras_lower)
        tem_regra_nunca = any("nunca" in r for r in regras_lower)

        assert tem_regra_vaga, "Deve ter regra sobre vagas"
        assert tem_regra_nunca, "Deve ter regra com 'nunca'"

    def test_campanha_discovery_objetivo_foca_em_conhecer(self, campanha_discovery_data):
        """Objetivo de discovery deve focar em conhecer médicos."""
        objetivo = campanha_discovery_data["objetivo"].lower()

        assert "conhecer" in objetivo or "preferência" in objetivo

    def test_regras_discovery_nao_fala_valores(self, campanha_discovery_data):
        """Regras devem proibir falar de valores."""
        regras = campanha_discovery_data["regras"]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "valor" in regras_texto, "Deve mencionar restrição sobre valores"


class TestDiscoveryComportamento:
    """Testes de comportamento discovery."""

    def test_tipo_discovery_inferido_corretamente(self):
        """Verifica que inferir_tipo retorna DISCOVERY para campanhas certas."""
        from scripts.migrar_campanhas_v2 import inferir_tipo, TipoCampanha

        campanha = {
            "nome_template": "prospecção_cardiologistas",
            "corpo": "",
            "tipo_campanha": ""
        }

        tipo = inferir_tipo(campanha)
        assert tipo == TipoCampanha.DISCOVERY

    def test_discovery_nao_tem_keyword_oferta(self):
        """Discovery não deve ter keywords de oferta."""
        from scripts.migrar_campanhas_v2 import KEYWORDS_TIPO, TipoCampanha

        keywords_discovery = KEYWORDS_TIPO[TipoCampanha.DISCOVERY]
        keywords_oferta = KEYWORDS_TIPO[TipoCampanha.OFERTA]

        # Não deve haver overlap
        overlap = set(keywords_discovery) & set(keywords_oferta)
        assert len(overlap) == 0, f"Keywords não devem ter overlap: {overlap}"


class TestDiscoveryRegras:
    """Testes das regras padrão de discovery."""

    def test_regras_discovery_existem(self):
        """Regras padrão de discovery devem existir."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        assert TipoCampanha.DISCOVERY in REGRAS_PADRAO
        assert len(REGRAS_PADRAO[TipoCampanha.DISCOVERY]) > 0

    def test_regras_discovery_tem_restricao_vagas(self):
        """Regras de discovery devem ter restrição sobre vagas."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        regras = REGRAS_PADRAO[TipoCampanha.DISCOVERY]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "vaga" in regras_texto
        assert "nunca" in regras_texto or "não" in regras_texto

    def test_regras_discovery_foca_conhecer_medico(self):
        """Regras de discovery devem focar em conhecer o médico."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        regras = REGRAS_PADRAO[TipoCampanha.DISCOVERY]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "conhecer" in regras_texto or "preferência" in regras_texto
