"""
Testes para o circuit breaker por chip.

Valida máquina de estados (CLOSED→OPEN→HALF_OPEN→CLOSED),
thresholds configuráveis, timeout de recuperação, reset manual
e isolamento entre chips.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from app.services.chips.circuit_breaker import (
    ChipCircuit,
    ChipCircuitBreaker,
    ChipCircuitOpenError,
    CircuitState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def circuit():
    """Cria um ChipCircuit com defaults para testes."""
    return ChipCircuit(
        chip_id="chip-abc-123",
        telefone="5511999990000",
        falhas_para_abrir=3,
        tempo_reset_segundos=300,
    )


@pytest.fixture
def circuit_threshold_2():
    """Cria um ChipCircuit com threshold de 2 falhas."""
    return ChipCircuit(
        chip_id="chip-low",
        telefone="5511888880000",
        falhas_para_abrir=2,
        tempo_reset_segundos=60,
    )


@pytest.fixture(autouse=True)
def _limpar_circuits():
    """Limpa o estado global do ChipCircuitBreaker entre testes."""
    ChipCircuitBreaker._circuits.clear()
    yield
    ChipCircuitBreaker._circuits.clear()


# ---------------------------------------------------------------------------
# CircuitState enum
# ---------------------------------------------------------------------------

class TestCircuitState:
    """Testes para o enum CircuitState."""

    @pytest.mark.unit
    def test_valores_do_enum(self):
        """Verifica que os três estados existem com valores corretos."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    @pytest.mark.unit
    def test_enum_tem_tres_membros(self):
        """Enum deve ter exatamente 3 estados."""
        assert len(CircuitState) == 3


# ---------------------------------------------------------------------------
# ChipCircuitOpenError
# ---------------------------------------------------------------------------

class TestChipCircuitOpenError:
    """Testes para a exceção ChipCircuitOpenError."""

    @pytest.mark.unit
    def test_mensagem_com_telefone(self):
        """Mensagem usa telefone quando disponível."""
        err = ChipCircuitOpenError(chip_id="abc-12345678", telefone="5511999")
        assert "5511999" in str(err)
        assert err.chip_id == "abc-12345678"
        assert err.telefone == "5511999"

    @pytest.mark.unit
    def test_mensagem_sem_telefone_usa_chip_id(self):
        """Sem telefone, mensagem usa os primeiros 8 chars do chip_id."""
        err = ChipCircuitOpenError(chip_id="abcdefghijklmnop")
        assert "abcdefgh" in str(err)
        assert err.telefone == ""

    @pytest.mark.unit
    def test_eh_subclasse_de_exception(self):
        """Deve ser subclasse de Exception."""
        assert issubclass(ChipCircuitOpenError, Exception)


# ---------------------------------------------------------------------------
# ChipCircuit — estado inicial
# ---------------------------------------------------------------------------

class TestChipCircuitEstadoInicial:
    """Testes para o estado inicial do ChipCircuit."""

    @pytest.mark.unit
    def test_estado_inicial_closed(self, circuit):
        """Circuit inicia no estado CLOSED."""
        assert circuit.estado == CircuitState.CLOSED

    @pytest.mark.unit
    def test_falhas_consecutivas_zero(self, circuit):
        """Falhas consecutivas iniciam em zero."""
        assert circuit.falhas_consecutivas == 0

    @pytest.mark.unit
    def test_pode_executar_no_inicio(self, circuit):
        """Pode executar quando está CLOSED."""
        assert circuit.pode_executar() is True

    @pytest.mark.unit
    def test_timestamps_none(self, circuit):
        """Timestamps de falha e sucesso iniciam como None."""
        assert circuit.ultima_falha is None
        assert circuit.ultimo_sucesso is None

    @pytest.mark.unit
    def test_erro_info_none(self, circuit):
        """Código e mensagem de erro iniciam como None."""
        assert circuit.ultimo_erro_codigo is None
        assert circuit.ultimo_erro_msg is None


# ---------------------------------------------------------------------------
# Transição CLOSED → OPEN
# ---------------------------------------------------------------------------

class TestTransicaoClosedParaOpen:
    """Testes para a transição CLOSED → OPEN por falhas consecutivas."""

    @pytest.mark.unit
    def test_abre_ao_atingir_threshold(self, circuit):
        """Circuit abre após N falhas consecutivas (threshold=3)."""
        circuit.registrar_falha(error_code=500, error_message="Internal Error")
        assert circuit.estado == CircuitState.CLOSED
        circuit.registrar_falha(error_code=500)
        assert circuit.estado == CircuitState.CLOSED
        circuit.registrar_falha(error_code=500)
        assert circuit.estado == CircuitState.OPEN

    @pytest.mark.unit
    def test_threshold_configuravel(self, circuit_threshold_2):
        """Threshold de 2 abre mais rápido."""
        circuit_threshold_2.registrar_falha()
        assert circuit_threshold_2.estado == CircuitState.CLOSED
        circuit_threshold_2.registrar_falha()
        assert circuit_threshold_2.estado == CircuitState.OPEN

    @pytest.mark.unit
    def test_nao_pode_executar_quando_open(self, circuit):
        """Não pode executar quando circuit está OPEN."""
        for _ in range(3):
            circuit.registrar_falha()
        assert circuit.pode_executar() is False

    @pytest.mark.unit
    def test_sucesso_reseta_contador_de_falhas(self, circuit):
        """Sucesso no meio reseta o contador e evita abertura."""
        circuit.registrar_falha()
        circuit.registrar_falha()
        circuit.registrar_sucesso()
        assert circuit.falhas_consecutivas == 0
        circuit.registrar_falha()
        assert circuit.estado == CircuitState.CLOSED

    @pytest.mark.unit
    def test_armazena_info_do_erro(self, circuit):
        """Registra código e mensagem do último erro."""
        circuit.registrar_falha(error_code=429, error_message="rate limited")
        assert circuit.ultimo_erro_codigo == 429
        assert circuit.ultimo_erro_msg == "rate limited"

    @pytest.mark.unit
    def test_ultima_falha_tem_timestamp(self, circuit):
        """Timestamp de última falha é preenchido."""
        circuit.registrar_falha()
        assert circuit.ultima_falha is not None
        assert isinstance(circuit.ultima_falha, datetime)


# ---------------------------------------------------------------------------
# Transição OPEN → HALF_OPEN (via timeout)
# ---------------------------------------------------------------------------

class TestTransicaoOpenParaHalfOpen:
    """Testes para a transição OPEN → HALF_OPEN após timeout."""

    @pytest.mark.unit
    def test_nao_transiciona_antes_do_timeout(self, circuit):
        """Permanece OPEN se timeout não expirou."""
        for _ in range(3):
            circuit.registrar_falha()
        assert circuit.estado == CircuitState.OPEN
        # Ainda dentro do timeout
        assert circuit.pode_executar() is False
        assert circuit.estado == CircuitState.OPEN

    @pytest.mark.unit
    def test_transiciona_apos_timeout(self, circuit):
        """Vai para HALF_OPEN quando timeout expira."""
        for _ in range(3):
            circuit.registrar_falha()

        # Simula que a última falha foi há 301 segundos
        circuit.ultima_falha = datetime.now(timezone.utc) - timedelta(seconds=301)
        assert circuit.pode_executar() is True
        assert circuit.estado == CircuitState.HALF_OPEN

    @pytest.mark.unit
    def test_timeout_configuravel(self, circuit_threshold_2):
        """Timeout de 60s funciona corretamente."""
        for _ in range(2):
            circuit_threshold_2.registrar_falha()
        assert circuit_threshold_2.estado == CircuitState.OPEN

        # 59s — ainda bloqueado
        circuit_threshold_2.ultima_falha = datetime.now(timezone.utc) - timedelta(seconds=59)
        assert circuit_threshold_2.pode_executar() is False

        # 61s — transiciona
        circuit_threshold_2.ultima_falha = datetime.now(timezone.utc) - timedelta(seconds=61)
        assert circuit_threshold_2.pode_executar() is True
        assert circuit_threshold_2.estado == CircuitState.HALF_OPEN

    @pytest.mark.unit
    def test_open_sem_ultima_falha_nao_transiciona(self, circuit):
        """Se estado é OPEN mas ultima_falha é None, não transiciona."""
        circuit.estado = CircuitState.OPEN
        circuit.ultima_falha = None
        result = circuit._verificar_transicao_half_open()
        assert result is False
        assert circuit.estado == CircuitState.OPEN

    @pytest.mark.unit
    def test_verificar_transicao_retorna_false_se_closed(self, circuit):
        """_verificar_transicao_half_open retorna False se CLOSED."""
        assert circuit._verificar_transicao_half_open() is False


# ---------------------------------------------------------------------------
# Transição HALF_OPEN → CLOSED (sucesso na recuperação)
# ---------------------------------------------------------------------------

class TestTransicaoHalfOpenParaClosed:
    """Testes para a transição HALF_OPEN → CLOSED ao registrar sucesso."""

    @pytest.mark.unit
    def test_sucesso_em_half_open_fecha_circuit(self, circuit):
        """Sucesso em HALF_OPEN transiciona para CLOSED."""
        circuit.estado = CircuitState.HALF_OPEN
        circuit.registrar_sucesso()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.falhas_consecutivas == 0

    @pytest.mark.unit
    def test_sucesso_em_closed_mantem_closed(self, circuit):
        """Sucesso em CLOSED apenas reseta contadores, sem transição."""
        circuit.registrar_sucesso()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.ultimo_sucesso is not None


# ---------------------------------------------------------------------------
# Transição HALF_OPEN → OPEN (falha na recuperação)
# ---------------------------------------------------------------------------

class TestTransicaoHalfOpenParaOpen:
    """Testes para a transição HALF_OPEN → OPEN ao registrar falha."""

    @pytest.mark.unit
    def test_falha_em_half_open_abre_circuit(self, circuit):
        """Uma única falha em HALF_OPEN volta para OPEN."""
        circuit.estado = CircuitState.HALF_OPEN
        circuit.registrar_falha(error_code=503)
        assert circuit.estado == CircuitState.OPEN

    @pytest.mark.unit
    def test_falha_em_half_open_incrementa_contador(self, circuit):
        """Falha em HALF_OPEN incrementa o contador de falhas."""
        circuit.estado = CircuitState.HALF_OPEN
        circuit.falhas_consecutivas = 0
        circuit.registrar_falha()
        assert circuit.falhas_consecutivas == 1


# ---------------------------------------------------------------------------
# Ciclo completo da FSM
# ---------------------------------------------------------------------------

class TestCicloCompletoFSM:
    """Testa o ciclo completo: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    @pytest.mark.unit
    def test_ciclo_completo(self, circuit):
        """Percorre todo o ciclo da máquina de estados."""
        # CLOSED → OPEN (3 falhas)
        for _ in range(3):
            circuit.registrar_falha(error_code=500)
        assert circuit.estado == CircuitState.OPEN
        assert circuit.pode_executar() is False

        # OPEN → HALF_OPEN (simula timeout)
        circuit.ultima_falha = datetime.now(timezone.utc) - timedelta(seconds=301)
        assert circuit.pode_executar() is True
        assert circuit.estado == CircuitState.HALF_OPEN

        # HALF_OPEN → CLOSED (sucesso)
        circuit.registrar_sucesso()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.falhas_consecutivas == 0
        assert circuit.pode_executar() is True

    @pytest.mark.unit
    def test_ciclo_com_falha_na_recuperacao(self, circuit):
        """CLOSED → OPEN → HALF_OPEN → OPEN (falha na recuperação)."""
        for _ in range(3):
            circuit.registrar_falha()
        assert circuit.estado == CircuitState.OPEN

        circuit.ultima_falha = datetime.now(timezone.utc) - timedelta(seconds=301)
        assert circuit.pode_executar() is True
        assert circuit.estado == CircuitState.HALF_OPEN

        # Falha na recuperação → volta para OPEN
        circuit.registrar_falha()
        assert circuit.estado == CircuitState.OPEN
        assert circuit.pode_executar() is False


# ---------------------------------------------------------------------------
# Reset manual
# ---------------------------------------------------------------------------

class TestResetManual:
    """Testes para o reset manual do circuit breaker."""

    @pytest.mark.unit
    def test_reset_de_open_para_closed(self, circuit):
        """Reset manual volta de OPEN para CLOSED."""
        for _ in range(3):
            circuit.registrar_falha()
        assert circuit.estado == CircuitState.OPEN

        circuit.reset()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.falhas_consecutivas == 0

    @pytest.mark.unit
    def test_reset_de_half_open(self, circuit):
        """Reset manual de HALF_OPEN volta para CLOSED."""
        circuit.estado = CircuitState.HALF_OPEN
        circuit.falhas_consecutivas = 5
        circuit.reset()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.falhas_consecutivas == 0

    @pytest.mark.unit
    def test_reset_de_closed_eh_idempotente(self, circuit):
        """Reset em CLOSED não quebra nada."""
        circuit.reset()
        assert circuit.estado == CircuitState.CLOSED
        assert circuit.falhas_consecutivas == 0


# ---------------------------------------------------------------------------
# ChipCircuit.status()
# ---------------------------------------------------------------------------

class TestChipCircuitStatus:
    """Testes para o método status() do ChipCircuit."""

    @pytest.mark.unit
    def test_status_retorna_dict_completo(self, circuit):
        """Status retorna todas as chaves esperadas."""
        s = circuit.status()
        assert s["chip_id"] == "chip-abc-123"
        assert s["telefone"] == "5511999990000"
        assert s["estado"] == "closed"
        assert s["falhas_consecutivas"] == 0
        assert s["ultima_falha"] is None
        assert s["ultimo_sucesso"] is None
        assert s["ultimo_erro_codigo"] is None

    @pytest.mark.unit
    def test_status_com_falha_registrada(self, circuit):
        """Status reflete falhas registradas."""
        circuit.registrar_falha(error_code=502)
        s = circuit.status()
        assert s["falhas_consecutivas"] == 1
        assert s["ultima_falha"] is not None
        assert s["ultimo_erro_codigo"] == 502

    @pytest.mark.unit
    def test_status_com_sucesso_registrado(self, circuit):
        """Status reflete sucesso registrado."""
        circuit.registrar_sucesso()
        s = circuit.status()
        assert s["ultimo_sucesso"] is not None


# ---------------------------------------------------------------------------
# ChipCircuitBreaker (gerenciador)
# ---------------------------------------------------------------------------

class TestChipCircuitBreakerManager:
    """Testes para o gerenciador ChipCircuitBreaker."""

    @pytest.mark.unit
    def test_get_circuit_cria_novo(self):
        """get_circuit cria circuit se não existe."""
        c = ChipCircuitBreaker.get_circuit("chip-1", "5511111111111")
        assert c.chip_id == "chip-1"
        assert c.telefone == "5511111111111"
        assert c.estado == CircuitState.CLOSED

    @pytest.mark.unit
    def test_get_circuit_retorna_existente(self):
        """get_circuit retorna o mesmo circuit para o mesmo chip_id."""
        c1 = ChipCircuitBreaker.get_circuit("chip-2")
        c2 = ChipCircuitBreaker.get_circuit("chip-2")
        assert c1 is c2

    @pytest.mark.unit
    def test_get_circuit_atualiza_telefone_se_vazio(self):
        """get_circuit atualiza telefone se estava vazio."""
        c = ChipCircuitBreaker.get_circuit("chip-3")
        assert c.telefone == ""
        ChipCircuitBreaker.get_circuit("chip-3", "5511333333333")
        assert c.telefone == "5511333333333"

    @pytest.mark.unit
    def test_get_circuit_nao_sobrescreve_telefone(self):
        """get_circuit não sobrescreve telefone já preenchido."""
        ChipCircuitBreaker.get_circuit("chip-4", "5511444444444")
        c = ChipCircuitBreaker.get_circuit("chip-4", "5511999999999")
        assert c.telefone == "5511444444444"

    @pytest.mark.unit
    def test_registrar_sucesso_via_manager(self):
        """Registra sucesso via método do manager."""
        ChipCircuitBreaker.get_circuit("chip-5")
        ChipCircuitBreaker.registrar_sucesso("chip-5")
        c = ChipCircuitBreaker.get_circuit("chip-5")
        assert c.ultimo_sucesso is not None

    @pytest.mark.unit
    def test_registrar_falha_via_manager(self):
        """Registra falha via método do manager."""
        ChipCircuitBreaker.registrar_falha("chip-6", error_code=500, error_message="boom")
        c = ChipCircuitBreaker.get_circuit("chip-6")
        assert c.falhas_consecutivas == 1
        assert c.ultimo_erro_codigo == 500

    @pytest.mark.unit
    def test_pode_usar_chip_closed(self):
        """pode_usar_chip retorna True quando CLOSED."""
        ChipCircuitBreaker.get_circuit("chip-7")
        assert ChipCircuitBreaker.pode_usar_chip("chip-7") is True

    @pytest.mark.unit
    def test_pode_usar_chip_open(self):
        """pode_usar_chip retorna False quando OPEN."""
        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-8")
        assert ChipCircuitBreaker.pode_usar_chip("chip-8") is False


# ---------------------------------------------------------------------------
# ChipCircuitBreaker — status e listagem
# ---------------------------------------------------------------------------

class TestChipCircuitBreakerStatusListagem:
    """Testes para status e listagem de circuits."""

    @pytest.mark.unit
    def test_obter_status_todos_vazio(self):
        """Retorna dict vazio quando não há circuits."""
        assert ChipCircuitBreaker.obter_status_todos() == {}

    @pytest.mark.unit
    def test_obter_status_todos_com_circuits(self):
        """Retorna status de todos os circuits registrados."""
        ChipCircuitBreaker.get_circuit("chip-a")
        ChipCircuitBreaker.get_circuit("chip-b")
        status = ChipCircuitBreaker.obter_status_todos()
        assert "chip-a" in status
        assert "chip-b" in status
        assert status["chip-a"]["estado"] == "closed"

    @pytest.mark.unit
    def test_obter_chips_com_circuit_aberto_vazio(self):
        """Retorna lista vazia quando nenhum circuit está aberto."""
        ChipCircuitBreaker.get_circuit("chip-ok")
        assert ChipCircuitBreaker.obter_chips_com_circuit_aberto() == []

    @pytest.mark.unit
    def test_obter_chips_com_circuit_aberto(self):
        """Retorna apenas chips com circuit OPEN."""
        ChipCircuitBreaker.get_circuit("chip-ok")
        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-falho")
        abertos = ChipCircuitBreaker.obter_chips_com_circuit_aberto()
        assert "chip-falho" in abertos
        assert "chip-ok" not in abertos


# ---------------------------------------------------------------------------
# ChipCircuitBreaker — reset
# ---------------------------------------------------------------------------

class TestChipCircuitBreakerReset:
    """Testes para reset de circuits via manager."""

    @pytest.mark.unit
    def test_reset_chip_existente(self):
        """Reset de um chip existente retorna True e volta para CLOSED."""
        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-r1")
        assert ChipCircuitBreaker.reset_chip("chip-r1") is True
        assert ChipCircuitBreaker.pode_usar_chip("chip-r1") is True

    @pytest.mark.unit
    def test_reset_chip_inexistente(self):
        """Reset de chip inexistente retorna False."""
        assert ChipCircuitBreaker.reset_chip("nao-existe") is False

    @pytest.mark.unit
    def test_reset_todos(self):
        """Reset de todos os circuits retorna contagem e reseta estados."""
        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-t1")
            ChipCircuitBreaker.registrar_falha("chip-t2")
        count = ChipCircuitBreaker.reset_todos()
        assert count == 2
        assert ChipCircuitBreaker.pode_usar_chip("chip-t1") is True
        assert ChipCircuitBreaker.pode_usar_chip("chip-t2") is True

    @pytest.mark.unit
    def test_reset_todos_sem_circuits(self):
        """Reset todos sem circuits retorna 0."""
        assert ChipCircuitBreaker.reset_todos() == 0


# ---------------------------------------------------------------------------
# Isolamento entre chips
# ---------------------------------------------------------------------------

class TestIsolamentoEntreChips:
    """Testes para verificar que chips têm circuits independentes."""

    @pytest.mark.unit
    def test_falhas_em_um_nao_afetam_outro(self):
        """Falhas em chip-A não abrem o circuit de chip-B."""
        ChipCircuitBreaker.get_circuit("chip-A")
        ChipCircuitBreaker.get_circuit("chip-B")

        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-A")

        assert ChipCircuitBreaker.pode_usar_chip("chip-A") is False
        assert ChipCircuitBreaker.pode_usar_chip("chip-B") is True

    @pytest.mark.unit
    def test_reset_de_um_nao_afeta_outro(self):
        """Reset de chip-A não afeta chip-B."""
        for _ in range(3):
            ChipCircuitBreaker.registrar_falha("chip-X")
            ChipCircuitBreaker.registrar_falha("chip-Y")

        ChipCircuitBreaker.reset_chip("chip-X")
        assert ChipCircuitBreaker.pode_usar_chip("chip-X") is True
        assert ChipCircuitBreaker.pode_usar_chip("chip-Y") is False

    @pytest.mark.unit
    def test_sucesso_em_um_nao_reseta_outro(self):
        """Sucesso em chip-A não reseta contadores de chip-B."""
        ChipCircuitBreaker.registrar_falha("chip-P")
        ChipCircuitBreaker.registrar_falha("chip-Q")

        ChipCircuitBreaker.registrar_sucesso("chip-P")

        c_p = ChipCircuitBreaker.get_circuit("chip-P")
        c_q = ChipCircuitBreaker.get_circuit("chip-Q")
        assert c_p.falhas_consecutivas == 0
        assert c_q.falhas_consecutivas == 1
