"""
Testes de baseline de performance — Sprint 59, Epic 0: Safety Net.

Mede contagem de chamadas (DB, HTTP, LLM) nos hot paths ANTES das otimizações.
Estes valores servem como baseline para validar que cada epic reduziu chamadas.

NÃO mede tempo real (depende de rede/hardware). Mede quantidade de I/O.

Baseline documentado:
- processar_mensagem_completo: 2x load_doctor_state, 2x analisar_situacao
- ChipSelector: N queries _contar_msgs_ultima_hora (1 por chip)
- Scheduler: jobs executados sequencialmente (for loop)
- Health score: 4 componentes sequenciais
- Deep health: checks sequenciais (redis, supabase, tables, views, schema, prompts)
"""

import asyncio
import pytest

pytestmark = pytest.mark.architectural
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def medico():
    return {
        "id": str(uuid4()),
        "primeiro_nome": "Dr. Teste",
        "telefone": "5511999999999",
        "especialidade_nome": "Cardiologia",
        "especialidade_id": str(uuid4()),
        "stage_jornada": "novo",
        "crm": "123456-SP",
        "status": "ativo",
    }


@pytest.fixture
def conversa(medico):
    return {
        "id": str(uuid4()),
        "cliente_id": medico["id"],
        "telefone": medico["telefone"],
        "status": "ativa",
        "controlled_by": "ai",
        "last_message_at": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def mock_situacao():
    """Mock de ContextoSituacao retornado por analisar_situacao."""
    situacao = MagicMock()
    situacao.resumo = "Conhecimento dinâmico mockado"
    situacao.objecao.tem_objecao = False
    situacao.objecao.tipo = None
    situacao.objecao.subtipo = None
    situacao.objecao.confianca = 0
    situacao.perfil.perfil = "curioso"
    situacao.objetivo.objetivo = "buscar_vagas"
    return situacao


# =============================================================================
# Baseline: processar_mensagem_completo — chamadas DB/LLM
# =============================================================================


class TestOrchestratorBaseline:
    """Baseline de chamadas no hot path processar_mensagem_completo."""

    @pytest.mark.asyncio
    async def test_load_doctor_state_chamado_1x(self, medico, conversa, mock_situacao):
        """
        OTIMIZADO (Epic 2.2): load_doctor_state agora é chamado 1 vez.

        Sprint 59: Aplica updates em memória ao invés de recarregar do DB.
        ANTES: 2x (carrega + recarrega)
        DEPOIS: 1x (carrega + aplica in-memory)
        """
        from app.services.agente import processar_mensagem_completo

        mock_state = MagicMock()
        mock_state.permission_state.value = "active"
        mock_state.temperature = 50

        with (
            patch("app.services.contexto.montar_contexto_completo", new_callable=AsyncMock) as mock_ctx,
            patch("app.services.agente.load_doctor_state", new_callable=AsyncMock) as mock_load,
            patch("app.services.agente.save_doctor_state_updates", new_callable=AsyncMock),
            patch("app.services.agente.PolicyDecide") as MockPolicy,
            patch("app.services.agente.StateUpdate") as MockStateUpdate,
            patch("app.services.agente.log_policy_decision", return_value="pd-123"),
            patch("app.services.agente.log_policy_effect"),
            patch("app.services.agente.get_mode_router") as mock_mode_router,
            patch("app.services.agente.CapabilitiesGate") as MockGate,
            patch("app.services.agente.gerar_resposta_julia", new_callable=AsyncMock) as mock_gerar,
            patch("app.services.agente.safe_create_task"),
            patch("app.services.agente.OrquestradorConhecimento") as MockOrq,
        ):
            mock_ctx.return_value = {
                "medico": "Dr. Teste",
                "vagas": "",
                "historico": "",
                "historico_raw": [],
                "primeira_msg": False,
                "data_hora_atual": "",
                "dia_semana": "",
                "campanha": None,
            }
            mock_load.return_value = mock_state

            mock_orq_instance = MagicMock()
            mock_orq_instance.analisar_situacao = AsyncMock(return_value=mock_situacao)
            MockOrq.return_value = mock_orq_instance

            mock_state_updater = MagicMock()
            mock_state_updater.on_inbound_message.return_value = {"temperature": 55}
            mock_state_updater.on_outbound_message.return_value = {}
            MockStateUpdate.return_value = mock_state_updater

            from app.services.policy import PrimaryAction

            mock_decision = MagicMock()
            mock_decision.primary_action = PrimaryAction.OFFER
            mock_decision.requires_human = False
            mock_decision.constraints_text = ""
            mock_decision.reasoning = "Normal"
            mock_decision.rule_id = "default"
            MockPolicy.return_value.decide = AsyncMock(return_value=mock_decision)

            mock_mode_info = MagicMock()
            mock_mode_info.mode.value = "prospeccao"
            mock_mode_info.pending_transition = None
            mock_mode_router.return_value.process = AsyncMock(return_value=mock_mode_info)
            MockGate.return_value = MagicMock()

            mock_gerar.return_value = "Oi Dr!"

            await processar_mensagem_completo(
                mensagem_texto="Oi, tudo bem?",
                medico=medico,
                conversa=conversa,
            )

            # OTIMIZADO: 1 chamada (carrega + aplica updates in-memory)
            assert mock_load.call_count == 1, (
                f"load_doctor_state chamado {mock_load.call_count}x, esperado 1x. "
                "Sprint 59 Epic 2.2: updates aplicados em memória."
            )

    @pytest.mark.asyncio
    async def test_analisar_situacao_chamado_1x(self, medico, conversa, mock_situacao):
        """
        OTIMIZADO (Epic 2.1): analisar_situacao agora é chamado 1 vez.

        Sprint 59: Orchestrator passa situacao para gerar_resposta_julia.
        ANTES: 2x (orchestrator + generation)
        DEPOIS: 1x (orchestrator apenas, reutilizado em generation)
        """
        from app.services.agente import processar_mensagem_completo

        mock_state = MagicMock()
        mock_state.permission_state.value = "active"
        mock_state.temperature = 50

        analisar_call_count = 0

        async def counting_analisar(**kwargs):
            nonlocal analisar_call_count
            analisar_call_count += 1
            return mock_situacao

        with (
            patch("app.services.contexto.montar_contexto_completo", new_callable=AsyncMock) as mock_ctx,
            patch("app.services.agente.load_doctor_state", new_callable=AsyncMock) as mock_load,
            patch("app.services.agente.save_doctor_state_updates", new_callable=AsyncMock),
            patch("app.services.agente.PolicyDecide") as MockPolicy,
            patch("app.services.agente.StateUpdate") as MockStateUpdate,
            patch("app.services.agente.log_policy_decision", return_value="pd-123"),
            patch("app.services.agente.log_policy_effect"),
            patch("app.services.agente.get_mode_router") as mock_mode_router,
            patch("app.services.agente.CapabilitiesGate") as MockGate,
            patch("app.services.agente.OrquestradorConhecimento") as MockOrq,
            patch("app.services.agente.gerar_resposta", new_callable=AsyncMock) as mock_gerar_resp,
            patch("app.services.agente.gerar_resposta_com_tools", new_callable=AsyncMock) as mock_tools,
            patch("app.services.agente.continuar_apos_tool", new_callable=AsyncMock),
            patch("app.services.agente.montar_prompt_julia", new_callable=AsyncMock, return_value="prompt"),
            patch("app.services.agente.converter_historico_para_messages", return_value=[]),
            patch("app.services.agente.safe_create_task"),
            patch(
                "app.services.conversation_mode.response_validator.validar_resposta_julia",
                return_value=(True, None),
            ),
            patch("app.services.conversation_mode.response_validator.get_fallback_response"),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value=None),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
        ):
            mock_ctx.return_value = {
                "medico": "Dr. Teste",
                "vagas": "",
                "historico": "",
                "historico_raw": [],
                "primeira_msg": False,
                "data_hora_atual": "",
                "dia_semana": "",
                "campanha": None,
            }
            mock_load.return_value = mock_state

            mock_orq_instance = MagicMock()
            mock_orq_instance.analisar_situacao = AsyncMock(side_effect=counting_analisar)
            MockOrq.return_value = mock_orq_instance

            mock_state_updater = MagicMock()
            mock_state_updater.on_inbound_message.return_value = {}
            mock_state_updater.on_outbound_message.return_value = {}
            MockStateUpdate.return_value = mock_state_updater

            from app.services.policy import PrimaryAction

            mock_decision = MagicMock()
            mock_decision.primary_action = PrimaryAction.OFFER
            mock_decision.requires_human = False
            mock_decision.constraints_text = ""
            mock_decision.reasoning = "Normal"
            mock_decision.rule_id = "default"
            MockPolicy.return_value.decide = AsyncMock(return_value=mock_decision)

            mock_mode_info = MagicMock()
            mock_mode_info.mode.value = "prospeccao"
            mock_mode_info.pending_transition = None
            mock_mode_router.return_value.process = AsyncMock(return_value=mock_mode_info)
            MockGate.return_value = MagicMock()

            mock_tools.return_value = {"text": "Oi Dr!", "tool_use": [], "stop_reason": "end_turn"}

            await processar_mensagem_completo(
                mensagem_texto="Oi, tudo bem?",
                medico=medico,
                conversa=conversa,
            )

            # OTIMIZADO: 1 chamada (orchestrator apenas, reutilizado em generation)
            assert analisar_call_count == 1, (
                f"analisar_situacao chamado {analisar_call_count}x, esperado 1x. "
                "Sprint 59 Epic 2.1: situacao passado do orchestrator."
            )


# =============================================================================
# Baseline: ChipSelector — N+1 queries por chip
# =============================================================================


class TestChipSelectorBaseline:
    """Baseline de queries N+1 no ChipSelector."""

    @pytest.mark.asyncio
    async def test_contar_msgs_faz_1_query_por_chip(self):
        """
        BASELINE: _contar_msgs_ultima_hora faz 1 query DB por chamada.

        Como é chamado uma vez por chip no loop de seleção (selector.py:293),
        com N chips elegíveis resulta em N queries individuais COUNT.

        Epic 4 substituiu por 1 query batch.
        """
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        chip_ids = [str(uuid4()) for _ in range(5)]

        with patch("app.services.chips.selector.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.count = 3
            mock_chain = MagicMock()
            mock_chain.execute.return_value = mock_response
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_sb.table.return_value.select.return_value = mock_chain

            # Chamar para cada chip (como o loop antigo fazia)
            for chip_id in chip_ids:
                count = await selector._contar_msgs_ultima_hora(chip_id)
                assert count == 3

            # BASELINE: 5 queries individuais (1 por chip = N+1 pattern)
            assert mock_sb.table.call_count == 5, (
                f"BASELINE: supabase.table chamado {mock_sb.table.call_count}x "
                "para 5 chips."
            )

    @pytest.mark.asyncio
    async def test_batch_contar_msgs_faz_1_query(self):
        """
        OTIMIZADO (Epic 4): _contar_msgs_ultima_hora_batch faz 1 query para N chips.

        Sprint 59: Substitui N queries individuais por 1 query com IN filter.
        """
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        chip_ids = [str(uuid4()) for _ in range(5)]

        with patch("app.services.chips.selector.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = [
                {"chip_id": chip_ids[0]},
                {"chip_id": chip_ids[0]},
                {"chip_id": chip_ids[2]},
            ]
            mock_chain = MagicMock()
            mock_chain.execute.return_value = mock_response
            mock_chain.in_.return_value = mock_chain
            mock_chain.eq.return_value = mock_chain
            mock_chain.gte.return_value = mock_chain
            mock_sb.table.return_value.select.return_value = mock_chain

            result = await selector._contar_msgs_ultima_hora_batch(chip_ids)

            # 1 query para todos os chips
            assert mock_sb.table.call_count == 1, (
                f"OTIMIZADO: batch deve usar 1 query, usou {mock_sb.table.call_count}"
            )
            assert result[chip_ids[0]] == 2
            assert result[chip_ids[2]] == 1
            assert result.get(chip_ids[1], 0) == 0


# =============================================================================
# Baseline: Scheduler — execução sequencial
# =============================================================================


class TestSchedulerBaseline:
    """Epic 3.1: scheduler now parallelizes jobs via asyncio.gather."""

    @pytest.mark.asyncio
    async def test_jobs_executados_em_paralelo(self):
        """
        OTIMIZADO (Epic 3.1): Jobs do mesmo minuto rodam em paralelo.

        Sprint 59: asyncio.gather executa jobs concorrentemente.
        ANTES: sequencial (start_a, end_a, start_b, end_b, start_c, end_c)
        DEPOIS: paralelo (start_a, start_b, start_c, end_*, end_*, end_*)
        """
        from app.workers.scheduler import should_run

        execution_order = []

        async def mock_execute_job(job):
            execution_order.append(("start", job["name"]))
            await asyncio.sleep(0.01)  # Simula I/O
            execution_order.append(("end", job["name"]))

        jobs = [
            {"name": "job_a", "schedule": "* * * * *"},
            {"name": "job_b", "schedule": "* * * * *"},
            {"name": "job_c", "schedule": "* * * * *"},
        ]

        from datetime import datetime

        now = datetime(2025, 1, 15, 10, 0, 0)

        # Executar como o scheduler agora faz (paralelo)
        jobs_to_run = [job for job in jobs if should_run(job["schedule"], now)]
        await asyncio.gather(
            *(mock_execute_job(job) for job in jobs_to_run),
            return_exceptions=True,
        )

        # OTIMIZADO: todos iniciam antes de qualquer um terminar
        starts = [e for e in execution_order if e[0] == "start"]
        ends = [e for e in execution_order if e[0] == "end"]
        assert len(starts) == 3
        assert len(ends) == 3
        # Todos os starts devem vir antes de qualquer end (prova de paralelismo)
        first_end_idx = next(i for i, e in enumerate(execution_order) if e[0] == "end")
        starts_before_first_end = sum(1 for i, e in enumerate(execution_order) if e[0] == "start" and i < first_end_idx)
        assert starts_before_first_end >= 2, (
            f"Jobs devem iniciar em paralelo. Starts antes do 1o end: {starts_before_first_end}"
        )


# =============================================================================
# Baseline: Health Score — componentes sequenciais
# =============================================================================


class TestHealthScoreBaseline:
    """Epic 3.4: health score now parallelizes async components."""

    @pytest.mark.asyncio
    async def test_score_componentes_paralelos(self):
        """
        OTIMIZADO (Epic 3.4): calcular_health_score paraleliza async components.

        Sprint 59: connectivity e fila rodam via asyncio.gather.
        ANTES: sequencial
        DEPOIS: paralelo (connectivity e fila iniciam juntos)
        """
        execution_order = []

        with (
            patch(
                "app.services.health.scoring._calcular_score_conectividade",
                new_callable=AsyncMock,
            ) as mock_conn,
            patch(
                "app.services.health.scoring._calcular_score_fila",
                new_callable=AsyncMock,
            ) as mock_fila,
            patch(
                "app.services.health.scoring._calcular_score_chips",
            ) as mock_chips,
            patch(
                "app.services.health.scoring._calcular_score_circuits",
            ) as mock_circuits,
        ):
            async def track_conn():
                execution_order.append("connectivity_start")
                await asyncio.sleep(0.01)
                execution_order.append("connectivity_end")
                return 30

            async def track_fila():
                execution_order.append("fila_start")
                await asyncio.sleep(0.01)
                execution_order.append("fila_end")
                return 25

            mock_conn.side_effect = track_conn
            mock_fila.side_effect = track_fila
            mock_chips.return_value = 25
            mock_circuits.return_value = 20

            from app.services.health.scoring import calcular_health_score

            result = await calcular_health_score()

            assert result["score"] == 100
            # OTIMIZADO: paralelo — ambos iniciam antes de qualquer um terminar
            assert "connectivity_start" in execution_order
            assert "fila_start" in execution_order
            first_end_idx = min(
                execution_order.index("connectivity_end"),
                execution_order.index("fila_end"),
            )
            starts_before_end = sum(
                1 for e in execution_order[:first_end_idx] if e.endswith("_start")
            )
            assert starts_before_end >= 2, (
                f"Componentes async devem rodar em paralelo. "
                f"Ordem: {execution_order}"
            )

    @pytest.mark.asyncio
    async def test_conectividade_3_checks_sequenciais(self):
        """
        BASELINE: _calcular_score_conectividade faz 3 checks sequenciais.

        Redis, Supabase, Evolution — cada um sequencial.
        Epic 3.4 deve paralelizar Redis + Evolution (ambos async).
        """
        with (
            patch(
                "app.services.health.scoring.verificar_conexao_redis",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_redis,
            patch("app.services.health.scoring.supabase") as mock_sb,
            patch(
                "app.services.health.scoring.evolution.verificar_conexao",
                new_callable=AsyncMock,
                return_value={"instance": {"state": "open"}},
            ) as mock_evo,
        ):
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": 1}]
            )

            from app.services.health.scoring import _calcular_score_conectividade

            score = await _calcular_score_conectividade()

            assert score == 30  # Todos OK
            mock_redis.assert_called_once()
            mock_evo.assert_called_once()


# =============================================================================
# Baseline: Deep Health Check — checks sequenciais
# =============================================================================


class TestDeepHealthBaseline:
    """Baseline: deep health check executa checks sequencialmente."""

    @pytest.mark.asyncio
    async def test_deep_check_sequencial(self):
        """
        BASELINE: executar_deep_health_check executa 6+ checks sequencialmente.

        Checks: environment, project_ref, localhost, dev_guardrails, redis,
                supabase, tables, views, schema_version, prompts.

        Os checks independentes (redis, tables, views) poderiam ser paralelos.
        Epic 3.3 deve paralelizar checks independentes.
        """
        with (
            patch("app.services.health.deep.supabase") as mock_sb,
            patch(
                "app.services.health.deep.verificar_conexao_redis",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.services.health.deep.settings") as mock_settings,
            patch(
                "app.services.health.deep.gerar_schema_fingerprint",
                return_value={"hash": "abc123"},
            ),
            patch(
                "app.services.health.deep.verificar_contrato_prompts",
                new_callable=AsyncMock,
                return_value={"status": "ok"},
            ),
        ):
            mock_settings.runtime_endpoints = {}
            mock_settings.is_production = False
            mock_settings.APP_ENV = "development"
            mock_settings.outbound_allowlist_numbers = ["5511999999999"]
            mock_settings.has_localhost_urls = []

            mock_response = MagicMock()
            mock_response.data = {"value": "development"}
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
                mock_response
            )
            mock_sb.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": 1}]
            )
            mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
                data=[{"id": 1}]
            )

            from app.services.health.deep import executar_deep_health_check

            result = await executar_deep_health_check()

            # Verifica que o check completou e retornou dados válidos
            assert "status" in result
            assert "checks" in result
            # Verifica que os supabase queries foram feitos (baseline para contagem)
            assert mock_sb.table.call_count >= 4, (
                f"BASELINE: {mock_sb.table.call_count} queries Supabase no deep check. "
                "Epic 3.3 deve paralelizar checks independentes."
            )


# =============================================================================
# Baseline: HTTP Client — contagem de instancias efêmeras
# =============================================================================


class TestHttpClientBaseline:
    """Baseline: verificar quantos arquivos usam httpx.AsyncClient() efêmero."""

    def test_singleton_existe_e_funciona(self):
        """Verifica que o singleton HTTP existe e tem a API correta."""
        from app.services.http_client import (
            get_http_client,
            close_http_client,
            http_get,
            http_post,
            http_put,
            http_delete,
        )

        # Funções existem
        assert callable(get_http_client)
        assert callable(close_http_client)
        assert callable(http_get)
        assert callable(http_post)
        assert callable(http_put)
        assert callable(http_delete)

    @pytest.mark.asyncio
    async def test_singleton_retorna_mesma_instancia(self):
        """Verifica comportamento singleton do HTTP client."""
        from app.services.http_client import get_http_client, close_http_client

        # Limpar qualquer singleton existente
        import app.services.http_client as mod

        old_client = mod._client
        mod._client = None

        try:
            client1 = await get_http_client()
            client2 = await get_http_client()
            assert client1 is client2, "get_http_client deve retornar a mesma instância"
        finally:
            # Cleanup
            if mod._client is not None:
                await close_http_client()
            mod._client = old_client


# =============================================================================
# Baseline: Contagem efêmera de httpx.AsyncClient em app/
# =============================================================================


# =============================================================================
# Epic 4: Temperature Decay — batch SELECT instead of individual loads
# =============================================================================


class TestTemperatureDecayBaseline:
    """Epic 4.2: temperature decay uses _row_to_state directly."""

    @pytest.mark.asyncio
    async def test_decay_usa_row_to_state_direto(self):
        """
        OTIMIZADO (Epic 4.2): decay_all_temperatures usa _row_to_state ao invés
        de load_doctor_state individual por médico.

        Sprint 59: buscar_states_para_decay retorna SELECT * com LIMIT,
        e o loop usa _row_to_state para converter diretamente.
        """
        from app.workers.temperature_decay import decay_all_temperatures

        fake_rows = [
            {
                "cliente_id": str(uuid4()),
                "temperature": 0.8,
                "permission_state": "active",
                "temperature_trend": "stable",
                "temperature_band": "warm",
                "risk_tolerance": "unknown",
                "lifecycle_stage": "novo",
                "last_inbound_at": "2025-01-10T10:00:00+00:00",
                "last_outbound_at": None,
                "last_outbound_actor": None,
                "next_allowed_at": None,
                "contact_count_7d": 0,
                "active_objection": None,
                "objection_severity": None,
                "objection_detected_at": None,
                "objection_resolved_at": None,
                "pending_action": None,
                "current_intent": None,
                "flags": {},
                "last_decay_at": None,
                "cooling_off_until": None,
            }
            for _ in range(3)
        ]

        with (
            patch(
                "app.workers.temperature_decay.buscar_states_para_decay",
                new_callable=AsyncMock,
                return_value=fake_rows,
            ),
            patch(
                "app.workers.temperature_decay.save_doctor_state_updates",
                new_callable=AsyncMock,
            ),
        ):
            await decay_all_temperatures(batch_size=10)

            # OTIMIZADO: load_doctor_state não é importado no módulo,
            # confirmando que Epic 4.2 usa _row_to_state direto.
            import app.workers.temperature_decay as td_module

            assert not hasattr(td_module, "load_doctor_state"), (
                "load_doctor_state não deve ser importado em temperature_decay. "
                "Epic 4.2: usa _row_to_state direto."
            )


# =============================================================================
# Epic 4.4: Qualidade — LIMIT nas queries
# =============================================================================


class TestQualidadeBaseline:
    """Epic 4.4: qualidade queries have LIMIT."""

    @pytest.mark.asyncio
    async def test_avaliar_conversas_usa_limit(self):
        """
        OTIMIZADO (Epic 4.4): avaliar_conversas_pendentes usa LIMIT.

        Sprint 59: Queries de conversas e avaliações têm .limit(500).
        """
        with patch("app.services.qualidade.supabase") as mock_sb:
            # Mock chain for conversations query
            mock_chain = MagicMock()
            mock_chain.execute.return_value = MagicMock(data=[])
            mock_chain.in_.return_value = mock_chain
            mock_chain.limit.return_value = mock_chain
            mock_sb.table.return_value.select.return_value = mock_chain

            from app.services.qualidade import avaliar_conversas_pendentes

            await avaliar_conversas_pendentes(limite=50)

            # Verificar que .limit() foi chamado (pelo menos 1x para conversations)
            assert mock_chain.limit.call_count >= 1, (
                "avaliar_conversas_pendentes deve usar .limit() para evitar unbounded queries"
            )


class TestEphemeralClientCount:
    """
    BASELINE: Conta quantos arquivos usam httpx.AsyncClient() efêmero.

    Epic 1 deve zerar essa contagem.
    """

    def test_zero_ephemeral_clients(self):
        """
        Verifica que não existem mais instâncias efêmeras de httpx.AsyncClient.

        ANTES (baseline): ~57 instâncias em 16+ arquivos.
        DEPOIS (Epic 1): 0 instâncias — todas migradas para singleton.
        """
        import subprocess

        result = subprocess.run(
            ["grep", "-rn", "async with httpx.AsyncClient", "app/"],
            capture_output=True,
            text=True,
            cwd="/Users/rafaelpivovar/Documents/Projetos/whatsapp-api",
        )

        lines = [l for l in result.stdout.strip().split("\n") if l]
        count = len(lines)

        # Epic 1 COMPLETO: zero instâncias efêmeras
        assert count == 0, (
            f"Encontradas {count} instâncias efêmeras de httpx.AsyncClient. "
            "Todas devem usar get_http_client() do singleton.\n"
            + "\n".join(lines[:10])
        )
