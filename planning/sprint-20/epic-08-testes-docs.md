# Epic 08: Testes e Documentacao

## Objetivo

Garantir cobertura de testes adequada e documentar o sistema de ponte externa.

## Contexto

Este epico e o ultimo da Sprint 20 e foca em:
1. Testes de integracao end-to-end
2. Testes de regressao
3. Documentacao tecnica
4. Validacao de metricas

---

## Story 8.1: Testes de Integracao

### Objetivo
Criar testes end-to-end que validam o fluxo completo.

### Arquivo: `tests/external_handoff/test_integration.py`

```python
"""Testes de integracao para external handoff."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.external_handoff.service import criar_ponte_externa
from app.services.external_handoff.confirmacao import processar_confirmacao
from app.services.external_handoff.tokens import (
    gerar_token_confirmacao,
    validar_token,
    gerar_par_links,
)


class TestFluxoCompleto:
    """Testes do fluxo end-to-end."""

    @pytest.fixture
    def medico(self):
        return {
            "id": str(uuid4()),
            "nome": "Dr. Teste",
            "telefone": "11999998888",
            "especialidade": "Cardiologia",
        }

    @pytest.fixture
    def vaga_grupo(self):
        return {
            "id": str(uuid4()),
            "data": "2025-01-15",
            "source": "grupo",
            "source_id": str(uuid4()),
            "hospitais": {"nome": "Hospital Teste"},
            "periodos": {"nome": "Noturno"},
            "valor": 2000,
            "valor_tipo": "fixo",
        }

    @pytest.mark.asyncio
    async def test_fluxo_medico_aceita_vaga_grupo(self, medico, vaga_grupo):
        """
        Fluxo completo:
        1. Medico aceita vaga de grupo
        2. Ponte externa criada
        3. Mensagens enviadas
        4. Divulgador confirma via link
        5. Vaga fechada
        """
        with patch(
            "app.services.external_handoff.service.buscar_divulgador_por_vaga_grupo",
            new_callable=AsyncMock,
            return_value={
                "nome": "Joao Divulgador",
                "telefone": "11888887777",
                "empresa": "MedStaff",
            }
        ), patch(
            "app.services.external_handoff.repository.criar_handoff",
            new_callable=AsyncMock,
            return_value={"id": str(uuid4()), "status": "pending"}
        ), patch(
            "app.services.external_handoff.messaging.enviar_mensagem_medico",
            new_callable=AsyncMock
        ), patch(
            "app.services.external_handoff.messaging.enviar_mensagem_divulgador",
            new_callable=AsyncMock
        ), patch(
            "app.services.business_events.emit_event",
            new_callable=AsyncMock
        ), patch(
            "app.services.slack.notificador.notificar_slack",
            new_callable=AsyncMock
        ):
            # 1. Criar ponte externa
            resultado = await criar_ponte_externa(
                vaga_id=vaga_grupo["id"],
                cliente_id=medico["id"],
                medico=medico,
                vaga=vaga_grupo,
            )

            assert resultado["success"] is True
            assert "handoff_id" in resultado
            assert resultado["divulgador"]["nome"] == "Joao Divulgador"

    @pytest.mark.asyncio
    async def test_fluxo_confirmacao_via_link(self):
        """Teste de confirmacao via link JWT."""
        handoff_id = str(uuid4())

        # Gerar token
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            token = gerar_token_confirmacao(handoff_id, "confirmed")

        # Validar token
        with patch(
            "app.services.external_handoff.tokens.settings"
        ) as mock_settings, patch(
            "app.services.external_handoff.tokens.supabase"
        ) as mock_supabase:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

            valido, payload, erro = await validar_token(token)

            assert valido is True
            assert payload["handoff_id"] == handoff_id
            assert payload["action"] == "confirmed"

    @pytest.mark.asyncio
    async def test_fluxo_confirmacao_processa_corretamente(self):
        """Confirmacao deve atualizar handoff e vaga."""
        handoff = {
            "id": str(uuid4()),
            "vaga_id": str(uuid4()),
            "cliente_id": str(uuid4()),
            "divulgador_nome": "Joao",
            "status": "contacted",
        }

        with patch(
            "app.services.external_handoff.confirmacao.atualizar_status_handoff",
            new_callable=AsyncMock
        ) as mock_atualizar, patch(
            "app.services.external_handoff.confirmacao.supabase"
        ) as mock_supabase, patch(
            "app.services.external_handoff.confirmacao.emit_event",
            new_callable=AsyncMock
        ), patch(
            "app.services.external_handoff.confirmacao.notificar_slack",
            new_callable=AsyncMock
        ), patch(
            "app.services.external_handoff.confirmacao._notificar_medico",
            new_callable=AsyncMock
        ):
            resultado = await processar_confirmacao(
                handoff=handoff,
                action="confirmed",
                confirmed_by="link",
            )

            assert resultado["success"] is True
            assert resultado["handoff_status"] == "confirmed"
            assert resultado["vaga_status"] == "fechada"

            # Verificar que vaga foi atualizada
            mock_supabase.table.return_value.update.assert_called()


class TestRegressao:
    """Testes de regressao para garantir compatibilidade."""

    @pytest.mark.asyncio
    async def test_reservar_plantao_sem_grupo_funciona(self):
        """Vagas sem source=grupo devem funcionar normalmente."""
        from app.tools.vagas import handle_reservar_plantao

        medico = {
            "id": str(uuid4()),
            "nome": "Dr. Teste",
            "especialidade_id": str(uuid4()),
        }

        conversa = {"id": str(uuid4())}

        vaga_interna = {
            "id": str(uuid4()),
            "data": "2025-01-20",
            "status": "aberta",
            "source": None,  # Vaga interna, sem grupo
            "hospitais": {"nome": "Hospital Interno"},
            "periodos": {"nome": "Diurno"},
            "valor": 1800,
            "valor_tipo": "fixo",
        }

        with patch(
            "app.tools.vagas._buscar_vaga_por_data",
            new_callable=AsyncMock,
            return_value=vaga_interna
        ), patch(
            "app.tools.vagas.reservar_vaga",
            new_callable=AsyncMock,
            return_value={**vaga_interna, "status": "reservada"}
        ), patch(
            "app.tools.vagas.formatar_vaga_para_mensagem",
            return_value="Vaga formatada"
        ):
            resultado = await handle_reservar_plantao(
                tool_input={
                    "data_plantao": "2025-01-20",
                    "confirmacao": "quero essa"
                },
                medico=medico,
                conversa=conversa,
            )

            assert resultado["success"] is True
            # Nao deve ter ponte_externa pois nao e vaga de grupo
            assert "ponte_externa" not in resultado or resultado.get("ponte_externa") is None

    @pytest.mark.asyncio
    async def test_buscar_vagas_inclui_source(self):
        """buscar_vagas deve incluir source nos resultados."""
        from app.tools.vagas import handle_buscar_vagas

        medico = {
            "id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "especialidade": "Cardiologia",
        }

        conversa = {"id": str(uuid4())}

        vagas_mock = [
            {
                "id": str(uuid4()),
                "data": "2025-01-15",
                "source": "grupo",
                "hospitais": {"nome": "Hospital A", "cidade": "SP"},
                "periodos": {"nome": "Noturno"},
                "especialidades": {"nome": "Cardiologia"},
                "setores": {"nome": "UTI"},
                "valor": 2000,
                "valor_tipo": "fixo",
            }
        ]

        with patch(
            "app.tools.vagas.buscar_vagas_compativeis",
            new_callable=AsyncMock,
            return_value=vagas_mock
        ), patch(
            "app.tools.vagas.verificar_conflito",
            new_callable=AsyncMock,
            return_value=False
        ), patch(
            "app.tools.vagas.formatar_vagas_contexto",
            return_value="Contexto"
        ):
            resultado = await handle_buscar_vagas(
                tool_input={},
                medico=medico,
                conversa=conversa,
            )

            assert resultado["success"] is True
            assert len(resultado["vagas"]) > 0
```

### DoD

- [ ] Teste de fluxo completo (medico aceita → divulgador confirma)
- [ ] Teste de confirmacao via link
- [ ] Testes de regressao para vagas internas
- [ ] Testes de buscar_vagas com source

---

## Story 8.2: Testes de Tokens

### Objetivo
Cobertura completa do modulo de tokens.

### Arquivo: `tests/external_handoff/test_tokens.py`

(Ja definido no Epic 02, expandir aqui)

```python
"""Testes adicionais para modulo de tokens."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.external_handoff.tokens import (
    gerar_token_confirmacao,
    gerar_par_links,
    validar_token,
    marcar_token_usado,
    TOKEN_EXPIRY_HOURS,
)


class TestMarcarTokenUsado:
    """Testes para funcao marcar_token_usado."""

    @pytest.mark.asyncio
    async def test_marca_token_primeira_vez(self):
        """Deve marcar token na primeira vez."""
        with patch("app.services.external_handoff.tokens.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

            resultado = await marcar_token_usado(
                jti="test-jti",
                handoff_id="handoff-123",
                action="confirmed",
            )

            assert resultado is True
            mock_supabase.table.return_value.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_falha_se_token_ja_usado(self):
        """Deve retornar False se token ja foi usado."""
        with patch("app.services.external_handoff.tokens.supabase") as mock_supabase:
            # Simular erro de unique constraint
            mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key")

            resultado = await marcar_token_usado(
                jti="test-jti",
                handoff_id="handoff-123",
                action="confirmed",
            )

            assert resultado is False


class TestSeguranca:
    """Testes de seguranca dos tokens."""

    def test_token_diferente_a_cada_geracao(self):
        """Tokens devem ser unicos mesmo para mesmo handoff."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            token1 = gerar_token_confirmacao("handoff-123", "confirmed")
            token2 = gerar_token_confirmacao("handoff-123", "confirmed")

            assert token1 != token2

    @pytest.mark.asyncio
    async def test_token_adulterado_invalido(self):
        """Token adulterado deve ser invalido."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            token = gerar_token_confirmacao("handoff-123", "confirmed")
            # Adulterar token
            token_adulterado = token[:-5] + "XXXXX"

            valido, _, erro = await validar_token(token_adulterado)

            assert valido is False
            assert "invalido" in erro.lower()
```

### DoD

- [ ] Testes de marcar_token_usado
- [ ] Testes de unicidade de tokens
- [ ] Testes de token adulterado
- [ ] Cobertura > 90%

---

## Story 8.3: Documentacao Tecnica

### Objetivo
Documentar o sistema de ponte externa.

### Arquivo: `docs/EXTERNAL_HANDOFF.md`

```markdown
# External Handoff - Ponte Automatica

## Visao Geral

O sistema de External Handoff e responsavel por criar uma ponte entre medicos
interessados em vagas e divulgadores externos (donos das vagas de grupo).

## Arquitetura

```
┌─────────────┐     ┌─────────────────┐     ┌───────────────┐
│   Medico    │────►│  reservar_      │────►│   external_   │
│   aceita    │     │  plantao        │     │   handoffs    │
└─────────────┘     └─────────────────┘     └───────┬───────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    │                               │                               │
                    ▼                               ▼                               ▼
            ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
            │  Msg Medico   │              │ Msg Divulgador│              │    Slack      │
            │  (contato)    │              │ (links JWT)   │              │  (notificacao)│
            └───────────────┘              └───────┬───────┘              └───────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
            ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
            │   Link JWT    │              │   Keywords    │              │  Job Follow-up│
            │  (endpoint)   │              │  (webhook)    │              │  (+expiracao) │
            └───────────────┘              └───────────────┘              └───────────────┘
```

## Fluxos

### 1. Medico Aceita Vaga de Grupo

1. Julia oferece vaga com `source='grupo'`
2. Medico aceita
3. `reservar_plantao()` detecta origem
4. `criar_ponte_externa()` e chamado
5. Mensagens enviadas para medico e divulgador
6. Evento `HANDOFF_CREATED` emitido

### 2. Divulgador Confirma via Link

1. Divulgador clica no link de confirmacao
2. Endpoint `/handoff/confirm` valida JWT
3. Token marcado como usado (single-use)
4. Handoff atualizado para `confirmed`
5. Vaga atualizada para `fechada`
6. Medico notificado
7. Evento `HANDOFF_CONFIRMED` emitido

### 3. Divulgador Confirma via Keyword

1. Divulgador responde "CONFIRMADO" no WhatsApp
2. `HandoffKeywordDetector` detecta mensagem
3. Busca handoff pendente por telefone
4. Processa confirmacao
5. Julia responde agradecendo

### 4. Expiracao

1. Job roda a cada 10 minutos
2. Handoffs com `reserved_until < now()` sao expirados
3. Vaga liberada (status='aberta')
4. Medico notificado
5. Evento `HANDOFF_EXPIRED` emitido

## Tabelas

### external_handoffs

| Campo | Tipo | Descricao |
|-------|------|-----------|
| id | UUID | Primary key |
| vaga_id | UUID | FK para vagas |
| cliente_id | UUID | FK para clientes (medico) |
| divulgador_nome | TEXT | Nome do divulgador |
| divulgador_telefone | TEXT | Telefone do divulgador |
| divulgador_empresa | TEXT | Empresa do divulgador |
| status | TEXT | pending, contacted, confirmed, not_confirmed, expired |
| reserved_until | TIMESTAMPTZ | Prazo para confirmacao |
| followup_count | INT | Quantidade de follow-ups enviados |
| confirmed_at | TIMESTAMPTZ | Quando foi confirmado |
| confirmed_by | TEXT | 'link' ou 'keyword' |

### handoff_used_tokens

| Campo | Tipo | Descricao |
|-------|------|-----------|
| jti | TEXT | JWT ID (PK) |
| handoff_id | UUID | FK para external_handoffs |
| action | TEXT | 'confirmed' ou 'not_confirmed' |
| used_at | TIMESTAMPTZ | Quando foi usado |
| ip_address | TEXT | IP de origem |

## Eventos

| Evento | Trigger |
|--------|---------|
| HANDOFF_CREATED | Ponte criada |
| HANDOFF_CONTACTED | Msg enviada ao divulgador |
| HANDOFF_CONFIRM_CLICKED | Link clicado |
| HANDOFF_CONFIRMED | Plantao confirmado |
| HANDOFF_NOT_CONFIRMED | Plantao nao fechou |
| HANDOFF_EXPIRED | 48h sem resposta |
| HANDOFF_FOLLOWUP_SENT | Follow-up enviado |

## Configuracoes

| Variavel | Default | Descricao |
|----------|---------|-----------|
| JWT_SECRET_KEY | - | Secret para assinar tokens |
| APP_BASE_URL | https://api.revoluna.com | URL base para links |
| TOKEN_EXPIRY_HOURS | 48 | Expiracao do token |

## Queries Uteis

```sql
-- Taxa de confirmacao
SELECT
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmados,
    COUNT(*) FILTER (WHERE status = 'not_confirmed') as nao_fechou,
    COUNT(*) FILTER (WHERE status = 'expired') as expirados,
    COUNT(*) as total
FROM external_handoffs
WHERE created_at >= now() - interval '7 days';

-- Handoffs pendentes
SELECT *
FROM external_handoffs
WHERE status IN ('pending', 'contacted')
ORDER BY reserved_until;
```
```

### DoD

- [ ] Documento criado
- [ ] Arquitetura documentada
- [ ] Fluxos explicados
- [ ] Tabelas documentadas
- [ ] Queries uteis incluidas

---

## Story 8.4: Validacao de Metricas

### Objetivo
Criar queries e dashboards para monitorar o sistema.

### Arquivo: `docs/EXTERNAL_HANDOFF_METRICAS.md`

```markdown
# Metricas de External Handoff

## KPIs Principais

| Metrica | Meta | Query |
|---------|------|-------|
| Taxa de confirmacao | > 30% | Ver abaixo |
| Taxa de expiracao | < 50% | Ver abaixo |
| Tempo medio ate confirmacao | < 24h | Ver abaixo |

## Queries de Monitoramento

### Taxa de Confirmacao (Ultimos 7 dias)

```sql
SELECT
    ROUND(
        COUNT(*) FILTER (WHERE status = 'confirmed') * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE status != 'pending'), 0),
        2
    ) as taxa_confirmacao_pct
FROM external_handoffs
WHERE created_at >= now() - interval '7 days';
```

### Tempo Medio ate Confirmacao

```sql
SELECT
    AVG(EXTRACT(EPOCH FROM (confirmed_at - created_at)) / 3600) as horas_media,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (confirmed_at - created_at)) / 3600) as mediana_horas
FROM external_handoffs
WHERE status = 'confirmed'
AND created_at >= now() - interval '30 days';
```

### Follow-ups por Handoff

```sql
SELECT
    followup_count,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM external_handoffs
WHERE status IN ('confirmed', 'not_confirmed', 'expired')
AND created_at >= now() - interval '30 days'
GROUP BY followup_count
ORDER BY followup_count;
```

### Handoffs por Status (Diario)

```sql
SELECT
    DATE(created_at) as data,
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmados,
    COUNT(*) FILTER (WHERE status = 'not_confirmed') as nao_fechou,
    COUNT(*) FILTER (WHERE status = 'expired') as expirados,
    COUNT(*) FILTER (WHERE status IN ('pending', 'contacted')) as pendentes
FROM external_handoffs
WHERE created_at >= now() - interval '30 days'
GROUP BY DATE(created_at)
ORDER BY data DESC;
```

### Confirmacao por Metodo (link vs keyword)

```sql
SELECT
    confirmed_by,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM external_handoffs
WHERE status = 'confirmed'
AND created_at >= now() - interval '30 days'
GROUP BY confirmed_by;
```
```

### DoD

- [ ] KPIs definidos
- [ ] Queries de monitoramento criadas
- [ ] Documentacao de metricas

---

## Checklist do Epico

- [ ] **S20.E08.1** - Testes de integracao criados
- [ ] **S20.E08.2** - Testes de tokens completos
- [ ] **S20.E08.3** - Documentacao tecnica criada
- [ ] **S20.E08.4** - Queries de metricas documentadas
- [ ] Cobertura de testes > 80%
- [ ] Documentacao revisada
- [ ] Fluxos validados manualmente

---

## Checklist Final da Sprint 20

### Migrations
- [ ] external_handoffs criada
- [ ] source/source_id em vagas
- [ ] handoff_used_tokens criada

### Codigo
- [ ] EventTypes novos adicionados
- [ ] Modulo de tokens funcionando
- [ ] Service criar_ponte_externa implementado
- [ ] Tool reservar_plantao integrada
- [ ] Endpoint /handoff/confirm funcionando
- [ ] Detector de keywords funcionando
- [ ] Job de follow-up/expiracao funcionando

### Testes
- [ ] Testes unitarios passando
- [ ] Testes de integracao passando
- [ ] Testes de regressao passando

### Observabilidade
- [ ] Eventos sendo emitidos
- [ ] Slack notificando
- [ ] Logs estruturados
- [ ] Queries de metricas prontas
