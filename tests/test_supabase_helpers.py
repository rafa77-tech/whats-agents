"""
Testes para os helpers centralizados do Supabase.

Sprint 10 - S10.E1.2
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.supabase import (
    contar_interacoes_periodo,
    buscar_medico_por_telefone,
    buscar_conversa_ativa,
    listar_handoffs_pendentes,
    buscar_vagas_disponiveis,
    atualizar_controle_conversa,
)


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


class TestBuscarMedicoPorTelefone:
    """Testes para buscar_medico_por_telefone()."""

    @pytest.mark.asyncio
    async def test_encontra_medico(self):
        """Deve encontrar medico pelo telefone."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "uuid", "telefone": "11999887766", "nome": "Dr Test"}]
            mock_exec.return_value = mock_response

            resultado = await buscar_medico_por_telefone("11999887766")

            assert resultado is not None
            assert resultado["telefone"] == "11999887766"

    @pytest.mark.asyncio
    async def test_limpa_formatacao_telefone(self):
        """Deve limpar formatacao do telefone antes de buscar."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "uuid", "telefone": "11999887766"}]
            mock_exec.return_value = mock_response

            # Telefone com formatacao
            resultado = await buscar_medico_por_telefone("(11) 99988-7766")

            assert resultado is not None

    @pytest.mark.asyncio
    async def test_retorna_none_quando_nao_encontra(self):
        """Deve retornar None quando medico nao existe."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = []
            mock_exec.return_value = mock_response

            resultado = await buscar_medico_por_telefone("00000000000")

            assert resultado is None


class TestBuscarConversaAtiva:
    """Testes para buscar_conversa_ativa()."""

    @pytest.mark.asyncio
    async def test_encontra_conversa_ativa(self):
        """Deve encontrar conversa ativa do cliente."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "conv-uuid", "status": "active", "cliente_id": "cli-uuid"}]
            mock_exec.return_value = mock_response

            resultado = await buscar_conversa_ativa("cli-uuid")

            assert resultado is not None
            assert resultado["status"] == "active"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_conversa(self):
        """Deve retornar None quando nao ha conversa ativa."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = []
            mock_exec.return_value = mock_response

            resultado = await buscar_conversa_ativa("cli-uuid")

            assert resultado is None


class TestListarHandoffsPendentes:
    """Testes para listar_handoffs_pendentes()."""

    @pytest.mark.asyncio
    async def test_lista_pendentes(self):
        """Deve listar todos os handoffs pendentes."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [
                {"id": "h1", "status": "pendente", "motivo": "teste1"},
                {"id": "h2", "status": "pendente", "motivo": "teste2"},
            ]
            mock_exec.return_value = mock_response

            resultado = await listar_handoffs_pendentes()

            assert len(resultado) == 2
            assert resultado[0]["status"] == "pendente"

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando nao ha pendentes."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = None
            mock_exec.return_value = mock_response

            resultado = await listar_handoffs_pendentes()

            assert resultado == []


class TestBuscarVagasDisponiveis:
    """Testes para buscar_vagas_disponiveis()."""

    @pytest.mark.asyncio
    async def test_busca_vagas_sem_filtro(self):
        """Deve buscar vagas sem filtros."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [
                {"id": "v1", "status": "aberta"},
                {"id": "v2", "status": "aberta"},
            ]
            mock_exec.return_value = mock_response

            resultado = await buscar_vagas_disponiveis()

            assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_busca_com_filtro_especialidade(self):
        """Deve filtrar por especialidade."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "v1", "especialidade_id": "esp-uuid"}]
            mock_exec.return_value = mock_response

            resultado = await buscar_vagas_disponiveis(especialidade_id="esp-uuid")

            assert len(resultado) == 1

    @pytest.mark.asyncio
    async def test_respeita_limite(self):
        """Deve respeitar o limite de resultados."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": f"v{i}"} for i in range(5)]
            mock_exec.return_value = mock_response

            resultado = await buscar_vagas_disponiveis(limite=5)

            assert len(resultado) == 5

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando nao ha vagas."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = None
            mock_exec.return_value = mock_response

            resultado = await buscar_vagas_disponiveis()

            assert resultado == []


class TestAtualizarControleConversa:
    """Testes para atualizar_controle_conversa()."""

    @pytest.mark.asyncio
    async def test_atualiza_para_human(self):
        """Deve atualizar conversa para controle humano."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "conv-uuid", "controlled_by": "human"}]
            mock_exec.return_value = mock_response

            resultado = await atualizar_controle_conversa("conv-uuid", "human")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_atualiza_para_ai(self):
        """Deve atualizar conversa para controle IA."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = [{"id": "conv-uuid", "controlled_by": "ai"}]
            mock_exec.return_value = mock_response

            resultado = await atualizar_controle_conversa("conv-uuid", "ai")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_retorna_false_quando_falha(self):
        """Deve retornar False quando atualizacao falha."""
        with patch("app.services.supabase._executar_com_circuit_breaker") as mock_exec:
            mock_response = MagicMock()
            mock_response.data = []
            mock_exec.return_value = mock_response

            resultado = await atualizar_controle_conversa("conv-inexistente", "human")

            assert resultado is False
