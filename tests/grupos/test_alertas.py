"""
Testes do módulo de alertas do pipeline de grupos.

Sprint 14 - E12 - Métricas e Monitoramento
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, UTC

from app.services.grupos.alertas import (
    ALERTAS_GRUPOS,
    verificar_fila_travada,
    verificar_taxa_conversao,
    verificar_custo_alto,
    verificar_itens_pendentes_antigos,
    verificar_duplicacao_alta,
    verificar_alertas_grupos,
    enviar_alerta_grupos_slack,
    executar_verificacao_alertas_grupos,
)


# =============================================================================
# Testes das Configurações de Alertas
# =============================================================================

class TestConfiguracaoAlertas:
    """Testes das configurações de alertas."""

    def test_alertas_definidos(self):
        """Verifica que todos os alertas estão definidos."""
        assert "fila_travada" in ALERTAS_GRUPOS
        assert "taxa_conversao_baixa" in ALERTAS_GRUPOS
        assert "custo_alto" in ALERTAS_GRUPOS
        assert "itens_pendentes_antigos" in ALERTAS_GRUPOS
        assert "duplicacao_alta" in ALERTAS_GRUPOS

    def test_fila_travada_config(self):
        """Verifica configuração de fila travada."""
        config = ALERTAS_GRUPOS["fila_travada"]
        assert config["threshold"] == 10
        assert config["severidade"] == "error"

    def test_custo_alto_config(self):
        """Verifica configuração de custo alto."""
        config = ALERTAS_GRUPOS["custo_alto"]
        assert config["threshold_usd"] == 1.0
        assert config["severidade"] == "warning"


# =============================================================================
# Testes dos Verificadores de Alertas
# =============================================================================

class TestVerificarFilaTravada:
    """Testes de verificação de fila travada."""

    @pytest.mark.asyncio
    async def test_sem_itens_erro(self):
        """Retorna vazio quando não há itens com erro."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await verificar_fila_travada()

            assert result == []

    @pytest.mark.asyncio
    async def test_poucos_itens_erro(self):
        """Retorna vazio quando há poucos itens com erro."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                count=5  # Abaixo do threshold de 10
            )

            result = await verificar_fila_travada()

            assert result == []

    @pytest.mark.asyncio
    async def test_muitos_itens_erro(self):
        """Retorna alerta quando há muitos itens com erro."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                count=15  # Acima do threshold de 10
            )

            result = await verificar_fila_travada()

            assert len(result) == 1
            assert result[0]["tipo"] == "fila_travada"
            assert result[0]["valor"] == 15
            assert result[0]["severidade"] == "error"


class TestVerificarTaxaConversao:
    """Testes de verificação de taxa de conversão."""

    @pytest.mark.asyncio
    async def test_taxa_ok(self):
        """Retorna vazio quando taxa está OK."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            # Total: 100, Importadas: 10 = 10%
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                count=100
            )
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
                count=10
            )

            result = await verificar_taxa_conversao()

            assert result == []

    @pytest.mark.asyncio
    async def test_taxa_baixa(self):
        """Retorna alerta quando taxa está baixa."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            # Total: 100, Importadas: 2 = 2%
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                count=100
            )
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
                count=2
            )

            result = await verificar_taxa_conversao()

            assert len(result) == 1
            assert result[0]["tipo"] == "taxa_conversao_baixa"

    @pytest.mark.asyncio
    async def test_sem_vagas(self):
        """Retorna vazio quando não há vagas."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await verificar_taxa_conversao()

            assert result == []


class TestVerificarCustoAlto:
    """Testes de verificação de custo alto."""

    @pytest.mark.asyncio
    async def test_custo_ok(self):
        """Retorna vazio quando custo está OK."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"custo_total_usd": 0.5}  # Abaixo de $1
            )

            result = await verificar_custo_alto()

            assert result == []

    @pytest.mark.asyncio
    async def test_custo_alto(self):
        """Retorna alerta quando custo está alto."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"custo_total_usd": 1.5}  # Acima de $1
            )

            result = await verificar_custo_alto()

            assert len(result) == 1
            assert result[0]["tipo"] == "custo_alto"
            assert result[0]["valor"] == 1.5

    @pytest.mark.asyncio
    async def test_sem_dados(self):
        """Retorna vazio quando não há dados."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await verificar_custo_alto()

            assert result == []


class TestVerificarItensPendentesAntigos:
    """Testes de verificação de itens pendentes antigos."""

    @pytest.mark.asyncio
    async def test_sem_itens_antigos(self):
        """Retorna vazio quando não há itens antigos."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await verificar_itens_pendentes_antigos()

            assert result == []

    @pytest.mark.asyncio
    async def test_poucos_itens_antigos(self):
        """Retorna vazio quando há poucos itens antigos."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
                count=3  # Abaixo do threshold de 5
            )

            result = await verificar_itens_pendentes_antigos()

            assert result == []

    @pytest.mark.asyncio
    async def test_muitos_itens_antigos(self):
        """Retorna alerta quando há muitos itens antigos."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
                count=10  # Acima do threshold de 5
            )

            result = await verificar_itens_pendentes_antigos()

            assert len(result) == 1
            assert result[0]["tipo"] == "itens_pendentes_antigos"


class TestVerificarDuplicacaoAlta:
    """Testes de verificação de duplicação alta."""

    @pytest.mark.asyncio
    async def test_duplicacao_ok(self):
        """Retorna vazio quando duplicação está OK."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            # Total: 100, Duplicadas: 30 = 30%
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                count=100
            )
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
                count=30
            )

            result = await verificar_duplicacao_alta()

            assert result == []

    @pytest.mark.asyncio
    async def test_duplicacao_alta(self):
        """Retorna alerta quando duplicação está alta."""
        with patch("app.services.grupos.alertas.supabase") as mock_supabase:
            # Total: 100, Duplicadas: 60 = 60%
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
                count=100
            )
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
                count=60
            )

            result = await verificar_duplicacao_alta()

            assert len(result) == 1
            assert result[0]["tipo"] == "duplicacao_alta"


# =============================================================================
# Testes do Verificador Agregado
# =============================================================================

class TestVerificarAlertasGrupos:
    """Testes do verificador agregado."""

    @pytest.mark.asyncio
    async def test_sem_alertas(self):
        """Retorna lista vazia quando não há alertas."""
        with patch("app.services.grupos.alertas.verificar_fila_travada", new_callable=AsyncMock) as m1, \
             patch("app.services.grupos.alertas.verificar_taxa_conversao", new_callable=AsyncMock) as m2, \
             patch("app.services.grupos.alertas.verificar_custo_alto", new_callable=AsyncMock) as m3, \
             patch("app.services.grupos.alertas.verificar_itens_pendentes_antigos", new_callable=AsyncMock) as m4, \
             patch("app.services.grupos.alertas.verificar_duplicacao_alta", new_callable=AsyncMock) as m5:

            m1.return_value = []
            m2.return_value = []
            m3.return_value = []
            m4.return_value = []
            m5.return_value = []

            result = await verificar_alertas_grupos()

            assert result == []

    @pytest.mark.asyncio
    async def test_multiplos_alertas(self):
        """Retorna múltiplos alertas quando há problemas."""
        with patch("app.services.grupos.alertas.verificar_fila_travada", new_callable=AsyncMock) as m1, \
             patch("app.services.grupos.alertas.verificar_taxa_conversao", new_callable=AsyncMock) as m2, \
             patch("app.services.grupos.alertas.verificar_custo_alto", new_callable=AsyncMock) as m3, \
             patch("app.services.grupos.alertas.verificar_itens_pendentes_antigos", new_callable=AsyncMock) as m4, \
             patch("app.services.grupos.alertas.verificar_duplicacao_alta", new_callable=AsyncMock) as m5:

            m1.return_value = [{"tipo": "fila_travada"}]
            m2.return_value = [{"tipo": "taxa_conversao_baixa"}]
            m3.return_value = []
            m4.return_value = []
            m5.return_value = []

            result = await verificar_alertas_grupos()

            assert len(result) == 2


# =============================================================================
# Testes do Envio de Alertas
# =============================================================================

class TestEnviarAlertaSlack:
    """Testes de envio de alertas para Slack."""

    @pytest.mark.asyncio
    async def test_enviar_alerta_warning(self):
        """Envia alerta de warning."""
        with patch("app.services.grupos.alertas.enviar_slack", new_callable=AsyncMock) as mock_enviar:
            alerta = {
                "tipo": "custo_alto",
                "mensagem": "Custo hoje: $1.50",
                "severidade": "warning",
                "valor": 1.5
            }

            await enviar_alerta_grupos_slack(alerta)

            mock_enviar.assert_called_once()
            # Verificar que usou cor de warning
            call_args = mock_enviar.call_args
            assert "#FF9800" in str(call_args)

    @pytest.mark.asyncio
    async def test_enviar_alerta_error(self):
        """Envia alerta de error."""
        with patch("app.services.grupos.alertas.enviar_slack", new_callable=AsyncMock) as mock_enviar:
            alerta = {
                "tipo": "fila_travada",
                "mensagem": "15 itens com erro",
                "severidade": "error",
                "valor": 15
            }

            await enviar_alerta_grupos_slack(alerta)

            mock_enviar.assert_called_once()


# =============================================================================
# Testes do Executor de Alertas
# =============================================================================

class TestExecutarVerificacaoAlertas:
    """Testes do executor de verificação de alertas."""

    @pytest.mark.asyncio
    async def test_sem_alertas(self):
        """Não envia nada quando não há alertas."""
        with patch("app.services.grupos.alertas.verificar_alertas_grupos", new_callable=AsyncMock) as mock_verificar, \
             patch("app.services.grupos.alertas.enviar_alerta_grupos_slack", new_callable=AsyncMock) as mock_enviar:

            mock_verificar.return_value = []

            result = await executar_verificacao_alertas_grupos()

            assert result == []
            mock_enviar.assert_not_called()

    @pytest.mark.asyncio
    async def test_com_alertas(self):
        """Envia alertas encontrados."""
        with patch("app.services.grupos.alertas.verificar_alertas_grupos", new_callable=AsyncMock) as mock_verificar, \
             patch("app.services.grupos.alertas.enviar_alerta_grupos_slack", new_callable=AsyncMock) as mock_enviar:

            mock_verificar.return_value = [
                {"tipo": "alerta1", "mensagem": "Teste 1", "severidade": "warning"},
                {"tipo": "alerta2", "mensagem": "Teste 2", "severidade": "error"},
            ]

            result = await executar_verificacao_alertas_grupos()

            assert len(result) == 2
            assert mock_enviar.call_count == 2

    @pytest.mark.asyncio
    async def test_erro_nao_propaga(self):
        """Erro não propaga exceção."""
        with patch("app.services.grupos.alertas.verificar_alertas_grupos", new_callable=AsyncMock) as mock_verificar:
            mock_verificar.side_effect = Exception("Erro de teste")

            result = await executar_verificacao_alertas_grupos()

            assert result == []
