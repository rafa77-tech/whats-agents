"""
Testes para mensagens de erro amigáveis.
"""
import pytest
from app.services.error_handler import obter_mensagem_erro

TIPOS_ERRO = ["llm_timeout", "llm_error", "whatsapp_error", "generico"]


@pytest.mark.parametrize("tipo", TIPOS_ERRO)
def test_mensagem_erro_existe(tipo):
    """Cada tipo de erro tem mensagem definida."""
    msg = obter_mensagem_erro(tipo)
    assert msg is not None
    assert len(msg) > 10


@pytest.mark.parametrize("tipo", TIPOS_ERRO)
def test_mensagem_erro_informal(tipo):
    """Mensagens de erro mantêm tom informal."""
    msg = obter_mensagem_erro(tipo)
    # Não deve ter linguagem formal
    assert "prezado" not in msg.lower()
    assert "senhores" not in msg.lower()
    assert "atenciosamente" not in msg.lower()
    # Deve ter tom amigável
    assert any(c in msg for c in ["?", "!", "😅", "👍", "opa", "eita", "ops"])


def test_mensagens_erro_variam():
    """Mensagens de erro não são sempre iguais."""
    msgs = [obter_mensagem_erro("generico") for _ in range(20)]
    # Deve ter pelo menos 2 variações
    assert len(set(msgs)) >= 2


def test_tipo_inexistente_usa_generico():
    """Tipo de erro inexistente usa mensagem genérica."""
    msg = obter_mensagem_erro("tipo_inexistente")
    assert msg is not None
    assert len(msg) > 10

