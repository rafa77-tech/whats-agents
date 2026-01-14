"""
Testes para os helpers genericos do Supabase.

Sprint 10 - S10.E1.2 (original)
Sprint 30 - Consolidado (testes de entidade movidos para services especificos)

Funcoes de entidade foram movidas:
- buscar_medico_por_telefone -> tests/services/test_medico.py
- buscar_conversa_ativa -> tests/services/test_conversa.py
- listar_handoffs_pendentes -> tests/services/test_handoff.py
- buscar_vagas_disponiveis -> tests/services/test_vagas.py
- atualizar_controle_conversa -> tests/services/test_conversa.py
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.supabase import contar_interacoes_periodo


class TestContarInteracoesPeriodo:
    """Testes para contar_interacoes_periodo()."""

    @pytest.mark.asyncio
    async def test_conta_todas_interacoes(self):
        """Deve contar todas as interacoes no periodo."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.count = 42
            mock_exec.return_value = mock_response

            inicio = datetime(2024, 1, 1)
            fim = datetime(2024, 1, 31)

            resultado = await contar_interacoes_periodo(inicio, fim)

            assert resultado == 42
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_conta_com_filtro_direcao(self):
        """Deve filtrar por direcao (entrada/saida)."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.count = 15
            mock_exec.return_value = mock_response

            inicio = datetime(2024, 1, 1)
            fim = datetime(2024, 1, 31)

            resultado = await contar_interacoes_periodo(inicio, fim, direcao="saida")

            assert resultado == 15

    @pytest.mark.asyncio
    async def test_conta_com_filtro_cliente(self):
        """Deve filtrar por cliente_id."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.count = 5
            mock_exec.return_value = mock_response

            inicio = datetime(2024, 1, 1)
            fim = datetime(2024, 1, 31)

            resultado = await contar_interacoes_periodo(
                inicio, fim, cliente_id="uuid-cliente"
            )

            assert resultado == 5

    @pytest.mark.asyncio
    async def test_retorna_zero_quando_nenhuma(self):
        """Deve retornar 0 quando nao ha interacoes."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.count = None
            mock_exec.return_value = mock_response

            inicio = datetime(2024, 1, 1)
            fim = datetime(2024, 1, 31)

            resultado = await contar_interacoes_periodo(inicio, fim)

            assert resultado == 0
