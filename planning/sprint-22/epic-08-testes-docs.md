# E08: Testes e Documentacao

**Epico:** Cobertura de Testes e Documentacao
**Estimativa:** 4h
**Dependencias:** E01-E07

---

## Objetivo

Garantir cobertura de testes adequada e documentacao completa para todos os componentes da Sprint 22.

---

## Escopo

### Incluido

- [x] Testes unitarios para todos os servicos
- [x] Testes de integracao
- [x] Documentacao de arquitetura
- [x] Atualizacao do CLAUDE.md
- [x] Runbook operacional

### Excluido

- [ ] Testes de carga
- [ ] Testes E2E completos

---

## Tarefas

### T01: Testes Unitarios

**Arquivos:**

```
tests/unit/
├── test_message_context_classifier.py  (E02)
├── test_delay_engine.py                (E03)
├── test_fora_horario.py                (E04)
├── test_julia_estado.py                (E06)
└── test_painel_slack.py                (E07)
```

**Cobertura Minima:**

| Servico | Cobertura |
|---------|-----------|
| message_context_classifier.py | > 90% |
| delay_engine.py | > 90% |
| fora_horario.py | > 85% |
| julia_estado.py | > 80% |
| painel_slack.py | > 75% |

**DoD:**
- [ ] Todos os arquivos de teste criados
- [ ] Cobertura acima do minimo
- [ ] Todos os testes passando
- [ ] Edge cases cobertos

---

### T02: Testes de Integracao

**Arquivo:** `tests/integration/test_responsividade.py`

```python
"""
Testes de integracao para responsividade inteligente.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock


class TestFluxoCompleto:
    """Testes de fluxo completo."""

    @pytest.mark.asyncio
    async def test_mensagem_durante_horario_comercial(self):
        """
        Mensagem recebida durante horario comercial:
        1. Classificar contexto
        2. Calcular delay
        3. Aplicar delay
        4. Processar normalmente
        """
        # Arrange
        mensagem = "ok pode reservar"
        cliente_id = "123"

        # Act
        from app.services.message_context_classifier import classificar_contexto
        from app.services.delay_engine import calcular_delay

        classificacao = await classificar_contexto(mensagem, cliente_id)
        delay = calcular_delay(classificacao)

        # Assert
        assert classificacao.tipo.value == "aceite_vaga"
        assert delay.delay_ms <= 4000  # Max 2s + variacao
        assert delay.prioridade == 1

    @pytest.mark.asyncio
    async def test_mensagem_fora_horario(self):
        """
        Mensagem recebida fora do horario:
        1. Detectar fora do horario
        2. Enviar ack imediato
        3. Salvar para retomada
        """
        # Arrange
        from app.services.fora_horario import (
            eh_horario_comercial,
            processar_mensagem_fora_horario,
        )
        from app.services.message_context_classifier import (
            classificar_contexto,
            ContextType,
        )

        # Simular 21:00
        with patch('app.services.fora_horario.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 30, 21, 0)

            # Assert fora do horario
            assert eh_horario_comercial() is False

    @pytest.mark.asyncio
    async def test_delay_por_tipo(self):
        """Verifica delays corretos por tipo."""
        from app.services.message_context_classifier import ContextClassification, ContextType
        from app.services.delay_engine import calcular_delay

        # Reply direta: 0-3s
        result = calcular_delay(ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        ))
        assert result.delay_ms <= 5000

        # Campanha fria: 60-180s
        result = calcular_delay(ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.7,
            razao="teste"
        ))
        assert result.delay_ms >= 50000


class TestEstadoJulia:
    """Testes de estado da Julia."""

    @pytest.mark.asyncio
    async def test_singleton_existe(self):
        """Verifica que singleton existe."""
        from app.services.julia_estado import buscar_estado

        estado = await buscar_estado()
        assert estado is not None
        assert estado.modo in ["atendimento", "comercial", "batch", "pausada"]

    @pytest.mark.asyncio
    async def test_atualizacao_metricas(self):
        """Verifica atualizacao de metricas."""
        from app.services.julia_estado import atualizar_metricas

        metricas = await atualizar_metricas()
        assert "conversas_ativas" in metricas
        assert "replies_pendentes" in metricas
        assert "handoffs_abertos" in metricas
```

**DoD:**
- [ ] Arquivo de integracao criado
- [ ] Fluxos principais testados
- [ ] Mocks apropriados
- [ ] Testes passando

---

### T03: Documentacao de Arquitetura

**Arquivo:** `docs/responsividade-inteligente.md`

```markdown
# Responsividade Inteligente

> Sprint 22 - Transformando Julia em assistente genuinamente responsiva

## Visao Geral

A responsividade inteligente ajusta o timing da Julia baseado no contexto,
garantindo que:

- Replies urgentes: 0-3 segundos
- Aceites de vaga: 0-2 segundos
- Campanhas frias: 60-180 segundos
- Fora do horario: Ack imediato + processamento diferido

## Arquitetura

### Componentes

| Componente | Responsabilidade |
|------------|------------------|
| message_context_classifier | Detectar tipo de mensagem |
| delay_engine | Calcular delay apropriado |
| fora_horario | Tratar mensagens fora do horario |
| julia_estado | Manter estado em tempo real |
| painel_slack | Exibir status no Slack |

### Fluxo

```
Mensagem Recebida
       │
       ▼
┌─────────────────┐
│  Classificador  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Horario         │────►│ Fora Horario    │
│ Comercial?      │ Não │ - Ack imediato  │
└────────┬────────┘     │ - Salvar        │
         │ Sim          └─────────────────┘
         ▼
┌─────────────────┐
│  Delay Engine   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Processamento  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Atualizar Estado│
└─────────────────┘
```

## Configuracao

### Delays por Tipo

| Tipo | Min | Max | Prioridade |
|------|-----|-----|------------|
| reply_direta | 0ms | 3000ms | 1 |
| aceite_vaga | 0ms | 2000ms | 1 |
| confirmacao | 2000ms | 5000ms | 2 |
| oferta_ativa | 15000ms | 45000ms | 3 |
| followup | 30000ms | 120000ms | 4 |
| campanha_fria | 60000ms | 180000ms | 5 |

### Horario Comercial

- Segunda a Sexta: 08:00 - 20:00
- Fins de semana: Apenas ack

## Operacao

### Painel de Status

Canal: #julia-status
Frequencia: A cada 5 minutos

### Jobs

| Job | Frequencia |
|-----|------------|
| processar_retomadas | 08:00 seg-sex |
| atualizar_estado_julia | 5 min |
| enviar_painel_status | 5 min |

## Troubleshooting

### Reply demorada

1. Verificar classificacao: `SELECT tipo_contexto FROM fila_mensagens WHERE ...`
2. Verificar delay calculado: `delay_calculado_ms`
3. Verificar logs do agente

### Ack nao enviado

1. Verificar `mensagens_fora_horario`: `SELECT * WHERE ack_enviado = FALSE`
2. Verificar conexao WhatsApp
3. Verificar logs de fora_horario

### Retomada nao processada

1. Verificar job: `/jobs/processar-retomadas`
2. Verificar pendentes: `SELECT * FROM mensagens_fora_horario WHERE processada = FALSE`
3. Verificar logs do job
```

**DoD:**
- [ ] Documentacao criada
- [ ] Diagramas claros
- [ ] Configuracoes documentadas
- [ ] Troubleshooting util

---

### T04: Atualizar CLAUDE.md

**Adicionar em CLAUDE.md:**

```markdown
### Sprint 22 - Responsividade Inteligente

**Foco:** Transformar Julia de sistema batch em assistente responsiva.

**Componentes:**
- Classificador de contexto (6 tipos)
- Delay Engine (0-180s por tipo)
- Modo fora do horario (ack + retomada)
- Estado em tempo real (singleton)
- Painel Slack (a cada 5 min)

**Delays:**
| Tipo | Delay |
|------|-------|
| Reply/Aceite | 0-3s |
| Oferta | 15-45s |
| Campanha | 60-180s |
```

**DoD:**
- [ ] CLAUDE.md atualizado
- [ ] Sprint 22 documentada
- [ ] Componentes listados

---

### T05: Runbook Operacional

**Arquivo:** `docs/runbook-responsividade.md`

```markdown
# Runbook - Responsividade Inteligente

## Verificacoes Diarias

### 1. Estado da Julia

```sql
SELECT * FROM julia_estado;
```

Esperado: modo = 'atendimento' durante horario comercial

### 2. Mensagens Fora do Horario

```sql
SELECT
    COUNT(*) FILTER (WHERE ack_enviado) as com_ack,
    COUNT(*) FILTER (WHERE processada) as processadas,
    COUNT(*) FILTER (WHERE NOT processada AND NOT ack_enviado) as problema
FROM mensagens_fora_horario
WHERE recebida_em >= CURRENT_DATE - 1;
```

Esperado: problema = 0

### 3. Latencia por Tipo

```sql
SELECT
    tipo_contexto,
    ROUND(AVG(delay_calculado_ms)) as delay_medio,
    COUNT(*) as total
FROM fila_mensagens
WHERE criado_em >= CURRENT_DATE
GROUP BY tipo_contexto;
```

## Alertas

### Reply lenta (> 5s)

1. Verificar classificacao
2. Verificar carga do sistema
3. Verificar conexao WhatsApp

### Ack nao enviado

1. Verificar tabela mensagens_fora_horario
2. Verificar servico fora_horario
3. Verificar Evolution API

### Retomada falhou

1. Verificar job processar_retomadas
2. Verificar mensagens pendentes
3. Processar manualmente se necessario

## Comandos Uteis

```bash
# Verificar estado
curl http://localhost:8000/jobs/atualizar-estado-julia

# Forcar retomadas
curl -X POST http://localhost:8000/jobs/processar-retomadas

# Enviar painel
curl -X POST http://localhost:8000/jobs/enviar-painel-status
```
```

**DoD:**
- [ ] Runbook criado
- [ ] Verificacoes documentadas
- [ ] Comandos uteis listados

---

## Validacao Final

### Checklist de Qualidade

- [ ] Todos os testes unitarios passando
- [ ] Todos os testes de integracao passando
- [ ] Cobertura > 80% geral
- [ ] Documentacao completa
- [ ] CLAUDE.md atualizado
- [ ] Runbook operacional

### Comando de Verificacao

```bash
# Rodar todos os testes
uv run pytest tests/ -v --cov=app/services

# Verificar cobertura
uv run pytest tests/ --cov=app/services --cov-report=html
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Testes unitarios para todos os servicos
- [ ] Testes de integracao principais
- [ ] Documentacao de arquitetura
- [ ] CLAUDE.md atualizado
- [ ] Runbook operacional

### Qualidade

- [ ] Cobertura > 80%
- [ ] Zero testes falhando
- [ ] Documentacao clara

### Entrega

- [ ] PR com todos os arquivos
- [ ] Review de documentacao
- [ ] Deploy em staging

---

*Epico criado em 29/12/2025*
