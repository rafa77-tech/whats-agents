# Dev Skills para Claude Code

Skills de qualidade e produtividade para Claude Code, inspiradas no [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD). Agnósticas de stack — o contexto específico do projeto fica no `CLAUDE.md`.

## Skills

### QA & Quality
| Skill | Propósito |
|-------|-----------|
| **code-review/** | Senior code review com risk scoring |
| **test-architect/** | Test strategy risk-based + quality gates |
| **qa-gate/** | Quick pre-merge check (<5 min) |

### Architecture & Development
| Skill | Propósito |
|-------|-----------|
| **architect/** | ADRs, trade-off analysis, system design, tech debt |
| **dev-standards/** | Implementation guide com context loading |
| **tech-writer/** | API docs, runbooks, onboarding, READMEs, changelogs |

### Database
| Skill | Propósito |
|-------|-----------|
| **db-review/** | Schema review, access control audit, performance, migrations |

### Security
| Skill | Propósito |
|-------|-----------|
| **security-review/** | Threat modeling (STRIDE), OWASP Top 10, auth, data exposure, compliance |

### Product & Planning
| Skill | Propósito |
|-------|-----------|
| **product-review/** | Feature eval, prioritização, product-market fit, metrics mapping |
| **sprint-planner/** | Sprint planning, épicos granulares, feature breakdown, DoD |

## Instalação

```
.claude/skills/
├── code-review/SKILL.md
├── test-architect/SKILL.md
├── qa-gate/SKILL.md
├── architect/SKILL.md
├── dev-standards/SKILL.md
├── tech-writer/SKILL.md
├── db-review/SKILL.md
├── security-review/SKILL.md
├── product-review/SKILL.md
└── sprint-planner/SKILL.md
```

Adicionar o conteúdo de `CLAUDE-SKILLS-BLOCK.md` ao `CLAUDE.md` do projeto.

## Comandos

### code-review
Review completo com veredito PASS/CONCERNS/FAIL.

### test-architect
`*risk` · `*test-design` · `*trace` · `*nfr` · `*gate`

### qa-gate
Quick check com veredito LGTM/Blocker.

### architect
`*adr` · `*evaluate` · `*review-arch` · `*system-design` · `*debt`

### dev-standards
`*implement` · `*refactor` · `*fix` · `*standards`

### tech-writer
`*api-docs` · `*readme` · `*runbook` · `*onboarding` · `*changelog` · `*docs-audit`

### db-review
`*db-review` · `*db-quick` · `*rls-audit` · `*migration-review` · `*query-review` · `*schema-design`

### security-review
`*threat-model` · `*owasp-check` · `*auth-review` · `*data-exposure` · `*dependency-audit` · `*compliance-check` · `*infra-review` · `*security-gate`

### product-review
`*feature-eval` · `*prioritize` · `*product-fit` · `*value-check` · `*metrics-map` · `*stakeholder-impact`

### sprint-planner
`*sprint` · `*epic` · `*breakdown`

## Fluxo por Complexidade

| Cenário | Skills |
|---------|--------|
| Bug fix | `qa-gate` |
| Feature pequena | `*implement` → `qa-gate` |
| Feature média | `*risk` → `*test-design` → `*implement` → `code-review` |
| Feature grande | `*feature-eval` → `*system-design` → `*risk` → `*test-design` → `*implement` → `code-review` |
| Decisão técnica | `*evaluate` → `*adr` |
| Release | `*nfr` → `*gate` → `*security-gate` → `*changelog` |
| Nova migration | `*migration-review` |
| Audit de segurança | `*threat-model` → `*owasp-check` → `*rls-audit` |
| Sprint planning | `*prioritize` → `*sprint` → `*epic` |
| Novo dev | `*onboarding` |
| Tech debt | `*debt` → `*refactor` |

## Créditos

Baseado em conceitos do [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) (MIT License) por BMad Code, LLC.
