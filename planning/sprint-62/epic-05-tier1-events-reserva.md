# EPIC 05: Tier 1 Coverage — Business Events & Reserva de Plantao

## Contexto

Business events tem 1.148 linhas sem testes (kpis.py, audit.py, reconciliation.py).
KPIs errados = decisoes operacionais erradas. Audit incompleto = perda de rastreabilidade.

Reserva de plantao tem apenas testes de shape/happy-path. Nao testa idempotencia nem double-booking.

## Escopo

- **Incluido**: Testes para kpis.py, audit.py, reconciliation.py, e testes robustos de reserva
- **Excluido**: Novos tipos de business events, refatoracao

---

## Tarefa 5.1: Testes para `app/services/business_events/kpis.py`

### Objetivo
Cobrir calculos de KPI (460 linhas, 0 testes). KPIs errados levam a decisoes operacionais incorretas.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/business_events/test_kpis.py` |
| Ler | `app/services/business_events/kpis.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Calculo de taxa de conversao: cenarios com dados normais
- [ ] Calculo de taxa de conversao: divisao por zero (zero eventos)
- [ ] Calculo de tempo medio de resposta
- [ ] Calculo de taxa de opt-out
- [ ] Calculo de NPS/satisfacao
- [ ] Agregacao por periodo (dia, semana, mes)
- [ ] Dados faltantes: retorno default (nao excecao)

**Edge cases:**
- [ ] Periodo sem nenhum evento
- [ ] Periodo com um unico evento
- [ ] Eventos com timestamps fora de ordem

### Definition of Done
- [ ] >85% de cobertura em kpis.py
- [ ] Testes documentam formula de cada KPI

---

## Tarefa 5.2: Testes para `app/services/business_events/audit.py`

### Objetivo
Cobrir audit trail (302 linhas, 0 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/business_events/test_audit.py` |
| Ler | `app/services/business_events/audit.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Registro de audit log com todos os campos obrigatorios
- [ ] Busca de audit logs por entidade (medico, vaga, campanha)
- [ ] Filtro por periodo
- [ ] Filtro por tipo de acao
- [ ] Paginacao de resultados
- [ ] Falha ao persistir: erro propagado (nao silenciado)

### Definition of Done
- [ ] >85% de cobertura em audit.py

---

## Tarefa 5.3: Testes para `app/services/business_events/reconciliation.py`

### Objetivo
Cobrir reconciliacao de eventos (386 linhas, 0 testes). Reconciliacao incorreta = metricas divergentes.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/business_events/test_reconciliation.py` |
| Ler | `app/services/business_events/reconciliation.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Reconciliacao detecta eventos duplicados
- [ ] Reconciliacao detecta eventos faltantes
- [ ] Reconciliacao com dados consistentes: sem divergencias
- [ ] Correcao automatica de divergencias (se aplicavel)
- [ ] Relatorio de reconciliacao gerado corretamente

### Definition of Done
- [ ] >80% de cobertura em reconciliation.py

---

## Tarefa 5.4: Testes robustos para reserva de plantao

### Objetivo
Complementar os testes de `reservar_plantao.py` com cenarios de invariantes criticas.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `tests/characterization/test_vagas_tools.py` ou criar `tests/tools/vagas/test_reservar_plantao.py` |
| Ler | `app/tools/vagas/reservar_plantao.py` |

### Testes Obrigatorios

**Invariantes criticas:**
- [ ] Idempotencia: mesma reserva duas vezes nao cria duplicata
- [ ] Vaga ja reservada por outro medico: retorna erro claro
- [ ] Vaga com status incompativel (cancelada, expirada): rejeita
- [ ] Dados incompletos do medico: rejeita com mensagem clara
- [ ] Reserva com data no passado: rejeita
- [ ] Concorrencia: duas reservas simultaneas para mesma vaga (apenas uma deve suceder)

**Integracao:**
- [ ] Fluxo completo: buscar vaga -> reservar -> confirmar status no banco

### Definition of Done
- [ ] >80% de cobertura em reservar_plantao.py
- [ ] Teste de idempotencia documentado
- [ ] Teste de concorrencia documentado (mesmo que com mock)
