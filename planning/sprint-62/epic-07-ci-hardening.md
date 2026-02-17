# EPIC 07: CI Hardening & Coverage Gates

## Contexto

Apos os epics 01-06, teremos:
- CI blocking
- Tier 1 com cobertura alta
- Dashboard com API routes no coverage

Este epic consolida: thresholds finais, coverage por modulo, e alinhamento de documentacao.

## Escopo

- **Incluido**: Thresholds finais, coverage report por modulo, atualizacao de docs
- **Excluido**: Testes novos (ja feitos nos epics anteriores)

---

## Tarefa 7.1: Configurar coverage por modulo no backend

### Objetivo
Definir thresholds de coverage por diretorio/modulo ao inves de global.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `pyproject.toml` |
| Criar | `scripts/check-coverage-by-module.sh` (opcional) |

### Implementacao

O pytest-cov nao suporta thresholds por diretorio nativamente. Abordagem:

**Opcao A — Script de validacao (recomendada):**
```bash
#!/bin/bash
# scripts/check-coverage-by-module.sh

# Gerar coverage JSON
uv run pytest --cov=app --cov-report=json --no-header -q

# Verificar modulos Tier 1
python3 -c "
import json
with open('coverage.json') as f:
    data = json.load(f)

thresholds = {
    'app/services/rate_limiter.py': 85,
    'app/services/rate_limit.py': 85,
    'app/services/circuit_breaker.py': 85,
    'app/services/handoff/': 80,
    'app/pipeline/': 70,
    'app/services/business_events/': 70,
    'app/tools/vagas/reservar_plantao.py': 75,
}

# ... verificacao de cada modulo
"
```

**Opcao B — pyproject.toml com threshold global razoavel:**
```toml
[tool.coverage.report]
fail_under = 50  # subir de 45 para 50 (incremento realista)
```

### Testes Obrigatorios

- [ ] Script roda no CI sem erro
- [ ] Modulos Tier 1 acima do threshold definido
- [ ] CI falha se um modulo Tier 1 cair abaixo do threshold

### Definition of Done
- [ ] Coverage por modulo verificada no CI
- [ ] Thresholds documentados

---

## Tarefa 7.2: Ajustar thresholds finais do dashboard

### Objetivo
Definir thresholds finais do dashboard apos inclusao de API routes no coverage.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/vitest.config.ts` |

### Implementacao

Apos epics 01-06, rodar `npm run test:ci` e verificar coverage real.
Ajustar thresholds para:

```typescript
thresholds: {
  statements: 35,  // realista com API routes incluidas
  branches: 70,
  functions: 40,
  lines: 35,
}
```

Os thresholds devem ser o **piso** do que ja temos, nao aspiracional.
Subir incrementalmente em sprints futuras.

### Definition of Done
- [ ] Thresholds refletem realidade pos-inclusao de API routes
- [ ] CI passa com os novos thresholds

---

## Tarefa 7.3: Cleanup da lista de exclusoes do vitest

### Objetivo
Revisar as ~140 linhas de exclusoes e remover as que nao se justificam mais.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/vitest.config.ts` |

### Implementacao

Categorizar cada exclusao:

| Categoria | Acao |
|-----------|------|
| Re-exports (`index.ts` com apenas `export * from`) | Manter excluido |
| Tipos (`types.ts` com apenas interfaces) | Manter excluido |
| Wrappers UI sem logica (shadcn, Radix) | Manter excluido |
| Componentes com logica de negocio | REMOVER da exclusao |
| Hooks com logica | REMOVER da exclusao |
| Libs com logica | REMOVER da exclusao |

Focar em remover exclusoes de:
- `lib/validations/**` — validacoes TEM logica testavel
- `hooks/use-api-error.ts` — error handling tem logica
- Componentes de chips que tem logica de formatacao

### Definition of Done
- [ ] Exclusoes revisadas e documentadas (cada uma com justificativa)
- [ ] Exclusoes injustificadas removidas
- [ ] CI continua passando

---

## Tarefa 7.4: Atualizar CLAUDE.md e documentacao

### Objetivo
Alinhar documentacao com a realidade pos-sprint.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `CLAUDE.md` |
| Modificar | `app/CONVENTIONS.md` (se necessario) |

### Implementacao

Atualizar no CLAUDE.md:
- Sprint 62 na tabela de sprints concluidas
- Thresholds reais de cobertura (remover "70%" generico)
- Adicionar secao sobre tiers de cobertura por risco
- Atualizar metricas do projeto (testes, etc)

Adicionar em CONVENTIONS.md ou CLAUDE.md:
```markdown
## Cobertura de Testes por Risco

| Tier | Modulos | Threshold | Enforcement |
|------|---------|-----------|-------------|
| 1 | rate_limiter, circuit_breaker, handoff, pipeline, reserva | >85% | CI blocking (script) |
| 2 | campanhas, formatters, workers, integracoes | >60% | Coverage global |
| 3 | Dashboard UI, logging, config | >30% | Coverage global |

### Regra para codigo novo
- Codigo Tier 1: testes obrigatorios antes do merge
- Codigo Tier 2: testes obrigatorios, cobertura flexivel
- Codigo Tier 3: testes recomendados
```

### Definition of Done
- [ ] CLAUDE.md atualizado com thresholds reais
- [ ] Tiers de cobertura documentados
- [ ] Sprint 62 registrada

---

## Tarefa 7.5: Remover TODO comments obsoletos do CI

### Objetivo
Limpar os TODOs que referenciam numeros antigos (261 erros, 27 testes).

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `.github/workflows/ci.yml` |

### Implementacao

Remover comentarios:
```yaml
# REMOVER: # TODO: Remover continue-on-error apos corrigir 261 erros de lint (issue #73)
# REMOVER: # TODO: Remover continue-on-error apos formatar 354 arquivos (issue #73)
# REMOVER: # TODO: Remover continue-on-error apos corrigir 27 testes falhando (issue #48)
```

Esses TODOs ja foram resolvidos pelo Epic 01.

### Definition of Done
- [ ] Zero TODOs obsoletos no CI
- [ ] Comentarios restantes sao relevantes (como o de mypy)
