# CLAUDE.md

Este arquivo é a **fonte única de verdade** para o Claude Code ao trabalhar neste repositório.

## Projeto: Agente Júlia

**Escalista virtual autônoma** para staffing médico da Revoluna.

Júlia é um agente de IA que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp.

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

---

## Estado Atual

**Fase:** 0 - Setup & Configuração
**Início:** 05/12/2025

### Foco Inicial: Anestesiologia

| Métrica | Valor |
|---------|-------|
| Total anestesistas | 1.660 |
| Com CRM | 1.345 (81%) |
| Prioridade | Primeira especialidade do MVP |

**Por que Anestesiologia:**
- Alta demanda no mercado
- Boa base de dados com CRM
- Perfil de médico que faz plantão avulso

### Contexto de Mercado (Crítico)

| Aspecto | Realidade |
|---------|-----------|
| Saturação | Médicos recebem mensagens de staffing **o tempo todo** |
| Relacionamento | Todos são **contatos frios** (ninguém conhece Júlia) |
| Regulatório | Sem risco CFM para contato automatizado |
| Modelo | Apenas Revoluna (não é multi-tenant) |

**Ciclo de vida da vaga:**
- Hospital define escala mensal (X médicos, período Y, dias Z)
- Ideal: preencher com 30 dias de antecedência
- Urgência cresce conforme data se aproxima
- Fontes de urgência: escala não fechada, médico doente, cancelamento de última hora

**Implicação:** Qualidade > quantidade. Uma mensagem mal escrita = bloqueio.

### Concluído
- [x] Documentação base estruturada
- [x] Análise de custos LLM (decisão: Haiku + Sonnet híbrido)
- [x] Projeto Supabase criado
- [x] MCP Supabase configurado no Claude Code
- [x] Schema do banco executado (27 tabelas, 14 migrações)
- [x] Docker Compose configurado (Evolution, Chatwoot, n8n, Redis)
- [x] Documentação de fluxos de negócio detalhados
- [x] Documentação de métricas e critérios de sucesso
- [x] Documentação de escopo MVP
- [x] Documentação de integrações externas
- [x] Documentação de fonte de dados
- [x] Estratégia de testes e warm-up
- [x] Sistema de preferências do médico planejado
- [x] Planejamento de sprints (6 sprints, ~100h dev)

### Pendente
- [ ] Obter API key Anthropic
- [ ] Configurar Slack webhook
- [ ] Configurar Google Docs API
- [ ] Testar Evolution API + conectar número WhatsApp
- [ ] Testar Chatwoot

### Próxima Fase (1 - MVP)
- Estrutura FastAPI
- Webhook Evolution API
- Agente Júlia básico
- Integração Chatwoot
- Sistema de handoff

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
| Backend | Python 3.13+ / FastAPI | A implementar |
| Package Manager | uv (Astral) | Configurado |
| LLM Principal | Claude 3.5 Haiku | A configurar |
| LLM Complexo | Claude 4 Sonnet | A configurar |
| Banco de Dados | Supabase (PostgreSQL + pgvector) | Configurado |
| WhatsApp | Evolution API | Docker rodando |
| Supervisão | Chatwoot | Docker rodando |
| Automação | n8n | Docker rodando |
| Notificações | Slack | A configurar |

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
├── docs/
│   ├── SPEC.md                 # Especificações do produto
│   ├── TECHNICAL.md            # Arquitetura técnica
│   ├── DATABASE.md             # Schema do banco
│   ├── SETUP.md                # Checklist de configuração
│   ├── BRIEFING_TEMPLATE.md    # Template do Google Docs
│   └── archive/                # Documentos históricos
│
├── .claude/
│   └── commands/
│       └── pm-agent.md         # Prompt do PM Agent
│
├── deprecated/                  # Código legacy
│
├── docker-compose.yml          # Evolution, Chatwoot, n8n
├── .env.example                # Template de variáveis
└── pyproject.toml              # Dependências Python
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

**27 tabelas** organizadas em categorias:

| Categoria | Tabelas | Principais |
|-----------|---------|------------|
| Core do Agente | 5 | clientes, conversations, interacoes, handoffs, doctor_context |
| Gestão de Vagas | 7 | vagas, hospitais, especialidades, setores, periodos |
| Campanhas | 4 | campanhas, envios, execucoes_campanhas, metricas_campanhas |
| Gestão Júlia | 7 | diretrizes, reports, julia_status, briefing_config, feedbacks_gestor |
| Infraestrutura | 2 | whatsapp_instances, notificacoes_gestor |

**Detalhes completos:** `docs/DATABASE.md`

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