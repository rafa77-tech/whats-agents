"""
Testes para serviço de validação de telefones.

Sprint 32 E04 - checkNumberStatus Job.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestValidarTelefone:
    """Testes para validar_telefone()."""

    @pytest.mark.asyncio
    async def test_validar_telefone_existe(self):
        """Deve marcar como validado quando WhatsApp existe."""
        from app.services.validacao_telefone import validar_telefone

        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": True, "jid": "5511999999999@s.whatsapp.net"}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "validado"
                    mock_atualizar.assert_called_with("uuid-123", "validado")

    @pytest.mark.asyncio
    async def test_validar_telefone_nao_existe(self):
        """Deve marcar como inválido quando WhatsApp não existe."""
        from app.services.validacao_telefone import validar_telefone

        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": False}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "invalido"
                    mock_atualizar.assert_called_with("uuid-123", "invalido")

    @pytest.mark.asyncio
    async def test_validar_telefone_erro_api(self):
        """Deve marcar como erro quando API falha."""
        from app.services.validacao_telefone import validar_telefone

        with patch("app.services.validacao_telefone.evolution") as mock_evolution:
            mock_evolution.check_number_status = AsyncMock(
                return_value={"exists": False, "error": "timeout"}
            )

            with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
                mock_marcar.return_value = True

                with patch("app.services.validacao_telefone.atualizar_status_telefone") as mock_atualizar:
                    mock_atualizar.return_value = True

                    resultado = await validar_telefone("uuid-123", "5511999999999")

                    assert resultado == "erro"

    @pytest.mark.asyncio
    async def test_skip_se_ja_validando(self):
        """Deve pular se cliente já está sendo validado."""
        from app.services.validacao_telefone import validar_telefone

        with patch("app.services.validacao_telefone.marcar_como_validando") as mock_marcar:
            mock_marcar.return_value = False  # Já em outro estado

            resultado = await validar_telefone("uuid-123", "5511999999999")

            assert resultado == "skip"


class TestProcessarLote:
    """Testes para processamento em lote."""

    @pytest.mark.asyncio
    async def test_processar_lote_vazio(self):
        """Deve retornar stats zeradas se não há pendentes."""
        from app.services.validacao_telefone import processar_lote_validacao

        with patch("app.services.validacao_telefone.buscar_telefones_pendentes") as mock_buscar:
            mock_buscar.return_value = []

            stats = await processar_lote_validacao()

            assert stats["processados"] == 0
            assert stats["validados"] == 0

    @pytest.mark.asyncio
    async def test_processar_lote_com_pendentes(self):
        """Deve processar todos os pendentes do lote."""
        from app.services.validacao_telefone import processar_lote_validacao

        with patch("app.services.validacao_telefone.buscar_telefones_pendentes") as mock_buscar:
            mock_buscar.return_value = [
                {"id": "1", "telefone": "5511111111111"},
                {"id": "2", "telefone": "5522222222222"},
            ]

            with patch("app.services.validacao_telefone.validar_telefone") as mock_validar:
                mock_validar.side_effect = ["validado", "invalido"]

                stats = await processar_lote_validacao()

                assert stats["processados"] == 2
                assert stats["validados"] == 1
                assert stats["invalidos"] == 1


class TestBuscarTelefonesPendentes:
    """Testes para busca de telefones pendentes."""

    @pytest.mark.asyncio
    async def test_buscar_telefones_pendentes(self):
        """Deve retornar lista de telefones pendentes."""
        from app.services.validacao_telefone import buscar_telefones_pendentes

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {"id": "1", "telefone": "5511111111111", "nome": "Dr. João"},
                {"id": "2", "telefone": "5522222222222", "nome": "Dra. Maria"},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.not_.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_telefones_pendentes(limit=10)

            assert len(resultado) == 2
            assert resultado[0]["telefone"] == "5511111111111"


class TestMarcarComoValidando:
    """Testes para marcar_como_validando."""

    @pytest.mark.asyncio
    async def test_marca_se_pendente(self):
        """Deve marcar como validando se status é pendente."""
        from app.services.validacao_telefone import marcar_como_validando

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "1"}]  # Retornou algo = atualizou

            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await marcar_como_validando("uuid-123")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_nao_marca_se_outro_estado(self):
        """Deve retornar False se já está em outro estado."""
        from app.services.validacao_telefone import marcar_como_validando

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []  # Não retornou nada = não atualizou

            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await marcar_como_validando("uuid-123")

            assert resultado is False


class TestAtualizarStatusTelefone:
    """Testes para atualizar_status_telefone."""

    @pytest.mark.asyncio
    async def test_atualiza_status_validado(self):
        """Deve atualizar status para validado."""
        from app.services.validacao_telefone import atualizar_status_telefone

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "1"}]

            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await atualizar_status_telefone("uuid-123", "validado")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_atualiza_status_com_erro(self):
        """Deve incluir mensagem de erro quando fornecida."""
        from app.services.validacao_telefone import atualizar_status_telefone

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "1"}]

            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await atualizar_status_telefone("uuid-123", "erro", erro="timeout")

            assert resultado is True
            # Verificar que update foi chamado com erro
            call_args = mock_supabase.table.return_value.update.call_args
            assert "telefone_erro" in call_args[0][0]


class TestObterEstatisticasValidacao:
    """Testes para obter_estatisticas_validacao."""

    @pytest.mark.asyncio
    async def test_obter_estatisticas_via_rpc(self):
        """Deve retornar estatísticas via RPC."""
        from app.services.validacao_telefone import obter_estatisticas_validacao

        with patch("app.services.validacao_telefone.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {"status": "validado", "count": 100},
                {"status": "invalido", "count": 50},
                {"status": "pendente", "count": 200},
            ]

            mock_supabase.rpc.return_value.execute.return_value = mock_execute

            resultado = await obter_estatisticas_validacao()

            assert resultado["validado"] == 100
            assert resultado["invalido"] == 50
            assert resultado["pendente"] == 200


class TestCheckNumberStatus:
    """Testes para evolution.check_number_status."""

    @pytest.mark.asyncio
    async def test_check_number_existe(self):
        """Deve retornar exists=True para número válido."""
        from app.services.whatsapp import EvolutionClient

        with patch("app.services.whatsapp.settings") as mock_settings:
            mock_settings.EVOLUTION_API_URL = "http://test"
            mock_settings.EVOLUTION_API_KEY = "test-key"
            mock_settings.EVOLUTION_INSTANCE = "test-instance"

            client = EvolutionClient()

            with patch("httpx.AsyncClient.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = [
                    {"exists": True, "jid": "5511999999999@s.whatsapp.net", "number": "5511999999999"}
                ]

                # Configurar context manager
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post.return_value = mock_response

                with patch("httpx.AsyncClient", return_value=mock_client):
                    resultado = await client.check_number_status("5511999999999")

                    assert resultado["exists"] is True
                    assert resultado["jid"] == "5511999999999@s.whatsapp.net"

    @pytest.mark.asyncio
    async def test_check_number_nao_existe(self):
        """Deve retornar exists=False para número inválido."""
        from app.services.whatsapp import EvolutionClient

        with patch("app.services.whatsapp.settings") as mock_settings:
            mock_settings.EVOLUTION_API_URL = "http://test"
            mock_settings.EVOLUTION_API_KEY = "test-key"
            mock_settings.EVOLUTION_INSTANCE = "test-instance"

            client = EvolutionClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"exists": False, "number": "5511999999999"}
            ]

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response

            with patch("httpx.AsyncClient", return_value=mock_client):
                resultado = await client.check_number_status("5511999999999")

                assert resultado["exists"] is False

    @pytest.mark.asyncio
    async def test_check_number_normaliza_telefone(self):
        """Deve normalizar número adicionando 55 se necessário."""
        from app.services.whatsapp import EvolutionClient

        with patch("app.services.whatsapp.settings") as mock_settings:
            mock_settings.EVOLUTION_API_URL = "http://test"
            mock_settings.EVOLUTION_API_KEY = "test-key"
            mock_settings.EVOLUTION_INSTANCE = "test-instance"

            client = EvolutionClient()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"exists": True, "jid": "5511999999999@s.whatsapp.net", "number": "5511999999999"}
            ]

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response

            with patch("httpx.AsyncClient", return_value=mock_client):
                # Número sem 55
                resultado = await client.check_number_status("11999999999")

                assert resultado["exists"] is True
                # Verificar que o request foi feito com número normalizado
                call_args = mock_client.post.call_args
                assert "5511999999999" in str(call_args)


class TestHealthEndpointTelefones:
    """Testes para endpoint /health/telefones."""

    @pytest.mark.asyncio
    async def test_endpoint_retorna_estatisticas(self):
        """Endpoint deve retornar estatísticas de validação."""
        from app.api.routes.health import telefones_validation_status

        with patch("app.services.validacao_telefone.obter_estatisticas_validacao") as mock_stats:
            mock_stats.return_value = {
                "validado": 100,
                "invalido": 50,
                "pendente": 200,
                "erro": 10,
            }

            resultado = await telefones_validation_status()

            assert "stats" in resultado
            assert resultado["total"] == 360
            assert resultado["taxa_validos_pct"] > 0
            assert resultado["backlog_pendentes"] == 200
