# Sprint 31: Refatoração do Core da Julia

## Objetivo

Resolver os problemas arquiteturais críticos identificados na **análise focada do agente Julia**, melhorando testabilidade, manutenibilidade e preparando o código para escalabilidade futura.

**Foco:** Core do Agente Julia (não sistema todo)

---

## Contexto

Esta sprint foi criada após uma revisão arquitetural profunda focada especificamente na **Agente Julia** como sistema conversacional. A análise identificou:

| Severidade | Problema | Épico |
|------------|----------|-------|
| **P0 (Crítico)** | Sem abstração de LLM - acoplamento direto à Anthropic | E01 |
| **P0 (Crítico)** | God Function `gerar_resposta_julia()` (~350 linhas) | E02 |
| **P1 (Alto)** | Sem tracing/correlation ID para debug | E03 |
| **P1 (Alto)** | Singletons globais dificultam testes | E04 |
| **P1 (Médio)** | Tool handlers com responsabilidades mistas | E05 |
| **P2 (Baixo)** | Ajustes menores e cleanup | E06 |

### Impacto Esperado

| Métrica | Antes | Depois |
|---------|-------|--------|
| Linhas em `agente.py:gerar_resposta_julia()` | ~350 | <100 |
| Acoplamento LLM | Direto (Anthropic) | Interface abstrata |
| Testabilidade do agente | Requer mocks complexos | DI nativo |
| Debugging em produção | Difícil (sem trace) | Correlation ID |

---

## Estrutura

```
sprint-31/
├── README.md                              ← Este arquivo
├── epic-01-llm-provider-abstraction.md    ← P0: Interface LLM
├── epic-02-decomposicao-agente.md         ← P0: Quebrar God Function
├── epic-03-correlation-id.md              ← P1: Tracing
├── epic-04-dependency-injection.md        ← P1: DI completo
├── epic-05-tool-handlers-refactor.md      ← P1: Separar camadas
└── epic-06-cleanup-ajustes.md             ← P2: Ajustes menores
```

---

## Épicos

### Epic 01: LLM Provider Abstraction (P0 - CRÍTICO)

**Problema:** O código chama `anthropic.Anthropic()` diretamente em `app/services/llm.py`. Impossível trocar provider, mockar em testes, ou adicionar observabilidade.

**Objetivo:** Criar interface `LLMProvider` que abstraia qualquer LLM.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E1.1 | Criar Protocol `LLMProvider` | Baixa |
| S31.E1.2 | Criar dataclasses de Request/Response | Baixa |
| S31.E1.3 | Implementar `AnthropicProvider` | Média |
| S31.E1.4 | Criar `MockLLMProvider` para testes | Baixa |
| S31.E1.5 | Migrar `agente.py` para usar interface | Média |
| S31.E1.6 | Criar testes unitários do provider | Média |

**Arquivos:** `app/services/llm/` (novo módulo)

---

### Epic 02: Decomposição do gerar_resposta_julia (P0 - CRÍTICO)

**Problema:** Função `gerar_resposta_julia()` tem ~350 linhas, faz tudo: monta prompt, chama LLM, processa tools, faz retry. Impossível testar partes isoladas.

**Objetivo:** Quebrar em funções pequenas, single-responsibility, testáveis.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E2.1 | Extrair `_build_prompt_context()` | Média |
| S31.E2.2 | Extrair `_filter_tools_for_mode()` | Baixa |
| S31.E2.3 | Extrair `_invoke_llm()` | Média |
| S31.E2.4 | Extrair `_process_tool_calls()` | Média |
| S31.E2.5 | Extrair `_handle_incomplete_response()` | Baixa |
| S31.E2.6 | Refatorar `gerar_resposta_julia()` como orquestrador | Alta |
| S31.E2.7 | Criar testes para cada função extraída | Alta |

**Arquivos:** `app/services/agente.py`, `app/services/julia/` (novo módulo)

---

### Epic 03: Correlation ID Tracing (P1 - ALTO)

**Problema:** Impossível rastrear uma mensagem do webhook até a resposta. Logs não têm contexto compartilhado.

**Objetivo:** Adicionar correlation ID que propaga por todo o pipeline.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E3.1 | Criar middleware de correlation ID | Baixa |
| S31.E3.2 | Criar context var para propagar ID | Baixa |
| S31.E3.3 | Atualizar logging para incluir trace_id | Baixa |
| S31.E3.4 | Propagar trace_id no pipeline | Média |
| S31.E3.5 | Salvar trace_id nas tabelas (interacoes) | Baixa |
| S31.E3.6 | Criar endpoint de busca por trace_id | Baixa |

**Arquivos:** `app/core/tracing.py` (novo), `app/api/middleware.py`

---

### Epic 04: Dependency Injection Completo (P1 - ALTO)

**Problema:** Singletons globais (`supabase`, `client`, `_router`) tornam testes difíceis e criam dependências ocultas.

**Objetivo:** Substituir singletons por DI via FastAPI Depends.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E4.1 | Criar factory `get_llm_provider()` | Baixa |
| S31.E4.2 | Criar factory `get_mode_router()` | Baixa |
| S31.E4.3 | Criar factory `get_redis_client()` | Baixa |
| S31.E4.4 | Migrar webhook para usar DI | Média |
| S31.E4.5 | Migrar pipeline para receber deps | Alta |
| S31.E4.6 | Documentar padrão de DI | Baixa |

**Arquivos:** `app/api/dependencies.py`, múltiplos services

---

### Epic 05: Tool Handlers Refactor (P1 - MÉDIO)

**Problema:** `handle_buscar_vagas()` tem 270 linhas, mistura: parsing JSON, queries DB, lógica de negócio, formatação de output.

**Objetivo:** Separar em camadas: Handler (fino) → Service (lógica) → Repository (dados).

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E5.1 | Criar `VagaService` com lógica de negócio | Média |
| S31.E5.2 | Criar `ToolResponseFormatter` | Baixa |
| S31.E5.3 | Refatorar `handle_buscar_vagas()` | Média |
| S31.E5.4 | Refatorar `handle_salvar_memoria()` | Baixa |
| S31.E5.5 | Criar testes do VagaService isolado | Média |

**Arquivos:** `app/tools/vagas.py`, `app/services/vaga_service.py` (novo)

---

### Epic 06: Cleanup e Ajustes Menores (P2 - BAIXO)

**Problema:** Pequenos débitos técnicos identificados na análise.

**Objetivo:** Limpar código e melhorar qualidade.

| Story | Descrição | Complexidade |
|-------|-----------|--------------|
| S31.E6.1 | Remover duplicação no loop de tools | Baixa |
| S31.E6.2 | Extrair constantes hardcoded (`max_tokens=300`) | Baixa |
| S31.E6.3 | Adicionar type hints faltantes | Baixa |
| S31.E6.4 | Atualizar docstrings desatualizadas | Baixa |
| S31.E6.5 | Rodar linter e corrigir warnings | Baixa |

**Arquivos:** Múltiplos

---

## Ordem de Execução

```
┌─────────────────────────────────────────────────────────────┐
│                         P0 (Crítico)                        │
│                                                             │
│   Epic 01 (LLM Abstraction)                                 │
│            │                                                │
│            ▼                                                │
│   Epic 02 (Decomposição Agente)                             │
│            │                                                │
└────────────┼────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                         P1 (Alto)                           │
│                                                             │
│   Epic 03 (Correlation ID)  ←──┐                            │
│            │                   │                            │
│            │              Pode rodar                        │
│            │              em paralelo                       │
│            │                   │                            │
│   Epic 04 (DI Completo)    ←───┘                            │
│            │                                                │
│            ▼                                                │
│   Epic 05 (Tool Handlers)                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                         P2 (Baixo)                          │
│                                                             │
│   Epic 06 (Cleanup)                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Dependências Críticas:**
- E01 → E02: Precisa da interface LLM antes de decompor o agente
- E02 → E04, E05: Agente decomposto facilita DI e refatoração de tools
- E03, E04: Podem rodar em paralelo (independentes)

---

## Critérios de Aceite da Sprint

### Obrigatórios (P0)
- [ ] Interface `LLMProvider` criada e funcionando
- [ ] `AnthropicProvider` implementado e testado
- [ ] `gerar_resposta_julia()` decomposta em ≤100 linhas
- [ ] Funções extraídas com testes unitários
- [ ] Zero regressão (todos os testes passando)

### Esperados (P1)
- [ ] Correlation ID propagando pelo pipeline
- [ ] DI configurado para LLM e ModeRouter
- [ ] Pelo menos 1 tool handler refatorado (buscar_vagas)

### Desejáveis (P2)
- [ ] Cleanup de código concluído
- [ ] Cobertura de testes >80% nos novos módulos

---

## Métricas de Sucesso

| Métrica | Antes | Meta |
|---------|-------|------|
| Linhas `gerar_resposta_julia()` | ~350 | <100 |
| Funções >50 linhas em agente.py | 3 | 0 |
| Acoplamento direto Anthropic | Sim | Não (interface) |
| Trace ID em logs | Não | Sim |
| Testes sem mock de import | 20% | 80% |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Quebrar comportamento da Julia | Média | Alto | Testes E2E antes/depois |
| Performance degradar | Baixa | Médio | Benchmark das funções críticas |
| Refatoração incompleta | Média | Médio | Aceitar P1 parcial, priorizar P0 |

---

## Começando

**Próximo passo:** Comece pelo [Epic 01: LLM Provider Abstraction](./epic-01-llm-provider-abstraction.md) - é o foundation para todas as outras melhorias.

---

## Links Úteis

| Recurso | Localização |
|---------|-------------|
| Análise Arquitetural | (revisão que originou esta sprint) |
| Código atual do agente | `app/services/agente.py` |
| Código atual do LLM | `app/services/llm.py` |
| Convenções de Código | `app/CONVENTIONS.md` |
