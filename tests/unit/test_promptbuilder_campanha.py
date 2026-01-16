"""
Testes para PromptBuilder com contexto de campanha.

Sprint 32 E02 - PromptBuilder com Contexto.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.prompts.builder import (
    construir_prompt_julia,
    PromptBuilder,
    _formatar_escopo_vagas,
    _formatar_margem_negociacao,
    _formatar_data,
)


class TestFormatarData:
    """Testes para _formatar_data."""

    def test_formatar_data_valida(self):
        """Deve converter data ISO para formato brasileiro."""
        resultado = _formatar_data("2026-03-15")
        assert resultado == "15/03/2026"

    def test_formatar_data_invalida(self):
        """Deve retornar a string original se inválida."""
        resultado = _formatar_data("invalido")
        assert resultado == "invalido"

    def test_formatar_data_none(self):
        """Deve retornar None se receber None."""
        resultado = _formatar_data(None)
        assert resultado is None


class TestFormatarEscopoVagas:
    """Testes para _formatar_escopo_vagas."""

    def test_escopo_completo(self):
        """Deve formatar escopo com todos os campos."""
        escopo = {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
            "regiao": "grande_sp"
        }
        resultado = _formatar_escopo_vagas(escopo)

        assert "ESCOPO PERMITIDO" in resultado
        assert "Cardiologia" in resultado
        assert "01/03/2026" in resultado
        assert "31/03/2026" in resultado
        assert "grande_sp" in resultado

    def test_escopo_com_hospital(self):
        """Deve incluir nome do hospital se fornecido."""
        escopo = {
            "especialidade": "pediatria",
            "hospital_id": "uuid-123",
            "hospital_nome": "Hospital São Luiz"
        }
        resultado = _formatar_escopo_vagas(escopo)

        assert "Hospital São Luiz" in resultado

    def test_escopo_sem_hospital(self):
        """Deve indicar 'qualquer hospital' se não especificado."""
        escopo = {"especialidade": "ortopedia"}
        resultado = _formatar_escopo_vagas(escopo)

        assert "Qualquer hospital disponível" in resultado

    def test_escopo_vazio(self):
        """Escopo vazio deve retornar mensagem de bloqueio."""
        resultado = _formatar_escopo_vagas(None)

        assert "NÃO oferte vagas" in resultado

    def test_escopo_dict_vazio(self):
        """Dict vazio deve retornar mensagem de bloqueio."""
        resultado = _formatar_escopo_vagas({})

        assert "NÃO oferte vagas" in resultado


class TestFormatarMargemNegociacao:
    """Testes para _formatar_margem_negociacao."""

    def test_margem_percentual(self):
        """Deve formatar margem percentual corretamente."""
        margem = {"tipo": "percentual", "valor": 15}
        resultado = _formatar_margem_negociacao(margem)

        assert "15%" in resultado
        assert "acima do valor base" in resultado

    def test_margem_valor_maximo(self):
        """Deve formatar margem com valor máximo."""
        margem = {"tipo": "valor_maximo", "valor": 3000}
        resultado = _formatar_margem_negociacao(margem)

        assert "R$" in resultado
        assert "3.000" in resultado or "3000" in resultado

    def test_margem_nula(self):
        """Margem nula deve instruir a não negociar."""
        resultado = _formatar_margem_negociacao(None)

        assert "Não definida" in resultado
        assert "valor é fechado" in resultado

    def test_margem_tipo_desconhecido(self):
        """Tipo desconhecido deve retornar mensagem de erro."""
        margem = {"tipo": "outro", "valor": 100}
        resultado = _formatar_margem_negociacao(margem)

        assert "Formato não reconhecido" in resultado


class TestPromptBuilderCampanha:
    """Testes para PromptBuilder com contexto de campanha."""

    @pytest.mark.asyncio
    async def test_builder_com_campanha_discovery(self):
        """Deve carregar prompt de discovery via com_campanha."""
        mock_prompt = "Prompt de discovery com regras"

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = mock_prompt

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(campaign_type="discovery")

                assert builder._prompt_campanha == mock_prompt
                assert builder._campaign_type == "discovery"

    @pytest.mark.asyncio
    async def test_builder_com_campanha_oferta_e_escopo(self):
        """Deve configurar escopo de vagas para campanha de oferta."""
        escopo = {"especialidade": "cardiologia", "regiao": "sp"}

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt de oferta"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(
                    campaign_type="oferta",
                    offer_scope=escopo
                )

                assert builder._campaign_type == "oferta"
                assert builder._offer_scope == escopo

    @pytest.mark.asyncio
    async def test_build_inclui_campanha(self):
        """Build deve incluir seção de campanha."""
        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt de discovery"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(campaign_type="discovery")
                resultado = builder.build()

                assert "COMPORTAMENTO DESTA CAMPANHA" in resultado
                assert "Prompt de discovery" in resultado

    @pytest.mark.asyncio
    async def test_build_inclui_escopo_para_oferta(self):
        """Build deve incluir escopo de vagas para campanhas de oferta."""
        escopo = {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31"
        }

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt de oferta"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(
                    campaign_type="oferta",
                    offer_scope=escopo
                )
                resultado = builder.build()

                assert "ESCOPO PERMITIDO" in resultado
                assert "Cardiologia" in resultado

    @pytest.mark.asyncio
    async def test_build_inclui_margem_negociacao(self):
        """Build deve incluir margem de negociação."""
        margem = {"tipo": "percentual", "valor": 10}

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt de oferta"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(
                    campaign_type="oferta",
                    negotiation_margin=margem
                )
                resultado = builder.build()

                assert "MARGEM DE NEGOCIAÇÃO" in resultado
                assert "10%" in resultado

    @pytest.mark.asyncio
    async def test_build_inclui_regras_especificas(self):
        """Build deve incluir regras específicas da campanha."""
        regras = [
            "Só ofertar vagas acima de R$ 2.000",
            "Priorizar plantões noturnos"
        ]

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Base"

                builder = PromptBuilder()
                await builder.com_base()
                await builder.com_campanha(
                    campaign_type="oferta",
                    campaign_rules=regras
                )
                resultado = builder.build()

                assert "REGRAS ESPECÍFICAS" in resultado
                assert "R$ 2.000" in resultado
                assert "noturnos" in resultado


class TestConstruirPromptJulia:
    """Testes para função helper construir_prompt_julia."""

    @pytest.mark.asyncio
    async def test_com_campaign_type_discovery(self):
        """Deve usar prompt de discovery quando tipo definido."""
        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "NÃO mencione vagas"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                prompt = await construir_prompt_julia(campaign_type="discovery")

                assert "NÃO mencione vagas" in prompt
                mock_buscar.assert_called_once_with("discovery")

    @pytest.mark.asyncio
    async def test_com_campaign_type_oferta(self):
        """Deve usar prompt de oferta quando tipo definido."""
        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "buscar_vagas()"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                prompt = await construir_prompt_julia(campaign_type="oferta")

                assert "buscar_vagas()" in prompt

    @pytest.mark.asyncio
    async def test_sem_campaign_type_usa_legado(self):
        """Sem campaign_type, deve usar comportamento legado."""
        with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
            mock_carregar.return_value = "Prompt legado"

            prompt = await construir_prompt_julia(primeira_msg=True)

            assert prompt is not None
            # Verifica que chamou julia_primeira_msg
            calls = [str(c) for c in mock_carregar.call_args_list]
            assert any("julia_primeira_msg" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_escopo_vagas_injetado_em_oferta(self):
        """Escopo de vagas deve ser injetado em campanhas de oferta."""
        escopo = {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
        }

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt oferta"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                prompt = await construir_prompt_julia(
                    campaign_type="oferta",
                    offer_scope=escopo
                )

                assert "Cardiologia" in prompt
                assert "01/03/2026" in prompt
                assert "31/03/2026" in prompt

    @pytest.mark.asyncio
    async def test_margem_negociacao_percentual(self):
        """Margem percentual deve ser formatada corretamente."""
        margem = {"tipo": "percentual", "valor": 15}

        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Base"

                prompt = await construir_prompt_julia(
                    campaign_type="oferta",
                    negotiation_margin=margem
                )

                assert "15%" in prompt

    @pytest.mark.asyncio
    async def test_objetivo_campanha_injetado(self):
        """Objetivo da campanha deve aparecer no prompt."""
        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Base"

                prompt = await construir_prompt_julia(
                    campaign_type="oferta",
                    campaign_objective="Apresentar vagas de cardiologia para março"
                )

                assert "cardiologia" in prompt.lower()
                assert "março" in prompt.lower()

    @pytest.mark.asyncio
    async def test_compatibilidade_chamada_antiga(self):
        """Chamadas sem novos parâmetros devem continuar funcionando."""
        with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
            mock_carregar.return_value = "Prompt"

            # Chamada no estilo antigo
            prompt = await construir_prompt_julia(
                diretrizes="Teste de diretrizes",
                contexto="Contexto de teste",
                primeira_msg=True
            )

            assert prompt is not None
            assert "Teste de diretrizes" in prompt or "diretrizes" in prompt.lower()

    @pytest.mark.asyncio
    async def test_campaign_type_tem_prioridade_sobre_primeira_msg(self):
        """campaign_type deve ter prioridade sobre primeira_msg."""
        with patch("app.prompts.builder.buscar_prompt_por_tipo_campanha") as mock_buscar:
            mock_buscar.return_value = "Prompt de campanha"

            with patch("app.prompts.builder.carregar_prompt") as mock_carregar:
                mock_carregar.return_value = "Prompt base"

                prompt = await construir_prompt_julia(
                    campaign_type="discovery",
                    primeira_msg=True  # Deve ser ignorado
                )

                # Verifica que usou o prompt de campanha, não o de primeira_msg
                assert "Prompt de campanha" in prompt
                # Verifica que chamou buscar_prompt_por_tipo_campanha
                mock_buscar.assert_called_once_with("discovery")
