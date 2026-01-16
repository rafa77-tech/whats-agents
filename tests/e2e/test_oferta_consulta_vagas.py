"""
Testes E2E: Oferta deve consultar vagas antes de mencionar.

Sprint 32 - Cenário: Campanha de Oferta
Comportamento esperado: Julia SEMPRE consulta vagas antes de ofertar.
"""
import pytest
from unittest.mock import patch, AsyncMock


class TestOfertaConsultaVagas:
    """Testes para garantir que oferta consulta vagas."""

    def test_campanha_oferta_tem_pode_ofertar_true(self, campanha_oferta_data):
        """Campanha oferta deve ter pode_ofertar=True."""
        assert campanha_oferta_data["pode_ofertar"] is True

    def test_campanha_oferta_tem_regra_consultar(self, campanha_oferta_data):
        """Campanha oferta deve ter regra de consultar sistema."""
        regras = campanha_oferta_data["regras"]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "consultar" in regras_texto, "Deve ter regra de consultar sistema"

    def test_campanha_oferta_proibe_inventar(self, campanha_oferta_data):
        """Campanha oferta deve proibir inventar vagas."""
        regras = campanha_oferta_data["regras"]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "inventar" in regras_texto or "nunca" in regras_texto


class TestOfertaTipoInferencia:
    """Testes de inferência de tipo oferta."""

    def test_tipo_oferta_inferido_por_vaga(self):
        """Infere OFERTA quando tem 'vaga' no nome."""
        from scripts.migrar_campanhas_v2 import inferir_tipo, TipoCampanha

        campanha = {
            "nome_template": "vaga_cardio_mooca",
            "corpo": "",
            "tipo_campanha": ""
        }

        tipo = inferir_tipo(campanha)
        assert tipo == TipoCampanha.OFERTA

    def test_tipo_oferta_inferido_por_plantao(self):
        """Infere OFERTA quando tem 'plantão' no corpo."""
        from scripts.migrar_campanhas_v2 import inferir_tipo, TipoCampanha

        campanha = {
            "nome_template": "",
            "corpo": "Tenho um plantão disponível",
            "tipo_campanha": ""
        }

        tipo = inferir_tipo(campanha)
        assert tipo == TipoCampanha.OFERTA

    def test_tipo_oferta_inferido_por_tipo_campanha(self):
        """Infere OFERTA quando tipo_campanha contém 'oferta'."""
        from scripts.migrar_campanhas_v2 import inferir_tipo, TipoCampanha

        campanha = {
            "nome_template": "",
            "corpo": "",
            "tipo_campanha": "oferta_plantao"
        }

        tipo = inferir_tipo(campanha)
        assert tipo == TipoCampanha.OFERTA


class TestOfertaRegras:
    """Testes das regras padrão de oferta."""

    def test_regras_oferta_existem(self):
        """Regras padrão de oferta devem existir."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        assert TipoCampanha.OFERTA in REGRAS_PADRAO
        assert len(REGRAS_PADRAO[TipoCampanha.OFERTA]) > 0

    def test_regras_oferta_tem_consultar_sistema(self):
        """Regras de oferta devem ter consulta ao sistema."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        regras = REGRAS_PADRAO[TipoCampanha.OFERTA]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "consultar" in regras_texto

    def test_regras_oferta_proibe_inventar(self):
        """Regras de oferta devem proibir inventar vagas."""
        from scripts.migrar_campanhas_v2 import REGRAS_PADRAO, TipoCampanha

        regras = REGRAS_PADRAO[TipoCampanha.OFERTA]
        regras_texto = " ".join(r.lower() for r in regras)

        assert "inventar" in regras_texto or "nunca" in regras_texto


class TestOfertaComVaga:
    """Testes de oferta com vaga disponível."""

    def test_vaga_data_tem_campos_necessarios(self, vaga_data, hospital_data):
        """Vaga deve ter todos os campos necessários."""
        assert "id" in vaga_data
        assert "hospital_id" in vaga_data
        assert "data" in vaga_data
        assert "valor" in vaga_data
        assert "status" in vaga_data

        # Hospital ID deve bater
        assert vaga_data["hospital_id"] == hospital_data["id"]

    def test_vaga_valor_e_numerico(self, vaga_data):
        """Valor da vaga deve ser numérico."""
        assert isinstance(vaga_data["valor"], (int, float))
        assert vaga_data["valor"] > 0
