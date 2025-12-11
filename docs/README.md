# Documentacao do Agente Julia

> **Escalista virtual autonoma para staffing medico da Revoluna**

Julia e um agente de IA que prospecta medicos, oferece plantoes, gerencia relacionamentos e fecha vagas via WhatsApp. O objetivo principal e passar no teste de Turing - medicos nao devem perceber que estao falando com uma IA.

---

## Indice da Documentacao

| # | Documento | Descricao |
|---|-----------|-----------|
| 1 | [Arquitetura](./01-ARQUITETURA.md) | Visao geral do sistema, componentes e fluxos |
| 2 | [API e Endpoints](./02-API-ENDPOINTS.md) | Referencia completa de todos os endpoints |
| 3 | [Servicos](./03-SERVICOS.md) | Detalhes dos 46 modulos de servico |
| 4 | [Banco de Dados](./04-BANCO-DE-DADOS.md) | Schema das 35 tabelas e relacionamentos |
| 5 | [Configuracao e Setup](./05-CONFIGURACAO.md) | Como configurar e rodar o projeto |
| 6 | [Deploy e Operacao](./06-DEPLOY.md) | Docker, workers e monitoramento |
| 7 | [Logica de Negocio](./07-LOGICA-NEGOCIO.md) | Fluxos de negocio e regras |
| 8 | [Persona Julia](./08-PERSONA-JULIA.md) | Identidade, tom e exemplos |
| 9 | [Integracoes](./09-INTEGRACOES.md) | WhatsApp, Chatwoot, Slack, etc |
| 10 | [Testes Manuais](./10-TESTES-MANUAIS.md) | Guia de testes antes do lancamento |

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
│   ├── services/         # 41 modulos de servico
│   ├── core/             # Config, prompts, logging
│   ├── tools/            # Ferramentas do agente (vagas, lembrete)
│   ├── workers/          # Scheduler e fila
│   ├── schemas/          # Pydantic models
│   └── main.py           # FastAPI app
├── tests/
│   ├── persona/          # Testes de identidade
│   ├── resiliencia/      # Testes de circuit breaker
│   └── optout/           # Testes de opt-out
├── docs/                 # Esta documentacao
├── planning/             # Sprints e epics
└── docker-compose.yml    # Evolution, Chatwoot, Redis
```

### Metricas Atuais

| Recurso | Quantidade |
|---------|------------|
| Arquivos Python | 100 |
| Endpoints API | 25+ |
| Servicos | 46 |
| Tabelas no banco | 35 |
| Migracoes | 44 |
| Testes | 443 |

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
- **Sprint atual:** 9 - Julia como Colega no Slack (Completa)

---

*Documentacao atualizada em 11/12/2025*
