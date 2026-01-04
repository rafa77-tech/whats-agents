# CLAUDE.md

Este arquivo é a **fonte única de verdade** para o Claude Code ao trabalhar neste repositório.

## Projeto: Agente Júlia

**Escalista virtual autônoma** para staffing médico da Revoluna.

Júlia é um agente de IA que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp.

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

---

## Estado Atual

**Sprint Atual:** Entre sprints (18 encerrada, 25 planejada)
**Início do Projeto:** 05/12/2025
**Última Atualização:** 31/12/2025

### Métricas do Projeto

| Recurso | Quantidade | Como verificar |
|---------|------------|----------------|
| Arquivos Python | ~220 | `find app -name "*.py" \| wc -l` |
| Módulos de serviço | ~150 | `find app/services -name "*.py" \| wc -l` |
| Tabelas no banco | ~55 | `mcp__supabase__list_tables` |
| Testes | ~1500 | `grep -r "def test_" tests/ \| wc -l` |
| Routers API | ~15 | `find app/api/routes -name "*.py" \| wc -l` |

> **Nota:** Métricas aproximadas. Rodar comandos para valores exatos.

### Sprints Concluídas

| Sprint | Foco | Status |
|--------|------|--------|
| 0 | Setup & Configuração | ✅ Completa |
| 1 | Core do Agente (webhook, LLM) | ✅ Completa |
| 2 | Vagas & Chatwoot | ✅ Completa |
| 3 | Persona & Timing | ✅ Completa |
| 4 | Métricas & Feedback | ✅ Completa |
| 5 | Campanhas & Escalabilidade | ✅ Completa |
| 6 | Multi-instância WhatsApp | ✅ Completa |
| 7 | Briefing Google Docs | ✅ Completa |
| 8 | Memória & Pipeline | ✅ Completa |
| 9 | Julia no Slack (NLP) | ✅ Completa |
| 10 | Refatoracao e Divida Tecnica | ✅ Completa |
| 11 | Briefing Conversacional | ✅ Completa |
| 12 | Deploy Produção | 📋 Planejado |
| 13 | Conhecimento Dinâmico (RAG) | ✅ Completa |
| 14 | Pipeline de Grupos WhatsApp | ✅ Completa |
| 15 | Policy Engine (Estado + Decisão) | ✅ Completa |
| 16 | Confirmação de Plantão | ✅ Completa |
| 17 | Business Events e Funil | ✅ Completa |
| 18 | Auditoria e Integridade | ✅ Completa |
| 25 | Julia Warmer (Foundation) | 📋 Planejado |
| 26 | Multi-Julia Orchestration | 📋 Planejado |

### Funcionalidades Implementadas

**Core:**
- [x] Webhook Evolution API com processamento de mensagens
- [x] Agente Julia com Claude (Haiku + Sonnet híbrido)
- [x] Sistema de tools (buscar_vagas, reservar_plantao, salvar_memoria)
- [x] Rate limiting (20/hora, 100/dia)
- [x] Circuit breaker para resiliência

**Integrações:**
- [x] Evolution API (WhatsApp)
- [x] Chatwoot (supervisão + handoff)
- [x] Slack (notificações + comandos NLP)
- [x] Google Docs (briefing automático)
- [x] Google Drive (templates de campanha)
- [x] Supabase (PostgreSQL + pgvector)

**Inteligência:**
- [x] Memória de longo prazo (RAG com embeddings)
- [x] Detecção de opt-out automática
- [x] Detecção de handoff (sentimento negativo, pedido humano)
- [x] Detecção de bot (37 padrões)
- [x] Pipeline de processamento extensível
- [x] Sistema de prompts dinâmicos
- [x] Conhecimento dinâmico (Sprint 13)
  - Indexação de 529 chunks de docs/julia/
  - Detector de objeções (10 tipos + subtipos)
  - Detector de perfil médico (7 perfis)
  - Detector de objetivo de conversa (8 objetivos)
  - Injeção automática de conhecimento no prompt

**Gestão via Slack:**
- [x] Linguagem natural para comandos
- [x] 14 tools de gestão (métricas, médicos, vagas, etc)
- [x] Confirmação antes de ações críticas
- [x] Contexto de sessão (30 min TTL)
- [x] 5 tipos de abordagem (discovery, oferta, reativação, followup, custom)

### Contexto de Mercado (Crítico)

| Aspecto | Realidade |
|---------|-----------|
| Saturação | Médicos recebem mensagens de staffing **o tempo todo** |
| Relacionamento | Todos são **contatos frios** (ninguém conhece Júlia) |
| Regulatório | Sem risco CFM para contato automatizado |
| Modelo | Apenas Revoluna (não é multi-tenant) |

**Implicação:** Qualidade > quantidade. Uma mensagem mal escrita = bloqueio.

---

## Persona: Júlia Mendes

**Esta é a ÚNICA fonte de verdade para a persona.**

| Atributo | Valor |
|----------|-------|
| Nome | Júlia Mendes |
| Idade | 27 anos |
| Cargo | Escalista |
| Empresa | Revoluna |
| Experiência | 4 anos em staffing médico |

### Tom e Estilo

**FAZ:**
- Mensagens curtas (1-2 linhas), quebra em várias
- Usa: "vc", "pra", "tá", "blz", "msg"
- Emoji com moderação (1-2 por conversa)
- Às vezes erra e corrige: "plantao* plantão"
- Responde rápido quando engajada, demora quando "ocupada"

**NÃO FAZ:**
- Mensagens longas com tudo de uma vez
- Bullet points ou listas formatadas
- Linguagem corporativa/formal
- Emojis em excesso
- Respostas instantâneas sempre

### Regras Absolutas

1. **NUNCA** revela que é IA, bot, ou assistente virtual
2. **NUNCA** usa linguagem formal demais
3. **NUNCA** envia listas com bullet points
4. **NUNCA** responde instantaneamente sempre
5. **NUNCA** ignora opt-out ou reclamações

### Exemplos de Mensagens

**Abertura (prospecção fria):**
```
Oi Dr Carlos! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas na região do ABC

Vi que vc é cardiologista né? Temos algumas vagas bem legais aqui
```

**Follow-up:**
```
Oi de novo!

Lembrei de vc pq surgiu uma vaga boa no São Luiz, plantão noturno de cardio

Seria dia 15, das 19h às 7h, R$ 2.500

Tem interesse?
```

**Fechamento:**
```
Show! Reservei pra vc então

Vou precisar de alguns docs pra finalizar, me manda por aqui mesmo que eu organizo tudo

CRM, RG e dados bancários, blz?
```

---

## Stack Tecnológico

| Componente | Tecnologia | Status |
|------------|------------|--------|
| Backend | Python 3.13+ / FastAPI | ✅ Implementado |
| Package Manager | uv (Astral) | ✅ Configurado |
| LLM Principal | Claude 3.5 Haiku | ✅ Funcionando |
| LLM Complexo | Claude 4 Sonnet | ✅ Funcionando |
| Banco de Dados | Supabase (PostgreSQL + pgvector) | ✅ Funcionando |
| WhatsApp | Evolution API | ✅ Integrado |
| Supervisão | Chatwoot | ✅ Integrado |
| Notificações | Slack | ✅ Integrado |
| Cache/Filas | Redis | ✅ Funcionando |
| Embeddings | Voyage AI | ✅ Funcionando |

### Decisões Técnicas

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Banco de dados | Supabase | Managed, pgvector nativo, API REST |
| LLM principal | Claude Haiku | $0.25/1M input, melhor custo-benefício |
| LLM complexo | Claude Sonnet | Qualidade superior para negociação |
| Estratégia LLM | Híbrida 80/20 | 80% Haiku, 20% Sonnet = 73% economia |
| WhatsApp | Evolution API | Open source, self-hosted, multi-device |

---

## Estrutura do Projeto

```
/whatsapp-api
├── CLAUDE.md                    # Este arquivo (fonte única de verdade)
├── app/
│   ├── api/routes/             # Routers de endpoints
│   ├── services/               # Módulos de serviço
│   ├── tools/                  # Tools do agente (vagas, memoria, slack)
│   ├── pipeline/               # Pipeline de processamento
│   ├── prompts/                # Sistema de prompts dinâmicos
│   ├── templates/              # Templates de mensagens
│   ├── workers/                # Scheduler e workers
│   ├── core/                   # Config, logging, exceptions
│   ├── CONVENTIONS.md          # Convenções de código
│   └── main.py                 # FastAPI app
│
├── tests/                      # Testes (ver métricas acima)
│
├── docs/                       # Documentação técnica
│   ├── arquitetura/            # Docs de arquitetura
│   ├── setup/                  # Docs de configuração
│   ├── operacao/               # Runbooks e procedimentos
│   ├── integracoes/            # APIs externas (Evolution, Chatwoot, Railway)
│   ├── julia/                  # Persona, prompts, conhecimento RAG
│   ├── templates/              # Templates de campanha
│   ├── auditorias/             # Relatórios de auditoria
│   └── archive/                # Docs obsoletos
│
├── planning/                   # Sprints e épicos
│   ├── sprint-*/               # Planejamento por sprint
│   └── README.md               # Roadmap
│
├── docker-compose.yml          # Evolution, Chatwoot, Redis
├── .env.example                # Template de variáveis
└── pyproject.toml              # Dependências Python (uv)
```

---

## Comandos Úteis

```bash
# Dependências Python
uv sync                          # Instalar
uv add <pacote>                  # Adicionar

# Docker
docker compose up -d             # Subir serviços
docker compose down              # Parar
docker compose ps                # Status
docker compose logs -f <serviço> # Logs

# Serviços locais
# Evolution API: http://localhost:8080
# Chatwoot:      http://localhost:3000
# n8n:           http://localhost:5678
# PgAdmin:       http://localhost:4000
```

### Railway CLI (Resumo)

```bash
railway login                    # Auth
railway logs -n 50               # Últimas 50 linhas
railway logs                     # Streaming
railway status                   # Projeto atual
```

**Docs completos:** `docs/integracoes/railway-quickref.md` e `docs/integracoes/railway-deploy.md`

**Projeto:** `remarkable-communication` | **Serviço:** `whats-agents` | **Ambiente:** `production`

---

## Ambientes Supabase (MCP)

O projeto possui dois ambientes Supabase configurados via MCP:

| Ambiente | Project Ref | URL | Uso |
|----------|-------------|-----|-----|
| **PROD** | `jyqgbzhqavgpxqacduoi` | https://jyqgbzhqavgpxqacduoi.supabase.co | Julia em produção |
| **DEV** | `ofpnronthwcsybfxnxgj` | https://ofpnronthwcsybfxnxgj.supabase.co | Desenvolvimento/testes |

### Ferramentas MCP

```
# PROD (julia-prod)
mcp__supabase-prod__execute_sql
mcp__supabase-prod__apply_migration
mcp__supabase-prod__list_tables
mcp__supabase-prod__get_project_url

# DEV (banco_medicos)
mcp__supabase-dev__execute_sql
mcp__supabase-dev__apply_migration
mcp__supabase-dev__list_tables
mcp__supabase-dev__get_project_url
```

### Regras Importantes

1. **Migrations em PROD**: Sempre usar `mcp__supabase-prod__apply_migration` para produção
2. **Testes em DEV**: Testar queries complexas primeiro no DEV
3. **Nunca confundir**: Verificar o ambiente antes de executar DDL

### Configuração (se precisar reconfigurar)

```bash
# Listar MCPs configurados
claude mcp list

# Adicionar PROD
claude mcp add supabase-prod --transport http "https://mcp.supabase.com/mcp?project_ref=jyqgbzhqavgpxqacduoi"

# Adicionar DEV
claude mcp add supabase-dev --transport http "https://mcp.supabase.com/mcp?project_ref=ofpnronthwcsybfxnxgj"

# Autenticação acontece automaticamente via OAuth ao usar /mcp
```

---

## Banco de Dados

Tabelas organizadas em categorias (ver métricas acima para contagem atual):

| Categoria | Tabelas | Principais |
|-----------|---------|------------|
| Core do Agente | 6 | clientes, conversations, interacoes, handoffs, doctor_context, fila_mensagens |
| Gestão de Vagas | 7 | vagas, hospitais, especialidades, setores, periodos, tipos_vaga, formas_recebimento |
| Campanhas | 4 | campanhas, envios, execucoes_campanhas, metricas_campanhas |
| Gestão Júlia | 10 | diretrizes, reports, julia_status, briefing_config, feedbacks_gestor, prompts, slack_sessoes |
| Analytics | 4 | metricas_conversa, avaliacoes_qualidade, metricas_deteccao_bot, sugestoes_prompt |
| Infraestrutura | 4 | whatsapp_instances, notificacoes_gestor, slack_comandos, briefing_sync_log |

**Detalhes completos:** `docs/arquitetura/banco-de-dados.md`

---

## Rate Limiting (Crítico)

| Limite | Valor | Motivo |
|--------|-------|--------|
| Mensagens/hora | 20 | Evitar ban WhatsApp |
| Mensagens/dia | 100 | Evitar ban WhatsApp |
| Intervalo entre msgs | 45-180s | Parecer humano |
| Horário | 08h-20h | Horário comercial |
| Dias | Seg-Sex | Horário comercial |

---

## Handoff IA ↔ Humano

**Triggers automáticos:**
- Médico pede para falar com humano
- Médico muito irritado (sentimento negativo)
- Situação complexa (jurídico, financeiro)
- Confiança baixa na resposta

**Trigger manual:**
- Label "humano" no Chatwoot

**Fluxo:**
1. Trigger detectado
2. Júlia avisa: "Vou pedir pra minha supervisora te ajudar"
3. `UPDATE conversations SET controlled_by='human'`
4. Notifica gestor no Slack
5. Júlia para de responder
6. Humano assume via Chatwoot

---

## Notas para Desenvolvimento

- Usar `async/await` em todo o código
- Logging estruturado com contexto (médico_id, conversa_id)
- Nunca expor API keys no código
- Rate limiting é crítico
- Testes de persona antes de qualquer deploy
- Sempre respeitar opt-out imediatamente
- **Seguir convenções de código em `app/CONVENTIONS.md`**

---

## Convenções de Código

Ver arquivo completo em `app/CONVENTIONS.md`. Resumo:

### Nomenclatura de Funções

| Operação | Prefixo | Exemplo |
|----------|---------|---------|
| Buscar um | `buscar_` | `buscar_medico_por_telefone()` |
| Buscar vários | `listar_` | `listar_vagas_disponiveis()` |
| Criar | `criar_` | `criar_conversa()` |
| Atualizar | `atualizar_` | `atualizar_status_vaga()` |
| Deletar | `deletar_` | `deletar_handoff()` |

### Predicados (retornam bool)

| Prefixo | Uso |
|---------|-----|
| `pode_` | Permissão/capacidade |
| `tem_` | Existência |
| `esta_` | Estado atual |
| `eh_` | Identidade/tipo |

### Ações

| Prefixo | Uso |
|---------|-----|
| `enviar_` | Envia para sistema externo |
| `processar_` | Transforma/processa dados |
| `gerar_` | Cria output/relatório |
| `formatar_` | Formata para exibição |
| `notificar_` | Envia notificação |

### Import do Supabase

```python
# Correto
from app.services.supabase import supabase

# Incorreto (deprecated)
from app.services.supabase import get_supabase
```

### Exceptions Customizadas

Usar exceptions de `app/core/exceptions.py`:
- `DatabaseError` - erros de banco
- `ExternalAPIError` - erros de APIs externas
- `ValidationError` - erros de validação
- `RateLimitError` - rate limit atingido
- `NotFoundError` - recurso não encontrado

---

## Documentação Detalhada

### Docs por Categoria

| Categoria | Diretório | Conteúdo |
|-----------|-----------|----------|
| Arquitetura | `docs/arquitetura/` | Visão geral, endpoints, banco, serviços |
| Setup | `docs/setup/` | Configuração, deploy, produção |
| Operação | `docs/operacao/` | Runbook, playbooks, testes manuais |
| Integrações | `docs/integracoes/` | Evolution, Chatwoot, Railway, Slack |
| Julia | `docs/julia/` | Persona, prompts, conhecimento RAG |
| Auditorias | `docs/auditorias/` | Relatórios técnicos e de processos |

### Docs de Integrações (Quick Reference)

| Documento | Conteúdo |
|-----------|----------|
| `docs/integracoes/evolution-api-quickref.md` | Endpoints, auth, envio de mensagens |
| `docs/integracoes/evolution-api-webhooks.md` | Eventos, payloads, configuração |
| `docs/integracoes/chatwoot-api-quickref.md` | Endpoints, auth, conversas, contatos |
| `docs/integracoes/chatwoot-webhooks.md` | Eventos, payloads, handoff |
| `docs/integracoes/railway-quickref.md` | CLI, comandos, variáveis |
| `docs/integracoes/railway-deploy.md` | Deploy, troubleshooting, logs |
| `planning/sprint-25/docs-salvy-*.md` | Salvy API (números virtuais) |

---

## Documentação de Integrações Externas

Ao trabalhar com serviços externos, **sempre consultar a documentação local primeiro**. Na dúvida, fazer pesquisa online com `WebFetch` ou `WebSearch`.

### Salvy (Números Virtuais)

**Serviço:** Provisionamento de números virtuais para WhatsApp

**Documentação local (consultar primeiro):**
- `planning/sprint-25/docs-salvy-quickref.md` - Endpoints, auth, exemplos rápidos
- `planning/sprint-25/docs-salvy-webhooks.md` - Webhook SMS, verificação Svix

**Documentação oficial (na dúvida):**
- https://docs.salvy.com.br/api-reference/virtual-phone-accounts/introduction

**Epic de implementação:** `planning/sprint-25/epic-02-salvy-integration.md`

### Evolution API (WhatsApp)

**Serviço:** API para controle do WhatsApp via Baileys

**Documentação local (consultar primeiro):**
- `docs/integracoes/evolution-api-quickref.md` - Endpoints, auth, envio de mensagens
- `docs/integracoes/evolution-api-webhooks.md` - Eventos, payloads, configuração

**Documentação oficial (na dúvida):**
- https://doc.evolution-api.com/v2/

### Chatwoot (Supervisão)

**Serviço:** Plataforma de atendimento e supervisão

**Documentação local (consultar primeiro):**
- `docs/integracoes/chatwoot-api-quickref.md` - Endpoints, auth, conversas, contatos
- `docs/integracoes/chatwoot-webhooks.md` - Eventos, payloads, handoff

**Documentação oficial (na dúvida):**
- https://developers.chatwoot.com/

### Railway (Deploy)

**Serviço:** Plataforma de deploy via GitHub

**Documentação local (consultar primeiro):**
- `docs/integracoes/railway-quickref.md` - CLI, comandos, variaveis, healthcheck
- `docs/integracoes/railway-deploy.md` - Deploy, troubleshooting, logs, rollback

**Documentação oficial (na dúvida):**
- https://docs.railway.com/

**Projeto:** `remarkable-communication` | **Serviço:** `whats-agents`

### Outras Integrações

| Serviço | Docs |
|---------|------|
| Slack | https://api.slack.com/methods |
| Google Docs | https://developers.google.com/docs/api |

---

## Boas Práticas - Projetos Frontend (Next.js/TypeScript)

> **ATENÇÃO:** Para projetos Next.js/TypeScript, existe documentação específica obrigatória.

**Arquivo:** `docs/best-practices/nextjs-typescript-rules.md`

### Quando Consultar (OBRIGATÓRIO)

| Momento | Ação |
|---------|------|
| ANTES de escrever código | Ler regras de Client/Server Components e TypeScript strict |
| APÓS terminar código | Verificar conformidade com checklist |
| ANTES de commitar | Garantir todos os testes passam |

### Problemas Críticos que o Arquivo Previne

1. **Webpack Build Errors** - Importação de Node.js em Client Components
2. **Hydration Errors** - Diferença server/client render
3. **Uso de `any`** - Tolerância ZERO para `any` em TypeScript
4. **Testes não executados** - Validação obrigatória antes de commit

### Workflow Resumido

```bash
# 1. Antes de codificar
cat docs/best-practices/nextjs-typescript-rules.md

# 2. Após codificar - Validação obrigatória
npm run tsc -- --noEmit    # Type check
npm run lint               # Linting
npm run format             # Formatting
npm test                   # Testes

# 3. Verificar any (deve retornar vazio)
grep -r ": any" src/
grep -r "as any" src/

# 4. Build final
npm run build
```

### Regras Principais (Resumo)

- **NUNCA** usar `any` - usar `unknown` + type guards
- **NUNCA** importar Node.js (`fs`, `path`, `crypto`) em Client Components
- **NUNCA** usar `Math.random()`, `Date.now()`, `window` no render inicial
- **SEMPRE** tipar retornos de função explicitamente
- **SEMPRE** validar dados externos com Zod ou type guards
- **SEMPRE** rodar testes antes de commitar

---

## Dashboard CI/CD (Next.js/TypeScript)

O dashboard tem seu próprio pipeline de CI/CD em `.github/workflows/dashboard-ci.yml`.

### Pipeline de CI

| Job | Descrição | Bloqueia Build? |
|-----|-----------|-----------------|
| install | Instala dependências com cache | Não |
| typecheck | `tsc --noEmit` + verificação de `any` | Sim |
| lint | ESLint com regras strict | Sim |
| format | Prettier check | Sim |
| unit-tests | Vitest + React Testing Library | Sim |
| e2e-tests | Playwright (Chromium) | Sim |
| build | `next build` | Sim |
| security | `npm audit` + verificação de secrets | Não |
| lighthouse | Performance, A11y, SEO, Best Practices | Sim |
| deploy | Railway (apenas main) | N/A |

### Comandos Locais

```bash
cd dashboard

# Validação completa (type-check + lint + format + tests)
npm run validate

# Testes unitários
npm run test              # Watch mode
npm run test:ci           # CI mode com coverage

# Testes E2E
npm run test:e2e          # Headless
npm run test:e2e:ui       # UI mode
npm run test:e2e:report   # Ver relatório

# Linting e formatação
npm run lint              # Verificar
npm run lint:fix          # Corrigir
npm run format            # Formatar
npm run format:check      # Verificar formatação

# Type check
npm run type-check

# Build com análise de bundle
ANALYZE=true npm run build
```

### Estrutura de Testes

```
dashboard/
├── __tests__/           # Testes unitários (Vitest + RTL)
│   └── *.test.tsx
├── e2e/                  # Testes E2E (Playwright)
│   └── *.e2e.ts
├── vitest.config.ts      # Configuração Vitest
├── vitest.setup.ts       # Setup (mocks, globals)
└── playwright.config.ts  # Configuração Playwright
```

### Cobertura de Código

**Thresholds mínimos (falha se abaixo):**
- Statements: 70%
- Branches: 70%
- Functions: 70%
- Lines: 70%

### Lighthouse CI (Performance)

**Thresholds configurados em `lighthouserc.js`:**

| Métrica | Mínimo | Tipo |
|---------|--------|------|
| Performance | 70% | warn |
| Accessibility | 90% | error |
| Best Practices | 80% | warn |
| SEO | 80% | warn |

**Core Web Vitals:**
| Métrica | Máximo |
|---------|--------|
| First Contentful Paint | 2000ms |
| Largest Contentful Paint | 2500ms |
| Cumulative Layout Shift | 0.1 |
| Total Blocking Time | 300ms |
| Time to Interactive | 3500ms |

**Rodar localmente:**
```bash
npm install -g @lhci/cli
cd dashboard
npm run build && lhci autorun
```

### Secrets Necessários (GitHub Actions)

| Secret | Descrição | Obrigatório |
|--------|-----------|-------------|
| `RAILWAY_TOKEN` | Token para deploy | Sim (para deploy) |
| `DASHBOARD_URL` | URL do dashboard em prod | Não (health check) |
| `NEXT_PUBLIC_SUPABASE_URL` | URL do Supabase | Não (usa fallback) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Anon key do Supabase | Não (usa fallback) |
| `LHCI_GITHUB_APP_TOKEN` | Token para Lighthouse status checks | Não (opcional) |

> **Nota:** Para habilitar status checks do Lighthouse em PRs, instale o [Lighthouse CI GitHub App](https://github.com/apps/lighthouse-ci) e configure o token.

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de resposta médicos | > 30% |
| Latência de resposta | < 30s |
| Taxa detecção como bot | < 1% |
| Uptime | > 99% |

---

## Regras para o Claude

1. **Seguir a sprint atual** - Verificar qual sprint está em andamento antes de implementar
2. **Consultar docs locais primeiro** - Para integrações, sempre ler docs em `docs/` antes de buscar online
3. **Perguntar na dúvida** - Se não tiver certeza do escopo ou abordagem, perguntar ao usuário
4. **Convenções de código** - Seguir `app/CONVENTIONS.md` rigorosamente
5. **Testes** - Rodar `uv run pytest` antes de considerar tarefa completa
6. **Verificar branch antes de commit** - SEMPRE executar `git branch --show-current` antes de fazer commit/push para garantir que está no branch correto
7. **Projetos Next.js/TypeScript** - OBRIGATÓRIO consultar `docs/best-practices/nextjs-typescript-rules.md`:
   - ANTES de escrever código (ler regras)
   - APÓS terminar (verificar conformidade)
   - ANTES de commitar (todos os testes devem passar)
8. **Nunca fazer fix rápidos ou hardcoded** - Ao corrigir bugs ou fazer debug:
   - NUNCA usar soluções temporárias ou gambiarras
   - NUNCA hardcodar valores que deveriam ser configuráveis
   - SEMPRE entender a causa raiz antes de corrigir
   - SEMPRE implementar a solução correta, mesmo que demore mais
   - Se precisar de fix temporário, perguntar ao usuário primeiro
