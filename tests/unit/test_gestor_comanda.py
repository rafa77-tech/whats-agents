"""
Testes para serviço de Gestor Comanda Julia.

Sprint 32 E09 - Interpretação com Opus, execução com Haiku.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestGestorComandaInterpretar:
    """Testes para interpretar_comando()."""

    @pytest.mark.asyncio
    async def test_interpreta_comando_contato_medicos(self):
        """Deve interpretar comando de contato com médicos."""
        from app.services.gestor_comanda import GestorComanda

        with patch("app.services.gestor_comanda.anthropic.Anthropic") as mock_anthropic:
            # Mock resposta do Claude
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=json.dumps({
                "interpretacao": "Contatar cardiologistas com interesse positivo",
                "tipo_acao": "contatar_medicos",
                "filtros": {"especialidade": "cardiologia", "status_interesse": "positivo"},
                "acoes": [{"ordem": 1, "descricao": "Buscar médicos", "tipo": "buscar"}],
                "precisa_confirmar": True,
                "pergunta_confirmacao": "Posso contatar os médicos?",
                "dados_a_buscar": ["medicos"],
                "estimativa_impacto": {"medicos_afetados": 0},
                "duvidas": [],
            }))]

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            with patch("app.services.gestor_comanda.supabase") as mock_supabase:
                # Mock insert comando
                mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

                # Mock busca médicos
                mock_medicos = MagicMock()
                mock_medicos.data = [{"id": "m1"}, {"id": "m2"}]
                mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.ilike.return_value.gt.return_value.limit.return_value.execute.return_value = mock_medicos

                gestor = GestorComanda("user-123", "channel-123")
                resultado = await gestor.interpretar_comando(
                    "Contata todos os cardiologistas que mostraram interesse"
                )

                assert resultado["success"] is True
                assert "interpretacao" in resultado

    @pytest.mark.asyncio
    async def test_interpreta_comando_criar_margem(self):
        """Deve interpretar comando de criação de margem."""
        from app.services.gestor_comanda import GestorComanda

        with patch("app.services.gestor_comanda.anthropic.Anthropic") as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=json.dumps({
                "interpretacao": "Definir margem de 15% para vaga específica",
                "tipo_acao": "definir_margem",
                "filtros": {"vaga_id": "vaga-123", "percentual_maximo": 15},
                "acoes": [{"ordem": 1, "descricao": "Criar diretriz", "tipo": "criar"}],
                "precisa_confirmar": True,
                "pergunta_confirmacao": "Confirma a margem?",
                "dados_a_buscar": [],
                "estimativa_impacto": {},
                "duvidas": [],
            }))]

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            with patch("app.services.gestor_comanda.supabase") as mock_supabase:
                mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

                gestor = GestorComanda("user-123", "channel-123")
                resultado = await gestor.interpretar_comando(
                    "Define margem de 15% para a vaga vaga-123"
                )

                assert resultado["success"] is True


class TestGestorComandaAjustar:
    """Testes para ajustar_plano()."""

    @pytest.mark.asyncio
    async def test_ajusta_plano_com_feedback(self):
        """Deve ajustar plano baseado em feedback do gestor."""
        from app.services.gestor_comanda import GestorComanda

        with patch("app.services.gestor_comanda.anthropic.Anthropic") as mock_anthropic:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=json.dumps({
                "interpretacao": "Contatar apenas 10 médicos mais ativos",
                "tipo_acao": "contatar_medicos",
                "filtros": {"limite": 10},
                "acoes": [{"ordem": 1, "descricao": "Buscar top 10", "tipo": "buscar"}],
                "precisa_confirmar": True,
                "pergunta_confirmacao": "Posso prosseguir?",
                "dados_a_buscar": ["medicos"],
                "estimativa_impacto": {"medicos_afetados": 10},
                "duvidas": [],
            }))]

            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            with patch("app.services.gestor_comanda.supabase") as mock_supabase:
                # Mock busca comando existente
                mock_comando = MagicMock()
                mock_comando.data = [{
                    "id": "cmd-123",
                    "comando_original": "Contata cardiologistas",
                    "interpretacao": {"tipo_acao": "contatar_medicos"},
                    "status": "aguardando_confirmacao",
                }]
                mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_comando

                mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

                gestor = GestorComanda("user-123", "channel-123")
                resultado = await gestor.ajustar_plano(
                    comando_id="cmd-123",
                    ajuste="Mas contata apenas os 10 mais ativos"
                )

                assert resultado["success"] is True


class TestGestorComandaCancelar:
    """Testes para cancelar_comando()."""

    @pytest.mark.asyncio
    async def test_cancela_comando(self):
        """Deve cancelar comando corretamente."""
        from app.services.gestor_comanda import GestorComanda

        with patch("app.services.gestor_comanda.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            gestor = GestorComanda("user-123", "channel-123")
            resultado = await gestor.cancelar_comando(
                comando_id="cmd-123",
                motivo="Mudei de ideia"
            )

            assert resultado["success"] is True
            assert resultado["status"] == "cancelado"


class TestExtrairJson:
    """Testes para _extrair_json()."""

    def test_extrai_json_direto(self):
        """Deve extrair JSON quando está no início."""
        from app.services.gestor_comanda import _extrair_json

        texto = '{"chave": "valor"}'
        resultado = _extrair_json(texto)

        assert resultado is not None
        assert resultado["chave"] == "valor"

    def test_extrai_json_no_meio_do_texto(self):
        """Deve extrair JSON do meio do texto."""
        from app.services.gestor_comanda import _extrair_json

        texto = 'Aqui está a resposta: {"chave": "valor"} mais texto'
        resultado = _extrair_json(texto)

        assert resultado is not None
        assert resultado["chave"] == "valor"

    def test_retorna_none_para_texto_invalido(self):
        """Deve retornar None para texto sem JSON."""
        from app.services.gestor_comanda import _extrair_json

        texto = 'Texto sem JSON válido'
        resultado = _extrair_json(texto)

        assert resultado is None


class TestFormatarMensagemInterpretacao:
    """Testes para _formatar_mensagem_interpretacao()."""

    def test_formata_mensagem_completa(self):
        """Deve formatar mensagem com todos os campos."""
        from app.services.gestor_comanda import GestorComanda

        interpretacao = {
            "interpretacao": "Vou contatar os médicos",
            "acoes": [
                {"ordem": 1, "descricao": "Buscar médicos"},
                {"ordem": 2, "descricao": "Enviar mensagens"},
            ],
            "estimativa_impacto": {
                "medicos_afetados": 25,
                "mensagens_a_enviar": 25,
            },
            "precisa_confirmar": True,
            "pergunta_confirmacao": "Posso começar?",
            "duvidas": [],
        }

        gestor = GestorComanda("user-123", "channel-123")
        mensagem = gestor._formatar_mensagem_interpretacao(interpretacao)

        assert "Entendi!" in mensagem
        assert "Vou contatar os médicos" in mensagem
        assert "Médicos: 25" in mensagem
        assert "Buscar médicos" in mensagem
        assert "Enviar mensagens" in mensagem
        assert "Posso começar?" in mensagem

    def test_formata_mensagem_com_duvidas(self):
        """Deve incluir dúvidas na mensagem."""
        from app.services.gestor_comanda import GestorComanda

        interpretacao = {
            "interpretacao": "Não tenho certeza",
            "acoes": [],
            "estimativa_impacto": {},
            "precisa_confirmar": True,
            "pergunta_confirmacao": "Confirma?",
            "duvidas": ["Qual especialidade?", "Qual período?"],
        }

        gestor = GestorComanda("user-123", "channel-123")
        mensagem = gestor._formatar_mensagem_interpretacao(interpretacao)

        assert "Dúvidas:" in mensagem
        assert "Qual especialidade?" in mensagem
        assert "Qual período?" in mensagem


class TestProcessarComandoGestor:
    """Testes para processar_comando_gestor()."""

    @pytest.mark.asyncio
    async def test_processa_comando_simples(self):
        """Deve processar comando simples."""
        from app.services.gestor_comanda import processar_comando_gestor

        with patch("app.services.gestor_comanda.GestorComanda") as mock_class:
            mock_instance = MagicMock()
            mock_instance.interpretar_comando = AsyncMock(return_value={
                "success": True,
                "interpretacao": {"tipo_acao": "consultar"},
            })
            mock_class.return_value = mock_instance

            resultado = await processar_comando_gestor(
                comando="Quantos médicos temos?",
                user_id="user-123",
                channel_id="channel-123",
            )

            assert resultado["success"] is True
            mock_instance.interpretar_comando.assert_called_once()
