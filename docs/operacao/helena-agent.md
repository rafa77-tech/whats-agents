# Helena - Agente de Analytics

**Sprint:** 47
**Módulo:** Agente de IA para Slack
**Modelo:** Claude 3.5 Haiku

## Visão Geral

Helena é um agente de IA especializado em analytics e operações, que funciona exclusivamente via Slack. Diferente da Julia (que opera no WhatsApp), Helena fornece insights de métricas, status do sistema, e permite consultas SQL dinâmicas para análise de dados.

**Características principais:**

- Respostas em linguagem natural
- 5 tools pré-definidas para métricas e sistema
- SQL dinâmico seguro (apenas SELECT, LIMIT <= 100)
- Sessão com contexto (TTL 30 minutos)
- Retry automático para respostas incompletas

## Diferenças: Helena vs Julia

| Aspecto | Helena | Julia |
|---------|--------|-------|
| Canal | Apenas Slack | Apenas WhatsApp |
| Propósito | Analytics e operações | Prospecção e vendas |
| Público | Time interno (Revoluna) | Médicos (externos) |
| Tools | 5 fixas + SQL dinâmico | 8+ tools (vagas, memória, etc) |
| Persona | Analista técnica | Escalista casual |
| Modelo | Haiku | Haiku + Sonnet híbrido |

## Como Usar

### 1. Iniciar Conversa

Mencione `@Helena` em qualquer canal do Slack onde o bot está presente:

```
@Helena Como foram as conversas hoje?
```

Helena responde em thread, mantendo contexto da conversa.

### 2. Perguntas Comuns

**Métricas de Conversas:**

```
@Helena Quantas conversas tivemos essa semana?
@Helena Taxa de conversão hoje
@Helena Resumo do mês
```

**Status do Sistema:**

```
@Helena Como estão os chips?
@Helena Tem algo errado no sistema?
@Helena Quantos handoffs pendentes?
```

**Campanhas:**

```
@Helena Performance das campanhas ativas
@Helena Como foi a campanha "Oferta Cardio SP"?
```

**Consultas Customizadas:**

```
@Helena Quantos médicos cardiologistas temos cadastrados?
@Helena Top 5 hospitais com mais vagas abertas
@Helena Qual especialidade tem maior taxa de conversão?
```

### 3. Contexto de Sessão

Helena mantém contexto por 30 minutos. Você pode fazer perguntas sequenciais:

```
User: @Helena Como foi hoje?
Helena: Hoje tivemos 45 conversas, 18 responderam...

User: E ontem?
Helena: Ontem foram 52 conversas, 21 responderam...

User: Qual teve melhor taxa de resposta?
Helena: Hoje teve melhor: 40% vs 40.4% ontem... [usa contexto das perguntas anteriores]
```

## Tools Pré-Definidas

### 1. metricas_periodo

**Quando usar:**
- "Como foi hoje?"
- "Métricas da semana"
- "Resumo do mês"

**Parâmetros:**
- `periodo`: `hoje` | `ontem` | `semana` | `mes`

**Retorna:**
```json
{
  "success": true,
  "periodo": "hoje",
  "data_inicio": "2026-02-10",
  "data_fim": "2026-02-11",
  "metricas": {
    "total_conversas": 45,
    "com_resposta": 18,
    "conversoes": 3,
    "taxa_resposta": 40.0,
    "taxa_conversao": 16.7
  }
}
```

### 2. metricas_conversao

**Quando usar:**
- "Como está o funil?"
- "Taxa de conversão detalhada"
- "Onde estamos perdendo?"

**Parâmetros:**
- `dias`: Número de dias (default: 7)

**Retorna:**
```json
{
  "success": true,
  "dias": 7,
  "funil": {
    "abordados": {"quantidade": 320, "taxa": 100},
    "responderam": {"quantidade": 128, "taxa": 40.0},
    "converteram": {"quantidade": 21, "taxa": 16.4},
    "perdidos": {"quantidade": 85, "taxa": 26.6}
  }
}
```

### 3. metricas_campanhas

**Quando usar:**
- "Como estão as campanhas?"
- "Performance da campanha X"
- "Campanhas ativas"

**Parâmetros:**
- `status`: `todas` | `ativa` | `concluida` | `agendada` (default: `todas`)
- `limite`: Máximo de campanhas (default: 10, max: 50)

**Retorna:**
```json
{
  "success": true,
  "filtro_status": "ativa",
  "campanhas": [
    {
      "id": "uuid",
      "nome_template": "Oferta Cardio SP",
      "tipo_campanha": "oferta_direta",
      "status": "ativa",
      "total_destinatarios": 150,
      "enviados": 120,
      "entregues": 115,
      "respondidos": 48,
      "taxa_entrega": 95.8,
      "taxa_resposta": 41.7,
      "created_at": "2026-02-08T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 4. status_sistema

**Quando usar:**
- "Como está o sistema?"
- "Status dos chips"
- "Tem algo errado?"

**Parâmetros:** Nenhum

**Retorna:**
```json
{
  "success": true,
  "timestamp": "2026-02-10T15:30:00Z",
  "chips": [
    {"status": "active", "quantidade": 8, "trust_medio": 85.5},
    {"status": "warming", "quantidade": 2, "trust_medio": 60.0}
  ],
  "fila_24h": [
    {"status": "enviada", "quantidade": 450},
    {"status": "pendente", "quantidade": 12}
  ],
  "handoffs_pendentes": 3
}
```

### 5. listar_handoffs

**Quando usar:**
- "Tem handoff pendente?"
- "Listar escalações"
- "Quem precisa de atendimento?"

**Parâmetros:**
- `status`: `pendente` | `em_atendimento` | `resolvido` | `todos` (default: `pendente`)
- `limite`: Máximo de resultados (default: 10, max: 50)

**Retorna:**
```json
{
  "success": true,
  "filtro_status": "pendente",
  "handoffs": [
    {
      "id": "uuid",
      "motivo": "Reclamação sobre vaga cancelada",
      "status": "pendente",
      "created_at": "2026-02-10T14:20:00Z",
      "primeiro_nome": "Carlos",
      "sobrenome": "Silva",
      "telefone": "+5511999887766",
      "especialidade": "Cardiologia"
    }
  ],
  "total": 1
}
```

## SQL Dinâmico (consulta_sql)

Helena pode executar queries SQL customizadas com guardrails de segurança.

### Regras Obrigatórias

1. Apenas `SELECT` (nunca INSERT, UPDATE, DELETE, DROP, etc)
2. SEMPRE usar `LIMIT` (máximo 100 rows)
3. Preferir agregações (COUNT, SUM, AVG) a listagens completas
4. Timeout de 10 segundos

### Schema Disponível

**Principais tabelas:**

- `clientes`: Médicos cadastrados
- `especialidades`: Especialidades médicas
- `conversations`: Conversas com médicos
- `interacoes`: Mensagens enviadas/recebidas
- `campanhas`: Campanhas de prospecção
- `fila_mensagens`: Fila de envio
- `vagas`: Vagas de plantão
- `hospitais`: Hospitais parceiros
- `handoffs`: Escalações para humano
- `julia_chips`: Chips WhatsApp

**Schema completo na tool description** (app/tools/helena/sql.py linhas 53-63)

### Validação de Segurança

**Bloqueios:**

- Palavras bloqueadas: INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, COPY, EXECUTE
- Tabelas bloqueadas: pg_shadow, pg_authid, pg_roles, information_schema.columns
- LIMIT obrigatório (max 100)
- Queries começando com não-SELECT são rejeitadas

**Implementação:** `validar_query()` em app/tools/helena/sql.py

### Exemplos de Uso

**Pergunta:** "Quantos médicos cardiologistas temos?"

**Query gerada:**
```sql
SELECT COUNT(*) as total
FROM clientes c
JOIN especialidades e ON e.id = c.especialidade_id
WHERE e.nome ILIKE '%cardio%'
LIMIT 1
```

**Pergunta:** "Top 5 hospitais com mais vagas abertas"

**Query gerada:**
```sql
SELECT h.nome, COUNT(v.id) as vagas
FROM hospitais h
JOIN vagas v ON v.hospital_id = h.id
WHERE v.status = 'aberta'
GROUP BY h.id, h.nome
ORDER BY vagas DESC
LIMIT 5
```

**Pergunta:** "Mensagens enviadas por campanha hoje"

**Query gerada:**
```sql
SELECT
  metadata->>'campanha_id' as campanha,
  COUNT(*) as mensagens
FROM fila_mensagens
WHERE metadata->>'campanha_id' IS NOT NULL
AND created_at >= CURRENT_DATE
GROUP BY 1
ORDER BY mensagens DESC
LIMIT 20
```

### Quando SQL Dinâmico É Usado

Helena PREFERE tools pré-definidas. SQL dinâmico é usado apenas quando:

1. Pergunta não se encaixa em nenhuma tool existente
2. Requer JOIN complexo ou filtro específico
3. Análise exploratória (ex: "quais cidades têm mais médicos ortopedistas?")

## Sessão e Contexto

### Session Manager

Implementado em `app/services/helena/session.py`.

**Características:**

- TTL: 30 minutos (renovado a cada mensagem)
- Máximo: 20 mensagens no histórico (evita context overflow)
- Armazena contexto customizado (ex: última query executada)
- Tabela: `helena_sessoes`

**Schema da tabela:**

```sql
CREATE TABLE helena_sessoes (
    user_id TEXT,
    channel_id TEXT,
    mensagens JSONB DEFAULT '[]'::jsonb,
    contexto JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, channel_id)
);
```

### Contexto Customizado

Helena salva resultados de tools no contexto para referência futura:

```python
# Após executar tool
self.session.atualizar_contexto(
    f"ultima_{tool_call.name}",
    result
)
```

Permite perguntas como:
```
@Helena Quantas conversas hoje?
[Helena executa metricas_periodo, salva em contexto]

@Helena E quantas foram convertidas?
[Helena usa resultado anterior do contexto]
```

## Retry para Respostas Incompletas

Helena detecta quando LLM responde de forma incompleta e automaticamente faz retry.

### Padrões Detectados

Resposta é considerada incompleta se termina com:
- `:`
- `...`
- "vou verificar"
- "deixa eu ver"
- "um momento"
- "vou buscar"
- "consultando"

### Comportamento

1. LLM responde: "Vou buscar as métricas..."
2. Helena detecta resposta incompleta
3. Adiciona prompt interno: "Use a tool apropriada para buscar os dados e me responda com números concretos."
4. LLM executa tool e responde com dados completos
5. Máximo de 2 retries

**Implementação:** `_resposta_incompleta()` em app/services/helena/agent.py

## Arquitetura Interna

### Fluxo de Processamento

```
1. Slack envia mensagem → Webhook /slack/events
2. Event handler detecta menção @Helena
3. AgenteHelena.processar_mensagem(texto)
4. Session Manager carrega/cria sessão
5. LLM chamado com tools + histórico
6. Loop de tool execution (max 5 iterações):
   - LLM decide qual tool usar
   - Tool executada
   - Resultado adicionado ao histórico
   - LLM analisa resultado e responde
7. Resposta final enviada ao Slack
8. Sessão salva no banco
```

### Configuração de Modelo

```python
# app/services/helena/agent.py
response = self.client.messages.create(
    model=settings.LLM_MODEL,  # claude-3-5-haiku
    max_tokens=2048,
    system=montar_prompt_helena(data_hora),
    tools=self._get_tools(),
    messages=self.session.mensagens
)
```

**Custo:** ~$0.25 por 1M tokens de input (Haiku é 8x mais barato que Sonnet)

### Limites de Segurança

- Max tool iterations: 5 (evita loops infinitos)
- Max retries incompleto: 2
- Max mensagens na sessão: 20
- SQL LIMIT máximo: 100
- SQL timeout: 10 segundos

## Troubleshooting

### Problema: Helena não responde

**Diagnóstico:**

1. Verificar se foi mencionada corretamente:
   ```
   @Helena [pergunta]  ✅
   Helena [pergunta]   ❌ (sem @)
   ```

2. Checar logs:
   ```bash
   railway logs | grep "Helena processando"
   ```

3. Verificar sessão no banco:
   ```sql
   SELECT * FROM helena_sessoes
   WHERE user_id = 'U123456'
   ORDER BY updated_at DESC
   LIMIT 1;
   ```

**Solução:**

- Se não há logs: problema no webhook Slack ou event handler
- Se erro na sessão: deletar sessão corrompida
  ```sql
  DELETE FROM helena_sessoes WHERE user_id = 'U123456';
  ```

### Problema: Resposta genérica sem dados

**Sintoma:**

```
User: @Helena Quantas conversas hoje?
Helena: Temos algumas conversas hoje, deixa eu verificar os detalhes...
```

**Causa:** LLM não executou tool, deu resposta genérica.

**Solução:**

1. Sistema de retry deve detectar isso automaticamente
2. Se retry falhou, reformular pergunta:
   ```
   @Helena Use a tool metricas_periodo para me dar o total de conversas hoje
   ```

3. Verificar se tool está registrada:
   ```python
   # app/tools/helena/__init__.py
   from .metricas import TOOL_METRICAS_PERIODO
   HELENA_TOOLS = [TOOL_METRICAS_PERIODO, ...]
   ```

### Problema: Erro "Operação DELETE não é permitida"

**Causa:** LLM tentou gerar query SQL com operação bloqueada.

**Exemplo:**
```
User: @Helena Deletar médicos sem CRM
Helena: Erro: Operação 'DELETE' não é permitida
```

**Solução:**

1. Reformular pergunta para SELECT:
   ```
   @Helena Quantos médicos não têm CRM cadastrado?
   ```

2. Sistema já valida automaticamente, mas LLM às vezes tenta operações perigosas

### Problema: Query SQL com timeout

**Sintoma:**

```
Helena: Query excedeu o tempo limite de 10 segundos. Tente uma query mais simples.
```

**Causa:** Query muito complexa ou tabela muito grande sem índices.

**Solução:**

1. Simplificar query:
   - Remover JOINs desnecessários
   - Adicionar filtros WHERE (ex: datas recentes)
   - Usar agregações ao invés de SELECT *

2. Verificar índices na tabela:
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'conversations';
   ```

3. Exemplo ruim vs bom:
   ```sql
   -- Ruim (sem filtro, pode ser lento)
   SELECT * FROM interacoes LIMIT 100;

   -- Bom (filtra por data recente)
   SELECT * FROM interacoes
   WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
   LIMIT 100;
   ```

### Problema: Contexto perdido entre mensagens

**Sintoma:**

```
User: @Helena Métricas de hoje
Helena: [responde]

User: E de ontem?
Helena: Desculpa, não entendi. Pode ser mais específico?
```

**Causa:** Sessão expirou (30 min) ou foi deletada.

**Diagnóstico:**

```sql
SELECT
  user_id,
  expires_at,
  NOW() - expires_at as tempo_expirado
FROM helena_sessoes
WHERE user_id = 'U123456';
```

**Solução:**

1. Fazer pergunta completa:
   ```
   @Helena Métricas de ontem
   ```

2. Aumentar TTL se necessário:
   ```python
   # app/services/helena/session.py
   SESSION_TTL_MINUTES = 60  # Era 30
   ```

### Problema: Muitas iterações de tools

**Sintoma (logs):**

```
Helena executando tool: metricas_periodo
Helena executando tool: metricas_conversao
Helena executando tool: consulta_sql
Helena executando tool: metricas_periodo
Helena executando tool: consulta_sql
Limite de 5 iterações atingido
```

**Causa:** LLM em loop, executando tools repetidamente sem convergir para resposta.

**Solução:**

1. Sistema já limita a 5 iterações (MAX_TOOL_ITERATIONS)
2. Reformular pergunta de forma mais direta
3. Se recorrente, ajustar prompt do sistema

## Exemplos de Conversas

### Exemplo 1: Métricas Simples

```
User: @Helena Como foi hoje?

Helena: Hoje tivemos 45 conversas:
• 18 médicos responderam (40% de taxa de resposta)
• 3 conversões concluídas (16.7% dos que responderam)

Uma performance sólida! 💪
```

### Exemplo 2: Análise de Funil

```
User: @Helena Onde estamos perdendo mais médicos no funil?

Helena: Analisando os últimos 7 dias:

Funil de conversão:
1. Abordados: 320 médicos (100%)
2. Responderam: 128 (40%)
3. Converteram: 21 (16.4% dos que responderam)
4. Perdidos: 85 (26.6%)

O maior drop está entre abordagem e resposta (60% não respondem).
Isso é esperado para contato frio, mas podemos melhorar:

Sugestões:
• Testar horários diferentes de envio
• A/B test de templates de mensagem inicial
• Segmentar por especialidade (algumas respondem mais)
```

### Exemplo 3: SQL Dinâmico

```
User: @Helena Quais especialidades têm maior taxa de conversão?

Helena: Consultando... [executa SQL]

Top 5 especialidades por taxa de conversão:

1. Anestesiologia: 28.5% (20 de 70)
2. Cardiologia: 22.1% (34 de 154)
3. Ortopedia: 18.9% (17 de 90)
4. Clínica Geral: 15.2% (41 de 270)
5. Pediatria: 12.8% (8 de 62)

Anestesio e Cardio estão acima da média (16.4%).
Vale a pena focar campanhas nessas especialidades! 🎯
```

### Exemplo 4: Status do Sistema

```
User: @Helena Tá tudo ok no sistema?

Helena: Checando... ✅

Chips WhatsApp:
• 8 ativos (trust médio: 85.5)
• 2 em aquecimento (trust médio: 60.0)

Fila de mensagens (últimas 24h):
• 450 enviadas
• 12 pendentes

Handoffs: 3 pendentes de atendimento humano

Tudo funcionando normalmente! Os 3 handoffs precisam de atenção.
```

## Métricas de Performance

| Métrica | Meta | Como Medir |
|---------|------|------------|
| Tempo de resposta | < 5s | Logs: tempo entre "processando" e resposta |
| Taxa de execução de tool | > 80% | Perguntas que acionam tool vs genéricas |
| Queries SQL bloqueadas | < 1% | Logs: "Operação X não é permitida" |
| Timeout de queries | < 5% | Logs: "Query excedeu tempo limite" |

## Próximos Passos

1. **Mais Tools**: Adicionar tools para vagas, médicos, campanhas (CRUD)
2. **Alertas Proativos**: Helena notifica automaticamente quando métricas caem
3. **Sugestões**: LLM sugere ações baseado em patterns (ex: "Taxa de resposta caiu 10%, testar novo template?")
4. **Visualizações**: Gerar gráficos simples (ASCII art ou links para dashboard)
5. **Comandos de Sistema**: Pausar/retomar campanhas, aprovar/rejeitar handoffs via Helena
