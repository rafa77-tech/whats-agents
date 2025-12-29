"""
Testes de arquitetura para garantir soberania dos guardrails.

Sprint 18.1 P0: Bloqueia imports diretos da Evolution API fora de outbound.py

Estes testes garantem que TODAS as mensagens outbound passam pelo wrapper
send_outbound_message em app/services/outbound.py.
"""
import os
import re
import ast
from pathlib import Path
from typing import List, Tuple

import pytest


# Arquivos permitidos a importar diretamente da Evolution
ALLOWED_EVOLUTION_IMPORTERS = {
    "app/services/outbound.py",  # Wrapper oficial
    "app/services/whatsapp/__init__.py",  # Re-export
    "app/services/whatsapp/evolution.py",  # Implementação
    "app/services/whatsapp.py",  # Implementação legada
    # Monitoramento e health (não enviam mensagens)
    "app/services/monitor_whatsapp.py",  # Monitoramento de conexão
    "app/api/routes/health.py",  # Health check
    "app/api/routes/test_whatsapp.py",  # Endpoint de teste
    # Pipeline pre-processors (apenas mostrar_online, não envio)
    "app/pipeline/pre_processors.py",
    # Grupos (ingestão, não envio outbound)
    "app/services/grupos/ingestor.py",
    # Agente (fallback legado com warning - TODO: remover)
    "app/services/agente.py",
    # Testes podem importar para mocking
    "tests/",
}

# Padrões de import proibidos
FORBIDDEN_PATTERNS = [
    # Imports diretos da Evolution
    r"from app\.services\.whatsapp import evolution",
    r"from app\.services\.whatsapp\.evolution import",
    r"from app\.services\.whatsapp import.*enviar_mensagem",
    r"from app\.services\.whatsapp import.*enviar_com_digitacao",
    # Uso direto de evolution.enviar_mensagem
    r"evolution\.enviar_mensagem\(",
    # Uso direto de enviar_com_digitacao fora do outbound.py
    r"await\s+enviar_com_digitacao\(",
]

# Mensagem de erro
ERROR_MESSAGE = """
ARQUITETURA VIOLADA: Import direto da Evolution API detectado!

Arquivo: {file}
Linha {line}: {content}

SOLUÇÃO: Use send_outbound_message de app/services/outbound.py

Exemplo:
    from app.services.outbound import send_outbound_message, criar_contexto_reply

    ctx = criar_contexto_reply(cliente_id=..., conversation_id=..., ...)
    result = await send_outbound_message(telefone, texto, ctx)

Motivo: Todos os envios devem passar pelo wrapper para garantir verificação
de guardrails (opted_out, cooling_off, contact_cap, etc).

Documentação: docs/GUARDRAILS.md
"""


def is_allowed_file(file_path: str) -> bool:
    """Verifica se o arquivo está na lista de permitidos."""
    for allowed in ALLOWED_EVOLUTION_IMPORTERS:
        if allowed.endswith("/"):
            # É um diretório
            if file_path.startswith(allowed):
                return True
        else:
            # É um arquivo específico
            if file_path == allowed:
                return True
    return False


def find_violations_in_file(file_path: Path) -> List[Tuple[int, str]]:
    """Encontra violações de arquitetura em um arquivo."""
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                violations.append((line_num, line.strip()))
                break

    return violations


def get_python_files(base_dir: Path) -> List[Path]:
    """Retorna todos os arquivos Python no diretório."""
    return list(base_dir.rglob("*.py"))


class TestGuardrailArchitecture:
    """Testes de arquitetura para garantir soberania dos guardrails."""

    def test_no_direct_evolution_imports(self):
        """
        Verifica que nenhum arquivo fora dos permitidos importa diretamente
        da Evolution API.

        Este teste garante que TODAS as mensagens outbound passam pelo
        wrapper send_outbound_message que verifica guardrails.
        """
        base_dir = Path(__file__).parent.parent / "app"
        all_violations = []

        for py_file in get_python_files(base_dir):
            # Converter para path relativo
            relative_path = str(py_file.relative_to(base_dir.parent))

            # Pular arquivos permitidos
            if is_allowed_file(relative_path):
                continue

            # Buscar violações
            violations = find_violations_in_file(py_file)

            for line_num, line_content in violations:
                all_violations.append({
                    "file": relative_path,
                    "line": line_num,
                    "content": line_content,
                })

        if all_violations:
            # Formatar mensagem de erro
            messages = []
            for v in all_violations:
                messages.append(ERROR_MESSAGE.format(**v))

            pytest.fail("\n".join(messages))

    def test_outbound_wrapper_exists(self):
        """Verifica que o wrapper outbound.py existe e tem as funções corretas."""
        outbound_path = Path(__file__).parent.parent / "app/services/outbound.py"
        assert outbound_path.exists(), "app/services/outbound.py não encontrado!"

        content = outbound_path.read_text()

        # Verificar função principal
        assert "async def send_outbound_message" in content, \
            "send_outbound_message não encontrado em outbound.py"

        # Verificar helpers de contexto
        assert "def criar_contexto_reply" in content, \
            "criar_contexto_reply não encontrado em outbound.py"
        assert "def criar_contexto_campanha" in content, \
            "criar_contexto_campanha não encontrado em outbound.py"
        assert "def criar_contexto_followup" in content, \
            "criar_contexto_followup não encontrado em outbound.py"

    def test_outbound_uses_guardrails(self):
        """Verifica que outbound.py usa o módulo de guardrails."""
        outbound_path = Path(__file__).parent.parent / "app/services/outbound.py"
        content = outbound_path.read_text()

        assert "from app.services.guardrails import" in content, \
            "outbound.py deve importar de guardrails"
        assert "check_outbound_guardrails" in content, \
            "outbound.py deve chamar check_outbound_guardrails"

    def test_guardrails_module_exists(self):
        """Verifica que o módulo de guardrails existe."""
        guardrails_path = Path(__file__).parent.parent / "app/services/guardrails/__init__.py"
        assert guardrails_path.exists(), "app/services/guardrails/__init__.py não encontrado!"

        check_path = Path(__file__).parent.parent / "app/services/guardrails/check.py"
        assert check_path.exists(), "app/services/guardrails/check.py não encontrado!"


class TestGuardrailCallSites:
    """Testes para verificar que call sites usam o wrapper corretamente."""

    def test_pipeline_uses_wrapper(self):
        """Verifica que o pipeline usa send_outbound_message."""
        pipeline_path = Path(__file__).parent.parent / "app/pipeline/post_processors.py"
        content = pipeline_path.read_text()

        # Deve usar criar_contexto_reply
        assert "criar_contexto_reply" in content, \
            "Pipeline deve usar criar_contexto_reply para envios"

    def test_campanha_uses_wrapper(self):
        """Verifica que campanhas usam send_outbound_message."""
        campanha_path = Path(__file__).parent.parent / "app/services/campanha.py"
        content = campanha_path.read_text()

        # Deve usar criar_contexto_campanha ou send_outbound_message
        assert "criar_contexto_campanha" in content or "send_outbound_message" in content, \
            "Campanhas devem usar wrapper de outbound"

    def test_handoff_uses_wrapper(self):
        """Verifica que handoff usa send_outbound_message."""
        handoff_path = Path(__file__).parent.parent / "app/services/handoff/flow.py"
        content = handoff_path.read_text()

        # Deve usar send_outbound_message
        assert "send_outbound_message" in content, \
            "Handoff deve usar send_outbound_message"

        # Não deve importar evolution diretamente
        assert "from app.services.whatsapp import evolution" not in content, \
            "Handoff não deve importar evolution diretamente"
