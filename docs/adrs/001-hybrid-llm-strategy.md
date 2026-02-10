# ADR-001: Estrategia Hibrida de LLM (80/20 Haiku/Sonnet)

- Status: Aceita
- Data: Dezembro 2025
- Sprint: Sprint 1-4
- Decisores: Equipe de Engenharia

## Contexto

O Agente Julia precisa processar milhares de conversas por dia via WhatsApp, com duas necessidades conflitantes:

1. **Custo controlado**: LLMs de alta qualidade como Claude Sonnet sao caros ($3/1M input tokens, $15/1M output)
2. **Qualidade de conversacao**: Passar no teste de Turing exige respostas naturais e contextuais

A maioria das conversas sao simples:
- Prospecção inicial ("Oi, tem vaga?")
- Follow-ups de rotina ("Sim, tenho interesse")
- Confirmacoes simples ("Ok, obrigado")

Mas algumas conversas exigem mais sofisticacao:
- Negociacao de valores
- Objecoes complexas
- Situacoes emocionalmente sensíveis

**Problema**: Como otimizar custo sem sacrificar qualidade onde importa?

## Decisao

Implementar estrategia hibrida de LLM:

1. **Claude 3.5 Haiku** para 80% das chamadas (conversas simples)
   - Custo: $0.25/1M input tokens, $1.25/1M output
   - Latencia: ~500ms
   - Use case: prospeccao, follow-ups, confirmacoes

2. **Claude 4 Sonnet** para 20% das chamadas (conversas complexas)
   - Custo: $3/1M input tokens, $15/1M output
   - Latencia: ~2s
   - Use case: negociacao, objecoes, handoff prevention

**Criterios de roteamento para Sonnet:**
- Presenca de objecoes detectadas (10 tipos)
- Sentimento negativo no historico
- Conversas com > 5 turnos
- Negociacao de valores/condicoes
- Pedido explicito de informacoes complexas

**Implementacao:** Logica no `app/services/claude.py` com fallback automatico.

## Alternativas Consideradas

### 1. Usar apenas Haiku
- **Pros**: Custo minimo ($0.25/1M), latencia baixa
- **Cons**: Qualidade inferior em conversas complexas, risco de falhar teste de Turing
- **Rejeicao**: Qualidade nao e negociavel para o core value prop

### 2. Usar apenas Sonnet
- **Pros**: Maxima qualidade em todas as conversas
- **Cons**: Custo 12x maior ($3/1M vs $0.25/1M), latencia 4x maior
- **Rejeicao**: Custo insustentavel para operacao em escala

### 3. Usar GPT-4o/GPT-4o-mini (OpenAI)
- **Pros**: Preco competitivo, infraestrutura robusta
- **Cons**: Menor qualidade em portugues brasileiro, menos control sobre output
- **Rejeicao**: Testes preliminares mostraram Claude superior para persona Julia

### 4. Fine-tune de modelo menor (Llama 3, Mistral)
- **Pros**: Custo operacional muito baixo apos fine-tune
- **Cons**: Custo inicial alto, manutencao complexa, risco de qualidade
- **Rejeicao**: Defer para futuro, quando volume justificar investimento

## Consequencias

### Positivas

1. **Reducao de 73% no custo de LLM**
   - Baseline (100% Sonnet): $3/1M input
   - Hybrid (80% Haiku + 20% Sonnet): $0.80/1M input
   - Savings: (3 - 0.8) / 3 = 73%

2. **Latencia media 60% menor**
   - Haiku: 500ms vs Sonnet: 2s
   - Media ponderada: 0.8 * 500ms + 0.2 * 2000ms = 800ms (vs 2s full Sonnet)

3. **Qualidade preservada onde importa**
   - Conversas criticas usam Sonnet
   - Prospeccao simples usa Haiku (suficiente)

4. **Flexibilidade para ajustar ratio**
   - Configuracao via feature flag
   - Pode aumentar % Sonnet se necessario

### Negativas

1. **Complexidade de roteamento**
   - Necessita logica de deteccao de complexidade
   - Risco de classificacao errada (conversa complexa roteada para Haiku)

2. **Inconsistencia potencial**
   - Mesmo medico pode receber qualidade variavel
   - Mitigacao: contexto compartilhado, prompts alinhados

3. **Mais dificil de debugar**
   - Precisa rastrear qual modelo foi usado em cada turno
   - Mitigacao: logging estruturado com `modelo_llm` field

### Mitigacoes

1. **Deteccao de complexidade robusta**
   - Pre-processor pipeline detecta objecoes, sentimento, turno count
   - Fallback: se Haiku responde "nao sei", re-processar com Sonnet

2. **Prompts alinhados**
   - Persona Julia identica em ambos os modelos
   - System prompt compartilhado

3. **Monitoring ativo**
   - Dashboard rastreia % de uso Haiku vs Sonnet
   - Alerta se ratio desvia muito de 80/20
   - Tracking de custo real vs target

4. **Escape hatch**
   - Feature flag para forcar 100% Sonnet se qualidade cair
   - A/B testing para validar ratio ideal

## Metricas de Sucesso

1. **Custo mensal de LLM < $500** (baseline: $1.800 com full Sonnet)
2. **Taxa de deteccao como bot < 1%** (qualidade percebida)
3. **Taxa de handoff por qualidade < 2%** (falhas de conversacao)
4. **Latencia p95 < 3s** (experiencia do usuario)

## Referencias

- Codigo: `app/services/claude.py` (logica de roteamento)
- Config: `app/core/config.py` (feature flags)
- Metricas: `app/core/metrics.py` (tracking de uso)
- Docs: `docs/julia/prompts/` (system prompts compartilhados)
- Planilha de custos: `planning/sprint-4/custo-llm-analysis.xlsx` (se existir)

## Historico de Mudancas

- **2025-12**: Decisao inicial (80/20 ratio)
- **2026-01**: Sprint 10 - Adicao de fallback automatico
- **2026-02**: Atual - Ratio mantido, metricas dentro do target
