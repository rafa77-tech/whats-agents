# Sprint 43 - Operacao Unificada & Completude do Dashboard

## Objetivo
Expor no dashboard **todas as funcionalidades operacionais** do backend que atualmente so sao acessiveis via API/SQL, criando uma experiencia operacional completa e self-service.

## Contexto
Analise de APIs mostrou que o backend tem **100+ endpoints** e **modulos completos sem exposicao HTTP**. Esta sprint fecha esse gap.

### Estado Atual vs Desejado

| Area | Backend | Dashboard | Gap | Acao |
|------|---------|-----------|-----|------|
| Integridade | 10 endpoints | 0% | Pagina nao existe | Criar UI |
| Group Entry | 21 endpoints | 0% | Pagina nao existe | Criar UI |
| Admin/Qualidade | 16 endpoints | 0% | Pagina nao existe | Criar UI |
| Health/Diagnostico | 15+ endpoints | Parcial | Fragmentado | Consolidar |
| Sistema/Guardrails | 3 endpoints | 80% | Falta circuit breakers | Expandir |
| **Guardrails** | **Modulo completo** | **0%** | **Sem API HTTP** | **Criar API + UI** |
| **Policy Engine** | **Modulo completo** | **0%** | **Sem API HTTP** | **Criar API + UI** |

### Descoberta Importante

Dois modulos completos existem no backend mas **NAO tem endpoints HTTP**:

1. **`app/services/sistema_guardrails.py`** - 15+ feature flags, desbloqueio, circuit breaker reset, modo emergencia
2. **`app/services/policy/`** - Policy engine completo com flags, metricas, replay, orphan detection

Esta sprint cria os routers HTTP e UIs correspondentes.

## Escopo

### Backend (Novos Routers)
1. **Router Guardrails** - Expor `sistema_guardrails.py`
2. **Router Policy** - Expor `app/services/policy/`

### Novas Paginas Frontend
1. **Integridade** - Anomalias, KPIs de saude, reconciliacao
2. **Group Entry** - Importacao, fila, capacidade, config
3. **Qualidade** - Avaliacao de conversas, sugestoes de prompt
4. **Health Center** - Visao consolidada de saude do sistema

### Melhorias em Paginas Existentes
1. **Sistema** - Feature flags, Policy Engine, circuit breaker reset, rate limit configuravel
2. **Dashboard** - Alertas criticos sempre visiveis
3. **Conversas** - (futuro) Aba de policy decisions

## Fora de Escopo
- Reescrever frontend inteiro
- Mudancas de modelo de dados

## Metricas de Sucesso
- 95%+ das features operacionais do backend com UI
- Zero necessidade de SQL para operacoes rotineiras
- Tempo medio para diagnostico de incidentes < 3 min
- Todas as acoes criticas com confirmacao e audit trail

## Epicos

| Epic | Descricao | Stories | Backend | Frontend |
|------|-----------|---------|---------|----------|
| E01 | Integridade & Anomalias | 4 | - | Novo |
| E02 | Group Entry UI | 5 | - | Novo |
| E03 | Admin/Qualidade | 4 | - | Novo |
| E04 | Health Center | 4 | - | Novo |
| E05 | Sistema Avancado | 3 | - | Update |
| E06 | UX & Consistencia | 4 | - | Update |
| **E07** | **Guardrails & Policy** | **5** | **2 routers** | **3 UIs** |
| **Total** | | **29** | | |

## Ordem de Execucao Recomendada

```
Fase 1 - Backend (E07 parcial)
├── S43.E7.1 - Router Guardrails
└── S43.E7.2 - Router Policy

Fase 2 - Health & Diagnostico
├── E04 - Health Center (4 stories)
└── E01 - Integridade (4 stories)

Fase 3 - Gestao Operacional
├── E02 - Group Entry (5 stories)
└── E03 - Qualidade (4 stories)

Fase 4 - Sistema & UX
├── E05 - Sistema Avancado (3 stories)
├── E06 - UX (4 stories)
└── E07 - UIs de Guardrails/Policy (3 stories)
```

## Resumo de Entregas

### Novos Endpoints Backend

**Router `/guardrails`:**
- `GET/POST /guardrails/flags` - Feature flags
- `POST /guardrails/desbloquear/chip|cliente/{id}`
- `POST /guardrails/circuits/{name}/reset`
- `POST /guardrails/emergencia/ativar|desativar`
- `GET /guardrails/audit`

**Router `/policy`:**
- `GET/POST /policy/status|enable|disable`
- `GET/POST /policy/safe-mode`
- `GET/POST /policy/rules/{id}/enable|disable`
- `GET /policy/metrics`

### Novas Paginas Frontend

| Pagina | Funcionalidades |
|--------|-----------------|
| `/integridade` | Anomalias, KPIs, reconciliacao |
| `/grupos` | Import, fila, capacidade, config |
| `/qualidade` | Avaliacao conversas, sugestoes |
| `/health` | Health score, circuits, rate limit, jobs |

### Updates em Paginas Existentes

| Pagina | Adicoes |
|--------|---------|
| `/sistema` | Feature flags, Policy Engine, rate limit editavel |
| `/dashboard` | Banner de alertas criticos |
| Health Center | Reset de circuit breakers |

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Backend nao testado em producao | Media | Alto | Criar testes de integracao primeiro |
| Feature flags com side effects | Media | Alto | Adicionar confirmacoes e audit trail |
| Performance com muitos dados | Baixa | Medio | Usar paginacao e virtualizacao |

## Criterios de Aceite da Sprint

### Backend
- [ ] Router guardrails com testes
- [ ] Router policy com testes
- [ ] Todos os endpoints com autenticacao
- [ ] Audit trail para acoes criticas

### Frontend
- [ ] 4 novas paginas funcionando
- [ ] Testes unitarios com 70%+ cobertura
- [ ] Zero erros de TypeScript
- [ ] Lighthouse Performance > 70
- [ ] Lighthouse Accessibility > 90

### Documentacao
- [ ] OpenAPI atualizada
- [ ] README de cada epic

---

## Stories
Ver arquivos `epic-*.md` para detalhamento.
