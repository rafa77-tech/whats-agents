# Epic 04 - Health Center

## Objetivo
Criar pagina `/health` que consolida todas as informacoes de saude do sistema em um unico lugar: circuit breakers, rate limiting, conexoes, alertas e score geral.

## APIs Disponiveis (Backend Pronto - 15+ endpoints)

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/health` | GET | Liveness basico |
| `/health/ready` | GET | Readiness (Redis + Supabase) |
| `/health/deep` | GET | Deep check para CI/CD |
| `/health/score` | GET | Health score consolidado (0-100) |
| `/health/alerts` | GET | Alertas consolidados |
| `/health/circuits` | GET | Status dos circuit breakers |
| `/health/circuits/history` | GET | Historico de transicoes |
| `/health/rate-limit` | GET | Estatisticas de rate limiting |
| `/health/whatsapp` | GET | Status conexao WhatsApp |
| `/health/fila` | GET | Metricas da fila de mensagens |
| `/health/jobs` | GET | Status das execucoes dos jobs |
| `/health/pilot` | GET | Status do modo piloto |
| `/health/chips` | GET | Dashboard de saude dos chips |
| `/health/grupos` | GET | Health check do worker de grupos |
| `/health/telefones` | GET | Estatisticas de validacao |

## Stories

---

### S43.E4.1 - Pagina Health Center (Overview)

**Objetivo:** Dashboard consolidado de saude com score geral e alertas.

**Layout:**
```
+----------------------------------------------------------+
| Health Center                              [Refresh] 30s  |
+----------------------------------------------------------+
|                    HEALTH SCORE                           |
|                       [85]                                |
|                    ████████░░                             |
|                     HEALTHY                               |
+----------------------------------------------------------+
| Alertas Ativos: 3                                         |
| +------------------------------------------------------+ |
| | ! Rate limit proximo do limite (85%)         [Ver]   | |
| | ! Circuit breaker LLM em half-open           [Ver]   | |
| | ! 2 chips com trust score baixo              [Ver]   | |
| +------------------------------------------------------+ |
+----------------------------------------------------------+
| Status Rapido:                                            |
| [WhatsApp]  [Redis]  [Supabase]  [LLM]  [Fila]          |
|    OK         OK        OK        WARN     OK            |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar rota `/health` no dashboard
2. Componente `HealthScore` com gauge visual
3. Lista de alertas ativos
4. Status icons para servicos principais

**API Calls:**
- `GET /health/score` - Score consolidado
- `GET /health/alerts` - Alertas ativos
- `GET /health/ready` - Status basico
- `GET /health/whatsapp` - Status WhatsApp

**DoD:**
- [ ] Pagina criada
- [ ] Score visual com gauge
- [ ] Alertas listados
- [ ] Status dos servicos
- [ ] Auto-refresh a cada 30s
- [ ] Testes unitarios

---

### S43.E4.2 - Circuit Breakers Dashboard

**Objetivo:** Visualizar e gerenciar circuit breakers do sistema.

**Layout:**
```
+----------------------------------------------------------+
| Circuit Breakers                                          |
+----------------------------------------------------------+
| Circuit       | Estado    | Falhas | Ultimo Reset | Acao |
|---------------|-----------|--------|--------------|------|
| llm_provider  | CLOSED    | 0/5    | 2h atras     | [-]  |
| evolution_api | HALF_OPEN | 3/5    | 10min atras  | [R]  |
| supabase      | CLOSED    | 1/5    | 1h atras     | [-]  |
| chatwoot      | OPEN      | 5/5    | 5min atras   | [R]  |
+----------------------------------------------------------+
| Legenda: [R] = Reset Manual                               |
+----------------------------------------------------------+

--- Historico ---

+----------------------------------------------------------+
| Historico de Transicoes (ultimas 24h)                    |
+----------------------------------------------------------+
| 15:30 | evolution_api | CLOSED -> HALF_OPEN | 3 falhas   |
| 15:25 | chatwoot      | HALF_OPEN -> OPEN   | timeout    |
| 14:00 | llm_provider  | OPEN -> CLOSED      | reset      |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `CircuitBreakersPanel`
2. Tabela com estado atual de cada circuit
3. Botao de reset manual (com confirmacao)
4. Historico de transicoes
5. Indicadores visuais por estado (verde/amarelo/vermelho)

**API Calls:**
- `GET /health/circuits` - Estado atual
- `GET /health/circuits/history` - Historico
- `POST /health/circuits/{name}/reset` (se disponivel)

**DoD:**
- [ ] Tabela com estados
- [ ] Cores por estado
- [ ] Historico visivel
- [ ] Reset manual (se API disponivel)
- [ ] Testes unitarios

---

### S43.E4.3 - Rate Limiting & Fila

**Objetivo:** Visualizar uso de rate limiting e status da fila de mensagens.

**Layout:**
```
+----------------------------------------------------------+
| Rate Limiting                                             |
+----------------------------------------------------------+
| Por Hora:                        Por Dia:                 |
| [████████░░] 16/20 (80%)        [███░░░░░░░] 45/100 (45%) |
+----------------------------------------------------------+
| Historico de Uso (ultimas 6h):                           |
|     |    *                                                |
| 20 -|   * *    *                                         |
| 15 -|  *   *  * *                                        |
| 10 -| *     **   *                                       |
|  5 -|*           **                                      |
|     +-----|-----|-----|-----|-----|-----|                |
|          -5h   -4h   -3h   -2h   -1h   now               |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Fila de Mensagens                                         |
+----------------------------------------------------------+
| Pendentes: 5  |  Processando: 2  |  Processadas/h: 45    |
+----------------------------------------------------------+
| Tempo medio de espera: 2.3s                               |
| Maior espera atual: 8s                                    |
+----------------------------------------------------------+
```

**Tarefas:**
1. Criar componente `RateLimitPanel`
2. Barras de progresso por hora/dia
3. Grafico de uso historico
4. Componente `QueueStatus` para fila
5. Metricas de tempo de espera

**API Calls:**
- `GET /health/rate-limit` - Stats de rate limiting
- `GET /health/fila` - Metricas da fila

**DoD:**
- [ ] Barras de progresso
- [ ] Grafico historico
- [ ] Status da fila
- [ ] Metricas de tempo
- [ ] Testes unitarios

---

### S43.E4.4 - Jobs & Scheduler Status

**Objetivo:** Visualizar status dos jobs agendados e suas execucoes.

**Layout:**
```
+----------------------------------------------------------+
| Jobs Scheduler                                            |
+----------------------------------------------------------+
| Job                  | Ultimo Run | Duracao | Status | SLA|
|----------------------|------------|---------|--------|-----|
| processar_fila       | 2min atras | 1.2s    | OK     | OK |
| sincronizar_chips    | 5min atras | 3.4s    | OK     | OK |
| atualizar_trust      | 1h atras   | 45s     | OK     | OK |
| verificar_whatsapp   | 10min atras| 0.8s    | WARN   | MISS|
+----------------------------------------------------------+
| Jobs com SLA Miss: 1                                      |
| Jobs com Erro: 0                                          |
+----------------------------------------------------------+

--- Detalhes de Job ---

+------------------------------------------+
| Job: verificar_whatsapp                   |
+------------------------------------------+
| Frequencia: a cada 5 minutos              |
| SLA: 5 minutos                            |
| Ultimo sucesso: 10min atras (SLA MISS)    |
| Ultima falha: nunca                       |
+------------------------------------------+
| Ultimas 10 execucoes:                     |
| 14:30 OK 0.8s                             |
| 14:25 OK 0.7s                             |
| 14:20 SKIP (fora do horario)              |
+------------------------------------------+
```

**Tarefas:**
1. Criar componente `JobsStatusPanel`
2. Tabela com todos os jobs
3. Indicador de SLA (OK/MISS)
4. Modal de detalhes do job
5. Historico de execucoes

**API Calls:**
- `GET /health/jobs` - Status dos jobs

**DoD:**
- [ ] Tabela com jobs
- [ ] Indicadores de SLA
- [ ] Detalhes por job
- [ ] Historico visivel
- [ ] Testes unitarios

---

## Navegacao

Adicionar na sidebar:
```
Operacao
├── Dashboard
├── Monitor       (existente - jobs detalhado)
├── Integridade
├── Grupos
└── Health Center <- NOVO (visao consolidada)
```

## Componentes Reutilizaveis

1. `HealthGauge` - Gauge circular de 0-100
2. `StatusIndicator` - Icone com status (OK/WARN/ERROR)
3. `CircuitBadge` - Badge por estado do circuit (OPEN/HALF_OPEN/CLOSED)
4. `ProgressBar` - Barra de progresso com threshold de warning
5. `SparklineChart` - Grafico pequeno de historico

## Consideracoes Tecnicas

- Auto-refresh configuravel (15s/30s/60s/off)
- Notificacao sonora opcional para alertas criticos
- Export de diagnostico para suporte
- Deep link para alertas especificos
