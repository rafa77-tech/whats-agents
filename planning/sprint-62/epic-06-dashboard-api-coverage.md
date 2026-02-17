# EPIC 06: Dashboard API Coverage

## Contexto

O dashboard tem 135 API routes. 43 tem testes unitarios. 92 nao tem nenhum.
Pior: `app/api/**` esta excluido do coverage report, tornando essa lacuna invisivel.

Nao vamos testar todas as 92 routes nesta sprint. Vamos focar nas que tem impacto operacional
e remover a exclusao para que o gap fique visivel.

## Escopo

- **Incluido**: Remover exclusao de app/api do coverage, testar ~20 routes criticas
- **Excluido**: Testar todas as 135 routes (escopo futuro), testes E2E de API

---

## Tarefa 6.1: Remover exclusao de `app/api/**` do vitest coverage

### Objetivo
Tornar a cobertura de API routes visivel no coverage report.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/vitest.config.ts` |

### Implementacao

```typescript
// ANTES
exclude: [
  // ...
  'app/api/**',
  // ...
]

// DEPOIS: remover 'app/api/**' da lista de exclusao
// Nota: isso vai derrubar o % de cobertura global temporariamente
```

**Ajustar thresholds temporariamente** para acomodar a inclusao:
- statements: 40 -> 30 (temporario, subir conforme testes sao adicionados)
- lines: 40 -> 30 (temporario)
- functions: 45 -> 35 (temporario)
- branches: 75 -> manter (routes simples nao afetam tanto)

### Testes Obrigatorios

- [ ] `npm run test:ci` no dashboard — coverage report agora inclui app/api/
- [ ] Thresholds ajustados para nao quebrar CI imediatamente
- [ ] Coverage report mostra routes com 0% (evidenciando o gap)

### Definition of Done
- [ ] `app/api/**` aparece no coverage report
- [ ] CI continua passando com thresholds ajustados

---

## Tarefa 6.2: Testes para routes de conversas (impacto operacional alto)

### Objetivo
Testar as routes de conversas — o core da operacao do dashboard.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/api/conversas/route.test.ts` |
| Criar | `dashboard/__tests__/api/conversas/[id]/route.test.ts` |
| Criar | `dashboard/__tests__/api/conversas/[id]/control.test.ts` |
| Ler | `dashboard/app/api/conversas/route.ts` |
| Ler | `dashboard/app/api/conversas/[id]/route.ts` |
| Ler | `dashboard/app/api/conversas/[id]/control/route.ts` |

### Testes Obrigatorios

**conversas/route.ts (listagem):**
- [ ] GET retorna lista de conversas
- [ ] Filtros funcionam (status, medico, periodo)
- [ ] Paginacao
- [ ] Erro de Supabase tratado

**conversas/[id]/route.ts (detalhe):**
- [ ] GET retorna conversa por ID
- [ ] ID inexistente retorna 404
- [ ] Erro de Supabase tratado

**conversas/[id]/control/route.ts (controle Julia/humano):**
- [ ] POST muda controle para humano
- [ ] POST muda controle para Julia
- [ ] Validacao de payload

### Definition of Done
- [ ] Routes de conversas com testes
- [ ] Coverage de app/api/conversas/ > 70%

---

## Tarefa 6.3: Testes para routes de campanhas

### Objetivo
Testar routes de campanhas — impacto direto nas operacoes de outbound.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/api/campanhas/route.test.ts` |
| Criar | `dashboard/__tests__/api/campanhas/[id]/route.test.ts` |
| Ler | `dashboard/app/api/campanhas/route.ts` |
| Ler | `dashboard/app/api/campanhas/[id]/route.ts` |

### Testes Obrigatorios

- [ ] GET lista campanhas
- [ ] POST cria campanha com validacao
- [ ] GET detalhe de campanha
- [ ] PATCH atualiza campanha
- [ ] Validacao de payload (campos obrigatorios, tipos)
- [ ] Erro tratado

### Definition of Done
- [ ] Routes de campanhas com testes

---

## Tarefa 6.4: Testes para routes de medicos

### Objetivo
Testar routes de medicos — dados sensiveis com impacto em LGPD.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/api/medicos/route.test.ts` |
| Criar | `dashboard/__tests__/api/medicos/[id]/route.test.ts` |
| Criar | `dashboard/__tests__/api/medicos/[id]/opt-out.test.ts` |
| Ler | `dashboard/app/api/medicos/route.ts` |
| Ler | `dashboard/app/api/medicos/[id]/route.ts` |
| Ler | `dashboard/app/api/medicos/[id]/opt-out/route.ts` |

### Testes Obrigatorios

- [ ] GET lista medicos
- [ ] GET detalhe do medico
- [ ] POST opt-out: marca medico como opted-out
- [ ] POST opt-out: idempotente (marcar 2x nao da erro)
- [ ] Dados sensiveis nao expostos indevidamente

### Definition of Done
- [ ] Routes de medicos com testes
- [ ] Route de opt-out com testes de idempotencia

---

## Tarefa 6.5: Testes para routes de chips (operacao WhatsApp)

### Objetivo
Testar routes de chips — operacao critica de WhatsApp.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/api/chips/route.test.ts` |
| Criar | `dashboard/__tests__/api/dashboard/chips/route.test.ts` |
| Ler | `dashboard/app/api/chips/route.ts` |
| Ler | `dashboard/app/api/dashboard/chips/route.ts` |

### Testes Obrigatorios

- [ ] GET lista chips com status
- [ ] Acoes de chip (pause, resume, reactivate) validam payload
- [ ] Erro de backend tratado com mensagem clara
- [ ] Dados de trust/metrics retornados corretamente

### Definition of Done
- [ ] Routes de chips com testes basicos
