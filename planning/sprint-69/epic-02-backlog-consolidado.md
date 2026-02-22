# Epic 02 — Backlog Consolidado

## Objetivo

Consolidar todos os itens de trabalho futuro espalhados pelo codebase em um documento unico e categorizado para facilitar priorizacao e planejamento de sprints futuras.

## Estimativa: 8 pontos

## Tarefas

### T1: Levantamento de itens (3 pts)

Buscar em todo o codebase por:
- `TODO`, `FIXME`, `HACK`, `XXX` em comentarios
- "Em breve", "nao implementado", "not implemented"
- "placeholder", "stub", "mock" em codigo de producao
- Itens pendentes em docs de sprint (planning/)
- Features mencionadas em docs mas nao implementadas

### T2: Categorizacao e priorizacao (3 pts)

Categorizar itens em:
- Backend (Python/FastAPI)
- Dashboard (Next.js/TypeScript)
- Infraestrutura (Docker, CI/CD, Deploy)
- Seguranca
- Testes
- Documentacao
- Inteligencia/IA
- Integracoes

Priorizar por impacto:
- P1: Critico (afeta producao)
- P2: Importante (melhoria significativa)
- P3: Desejavel (nice-to-have)

### T3: Documento final (2 pts)

**Arquivo:** `planning/backlog-consolidado.md`

Documento com:
- Sumario executivo
- Tabela por categoria com: item, arquivo, prioridade, sprint sugerida
- Total de itens por categoria e prioridade
- Recomendacoes para proximas sprints

## Criterios de Aceite

- [ ] 65+ itens identificados e catalogados
- [ ] Todos os itens tem categoria e prioridade
- [ ] Documento publicado em planning/backlog-consolidado.md
- [ ] Sumario executivo com visao geral
