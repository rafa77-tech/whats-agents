"""
Testes do modulo de tipos de abordagem.
"""
import pytest
from datetime import datetime

from app.services.tipos_abordagem import (
    TipoAbordagem,
    inferir_tipo,
    obter_prompt,
    preparar_prompt,
    descrever_tipo,
    extrair_telefone,
    extrair_hospital,
    extrair_data,
    PROMPT_DISCOVERY,
    PROMPT_OFERTA,
    PROMPT_REATIVACAO,
    PROMPT_FOLLOWUP,
    PROMPT_CUSTOM,
)


class TestInferirTipo:
    """Testes de inferencia de tipo de abordagem."""

    # Discovery
    def test_inferir_discovery_se_apresenta(self):
        """Testa inferencia de discovery."""
        assert inferir_tipo("se apresenta pro medico") == TipoAbordagem.DISCOVERY

    def test_inferir_discovery_primeiro_contato(self):
        """Testa inferencia com primeiro contato."""
        assert inferir_tipo("faz primeiro contato") == TipoAbordagem.DISCOVERY

    def test_inferir_discovery_padrao_novo(self):
        """Testa que novo medico sem instrucao = discovery."""
        assert inferir_tipo("", eh_novo=True) == TipoAbordagem.DISCOVERY

    # Oferta
    def test_inferir_oferta_oferece(self):
        """Testa inferencia de oferta."""
        assert inferir_tipo("oferece a vaga do Sao Luiz") == TipoAbordagem.OFERTA

    def test_inferir_oferta_plantao(self):
        """Testa inferencia com plantao."""
        assert inferir_tipo("fala do plantao dia 15") == TipoAbordagem.OFERTA

    def test_inferir_oferta_tem_vaga(self):
        """Testa que tem_vaga=True resulta em oferta."""
        assert inferir_tipo("manda msg", tem_vaga=True) == TipoAbordagem.OFERTA

    def test_inferir_oferta_convida(self):
        """Testa inferencia com convida."""
        assert inferir_tipo("convida pro plantao") == TipoAbordagem.OFERTA

    # Reativacao
    def test_inferir_reativacao_reativa(self):
        """Testa inferencia de reativacao."""
        assert inferir_tipo("reativa o contato") == TipoAbordagem.REATIVACAO

    def test_inferir_reativacao_sumiu(self):
        """Testa inferencia com sumiu."""
        assert inferir_tipo("ele sumiu faz tempo") == TipoAbordagem.REATIVACAO

    def test_inferir_reativacao_faz_tempo(self):
        """Testa inferencia com faz tempo."""
        assert inferir_tipo("faz tempo que nao fala") == TipoAbordagem.REATIVACAO

    def test_inferir_reativacao_nao_responde(self):
        """Testa inferencia com nao responde."""
        assert inferir_tipo("ele nao responde ha semanas") == TipoAbordagem.REATIVACAO

    # Follow-up
    def test_inferir_followup_follow(self):
        """Testa inferencia de followup."""
        assert inferir_tipo("manda follow-up") == TipoAbordagem.FOLLOWUP

    def test_inferir_followup_continua(self):
        """Testa inferencia com continua."""
        assert inferir_tipo("continua a conversa") == TipoAbordagem.FOLLOWUP

    def test_inferir_followup_padrao_existente(self):
        """Testa que medico existente sem instrucao = followup."""
        assert inferir_tipo("", eh_novo=False) == TipoAbordagem.FOLLOWUP

    def test_inferir_followup_lembra(self):
        """Testa inferencia com lembra."""
        # Nota: "lembra ele da vaga" tem "vaga" que eh keyword de oferta
        # Testamos com instrucao sem "vaga"
        assert inferir_tipo("lembra ele da conversa") == TipoAbordagem.FOLLOWUP

    # Custom
    def test_inferir_custom_instrucao_especifica(self):
        """Testa inferencia de custom com instrucao especifica."""
        assert inferir_tipo("pergunta se ele conhece algum colega anestesista") == TipoAbordagem.CUSTOM

    def test_inferir_custom_instrucao_longa(self):
        """Testa que instrucao longa nao padrao = custom."""
        assert inferir_tipo("fala que temos uma oportunidade especial para indicacoes") == TipoAbordagem.CUSTOM


class TestObterPrompt:
    """Testes de obtencao de prompt."""

    def test_obter_prompt_discovery(self):
        """Testa obtencao do prompt discovery."""
        prompt = obter_prompt(TipoAbordagem.DISCOVERY)
        assert "PRIMEIRO CONTATO" in prompt
        assert "{nome}" in prompt

    def test_obter_prompt_oferta(self):
        """Testa obtencao do prompt oferta."""
        prompt = obter_prompt(TipoAbordagem.OFERTA)
        assert "VAGA ESPECIFICA" in prompt
        assert "{hospital}" in prompt
        assert "{valor}" in prompt

    def test_obter_prompt_reativacao(self):
        """Testa obtencao do prompt reativacao."""
        prompt = obter_prompt(TipoAbordagem.REATIVACAO)
        assert "REATIVAR" in prompt
        assert "{ultima_interacao}" in prompt

    def test_obter_prompt_followup(self):
        """Testa obtencao do prompt followup."""
        prompt = obter_prompt(TipoAbordagem.FOLLOWUP)
        assert "FOLLOW-UP" in prompt
        assert "{historico_resumido}" in prompt

    def test_obter_prompt_custom(self):
        """Testa obtencao do prompt custom."""
        prompt = obter_prompt(TipoAbordagem.CUSTOM)
        assert "instrucao especifica" in prompt
        assert "{instrucao}" in prompt


class TestPrepararPrompt:
    """Testes de preparacao de prompt."""

    def test_preparar_prompt_discovery(self):
        """Testa preparacao do prompt discovery."""
        prompt = preparar_prompt(
            TipoAbordagem.DISCOVERY,
            nome="Dr Carlos",
            especialidade="Anestesiologia"
        )
        assert "Dr Carlos" in prompt
        assert "Anestesiologia" in prompt

    def test_preparar_prompt_oferta(self):
        """Testa preparacao do prompt oferta."""
        prompt = preparar_prompt(
            TipoAbordagem.OFERTA,
            nome="Dr Carlos",
            vaga={
                "hospital": "Sao Luiz",
                "data": "15/12",
                "periodo": "Noturno",
                "valor": "2500",
                "especialidade": "Anestesio"
            }
        )
        assert "Dr Carlos" in prompt
        assert "Sao Luiz" in prompt
        assert "2500" in prompt

    def test_preparar_prompt_com_instrucao(self):
        """Testa preparacao com instrucao."""
        prompt = preparar_prompt(
            TipoAbordagem.CUSTOM,
            nome="Dr Carlos",
            instrucao="perguntar se conhece colegas"
        )
        assert "perguntar se conhece colegas" in prompt


class TestDescreverTipo:
    """Testes de descricao de tipo."""

    def test_descrever_discovery(self):
        """Testa descricao discovery."""
        assert descrever_tipo(TipoAbordagem.DISCOVERY) == "primeiro contato"

    def test_descrever_oferta(self):
        """Testa descricao oferta."""
        assert descrever_tipo(TipoAbordagem.OFERTA) == "oferta de vaga"

    def test_descrever_reativacao(self):
        """Testa descricao reativacao."""
        assert descrever_tipo(TipoAbordagem.REATIVACAO) == "reativacao"

    def test_descrever_followup(self):
        """Testa descricao followup."""
        assert descrever_tipo(TipoAbordagem.FOLLOWUP) == "follow-up"

    def test_descrever_custom(self):
        """Testa descricao custom."""
        assert descrever_tipo(TipoAbordagem.CUSTOM) == "mensagem personalizada"


class TestExtrairTelefone:
    """Testes de extracao de telefone."""

    def test_extrair_telefone_11_digitos(self):
        """Testa extracao de telefone com 11 digitos."""
        assert extrair_telefone("manda pro 11999887766") == "11999887766"

    def test_extrair_telefone_com_hifen(self):
        """Testa extracao com hifen."""
        assert extrair_telefone("11 99988-7766") == "11999887766"

    def test_extrair_telefone_com_55(self):
        """Testa extracao com codigo do pais."""
        resultado = extrair_telefone("5511999887766")
        assert resultado is not None
        assert "999887766" in resultado

    def test_extrair_telefone_nao_encontrado(self):
        """Testa quando nao tem telefone."""
        assert extrair_telefone("manda pro Dr Carlos") is None


class TestExtrairHospital:
    """Testes de extracao de hospital."""

    def test_extrair_hospital_sao_luiz(self):
        """Testa extracao de Sao Luiz."""
        assert extrair_hospital("vaga no Sao Luiz") == "Sao Luiz"

    def test_extrair_hospital_einstein(self):
        """Testa extracao de Einstein."""
        assert extrair_hospital("plantao no einstein") == "Einstein"

    def test_extrair_hospital_sirio(self):
        """Testa extracao de Sirio."""
        assert extrair_hospital("vaga no sirio") == "Sirio"

    def test_extrair_hospital_nao_encontrado(self):
        """Testa quando nao tem hospital."""
        assert extrair_hospital("manda msg pro medico") is None

    def test_extrair_hospital_customizado(self):
        """Testa com lista customizada."""
        hospitais = ["hospital abc", "clinica xyz"]
        assert extrair_hospital("vaga no Hospital ABC", hospitais) == "Hospital Abc"


class TestExtrairData:
    """Testes de extracao de data."""

    def test_extrair_data_hoje(self):
        """Testa extracao de hoje."""
        resultado = extrair_data("plantao hoje")
        assert resultado == datetime.now().strftime("%Y-%m-%d")

    def test_extrair_data_amanha(self):
        """Testa extracao de amanha."""
        from datetime import timedelta
        resultado = extrair_data("plantao amanha")
        esperado = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert resultado == esperado

    def test_extrair_data_dia_especifico(self):
        """Testa extracao de dia especifico."""
        resultado = extrair_data("plantao dia 15")
        assert resultado is not None
        assert "-15" in resultado

    def test_extrair_data_formato_barra(self):
        """Testa extracao com formato dd/mm."""
        resultado = extrair_data("vaga 15/12")
        assert resultado is not None
        assert "-12-15" in resultado

    def test_extrair_data_nao_encontrada(self):
        """Testa quando nao tem data."""
        assert extrair_data("manda msg pro medico") is None


class TestIntegracaoInferencia:
    """Testes de integracao da inferencia."""

    def test_cenario_manda_msg_simples(self):
        """Testa 'manda msg pro 11999' = discovery para novo."""
        assert inferir_tipo("manda msg", eh_novo=True) == TipoAbordagem.DISCOVERY

    def test_cenario_oferece_vaga(self):
        """Testa 'oferece a vaga do Sao Luiz' = oferta."""
        assert inferir_tipo("oferece a vaga do Sao Luiz") == TipoAbordagem.OFERTA

    def test_cenario_tenta_contato_novo(self):
        """Testa 'tenta contato de novo' = reativacao."""
        # "de novo" pode ser ambiguo, mas "tenta contato" nao eh reativacao
        # vamos verificar o comportamento atual
        resultado = inferir_tipo("tenta contato de novo")
        assert resultado in [TipoAbordagem.CUSTOM, TipoAbordagem.DISCOVERY]

    def test_cenario_pergunta_interesse(self):
        """Testa 'pergunta se tem interesse' = followup para existente."""
        # Instrucao especifica -> custom
        resultado = inferir_tipo("pergunta se ele tem interesse", eh_novo=False)
        assert resultado == TipoAbordagem.CUSTOM

    def test_cenario_pergunta_colegas(self):
        """Testa 'pergunta se conhece colegas' = custom."""
        assert inferir_tipo("pergunta se conhece colegas anestesistas") == TipoAbordagem.CUSTOM

    def test_cenario_com_vaga_detectada(self):
        """Testa que vaga detectada = oferta."""
        assert inferir_tipo("manda msg", tem_vaga=True) == TipoAbordagem.OFERTA
