"""
Testes para o script de migração de campanhas.
"""
import pytest
from scripts.migrar_campanhas_v2 import (
    TipoCampanha,
    KEYWORDS_TIPO,
    REGRAS_PADRAO,
    inferir_tipo,
    gerar_objetivo,
)


class TestInferirTipo:
    """Testes para inferência de tipo de campanha."""

    def test_infere_oferta_por_palavra_vaga(self):
        """Deve inferir OFERTA quando tem 'vaga' no nome."""
        campanha = {"nome_template": "vaga_cardio_mooca", "corpo": "", "tipo_campanha": ""}
        assert inferir_tipo(campanha) == TipoCampanha.OFERTA

    def test_infere_oferta_por_plantao(self):
        """Deve inferir OFERTA quando tem 'plantao' no corpo."""
        campanha = {
            "nome_template": "",
            "corpo": "Tenho um plantão disponível",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.OFERTA

    def test_infere_oferta_por_tipo_campanha(self):
        """Deve inferir OFERTA quando tipo_campanha contém 'oferta'."""
        campanha = {
            "nome_template": "",
            "corpo": "",
            "tipo_campanha": "oferta_plantao"
        }
        assert inferir_tipo(campanha) == TipoCampanha.OFERTA

    def test_infere_discovery_por_prospeccao(self):
        """Deve inferir DISCOVERY quando tem 'prospecção'."""
        campanha = {
            "nome_template": "prospecção_cardiologistas",
            "corpo": "",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.DISCOVERY

    def test_infere_discovery_por_conhecer(self):
        """Deve inferir DISCOVERY quando tem 'conhecer'."""
        campanha = {
            "nome_template": "",
            "corpo": "Quero conhecer você melhor",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.DISCOVERY

    def test_infere_followup(self):
        """Deve inferir FOLLOWUP quando tem 'follow'."""
        campanha = {
            "nome_template": "followup_semana_2",
            "corpo": "",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.FOLLOWUP

    def test_infere_feedback(self):
        """Deve inferir FEEDBACK quando tem 'feedback'."""
        campanha = {
            "nome_template": "",
            "corpo": "Como foi o plantão? Quero seu feedback",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.FEEDBACK

    def test_infere_reativacao(self):
        """Deve inferir REATIVACAO quando tem 'reativar'."""
        campanha = {
            "nome_template": "reativacao_inativos",
            "corpo": "",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.REATIVACAO

    def test_padrao_discovery_quando_sem_match(self):
        """Deve retornar DISCOVERY quando não encontra matches."""
        campanha = {
            "nome_template": "campanha_xyz",
            "corpo": "mensagem genérica",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.DISCOVERY

    def test_maior_score_ganha(self):
        """Deve retornar tipo com maior número de matches."""
        # Tem 'vaga' (oferta) e 'primeiro' (discovery), mas 'vaga plantão' = 2 matches
        campanha = {
            "nome_template": "vaga_primeiro_contato",
            "corpo": "plantão disponível",
            "tipo_campanha": ""
        }
        assert inferir_tipo(campanha) == TipoCampanha.OFERTA


class TestGerarObjetivo:
    """Testes para geração de objetivo."""

    def test_objetivo_discovery(self):
        """Deve gerar objetivo para DISCOVERY."""
        campanha = {"nome_template": "campanha_test"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.DISCOVERY)
        assert "Conhecer médicos" in objetivo

    def test_objetivo_oferta(self):
        """Deve gerar objetivo para OFERTA."""
        campanha = {"nome_template": "campanha_test"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.OFERTA)
        assert "Ofertar vagas" in objetivo

    def test_objetivo_followup(self):
        """Deve gerar objetivo para FOLLOWUP."""
        campanha = {"nome_template": "campanha_test"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.FOLLOWUP)
        assert "relacionamento" in objetivo

    def test_objetivo_feedback(self):
        """Deve gerar objetivo para FEEDBACK."""
        campanha = {"nome_template": "campanha_test"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.FEEDBACK)
        assert "feedback" in objetivo

    def test_objetivo_reativacao(self):
        """Deve gerar objetivo para REATIVACAO."""
        campanha = {"nome_template": "campanha_test"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.REATIVACAO)
        assert "Retomar contato" in objetivo

    def test_objetivo_adiciona_especialidade_cardio(self):
        """Deve adicionar 'cardiologia' se nome contém 'cardio'."""
        campanha = {"nome_template": "vaga_cardio_mooca"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.OFERTA)
        assert "cardiologia" in objetivo

    def test_objetivo_adiciona_especialidade_anestesia(self):
        """Deve adicionar 'anestesiologia' se nome contém 'anestesi'."""
        campanha = {"nome_template": "oferta_anestesistas"}
        objetivo = gerar_objetivo(campanha, TipoCampanha.OFERTA)
        assert "anestesiologia" in objetivo


class TestRegrasPadrao:
    """Testes para regras padrão por tipo."""

    def test_discovery_tem_regra_nao_mencionar_vagas(self):
        """DISCOVERY deve ter regra de não mencionar vagas."""
        regras = REGRAS_PADRAO[TipoCampanha.DISCOVERY]
        assert any("vaga" in r.lower() for r in regras)
        assert any("nunca" in r.lower() for r in regras)

    def test_oferta_tem_regra_consultar_sistema(self):
        """OFERTA deve ter regra de consultar sistema."""
        regras = REGRAS_PADRAO[TipoCampanha.OFERTA]
        assert any("consultar" in r.lower() for r in regras)

    def test_followup_tem_regra_conversa_leve(self):
        """FOLLOWUP deve ter regra de conversa leve."""
        regras = REGRAS_PADRAO[TipoCampanha.FOLLOWUP]
        assert any("leve" in r.lower() for r in regras)

    def test_feedback_tem_regra_perguntar_plantao(self):
        """FEEDBACK deve ter regra de perguntar sobre plantão."""
        regras = REGRAS_PADRAO[TipoCampanha.FEEDBACK]
        assert any("plantão" in r.lower() for r in regras)

    def test_reativacao_tem_regra_nao_ofertar(self):
        """REATIVACAO deve ter regra de não ofertar imediatamente."""
        regras = REGRAS_PADRAO[TipoCampanha.REATIVACAO]
        assert any("ofertar" in r.lower() for r in regras)


class TestKeywords:
    """Testes para keywords de detecção."""

    def test_todos_tipos_tem_keywords(self):
        """Todos os tipos devem ter keywords definidas."""
        for tipo in TipoCampanha:
            assert tipo in KEYWORDS_TIPO
            assert len(KEYWORDS_TIPO[tipo]) > 0

    def test_keywords_sao_lowercase(self):
        """Todas as keywords devem estar em lowercase."""
        for tipo, keywords in KEYWORDS_TIPO.items():
            for kw in keywords:
                assert kw == kw.lower(), f"Keyword '{kw}' deveria ser lowercase"
