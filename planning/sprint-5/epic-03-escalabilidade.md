# Epic 3: Escalabilidade

## Objetivo

> **Preparar sistema para suportar 1000+ médicos com performance.**

---

## Stories

---

# S5.E3.1 - Otimizar queries do banco

## Objetivo

> **Garantir que queries principais sejam eficientes em escala.**

**Resultado esperado:** Queries principais executam em < 100ms.

## Tarefas

### 1. Identificar queries lentas

```python
# scripts/analisar_queries.py

import time
from app.core.supabase import supabase

QUERIES_CRITICAS = [
    {
        "nome": "buscar_medico_por_telefone",
        "query": lambda: supabase.table("clientes").select("*").eq("telefone", "+5511999999999").execute()
    },
    {
        "nome": "buscar_conversa_ativa",
        "query": lambda: supabase.table("conversations").select("*").eq("cliente_id", "uuid").eq("status", "ativa").execute()
    },
    {
        "nome": "carregar_historico",
        "query": lambda: supabase.table("interacoes").select("*").eq("conversa_id", "uuid").order("created_at", desc=True).limit(20).execute()
    },
    {
        "nome": "buscar_vagas",
        "query": lambda: supabase.table("vagas").select("*, hospitais(*), periodos(*)").eq("especialidade_id", "uuid").eq("status", "aberta").limit(10).execute()
    },
]

def medir_queries():
    """Mede tempo de execução das queries críticas."""
    resultados = []

    for q in QUERIES_CRITICAS:
        tempos = []
        for _ in range(10):  # 10 execuções
            inicio = time.time()
            try:
                q["query"]()
            except:
                pass
            tempos.append(time.time() - inicio)

        resultados.append({
            "nome": q["nome"],
            "media_ms": sum(tempos) / len(tempos) * 1000,
            "max_ms": max(tempos) * 1000,
            "min_ms": min(tempos) * 1000
        })

    return resultados
```

### 2. Criar índices otimizados

```sql
-- migration: criar_indices_performance.sql

-- Índice para busca de cliente por telefone
CREATE INDEX IF NOT EXISTS idx_clientes_telefone
ON clientes(telefone);

-- Índice para busca de conversa ativa
CREATE INDEX IF NOT EXISTS idx_conversations_cliente_status
ON conversations(cliente_id, status)
WHERE status = 'ativa';

-- Índice para histórico de interações
CREATE INDEX IF NOT EXISTS idx_interacoes_conversa_data
ON interacoes(conversa_id, created_at DESC);

-- Índice para vagas abertas
CREATE INDEX IF NOT EXISTS idx_vagas_especialidade_status
ON vagas(especialidade_id, status, data_plantao)
WHERE status = 'aberta';

-- Índice para fila de mensagens
CREATE INDEX IF NOT EXISTS idx_fila_processamento
ON fila_mensagens(status, prioridade DESC, agendar_para)
WHERE status = 'pendente';

-- Índice para busca por tags
CREATE INDEX IF NOT EXISTS idx_clientes_tags
ON clientes USING GIN(tags);
```

### 3. Otimizar queries específicas

```python
# app/services/medico.py (otimizado)

async def buscar_medico_por_telefone_otimizado(telefone: str) -> dict | None:
    """
    Busca médico por telefone com query otimizada.

    Usa índice idx_clientes_telefone.
    """
    response = (
        supabase.table("clientes")
        .select("id, primeiro_nome, especialidade_id, status, tags, preferencias")  # Seleciona apenas campos necessários
        .eq("telefone", telefone)
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None


# app/services/conversa.py (otimizado)

async def buscar_conversa_ativa_otimizada(cliente_id: str) -> dict | None:
    """
    Busca conversa ativa com query otimizada.

    Usa índice idx_conversations_cliente_status.
    """
    response = (
        supabase.table("conversations")
        .select("id, cliente_id, status, controlled_by, chatwoot_conversation_id")
        .eq("cliente_id", cliente_id)
        .eq("status", "ativa")
        .limit(1)
        .execute()
    )

    return response.data[0] if response.data else None
```

## DoD

- [ ] Queries críticas identificadas
- [ ] Tempos de execução medidos
- [ ] Índices criados
- [ ] Queries principais < 100ms
- [ ] Script de benchmark disponível

---

# S5.E3.2 - Implementar cache Redis

## Objetivo

> **Reduzir carga no banco com cache de dados frequentes.**

**Resultado esperado:** Dados frequentes servidos do cache em < 10ms.

## Tarefas

### 1. Configurar cliente Redis

```python
# app/core/redis.py

import redis.asyncio as redis
from app.core.config import settings

class RedisCache:
    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

    async def get(self, key: str) -> str | None:
        """Obtém valor do cache."""
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: int = 300):
        """Define valor no cache com TTL em segundos."""
        await self.redis.setex(key, ttl, value)

    async def delete(self, key: str):
        """Remove valor do cache."""
        await self.redis.delete(key)

    async def get_json(self, key: str) -> dict | None:
        """Obtém JSON do cache."""
        data = await self.get(key)
        if data:
            import json
            return json.loads(data)
        return None

    async def set_json(self, key: str, value: dict, ttl: int = 300):
        """Define JSON no cache."""
        import json
        await self.set(key, json.dumps(value), ttl)


cache = RedisCache()
```

### 2. Cache de médicos

```python
# app/services/medico.py (com cache)

from app.core.redis import cache

CACHE_TTL_MEDICO = 300  # 5 minutos

async def buscar_medico_por_telefone(telefone: str) -> dict | None:
    """Busca médico por telefone com cache."""
    cache_key = f"medico:telefone:{telefone}"

    # Tentar cache primeiro
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    # Buscar no banco
    response = (
        supabase.table("clientes")
        .select("*")
        .eq("telefone", telefone)
        .limit(1)
        .execute()
    )

    if response.data:
        medico = response.data[0]
        # Salvar no cache
        await cache.set_json(cache_key, medico, CACHE_TTL_MEDICO)
        return medico

    return None


async def invalidar_cache_medico(medico_id: str, telefone: str = None):
    """Invalida cache do médico após atualização."""
    await cache.delete(f"medico:id:{medico_id}")
    if telefone:
        await cache.delete(f"medico:telefone:{telefone}")
```

### 3. Cache de vagas

```python
# app/services/vaga.py (com cache)

CACHE_TTL_VAGAS = 60  # 1 minuto (vagas mudam frequentemente)

async def buscar_vagas_compativeis(medico: dict, limite: int = 5) -> list:
    """Busca vagas com cache."""
    especialidade_id = medico.get("especialidade_id")
    cache_key = f"vagas:especialidade:{especialidade_id}:limite:{limite}"

    # Tentar cache
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    # Buscar no banco
    vagas = await _buscar_vagas_banco(especialidade_id, limite)

    # Salvar no cache
    await cache.set_json(cache_key, vagas, CACHE_TTL_VAGAS)

    return vagas


async def invalidar_cache_vagas(especialidade_id: str = None):
    """Invalida cache de vagas após alteração."""
    if especialidade_id:
        # Invalidar padrão específico
        keys = await cache.redis.keys(f"vagas:especialidade:{especialidade_id}:*")
    else:
        keys = await cache.redis.keys("vagas:*")

    for key in keys:
        await cache.delete(key)
```

### 4. Cache de contexto

```python
# app/services/contexto.py (com cache)

CACHE_TTL_CONTEXTO = 120  # 2 minutos

async def montar_contexto_completo(medico: dict, conversa: dict) -> dict:
    """Monta contexto com cache de partes estáticas."""
    cache_key = f"contexto:medico:{medico['id']}"

    # Partes estáticas podem ser cacheadas
    cached = await cache.get_json(cache_key)
    if cached:
        contexto_estatico = cached
    else:
        contexto_estatico = {
            "medico": formatar_contexto_medico(medico),
            "especialidade": montar_contexto_especialidade(medico),
        }
        await cache.set_json(cache_key, contexto_estatico, CACHE_TTL_CONTEXTO)

    # Partes dinâmicas sempre buscam
    contexto_dinamico = {
        "vagas": await buscar_vagas_compativeis(medico),
        "historico": await carregar_historico(conversa["id"])
    }

    return {**contexto_estatico, **contexto_dinamico}
```

## DoD

- [ ] Cliente Redis configurado
- [ ] Cache de médicos funciona
- [ ] Cache de vagas funciona
- [ ] Cache de contexto funciona
- [ ] Invalidação de cache implementada
- [ ] Tempo de resposta < 10ms para cache hit

---

# S5.E3.3 - Monitoramento de performance

## Objetivo

> **Implementar monitoramento em tempo real de performance.**

**Resultado esperado:** Alertas quando performance degradar.

## Tarefas

### 1. Métricas de aplicação

```python
# app/core/metrics.py

import time
from functools import wraps
from collections import defaultdict
from datetime import datetime

class MetricsCollector:
    def __init__(self):
        self.tempos = defaultdict(list)
        self.contadores = defaultdict(int)
        self.erros = defaultdict(int)

    def medir_tempo(self, nome: str):
        """Decorator para medir tempo de execução."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                inicio = time.time()
                try:
                    resultado = await func(*args, **kwargs)
                    self.registrar_tempo(nome, time.time() - inicio)
                    self.incrementar(f"{nome}_sucesso")
                    return resultado
                except Exception as e:
                    self.registrar_erro(nome, str(e))
                    raise
            return wrapper
        return decorator

    def registrar_tempo(self, nome: str, tempo: float):
        """Registra tempo de execução."""
        self.tempos[nome].append({
            "tempo": tempo,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Manter apenas últimos 1000
        if len(self.tempos[nome]) > 1000:
            self.tempos[nome] = self.tempos[nome][-1000:]

    def incrementar(self, nome: str):
        """Incrementa contador."""
        self.contadores[nome] += 1

    def registrar_erro(self, nome: str, erro: str):
        """Registra erro."""
        self.erros[nome] += 1
        self.incrementar(f"{nome}_erro")

    def obter_resumo(self) -> dict:
        """Retorna resumo das métricas."""
        resumo = {}

        for nome, tempos in self.tempos.items():
            valores = [t["tempo"] for t in tempos[-100:]]  # Últimos 100
            if valores:
                resumo[nome] = {
                    "media_ms": sum(valores) / len(valores) * 1000,
                    "max_ms": max(valores) * 1000,
                    "min_ms": min(valores) * 1000,
                    "total": len(tempos)
                }

        resumo["contadores"] = dict(self.contadores)
        resumo["erros"] = dict(self.erros)

        return resumo


metrics = MetricsCollector()
```

### 2. Aplicar métricas nos serviços

```python
# app/services/agente.py (com métricas)

from app.core.metrics import metrics

@metrics.medir_tempo("gerar_resposta")
async def gerar_resposta(mensagem: str, contexto: dict) -> str:
    """Gera resposta com monitoramento."""
    # ... implementação ...


@metrics.medir_tempo("processar_webhook")
async def processar_webhook(payload: dict):
    """Processa webhook com monitoramento."""
    # ... implementação ...


# app/services/vaga.py
@metrics.medir_tempo("buscar_vagas")
async def buscar_vagas_compativeis(medico: dict, limite: int = 5) -> list:
    # ... implementação ...
```

### 3. Endpoint de métricas

```python
# app/routes/admin.py (adicionar)

@router.get("/metricas/performance")
async def metricas_performance():
    """Retorna métricas de performance."""
    return metrics.obter_resumo()


@router.get("/metricas/health")
async def health_check():
    """Health check detalhado."""
    resumo = metrics.obter_resumo()

    # Verificar thresholds
    problemas = []

    for nome, dados in resumo.items():
        if isinstance(dados, dict) and "media_ms" in dados:
            if dados["media_ms"] > 1000:  # > 1s
                problemas.append(f"{nome}: {dados['media_ms']:.0f}ms (muito lento)")

    return {
        "status": "healthy" if not problemas else "degraded",
        "problemas": problemas,
        "metricas": resumo
    }
```

### 4. Alertas de performance

```python
# app/services/alertas.py (adicionar)

async def verificar_performance():
    """Verifica performance e envia alertas se necessário."""
    resumo = metrics.obter_resumo()

    alertas = []

    for nome, dados in resumo.items():
        if isinstance(dados, dict) and "media_ms" in dados:
            # Tempo médio > 2s
            if dados["media_ms"] > 2000:
                alertas.append({
                    "tipo": "performance_critica",
                    "mensagem": f"{nome}: tempo médio {dados['media_ms']:.0f}ms",
                    "severidade": "critical"
                })
            # Tempo médio > 1s
            elif dados["media_ms"] > 1000:
                alertas.append({
                    "tipo": "performance_warning",
                    "mensagem": f"{nome}: tempo médio {dados['media_ms']:.0f}ms",
                    "severidade": "warning"
                })

    for alerta in alertas:
        await enviar_alerta_slack(alerta)

    return alertas
```

## DoD

- [ ] Collector de métricas implementado
- [ ] Métricas aplicadas nos serviços principais
- [ ] Endpoint de métricas disponível
- [ ] Health check detalhado
- [ ] Alertas de performance funcionando

---

# S5.E3.4 - Documentação de operações

## Objetivo

> **Criar documentação completa para operação do sistema.**

**Resultado esperado:** Runbook com procedimentos operacionais.

## Tarefas

### 1. Criar runbook

```markdown
# Runbook Operacional - Júlia

## Arquitetura

```
[WhatsApp] → [Evolution API] → [FastAPI] → [Claude API]
                                    ↓
                              [Supabase]
                                    ↓
                              [Chatwoot]
```

## Serviços

| Serviço | URL | Health Check |
|---------|-----|--------------|
| API | http://api.julia.com | /health |
| Evolution | http://localhost:8080 | /status |
| Chatwoot | http://localhost:3000 | /api/v1/profile |
| Redis | localhost:6379 | PING |

## Comandos Úteis

### Docker
```bash
# Ver status
docker compose ps

# Logs
docker compose logs -f api

# Reiniciar serviço
docker compose restart api
```

### Banco de Dados
```sql
-- Conversas ativas
SELECT COUNT(*) FROM conversations WHERE status = 'ativa';

-- Fila pendente
SELECT COUNT(*) FROM fila_mensagens WHERE status = 'pendente';

-- Handoffs pendentes
SELECT * FROM handoffs WHERE status = 'pendente';
```

## Procedimentos

### 1. Alta taxa de erros
1. Verificar logs: `docker compose logs -f api`
2. Verificar métricas: GET /admin/metricas/performance
3. Verificar saúde: GET /admin/metricas/health
4. Se Redis: `redis-cli PING`
5. Se banco: verificar conexões Supabase

### 2. WhatsApp desconectado
1. Acessar Evolution: http://localhost:8080
2. Verificar status da instância
3. Se desconectado, escanear QR novamente
4. Testar envio manual

### 3. Fila congestionada
1. Verificar quantidade: SELECT COUNT(*) FROM fila_mensagens WHERE status = 'pendente'
2. Verificar worker: docker compose logs -f worker
3. Se travado, reiniciar: docker compose restart worker
4. Verificar rate limiting

### 4. Handoff não notificado
1. Verificar webhook Slack configurado
2. Testar webhook manual
3. Verificar logs de notificação
4. Verificar Chatwoot (label "humano")
```

### 2. Documentar variáveis de ambiente

```markdown
# Variáveis de Ambiente

## Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| SUPABASE_URL | URL do projeto Supabase | https://xxx.supabase.co |
| SUPABASE_KEY | Chave de serviço | eyJ... |
| ANTHROPIC_API_KEY | Chave da API Anthropic | sk-ant-... |
| EVOLUTION_URL | URL da Evolution API | http://localhost:8080 |
| EVOLUTION_API_KEY | Chave da Evolution | xxx |
| REDIS_URL | URL do Redis | redis://localhost:6379 |

## Opcionais

| Variável | Descrição | Default |
|----------|-----------|---------|
| LOG_LEVEL | Nível de log | INFO |
| MAX_WORKERS | Workers paralelos | 4 |
| CACHE_TTL | TTL do cache em segundos | 300 |

## Chatwoot

| Variável | Descrição |
|----------|-----------|
| CHATWOOT_URL | URL do Chatwoot |
| CHATWOOT_API_TOKEN | Token de API |
| CHATWOOT_ACCOUNT_ID | ID da conta |
| CHATWOOT_INBOX_ID | ID do inbox |

## Slack

| Variável | Descrição |
|----------|-----------|
| SLACK_WEBHOOK_URL | URL do webhook |
```

### 3. Documentar troubleshooting

```markdown
# Troubleshooting

## Mensagens não estão sendo enviadas

### Sintomas
- Fila cresce mas não processa
- Logs mostram erros de envio

### Diagnóstico
1. Verificar status Evolution API
2. Verificar conexão WhatsApp
3. Verificar rate limiting

### Solução
- Se Evolution offline: reiniciar container
- Se WhatsApp desconectado: reconectar via QR
- Se rate limit: aguardar ou ajustar limites

## Respostas muito lentas

### Sintomas
- Tempo de resposta > 30s
- Usuários reclamando

### Diagnóstico
1. GET /admin/metricas/performance
2. Identificar operação lenta
3. Verificar uso de recursos

### Solução
- Se banco lento: verificar índices, conexões
- Se LLM lento: verificar status Anthropic
- Se cache miss alto: verificar Redis

## Handoff não funciona

### Sintomas
- Label adicionada mas Júlia continua respondendo
- Gestor não notificado

### Diagnóstico
1. Verificar webhook Chatwoot configurado
2. Verificar campo controlled_by na conversa
3. Verificar logs de handoff

### Solução
- Se webhook não configurado: configurar em Chatwoot
- Se campo não atualiza: verificar integração
- Se Slack não notifica: verificar webhook URL
```

## DoD

- [ ] Runbook criado
- [ ] Variáveis de ambiente documentadas
- [ ] Troubleshooting documentado
- [ ] Procedimentos de emergência
- [ ] Comandos úteis listados
