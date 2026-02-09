# Sprint 53 - Discovery Intelligence Pipeline

**Início:** 09/02/2026
**Duração estimada:** 1.5-2 semanas
**Dependências:** Sprint 52 (Pipeline v3) completa
**Status:** ✅ Completa

---

## Progresso

| Epic | Status | Descrição |
|------|--------|-----------|
| Epic 1: Modelo de Dados | ✅ FEITO | Tabela `conversation_insights` criada |
| Epic 2: Serviço de Extração | ✅ FEITO | `app/services/extraction/` com prompt LLM |
| Epic 3: Post-Processor | ✅ FEITO | `ExtractionProcessor` priority 35 |
| Epic 4: Persistência RAG | ✅ FEITO | Integração com `doctor_context` |
| Epic 5: Auto-Correção Dados | ✅ FEITO | Atualização automática de clientes |
| Epic 6: Backfill Histórico | ✅ FEITO | `app/workers/backfill_extraction.py` |
| Epic 7: Campaign Insights View | ✅ FEITO | View materializada `campaign_insights` |
| Epic 8: Observabilidade | ✅ FEITO | Endpoint `/extraction/stats` |
| Epic 9: Testes | ✅ FEITO | 30 testes unitários passando |
| Epic 10: API/Endpoints | ✅ FEITO | `app/api/routes/extraction.py` |

---

## Objetivo Estratégico

Criar um **pipeline robusto de extração automática de dados** que captura informações estruturadas de TODA conversa, transformando campanhas de discovery em inteligência acionável.

### Por que agora?

Campanhas de discovery estão rodando, mas **ZERO dados estão sendo extraídos e salvos**:
- Últimos 30 dias: apenas 13 memórias salvas de ~500 conversas
- Tool `salvar_memoria` existe mas Julia raramente usa
- Dados valiosos perdidos a cada conversa

**Sem isso, campanhas de discovery são desperdício de recursos.**

### Benefícios

| Antes | Depois |
|-------|--------|
| ~0.4 memórias/dia | ~50-100 memórias/dia |
| 0% dados de campanha extraídos | 100% cobertura |
| Correções de cadastro manuais | Auto-correção (confiança > 0.7) |
| Interesse não rastreado | Classificação por turno |
| Objeções perdidas | Catalogadas e agregadas |

---

## Motivação (Problema Real: Campanha 19)

### Análise Concreta

Campanha 19 "Discovery Cardiologia" teve 50 envios e 16 respostas (32% response rate).

**Dados extraídos manualmente (não salvos):**

| Médico | Interesse | Dado Revelado | Status DB |
|--------|-----------|---------------|-----------|
| Sergio | ✅ Positivo | "Trabalho no RJ" | Região não atualizada |
| Enrico | ✅ Positivo | Mencionou Reumatologia | Cadastrado como Cirurgia Geral |
| Debora | ✅ Positivo | Disponível fins de semana | Não registrado |
| Cristiano | ❌ Negativo | "Já trabalho com empresas" | Objeção não catalogada |
| Danusa | ⚪ Neutro | "Talvez no futuro" | Follow-up não agendado |
| Nadia | 🤖 Bot | Sistema Gennex | Marcado manualmente |

**Problema:** Essas informações foram perdidas. Próxima campanha não terá esse contexto.

---

## Arquitetura

### Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION TURN                                │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Médico envia mensagem                                            │
│ 2. Pipeline processa (pre-processors → LLM → post-processors)       │
│ 3. Julia responde                                                    │
│ 4. SendMessageProcessor envia (priority 20)                         │
│ 5. SaveInteractionProcessor salva (priority 30)                     │
│ 6. ★ ExtractionProcessor extrai dados (priority 35) ★               │
│ 7. MetricsProcessor finaliza (priority 40)                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EXTRACTION SERVICE                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Input:                                                               │
│   - mensagem_medico: str                                            │
│   - resposta_julia: str                                             │
│   - contexto: {nome, especialidade, campanha, histórico}            │
│                                                                      │
│ Output (JSON estruturado):                                          │
│   - interesse: positivo | negativo | neutro | incerto               │
│   - interesse_score: 0.0-1.0                                        │
│   - especialidade_mencionada: str | null                            │
│   - regiao_mencionada: str | null                                   │
│   - disponibilidade: str | null                                     │
│   - objecao: {tipo, descricao, severidade} | null                   │
│   - preferencias: list[str]                                         │
│   - restricoes: list[str]                                           │
│   - dados_corrigidos: {campo: valor_novo}                           │
│   - proximo_passo: enum                                             │
│   - confianca: 0.0-1.0                                              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA PERSISTENCE                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐                 │
│  │ conversation_insights│  │   doctor_context     │                 │
│  │ (nova tabela)        │  │   (existente - RAG)  │                 │
│  ├──────────────────────┤  ├──────────────────────┤                 │
│  │ - interesse          │  │ - preferencias       │                 │
│  │ - objecoes           │  │ - restricoes         │                 │
│  │ - proximo_passo      │  │ - info_pessoal       │                 │
│  │ - dados_brutos       │  │ - embeddings         │                 │
│  └──────────────────────┘  └──────────────────────┘                 │
│              │                        │                              │
│              │                        │                              │
│  ┌───────────┴───────────┐  ┌────────┴────────────┐                 │
│  │  campaign_insights    │  │      clientes       │                 │
│  │  (view materializada) │  │  (atualiza dados)   │                 │
│  ├───────────────────────┤  ├─────────────────────┤                 │
│  │ - taxa_interesse      │  │ - especialidade     │                 │
│  │ - objecoes_comuns     │  │ - regiao            │                 │
│  │ - medicos_prontos     │  │ - preferencias_json │                 │
│  └───────────────────────┘  └─────────────────────┘                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Integração com Pipeline Existente

```python
# app/pipeline/post_processors.py - ATUAL
class ValidateOutputProcessor:   priority = 5
class TimingProcessor:           priority = 10
class SendMessageProcessor:      priority = 20
class ChatwootResponseProcessor: priority = 25
class SaveInteractionProcessor:  priority = 30
# ★ ExtractionProcessor:         priority = 35 ★  <- NOVO
class MetricsProcessor:          priority = 40
```

---

## Épicos

### Epic 1: Modelo de Dados (P0 - Crítico) ✅ CONCLUÍDO

**Objetivo:** Criar estrutura de dados para armazenar extrações.

**Migração aplicada:** `create_conversation_insights`

**Schema criado:**

```sql
CREATE TABLE conversation_insights (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    interaction_id BIGINT REFERENCES interacoes(id),
    campaign_id BIGINT REFERENCES campanhas(id),
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    interesse TEXT CHECK (interesse IN ('positivo', 'negativo', 'neutro', 'incerto')),
    interesse_score DECIMAL(3,2),
    especialidade_mencionada TEXT,
    regiao_mencionada TEXT,
    disponibilidade_mencionada TEXT,
    objecao_tipo TEXT,
    objecao_descricao TEXT,
    objecao_severidade TEXT,
    preferencias JSONB DEFAULT '[]',
    restricoes JSONB DEFAULT '[]',
    dados_corrigidos JSONB DEFAULT '{}',
    proximo_passo TEXT,
    modelo_extracao TEXT DEFAULT 'haiku',
    confianca DECIMAL(3,2),
    tokens_input INTEGER,
    tokens_output INTEGER,
    latencia_ms INTEGER,
    raw_extraction JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Índices criados:**
- `idx_insights_conversation`
- `idx_insights_campaign`
- `idx_insights_cliente`
- `idx_insights_interesse`
- `idx_insights_created`
- `idx_insights_proximo_passo`
- `idx_insights_objecao`
- `idx_insights_campaign_interesse`

---

### Epic 2: Serviço de Extração LLM (P0 - Crítico)

**Objetivo:** Criar serviço que usa Claude Haiku para extrair dados estruturados.

**Arquivos:**
- `app/services/extraction/extractor.py` (NOVO)
- `app/services/extraction/schemas.py` (NOVO)
- `app/services/extraction/prompts.py` (NOVO)
- `app/services/extraction/__init__.py` (NOVO)

**Tarefas:**
- [ ] 2.1 Criar estrutura de diretório `app/services/extraction/`
- [ ] 2.2 Definir dataclass `ExtractionResult` com todos os campos
- [ ] 2.3 Definir dataclass `ExtractionContext` para input
- [ ] 2.4 Criar prompt otimizado para extração
- [ ] 2.5 Implementar função `extrair_dados_conversa()`
- [ ] 2.6 Adicionar parsing robusto de JSON (com fallback)
- [ ] 2.7 Adicionar retry com exponential backoff
- [ ] 2.8 Adicionar cache Redis (24h TTL por hash da mensagem)
- [ ] 2.9 Adicionar métricas (tokens, latência, erros)
- [ ] 2.10 Tratar edge cases (mensagens muito curtas, emojis only, etc.)

---

### Epic 3: Post-Processor de Extração (P0 - Crítico)

**Objetivo:** Integrar extração no pipeline de mensagens.

**Arquivos:**
- `app/pipeline/processors/extraction.py` (NOVO)

**Tarefas:**
- [ ] 3.1 Criar `ExtractionProcessor` com priority 35
- [ ] 3.2 Implementar `should_run()` - só roda se há mensagem e resposta
- [ ] 3.3 Implementar `process()` - extrai e persiste
- [ ] 3.4 Tornar fault-tolerant (erros não bloqueiam pipeline)
- [ ] 3.5 Adicionar feature flag `EXTRACTION_ENABLED`
- [ ] 3.6 Executar em background (não bloqueia resposta)
- [ ] 3.7 Registrar no pipeline
- [ ] 3.8 Adicionar logs estruturados

---

### Epic 4: Persistência RAG (P1)

**Objetivo:** Salvar memórias extraídas no `doctor_context` para RAG.

**Arquivos:**
- `app/services/extraction/persistence.py` (NOVO)

**Tarefas:**
- [ ] 4.1 Implementar `salvar_insight()` - salva em conversation_insights
- [ ] 4.2 Implementar `salvar_memorias_extraidas()` - cria entradas em doctor_context
- [ ] 4.3 Gerar embeddings para preferências e restrições
- [ ] 4.4 Categorizar memórias corretamente (preferencia, restricao, info_pessoal)
- [ ] 4.5 Evitar duplicatas (verificar se memória similar já existe)
- [ ] 4.6 Adicionar source "extraction" para rastreamento

---

### Epic 5: Auto-Correção de Dados (P1)

**Objetivo:** Atualizar dados de clientes automaticamente quando confiança é alta.

**Campos Permitidos:**

| Campo | Auto-Update | Justificativa |
|-------|-------------|---------------|
| especialidade | ✅ Sim | Médico sabe sua especialidade |
| cidade | ✅ Sim | Médico sabe onde atua |
| estado | ✅ Sim | Médico sabe onde atua |
| regiao | ✅ Sim | Médico sabe onde atua |
| telefone | ❌ Não | Risco de dados incorretos |
| email | ❌ Não | Risco de dados incorretos |
| crm | ❌ Não | Validação manual necessária |
| nome | ❌ Não | Risco de confusão |

---

### Epic 6: Backfill Histórico (P2)

**Objetivo:** Processar conversas dos últimos 30 dias para popular insights.

**Arquivos:**
- `app/workers/backfill_extraction.py` (NOVO)
- `app/api/routes/jobs.py` (adicionar endpoint)

---

### Epic 7: Campaign Insights View (P2)

**Objetivo:** Criar view materializada para analytics de campanha.

---

### Epic 8: Observabilidade (P2)

**Objetivo:** Métricas e alertas para o pipeline de extração.

---

### Epic 9: Testes (P1)

**Objetivo:** Cobertura de testes para todo o sistema de extração.

---

### Epic 10: API/Endpoints (P2)

**Objetivo:** Endpoints para acessar dados de extração.

---

## Estimativas

| Epic | Complexidade | Tempo Estimado |
|------|--------------|----------------|
| Epic 1: Modelo de Dados | Baixa | 1 hora ✅ |
| Epic 2: Serviço de Extração | Alta | 3 horas |
| Epic 3: Post-Processor | Média | 2 horas |
| Epic 4: Persistência RAG | Média | 2 horas |
| Epic 5: Auto-Correção | Baixa | 1 hora |
| Epic 6: Backfill Histórico | Média | 2 horas |
| Epic 7: Campaign Insights View | Baixa | 1 hora |
| Epic 8: Observabilidade | Média | 1.5 horas |
| Epic 9: Testes | Média | 3 horas |
| Epic 10: API/Endpoints | Média | 2 horas |
| **Total** | | **18.5 horas** |

---

## Custos Estimados

| Operação | Custo/Unidade | Volume Diário | Custo/Dia |
|----------|---------------|---------------|-----------|
| Extração (Haiku) | ~$0.0001 | ~500 msgs | ~$0.05 |
| Embeddings (Voyage) | ~$0.00002 | ~100 memórias | ~$0.002 |
| **Total** | | | **~$0.05/dia** |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| LLM retorna JSON inválido | Média | Médio | Parser com fallback + retry |
| Latência adicional no pipeline | Baixa | Médio | Execução em background |
| Custo de tokens escala | Baixa | Baixo | Haiku é $0.25/1M tokens |
| Extração falha silenciosamente | Média | Baixo | Logs + métricas + alertas |
| Dados incorretos atualizados | Baixa | Alto | Threshold de confiança 0.7 |

---

## Ordem de Implementação

### Fase 1: Fundação (Dia 1)
1. ✅ **Epic 1**: Criar tabela `conversation_insights`
2. **Epic 2**: Implementar serviço de extração

### Fase 2: Integração (Dia 2)
3. **Epic 3**: Criar ExtractionProcessor
4. **Epic 4**: Implementar persistência RAG

### Fase 3: Automação (Dia 3)
5. **Epic 5**: Auto-correção de dados
6. **Epic 7**: Campaign insights view

### Fase 4: Histórico (Dia 4)
7. **Epic 6**: Backfill de últimos 30 dias

### Fase 5: Qualidade (Dia 5)
8. **Epic 8**: Observabilidade
9. **Epic 9**: Testes
10. **Epic 10**: Endpoints de API

---

## Escopo de Captura

### Todas as Conversas, Não Apenas Discovery

| Tipo de Conversa | Captura | Justificativa |
|------------------|---------|---------------|
| Discovery | ✅ Sim | Foco inicial, dados de prospecção |
| Oferta de Vaga | ✅ Sim | Interesse, objeções, preferências de vaga |
| Follow-up | ✅ Sim | Mudança de interesse, novas restrições |
| Reativação | ✅ Sim | Razões de inatividade, novo interesse |
| Inbound (médico inicia) | ✅ Sim | Demanda espontânea, preferências |
| Confirmação de Plantão | ✅ Sim | Feedback pós-plantão |
| Handoff para Humano | ✅ Sim | Situações complexas, objeções graves |

---

## Definition of Done (Sprint)

### Obrigatório (P0)
- [x] Tabela `conversation_insights` criada e funcionando
- [x] Serviço de extração retornando dados válidos
- [x] ExtractionProcessor integrado no pipeline
- [x] Persistência em doctor_context funcionando
- [x] Feature flag `EXTRACTION_ENABLED` implementada
- [x] Testes unitários passando (30 testes)

### Desejável (P1)
- [x] Auto-correção de dados com threshold (0.7)
- [x] Backfill worker implementado
- [x] View `campaign_insights` criada

### Futuro (P2)
- [x] Endpoints de API documentados
- [x] Endpoint `/extraction/stats` para métricas
- [ ] Alertas de cobertura (a implementar)

---

## Métricas de Sucesso

### Antes (atual)
- Memórias salvas/dia: ~0.4
- Dados de campanha extraídos: 0%
- Correções de cadastro: manual
- Objeções catalogadas: 0

### Depois (meta)
- Memórias salvas/dia: ~50-100
- Dados de campanha extraídos: 100%
- Correções de cadastro: automáticas (confiança > 0.7)
- Objeções catalogadas: 100%
