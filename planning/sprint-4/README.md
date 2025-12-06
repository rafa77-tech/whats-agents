# Sprint 4: Piloto Restrito

## Objetivo da Sprint

> **Validar Júlia com 100 médicos reais de forma controlada.**

Ao final desta sprint:
- Piloto rodando com 100 médicos
- Métricas de qualidade sendo coletadas
- Sistema de feedback do gestor funcionando
- Monitoramento em tempo real

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de resposta médicos | > 30% |
| Taxa de detecção como bot | < 5% |
| Satisfação (feedback gestor) | > 4/5 |
| Uptime | > 99% |
| Handoffs por 100 conversas | < 10 |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Sistema de Métricas](./epic-01-metricas.md) | 5 | P0 |
| E2 | [Feedback do Gestor](./epic-02-feedback.md) | 4 | P0 |
| E3 | [Execução do Piloto](./epic-03-piloto.md) | 5 | P0 |

---

## Resumo das Stories

### Epic 1: Sistema de Métricas

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S4.E1.1 | Dashboard de métricas básico | 3h | 🔴 |
| S4.E1.2 | Coletar métricas de conversa | 2h | 🔴 |
| S4.E1.3 | Coletar métricas de qualidade | 2h | 🔴 |
| S4.E1.4 | Alertas de anomalias | 2h | 🔴 |
| S4.E1.5 | Relatório diário automático | 2h | 🔴 |

### Epic 2: Feedback do Gestor

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S4.E2.1 | Interface de avaliação de conversas | 3h | 🔴 |
| S4.E2.2 | Sistema de notas e tags | 2h | 🔴 |
| S4.E2.3 | Sugestões de melhoria do prompt | 2h | 🔴 |
| S4.E2.4 | Integrar feedback no treinamento | 2h | 🔴 |

### Epic 3: Execução do Piloto

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S4.E3.1 | Selecionar 100 médicos piloto | 2h | 🔴 |
| S4.E3.2 | Configurar rate limiting para piloto | 1h | 🔴 |
| S4.E3.3 | Criar campanha de primeiro contato | 2h | 🔴 |
| S4.E3.4 | Executar piloto com monitoramento | 3h | 🔴 |
| S4.E3.5 | Análise de resultados do piloto | 3h | 🔴 |

---

## Definition of Done (Sprint)

- [ ] 100 médicos receberam primeira mensagem
- [ ] Taxa de resposta medida
- [ ] Taxa de detecção como bot medida
- [ ] Dashboard com métricas em tempo real
- [ ] Sistema de feedback funcionando
- [ ] Relatório diário sendo enviado
- [ ] Pelo menos 30% de taxa de resposta

---

## Teste de Aceitação

```
CENÁRIO: Piloto Funciona
DADO que 100 médicos foram selecionados
QUANDO Júlia envia primeira mensagem
ENTÃO pelo menos 30 médicos respondem
E menos de 2 detectam que é bot
E sistema registra todas as métricas

CENÁRIO: Feedback Funciona
DADO que conversa foi encerrada
QUANDO gestor avalia a conversa
ENTÃO avaliação é salva
E sugestões de melhoria são registradas
E relatório reflete o feedback
```
