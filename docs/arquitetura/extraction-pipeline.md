# Discovery Intelligence Pipeline

Documentacao tecnica do sistema de extracao automatica de dados de conversas usando LLM.

**Sprints:** 52 (Pipeline v3 para grupos), 53 (Discovery Intelligence Pipeline para conversas individuais)

**Status:** Producao

**Ultima Atualizacao:** Fevereiro 2026

---

## Visao Geral

O Discovery Intelligence Pipeline e um sistema de extracao automatica de dados estruturados a partir de conversas entre Julia e medicos. Utiliza Claude Haiku para extrair insights de cada turno de conversa, incluindo nivel de interesse, objecoes, preferencias, restricoes e sugestao de proximo passo.

### Objetivos

- Extrair dados estruturados de cada turno de conversa automaticamente
- Classificar interesse do medico em escala quantitativa (0.0-1.0)
- Detectar objecoes e suas severidades
- Identificar preferencias e restricoes mencionadas
- Sugerir proximo passo mais adequado (enviar vagas, follow-up, escalar, etc)
- Enriquecer base de conhecimento RAG (doctor_context) automaticamente
- Gerar relatorios qualitativos de campanhas usando LLM

### Beneficios

- **Custo minimo**: ~$0.0001 por extracao usando Haiku
- **Cache inteligente**: 24 horas de cache para extrações identicas
- **Alta precisao**: Confianca calculada pelo LLM para cada extracao
- **Escalavel**: Processa extrações em background via worker
- **Acionavel**: Identifica oportunidades concretas (prontos para vagas, follow-up, etc)

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FLUXO PRINCIPAL                          │
└─────────────────────────────────────────────────────────────────┘

Mensagem do Medico
        │
        v
┌──────────────────┐
│  Interacao Save  │ (conversations/interacoes)
└────────┬─────────┘
         │
         v
┌──────────────────────┐
│  Extraction Service  │
│  extrair_dados_      │
│    _conversa()       │
└──────┬───────────────┘
       │
       v
┌──────────────┐         ┌────────────┐
│   Cache?     │────Sim──│  Retorna   │
└──────┬───────┘         └────────────┘
       │ Nao
       v
┌──────────────────────┐
│   Claude Haiku       │
│   (EXTRACTION_PROMPT)│
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Parse JSON          │
│  → ExtractionResult  │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Persistence Layer   │
│  - conversation_     │
│    insights          │
│  - doctor_context    │
│    (memorias RAG)    │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      RELATORIO CAMPANHA                         │
└─────────────────────────────────────────────────────────────────┘

GET /extraction/campaign/{id}/report
        │
        v
┌──────────────────────┐
│  Report Generator    │
│  gerar_relatorio_    │
│    _campanha()       │
└──────┬───────────────┘
       │
       v
┌──────────────┐         ┌────────────┐
│   Cache?     │────Sim──│  Retorna   │
└──────┬───────┘         └────────────┘
       │ Nao
       v
┌──────────────────────┐
│  Agregar Insights    │
│  - Metricas          │
│  - Medicos destaque  │
│  - Objecoes          │
│  - Preferencias      │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│   Claude Haiku       │
│   (REPORT_PROMPT)    │
│   Gera analise       │
│   qualitativa Julia  │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  CampaignReport      │
│  (com relatorio_     │
│   julia)             │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          BACKFILL                               │
└─────────────────────────────────────────────────────────────────┘

POST /extraction/backfill
        │
        v
┌──────────────────────┐
│  Backfill Worker     │
│  (Background Task)   │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Buscar interacoes   │
│  dos ultimos N dias  │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Processar em        │
│  batches (50)        │
│  com rate limiting   │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│  Para cada interacao │
│  - Extrair           │
│  - Salvar insight    │
│  - Salvar memorias   │
└──────────────────────┘
```

---

## Modulos

### app/services/extraction/

Modulo principal de extracao de dados de conversas.

#### extractor.py
Servico de extracao usando Claude Haiku. Extrai dados estruturados de um turno de conversa.

**Funcao principal:**
- `extrair_dados_conversa(context: ExtractionContext) -> ExtractionResult`

**Features:**
- Cache de 24 horas (Redis)
- Retry com exponential backoff (3 tentativas)
- Temperature 0.1 para consistencia
- Validacao de input (mensagens muito curtas sao descartadas)

#### schemas.py
Definicao de tipos e enums para o sistema de extracao.

**Tipos principais:**
- `ExtractionContext`: Input para extracao (mensagem medico, resposta Julia, contexto)
- `ExtractionResult`: Output com dados extraidos (interesse, score, objecoes, preferencias, etc)
- `Interesse`: Enum (POSITIVO, NEGATIVO, NEUTRO, INCERTO)
- `ProximoPasso`: Enum (ENVIAR_VAGAS, AGENDAR_FOLLOWUP, AGUARDAR_RESPOSTA, ESCALAR_HUMANO, MARCAR_INATIVO, SEM_ACAO)
- `TipoObjecao`: Enum (PRECO, TEMPO, CONFIANCA, DISTANCIA, DISPONIBILIDADE, EMPRESA_ATUAL, PESSOAL, OUTRO)
- `SeveridadeObjecao`: Enum (BAIXA, MEDIA, ALTA)
- `Objecao`: Dataclass com tipo, descricao e severidade

#### persistence.py
Camada de persistencia para salvar insights e memorias extraidas.

**Funcoes principais:**
- `salvar_insight()`: Salva extracao na tabela conversation_insights
- `salvar_memorias_extraidas()`: Salva preferencias/restricoes como memorias RAG em doctor_context
- `atualizar_dados_cliente()`: Atualiza dados do cliente se confianca >= 0.7
- `buscar_insights_conversa()`: Busca insights de uma conversa
- `buscar_insights_cliente()`: Busca historico de insights de um cliente
- `buscar_insights_campanha()`: Busca insights de uma campanha

**Tabelas:**
- `conversation_insights`: Insights extraidos de cada turno
- `doctor_context`: Memorias RAG (preferencias, restricoes, disponibilidade, regiao)
- `clientes`: Atualizacao automatica de dados (apenas campos permitidos: especialidade, cidade, estado, regiao)

**Thresholds:**
- Auto-update de cliente: confianca >= 0.7
- Deteccao de duplicata de memoria: similaridade > 0.95 (embedding)

#### prompts.py
Prompt de extracao estruturado para Claude.

**Prompt:** `EXTRACTION_PROMPT`

**Instrucoes principais:**
- Classificacao de interesse em 4 niveis
- Score de interesse (0.0-1.0) com escala detalhada
- Extracao de especialidade/regiao apenas se mencionado EXPLICITAMENTE
- Deteccao de objecoes (8 tipos + severidade)
- Extracao de preferencias e restricoes explicitas
- Deteccao de dados corrigidos (divergencia com cadastro)
- Sugestao de proximo passo baseado no contexto
- Nivel de confianca da extracao (0.0-1.0)

**Output:** JSON estruturado parseado para ExtractionResult

#### report_generator.py
Gerador de relatorios qualitativos de campanhas usando LLM.

**Funcao principal:**
- `gerar_relatorio_campanha(campaign_id, force_refresh) -> CampaignReport`

**Fluxo:**
1. Verifica cache (1 hora)
2. Busca insights da campanha
3. Agrega metricas (total, interesse positivo/negativo, objecoes, etc)
4. Identifica medicos em destaque (interesse positivo ou acao pendente)
5. Agrega objecoes por tipo
6. Extrai preferencias comuns
7. Gera relatorio via LLM (Claude Haiku)
8. Salva no cache

**Tipos:**
- `CampaignReport`: Relatorio completo com metricas e analise Julia
- `CampaignReportMetrics`: Metricas agregadas (taxas, scores, contadores)
- `MedicoDestaque`: Medico em destaque com dados de interesse e insight
- `ObjecaoAgregada`: Objecao agregada por tipo com quantidade e exemplo

**Formato do relatorio:**
- O que funcionou (2-4 pontos)
- Pontos de atencao (2-3 problemas)
- Proximos passos sugeridos (3-5 acoes numeradas)
- Insight estrategico (1-2 paragrafos)

#### __init__.py
Exporta API publica do modulo.

---

### app/api/routes/extraction.py

Router FastAPI com endpoints para consulta e backfill.

---

### app/workers/backfill_extraction.py

Worker de backfill para processar conversas historicas.

---

## API Endpoints

### Consultas

#### GET /extraction/insights/conversation/{conversation_id}
Busca insights de uma conversa especifica.

**Parametros:**
- `conversation_id`: UUID da conversa
- `limit`: Numero maximo de resultados (default: 10, max: 50)

**Response:**
```json
{
  "conversation_id": "uuid",
  "total": 5,
  "insights": [...]
}
```

#### GET /extraction/insights/cliente/{cliente_id}
Busca historico de insights de um cliente.

**Parametros:**
- `cliente_id`: UUID do cliente
- `limit`: Numero maximo de resultados (default: 20, max: 100)

**Response:**
```json
{
  "cliente_id": "uuid",
  "total": 12,
  "resumo": {
    "interesse_positivo": 8,
    "interesse_negativo": 2,
    "interesse_score_medio": 0.72
  },
  "insights": [...]
}
```

#### GET /extraction/insights/campaign/{campaign_id}
Busca insights de uma campanha.

**Parametros:**
- `campaign_id`: ID da campanha
- `limit`: Numero maximo de resultados (default: 100, max: 500)

**Response:**
```json
{
  "campaign_id": 123,
  "total_insights": 87,
  "metricas": {
    "clientes_unicos": 65,
    "interesse_positivo": 42,
    "interesse_negativo": 15,
    "taxa_interesse_pct": 48.3,
    "prontos_para_vagas": 28
  },
  "insights": [...]
}
```

#### GET /extraction/campaign/{campaign_id}/report
Gera relatorio Julia para uma campanha.

**Parametros:**
- `campaign_id`: ID da campanha
- `force_refresh`: Ignorar cache e regenerar (default: false)

**Response:**
```json
{
  "campaign_id": 123,
  "campaign_name": "Campanha Cardio SP",
  "generated_at": "2026-02-10T14:30:00Z",
  "metrics": {
    "total_respostas": 87,
    "interesse_positivo": 42,
    "taxa_interesse_pct": 48.3,
    "interesse_score_medio": 6.8,
    "total_objecoes": 15,
    "objecao_mais_comum": "distancia",
    "prontos_para_vagas": 28,
    "para_followup": 12,
    "para_escalar": 3
  },
  "medicos_destaque": [...],
  "objecoes_encontradas": [...],
  "preferencias_comuns": ["plantao noturno", "UTI", "regiao ABC"],
  "relatorio_julia": "## ✅ O que funcionou\n...",
  "tokens_usados": 2340,
  "cached": false
}
```

**Cache:** 1 hora

#### GET /extraction/campaign-summary
Retorna resumo agregado de todas as campanhas com insights.

Usa a view materializada `campaign_insights`.

**Response:**
```json
{
  "total_campanhas": 15,
  "campanhas": [...]
}
```

#### GET /extraction/stats
Retorna estatisticas gerais do sistema de extracao.

**Response:**
```json
{
  "total_insights": 3542,
  "backfill": {
    "total_interacoes_30d": 4200,
    "total_insights_30d": 3800,
    "cobertura_pct": 90.5,
    "pendentes": 400
  },
  "distribuicao_interesse": {
    "positivo": 1520,
    "negativo": 680,
    "neutro": 920,
    "incerto": 422
  },
  "distribuicao_proximo_passo": {
    "enviar_vagas": 890,
    "agendar_followup": 650,
    "aguardar_resposta": 1200,
    "escalar_humano": 42,
    "marcar_inativo": 380,
    "sem_acao": 380
  }
}
```

#### GET /extraction/opportunities
Retorna oportunidades agrupadas por proximo_passo.

**Parametros:**
- `limit`: Numero maximo de resultados (default: 50, max: 200)
- `proximo_passo`: Filtrar por proximo_passo especifico (opcional)

**Response:**
```json
{
  "enviar_vagas": [...],
  "agendar_followup": [...],
  "escalar_humano": [...],
  "total": 150
}
```

Cada oportunidade inclui:
- Dados do insight
- Nome do cliente
- Especialidade do cliente
- Telefone do cliente
- Nome da campanha

---

### Backfill

#### POST /extraction/backfill
Dispara backfill de extracoes em background.

**CUIDADO:** Pode consumir muitos tokens de LLM se processar muitas interacoes. Use `dry_run=true` para simular primeiro.

**Request:**
```json
{
  "dias": 30,
  "campanha_id": 123,
  "dry_run": false,
  "max_interacoes": 1000
}
```

**Response:**
```json
{
  "status": "started",
  "message": "Backfill iniciado para ultimos 30 dias (campanha 123)"
}
```

**Executado em background** via FastAPI BackgroundTasks.

#### GET /extraction/backfill/status
Retorna status atual do backfill (cobertura, pendentes).

**Response:**
```json
{
  "total_interacoes_30d": 4200,
  "total_insights_30d": 3800,
  "cobertura_pct": 90.5,
  "pendentes": 400
}
```

---

### Administrativo

#### POST /extraction/refresh-campaign-view
Atualiza a view materializada `campaign_insights`.

Deve ser chamado periodicamente (ex: diariamente) para manter dados atualizados.

**Response:**
```json
{
  "status": "success",
  "message": "View atualizada com sucesso"
}
```

---

## Worker: Backfill Extraction

### Proposito

Processa conversas historicas para popular `conversation_insights` retroativamente.

### Funcionamento

1. Busca interacoes de medicos dos ultimos N dias
2. Filtra apenas mensagens de entrada (tipo="entrada", autor_tipo="medico")
3. Para cada interacao:
   - Verifica se ja foi processada (evita duplicatas)
   - Busca resposta da Julia imediatamente posterior
   - Busca dados do cliente
   - Cria ExtractionContext
   - Extrai dados via `extrair_dados_conversa()`
   - Salva insight em `conversation_insights`
   - Salva memorias em `doctor_context` se houver preferencias/restricoes
4. Processa em batches de 50 com rate limiting entre chamadas
5. Retorna estatisticas ao final

### Configuracao

**Constantes (em backfill_extraction.py):**
```python
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 5  # segundos
MAX_INTERACOES = 1000
DELAY_BETWEEN_CALLS = 0.5  # segundos (rate limit LLM)
```

### Uso

**Via API:**
```bash
curl -X POST http://localhost:8000/extraction/backfill \
  -H "Content-Type: application/json" \
  -d '{
    "dias": 30,
    "campanha_id": 123,
    "dry_run": false,
    "max_interacoes": 1000
  }'
```

**Dry run (simular sem salvar):**
```bash
curl -X POST http://localhost:8000/extraction/backfill \
  -H "Content-Type: application/json" \
  -d '{
    "dias": 7,
    "dry_run": true,
    "max_interacoes": 100
  }'
```

**Verificar cobertura:**
```bash
curl http://localhost:8000/extraction/backfill/status
```

### Estatisticas Retornadas

```python
{
  "total_interacoes": 850,        # Total encontrado para processar
  "processadas": 720,             # Processadas com sucesso
  "erros": 15,                    # Erros durante processamento
  "ja_processadas": 100,          # Ja existiam insights
  "sem_resposta": 15,             # Sem resposta da Julia
  "inicio": "2026-02-10T10:00:00Z",
  "fim": "2026-02-10T10:45:00Z",
  "dry_run": false
}
```

---

## Configuracao e Feature Flags

### Variaveis de Ambiente

```bash
# LLM (obrigatorio)
ANTHROPIC_API_KEY=sk-...

# Redis (para cache)
REDIS_URL=redis://localhost:6379

# Supabase (para persistencia)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
```

### Feature Flags

Nao ha feature flags especificos para o extraction pipeline. O sistema esta sempre ativo em producao.

Para o pipeline de grupos (v3), existe:
```bash
PIPELINE_V3_ENABLED=true  # Usar LLM unificado ao inves de regex (recomendado)
```

---

## Monitoramento e Troubleshooting

### Metricas-Chave

**Taxa de cobertura:**
```sql
SELECT
  COUNT(DISTINCT i.id) as total_interacoes,
  COUNT(DISTINCT ci.interaction_id) as total_insights,
  ROUND(COUNT(DISTINCT ci.interaction_id)::float / COUNT(DISTINCT i.id) * 100, 1) as cobertura_pct
FROM interacoes i
LEFT JOIN conversation_insights ci ON ci.interaction_id = i.id
WHERE i.tipo = 'entrada'
  AND i.autor_tipo = 'medico'
  AND i.created_at >= NOW() - INTERVAL '30 days';
```

**Distribuicao de interesse:**
```sql
SELECT
  interesse,
  COUNT(*) as quantidade,
  ROUND(AVG(interesse_score), 2) as score_medio
FROM conversation_insights
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY interesse
ORDER BY quantidade DESC;
```

**Objecoes mais comuns:**
```sql
SELECT
  objecao_tipo,
  objecao_severidade,
  COUNT(*) as quantidade
FROM conversation_insights
WHERE objecao_tipo IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY objecao_tipo, objecao_severidade
ORDER BY quantidade DESC;
```

**Proximos passos pendentes:**
```sql
SELECT
  proximo_passo,
  COUNT(*) as quantidade
FROM conversation_insights
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY proximo_passo
ORDER BY quantidade DESC;
```

### Logs

**Extrator:**
```
[Extraction] Cache hit para abc123...
[Extraction] interesse=positivo, score=0.85, confianca=0.90, latencia=450ms
[Extraction] Erro ao chamar LLM: {erro}
```

**Persistence:**
```
[Persistence] Insight salvo: 12345
[Persistence] 3 memorias salvas para cliente abc12345
[Persistence] Atualizando cliente abc12345: {"especialidade": "Cardiologia"} (confianca: 0.85)
[Persistence] Memoria duplicada ignorada: Prefiro plantoes...
```

**Report Generator:**
```
[Report] Relatório gerado para campanha 123: 87 respostas, 2340 tokens
[Report] Erro ao buscar campanha: {erro}
```

**Backfill:**
```
[Backfill] Iniciando backfill: dias=30, campanha_id=123, dry_run=false
[Backfill] Encontradas 850 interacoes para processar
[Backfill] Processando batch 1/17
[Backfill] Batch 1 concluido. Processadas: 45, Ja processadas: 5, Erros: 0
[Backfill] DRY RUN - Interacao 12345: interesse=positivo
[Backfill] Concluido: {...}
```

### Problemas Comuns

#### 1. Taxa de cobertura baixa

**Sintoma:** Muitas interacoes sem insights correspondentes.

**Causas possiveis:**
- Backfill nao executado
- Erros durante extracao (verificar logs)
- Mensagens muito curtas (< 2 caracteres) sao ignoradas

**Solucao:**
```bash
# Executar backfill para preencher lacunas
curl -X POST http://localhost:8000/extraction/backfill \
  -d '{"dias": 7, "dry_run": true, "max_interacoes": 100}'

# Verificar status
curl http://localhost:8000/extraction/backfill/status
```

#### 2. Confianca baixa nas extracoes

**Sintoma:** Muitos insights com confianca < 0.5.

**Causas possiveis:**
- Mensagens ambiguas ou muito curtas
- Contexto insuficiente para o LLM

**Solucao:**
- Revisar prompt de extracao (prompts.py)
- Verificar qualidade das mensagens (podem ser bot ou spam)
- Considerar ajustar threshold de confianca para auto-update (atualmente 0.7)

#### 3. Cache nao funcionando

**Sintoma:** Mesmas mensagens sendo processadas repetidamente.

**Causas possiveis:**
- Redis nao disponivel
- Erro ao salvar/buscar cache

**Solucao:**
```bash
# Verificar Redis
redis-cli ping

# Verificar logs
grep "Erro ao salvar cache\|Erro ao ler cache" logs/app.log
```

#### 4. Relatorio de campanha vazio

**Sintoma:** Relatorio retorna "Dados insuficientes para analise".

**Causas possiveis:**
- Campanha sem insights (nenhuma resposta processada)
- Insights com baixa qualidade

**Solucao:**
```bash
# Verificar se campanha tem insights
curl http://localhost:8000/extraction/insights/campaign/123

# Executar backfill para campanha especifica
curl -X POST http://localhost:8000/extraction/backfill \
  -d '{"dias": 30, "campanha_id": 123}'
```

#### 5. Erro de parse JSON do LLM

**Sintoma:** `[Extraction] Erro ao parsear JSON: {erro}`

**Causas possiveis:**
- LLM retornou texto nao estruturado
- Formato inesperado na resposta

**Solucao:**
- Verificar logs para ver resposta completa do LLM
- Revisar prompt (pode estar confuso)
- Tentar novamente (retry automatico ja configurado)

---

## Comparacao: Pipeline v3 (Grupos) vs Discovery Pipeline (Conversas)

### Pipeline v3 (Grupos)

**Proposito:** Extrair vagas atomicas de mensagens de grupos de WhatsApp.

**Modulo:** `app/services/grupos/extrator_v2/extrator_llm.py`

**LLM:** Claude Haiku (unificado, classificacao + extracao em uma chamada)

**Output:** Lista de `VagaAtomica` (hospital, data, periodo, valor, especialidade, contato)

**Uso:** Processar mensagens de staffing em grupos (ex: "Hospital ABC, 26/01 Manha, R$ 1.700")

**Feature flag:** `PIPELINE_V3_ENABLED=true`

### Discovery Intelligence Pipeline (Conversas)

**Proposito:** Extrair insights de conversas individuais (Julia ↔ Medico).

**Modulo:** `app/services/extraction/`

**LLM:** Claude Haiku (extracao de interesse, objecoes, preferencias, proximo passo)

**Output:** `ExtractionResult` (interesse, score, objecoes, preferencias, restricoes, proximo_passo)

**Uso:** Enriquecer conversas 1:1, identificar oportunidades, gerar relatorios de campanhas

**Feature flag:** Nenhum (sempre ativo em producao)

### Principais Diferencas

| Aspecto | Pipeline v3 (Grupos) | Discovery Pipeline (Conversas) |
|---------|----------------------|--------------------------------|
| Input | Mensagem de grupo (vagas) | Turno de conversa (medico + Julia) |
| Output | VagaAtomica[] | ExtractionResult (interesse, objecoes, etc) |
| Objetivo | Extrair vagas estruturadas | Entender interesse e comportamento |
| Persistencia | `grupos_mensagens`, `vagas` | `conversation_insights`, `doctor_context` |
| Cache | 24h (Redis) | 24h (Redis) |
| Custo | ~$0.0001-0.0003 por msg | ~$0.0001 por turno |
| Backfill | Nao | Sim (`backfill_extraction.py`) |
| Relatorios | Nao | Sim (relatorios de campanha com LLM) |

Ambos usam Claude Haiku para custo minimo e compartilham infraestrutura de cache.

---

## Proximos Passos e Melhorias Futuras

### Curto Prazo

- [ ] Adicionar job agendado para backfill incremental (processar ultimas 24h diariamente)
- [ ] Criar dashboard de insights no frontend (metricas, oportunidades)
- [ ] Adicionar notificacoes Slack para oportunidades criticas (escalar_humano)
- [ ] Implementar refresh automatico da view `campaign_insights` (cron diario)

### Medio Prazo

- [ ] Adicionar deteccao de "momento certo" para enviar vagas (timing otimo)
- [ ] Criar pipeline de follow-up automatico baseado em `proximo_passo`
- [ ] Adicionar analise de sentimento mais granular (alem de interesse)
- [ ] Implementar A/B testing de prompts de extracao

### Longo Prazo

- [ ] Usar insights para treinar modelo de scoring de leads
- [ ] Adicionar predicao de conversao (probabilidade de fechar vaga)
- [ ] Integrar insights com sistema de recomendacao de vagas
- [ ] Criar feedback loop: resultados reais → refinamento de prompt

---

## Referências

### Documentacao Interna

- `docs/julia/prompts.md`: Sistema de prompts dinamicos
- `docs/arquitetura/banco-de-dados.md`: Schema completo do banco
- `app/CONVENTIONS.md`: Convencoes de codigo

### Sprints Relacionadas

- Sprint 52: Pipeline v3 - Extracao LLM unificada (grupos)
- Sprint 53: Discovery Intelligence Pipeline (conversas)
- Sprint 54: Insights Dashboard & Relatorio Julia

### Codigo Fonte

- `app/services/extraction/`: Modulo principal
- `app/services/grupos/extrator_v2/extrator_llm.py`: Pipeline v3 (grupos)
- `app/api/routes/extraction.py`: Endpoints
- `app/workers/backfill_extraction.py`: Worker de backfill

### APIs Externas

- Anthropic Claude API: https://docs.anthropic.com/
- Redis: https://redis.io/docs/

---

Ultima atualizacao: 10 de fevereiro de 2026
