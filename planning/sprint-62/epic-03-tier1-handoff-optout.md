# EPIC 03: Tier 1 Coverage — Handoff & Opt-out Flow

## Contexto

A *deteccao* de handoff e opt-out esta bem testada (54 testes combinados).
A *execucao* — o fluxo que para a Julia, notifica no Slack, e atualiza o banco — tem ZERO testes.
`handoff/flow.py` (380 linhas) e `pipeline/processors/handoff.py` (224 linhas) sao os gaps criticos.

Bug aqui = medico pede humano e Julia continua respondendo, ou Julia para de responder sem avisar ninguem.

## Escopo

- **Incluido**: Testes para handoff/flow.py, processors/handoff.py, handoff/repository.py
- **Excluido**: Refatoracao do fluxo de handoff, testes de deteccao (ja cobertos)

---

## Tarefa 3.1: Testes para `app/services/handoff/flow.py`

### Objetivo
Cobrir o fluxo completo de execucao de handoff (380 linhas, 0 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/services/handoff/test_flow.py` |
| Ler | `app/services/handoff/flow.py` |

### Testes Obrigatorios

**Unitarios (mocando Supabase, Slack, Chatwoot):**
- [ ] Handoff por pedido de humano: Julia avisa medico, atualiza `controlled_by='human'`, notifica Slack
- [ ] Handoff por sentimento negativo: mesmo fluxo mas com trigger diferente
- [ ] Handoff por situacao juridica: escalacao correta
- [ ] Handoff por confianca baixa: fallback seguro
- [ ] Medico ja em handoff: nao cria duplicado (idempotencia)
- [ ] Falha ao notificar Slack: handoff continua (graceful degradation)
- [ ] Falha ao atualizar banco: retorna erro, nao marca como handoff parcial
- [ ] Mensagem de despedida da Julia esta correta e segue persona

**Edge cases:**
- [ ] Conversa inexistente
- [ ] Medico sem conversa ativa
- [ ] Handoff durante campanha ativa

### Definition of Done
- [ ] >85% de cobertura em `handoff/flow.py`
- [ ] Testes validam que `controlled_by` sempre muda atomicamente
- [ ] Testes validam que Julia PARA de responder apos handoff

---

## Tarefa 3.2: Testes para `app/pipeline/processors/handoff.py`

### Objetivo
Cobrir o processor de handoff no pipeline (224 linhas, 0 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/unit/pipeline/test_handoff_processor.py` |
| Ler | `app/pipeline/processors/handoff.py` |

### Testes Obrigatorios

**Unitarios:**
- [ ] Mensagem de medico em handoff: processor bloqueia processamento (nao chega na Julia)
- [ ] Mensagem de medico sem handoff: processor permite continuar
- [ ] Deteccao de trigger de handoff na mensagem: aciona fluxo
- [ ] Prioridade do processor no pipeline: roda antes do LLM
- [ ] Contexto do pipeline atualizado corretamente apos handoff

### Definition of Done
- [ ] >85% de cobertura em `processors/handoff.py`
- [ ] Testes verificam que mensagens nao chegam na Julia quando handoff ativo

---

## Tarefa 3.3: Testes para `app/services/handoff/repository.py`

### Objetivo
Cobrir as operacoes de banco do modulo de handoff.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `tests/services/handoff/test_repository.py` |
| Ler | `app/services/handoff/repository.py` |

### Testes Obrigatorios

**Unitarios (mocando Supabase):**
- [ ] Criar handoff: insere registro com dados corretos
- [ ] Buscar handoff ativo: retorna o mais recente
- [ ] Buscar handoff ativo quando nao existe: retorna None
- [ ] Finalizar handoff: atualiza status e timestamp
- [ ] Listar handoffs por medico: ordenacao e filtros

### Definition of Done
- [ ] >90% de cobertura em `handoff/repository.py`
