# Sprint 5: Expansão

## Objetivo da Sprint

> **Escalar Júlia para 1000+ médicos com múltiplas especialidades.**

Ao final desta sprint:
- Sistema rodando com 1000+ médicos
- Múltiplas especialidades suportadas
- Campanhas automatizadas funcionando
- Monitoramento e alertas robustos

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Médicos ativos | > 1000 |
| Especialidades | >= 5 |
| Taxa de resposta | > 30% |
| Uptime | > 99.5% |
| Tempo de resposta | < 30s |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Múltiplas Especialidades](./epic-01-especialidades.md) | 4 | P0 |
| E2 | [Campanhas Automatizadas](./epic-02-campanhas.md) | 5 | P0 |
| E3 | [Escalabilidade](./epic-03-escalabilidade.md) | 4 | P0 |

---

## Resumo das Stories

### Epic 1: Múltiplas Especialidades

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S5.E1.1 | Adaptar prompt por especialidade | 3h | 🔴 |
| S5.E1.2 | Carregar vagas por especialidade | 2h | 🔴 |
| S5.E1.3 | Cadastrar hospitais por região | 2h | 🔴 |
| S5.E1.4 | Testar com novas especialidades | 2h | 🔴 |

### Epic 2: Campanhas Automatizadas

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S5.E2.1 | Sistema de filas de envio | 3h | 🔴 |
| S5.E2.2 | Agendador de campanhas | 2h | 🔴 |
| S5.E2.3 | Follow-up automático | 3h | 🔴 |
| S5.E2.4 | Segmentação de médicos | 2h | 🔴 |
| S5.E2.5 | Relatório de campanhas | 2h | 🔴 |

### Epic 3: Escalabilidade

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S5.E3.1 | Otimizar queries do banco | 3h | 🔴 |
| S5.E3.2 | Implementar cache Redis | 3h | 🔴 |
| S5.E3.3 | Monitoramento de performance | 2h | 🔴 |
| S5.E3.4 | Documentação de operações | 2h | 🔴 |

---

## Definition of Done (Sprint)

- [ ] Pelo menos 5 especialidades configuradas
- [ ] Campanhas podem ser agendadas
- [ ] Follow-up automático funcionando
- [ ] Sistema suporta 1000+ médicos
- [ ] Tempo de resposta < 30s em carga
- [ ] Documentação completa

---

## Teste de Aceitação

```
CENÁRIO: Múltiplas Especialidades
DADO que tenho médicos de 5 especialidades
QUANDO Júlia conversa com cada um
ENTÃO ela usa contexto correto da especialidade
E oferece vagas adequadas

CENÁRIO: Escala
DADO que sistema tem 1000 médicos cadastrados
QUANDO 50 médicos mandam mensagem simultaneamente
ENTÃO todas as respostas são enviadas em < 30s
E nenhum erro ocorre
```
