# Skills Auto-Activation

## Skills Disponíveis

Este projeto possui skills em `.claude/skills/` que DEVEM ser consultadas automaticamente conforme o contexto da tarefa. Não espere o usuário pedir — ative proativamente.

### Regras de Ativação

#### Antes de implementar qualquer código:
- Leia `.claude/skills/dev-standards/SKILL.md` e siga o Passo 0 (Context Loading)
- Carregue arquitetura, coding standards, e código adjacente ANTES de escrever código

#### Ao criar ou modificar tabelas, migrations, access control policies, ou queries SQL:
- Leia `.claude/skills/db-review/SKILL.md`
- Nova tabela: siga `*schema-design`
- Migration: siga `*migration-review` antes de propor
- Query com performance relevante: aplique `*query-review`

#### Ao fazer code review ou antes de sugerir merge:
- Leia `.claude/skills/qa-gate/SKILL.md` e aplique o quick check
- Mudança grande ou toca dados sensíveis: use `.claude/skills/code-review/SKILL.md`

#### Ao tomar decisão técnica:
- Leia `.claude/skills/architect/SKILL.md`
- Comparar opções: `*evaluate`
- Decisão que merece registro: sugira `*adr`

#### Ao planejar testes ou avaliar cobertura:
- Leia `.claude/skills/test-architect/SKILL.md`
- Aplique risk scoring para determinar profundidade

#### Ao criar documentação:
- Leia `.claude/skills/tech-writer/SKILL.md` e siga o template

#### Ao adicionar integração, endpoint público, ou mudar auth:
- Leia `.claude/skills/security-review/SKILL.md`
- Nova integração: `*threat-model`
- Mudança em auth: `*auth-review`
- Endpoint que retorna dados: considere `*data-exposure`

#### Ao discutir features, priorização, ou valor de negócio:
- Leia `.claude/skills/product-review/SKILL.md`
- SEMPRE carregue o business model do projeto primeiro (Passo 0)
- Feature nova: `*feature-eval` antes de design técnico
- Priorização: `*prioritize`

#### Ao planejar sprints, quebrar features em tarefas, ou criar épicos:
- Leia `.claude/skills/sprint-planner/SKILL.md`
- Sprint nova: `*sprint` para planejar, depois `*epic` para detalhar
- Feature grande: `*breakdown` para quebrar em tarefas estimáveis
- Combine com `product-review (*prioritize)` para definir o que entra na sprint

### Prioridade por Tarefa

| Tarefa | Skills (em ordem) |
|--------|-------------------|
| Implementar feature | dev-standards → test-architect (*risk) → qa-gate |
| Bug fix | dev-standards (*fix) → qa-gate |
| Nova tabela / migration | db-review → dev-standards |
| Refactoring | dev-standards (*refactor) → code-review |
| Decisão técnica | architect (*evaluate / *adr) |
| Review de PR | qa-gate → code-review (se complexo) |
| Release / deploy | test-architect (*gate) → security-review (*security-gate) → tech-writer (*changelog) |
| Nova integração | security-review (*threat-model) → dev-standards |
| Mudança em auth | security-review (*auth-review) → code-review |
| Feature nova (ideia → código) | product-review (*feature-eval) → architect (*system-design) → test-architect (*risk) → dev-standards |
| Sprint planning | product-review (*prioritize) → sprint-planner (*sprint) → sprint-planner (*epic) |
| Audit de segurança | security-review (*owasp-check) → db-review (*rls-audit) → code-review |
| Documentação | tech-writer |

### Princípios Sempre Ativos

1. **Access control obrigatório** em qualquer tabela com dados sensíveis
2. **Constraints no banco** — validação no app é complementar, não substituta
3. **Índices em FK** — PostgreSQL não cria automaticamente, sempre criar
4. **Testes proporcionais ao risco** — mais testes onde mais pode dar errado
5. **Context loading antes de código** — ler código adjacente antes de implementar
6. **Migrations reversíveis** — sempre com UP e DOWN
7. **Não inventar patterns** — seguir os existentes, ou propor ADR para mudar
8. **Secrets nunca no client** — API keys, tokens internos: apenas server-side
9. **Input é hostil** — tudo do browser, app, ou webhook deve ser validado
