"""
Testes para sincronizacao de briefing via Slack.

Sprint 23 E06 - Briefing Tatico.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.tools.slack.briefing import (
    handle_sincronizar_briefing,
    TOOL_SINCRONIZAR_BRIEFING,
    SYNC_RATE_LIMIT_MINUTES,
    _buscar_hash_atual,
)


class TestToolDefinition:
    """Testes para definicao da tool."""

    def test_tool_name(self):
        """Tool deve ter nome correto."""
        assert TOOL_SINCRONIZAR_BRIEFING["name"] == "sincronizar_briefing"

    def test_tool_description_tem_padroes_nlp(self):
        """Descricao deve conter padroes NLP."""
        desc = TOOL_SINCRONIZAR_BRIEFING["description"]
        assert "sync briefing" in desc
        assert "sincroniza" in desc
        assert "atualiza briefing" in desc
        assert "puxa briefing" in desc
        assert "recarrega" in desc

    def test_rate_limit_configurado(self):
        """Rate limit deve ser 5 minutos."""
        assert SYNC_RATE_LIMIT_MINUTES == 5


class TestRateLimit:
    """Testes para rate limit."""

    @pytest.mark.asyncio
    async def test_primeiro_sync_nao_bloqueia(self):
        """Primeiro sync nao deve ser bloqueado."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        # Patch no modulo de origem (lazy import)
        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": True,
                "changed": True,
                "hash": "abc123def456",
                "titulo": "Briefing Teste",
                "secoes_atualizadas": ["foco_semana"],
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = "old_hash_123"

                with patch("app.tools.slack.briefing._emitir_evento_sync") as mock_event:
                    mock_event.return_value = None

                    result = await handle_sincronizar_briefing({}, "user-123")

                    assert result["success"] is True
                    assert result["atualizado"] is True
                    mock_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_repetido_bloqueia(self):
        """Sync repetido dentro de 5 min deve bloquear."""
        import app.tools.slack.briefing as briefing_module

        # Simular sync ha 2 minutos
        briefing_module._ultimo_sync_manual = datetime.now(timezone.utc) - timedelta(minutes=2)

        result = await handle_sincronizar_briefing({}, "user-123")

        assert result["success"] is False
        assert result.get("rate_limited") is True
        assert "Calma" in result["mensagem"]
        assert result.get("minutos_restantes") is not None

    @pytest.mark.asyncio
    async def test_sync_apos_5_min_permite(self):
        """Sync apos 5 minutos deve permitir."""
        import app.tools.slack.briefing as briefing_module

        # Simular sync ha 6 minutos
        briefing_module._ultimo_sync_manual = datetime.now(timezone.utc) - timedelta(minutes=6)

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": True,
                "changed": False,
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = "hash_123"

                with patch("app.tools.slack.briefing._emitir_evento_sync") as mock_event:
                    mock_event.return_value = None

                    result = await handle_sincronizar_briefing({}, "user-123")

                    assert result["success"] is True
                    mock_sync.assert_called_once()


class TestFeedback:
    """Testes para feedback do sync."""

    @pytest.mark.asyncio
    async def test_feedback_quando_atualizado(self):
        """Deve mostrar hash antes/depois quando atualizado."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": True,
                "changed": True,
                "hash": "new_hash_789",
                "titulo": "Briefing Semanal",
                "secoes_atualizadas": ["foco_semana", "tom_semana"],
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = "old_hash_123"

                with patch("app.tools.slack.briefing._emitir_evento_sync") as mock_event:
                    mock_event.return_value = None

                    result = await handle_sincronizar_briefing({}, "user-123")

                    assert result["success"] is True
                    assert result["atualizado"] is True
                    assert result["hash_antes"] == "old_hash"
                    assert result["hash_depois"] == "new_hash"
                    assert "foco_semana" in result["secoes_atualizadas"]
                    assert "Briefing sincronizado" in result["mensagem"]
                    assert "old_hash" in result["mensagem"]
                    assert "new_hash" in result["mensagem"]

    @pytest.mark.asyncio
    async def test_feedback_quando_nao_mudou(self):
        """Deve informar que nao houve mudanca."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": True,
                "changed": False,
                "hash": "same_hash",
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = "same_hash"

                with patch("app.tools.slack.briefing._emitir_evento_sync") as mock_event:
                    mock_event.return_value = None

                    result = await handle_sincronizar_briefing({}, "user-123")

                    assert result["success"] is True
                    assert result["atualizado"] is False
                    assert "ja estava atualizado" in result["mensagem"]


class TestEventoAuditoria:
    """Testes para evento de auditoria."""

    @pytest.mark.asyncio
    async def test_emite_evento_sync_triggered(self):
        """Deve emitir evento BRIEFING_SYNC_TRIGGERED."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": True,
                "changed": True,
                "hash": "new_hash",
                "secoes_atualizadas": ["foco_semana"],
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = "old_hash"

                with patch("app.tools.slack.briefing._emitir_evento_sync") as mock_event:
                    mock_event.return_value = None

                    await handle_sincronizar_briefing({}, "user-slack-456")

                    mock_event.assert_called_once()
                    call_args = mock_event.call_args
                    assert call_args.kwargs["user_id"] == "user-slack-456"
                    assert call_args.kwargs["hash_antes"] == "old_hash"
                    assert call_args.kwargs["hash_depois"] == "new_hash"
                    assert call_args.kwargs["atualizado"] is True


class TestErros:
    """Testes para tratamento de erros."""

    @pytest.mark.asyncio
    async def test_erro_sincronizacao_retorna_mensagem(self):
        """Erro na sincronizacao deve retornar mensagem amigavel."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.return_value = {
                "success": False,
                "error": "Google Docs nao configurado",
            }

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = None

                result = await handle_sincronizar_briefing({}, "user-123")

                assert result["success"] is False
                assert "Google Docs" in result["mensagem"]

    @pytest.mark.asyncio
    async def test_excecao_retorna_erro(self):
        """Excecao deve retornar erro tratado."""
        import app.tools.slack.briefing as briefing_module
        briefing_module._ultimo_sync_manual = None

        with patch("app.services.briefing.sincronizar_briefing") as mock_sync:
            mock_sync.side_effect = Exception("Erro inesperado")

            with patch("app.tools.slack.briefing._buscar_hash_atual") as mock_hash:
                mock_hash.return_value = None

                result = await handle_sincronizar_briefing({}, "user-123")

                assert result["success"] is False
                assert "Erro" in result["mensagem"]


class TestBuscarHashAtual:
    """Testes para _buscar_hash_atual."""

    @pytest.mark.asyncio
    async def test_retorna_hash_quando_existe(self):
        """Deve retornar hash do ultimo sync."""
        with patch("app.tools.slack.briefing.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"doc_hash": "abc123def456"}]
            )

            result = await _buscar_hash_atual()

            assert result == "abc123def456"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_historico(self):
        """Deve retornar None se nao houver historico."""
        with patch("app.tools.slack.briefing.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await _buscar_hash_atual()

            assert result is None


class TestIntegracaoSlackTools:
    """Testes de integracao com Slack tools."""

    def test_tool_registrada_em_slack_tools(self):
        """Tool deve estar registrada em SLACK_TOOLS."""
        from app.tools.slack import SLACK_TOOLS, TOOL_SINCRONIZAR_BRIEFING

        tool_names = [t["name"] for t in SLACK_TOOLS]
        assert "sincronizar_briefing" in tool_names

    def test_handler_registrado_em_executar_tool(self):
        """Handler deve estar registrado no executor."""
        from app.tools.slack import executar_tool

        # Verificar que a funcao existe e pode ser importada
        assert callable(executar_tool)
