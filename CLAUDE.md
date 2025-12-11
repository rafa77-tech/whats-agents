# CLAUDE.md

Este arquivo é a **fonte única de verdade** para o Claude Code ao trabalhar neste repositório.

## Projeto: Agente Júlia

**Escalista virtual autônoma** para staffing médico da Revoluna.

Júlia é um agente de IA que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp.

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

---

## Estado Atual

**Sprint Atual:** 9 - Julia como Colega no Slack
**Início do Projeto:** 05/12/2025
**Última Atualização:** 11/12/2025

### Métricas do Projeto

| Recurso | Quantidade |
|---------|------------|
| Arquivos Python | 100 |
| Serviços | 46 |
| Tabelas no banco | 35 |
| Migrações | 44 |
| Testes | 443 |
| Endpoints API | 25+ |

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
- [x] Supabase (PostgreSQL + pgvector)

**Inteligência:**
- [x] Memória de longo prazo (RAG com embeddings)
- [x] Detecção de opt-out automática
- [x] Detecção de handoff (sentimento negativo, pedido humano)
- [x] Detecção de bot (37 padrões)
- [x] Pipeline de processamento extensível
- [x] Sistema de prompts dinâmicos

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
├── CLAUDE.md                    # Este arquivo (fonte única)
├── app/
│   ├── api/routes/             # 10 routers de endpoints
│   ├── services/               # 46 módulos de serviço
│   ├── tools/                  # Tools do agente (vagas, memoria, slack)
│   ├── pipeline/               # Pipeline de processamento
│   ├── prompts/                # Sistema de prompts dinâmicos
│   ├── templates/              # Templates de mensagens
│   ├── workers/                # Scheduler e workers
│   ├── core/                   # Config, logging, prompts
│   └── main.py                 # FastAPI app
│
├── tests/                      # 443 testes
│
├── docs/                       # Documentação técnica
│   ├── README.md               # Índice da documentação
│   ├── 01-ARQUITETURA.md       # Visão geral do sistema
│   ├── 02-API-ENDPOINTS.md     # Referência de endpoints
│   ├── 03-SERVICOS.md          # Detalhes dos serviços
│   └── ...                     # Outros docs
│
├── planning/                   # Sprints e épicos
│   ├── sprint-0/ a sprint-9/   # Planejamento de cada sprint
│   └── README.md               # Visão geral do roadmap
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

---

## Banco de Dados

**35 tabelas** organizadas em categorias:

| Categoria | Tabelas | Principais |
|-----------|---------|------------|
| Core do Agente | 6 | clientes, conversations, interacoes, handoffs, doctor_context, fila_mensagens |
| Gestão de Vagas | 7 | vagas, hospitais, especialidades, setores, periodos, tipos_vaga, formas_recebimento |
| Campanhas | 4 | campanhas, envios, execucoes_campanhas, metricas_campanhas |
| Gestão Júlia | 10 | diretrizes, reports, julia_status, briefing_config, feedbacks_gestor, prompts, slack_sessoes |
| Analytics | 4 | metricas_conversa, avaliacoes_qualidade, metricas_deteccao_bot, sugestoes_prompt |
| Infraestrutura | 4 | whatsapp_instances, notificacoes_gestor, slack_comandos, briefing_sync_log |

**Detalhes completos:** `docs/04-BANCO-DE-DADOS.md`

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

---

## Documentação Detalhada

| Documento | Conteúdo |
|-----------|----------|
| `docs/SPEC.md` | Funcionalidades, fluxos, critérios de aceite |
| `docs/TECHNICAL.md` | Arquitetura, componentes, integrações |
| `docs/DATABASE.md` | Schema completo, queries úteis |
| `docs/SETUP.md` | Checklist de configuração |
| `docs/BRIEFING_TEMPLATE.md` | Template do Google Docs para gestor |
| `docs/CONVERSAS_REFERENCIA.md` | Conversas reais de escalistas para referência |
| `docs/FLUXOS.md` | Fluxos de negócio detalhados passo-a-passo |
| `docs/METRICAS_MVP.md` | Critérios de sucesso e métricas do MVP |
| `docs/ESCOPO_MVP.md` | O que entra e não entra no MVP |
| `docs/INTEGRACOES.md` | Detalhes de cada integração externa |
| `docs/DADOS.md` | Fonte e estrutura de dados (médicos, vagas) |
| `docs/ESTRATEGIA_TESTES.md` | Warm-up, fases de teste, validação de persona |
| `docs/PREFERENCIAS_MEDICO.md` | Sistema de captura e uso de preferências |
| `docs/SPRINTS.md` | Planejamento de sprints e tarefas |

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de resposta médicos | > 30% |
| Latência de resposta | < 30s |
| Taxa detecção como bot | < 1% |
| Uptime | > 99% |
- Quando for executar uma tarefa tenha certeza que está seguindo as orientacoes da sprint em que estamos. Caso tenha dúvida, pergunte.