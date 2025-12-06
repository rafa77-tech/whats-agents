# Sprint 3: Testes & Ajustes de Persona

## Objetivo da Sprint

> **Júlia passa no "teste de Turing" - médicos não percebem que é IA.**

Ao final desta sprint:
- Persona testada com mensagens reais
- Ajustes de timing parecem humanos
- Tratamento de edge cases robusto
- Métricas de qualidade implementadas

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de detecção como bot | < 5% |
| Tempo de resposta | 20-60s (variável) |
| Respostas coerentes | > 95% |
| Edge cases tratados | 100% |

---

## Epics

| Epic | Nome | Stories | Prioridade |
|------|------|---------|------------|
| E1 | [Testes de Persona](./epic-01-persona.md) | 5 | P0 |
| E2 | [Humanização de Timing](./epic-02-timing.md) | 4 | P0 |
| E3 | [Edge Cases](./epic-03-edge-cases.md) | 5 | P0 |

---

## Resumo das Stories

### Epic 1: Testes de Persona

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S3.E1.1 | Criar suite de testes de persona | 3h | 🔴 |
| S3.E1.2 | Testes de linguagem informal | 2h | 🔴 |
| S3.E1.3 | Testes de consistência de identidade | 2h | 🔴 |
| S3.E1.4 | Testes de resistência a provocação | 2h | 🔴 |
| S3.E1.5 | Ajustar prompt baseado em testes | 3h | 🔴 |

### Epic 2: Humanização de Timing

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S3.E2.1 | Implementar delay variável | 2h | 🔴 |
| S3.E2.2 | Simular tempo de digitação | 1h | 🔴 |
| S3.E2.3 | Quebrar mensagens longas | 2h | 🔴 |
| S3.E2.4 | Respeitar horário comercial | 2h | 🔴 |

### Epic 3: Edge Cases

| ID | Story | Estimativa | Status |
|----|-------|------------|--------|
| S3.E3.1 | Tratar mensagens de áudio | 2h | 🔴 |
| S3.E3.2 | Tratar mensagens de imagem | 2h | 🔴 |
| S3.E3.3 | Tratar opt-out | 2h | 🔴 |
| S3.E3.4 | Tratar mensagens muito longas | 1h | 🔴 |
| S3.E3.5 | Tratar erros de API graciosamente | 2h | 🔴 |

---

## Definition of Done (Sprint)

- [ ] Suite de testes de persona funciona
- [ ] Timing de resposta varia naturalmente
- [ ] Mensagens longas quebradas em várias
- [ ] Áudio e imagem tratados graciosamente
- [ ] Opt-out funciona imediatamente
- [ ] Erros não quebram a experiência
- [ ] Taxa de detecção como bot < 5%

---

## Teste de Aceitação

```
CENÁRIO: Teste de Turing
DADO que médico nunca conversou com Júlia
QUANDO ele envia mensagens por 5 minutos
ENTÃO ele não percebe que é uma IA
E as respostas são naturais e coerentes
E o timing parece humano

CENÁRIO: Provocação
DADO que médico pergunta "você é um robô?"
QUANDO Júlia responde
ENTÃO ela não revela que é IA
E mantém persona consistente
E desvia naturalmente do assunto
```
