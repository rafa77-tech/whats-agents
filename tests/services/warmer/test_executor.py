"""Testes do Warmup Executor.

Valida que atividades de warmup são executadas corretamente,
enviando mensagens reais via enviar_via_chip.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.services.warmer.executor import (
    executar_atividade,
    _executar_conversa_par,
    _executar_marcar_lido,
    _executar_entrar_grupo,
    _executar_mensagem_grupo,
    _executar_atualizar_perfil,
    _executar_enviar_midia,
    _registrar_interacao,
    _gerar_mensagem_simples,
)
from app.services.warmer.scheduler import AtividadeAgendada, TipoAtividade
from app.services.warmer.conversation_generator import MensagemGerada, TipoMidia
from app.services.warmer.pairing_engine import ParInfo, ChipInfo
from app.services.whatsapp_providers.base import MessageResult


CHIP_ID = "aaaaaaaa-1111-2222-3333-444444444444"
PAR_ID = "bbbbbbbb-1111-2222-3333-444444444444"


def _msg_gerada(texto: str = "oi, tudo bem?") -> MensagemGerada:
    """Helper para criar MensagemGerada de teste."""
    return MensagemGerada(texto=texto, tipo_midia=TipoMidia.TEXTO)


def _chip_info(chip_id: str = CHIP_ID, telefone: str = "5511999990001") -> ChipInfo:
    """Helper para criar ChipInfo de teste."""
    return ChipInfo(
        id=chip_id,
        telefone=telefone,
        ddd=11,
        fase_warmup="setup",
        trust_score=50,
        msgs_enviadas_hoje=2,
        msgs_recebidas_hoje=1,
    )


def _par_info() -> ParInfo:
    """Helper para criar ParInfo de teste."""
    return ParInfo(
        chip_a=_chip_info(CHIP_ID, "5511999990001"),
        chip_b=_chip_info(PAR_ID, "5511999990002"),
        score_compatibilidade=85.0,
        motivo="mesmo_ddd",
    )


@pytest.fixture
def chip_evolution():
    """Chip Evolution conectado."""
    return {
        "id": CHIP_ID,
        "telefone": "5511999990001",
        "instance_name": "julia-01",
        "evolution_connected": True,
        "fase_warmup": "setup",
        "provider": "evolution",
    }


@pytest.fixture
def chip_zapi():
    """Chip Z-API (não verifica evolution_connected)."""
    return {
        "id": CHIP_ID,
        "telefone": "5511999990001",
        "instance_name": "julia-zapi-01",
        "evolution_connected": False,
        "fase_warmup": "setup",
        "provider": "z-api",
    }


@pytest.fixture
def chip_desconectado():
    """Chip Evolution desconectado."""
    return {
        "id": CHIP_ID,
        "telefone": "5511999990001",
        "instance_name": "julia-01",
        "evolution_connected": False,
        "fase_warmup": "setup",
        "provider": "evolution",
    }


@pytest.fixture
def atividade_conversa():
    """Atividade de conversa_par."""
    return AtividadeAgendada(
        id="act-001",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.CONVERSA_PAR,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_marcar_lido():
    return AtividadeAgendada(
        id="act-002",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.MARCAR_LIDO,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_entrar_grupo():
    return AtividadeAgendada(
        id="act-003",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.ENTRAR_GRUPO,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_mensagem_grupo():
    return AtividadeAgendada(
        id="act-004",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.MENSAGEM_GRUPO,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_atualizar_perfil():
    return AtividadeAgendada(
        id="act-005",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.ATUALIZAR_PERFIL,
        horario=datetime.now(timezone.utc),
    )


@pytest.fixture
def atividade_enviar_midia():
    return AtividadeAgendada(
        id="act-006",
        chip_id=CHIP_ID,
        tipo=TipoAtividade.ENVIAR_MIDIA,
        horario=datetime.now(timezone.utc),
    )


# ── executar_atividade (dispatch) ──────────────────────────────


class TestExecutarAtividadeDispatch:
    """Testa o dispatch central para cada tipo de atividade."""

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_conversa_par")
    async def test_dispatch_conversa_par(
        self, mock_conv, mock_buscar, chip_evolution, atividade_conversa
    ):
        mock_buscar.return_value = chip_evolution
        mock_conv.return_value = True

        result = await executar_atividade(atividade_conversa)

        assert result is True
        mock_conv.assert_awaited_once_with(chip_evolution, atividade_conversa)

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_marcar_lido")
    async def test_dispatch_marcar_lido(
        self, mock_lido, mock_buscar, chip_evolution, atividade_marcar_lido
    ):
        mock_buscar.return_value = chip_evolution
        mock_lido.return_value = True

        result = await executar_atividade(atividade_marcar_lido)

        assert result is True
        mock_lido.assert_awaited_once_with(chip_evolution)

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_entrar_grupo")
    async def test_dispatch_entrar_grupo(
        self, mock_grupo, mock_buscar, chip_evolution, atividade_entrar_grupo
    ):
        mock_buscar.return_value = chip_evolution
        mock_grupo.return_value = True

        result = await executar_atividade(atividade_entrar_grupo)

        assert result is True
        mock_grupo.assert_awaited_once_with(chip_evolution)

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_mensagem_grupo")
    async def test_dispatch_mensagem_grupo(
        self, mock_msg, mock_buscar, chip_evolution, atividade_mensagem_grupo
    ):
        mock_buscar.return_value = chip_evolution
        mock_msg.return_value = True

        result = await executar_atividade(atividade_mensagem_grupo)

        assert result is True
        mock_msg.assert_awaited_once_with(chip_evolution)

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_atualizar_perfil")
    async def test_dispatch_atualizar_perfil(
        self, mock_perfil, mock_buscar, chip_evolution, atividade_atualizar_perfil
    ):
        mock_buscar.return_value = chip_evolution
        mock_perfil.return_value = True

        result = await executar_atividade(atividade_atualizar_perfil)

        assert result is True
        mock_perfil.assert_awaited_once_with(chip_evolution)

    @patch("app.services.warmer.executor._buscar_chip")
    @patch("app.services.warmer.executor._executar_enviar_midia")
    async def test_dispatch_enviar_midia(
        self, mock_midia, mock_buscar, chip_evolution, atividade_enviar_midia
    ):
        mock_buscar.return_value = chip_evolution
        mock_midia.return_value = True

        result = await executar_atividade(atividade_enviar_midia)

        assert result is True
        mock_midia.assert_awaited_once_with(chip_evolution, atividade_enviar_midia)

    @patch("app.services.warmer.executor._buscar_chip")
    async def test_chip_nao_encontrado_retorna_false(
        self, mock_buscar, atividade_conversa
    ):
        mock_buscar.return_value = None

        result = await executar_atividade(atividade_conversa)

        assert result is False

    @patch("app.services.warmer.executor._buscar_chip")
    async def test_exception_retorna_false(self, mock_buscar, atividade_conversa):
        mock_buscar.side_effect = RuntimeError("DB down")

        result = await executar_atividade(atividade_conversa)

        assert result is False


# ── _executar_conversa_par ─────────────────────────────────────


class TestExecutarConversaPar:
    """Testa envio real de mensagem entre pares."""

    @patch("app.services.warmer.executor._registrar_interacao")
    @patch("app.services.warmer.executor.enviar_via_chip")
    @patch("app.services.warmer.executor.gerar_mensagem_inicial")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_envia_mensagem_real_via_chip(
        self,
        mock_par,
        mock_gerar,
        mock_enviar,
        mock_registrar,
        chip_evolution,
        atividade_conversa,
    ):
        mock_par.return_value = _par_info()
        mock_gerar.return_value = _msg_gerada("oi, tudo bem?")
        mock_enviar.return_value = MessageResult(success=True, message_id="msg-123")

        result = await _executar_conversa_par(chip_evolution, atividade_conversa)

        assert result is True
        mock_enviar.assert_awaited_once_with(
            chip_evolution, "5511999990002", "oi, tudo bem?"
        )

    @patch("app.services.warmer.executor._registrar_interacao")
    @patch("app.services.warmer.executor.enviar_via_chip")
    @patch("app.services.warmer.executor.gerar_mensagem_inicial")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_fallback_mensagem_simples_quando_gerador_retorna_none(
        self,
        mock_par,
        mock_gerar,
        mock_enviar,
        mock_registrar,
        chip_evolution,
        atividade_conversa,
    ):
        mock_par.return_value = _par_info()
        mock_gerar.return_value = None
        mock_enviar.return_value = MessageResult(success=True)

        result = await _executar_conversa_par(chip_evolution, atividade_conversa)

        assert result is True
        # Verifica que usou uma mensagem simples (não None)
        call_args = mock_enviar.call_args
        assert call_args[0][2] is not None
        assert len(call_args[0][2]) > 0

    @patch("app.services.warmer.executor.enviar_via_chip")
    @patch("app.services.warmer.executor.gerar_mensagem_inicial")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_falha_envio_retorna_false(
        self,
        mock_par,
        mock_gerar,
        mock_enviar,
        chip_evolution,
        atividade_conversa,
    ):
        mock_par.return_value = _par_info()
        mock_gerar.return_value = _msg_gerada("oi!")
        mock_enviar.return_value = MessageResult(success=False, error="timeout")

        result = await _executar_conversa_par(chip_evolution, atividade_conversa)

        assert result is False

    @patch("app.services.warmer.executor._executar_marcar_lido")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_sem_par_faz_fallback_marcar_lido(
        self, mock_par, mock_lido, chip_evolution, atividade_conversa
    ):
        mock_par.return_value = None
        mock_lido.return_value = True

        result = await _executar_conversa_par(chip_evolution, atividade_conversa)

        assert result is True
        mock_lido.assert_awaited_once_with(chip_evolution)

    async def test_chip_evolution_desconectado_retorna_false(
        self, chip_desconectado, atividade_conversa
    ):
        result = await _executar_conversa_par(chip_desconectado, atividade_conversa)

        assert result is False

    @patch("app.services.warmer.executor.enviar_via_chip")
    @patch("app.services.warmer.executor.gerar_mensagem_inicial")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_chip_zapi_ignora_evolution_connected(
        self,
        mock_par,
        mock_gerar,
        mock_enviar,
        chip_zapi,
        atividade_conversa,
    ):
        """Z-API não depende de evolution_connected."""
        mock_par.return_value = _par_info()
        mock_gerar.return_value = _msg_gerada("oi!")
        mock_enviar.return_value = MessageResult(success=True)

        result = await _executar_conversa_par(chip_zapi, atividade_conversa)

        assert result is True
        mock_enviar.assert_awaited_once()

    @patch("app.services.warmer.executor.enviar_via_chip")
    @patch("app.services.warmer.executor.gerar_mensagem_inicial")
    @patch("app.services.warmer.executor.encontrar_par")
    async def test_passa_fase_warmup_para_gerador(
        self,
        mock_par,
        mock_gerar,
        mock_enviar,
        atividade_conversa,
    ):
        """Verifica que a fase do chip é passada ao gerador de mensagem."""
        chip = {
            "id": CHIP_ID,
            "telefone": "5511999990001",
            "evolution_connected": True,
            "fase_warmup": "expansao",
            "provider": "evolution",
        }
        mock_par.return_value = _par_info()
        mock_gerar.return_value = _msg_gerada("hey!")
        mock_enviar.return_value = MessageResult(success=True)

        await _executar_conversa_par(chip, atividade_conversa)

        mock_gerar.assert_called_once_with(fase_warmup="expansao")


# ── _executar_marcar_lido ──────────────────────────────────────


class TestExecutarMarcarLido:

    @patch("app.services.warmer.executor._registrar_interacao")
    async def test_registra_interacao_quando_conectado(
        self, mock_registrar, chip_evolution
    ):
        result = await _executar_marcar_lido(chip_evolution)

        assert result is True
        mock_registrar.assert_awaited_once_with(
            chip_evolution["id"], "marcar_lido", sucesso=True
        )

    async def test_retorna_false_quando_desconectado(self, chip_desconectado):
        result = await _executar_marcar_lido(chip_desconectado)

        assert result is False


# ── _executar_entrar_grupo ─────────────────────────────────────


class TestExecutarEntrarGrupo:

    @patch("app.services.warmer.executor._registrar_interacao")
    async def test_registra_interacao_simulada(self, mock_registrar, chip_evolution):
        result = await _executar_entrar_grupo(chip_evolution)

        assert result is True
        mock_registrar.assert_awaited_once_with(
            chip_evolution["id"], "entrar_grupo", sucesso=True, simulada=True
        )


# ── _executar_mensagem_grupo ───────────────────────────────────


class TestExecutarMensagemGrupo:

    @patch("app.services.warmer.executor._registrar_interacao")
    async def test_registra_interacao_simulada(self, mock_registrar, chip_evolution):
        result = await _executar_mensagem_grupo(chip_evolution)

        assert result is True
        mock_registrar.assert_awaited_once_with(
            chip_evolution["id"], "mensagem_grupo", sucesso=True, simulada=True
        )


# ── _executar_atualizar_perfil ─────────────────────────────────


class TestExecutarAtualizarPerfil:

    @patch("app.services.warmer.executor._registrar_interacao")
    async def test_registra_interacao_simulada(self, mock_registrar, chip_evolution):
        result = await _executar_atualizar_perfil(chip_evolution)

        assert result is True
        mock_registrar.assert_awaited_once_with(
            chip_evolution["id"], "atualizar_perfil", sucesso=True, simulada=True
        )


# ── _executar_enviar_midia ─────────────────────────────────────


class TestExecutarEnviarMidia:

    @patch("app.services.warmer.executor._executar_conversa_par")
    async def test_faz_fallback_para_conversa_par(
        self, mock_conv, chip_evolution, atividade_enviar_midia
    ):
        mock_conv.return_value = True

        result = await _executar_enviar_midia(chip_evolution, atividade_enviar_midia)

        assert result is True
        mock_conv.assert_awaited_once_with(chip_evolution, atividade_enviar_midia)


# ── _registrar_interacao ───────────────────────────────────────


class TestRegistrarInteracao:

    @patch("app.services.warmer.executor.supabase")
    async def test_insere_interacao_conversa_par(self, mock_sb):
        mock_sb.table.return_value.insert.return_value.execute.return_value = None

        await _registrar_interacao(CHIP_ID, "conversa_par", sucesso=True)

        insert_call = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_call["chip_id"] == CHIP_ID
        assert insert_call["tipo"] == "msg_enviada"
        assert insert_call["metadata"]["tipo_warmup"] == "conversa_par"

    @patch("app.services.warmer.executor.supabase")
    async def test_insere_interacao_marcar_lido_como_status_criado(self, mock_sb):
        mock_sb.table.return_value.insert.return_value.execute.return_value = None

        await _registrar_interacao(CHIP_ID, "marcar_lido", sucesso=True)

        insert_call = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_call["tipo"] == "status_criado"

    @patch("app.services.warmer.executor.supabase")
    async def test_mensagem_grupo_registra_como_msg_enviada(self, mock_sb):
        mock_sb.table.return_value.insert.return_value.execute.return_value = None

        await _registrar_interacao(CHIP_ID, "mensagem_grupo", sucesso=True)

        insert_call = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_call["tipo"] == "msg_enviada"

    @patch("app.services.warmer.executor.supabase")
    async def test_nao_propaga_erro_de_registro(self, mock_sb):
        mock_sb.table.return_value.insert.return_value.execute.side_effect = (
            RuntimeError("DB error")
        )

        # Não deve lançar exceção
        await _registrar_interacao(CHIP_ID, "conversa_par")


# ── _gerar_mensagem_simples ───────────────────────────────────


class TestGerarMensagemSimples:

    def test_retorna_string_nao_vazia(self):
        msg = _gerar_mensagem_simples()
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_retorna_mensagem_do_pool(self):
        mensagens_validas = {
            "oi, tudo bem?",
            "bom dia!",
            "opa, como vai?",
            "e aí, tranquilo?",
            "oi! como está?",
            "olá, tudo certo?",
            "boa tarde!",
            "hey, blz?",
        }
        for _ in range(20):
            assert _gerar_mensagem_simples() in mensagens_validas
