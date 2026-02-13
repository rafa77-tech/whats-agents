"""
Testes de caracterização para app/api/routes/jobs.py

Sprint 58 - Epic 0: Safety Net
Captura o comportamento atual dos 53 endpoints de jobs.

Foca em:
- Status codes (200, 500) para cenários de sucesso e erro
- Shape das respostas JSON (campos esperados)
- Contratos de interface (params, query strings)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient para jobs routes."""
    from app.main import app

    return TestClient(app)


# =============================================================================
# Core: Heartbeat, primeira-msg, fila, campanhas
# =============================================================================


class TestHeartbeat:
    """Testa /jobs/heartbeat - registra status online da Julia."""

    def test_heartbeat_sucesso(self, client):
        with patch("app.api.routes.jobs.core.supabase") as mock_sb:
            mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
            response = client.post("/jobs/heartbeat")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "message" in data

    def test_heartbeat_erro_db(self, client):
        with patch("app.api.routes.jobs.core.supabase") as mock_sb:
            mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception(
                "DB error"
            )
            response = client.post("/jobs/heartbeat")
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "message" in data


class TestPrimeiraMensagem:
    """Testa /jobs/primeira-mensagem - envia primeira msg de prospecção."""

    def test_primeira_mensagem_sucesso(self, client):
        with patch("app.api.routes.jobs.core.enviar_primeira_mensagem") as mock_enviar:
            mock_result = MagicMock()
            mock_result.sucesso = True
            mock_result.opted_out = False
            mock_result.cliente_nome = "Dr. Teste"
            mock_result.conversa_id = "conv-123"
            mock_result.mensagem_enviada = "Oi!"
            mock_result.resultado_envio = {"success": True}
            mock_enviar.return_value = mock_result

            response = client.post(
                "/jobs/primeira-mensagem", json={"telefone": "5511999999999"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "cliente" in data
            assert "conversa_id" in data

    def test_primeira_mensagem_opted_out(self, client):
        with patch("app.api.routes.jobs.core.enviar_primeira_mensagem") as mock_enviar:
            mock_result = MagicMock()
            mock_result.opted_out = True
            mock_result.erro = "Médico optou por não receber"
            mock_result.cliente_nome = "Dr. Teste"
            mock_enviar.return_value = mock_result

            response = client.post(
                "/jobs/primeira-mensagem", json={"telefone": "5511999999999"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "blocked"
            assert data["opted_out"] is True

    def test_primeira_mensagem_erro(self, client):
        with patch("app.api.routes.jobs.core.enviar_primeira_mensagem") as mock_enviar:
            mock_result = MagicMock()
            mock_result.sucesso = False
            mock_result.opted_out = False
            mock_result.erro = "Erro no envio"
            mock_enviar.return_value = mock_result

            response = client.post(
                "/jobs/primeira-mensagem", json={"telefone": "5511999999999"}
            )
            # Returns 500 via JSONResponse
            data = response.json()
            assert data["status"] == "error"


class TestProcessarMensagensAgendadas:
    """Testa /jobs/processar-mensagens-agendadas."""

    def test_sucesso(self, client):
        with patch(
            "app.api.routes.jobs.core.processar_mensagens_agendadas", new_callable=AsyncMock
        ) as mock_proc:
            mock_proc.return_value = None
            response = client.post("/jobs/processar-mensagens-agendadas")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_erro(self, client):
        with patch(
            "app.api.routes.jobs.core.processar_mensagens_agendadas", new_callable=AsyncMock
        ) as mock_proc:
            mock_proc.side_effect = Exception("Erro")
            response = client.post("/jobs/processar-mensagens-agendadas")
            assert response.json()["status"] == "error"


class TestAvaliarConversasPendentes:
    """Testa /jobs/avaliar-conversas-pendentes."""

    def test_sucesso(self, client):
        with patch(
            "app.api.routes.jobs.core.avaliar_conversas_pendentes", new_callable=AsyncMock
        ):
            response = client.post("/jobs/avaliar-conversas-pendentes")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


class TestVerificarAlertas:
    """Testa /jobs/verificar-alertas."""

    def test_sucesso(self, client):
        with patch(
            "app.api.routes.jobs.core.executar_verificacao_alertas", new_callable=AsyncMock
        ):
            response = client.post("/jobs/verificar-alertas")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


class TestRelatorioDiario:
    """Testa /jobs/relatorio-diario."""

    def test_sucesso(self, client):
        with patch(
            "app.api.routes.jobs.core.gerar_relatorio_diario", new_callable=AsyncMock
        ) as mock_gerar:
            mock_gerar.return_value = {"metricas": {}}
            with patch(
                "app.api.routes.jobs.core.enviar_relatorio_slack", new_callable=AsyncMock
            ):
                response = client.post("/jobs/relatorio-diario")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert "relatorio" in data


class TestProcessarCampanhasAgendadas:
    """Testa /jobs/processar-campanhas-agendadas."""

    def test_sucesso(self, client):
        with patch(
            "app.api.routes.jobs.core.processar_campanhas_agendadas", new_callable=AsyncMock
        ) as mock_proc:
            mock_result = MagicMock()
            mock_result.campanhas_iniciadas = 2
            mock_proc.return_value = mock_result
            response = client.post("/jobs/processar-campanhas-agendadas")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "campanha(s) iniciada(s)" in data["message"]


class TestProcessarFilaMensagens:
    """Testa /jobs/processar-fila-mensagens."""

    def test_sucesso_shape(self, client):
        with patch("app.api.routes.jobs.core.processar_fila", new_callable=AsyncMock) as mock_proc:
            mock_stats = MagicMock()
            mock_stats.processadas = 10
            mock_stats.enviadas = 8
            mock_stats.bloqueadas_optout = 1
            mock_stats.erros = 1
            mock_proc.return_value = mock_stats
            response = client.post("/jobs/processar-fila-mensagens?limite=20")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            stats = data["stats"]
            assert "processadas" in stats
            assert "enviadas" in stats
            assert "bloqueadas_optout" in stats
            assert "erros" in stats


# =============================================================================
# Doctor State: decay, cooling, maintenance
# =============================================================================


class TestDoctorStateMaintenance:
    """Testa endpoints de manutenção do doctor_state."""

    def test_manutencao_diaria(self, client):
        with patch(
            "app.workers.temperature_decay.run_daily_maintenance", new_callable=AsyncMock
        ) as mock_maint:
            mock_maint.return_value = {"decayed": 5, "expired": 2}
            response = client.post("/jobs/doctor-state-manutencao-diaria")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "result" in data

    def test_manutencao_semanal(self, client):
        with patch(
            "app.workers.temperature_decay.run_weekly_maintenance", new_callable=AsyncMock
        ) as mock_maint:
            mock_maint.return_value = {"decayed": 10}
            response = client.post("/jobs/doctor-state-manutencao-semanal")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_decay(self, client):
        with patch(
            "app.workers.temperature_decay.decay_all_temperatures", new_callable=AsyncMock
        ) as mock_decay:
            mock_decay.return_value = 15
            response = client.post("/jobs/doctor-state-decay?batch_size=100")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "decayed" in data

    def test_expire_cooling(self, client):
        with patch(
            "app.workers.temperature_decay.expire_cooling_off", new_callable=AsyncMock
        ) as mock_expire:
            mock_expire.return_value = 3
            response = client.post("/jobs/doctor-state-expire-cooling")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "expired" in data


# =============================================================================
# Grupos WhatsApp
# =============================================================================


class TestGrupos:
    """Testa endpoints de processamento de grupos."""

    def test_processar_grupos_sucesso(self, client):
        with patch(
            "app.workers.grupos_worker.processar_ciclo_grupos", new_callable=AsyncMock
        ) as mock_proc:
            mock_proc.return_value = {"sucesso": True, "ciclo": {}, "fila": {}}
            response = client.post("/jobs/processar-grupos?batch_size=50&max_workers=20")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "ciclo" in data
            assert "fila" in data

    def test_status_grupos(self, client):
        with patch(
            "app.workers.grupos_worker.obter_status_worker", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = {"fila": {"pendentes": 10}, "ultimo_ciclo": {}}
            response = client.get("/jobs/status-grupos")
            assert response.status_code == 200

    def test_limpar_finalizados(self, client):
        with patch(
            "app.services.grupos.fila.limpar_finalizados", new_callable=AsyncMock
        ) as mock_limpar:
            mock_limpar.return_value = 5
            response = client.post("/jobs/limpar-grupos-finalizados?dias=7")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "removidos" in data

    def test_reprocessar_erros(self, client):
        with patch(
            "app.services.grupos.fila.reprocessar_erros", new_callable=AsyncMock
        ) as mock_reproc:
            mock_reproc.return_value = 3
            response = client.post("/jobs/reprocessar-grupos-erro?limite=100")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


# =============================================================================
# Confirmação de Plantão
# =============================================================================


class TestConfirmacaoPlantao:
    """Testa endpoints de confirmação de plantão."""

    def test_processar_confirmacao(self, client):
        with patch(
            "app.services.confirmacao_plantao.processar_vagas_vencidas",
            new_callable=AsyncMock,
        ) as mock_proc:
            mock_proc.return_value = {"processadas": 2, "erros": 0, "vagas": []}
            response = client.post("/jobs/processar-confirmacao-plantao?buffer_horas=2")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "processadas" in data
            assert "erros" in data

    def test_backfill_confirmacao(self, client):
        with patch(
            "app.services.confirmacao_plantao.processar_vagas_vencidas",
            new_callable=AsyncMock,
        ) as mock_proc:
            mock_proc.return_value = {"processadas": 5, "erros": 0, "vagas": []}
            response = client.post("/jobs/backfill-confirmacao-plantao")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_pendentes_confirmacao_shape(self, client):
        with patch(
            "app.services.confirmacao_plantao.listar_pendentes_confirmacao",
            new_callable=AsyncMock,
        ) as mock_listar:
            mock_vaga = MagicMock()
            mock_vaga.id = "v-1"
            mock_vaga.data = "2025-01-15"
            mock_vaga.hora_inicio = "19:00"
            mock_vaga.hora_fim = "07:00"
            mock_vaga.valor = 2500
            mock_vaga.hospital_nome = "Hospital Teste"
            mock_vaga.especialidade_nome = "Cardiologia"
            mock_vaga.cliente_nome = "Dr. Teste"
            mock_vaga.cliente_telefone = "5511999999999"
            mock_listar.return_value = [mock_vaga]
            response = client.get("/jobs/pendentes-confirmacao")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["total"] == 1
            assert "vagas" in data


# =============================================================================
# Templates
# =============================================================================


class TestTemplates:
    """Testa endpoints de sincronização de templates."""

    def test_sync_templates(self, client):
        with patch(
            "app.services.campaign_behaviors.sincronizar_behaviors",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = {"status": "ok", "sincronizados": 3}
            response = client.post("/jobs/sync-templates")
            assert response.status_code == 200


# =============================================================================
# Reconciliação
# =============================================================================


class TestReconciliacao:
    """Testa endpoints de reconciliação de touches."""

    def test_reconcile_touches_shape(self, client):
        with patch(
            "app.services.touch_reconciliation.executar_reconciliacao",
            new_callable=AsyncMock,
        ) as mock_rec:
            mock_result = MagicMock()
            mock_result.summary = "Reconciliação ok"
            mock_result.total_candidates = 10
            mock_result.reconciled = 5
            mock_result.skipped_already_processed = 2
            mock_result.skipped_already_newer = 1
            mock_result.skipped_no_change = 1
            mock_result.failed = 1
            mock_result.errors = []
            mock_rec.return_value = mock_result
            response = client.post("/jobs/reconcile-touches?horas=72&limite=1000")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            stats = data["stats"]
            assert "total_candidates" in stats
            assert "reconciled" in stats
            assert "failed" in stats

    def test_reconciliacao_status_shape(self, client):
        with patch(
            "app.services.touch_reconciliation.contar_processing_stuck",
            new_callable=AsyncMock,
        ) as mock_count:
            mock_count.return_value = 0
            response = client.get("/jobs/reconciliacao-status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("healthy", "warning", "critical")
            assert "processing_stuck" in data


# =============================================================================
# Gatilhos Autônomos
# =============================================================================


class TestGatilhos:
    """Testa endpoints de gatilhos automáticos."""

    def test_executar_gatilhos_pilot_mode(self, client):
        with patch(
            "app.services.gatilhos_autonomos.executar_todos_gatilhos",
            new_callable=AsyncMock,
        ) as mock_gat:
            mock_gat.return_value = {"pilot_mode": True}
            response = client.post("/jobs/executar-gatilhos-autonomos")
            assert response.status_code == 200
            assert response.json()["status"] == "skipped"

    def test_executar_gatilhos_sucesso(self, client):
        with patch(
            "app.services.gatilhos_autonomos.executar_todos_gatilhos",
            new_callable=AsyncMock,
        ) as mock_gat:
            mock_gat.return_value = {
                "pilot_mode": False,
                "discovery": {"enfileirados": 5},
                "oferta": {"enfileirados": 3},
                "reativacao": {"enfileirados": 2},
                "feedback": {"enfileirados": 1},
            }
            response = client.post("/jobs/executar-gatilhos-autonomos")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "discovery" in data
            assert "oferta" in data

    def test_estatisticas_gatilhos_shape(self, client):
        with patch(
            "app.services.gatilhos_autonomos.obter_estatisticas_gatilhos",
            new_callable=AsyncMock,
        ) as mock_stats:
            mock_stats.return_value = {"discovery": {}, "oferta": {}}
            with patch("app.workers.pilot_mode.is_pilot_mode", return_value=False):
                response = client.get("/jobs/estatisticas-gatilhos")
                assert response.status_code == 200
                data = response.json()
                assert "pilot_mode" in data
                assert "gatilhos" in data


# =============================================================================
# Trust Score & Chips
# =============================================================================


class TestTrustScoreChips:
    """Testa endpoints de trust score e chips."""

    def test_atualizar_trust_scores_sem_chips(self, client):
        with patch("app.api.routes.jobs.chips_ops.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = []
            mock_sb.table.return_value.select.return_value.in_.return_value.execute.return_value = (
                mock_response
            )
            response = client.post("/jobs/atualizar-trust-scores")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["atualizados"] == 0

    def test_sincronizar_chips_shape(self, client):
        with patch(
            "app.services.chips.sincronizar_chips_com_evolution",
            new_callable=AsyncMock,
        ) as mock_sync:
            mock_sync.return_value = {
                "instancias_evolution": 5,
                "chips_atualizados": 3,
                "chips_criados": 1,
                "chips_conectados": 4,
                "chips_desconectados": 1,
                "erros": 0,
            }
            response = client.post("/jobs/sincronizar-chips")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "instancias_evolution" in data
            assert "chips_atualizados" in data

    def test_snapshot_chips_diario(self, client):
        with patch("app.api.routes.jobs.chips_ops.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = [
                {"total_chips": 5, "snapshots_criados": 5, "snapshots_existentes": 0, "erros": 0}
            ]
            mock_sb.rpc.return_value.execute.return_value = mock_response
            response = client.post("/jobs/snapshot-chips-diario")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "total_chips" in data

    def test_resetar_contadores_chips(self, client):
        with patch("app.api.routes.jobs.chips_ops.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = [{"chips_resetados": 5}]
            mock_sb.rpc.return_value.execute.return_value = mock_response
            response = client.post("/jobs/resetar-contadores-chips")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"


# =============================================================================
# Monitoramento de Fila
# =============================================================================


class TestMonitorarFila:
    """Testa endpoints de monitoramento de fila."""

    def test_monitorar_fila_ok(self, client):
        with patch(
            "app.services.fila.fila_service.obter_metricas_fila",
            new_callable=AsyncMock,
        ) as mock_metricas:
            mock_metricas.return_value = {
                "pendentes": 5,
                "processando": 1,
                "mensagem_mais_antiga_min": 10,
                "erros_ultimas_24h": 2,
            }
            response = client.post("/jobs/monitorar-fila")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "pendentes" in data
            assert "alertas" in data

    def test_monitorar_fila_warning(self, client):
        with patch(
            "app.services.fila.fila_service.obter_metricas_fila",
            new_callable=AsyncMock,
        ) as mock_metricas:
            mock_metricas.return_value = {
                "pendentes": 100,
                "processando": 0,
                "mensagem_mais_antiga_min": 60,
                "erros_ultimas_24h": 30,
            }
            response = client.post("/jobs/monitorar-fila")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "warning"
            assert len(data["alertas"]) > 0

    def test_fila_worker_health_shape(self, client):
        with patch(
            "app.services.fila.fila_service.obter_metricas_fila",
            new_callable=AsyncMock,
        ) as mock_metricas:
            mock_metricas.return_value = {
                "pendentes": 5,
                "processando": 1,
                "mensagem_mais_antiga_min": 2,
                "erros_ultimas_24h": 0,
            }
            with patch("app.services.circuit_breaker.circuit_evolution") as mock_circuit:
                mock_circuit.status.return_value = {
                    "estado": "closed",
                    "falhas_consecutivas": 0,
                    "ultima_falha": None,
                }
                response = client.get("/jobs/fila-worker-health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ("healthy", "warning", "critical")
                assert "circuit_breaker" in data
                assert "fila" in data
                assert "issues" in data
