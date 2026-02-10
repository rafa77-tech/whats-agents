---
name: qa-gate
description: Quick pre-merge QA check em menos de 5 minutos. Use como sanity check antes de qualquer merge. Se a mudança for complexa ou de alto risco, escale para code-review completo.
---

# QA Gate — Quick Pre-Merge Check

Review rápido (<5 min) focado em pegar problemas óbvios antes do merge.

## Processo

### 1. Scan Rápido — Categorizar arquivos

- 🔴 **Crítico**: auth, pagamentos, dados sensíveis, migrations, configs de prod
- 🟡 **Importante**: lógica de negócio, APIs, integrações
- 🟢 **Normal**: UI, docs, testes, configs de dev

### 2. Checklist Express

**Security P0:**
- [ ] Sem secrets/credentials no código?
- [ ] Input validation nos entry points?
- [ ] Auth/authz corretos?

**Correctness P1:**
- [ ] Lógica faz o que deveria?
- [ ] Null/empty/edge cases tratados?
- [ ] Error handling presente?

**Tests P2:**
- [ ] Testes existem para a mudança?
- [ ] Testes passam?

**Clean Code P3:**
- [ ] Consistente com patterns do projeto?
- [ ] Sem código morto ou debug?

### 3. Veredito

| Veredito | Significado |
|----------|-------------|
| ✅ **LGTM** | Pode mergear |
| ⚠️ **LGTM com notas** | Pode mergear, mas atenção aos pontos levantados |
| 🔍 **Precisa review completo** | Escalar para skill code-review |
| 🔴 **Blocker** | Não mergear — problema encontrado |

### Output

```
QA Gate: [descrição curta]
Arquivos: [N] (🔴 X / 🟡 X / 🟢 X)
Veredito: [veredito]
[findings, se houver — máximo 3-5 itens]
```
