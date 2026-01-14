# Sprint 30: Refatoração Arquitetural

## Objetivo

Resolver todos os problemas arquiteturais identificados na revisão de código, desde os mais críticos até os de baixa prioridade. Ao final desta sprint, o projeto terá:

- Testabilidade significativamente melhorada
- Zero queries duplicadas
- Error handling robusto em todo o código
- Código legado removido
- Arquivos grandes refatorados em módulos menores

---

## Contexto

Esta sprint foi criada após uma revisão arquitetural completa do projeto que identificou:

| Severidade | Problemas | Épicos |
|------------|-----------|--------|
| **Crítico** | 3 | E01, E02, E03 |
| **Alto** | 1 | E04 |
| **Médio** | 2 | E05 |
| **Baixo** | 2 | E06, E07 |

### Nota da Revisão: **B+**

**Pontos fortes:** Pipeline architecture (A), Policy Engine (A), Resilience (A)
**Pontos fracos:** Testability (C), Database coupling, Query duplication

---

## Estrutura

```
sprint-30/
├── README.md                              ← Este arquivo
├── epic-01-exception-handlers.md          ← CRÍTICO: Error handling centralizado
├── epic-02-consolidacao-queries.md        ← CRÍTICO: Eliminar queries duplicadas
├── epic-03-repository-pattern.md          ← CRÍTICO: Desacoplar do Supabase
├── epic-04-background-tasks.md            ← ALTO: Error handling em tasks async
├── epic-05-remocao-codigo-legado.md       ← MÉDIO: Limpar código obsoleto
├── epic-06-refatoracao-arquivos.md        ← BAIXO: Dividir arquivos grandes
└── epic-07-templates-mensagem.md          ← BAIXO: Externalizar mensagens
```

---

## Épicos

### Epic 01: Exception Handlers (CRÍTICO)
**Objetivo:** Registrar exception handlers no FastAPI e garantir respostas de erro consistentes.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E1.1 | Registrar handlers em main.py | Baixa |
| S30.E1.2 | Criar testes para cada handler | Baixa |
| S30.E1.3 | Validar em produção | Baixa |

**Arquivos:** `app/main.py`, `app/api/error_handlers.py`

---

### Epic 02: Consolidação de Queries (CRÍTICO)
**Objetivo:** Eliminar queries duplicadas, criando fonte única de verdade por entidade.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E2.1 | Auditar todas as queries duplicadas | Média |
| S30.E2.2 | Consolidar `buscar_conversa_ativa` | Baixa |
| S30.E2.3 | Consolidar `buscar_ou_criar_medico` | Média |
| S30.E2.4 | Remover funções órfãs do supabase.py | Baixa |
| S30.E2.5 | Criar testes de regressão | Média |

**Arquivos:** `app/services/supabase.py`, `app/services/conversa.py`, `app/services/medico.py`

---

### Epic 03: Repository Pattern (CRÍTICO)
**Objetivo:** Introduzir Repository pattern para as 3 entidades mais usadas, permitindo injeção de dependência e testes unitários sem mock de imports.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E3.1 | Criar interface base `BaseRepository` | Baixa |
| S30.E3.2 | Implementar `ClienteRepository` | Média |
| S30.E3.3 | Implementar `ConversaRepository` | Média |
| S30.E3.4 | Implementar `VagaRepository` | Média |
| S30.E3.5 | Configurar DI com FastAPI Depends | Média |
| S30.E3.6 | Migrar pipeline para usar repositories | Alta |
| S30.E3.7 | Criar testes com repository mockado | Média |

**Arquivos:** `app/repositories/` (novo), `app/api/dependencies.py` (novo)

---

### Epic 04: Background Tasks (ALTO)
**Objetivo:** Garantir que todas as tasks assíncronas tenham error handling adequado.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E4.1 | Criar wrapper `safe_create_task` | Baixa |
| S30.E4.2 | Auditar todos os `asyncio.create_task` | Média |
| S30.E4.3 | Substituir por wrapper seguro | Média |
| S30.E4.4 | Adicionar métricas de falha | Baixa |
| S30.E4.5 | Criar testes para cenários de erro | Média |

**Arquivos:** `app/core/tasks.py` (novo), múltiplos services

---

### Epic 05: Remoção de Código Legado (MÉDIO)
**Objetivo:** Remover código obsoleto e arquivos não utilizados.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E5.1 | Remover `app/agent.py` legado | Baixa |
| S30.E5.2 | Limpar imports não utilizados | Baixa |
| S30.E5.3 | Remover funções deprecated | Baixa |
| S30.E5.4 | Atualizar documentação | Baixa |

**Arquivos:** `app/agent.py`, vários

---

### Epic 06: Refatoração de Arquivos Grandes (BAIXO)
**Objetivo:** Dividir arquivos com mais de 500 linhas em módulos menores e mais coesos.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E6.1 | Dividir `agente.py` (983 linhas) | Alta |
| S30.E6.2 | Dividir `health.py` (918 linhas) | Média |
| S30.E6.3 | Dividir `whatsapp.py` (626 linhas) | Média |
| S30.E6.4 | Atualizar imports nos consumidores | Média |

**Arquivos:** `app/services/agente.py`, `app/api/routes/health.py`, `app/services/whatsapp.py`

---

### Epic 07: Templates de Mensagem (BAIXO)
**Objetivo:** Mover mensagens hardcoded para o banco de dados, permitindo atualização sem deploy.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S30.E7.1 | Criar tabela `message_templates` | Baixa |
| S30.E7.2 | Criar repository de templates | Baixa |
| S30.E7.3 | Migrar mensagens de opt-out | Baixa |
| S30.E7.4 | Migrar mensagens de confirmação | Baixa |
| S30.E7.5 | Adicionar cache Redis | Baixa |
| S30.E7.6 | Criar interface admin (Slack) | Média |

**Arquivos:** `app/services/templates/` (novo)

---

## Ordem de Execução

```
Epic 01 (Exception Handlers)     ─┐
                                  ├──▶ Pode rodar em paralelo
Epic 05 (Código Legado)          ─┘
         │
         ▼
Epic 02 (Consolidação Queries)
         │
         ▼
Epic 03 (Repository Pattern)
         │
         ├──────────────────────────────┐
         ▼                              ▼
Epic 04 (Background Tasks)       Epic 06 (Arquivos Grandes)
         │                              │
         └──────────┬───────────────────┘
                    ▼
             Epic 07 (Templates)
```

**Dependências:**
- E02 → E03: Repository precisa de queries consolidadas primeiro
- E03 → E04, E06: Repositories devem existir antes de refatorar
- E06, E04 → E07: Código limpo antes de adicionar funcionalidade

---

## Critérios de Aceite da Sprint

### Obrigatórios
- [ ] Exception handlers registrados e testados
- [ ] Zero queries duplicadas (auditoria limpa)
- [ ] Repositories implementados para Cliente, Conversa, Vaga
- [ ] Todos os `create_task` com error handling
- [ ] `app/agent.py` removido
- [ ] Todos os testes passando (`uv run pytest`)

### Desejáveis
- [ ] `agente.py` dividido em módulos
- [ ] `health.py` dividido em módulos
- [ ] Templates de mensagem no banco

---

## Métricas de Sucesso

| Métrica | Antes | Meta |
|---------|-------|------|
| Queries duplicadas | 4+ | 0 |
| Cobertura de testes | ~70% | >80% |
| Arquivos >500 linhas | 5 | 2 |
| `create_task` sem handler | ~15 | 0 |
| Código legado | 1 arquivo | 0 |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar funcionalidade existente | Média | Alto | Testes extensivos antes de cada commit |
| Regressão de performance | Baixa | Médio | Benchmark antes/depois do Repository pattern |
| Tempo maior que previsto | Média | Médio | Priorizar épicos críticos, deixar baixos para próxima sprint |

---

## Links Úteis

| Recurso | Localização |
|---------|-------------|
| Revisão Arquitetural | (documento que originou esta sprint) |
| Convenções de Código | `app/CONVENTIONS.md` |
| Documentação Técnica | `docs/arquitetura/` |

---

## Começando

**Próximo passo:** Comece pelo [Epic 01: Exception Handlers](./epic-01-exception-handlers.md) - é o mais rápido e de maior impacto imediato.
