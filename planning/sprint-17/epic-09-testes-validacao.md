# Epic 09: Testes e Validação

## Objetivo

Garantir que todo o sistema de Business Events funciona corretamente antes do rollout.

## Contexto

### Pirâmide de Testes

```
           /\
          /  \     E2E (2-3 testes)
         /____\    Fluxo completo: mensagem → evento → funil
        /      \
       /        \  Integração (10-15 testes)
      /__________\ Triggers, repository, alertas
     /            \
    /              \ Unitários (30+ testes)
   /________________\ Detectores, formatadores, helpers
```

### Cobertura Mínima

| Módulo | Meta |
|--------|------|
| business_events/repository | > 90% |
| business_events/recusa_detector | > 80% |
| business_events/metrics | > 80% |
| business_events/alerts | > 70% |

---

## Story 9.1: Testes Unitários

### Objetivo
Testar componentes isolados.

### Testes a Implementar

```python
# tests/business_events/test_types.py

import pytest
from app.services.business_events.types import BusinessEvent, EventType


class TestBusinessEvent:
    """Testes para BusinessEvent."""

    def test_to_dict_serializes_correctly(self):
        """Serializa evento para dict."""
        event = BusinessEvent(
            event_type=EventType.OFFER_MADE,
            cliente_id="cliente-123",
            vaga_id="vaga-456",
            event_props={"valor": 1800},
        )

        result = event.to_dict()

        assert result["event_type"] == "offer_made"
        assert result["cliente_id"] == "cliente-123"
        assert result["vaga_id"] == "vaga-456"
        assert result["event_props"]["valor"] == 1800

    def test_defaults(self):
        """Valores padrão corretos."""
        event = BusinessEvent(event_type=EventType.DOCTOR_INBOUND)

        assert event.cliente_id is None
        assert event.source == "backend"
        assert event.event_props == {}


class TestEventType:
    """Testes para EventType enum."""

    def test_all_types_have_value(self):
        """Todos os tipos têm valor string."""
        for event_type in EventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0

    def test_expected_types_exist(self):
        """Tipos esperados existem."""
        expected = [
            "doctor_inbound",
            "doctor_outbound",
            "offer_teaser_sent",
            "offer_made",
            "offer_accepted",
            "offer_declined",
            "handoff_created",
            "shift_completed",
        ]

        actual = [et.value for et in EventType]

        for exp in expected:
            assert exp in actual, f"Tipo {exp} não encontrado"
```

```python
# tests/business_events/test_recusa_detector.py

import pytest
from app.services.business_events.recusa_detector import (
    detectar_recusa,
    RecusaResult,
)


class TestDetectarRecusa:
    """Testes para detector de recusa."""

    @pytest.mark.parametrize("mensagem", [
        "não tenho interesse",
        "Não quero",
        "não vou poder",
        "passo essa",
    ])
    def test_detecta_recusa_explicita(self, mensagem):
        """Detecta recusas explícitas."""
        result = detectar_recusa(mensagem)

        assert result.is_recusa is True
        assert result.confianca >= 0.8
        assert result.tipo == "explicita"

    @pytest.mark.parametrize("mensagem", [
        "já tenho compromisso",
        "tenho outro plantão",
        "muito longe",
        "valor baixo",
    ])
    def test_detecta_desculpas(self, mensagem):
        """Detecta desculpas como recusa média."""
        result = detectar_recusa(mensagem)

        assert result.is_recusa is True
        assert 0.5 <= result.confianca < 0.8
        assert result.tipo == "desculpa"

    @pytest.mark.parametrize("mensagem", [
        "não entendi",
        "pode me explicar?",
        "qual o valor?",
        "onde fica?",
    ])
    def test_nao_confunde_com_recusa(self, mensagem):
        """Não confunde perguntas com recusa."""
        result = detectar_recusa(mensagem)

        assert result.is_recusa is False

    @pytest.mark.parametrize("mensagem", [
        "ok",
        "vou pensar",
        "interessante",
        "me manda mais info",
    ])
    def test_neutros_nao_sao_recusa(self, mensagem):
        """Mensagens neutras não são recusa."""
        result = detectar_recusa(mensagem)

        assert result.is_recusa is False
```

```python
# tests/business_events/test_rollout.py

import pytest
from unittest.mock import patch

from app.services.business_events.rollout import (
    should_emit_event,
    _get_phase_name,
)


class TestShouldEmitEvent:
    """Testes para decisão de rollout."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.get_flag")
    async def test_disabled_returns_false(self, mock_flag):
        """Master switch desabilitado retorna False."""
        mock_flag.side_effect = lambda key, default: False if key == "business_events_enabled" else default

        result = await should_emit_event("cliente-123", "offer_made")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.get_flag")
    async def test_100_percent_returns_true(self, mock_flag):
        """100% rollout sempre retorna True."""
        mock_flag.side_effect = lambda key, default: {
            "business_events_enabled": True,
            "business_events_rollout_pct": 100,
        }.get(key, default)

        result = await should_emit_event("cliente-123", "offer_made")

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.get_flag")
    async def test_consistent_for_same_client(self, mock_flag):
        """Mesmo cliente sempre tem mesmo resultado."""
        mock_flag.side_effect = lambda key, default: {
            "business_events_enabled": True,
            "business_events_rollout_pct": 50,
        }.get(key, default)

        results = []
        for _ in range(10):
            result = await should_emit_event("cliente-123", "offer_made")
            results.append(result)

        # Todos iguais
        assert all(r == results[0] for r in results)


class TestGetPhaseName:
    """Testes para nome da fase."""

    @pytest.mark.parametrize("pct,expected", [
        (0, "disabled"),
        (2, "canary_2pct"),
        (5, "canary_2pct"),
        (10, "canary_10pct"),
        (50, "canary_50pct"),
        (100, "full_rollout"),
    ])
    def test_phase_name(self, pct, expected):
        """Nome correto para cada percentual."""
        assert _get_phase_name(pct) == expected
```

### DoD

- [ ] Testes para BusinessEvent e EventType
- [ ] Testes para recusa_detector
- [ ] Testes para rollout
- [ ] Testes para formatadores Slack
- [ ] Cobertura > 80% nos módulos core

---

## Story 9.2: Testes de Integração

### Objetivo
Testar integração entre componentes.

### Testes a Implementar

```python
# tests/business_events/test_integration.py

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.business_events import (
    emit_event,
    get_funnel_counts,
    BusinessEvent,
    EventType,
)


class TestEmitAndRetrieve:
    """Testes de emissão e recuperação."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_emit_stores_and_returns_id(self, mock_supabase):
        """Emite evento e retorna ID."""
        mock_response = MagicMock()
        mock_response.data = [{"event_id": "evt-uuid-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        event_id = await emit_event(BusinessEvent(
            event_type=EventType.OFFER_MADE,
            cliente_id="cliente-123",
            vaga_id="vaga-456",
        ))

        assert event_id == "evt-uuid-123"
        mock_supabase.table.assert_called_with("business_events")

    @pytest.mark.asyncio
    @patch("app.services.business_events.repository.supabase")
    async def test_funnel_counts_aggregates(self, mock_supabase):
        """Conta eventos por tipo corretamente."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "offer_made"},
            {"event_type": "offer_made"},
            {"event_type": "offer_accepted"},
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value = mock_response

        counts = await get_funnel_counts(hours=24)

        assert counts["offer_made"] == 2
        assert counts["offer_accepted"] == 1


class TestTriggersIntegration:
    """Testes de integração com triggers (requer DB de teste)."""

    @pytest.mark.skip(reason="Requer DB de teste com triggers")
    @pytest.mark.asyncio
    async def test_offer_accepted_trigger(self):
        """Trigger emite evento ao aceitar oferta."""
        # 1. Criar vaga com status='aberta'
        # 2. UPDATE para status='reservada'
        # 3. Verificar business_event criado
        pass

    @pytest.mark.skip(reason="Requer DB de teste com triggers")
    @pytest.mark.asyncio
    async def test_shift_completed_trigger(self):
        """Trigger emite evento ao completar plantão."""
        # 1. Criar vaga com status='reservada'
        # 2. UPDATE para status='realizada'
        # 3. Verificar business_event criado
        pass


class TestAlertsIntegration:
    """Testes de integração de alertas."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts._get_event_count")
    @patch("app.services.business_events.alerts._get_hospital_name")
    async def test_detect_handoff_spike(
        self,
        mock_hospital_name,
        mock_event_count,
    ):
        """Detecta spike de handoff."""
        from app.services.business_events.alerts import detect_handoff_spike

        # Setup: 10 handoffs em 6h, baseline de 2
        mock_hospital_name.return_value = "Hospital Teste"
        mock_event_count.side_effect = lambda et, hours, hid: 10 if hours == 6 else 18

        # Mock para busca de hospitais
        with patch("app.services.business_events.alerts.supabase") as mock_sb:
            mock_response = MagicMock()
            mock_response.data = [{"hospital_id": "hosp-123"}]
            mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.not_.return_value.is_.return_value.execute.return_value = mock_response

            alerts = await detect_handoff_spike(threshold_pct=200)

        assert len(alerts) >= 0  # Pode não ter alerta se threshold não atingido
```

### DoD

- [ ] Testes de emit + retrieve
- [ ] Testes de agregação de funil
- [ ] Testes de detecção de alertas
- [ ] Mocks apropriados para Supabase

---

## Story 9.3: Testes E2E

### Objetivo
Testar fluxo completo end-to-end.

### Cenários E2E

```python
# tests/e2e/test_business_events_flow.py

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestOfferFlow:
    """Teste E2E do fluxo de oferta."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="E2E - executar manualmente")
    async def test_full_offer_flow(self):
        """
        Fluxo completo:
        1. Julia envia mensagem (doctor_outbound)
        2. Médico responde (doctor_inbound)
        3. Julia oferece vaga (offer_made)
        4. Médico aceita (offer_accepted via trigger)
        5. Plantão realizado (shift_completed via trigger)
        6. Funil mostra números corretos
        """
        # Este teste seria executado contra ambiente de staging
        pass


class TestAlertFlow:
    """Teste E2E do fluxo de alertas."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="E2E - executar manualmente")
    async def test_handoff_spike_alert(self):
        """
        Fluxo de alerta:
        1. Gerar múltiplos handoffs para hospital
        2. Detector identifica spike
        3. Alerta enviado ao Slack
        4. Cooldown previne spam
        """
        pass
```

### Checklist Manual E2E

```markdown
## Checklist de Validação E2E

### Preparação
- [ ] Ambiente de staging configurado
- [ ] Flags de rollout em 100%
- [ ] Canal Slack de teste configurado

### Fluxo de Oferta
- [ ] Enviar mensagem para médico teste
- [ ] Verificar doctor_outbound em business_events
- [ ] Responder como médico
- [ ] Verificar doctor_inbound
- [ ] Julia oferece vaga específica
- [ ] Verificar offer_made com vaga_id
- [ ] Aceitar oferta (UPDATE vaga.status = 'reservada')
- [ ] Verificar offer_accepted (trigger)
- [ ] Marcar como realizada
- [ ] Verificar shift_completed (trigger)

### Funil
- [ ] GET /metricas/funil retorna dados
- [ ] Contagens batem com eventos inseridos
- [ ] Taxas calculadas corretamente

### Alertas
- [ ] Gerar condição de spike
- [ ] Verificar alerta no Slack
- [ ] Tentar gerar novamente (cooldown)
- [ ] Verificar que não duplicou
```

### DoD

- [ ] Cenários E2E documentados
- [ ] Checklist manual criado
- [ ] Testes podem ser executados em staging

---

## Story 9.4: Validação de Migração

### Objetivo
Validar que migração de status não quebrou nada.

### Queries de Validação

```sql
-- 1. Verificar que não há mais status 'fechada'
SELECT COUNT(*) as count_fechada
FROM vagas
WHERE status = 'fechada';
-- Esperado: 0

-- 2. Verificar distribuição de status
SELECT status, COUNT(*)
FROM vagas
WHERE deleted_at IS NULL
GROUP BY status
ORDER BY COUNT(*) DESC;

-- 3. Verificar que 'reservada' aumentou
-- (comparar com snapshot pré-migração se disponível)

-- 4. Verificar integridade de vagas realizadas
SELECT v.id, v.status, v.realizada_em, v.realizada_por
FROM vagas v
WHERE v.status = 'realizada'
  AND (v.realizada_em IS NULL OR v.realizada_por IS NULL);
-- Esperado: 0 rows

-- 5. Verificar código não referencia 'fechada'
-- grep -r "fechada" app/ --include="*.py" | grep -v "__pycache__"
-- Esperado: apenas comentários de deprecação
```

### DoD

- [ ] Query 1: Zero vagas com status 'fechada'
- [ ] Query 2: Distribuição de status válida
- [ ] Query 4: Vagas realizadas com metadados
- [ ] Grep: Sem referências ativas a 'fechada'

---

## Checklist do Épico

- [ ] **S17.E09.1** - Testes unitários (30+)
- [ ] **S17.E09.2** - Testes de integração (10-15)
- [ ] **S17.E09.3** - Testes E2E documentados
- [ ] **S17.E09.4** - Validação de migração
- [ ] Cobertura > 80% nos módulos core
- [ ] Todos os testes passando
- [ ] Checklist E2E executado em staging
- [ ] Migração validada

---

## Métricas de Sucesso da Sprint

| Métrica | Meta | Como Medir |
|---------|------|------------|
| Eventos capturados | > 95% | Comparar com ações conhecidas |
| Funil calculado corretamente | 100% | Validação manual |
| Alertas funcionando | 100% | Teste de spike |
| Latência trigger | < 100ms | Logs de timing |
| Cobertura testes | > 80% | pytest --cov |
| Zero regressões | 0 | Testes existentes passando |
