"""
Testes do ResponseHandler.

Sprint 31 - S31.E2.7
"""
import pytest

from app.services.julia.response_handler import (
    ResponseHandler,
    get_response_handler,
    resposta_parece_incompleta,
    PADROES_RESPOSTA_INCOMPLETA,
)
from app.services.julia.models import GenerationResult


class TestResponseHandler:
    """Testes da classe ResponseHandler."""

    @pytest.fixture
    def handler(self):
        """Cria handler para testes."""
        return ResponseHandler()

    def test_resposta_vazia_nao_incompleta(self, handler):
        """Resposta vazia não deve ser marcada como incompleta."""
        assert handler.resposta_incompleta("") is False
        assert handler.resposta_incompleta(None) is False

    def test_resposta_tool_use_nao_incompleta(self, handler):
        """Se parou por tool_use, não é incompleta."""
        assert handler.resposta_incompleta(
            "Vou verificar:", stop_reason="tool_use"
        ) is False

    def test_resposta_com_dois_pontos_incompleta(self, handler):
        """Resposta terminando em : é incompleta."""
        assert handler.resposta_incompleta("Vou verificar o que temos:") is True
        assert handler.resposta_incompleta("Deixa eu ver as opções:") is True

    def test_resposta_com_reticencias_incompleta(self, handler):
        """Resposta terminando em ... é incompleta."""
        assert handler.resposta_incompleta("Deixa eu ver...") is True

    def test_resposta_com_padrao_incompleto(self, handler):
        """Resposta com padrões de continuação é incompleta."""
        assert handler.resposta_incompleta("vou verificar") is True
        assert handler.resposta_incompleta("deixa eu ver") is True
        assert handler.resposta_incompleta("um momento") is True
        assert handler.resposta_incompleta("vou buscar") is True

    def test_resposta_normal_completa(self, handler):
        """Resposta normal não deve ser incompleta."""
        assert handler.resposta_incompleta("Olá! Tudo bem?") is False
        assert handler.resposta_incompleta("Temos 3 vagas disponíveis!") is False

    def test_processar_resultado_llm(self, handler):
        """Deve processar resultado do LLM corretamente."""
        resultado = {
            "text": "Resposta",
            "tool_use": [],
            "stop_reason": "end_turn",
        }
        gen_result = handler.processar_resultado_llm(resultado)

        assert gen_result.text == "Resposta"
        assert gen_result.tool_calls == []
        assert gen_result.stop_reason == "end_turn"
        assert gen_result.needs_retry is False

    def test_processar_resultado_incompleto(self, handler):
        """Deve marcar needs_retry para resposta incompleta."""
        resultado = {
            "text": "Vou verificar:",
            "tool_use": [],
            "stop_reason": "end_turn",
        }
        gen_result = handler.processar_resultado_llm(resultado)
        assert gen_result.needs_retry is True

    def test_processar_resultado_com_tools_nao_retry(self, handler):
        """Não deve marcar retry se tem tool calls."""
        resultado = {
            "text": "Vou verificar:",
            "tool_use": [{"id": "1", "name": "test"}],
            "stop_reason": "tool_use",
        }
        gen_result = handler.processar_resultado_llm(resultado)
        assert gen_result.needs_retry is False

    def test_extrair_texto_final(self, handler):
        """Deve extrair texto final."""
        result = GenerationResult(text="Texto final")
        assert handler.extrair_texto_final(result) == "Texto final"

    def test_extrair_texto_final_com_fallback(self, handler):
        """Deve usar fallback se texto vazio."""
        result = GenerationResult(text="")
        assert handler.extrair_texto_final(result, "Fallback") == "Fallback"

    def test_criar_resposta_final(self, handler):
        """Deve criar resposta final."""
        resp = handler.criar_resposta_final(
            texto="Oi!",
            tool_calls_executadas=1,
            conhecimento_usado=True,
        )
        assert resp.texto == "Oi!"
        assert resp.tool_calls_executadas == 1
        assert resp.conhecimento_usado is True

    def test_montar_prompt_retry(self, handler):
        """Deve montar prompt de retry."""
        prompt = handler.montar_prompt_retry()
        assert "buscar_vagas" in prompt
        assert "ferramenta" in prompt.lower()

    def test_deve_forcar_retry_true(self, handler):
        """Deve retornar True quando precisa retry."""
        result = GenerationResult(text="Vou verificar:", needs_retry=True)
        assert handler.deve_forcar_retry(result, houve_tool_use=False) is True

    def test_deve_forcar_retry_false_com_tool_use(self, handler):
        """Não deve retry se já houve tool use."""
        result = GenerationResult(text="Vou verificar:", needs_retry=True)
        assert handler.deve_forcar_retry(result, houve_tool_use=True) is False

    def test_deve_forcar_retry_false_max_retries(self, handler):
        """Não deve retry se atingiu máximo."""
        result = GenerationResult(text="Vou verificar:", needs_retry=True)
        assert handler.deve_forcar_retry(result, houve_tool_use=False, retry_count=5) is False


class TestFuncoesCompatibilidade:
    """Testes das funções de compatibilidade."""

    def test_resposta_parece_incompleta_funcao(self):
        """Função de compatibilidade deve funcionar."""
        assert resposta_parece_incompleta("Vou verificar:") is True
        assert resposta_parece_incompleta("Olá!") is False

    def test_get_response_handler_singleton(self):
        """Deve retornar a mesma instância."""
        h1 = get_response_handler()
        h2 = get_response_handler()
        assert h1 is h2


class TestPadroesIncompletos:
    """Testes dos padrões de resposta incompleta."""

    def test_padroes_existem(self):
        """Deve ter padrões definidos."""
        assert len(PADROES_RESPOSTA_INCOMPLETA) > 0
        assert ":" in PADROES_RESPOSTA_INCOMPLETA
        assert "..." in PADROES_RESPOSTA_INCOMPLETA
