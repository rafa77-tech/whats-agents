# Documentacao do Agente Julia

> **Escalista virtual autonoma para staffing medico da Revoluna**

Julia e um agente de IA que prospecta medicos, oferece plantoes, gerencia relacionamentos e fecha vagas via WhatsApp. O objetivo principal e passar no teste de Turing - medicos nao devem perceber que estao falando com uma IA.

---

## Indice da Documentacao

| Documento | Descricao |
|-----------|-----------|
| [Arquitetura](./arquitetura.md) | Visao geral do sistema, componentes e fluxos |
| [API e Endpoints](./api-endpoints.md) | Referencia completa de todos os endpoints |
| [Servicos](./servicos.md) | Detalhes dos 118 modulos de servico |
| [Banco de Dados](./banco-de-dados.md) | Schema das 54 tabelas e relacionamentos |
| [Configuracao e Setup](./configuracao.md) | Como configurar e rodar o projeto |
| [Deploy e Operacao](./deploy.md) | Docker, workers e monitoramento |
| [Logica de Negocio](./logica-negocio.md) | Fluxos de negocio e regras |
| [Persona Julia](./persona-julia.md) | Identidade, tom e exemplos |
| [Integracoes](./integracoes.md) | WhatsApp, Chatwoot, Slack, etc |
| [Testes Manuais](./testes-manuais.md) | Guia de testes antes do lancamento |
| [Sistema de Prompts](./sistema-prompts.md) | Organizacao e planejamento dos prompts |
| [Runbook](./runbook.md) | Procedimentos operacionais |
| [Setup](./setup.md) | Checklist de configuracao com status |
| [Briefing Template](./briefing-template.md) | Template Google Docs para gestor |
| [Campaign Templates](./campaign-templates.md) | Templates de campanha no Google Drive |
| [Guardrails Queries](./guardrails-queries.md) | Queries de auditoria Sprint 18 |
| [Producao Canary](./producao-canary.md) | Governanca de rollout para producao |
| [Playbook Handoff](./playbook-handoff.md) | Operacao da ponte medico-divulgador |
| [Migracao Status](./migracao-status-fechada.md) | Notas sobre migracoes |

---

## Visao Geral Rapida

### O que e o Agente Julia?

Julia e uma **escalista virtual** que:
- Prospecta medicos via WhatsApp (contato frio)
- Oferece plantoes compativeis com o perfil
- Negocia valores e datas
- Gerencia follow-ups automaticos
- Escala para humanos quando necessario

### Stack Tecnologico

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.13+ / FastAPI |
| LLM | Claude 3.5 Haiku + Claude 4 Sonnet |
| Banco de Dados | Supabase (PostgreSQL + pgvector) |
| WhatsApp | Evolution API |
| Supervisao | Chatwoot |
| Notificacoes | Slack |
| Cache/Filas | Redis |
| Package Manager | uv (Astral) |

### Estrutura do Projeto

```
whatsapp-api/
├── app/
│   ├── api/routes/       # 10 routers de endpoints
│   ├── services/         # 118 modulos de servico
│   ├── core/             # Config, prompts, logging
│   ├── tools/            # Ferramentas do agente (vagas, slack, briefing)
│   ├── prompts/          # Sistema de prompts dinamicos
│   ├── pipeline/         # Pipeline de processamento
│   ├── workers/          # Scheduler e fila
│   ├── schemas/          # Pydantic models
│   └── main.py           # FastAPI app
├── tests/                # 1177 testes
│   ├── persona/          # Testes de identidade
│   ├── resiliencia/      # Testes de circuit breaker
│   └── optout/           # Testes de opt-out
├── docs/                 # Esta documentacao
├── planning/             # Sprints e epics (0-18)
└── docker-compose.yml    # Evolution, Chatwoot, Redis
```

### Metricas Atuais

| Recurso | Quantidade |
|---------|------------|
| Arquivos Python | 200 |
| Endpoints API | 97 |
| Servicos | 118 |
| Tabelas no banco | 54 |
| Migracoes | 93 |
| Testes | 1177 |

---

## Quick Start

### 1. Clonar e instalar dependencias

```bash
git clone <repo>
cd whatsapp-api
uv sync
```

### 2. Configurar variaveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas credenciais
```

### 3. Subir servicos Docker

```bash
docker compose up -d
```

### 4. Rodar a API

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Testar

```bash
# Health check
curl http://localhost:8000/health

# Rodar testes
uv run pytest
```

---

## Conceitos Importantes

### Rate Limiting (Critico!)

Para evitar ban do WhatsApp, o sistema implementa limites rigorosos:

| Limite | Valor |
|--------|-------|
| Mensagens por hora | 20 |
| Mensagens por dia | 100 |
| Intervalo entre msgs | 45-180 segundos |
| Horario permitido | 08:00 - 20:00 |
| Dias permitidos | Segunda a Sexta |

### Handoff IA <-> Humano

Quando transferir para humano:
- Medico pede explicitamente
- Sentimento muito negativo
- Questoes juridicas/financeiras
- Confianca baixa na resposta

### Deteccao de Bot

O sistema monitora quando medicos suspeitam que estao falando com IA:
- 37 padroes regex de deteccao
- Metrica de taxa de deteccao
- Alerta se > 5%

---

## Links Uteis

- [CLAUDE.md](../CLAUDE.md) - Instrucoes para o Claude Code
- [Supabase Dashboard](https://supabase.com/dashboard)
- [Evolution API Docs](https://doc.evolution-api.com)
- [Anthropic API Docs](https://docs.anthropic.com)

---

## Contato e Suporte

- **Projeto:** Agente Julia - Revoluna
- **Inicio:** 05/12/2025
- **Sprint atual:** 18 - Auditoria e Integridade

---

*Documentacao atualizada em 29/12/2025*
