"""
Testes para o extrator de dados.

Sprint 14 - E05 - S05.4
"""

import pytest
import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.services.grupos.extrator import (
    extrair_dados_mensagem,
    _parsear_resposta_extracao,
    VagaExtraida,
    DadosVagaExtraida,
    ConfiancaExtracao,
    ResultadoExtracao,
    salvar_vaga_extraida,
)


class TestParsearRespostaExtracao:
    """Testes do parser de extração."""

    def test_uma_vaga(self):
        """Deve parsear uma vaga corretamente."""
        json_str = '''
        {
          "vagas": [
            {
              "dados": {
                "hospital": "Hospital São Luiz",
                "especialidade": "Clínica Médica",
                "data": "2024-12-28",
                "valor": 1800
              },
              "confianca": {
                "hospital": 0.95,
                "especialidade": 0.90
              },
              "data_valida": true
            }
          ],
          "total_vagas": 1
        }
        '''
        resultado = _parsear_resposta_extracao(json_str)

        assert resultado.total_vagas == 1
        assert len(resultado.vagas) == 1
        assert resultado.vagas[0].dados.hospital == "Hospital São Luiz"
        assert resultado.vagas[0].dados.valor == 1800

    def test_multiplas_vagas(self):
        """Deve parsear múltiplas vagas."""
        json_str = '''
        {
          "vagas": [
            {"dados": {"hospital": "Hospital A", "especialidade": "CM"}, "confianca": {}, "data_valida": true},
            {"dados": {"hospital": "Hospital B", "especialidade": "Pediatria"}, "confianca": {}, "data_valida": true}
          ],
          "total_vagas": 2
        }
        '''
        resultado = _parsear_resposta_extracao(json_str)

        assert resultado.total_vagas == 2
        assert resultado.vagas[0].dados.hospital == "Hospital A"
        assert resultado.vagas[1].dados.hospital == "Hospital B"

    def test_vaga_com_data_invalida(self):
        """Deve marcar vaga com data passada."""
        json_str = '''
        {
          "vagas": [
            {
              "dados": {"hospital": "X", "especialidade": "Y", "data": "2020-01-01"},
              "confianca": {},
              "data_valida": false
            }
          ],
          "total_vagas": 1
        }
        '''
        resultado = _parsear_resposta_extracao(json_str)

        assert resultado.vagas[0].data_valida is False

    def test_json_com_texto_antes(self):
        """Deve extrair JSON mesmo com texto antes."""
        json_str = '''
        Analisando a mensagem, encontrei:
        {
          "vagas": [
            {"dados": {"hospital": "Test", "especialidade": "CM"}, "confianca": {}, "data_valida": true}
          ],
          "total_vagas": 1
        }
        '''
        resultado = _parsear_resposta_extracao(json_str)

        assert resultado.total_vagas == 1

    def test_vagas_vazias(self):
        """Deve retornar lista vazia se não houver vagas."""
        json_str = '{"vagas": [], "total_vagas": 0}'
        resultado = _parsear_resposta_extracao(json_str)

        assert resultado.total_vagas == 0
        assert len(resultado.vagas) == 0

    def test_json_invalido(self):
        """Deve levantar erro para JSON inválido."""
        with pytest.raises(json.JSONDecodeError):
            _parsear_resposta_extracao("isso não é json")


class TestConfiancaExtracao:
    """Testes do cálculo de confiança."""

    def test_media_ponderada_alta(self):
        """Confiança alta deve resultar em média alta."""
        confianca = ConfiancaExtracao(
            hospital=1.0,
            especialidade=1.0,
            data=0.8,
            hora_inicio=0.5,
            hora_fim=0.5,
            valor=0.9
        )

        media = confianca.media_ponderada()

        # Hospital e especialidade têm peso maior
        assert 0.8 < media < 1.0

    def test_media_ponderada_baixa(self):
        """Confiança baixa deve resultar em média baixa."""
        confianca = ConfiancaExtracao(
            hospital=0.3,
            especialidade=0.3,
            data=0.5,
            hora_inicio=0.5,
            hora_fim=0.5,
            valor=0.5
        )

        media = confianca.media_ponderada()

        assert media < 0.5

    def test_media_ponderada_zeros(self):
        """Deve funcionar com zeros."""
        confianca = ConfiancaExtracao()
        media = confianca.media_ponderada()

        assert media == 0.0


class TestCamposFaltando:
    """Testes de identificação de campos faltando."""

    def test_identifica_campos_faltando(self):
        """Deve identificar campos ausentes."""
        resultado = _parsear_resposta_extracao('''
        {
          "vagas": [{
            "dados": {"hospital": "X", "especialidade": null},
            "confianca": {},
            "data_valida": true
          }],
          "total_vagas": 1
        }
        ''')

        assert "especialidade" in resultado.vagas[0].campos_faltando

    def test_identifica_todos_campos_faltando(self):
        """Deve identificar múltiplos campos ausentes."""
        resultado = _parsear_resposta_extracao('''
        {
          "vagas": [{
            "dados": {},
            "confianca": {},
            "data_valida": true
          }],
          "total_vagas": 1
        }
        ''')

        campos = resultado.vagas[0].campos_faltando
        assert "hospital" in campos
        assert "especialidade" in campos
        assert "data" in campos
        assert "valor" in campos


class TestDadosVagaExtraida:
    """Testes da dataclass DadosVagaExtraida."""

    def test_criacao_completa(self):
        """Deve criar dados com todos os campos."""
        dados = DadosVagaExtraida(
            hospital="Hospital ABC",
            especialidade="Cardiologia",
            data=date.today(),
            hora_inicio="19:00",
            hora_fim="07:00",
            valor=2000,
            periodo="Noturno",
            setor="Pronto atendimento",
            tipo_vaga="Cobertura",
            forma_pagamento="Pessoa jurídica",
            observacoes="Necessário RQE"
        )

        assert dados.hospital == "Hospital ABC"
        assert dados.valor == 2000

    def test_criacao_minima(self):
        """Deve criar dados com campos mínimos."""
        dados = DadosVagaExtraida(
            hospital="Hospital XYZ",
            especialidade="CM"
        )

        assert dados.hospital == "Hospital XYZ"
        assert dados.valor is None


class TestVagaExtraida:
    """Testes da dataclass VagaExtraida."""

    def test_vaga_valida(self):
        """Deve criar vaga válida."""
        vaga = VagaExtraida(
            dados=DadosVagaExtraida(hospital="H", especialidade="E"),
            confianca=ConfiancaExtracao(hospital=0.9, especialidade=0.8),
            data_valida=True
        )

        assert vaga.data_valida is True
        assert vaga.campos_faltando == []

    def test_vaga_invalida(self):
        """Deve criar vaga inválida."""
        vaga = VagaExtraida(
            dados=DadosVagaExtraida(),
            confianca=ConfiancaExtracao(),
            data_valida=False,
            campos_faltando=["hospital", "especialidade"]
        )

        assert vaga.data_valida is False
        assert len(vaga.campos_faltando) == 2


class TestExtrairDadosMensagem:
    """Testes da função de extração."""

    @pytest.fixture
    def mock_anthropic(self):
        """Mock do cliente Anthropic."""
        with patch("app.services.grupos.extrator.anthropic.Anthropic") as mock:
            yield mock.return_value

    @pytest.mark.asyncio
    async def test_extracao_sucesso(self, mock_anthropic):
        """Deve extrair dados corretamente."""
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text='''
            {
              "vagas": [{
                "dados": {"hospital": "Hospital ABC", "especialidade": "CM", "valor": 1500},
                "confianca": {"hospital": 0.9, "especialidade": 0.85},
                "data_valida": true
              }],
              "total_vagas": 1
            }
            ''')],
            usage=MagicMock(input_tokens=200, output_tokens=100)
        )

        resultado = await extrair_dados_mensagem(
            texto="Plantão Hospital ABC CM R$ 1500",
            nome_grupo="Vagas ABC"
        )

        assert resultado.total_vagas == 1
        assert resultado.vagas[0].dados.hospital == "Hospital ABC"
        assert resultado.tokens_usados == 300

    @pytest.mark.asyncio
    async def test_extracao_multiplas_vagas(self, mock_anthropic):
        """Deve extrair múltiplas vagas."""
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text='''
            {
              "vagas": [
                {"dados": {"hospital": "H1", "especialidade": "CM"}, "confianca": {}, "data_valida": true},
                {"dados": {"hospital": "H2", "especialidade": "Pediatria"}, "confianca": {}, "data_valida": true}
              ],
              "total_vagas": 2
            }
            ''')],
            usage=MagicMock(input_tokens=200, output_tokens=150)
        )

        resultado = await extrair_dados_mensagem("Lista de vagas")

        assert resultado.total_vagas == 2

    @pytest.mark.asyncio
    async def test_extracao_erro_parse(self, mock_anthropic):
        """Deve tratar erro de parse."""
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Resposta inválida")],
            usage=MagicMock(input_tokens=100, output_tokens=50)
        )

        resultado = await extrair_dados_mensagem("Teste")

        assert resultado.total_vagas == 0
        assert resultado.erro is not None


class TestSalvarVagaExtraida:
    """Testes da função salvar_vaga_extraida."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.extrator.supabase") as mock:
            mock.table.return_value = mock
            mock.insert.return_value = mock
            mock.execute.return_value = MagicMock(data=[{"id": str(uuid4())}])
            yield mock

    @pytest.mark.asyncio
    async def test_salvar_vaga_valida(self, mock_supabase):
        """Deve salvar vaga válida."""
        vaga = VagaExtraida(
            dados=DadosVagaExtraida(
                hospital="Hospital ABC",
                especialidade="CM",
                valor=1500
            ),
            confianca=ConfiancaExtracao(hospital=0.9, especialidade=0.8),
            data_valida=True
        )

        vaga_id = await salvar_vaga_extraida(
            mensagem_id=uuid4(),
            grupo_id=uuid4(),
            contato_id=uuid4(),
            vaga=vaga
        )

        assert vaga_id is not None
        mock_supabase.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_nao_salvar_sem_hospital(self, mock_supabase):
        """Não deve salvar vaga sem hospital."""
        vaga = VagaExtraida(
            dados=DadosVagaExtraida(especialidade="CM"),
            confianca=ConfiancaExtracao(),
            data_valida=True
        )

        vaga_id = await salvar_vaga_extraida(
            mensagem_id=uuid4(),
            grupo_id=uuid4(),
            contato_id=None,
            vaga=vaga
        )

        assert vaga_id is None
        mock_supabase.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_nao_salvar_data_invalida(self, mock_supabase):
        """Não deve salvar vaga com data passada."""
        vaga = VagaExtraida(
            dados=DadosVagaExtraida(
                hospital="Hospital",
                especialidade="CM"
            ),
            confianca=ConfiancaExtracao(),
            data_valida=False
        )

        vaga_id = await salvar_vaga_extraida(
            mensagem_id=uuid4(),
            grupo_id=uuid4(),
            contato_id=None,
            vaga=vaga
        )

        assert vaga_id is None
