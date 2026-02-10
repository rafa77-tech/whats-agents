# Workers e Scheduler

Documentacao operacional dos workers do sistema Julia.

## Visao Geral

O sistema utiliza um scheduler central que executa jobs agendados via HTTP, chamando endpoints da API. Todos os jobs sao orquestrados pelo scheduler, que interpreta cron expressions no horario de Brasilia e registra execucoes para monitoramento.

## Arquitetura

### Estrutura de Arquivos

```
app/workers/
├── __init__.py                   # 2 linhas
├── __main__.py                   # 41 linhas - Entry point para workers
├── scheduler.py                  # 503 linhas - Orquestrador central de jobs
├── backfill_extraction.py        # 317 linhas - Backfill de extracoes historicas (Sprint 53)
├── fila_worker.py                # 287 linhas - Processador de fila (legado, nao usado em prod)
├── grupos_worker.py              # 235 linhas - Processador de grupos WhatsApp (legado)
├── handoff_processor.py          # 297 linhas - Processador de handoffs (legado)
├── pilot_mode.py                 # 236 linhas - Guards e decorators para modo piloto
├── retomada_fora_horario.py      # 119 linhas - Retomada de mensagens fora do horario (legado)
└── temperature_decay.py          # 250 linhas - Decaimento de temperatura de leads (legado)
```

### Arquitetura Atual (Sprint 33+)

A partir da Sprint 33, a arquitetura mudou de workers independentes para um modelo centralizado:

- **Scheduler**: Orquestrador unico que executa jobs agendados via cron expressions
- **Jobs API**: Endpoints em `/jobs/*` que executam tarefas especificas
- **Persistencia**: Tabela `job_executions` registra inicio, fim, duracao e erros de cada execucao

Os arquivos `*_worker.py` (exceto `scheduler.py`) ainda existem no codigo mas NAO sao executados diretamente em producao. Toda logica foi migrada para jobs HTTP.

## Jobs Ativos (Scheduler)

O scheduler executa 35 jobs via endpoints HTTP. Todos os schedules sao interpretados no horario de Brasilia (BRT/BRST).

### Jobs de Alta Frequencia

| Job | Schedule | Endpoint | Funcao |
|-----|----------|----------|--------|
| `heartbeat` | `* * * * *` (1 min) | `/jobs/heartbeat` | Heartbeat para monitoramento |
| `processar_mensagens_agendadas` | `* * * * *` (1 min) | `/jobs/processar-mensagens-agendadas` | Processa fila de mensagens agendadas |
| `processar_campanhas_agendadas` | `* * * * *` (1 min) | `/jobs/processar-campanhas-agendadas` | Executa campanhas agendadas |
| `processar_grupos` | `* * * * *` (1 min) | `/jobs/processar-grupos` | Processa mensagens de grupos WhatsApp (batch_size=200, max_workers=20) |
| `verificar_whatsapp` | `*/5 * * * *` (5 min) | `/jobs/verificar-whatsapp` | Monitor de conexao WhatsApp |
| `sincronizar_chips` | `*/5 * * * *` (5 min) | `/jobs/sincronizar-chips` | Sincroniza chips com Evolution API |
| `validar_telefones` | `*/5 8-19 * * *` (5 min, 8h-19h59) | `/jobs/validar-telefones` | Valida telefones via checkNumberStatus |
| `processar_handoffs` | `*/10 * * * *` (10 min) | `/jobs/processar-handoffs` | Follow-up e expiracao de handoffs |
| `verificar_alertas` | `*/15 * * * *` (15 min) | `/jobs/verificar-alertas` | Verifica alertas do sistema |
| `verificar_alertas_grupos` | `*/15 * * * *` (15 min) | `/jobs/verificar-alertas-grupos` | Verifica alertas de grupos |
| `atualizar_trust_scores` | `*/15 * * * *` (15 min) | `/jobs/atualizar-trust-scores` | Atualiza trust score dos chips |

### Jobs Horarios

| Job | Schedule | Endpoint | Funcao |
|-----|----------|----------|--------|
| `sincronizar_briefing` | `0 * * * *` (hora cheia) | `/jobs/sincronizar-briefing` | Sincroniza briefing do Google Docs |
| `processar_confirmacao_plantao` | `0 * * * *` (hora cheia) | `/jobs/processar-confirmacao-plantao` | Confirmacao de plantao pos-realizacao |
| `oferta_autonoma` | `0 * * * *` (hora cheia) | `/jobs/executar-oferta-autonoma` | Oferta automatica de vagas (se PILOT_MODE=False) |

### Jobs Diarios

| Job | Schedule | Endpoint | Funcao |
|-----|----------|----------|--------|
| `consolidar_metricas_grupos` | `0 1 * * *` (01:00) | `/jobs/consolidar-metricas-grupos` | Consolida metricas do dia anterior |
| `avaliar_conversas_pendentes` | `0 2 * * *` (02:00) | `/jobs/avaliar-conversas-pendentes` | Avalia qualidade de conversas |
| `atualizar_prompt_feedback` | `0 2 * * 0` (Dom 02:00) | `/jobs/atualizar-prompt-feedback` | Atualiza prompt com feedback (semanal) |
| `doctor_state_manutencao_diaria` | `0 3 * * *` (03:00) | `/jobs/doctor-state-manutencao-diaria` | Manutencao diaria de doctor_state |
| `limpar_grupos_finalizados` | `0 3 * * *` (03:00) | `/jobs/limpar-grupos-finalizados` | Limpa grupos finalizados |
| `doctor_state_manutencao_semanal` | `0 4 * * 1` (Seg 04:00) | `/jobs/doctor-state-manutencao-semanal` | Manutencao semanal de doctor_state |
| `processar_pausas_expiradas` | `0 6 * * *` (06:00) | `/jobs/processar-pausas-expiradas` | Processa pausas expiradas |
| `sincronizar_templates` | `0 6 * * *` (06:00) | `/jobs/sync-templates` | Sincroniza templates de campanha do Google Docs |
| `processar_retomadas` | `0 8 * * 1-5` (Seg-Sex 08:00) | `/jobs/processar-retomadas` | Retoma mensagens fora do horario |
| `report_semanal` | `0 9 * * 1` (Seg 09:00) | `/jobs/report-semanal` | Relatorio semanal |
| `discovery_autonomo` | `0 9,14 * * 1-5` (Seg-Sex 09:00 e 14:00) | `/jobs/executar-discovery-autonomo` | Discovery automatico (se PILOT_MODE=False) |
| `processar_followups` | `0 10 * * *` (10:00) | `/jobs/processar-followups` | Processa follow-ups agendados |
| `reativacao_autonoma` | `0 10 * * 1` (Seg 10:00) | `/jobs/executar-reativacao-autonoma` | Reativacao automatica (se PILOT_MODE=False) |
| `report_manha` | `0 10 * * *` (10:00) | `/jobs/report-periodo?tipo=manha` | Relatorio da manha |
| `feedback_autonomo` | `0 11 * * *` (11:00) | `/jobs/executar-feedback-autonomo` | Feedback automatico (se PILOT_MODE=False) |
| `report_fim_dia` | `0 20 * * *` (20:00) | `/jobs/report-periodo?tipo=fim_dia` | Relatorio do fim do dia |
| `snapshot_chips_diario` | `55 23 * * *` (23:55) | `/jobs/snapshot-chips-diario` | Snapshot de contadores de chips (antes do reset) |
| `resetar_contadores_chips` | `5 0 * * *` (00:05) | `/jobs/resetar-contadores-chips` | Reseta contadores diarios de chips |

### Observacoes Importantes

- **Horario de Brasilia**: Todos os schedules sao interpretados em BRT/BRST (UTC-3)
- **Modo Piloto**: Jobs de gatilhos autonomos (discovery, oferta, reativacao, feedback) so executam acoes se `PILOT_MODE=False`
- **Batch Size**: Jobs de alta frequencia usam batching para evitar sobrecarga (ex: `processar_grupos` processa 200 itens/minuto)
- **Timeout**: Cada job tem timeout de 300s (5 minutos)

## Railway: Arquitetura de Producao

Em producao (Railway), o sistema roda como 3 servicos separados usando a mesma imagem Docker:

### Servicos Railway

| Servico | RUN_MODE | Comando | Funcao | Criticidade |
|---------|----------|---------|--------|-------------|
| `whats-agents` (API) | `api` | `uvicorn app.main:app` | API principal, webhooks, endpoints `/jobs/*` | CRITICA |
| `whats-agents-scheduler` | `scheduler` | `python -m app.workers.scheduler` | Executa jobs agendados chamando API | CRITICA |
| `whats-agents-worker` | `worker` | `python -m app.workers.fila_worker` | Worker de fila (legado, nao usado atualmente) | BAIXA |

### Como Funciona

1. **Entrypoint**: O arquivo `scripts/entrypoint.sh` le a variavel `RUN_MODE` e inicia o servico apropriado
2. **Validacao**: Se `RUN_MODE` nao estiver setada, o container falha com erro explicativo
3. **Isolamento**: Cada servico roda em container separado, permitindo escalar independentemente

### Variaveis Criticas

```bash
# Obrigatorias para todos os servicos
APP_ENV=production
SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi

# Especificas por servico (setadas no Railway)
RUN_MODE=api          # Para servico de API
RUN_MODE=scheduler    # Para servico de scheduler
RUN_MODE=worker       # Para servico de worker (se usado)
```

## Comandos

### Desenvolvimento Local

```bash
# Iniciar API
RUN_MODE=api uv run uvicorn app.main:app --reload

# Iniciar scheduler
RUN_MODE=scheduler uv run python -m app.workers.scheduler

# Iniciar worker (legado)
RUN_MODE=worker uv run python -m app.workers.fila_worker
```

### Railway (Producao)

```bash
# Ver logs do scheduler
railway logs --service whats-agents-scheduler

# Ver logs da API
railway logs --service whats-agents

# Ver ultimas 50 linhas
railway logs --service whats-agents-scheduler -n 50

# Filtrar por job especifico
railway logs --service whats-agents-scheduler | grep "processar_grupos"

# Ver jobs que falharam
railway logs --service whats-agents-scheduler | grep "FAIL"

# Ver jobs em execucao
railway logs --service whats-agents-scheduler | grep "Executando job"

# Reiniciar scheduler
railway redeploy --service whats-agents-scheduler

# Reiniciar API
railway redeploy --service whats-agents
```

## Monitoramento

### Endpoints de Health Check

```bash
# Health geral da API
curl https://api.revoluna.com/health

# Status dos jobs (ultimas 24h)
curl https://api.revoluna.com/health/jobs

# Status de jobs individuais
curl https://api.revoluna.com/health/jobs | jq '.jobs.processar_grupos'

# Fila de mensagens
curl https://api.revoluna.com/health/fila

# Worker de grupos
curl https://api.revoluna.com/health/grupos

# Alertas consolidados
curl https://api.revoluna.com/health/alerts

# Score geral do sistema (0-100)
curl https://api.revoluna.com/health/score
```

### Metricas de Jobs (Tabela job_executions)

Cada execucao de job e registrada na tabela `job_executions` com:

- `id`: UUID da execucao
- `job_name`: Nome do job (ex: "processar_grupos")
- `started_at`: Timestamp de inicio (UTC)
- `finished_at`: Timestamp de fim (UTC)
- `status`: success | error | timeout
- `duration_ms`: Duracao em milissegundos
- `response_code`: HTTP status code do endpoint
- `error`: Mensagem de erro (se houver, truncada em 500 chars)
- `items_processed`: Quantidade de itens processados (se disponivel)

### Queries Uteis

```sql
-- Ultimas 20 execucoes de um job
SELECT job_name, started_at, status, duration_ms, items_processed
FROM job_executions
WHERE job_name = 'processar_grupos'
ORDER BY started_at DESC
LIMIT 20;

-- Jobs que falharam nas ultimas 24h
SELECT job_name, started_at, error
FROM job_executions
WHERE status = 'error'
  AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;

-- Media de duracao por job (ultimos 7 dias)
SELECT
  job_name,
  COUNT(*) as execucoes,
  AVG(duration_ms) as duracao_media_ms,
  MAX(duration_ms) as duracao_max_ms,
  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as erros
FROM job_executions
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY job_name
ORDER BY duracao_media_ms DESC;

-- Jobs que nao rodaram nas ultimas 2h (stale)
SELECT DISTINCT job_name
FROM job_executions
WHERE job_name IN (
  'heartbeat',
  'processar_mensagens_agendadas',
  'processar_campanhas_agendadas',
  'processar_grupos'
)
AND started_at > NOW() - INTERVAL '2 hours'
ORDER BY job_name;

-- Itens processados por job hoje
SELECT
  job_name,
  COUNT(*) as execucoes,
  SUM(items_processed) as total_processados
FROM job_executions
WHERE DATE(started_at) = CURRENT_DATE
  AND items_processed IS NOT NULL
GROUP BY job_name
ORDER BY total_processados DESC;
```

### SLA por Job

O sistema define SLAs baseados na frequencia de cada job:

| Frequencia | SLA | Jobs |
|------------|-----|------|
| 1 minuto | 3 minutos | `heartbeat`, `processar_mensagens_agendadas`, `processar_campanhas_agendadas`, `processar_grupos` |
| 5 minutos | 15 minutos | `verificar_whatsapp`, `sincronizar_chips`, `validar_telefones` |
| 10 minutos | 30 minutos | `processar_handoffs` |
| 15 minutos | 45 minutos | `verificar_alertas`, `verificar_alertas_grupos`, `atualizar_trust_scores` |
| 1 hora | 2 horas | `sincronizar_briefing`, `processar_confirmacao_plantao`, `oferta_autonoma` |
| Diario | 25 horas | Jobs diarios |
| Semanal | 8 dias | Jobs semanais |

Se um job nao rodar dentro do SLA, o status muda para **stale** (critico se for job critico).

### Jobs Criticos

Estes jobs DEVEM estar rodando para o sistema funcionar:

- `processar_mensagens_agendadas`
- `processar_campanhas_agendadas`
- `verificar_whatsapp`
- `processar_grupos`

Se qualquer job critico estiver stale, o `/health/jobs` retorna `status: "critical"`.

## Troubleshooting

### Scheduler nao esta rodando

**Sintomas**: Jobs nao executam, `/health/jobs` mostra jobs criticos stale

**Diagnostico**:

```bash
# Ver se scheduler esta ativo
railway logs --service whats-agents-scheduler -n 20

# Verificar se container esta rodando
railway status --service whats-agents-scheduler

# Ver ultimo heartbeat
curl https://api.revoluna.com/health/jobs | jq '.jobs.heartbeat'
```

**Solucao**:

```bash
# Reiniciar scheduler
railway redeploy --service whats-agents-scheduler

# Se persistir, verificar variaveis de ambiente
railway variables --service whats-agents-scheduler | grep RUN_MODE
# Deve retornar: RUN_MODE=scheduler
```

### Job falhando repetidamente

**Diagnostico**:

```bash
# Ver logs do job especifico
railway logs --service whats-agents-scheduler | grep "nome_do_job"

# Ver erros na tabela de execucoes
SELECT started_at, error
FROM job_executions
WHERE job_name = 'nome_do_job'
  AND status = 'error'
ORDER BY started_at DESC
LIMIT 10;

# Verificar endpoint do job diretamente
curl -X POST https://api.revoluna.com/jobs/nome-do-endpoint
```

**Solucoes comuns**:

- **Timeout (300s)**: Job muito lento, otimizar ou aumentar batch size
- **Connection refused**: API esta down, verificar servico `whats-agents`
- **500 error**: Bug no endpoint, verificar logs da API
- **429 Too Many Requests**: Rate limit externo (Evolution, Chatwoot), aguardar

### Fila acumulando (backlog alto)

**Diagnostico**:

```bash
# Verificar estatisticas da fila
curl https://api.revoluna.com/health/fila | jq

# Verificar se job esta processando
SELECT COUNT(*)
FROM fila_mensagens
WHERE status = 'pendente';

# Ver ultimas execucoes do job
SELECT started_at, status, items_processed
FROM job_executions
WHERE job_name = 'processar_mensagens_agendadas'
ORDER BY started_at DESC
LIMIT 10;
```

**Solucoes**:

```sql
-- Ver se ha mensagens travadas (processando por muito tempo)
SELECT id, created_at, telefone_destino
FROM fila_mensagens
WHERE status = 'processando'
  AND updated_at < NOW() - INTERVAL '5 minutes';

-- Resetar mensagens travadas para pendente
UPDATE fila_mensagens
SET status = 'pendente', tentativas = tentativas + 1
WHERE status = 'processando'
  AND updated_at < NOW() - INTERVAL '5 minutes';
```

```bash
# Se rate limit, verificar limites
curl https://api.revoluna.com/health/rate-limit | jq

# Se chip pool vazio, verificar chips
curl https://api.revoluna.com/health/chips | jq '.summary'
```

### Jobs de grupos travados

**Diagnostico**:

```bash
# Ver health do worker de grupos
curl https://api.revoluna.com/health/grupos | jq

# Ver itens travados
SELECT estagio, COUNT(*)
FROM grupo_pipeline_fila
WHERE status = 'pendente'
  AND updated_at < NOW() - INTERVAL '1 hour'
GROUP BY estagio;
```

**Solucao**:

```sql
-- Ver se ha itens travados em um estagio especifico
SELECT id, grupo_id, estagio, erro
FROM grupo_pipeline_fila
WHERE status = 'pendente'
  AND estagio = 'extracao'  -- ou outro estagio
  AND updated_at < NOW() - INTERVAL '1 hour'
LIMIT 20;

-- Resetar itens travados
UPDATE grupo_pipeline_fila
SET status = 'pendente', tentativas = tentativas + 1, erro = NULL
WHERE status = 'pendente'
  AND updated_at < NOW() - INTERVAL '1 hour';
```

### Verificar execucao manual de um job

Para testar um job sem esperar o schedule:

```bash
# Executar job manualmente
curl -X POST https://api.revoluna.com/jobs/processar-grupos

# Com parametros (se o endpoint aceitar)
curl -X POST "https://api.revoluna.com/jobs/report-periodo?tipo=manha"

# Ver resultado
curl -X POST https://api.revoluna.com/jobs/processar-grupos | jq
```

### Horario de execucao incorreto

**Problema**: Job rodando em horario errado

**Causa**: Scheduler usa horario de Brasilia, mas servidor pode estar em UTC

**Verificacao**:

```bash
# Ver horario atual do scheduler (deve estar em logs)
railway logs --service whats-agents-scheduler | grep "Hora atual"

# Comparar com horario esperado
date -u  # UTC
TZ=America/Sao_Paulo date  # Brasilia
```

**Solucao**: Os schedules ja consideram o timezone de Brasilia. Se o job nao esta rodando no horario certo, verificar a cron expression no arquivo `app/workers/scheduler.py`.

### Circuit breaker aberto

**Sintomas**: Jobs falhando com erro "circuit open"

**Diagnostico**:

```bash
# Ver status dos circuits
curl https://api.revoluna.com/health/circuits | jq

# Ver historico de transicoes
curl "https://api.revoluna.com/health/circuits/history?circuit_name=evolution&horas=24" | jq
```

**Solucao**:

- **Circuit aberto**: Aguardar 60s (periodo de timeout) ou reiniciar API
- **Falhas consecutivas**: Resolver problema raiz (Evolution down, Supabase lento, etc)

## Desenvolvimento

### Adicionar novo job

1. Criar endpoint em `/jobs/*` (arquivo `app/api/routes/jobs.py`)
2. Adicionar job ao array `JOBS` em `app/workers/scheduler.py`
3. Testar localmente: `RUN_MODE=scheduler uv run python -m app.workers.scheduler`
4. Deploy: push para main, Railway faz deploy automatico

Exemplo:

```python
# Em app/workers/scheduler.py
JOBS = [
    # ... jobs existentes ...
    {
        "name": "meu_novo_job",
        "endpoint": "/jobs/meu-novo-job",
        "schedule": "0 * * * *",  # A cada hora
    },
]
```

### Testar job localmente

```bash
# Iniciar API local
RUN_MODE=api uv run uvicorn app.main:app --reload

# Em outro terminal, executar job
curl -X POST http://localhost:8000/jobs/meu-novo-job

# Ou iniciar scheduler local (vai executar todos os jobs agendados)
RUN_MODE=scheduler uv run python -m app.workers.scheduler
```

### Cron Expression Helper

Formato: `minuto hora dia mes dia_da_semana`

```
* * * * *        # A cada minuto
*/5 * * * *      # A cada 5 minutos
0 * * * *        # A cada hora (minuto 0)
0 9 * * *        # Todo dia as 9h
0 9 * * 1        # Segunda-feira as 9h
0 9,14 * * 1-5   # Seg-Sex as 9h e 14h
*/10 8-18 * * *  # A cada 10 min, das 8h as 18h
```

Dia da semana: `0=domingo, 1=segunda, ..., 6=sabado`

## Referencias

- Codigo fonte: `/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/workers/`
- Endpoints de jobs: `/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/jobs.py`
- Health checks: `/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/health.py`
- Entrypoint: `/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/scripts/entrypoint.sh`
- Dockerfile: `/Users/rafaelpivovar/Documents/Projetos/whatsapp-api/Dockerfile`
