# Workers e Scheduler

> Documentação operacional dos workers do sistema

## Visão Geral

O sistema possui diversos workers que executam tarefas em background, orquestrados pelo scheduler central.

## Arquitetura

```
app/workers/
├── __init__.py
├── __main__.py              # Entry point
├── scheduler.py             # Orquestrador central (~15k linhas)
├── fila_worker.py           # Processador de fila de mensagens
├── grupos_worker.py         # Processador de grupos WhatsApp
├── handoff_processor.py     # Processador de handoffs
├── pilot_mode.py            # Monitoramento de piloto
├── retomada_fora_horario.py # Retomada de mensagens fora do horário
└── temperature_decay.py     # Decaimento de temperatura de leads
```

## Workers Ativos

| Worker | Intervalo | Função | Criticidade |
|--------|-----------|--------|-------------|
| `scheduler` | Contínuo | Orquestra todos os jobs | Alta |
| `fila_worker` | 30s | Processa fila de mensagens | Alta |
| `grupos_worker` | 10min | Processa grupos WhatsApp | Média |
| `handoff_processor` | 5min | Processa handoffs pendentes | Média |
| `pilot_mode` | 15min | Monitora grupo piloto | Baixa |
| `retomada_fora_horario` | 08:00 diário | Retoma msgs fora do horário | Média |
| `temperature_decay` | 1h | Decai temperatura de leads | Baixa |

## Scheduler

O scheduler é o componente central que orquestra a execução de todos os jobs.

### Jobs Agendados

```python
# Exemplo de jobs no scheduler
SCHEDULED_JOBS = {
    "process_queue": {"interval": 30, "func": process_fila},
    "sync_briefing": {"cron": "0 * * * *", "func": sync_briefing},
    "daily_report": {"cron": "0 8 * * 1-5", "func": send_report},
    "shift_confirmation": {"cron": "*/30 * * * *", "func": check_shifts},
}
```

## Comandos

### Iniciar Workers

```bash
# Iniciar scheduler (inicia todos os workers)
uv run python -m app.workers

# Rodar worker específico
uv run python -m app.workers.fila_worker
```

### Em Produção (Railway)

```bash
# Ver logs do scheduler
railway logs --service whats-agents | grep scheduler

# Ver jobs em execução
railway logs --service whats-agents | grep "job started"
```

## Troubleshooting

### Worker Não Está Rodando

1. Verificar se o processo está ativo:
```bash
railway logs --service whats-agents | grep "worker" | tail -20
```

2. Verificar erros recentes:
```bash
railway logs --service whats-agents | grep "ERROR" | tail -20
```

3. Reiniciar o serviço se necessário:
```bash
railway redeploy
```

### Fila de Mensagens Acumulando

1. Verificar tamanho da fila:
```sql
SELECT COUNT(*) FROM fila_mensagens WHERE status = 'pendente';
```

2. Verificar rate limits:
```bash
redis-cli KEYS "rate:*" | head -20
```

3. Verificar se fila_worker está processando:
```bash
railway logs | grep "fila_worker" | tail -20
```

### Jobs Não Executando

1. Verificar scheduler:
```bash
railway logs | grep "scheduler" | tail -50
```

2. Verificar horário do servidor (UTC):
```bash
date -u
```

3. Verificar cron expressions nos jobs

## Monitoramento

### Métricas

| Métrica | Descrição | Alerta Se |
|---------|-----------|-----------|
| `queue_size` | Tamanho da fila | > 100 |
| `job_duration_seconds` | Duração do job | > 60s |
| `job_failures` | Falhas nos últimos 5min | > 3 |
| `scheduler_lag` | Atraso do scheduler | > 30s |

### Health Check

```bash
curl http://localhost:8000/health/workers
```

Resposta esperada:
```json
{
  "scheduler": "running",
  "fila_worker": "healthy",
  "last_job_at": "2025-01-16T10:30:00Z",
  "queue_size": 5
}
```

## Configuração

### Variáveis de Ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `WORKER_CONCURRENCY` | Workers paralelos | 4 |
| `QUEUE_POLL_INTERVAL` | Intervalo de poll (s) | 30 |
| `JOB_TIMEOUT` | Timeout de job (s) | 300 |

## Referências

- Código: `app/workers/`
- Logs: `railway logs`
