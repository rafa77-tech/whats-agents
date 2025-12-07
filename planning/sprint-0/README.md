# Sprint 0: Setup & Configuração

## Status: COMPLETO ✅ (07/12/2025)

## Objetivo da Sprint

> **Todas as integrações externas funcionando e validadas antes de escrever código de negócio.**

Ao final desta sprint, você deve conseguir:
- ✅ Enviar uma mensagem via Evolution API
- ✅ Receber uma resposta do Claude
- ✅ Ver uma mensagem no Chatwoot
- ✅ Receber uma notificação no Slack
- ✅ Consultar dados no Supabase

---

## Métricas de Sucesso

| Métrica | Meta | Resultado |
|---------|------|-----------|
| APIs funcionando | 100% (4/4) | ✅ 100% |
| Dados básicos cadastrados | Hospitais, vagas, médicos | ✅ 85 hosp, 4.973 vagas, 29.645 médicos |
| Estrutura do projeto | FastAPI rodando | ✅ Funcionando |

---

## Epics

| Epic | Nome | Stories | Status |
|------|------|---------|--------|
| E1 | [Integrações](./epic-01-integracoes.md) | 8 | ✅ COMPLETO |
| E2 | [Dados](./epic-02-dados.md) | 4 | ✅ COMPLETO |
| E3 | [Estrutura do Projeto](./epic-03-estrutura.md) | 5 | ✅ COMPLETO |

---

## Resumo das Stories

### Epic 1: Integrações

| ID | Story | Responsável | Status |
|----|-------|-------------|--------|
| S0.E1.1 | Obter API Key Anthropic | Gestor | ✅ |
| S0.E1.2 | Testar chamada Claude API | Dev | ✅ |
| S0.E1.3 | Conectar WhatsApp Evolution | Gestor | ✅ |
| S0.E1.4 | Testar envio/recebimento Evolution | Dev | ✅ |
| S0.E1.5 | Configurar conta Chatwoot | Gestor | ✅ |
| S0.E1.6 | Criar inbox e testar Chatwoot | Dev | ✅ |
| S0.E1.7 | Criar webhook Slack | Gestor | ✅ |
| S0.E1.8 | Testar envio Slack | Dev | ✅ |

### Epic 2: Dados

| ID | Story | Responsável | Resultado |
|----|-------|-------------|-----------|
| S0.E2.1 | Seed de dados auxiliares | Dev | ✅ 56 esp, 9 set, 6 per |
| S0.E2.2 | Cadastrar hospitais | Gestor | ✅ 85 hospitais |
| S0.E2.3 | Cadastrar vagas reais | Gestor | ✅ 4.973 vagas |
| S0.E2.4 | Selecionar médicos piloto | Dev | ✅ 100 médicos |

### Epic 3: Estrutura do Projeto

| ID | Story | Responsável | Status |
|----|-------|-------------|--------|
| S0.E3.1 | Criar estrutura FastAPI | Dev | ✅ |
| S0.E3.2 | Configurar cliente Supabase | Dev | ✅ |
| S0.E3.3 | Configurar cliente Anthropic | Dev | ✅ |
| S0.E3.4 | Configurar cliente Evolution | Dev | ✅ |
| S0.E3.5 | Criar arquivo .env completo | Dev | ✅ |

---

## Ordem de Execução Sugerida

```
Dia 1:
├── [Gestor] S0.E1.1 - API Key Anthropic
├── [Gestor] S0.E1.3 - Conectar WhatsApp
├── [Gestor] S0.E1.5 - Conta Chatwoot
├── [Gestor] S0.E1.7 - Webhook Slack
│
├── [Dev] S0.E3.1 - Estrutura FastAPI
└── [Dev] S0.E3.2 - Cliente Supabase

Dia 2:
├── [Dev] S0.E1.2 - Testar Claude
├── [Dev] S0.E1.4 - Testar Evolution
├── [Dev] S0.E1.6 - Testar Chatwoot
├── [Dev] S0.E1.8 - Testar Slack
│
└── [Dev] S0.E2.1 - Seed dados

Dia 3:
├── [Gestor] S0.E2.2 - Cadastrar hospitais
├── [Gestor] S0.E2.3 - Cadastrar vagas
│
├── [Dev] S0.E3.3 - Cliente Anthropic
├── [Dev] S0.E3.4 - Cliente Evolution
├── [Dev] S0.E2.4 - Selecionar médicos
└── [Dev] S0.E3.5 - Arquivo .env
```

---

## Definition of Done (Sprint)

A sprint só está completa quando:

- [x] Todas as 17 stories com DoD completo
- [x] `curl` para Evolution envia mensagem com sucesso
- [x] `curl` para Claude retorna resposta
- [x] Chatwoot mostra inbox configurado
- [x] Slack recebe mensagem de teste
- [x] Supabase tem: especialidades, setores, períodos, hospitais, vagas
- [x] FastAPI roda sem erros
- [x] Arquivo `.env` com todas as variáveis

**Sprint DoD: COMPLETO** ✅

---

## Bloqueantes

| Bloqueante | Impacto | Ação |
|------------|---------|------|
| Sem cartão de crédito para Anthropic | Bloqueia Claude | Gestor resolve |
| Número WhatsApp em uso | Bloqueia Evolution | Usar número novo |
| Chatwoot não inicia | Bloqueia supervisão | Ver logs Docker |

---

## Próximos Passos

1. Comece pelo [Epic 1: Integrações](./epic-01-integracoes.md)
2. Devs podem começar [Epic 3: Estrutura](./epic-03-estrutura.md) em paralelo
3. Quando Epic 1 estiver pronto, Gestor faz [Epic 2: Dados](./epic-02-dados.md)
