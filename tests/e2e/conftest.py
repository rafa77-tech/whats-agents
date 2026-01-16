"""
Configuração para testes E2E.

Usa mocks de serviços externos e fixtures reutilizáveis.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.fixture
def mock_evolution_api():
    """Mock da Evolution API."""
    with patch("app.services.whatsapp.evolution.enviar_mensagem") as mock:
        mock.return_value = {"success": True, "message_id": f"msg-{uuid4()}"}
        yield mock


@pytest.fixture
def mock_slack():
    """Mock do Slack."""
    with patch("app.services.slack.enviar_slack") as mock:
        mock.return_value = {"ok": True, "ts": "1234567890.123456"}
        yield mock


@pytest.fixture
def mock_llm():
    """Mock do LLM (Claude)."""
    with patch("app.services.llm.chamar_llm") as mock:
        mock.return_value = "Resposta do LLM"
        yield mock


@pytest.fixture
def mock_supabase():
    """Mock do Supabase para testes sem banco real."""
    with patch("app.services.supabase.supabase") as mock:
        yield mock


@pytest.fixture
def campanha_discovery_data():
    """Dados de campanha discovery para testes."""
    return {
        "id": str(uuid4()),
        "nome_template": "test_discovery",
        "tipo_campanha": "discovery",
        "objetivo": "Conhecer médicos e entender suas preferências",
        "regras": [
            "Nunca mencionar vagas ou oportunidades",
            "Não falar de valores",
            "Foco em conhecer o médico"
        ],
        "pode_ofertar": False,
        "status": "ativa",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def campanha_oferta_data():
    """Dados de campanha oferta para testes."""
    return {
        "id": str(uuid4()),
        "nome_template": "test_oferta",
        "tipo_campanha": "oferta",
        "objetivo": "Ofertar vagas disponíveis",
        "regras": [
            "Consultar sistema antes de ofertar",
            "Nunca inventar vagas"
        ],
        "escopo_vagas": {},
        "pode_ofertar": True,
        "status": "ativa",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def medico_data():
    """Dados de médico para testes."""
    return {
        "id": str(uuid4()),
        "primeiro_nome": "Dr. Teste E2E",
        "telefone": "5511999999999",
        "especialidade_nome": "Cardiologia",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def conversa_data(medico_data):
    """Dados de conversa para testes."""
    return {
        "id": str(uuid4()),
        "cliente_id": medico_data["id"],
        "status": "ativa",
        "controlled_by": "julia",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def hospital_data():
    """Dados de hospital para testes."""
    return {
        "id": str(uuid4()),
        "nome": "Hospital E2E Test",
        "cidade": "São Paulo",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def vaga_data(hospital_data):
    """Dados de vaga para testes."""
    return {
        "id": str(uuid4()),
        "hospital_id": hospital_data["id"],
        "data": (datetime.now() + timedelta(days=10)).date().isoformat(),
        "valor": 2500,
        "status": "aberta",
        "created_at": datetime.utcnow().isoformat()
    }
