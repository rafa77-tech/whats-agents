# EPIC 07: Orchestrator + Health Adaptations

## Status: Implementado

## Contexto

Chips Meta nao precisam de warmup (API oficial, sem risco de ban) e degradam por quality rating da Meta, nao por trust score interno. Orchestrator e health monitor precisam de adaptacoes para suportar o terceiro provider.

## Escopo

- **Incluido**: Skip warming para Meta, quality-based degradation, delivery status normalization, health monitor alerts
- **Excluido**: Quality Monitor service polling Meta API (sprint 67)

---

## Tarefa 07.1: Orchestrator — Skip Warming para Meta

### Arquivo: `app/services/chips/orchestrator.py`

### Modificacoes

1. **Skip warming**: Chips com `provider="meta"` nao entram em `_promover_warming_para_ready()` nem `_promover_ready_para_active()`
2. **Criacao como active**: Chips Meta criados ja como `status='active'`, `trust_score=100`, `fase_warmup='operacao'`
3. **Quality degradation**:
   - `meta_quality_rating='RED'` → status `degraded`
   - `meta_quality_rating='YELLOW'` → alerta, mantém ativo

### Testes faltando

0 testes para Meta no orchestrator. Precisa de 4 testes:

1. Chip Meta nao entra no pipeline de warming
2. Chip Meta com quality RED → degradado
3. Chip Meta com quality YELLOW → alerta mas ativo
4. Chips Evolution/Z-API continuam com warming normal

---

## Tarefa 07.2: Health Monitor — Meta Quality Alerts

### Arquivo: `app/services/chips/health_monitor.py`

### Modificacoes

1. **Auto-demove**: Chip Meta com `meta_quality_rating='RED'` → auto-degradar
2. **Alert type**: `meta_quality_degraded` no `chip_alerts`
3. **Filter**: `evolution_connected` filter atualizado para nao exigir para chips Meta

### Testes faltando

0 testes para Meta no health monitor. Precisa de 2 testes:

1. Chip Meta quality RED → alert criado + auto-demove
2. Chip Meta quality GREEN → nenhuma acao

---

## Tarefa 07.3: Delivery Status — Meta Normalization

### Arquivo: `app/services/delivery_status.py`

(Documentado no Epic 03, incluido aqui por completude)

Mapeamento adicionado ao `_normalizar_status()`:

| Status Meta (uppercase) | Status Normalizado |
|------------------------|-------------------|
| SENT | sent |
| ACCEPTED | sent |
| DELIVERED | delivered |
| READ | read |
| FAILED | failed |

Testado em `tests/api/routes/test_webhook_meta.py` (7 testes de status).

---

## Definition of Done

- [x] Chips Meta nao entram no warmup
- [x] Chips Meta criados como active com trust 100
- [x] Quality RED → degraded
- [x] Quality YELLOW → alerta
- [x] Health monitor com auto-demove para quality RED
- [x] Delivery status normalizado (SENT/ACCEPTED/DELIVERED/READ/FAILED)

## Gaps Identificados

- [ ] 4 testes faltando para orchestrator Meta
- [ ] 2 testes faltando para health monitor Meta
- [ ] Quality Monitor service nao existe — rating depende de webhook callback da Meta ou polling manual (sprint 67)
- [ ] Nao ha mecanismo para atualizar `meta_quality_rating` automaticamente
- [ ] Nao ha kill switch para desativar todos os chips Meta de uma vez
