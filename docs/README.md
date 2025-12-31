# Documentacao do Agente Julia

> **Escalista virtual autonoma para staffing medico da Revoluna**

Julia e um agente de IA que prospecta medicos, oferece plantoes, gerencia relacionamentos e fecha vagas via WhatsApp. O objetivo principal e passar no teste de Turing - medicos nao devem perceber que estao falando com uma IA.

---

## Indice da Documentacao

### Arquitetura

| Documento | Descricao |
|-----------|-----------|
| [Visao Geral](./arquitetura/visao-geral.md) | Arquitetura do sistema, componentes e fluxos |
| [API e Endpoints](./arquitetura/api-endpoints.md) | Referencia completa de todos os endpoints |
| [Servicos](./arquitetura/servicos.md) | Detalhes dos modulos de servico |
| [Banco de Dados](./arquitetura/banco-de-dados.md) | Schema das tabelas e relacionamentos |
| [Logica de Negocio](./arquitetura/logica-negocio.md) | Fluxos de negocio e regras |

### Setup e Deploy

| Documento | Descricao |
|-----------|-----------|
| [Configuracao](./setup/configuracao.md) | Como configurar o projeto |
| [Setup](./setup/setup.md) | Checklist de configuracao com status |
| [Deploy](./setup/deploy.md) | Docker, Railway e monitoramento |
| [Producao Canary](./setup/producao-canary.md) | Governanca de rollout para producao |

### Operacao

| Documento | Descricao |
|-----------|-----------|
| [Runbook](./operacao/runbook.md) | Procedimentos operacionais |
| [Deploy Prod Report](./operacao/deploy-prod-report.md) | Relatorio de deploy em producao |
| [Playbook Handoff](./operacao/playbook-handoff.md) | Operacao da ponte medico-divulgador |
| [Testes Manuais](./operacao/testes-manuais.md) | Guia de testes antes do lancamento |
| [Guardrails Queries](./operacao/guardrails-queries.md) | Queries de auditoria |

### Integracoes Externas

| Documento | Descricao |
|-----------|-----------|
| [Visao Geral](./integracoes/README.md) | Overview de todas as integracoes |
| [Evolution API - Quick Reference](./integracoes/evolution-api-quickref.md) | Endpoints, autenticacao, exemplos |
| [Evolution API - Webhooks](./integracoes/evolution-api-webhooks.md) | Payloads de webhook e eventos |
| [Chatwoot API - Quick Reference](./integracoes/chatwoot-api-quickref.md) | Endpoints, autenticacao, exemplos |
| [Chatwoot - Webhooks](./integracoes/chatwoot-webhooks.md) | Payloads de webhook e eventos |
| [Railway - Quick Reference](./integracoes/railway-quickref.md) | CLI, auto-deploy, variaveis |
| [Railway - Deploy](./integracoes/railway-deploy.md) | Troubleshooting, logs, rollback |
| [Slack - Logica de Negocio](./integracoes/slack-logica-negocio.md) | Regras, fluxos e arquitetura Slack |

### Julia (Persona e Prompts)

| Documento | Descricao |
|-----------|-----------|
| [Persona Julia](./julia/persona-julia.md) | Identidade, tom e exemplos |
| [Sistema de Prompts](./julia/sistema-prompts.md) | Organizacao e planejamento dos prompts |
| [Prompt Coverage](./julia/prompt-coverage.md) | Cobertura de cenarios nos prompts |
| [Briefings](./julia/briefings.md) | Briefings do gestor |
| [Briefing Template](./julia/briefing-template.md) | Template Google Docs para gestor |

### Templates

| Documento | Descricao |
|-----------|-----------|
| [Campaign Templates](./templates/campaign-templates.md) | Templates de campanha no Google Drive |

### Auditorias

| Documento | Descricao |
|-----------|-----------|
| [Auditoria Processos](./auditorias/auditoria-processos.md) | Auditoria de processos de negocio |
| [Auditoria Tecnica](./auditorias/auditoria-tecnica.md) | Auditoria tecnica do sistema |
| [Migracao Status](./auditorias/migracao-status-fechada.md) | Notas sobre migracoes |

### Arquivo

Documentos obsoletos estao em [archive/](./archive/)

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
│   ├── api/routes/       # Routers de endpoints
│   ├── services/         # Modulos de servico
│   ├── core/             # Config, prompts, logging
│   ├── tools/            # Ferramentas do agente
│   ├── prompts/          # Sistema de prompts dinamicos
│   ├── pipeline/         # Pipeline de processamento
│   ├── workers/          # Scheduler e fila
│   └── main.py           # FastAPI app
├── tests/                # Testes unitarios e integracao
├── docs/                 # Esta documentacao
│   ├── arquitetura/      # Docs de arquitetura
│   ├── setup/            # Docs de configuracao
│   ├── operacao/         # Runbooks e procedimentos
│   ├── integracoes/      # APIs externas
│   ├── julia/            # Persona e prompts
│   ├── templates/        # Templates de campanha
│   ├── auditorias/       # Relatorios de auditoria
│   └── archive/          # Docs obsoletos
└── planning/             # Sprints e epics
```

### Metricas Atuais

Para metricas atualizadas, verificar CLAUDE.md ou rodar:
```bash
find app -name "*.py" | wc -l          # Arquivos Python
ls app/services/*.py | wc -l           # Servicos
uv run pytest --collect-only -q | tail -1  # Testes
```

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
- **Sprint atual:** Ver CLAUDE.md para status atualizado

---

*Documentacao atualizada em 31/12/2025*
