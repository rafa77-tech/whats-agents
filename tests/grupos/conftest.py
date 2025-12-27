"""
Fixtures para testes do módulo de grupos.

Sprint 14 - E02
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.schemas.mensagem import MensagemRecebida


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase para testes de grupos."""
    with patch("app.services.grupos.ingestor.supabase") as mock:
        # Configurar chain de métodos
        mock.table.return_value = mock
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.eq.return_value = mock
        mock.execute.return_value = MagicMock(data=[])
        mock.rpc.return_value = mock

        yield mock


@pytest.fixture
def mensagem_texto_grupo():
    """Mensagem de texto válida de grupo."""
    return MensagemRecebida(
        telefone="5511999999999",
        message_id="ABC123",
        from_me=False,
        tipo="texto",
        texto="Plantão disponível Hospital São Luiz, dia 28/12, noturno, R$ 1.800",
        nome_contato="Dr. João Silva",
        timestamp=datetime.now(),
        is_grupo=True,
    )


@pytest.fixture
def mensagem_imagem_grupo():
    """Mensagem de imagem de grupo."""
    return MensagemRecebida(
        telefone="5511999999999",
        message_id="IMG123",
        from_me=False,
        tipo="imagem",
        texto=None,
        nome_contato="Escalista",
        timestamp=datetime.now(),
        is_grupo=True,
    )


@pytest.fixture
def mensagem_curta_grupo():
    """Mensagem curta de grupo (será ignorada)."""
    return MensagemRecebida(
        telefone="5511999999999",
        message_id="SHORT123",
        from_me=False,
        tipo="texto",
        texto="Ok",
        nome_contato="Fulano",
        timestamp=datetime.now(),
        is_grupo=True,
    )


@pytest.fixture
def dados_webhook_grupo():
    """Dados brutos do webhook para mensagem de grupo."""
    return {
        "key": {
            "remoteJid": "120363123456789@g.us",
            "participant": "5511999999999@s.whatsapp.net",
            "id": "ABC123",
            "fromMe": False
        },
        "pushName": "Dr. João Silva",
        "messageTimestamp": 1703779200,
        "message": {
            "conversation": "Plantão disponível Hospital São Luiz"
        },
        "groupName": "Vagas Médicas ABC"
    }


@pytest.fixture
def grupo_id():
    """UUID de grupo para testes."""
    return uuid4()


@pytest.fixture
def contato_id():
    """UUID de contato para testes."""
    return uuid4()


@pytest.fixture
def mensagem_id():
    """UUID de mensagem para testes."""
    return uuid4()
