# Documentação Técnica - Agente Julia

Escalista virtual autônoma para staffing médico da Revoluna. Sistema de IA que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp.

**Objetivo:** Passar no teste de Turing - médicos não devem perceber que estão falando com IA.

---

## Quick Start (< 5 minutos)

Para começar a desenvolver ou operar Julia:

```bash
# 1. Preparar ambiente
git clone <repo> && cd whatsapp-api
uv sync

# 2. Configurar variáveis
cp .env.example .env
# Editar .env com credenciais (Supabase, Evolution, Slack, etc)

# 3. Subir dependências
docker compose up -d

# 4. Rodar API
uv run uvicorn app.main:app --reload --port 8000

# 5. Verificar saúde
curl http://localhost:8000/health
```

**Documentação do setup completo:** [docs/setup/setup.md](./setup/setup.md)

---

## Mapa de Documentação

### Para Desenvolvedores

**Comece aqui se você vai implementar features ou corrigir bugs:**

| Documentação | Conteúdo |
|---|---|
| [Visão Geral da Arquitetura](./arquitetura/visao-geral.md) | Diagrama do sistema, componentes, fluxos principais |
| [API e Endpoints (28 routers)](./arquitetura/api-endpoints.md) | Referência completa de todos os endpoints REST |
| [Serviços (267 módulos)](./arquitetura/servicos.md) | Arquitetura dos serviços, dependências, padrões |
| [Banco de Dados (64+ tabelas)](./arquitetura/banco-de-dados.md) | Schema PostgreSQL, relacionamentos, índices, RLS |
| [Pipeline de Processamento](./arquitetura/pipeline-processamento.md) | Fluxo de mensagem: webhook → processamento → resposta |
| [Lógica de Negócio](./arquitetura/logica-negocio.md) | Fluxos de negócio, regras, validações críticas |
| [Convenções de Código](../app/CONVENTIONS.md) | Padrões de nomenclatura, imports, exceptions |

**Para integração com sistemas externos:**

| Documentação | Sistema |
|---|---|
| [Evolution API - Quick Ref](./integracoes/evolution-api-quickref.md) | WhatsApp (webhooks, mensagens, status) |
| [Evolution API - Webhooks](./integracoes/evolution-api-webhooks.md) | Payloads de evento e tratamento |
| [Chatwoot API - Quick Ref](./integracoes/chatwoot-api-quickref.md) | Supervisão (conversas, handoff) |
| [Chatwoot - Webhooks](./integracoes/chatwoot-webhooks.md) | Eventos de integração |
| [Railway - Quick Ref](./integracoes/railway-quickref.md) | Deploy (CLI, logs, auto-deploy) |
| [Railway - Deploy Details](./integracoes/railway-deploy.md) | Troubleshooting, rollback, variáveis |
| [Salvy - Quick Ref](./integracoes/salvy-quickref.md) | Números virtuais (ativação, webhooks) |
| [Slack - Lógica de Negócio](./integracoes/slack-logica-negocio.md) | Notificações, comandos, sessões |

**Testes e Qualidade:**

| Documentação | Foco |
|---|---|
| [Testes Manuais (Playbook)](./operacao/TEST-PLAYBOOK.md) | Procedimentos de teste antes do deploy |
| [Testes Manuais (Guia)](./operacao/testes-manuais.md) | Cenários, workflows, validações |

---

### Para Operadores (SRE/DevOps/Suporte)

**Comece aqui se você vai manter, monitorar ou fazer deploy:**

| Documentação | Conteúdo |
|---|---|
| [Runbook de Produção](./operacao/runbook.md) | Procedimentos operacionais, troubleshooting, escalação |
| [Runbook Sprint 32](./operacao/runbook-sprint32.md) | Procedimentos específicos da sprint 32 |
| [Deploy Prod - Relatório](./operacao/deploy-prod-report.md) | Histórico de deploys, lições aprendidas |
| [Canary Deployment (Governança)](./setup/producao-canary.md) | Governance de rollout em produção |
| [Deploy & Docker](./setup/deploy.md) | Docker compose, Railway, monitoramento |
| [Workers & Jobs](./operacao/workers.md) | Jobs assíncronos, scheduler, troubleshooting |
| [ENV Contract](./operacao/ENV-CONTRACT.md) | Variáveis de ambiente obrigatórias e opcionais |
| [Guardrails Queries](./operacao/guardrails-queries.md) | Queries de auditoria e monitoramento |

**Integração com sistemas:**

| Documentação | Sistema |
|---|---|
| [Railway Deploy](./integracoes/railway-deploy.md) | Produção, logs, rollback |
| [Evolution API - Webhooks](./integracoes/evolution-api-webhooks.md) | Monitoramento de eventos |
| [Chatwoot - Webhooks](./integracoes/chatwoot-webhooks.md) | Integração, eventos |

**Playbooks operacionais:**

| Documentação | Procedimento |
|---|---|
| [Handoff (Procedimentos)](./operacao/playbook-handoff.md) | Bridge médico-divulgador, escalação |

---

### Para Product/Business (PMs, Gestores)

**Comece aqui se você vai entender capacidades, planejar features ou acompanhar métricas:**

| Documentação | Conteúdo |
|---|---|
| [Relatório Executivo Julia](../manual-julia-completo.md) | Visão executiva completa, métricas, roadmap (START HERE) |
| [Manual Operacional Completo](../manual-julia-completo.md) | Guia completo Julia: setup, operação, troubleshooting |
| [Análise Arquitetural Completa (Feb 2026)](./auditorias/analise-arquitetural-completa-2026-02.md) | Estado do sistema, decisões técnicas, debt |
| [Lógica de Negócio](./arquitetura/logica-negocio.md) | Fluxos, regras, políticas |
| [Business Events (17+ tipos)](./arquitetura/business-events.md) | Event-driven architecture, funil de conversão |

**Campanha e Templates:**

| Documentação | Conteúdo |
|---|---|
| [Sistema de Campanhas](./arquitetura/campanhas.md) | Design, tipos, execução, métricas |
| [Schema Campanhas](./arquitetura/schema-campanhas.md) | Banco de dados de campanhas |
| [Migracao Campanhas (Código)](./arquitetura/migracao-campanhas-codigo.md) | Implementação técnica |
| [Templates de Campanha](./templates/campaign-templates.md) | Discovery, Oferta, Reativação, Follow-up, Feedback |

**Julia (Persona e Voice):**

| Documentação | Conteúdo |
|---|---|
| [Persona Julia](./julia/persona-julia.md) | Identidade, tom, estilo, exemplos |
| [Sistema de Prompts](./julia/sistema-prompts.md) | Organização, planejamento, design |
| [Cobertura de Prompts](./julia/prompt-coverage.md) | Cenários cobertos, gaps |
| [Briefings (Google Docs)](./julia/briefings.md) | Como funcionam, uso, boas práticas |
| [Comportamentos](./julia/comportamentos.md) | Ações, reações, personalidade |

**Warming & Chips:**

| Documentação | Conteúdo |
|---|---|
| [Julia Warmer & Chips](./arquitetura/julia-warmer-chips.md) | Sistema de aquecimento, chip orchestration, SLA |

**Dashboard & UX:**

| Documentação | Conteúdo |
|---|---|
| [Navegação do Dashboard](./arquitetura/navegacao-dashboard.md) | Arquitetura, seções, componentes |
| [UX Frontend Checklist](./ux/frontend-ux-checklist.md) | Validações, A11y, performance |
| [CI/CD Dashboard](./setup/dashboard-cicd.md) | Pipeline, validações, deployment |

**Auditorias & Análises:**

| Documentação | Conteúdo |
|---|---|
| [Auditoria de Processos](./auditorias/auditoria-processos.md) | Compliance, controles, riscos |
| [Auditoria Técnica](./auditorias/auditoria-tecnica.md) | Code quality, segurança, performance |
| [NFR Assessment (Feb 2026)](./auditorias/nfr-assessment-2026-02-09.md) | Requisitos não-funcionais, métricas |
| [Feature Analysis](./arquitetura/feature-analysis.md) | Análise de requisitos, casos de uso |

---

## Índice Completo por Categoria

### Arquitetura (13 documentos)

| Arquivo | Descrição | Audience |
|---|---|---|
| [visao-geral.md](./arquitetura/visao-geral.md) | Diagrama do sistema, componentes, fluxos | Dev, PM |
| [api-endpoints.md](./arquitetura/api-endpoints.md) | Referência de 28 routers (GET, POST, PUT, DELETE) | Dev |
| [banco-de-dados.md](./arquitetura/banco-de-dados.md) | Schema PostgreSQL, 64+ tabelas, índices, RLS | Dev, DBA |
| [servicos.md](./arquitetura/servicos.md) | 267 módulos de serviço, arquitetura, padrões | Dev |
| [logica-negocio.md](./arquitetura/logica-negocio.md) | Fluxos, regras, políticas, validações | Dev, PM |
| [pipeline-processamento.md](./arquitetura/pipeline-processamento.md) | Webhook → parser → LLM → resposta | Dev |
| [campanhas.md](./arquitetura/campanhas.md) | Sistema de campanhas, tipos, execução | Dev, PM |
| [schema-campanhas.md](./arquitetura/schema-campanhas.md) | Banco de dados: campanhas, envios, execuções | Dev |
| [migracao-campanhas-codigo.md](./arquitetura/migracao-campanhas-codigo.md) | Guia de migração, implementação | Dev |
| [business-events.md](./arquitetura/business-events.md) | 17+ tipos de eventos, emissores, subscribers | Dev, PM |
| [julia-warmer-chips.md](./arquitetura/julia-warmer-chips.md) | Warming system, chip orchestration | Dev, PM |
| [navegacao-dashboard.md](./arquitetura/navegacao-dashboard.md) | Dashboard: seções, navegação, componentes | Dev, PM |
| [feature-analysis.md](./arquitetura/feature-analysis.md) | Análise de requisitos, casos de uso, critérios | PM |

### Operação (10 documentos)

| Arquivo | Descrição | Audience |
|---|---|---|
| [runbook.md](./operacao/runbook.md) | Procedimentos operacionais, troubleshooting | Ops, Support |
| [runbook-sprint32.md](./operacao/runbook-sprint32.md) | Procedimentos específicos Sprint 32 | Ops, Support |
| [testes-manuais.md](./operacao/testes-manuais.md) | Guia de testes, cenários, workflows | QA, Dev |
| [TEST-PLAYBOOK.md](./operacao/TEST-PLAYBOOK.md) | Playbook de testes antes do deploy | QA, Dev |
| [playbook-handoff.md](./operacao/playbook-handoff.md) | Bridge médico-divulgador, escalação | Ops, Support |
| [deploy-prod-report.md](./operacao/deploy-prod-report.md) | Histórico de deploys, lições aprendidas | Ops |
| [workers.md](./operacao/workers.md) | Jobs assíncronos, scheduler, debugging | Dev, Ops |
| [ENV-CONTRACT.md](./operacao/ENV-CONTRACT.md) | Variáveis de ambiente, contratos | Dev, Ops |
| [guardrails-queries.md](./operacao/guardrails-queries.md) | Queries de auditoria e monitoramento | Ops, Dev |
| [piloto-campanha-discovery.md](./operacao/piloto-campanha-discovery.md) | Piloto de discovery, métricas | PM, Ops |

### Setup & Deploy (5 documentos)

| Arquivo | Descrição | Audience |
|---|---|---|
| [setup.md](./setup/setup.md) | Checklist de setup local com status | Dev |
| [configuracao.md](./setup/configuracao.md) | Guia de configuração, variáveis | Dev, Ops |
| [deploy.md](./setup/deploy.md) | Docker, Railway, monitoramento | Ops, Dev |
| [producao-canary.md](./setup/producao-canary.md) | Governance de rollout em produção | Ops |
| [dashboard-cicd.md](./setup/dashboard-cicd.md) | CI/CD pipeline do dashboard (Next.js) | Dev, Ops |

### Integrações (11 documentos)

| Arquivo | Descrição | Sistema |
|---|---|---|
| [README.md](./integracoes/README.md) | Overview de todas as integrações | All |
| [evolution-api-quickref.md](./integracoes/evolution-api-quickref.md) | Endpoints, auth, exemplos | WhatsApp |
| [evolution-api-webhooks.md](./integracoes/evolution-api-webhooks.md) | Payloads, eventos, tratamento | WhatsApp |
| [chatwoot-api-quickref.md](./integracoes/chatwoot-api-quickref.md) | Endpoints, auth, exemplos | Chatwoot |
| [chatwoot-webhooks.md](./integracoes/chatwoot-webhooks.md) | Payloads, eventos, handoff | Chatwoot |
| [railway-quickref.md](./integracoes/railway-quickref.md) | CLI, logs, auto-deploy | Railway |
| [railway-deploy.md](./integracoes/railway-deploy.md) | Troubleshooting, rollback, variáveis | Railway |
| [salvy-quickref.md](./integracoes/salvy-quickref.md) | Endpoints, auth, números virtuais | Salvy |
| [salvy-webhooks.md](./integracoes/salvy-webhooks.md) | Webhooks de ativação, status | Salvy |
| [slack-logica-negocio.md](./integracoes/slack-logica-negocio.md) | Arquitetura, commands, notificações | Slack |
| [zapi-quickref.md](./integracoes/zapi-quickref.md) | Z-API (alternative WhatsApp) | Z-API |

### Julia - Persona & Prompts (17+ documentos)

**Núcleo:**

| Arquivo | Descrição |
|---|---|
| [README.md](./julia/README.md) | Overview do sistema Julia |
| [persona-julia.md](./julia/persona-julia.md) | Identidade, tom, estilo, exemplos de mensagens |
| [sistema-prompts.md](./julia/sistema-prompts.md) | Organização, arquitetura dos prompts |
| [prompt-coverage.md](./julia/prompt-coverage.md) | Cenários cobertos, gaps identificados |
| [comportamentos.md](./julia/comportamentos.md) | Ações, reações, personalidade |

**Briefings:**

| Arquivo | Descrição |
|---|---|
| [briefings.md](./julia/briefings.md) | Como funcionam, uso, boas práticas |
| [briefing-template.md](./julia/briefing-template.md) | Template Google Docs para gestor |

**Prompts Avançados (em julia/prompts/):**

| Arquivo | Descrição |
|---|---|
| advanced-prompts.md | Prompts avançados, customizações |
| negotiation-prompts.md | Negociação, fechamento |
| escalation-prompts.md | Escalação, handoff |

**Objeções (em julia/objecoes/):**

| Arquivo | Descrição |
|---|---|
| objecoes-catalog.md | Catálogo de 10 tipos de objeções |
| profile-guide.md | Detecção de perfil médico (7 tipos) |
| senior-errors.md | Erros comuns em sêniors, mitigação |
| handoff-triggers.md | Triggers de handoff, regras |

**Operacional (em julia/operacional/):**

| Arquivo | Descrição |
|---|---|
| scientific-foundation.md | Fundação científica: psicologia, persuasão |
| doctor-preferences.md | Preferências de médicos |
| metrics-julia.md | Métricas de desempenho Julia |
| reactivation-strategy.md | Estratégia de reativação |
| app-revoluna-guide.md | Guia do app Revoluna |

**Templates (em julia/templates/):**

| Arquivo | Descrição |
|---|---|
| opening-messages-220.md | 220 mensagens de abertura, variações |
| reference-conversations.md | Conversas de referência, best practices |

### Templates de Campanha (7 documentos)

| Arquivo | Descrição |
|---|---|
| [README.md](./templates/README.md) | Overview de templates |
| [campaign-templates.md](./templates/campaign-templates.md) | Referência de templates no Google Drive |
| discovery-template.md | Template de discovery |
| oferta-template.md | Template de oferta |
| reativacao-template.md | Template de reativação |
| followup-template.md | Template de follow-up |
| feedback-template.md | Template de feedback |

### Auditorias (7+ documentos)

| Arquivo | Descrição | Data |
|---|---|---|
| [auditoria-tecnica.md](./auditorias/auditoria-tecnica.md) | Code quality, segurança, performance | - |
| [auditoria-processos.md](./auditorias/auditoria-processos.md) | Compliance, controles, riscos | - |
| [analise-arquitetural-completa-2026-02.md](./auditorias/analise-arquitetural-completa-2026-02.md) | Estado do sistema, decisões, debt | Feb 2026 |
| [nfr-assessment-2026-02-09.md](./auditorias/nfr-assessment-2026-02-09.md) | Requisitos não-funcionais, métricas | Feb 2026 |
| [incidente-2026-01-23-campanha-sem-envio.md](./auditorias/incidente-2026-01-23-campanha-sem-envio.md) | Post-mortem: campanha não foi enviada | Jan 2026 |
| [migracao-status-fechada.md](./auditorias/migracao-status-fechada.md) | Notas sobre migrações | - |
| [sprint-18/](./auditorias/sprint-18/) | Encerramento Sprint 18 (3 docs) | - |

### Best Practices (1 documento)

| Arquivo | Descrição | Audience |
|---|---|---|
| [nextjs-typescript-rules.md](./best-practices/nextjs-typescript-rules.md) | Rules para dashboard (Next.js + TypeScript) | Dev |

### Testes (1 documento)

| Arquivo | Descrição |
|---|---|
| [external-handoff-sprint29.md](./testes/external-handoff-sprint29.md) | Testes de handoff externo |

### UX (1 documento)

| Arquivo | Descrição |
|---|---|
| [frontend-ux-checklist.md](./ux/frontend-ux-checklist.md) | Checklist de UX, A11y, performance |

### Documentos Raiz (2 documentos)

| Arquivo | Descrição |
|---|---|
| [manual-julia-completo.md](../manual-julia-completo.md) | Manual operacional completo Julia |
| [RELATORIO-EXECUTIVO-JULIA.md](../RELATORIO-EXECUTIVO-JULIA.md) | Relatório executivo para stakeholders |

### Snapshots (2026-02-01)

Análise completa do estado do projeto:
- [PROJETO.md](./snapshots/2026-02-01/PROJETO.md)
- [DESIGN_SYSTEM.md](./snapshots/2026-02-01/DESIGN_SYSTEM.md)
- [ANALISE_UX.md](./snapshots/2026-02-01/ANALISE_UX.md)
- [IA_FLUXOS.md](./snapshots/2026-02-01/IA_FLUXOS.md)
- [WIREFRAMES.md](./snapshots/2026-02-01/WIREFRAMES.md)

### Arquivo

Documentos obsoletos estão em [archive/](./archive/). Consultar quando necessário, mas **NÃO** usar como referência para nova implementação.

---

## Conceitos Críticos

### Rate Limiting (Obrigatório!)

Para evitar ban da Evolution API e WhatsApp:

| Limite | Valor | Motivo |
|--------|-------|--------|
| Mensagens/hora | 20 | WhatsApp abuse prevention |
| Mensagens/dia | 100 | WhatsApp abuse prevention |
| Intervalo entre msgs | 45-180s | Parecer natural (humano) |
| Horário permitido | 08:00 - 20:00 | Horário comercial |
| Dias permitidos | Seg-Sex | Horário comercial |

**Implementação:** `app/services/rate_limiter.py`

### Detecção de Bot (37 padrões)

Sistema monitora quando médicos suspeitam de IA:
- 37 padrões regex
- Métrica de taxa de detecção
- Alerta se > 5%
- Handoff automático em caso de detecção

**Implementação:** `app/services/bot_detection.py`

### Handoff IA ↔ Humano

Transferência automática para humano quando:
- Médico pede explicitamente
- Sentimento muito negativo (< -0.7)
- Questões jurídicas/financeiras
- Confiança baixa na resposta (<0.6)

**Fluxo:**
1. Trigger detectado
2. Julia avisa: "Vou pedir pra minha supervisora te ajudar"
3. `UPDATE conversations SET controlled_by='human'`
4. Notifica gestor no Slack
5. Gestor assume via Chatwoot
6. Julia para de responder

**Implementação:** `app/services/handoff_detector.py`, `playbook-handoff.md`

### Persona Julia - Regras Absolutas

1. NUNCA revela que é IA, bot, ou assistente virtual
2. NUNCA usa linguagem muito formal
3. NUNCA envia listas com bullet points
4. NUNCA responde instantaneamente sempre (simular humano)
5. NUNCA ignora opt-out ou reclamações

**Detalhes completos:** [julia/persona-julia.md](./julia/persona-julia.md)

---

## Stack Técnico

| Componente | Tecnologia | Status |
|------------|------------|--------|
| Backend | Python 3.13+ / FastAPI | ✅ Implementado |
| LLM Principal | Claude 3.5 Haiku | ✅ Funcionando |
| LLM Complexo | Claude 4 Sonnet | ✅ Funcionando |
| Banco de Dados | Supabase (PostgreSQL + pgvector) | ✅ Funcionando |
| WhatsApp | Evolution API | ✅ Integrado |
| Supervisão | Chatwoot | ✅ Integrado |
| Notificações | Slack | ✅ Integrado |
| Cache/Filas | Redis | ✅ Funcionando |
| Embeddings | Voyage AI | ✅ Funcionando |
| Package Manager | uv (Astral) | ✅ Configurado |
| Dashboard | Next.js + TypeScript | ✅ Implementado |

---

## Estrutura do Projeto

```
/whatsapp-api
├── CLAUDE.md                    # Instruções para Claude Code (fonte única de verdade)
├── app/
│   ├── api/routes/              # 24 routers de endpoints
│   ├── services/                # 267 módulos de serviço
│   ├── tools/                   # Tools do agente Julia
│   ├── pipeline/                # Pipeline de processamento de mensagens
│   ├── prompts/                 # Sistema de prompts dinâmicos
│   ├── workers/                 # Jobs assíncronos e scheduler
│   ├── core/                    # Config, logging, exceptions
│   ├── CONVENTIONS.md           # Convenções de código (obrigatório!)
│   └── main.py                  # FastAPI app
│
├── dashboard/                   # Frontend Next.js + TypeScript
│   ├── app/                     # Páginas, layouts, components
│   ├── lib/                     # Utilitários, hooks, types
│   └── tests/                   # E2E, unit tests
│
├── tests/                       # 2550+ testes (unit, integration)
│
├── docs/                        # Esta documentação (73+ arquivos)
│   ├── arquitetura/             # 13 docs de arquitetura
│   ├── operacao/                # 10 docs operacionais
│   ├── setup/                   # 5 docs de setup/deploy
│   ├── integracoes/             # 11 docs de integrações
│   ├── julia/                   # 17+ docs de persona/prompts
│   ├── templates/               # 7 templates de campanha
│   ├── best-practices/          # Rules e guidelines
│   ├── auditorias/              # 7+ docs de auditoria
│   ├── snapshots/               # Análise de estado (Feb 2026)
│   └── archive/                 # Docs obsoletos
│
├── planning/                    # Planejamento de sprints
│   ├── sprint-*/                # Documentação por sprint
│   └── README.md                # Roadmap
│
├── docker-compose.yml           # Evolution, Chatwoot, Redis
├── .env.example                 # Template de variáveis
├── pyproject.toml               # Dependências Python (uv)
└── README.md                    # Este arquivo
```

---

## Métricas do Projeto

| Métrica | Quantidade | Como Verificar |
|---------|------------|---|
| Arquivos Python | ~375 | `find app -name "*.py" \| wc -l` |
| Módulos de Serviço | 267 | `find app/services -name "*.py" \| wc -l` |
| Routers API | 24 | `find app/api/routes -name "*.py" \| wc -l` |
| Testes | 2550+ | `grep -r "def test_" tests/ \| wc -l` |
| Tabelas no Banco | 64+ | Consultar `docs/arquitetura/banco-de-dados.md` |
| Documentação | 73+ arquivos | `find docs -name "*.md" \| wc -l` |

---

## Serviços Locais

Ao rodar `docker compose up -d`:

| Serviço | URL | Credenciais |
|---------|-----|---|
| Evolution API | http://localhost:8080 | Ver `.env` |
| Chatwoot | http://localhost:3000 | user@example.com / password |
| Redis | localhost:6379 | Sem auth (dev) |
| Supabase (local) | Usar cloud | jyqgbzhqavgpxqacduoi |

---

## Sprints Concluídas

Histórico completo em [CLAUDE.md](../CLAUDE.md#sprints-concluídas). Sprints recentes:

| Sprint | Foco | Status |
|--------|------|--------|
| 52 | Pipeline v3: Extração LLM | ✅ Completa |
| 53 | Discovery Intelligence Pipeline | ✅ Completa |
| 56 | Message Flow Visualization | ✅ Completa |

---

## Links Úteis

**Documentação Local:**
- [CLAUDE.md](../CLAUDE.md) - Instruções para Claude Code (consultar antes de tudo!)
- [app/CONVENTIONS.md](../app/CONVENTIONS.md) - Convenções de código (obrigatório!)
- [docs/arquitetura/visao-geral.md](./arquitetura/visao-geral.md) - Visão geral da arquitetura

**Externos:**
- [Supabase Dashboard](https://supabase.com/dashboard) - Banco de dados
- [Evolution API Docs](https://doc.evolution-api.com/v2/) - WhatsApp
- [Chatwoot Docs](https://developers.chatwoot.com/) - Supervisão
- [Anthropic Docs](https://docs.anthropic.com) - Claude API
- [Railway Docs](https://docs.railway.app) - Deploy

**Para quem quer entender melhor:**
- Começar em: [docs/arquitetura/visao-geral.md](./arquitetura/visao-geral.md)
- Depois ler: [docs/integracoes/README.md](./integracoes/README.md)
- Para operação: [docs/operacao/runbook.md](./operacao/runbook.md)
- Para business: [manual-julia-completo.md](../manual-julia-completo.md)

---

## Contato e Escalação

| Tópico | Referência |
|--------|---|
| Estado do projeto | [CLAUDE.md](../CLAUDE.md) (fonte única de verdade) |
| Problemas em produção | [docs/operacao/runbook.md](./operacao/runbook.md) |
| Deploy issues | [docs/operacao/deploy-prod-report.md](./operacao/deploy-prod-report.md) |
| Incidentes | [docs/auditorias/](./auditorias/) |
| Feature requests | [docs/arquitetura/feature-analysis.md](./arquitetura/feature-analysis.md) |

---

**Documentação atualizada em 09/02/2026**

*Versão: Enterprise 1.0 | Gerada automaticamente a partir do índice de arquivos*
