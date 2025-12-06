# Análise de Custos - Modelos LLM para Júlia

**Data:** Dezembro 2025
**Objetivo:** Selecionar o melhor modelo para conversação (passar no teste de Turing) com custo sustentável

---

## Resumo Executivo

| Modelo | Input/1M tokens | Output/1M tokens | Qualidade | Recomendação |
|--------|-----------------|------------------|-----------|--------------|
| **Claude 3.5 Haiku** | $0.25 | $1.25 | Boa | **MVP** |
| Claude 4 Sonnet | $3.00 | $15.00 | Excelente | Produção |
| GPT-4o mini | $0.15 | $0.60 | Boa | Alternativa |
| **DeepSeek V3** | $0.28 | $0.42 | Boa | **Mais barato** |
| Claude Opus 4 | $15.00 | $75.00 | Premium | Overkill |

---

## Análise Detalhada

### 1. Claude 3.5 Haiku (Anthropic)

**Preço:** $0.25/1M input, $1.25/1M output

**Prós:**
- Melhor relação custo-benefício da família Claude
- Excelente para conversação natural em português
- Latência baixa (~500ms)
- Suporte nativo a system prompts complexos

**Contras:**
- Menos capaz em raciocínio complexo que Sonnet/Opus
- Pode precisar de prompts mais detalhados

**Caso de uso:** Conversas simples, follow-ups, respostas rápidas

---

### 2. Claude 4 Sonnet (Anthropic)

**Preço:** $3.00/1M input, $15.00/1M output

**Prós:**
- Qualidade excepcional em conversação
- Entende nuances culturais brasileiras
- Excelente em manter persona consistente
- Context window de até 1M tokens

**Contras:**
- 12x mais caro que Haiku no input
- Pode ser overkill para mensagens simples

**Caso de uso:** Conversas complexas, negociação, situações delicadas

---

### 3. GPT-4o mini (OpenAI)

**Preço:** $0.15/1M input, $0.60/1M output

**Prós:**
- Mais barato que Claude Haiku
- Boa qualidade geral
- Suporte a vision (para documentos)

**Contras:**
- Menos natural em português brasileiro que Claude
- System prompts menos flexíveis
- Tendência a respostas mais "robóticas"

**Caso de uso:** Backup, processamento de documentos

---

### 4. DeepSeek V3 (DeepSeek)

**Preço:** $0.28/1M input, $0.42/1M output (cache hit: $0.028!)

**Prós:**
- **Extremamente barato** (até 95% menos que GPT-4)
- Cache agressivo reduz custos ainda mais
- Context window de 128K

**Contras:**
- Empresa chinesa (considerações de dados/LGPD)
- Menos testado em português brasileiro
- Documentação mais limitada
- Pode ter instabilidade de serviço

**Caso de uso:** Testes, desenvolvimento, workloads de baixo risco

---

## Estimativa de Custos Mensais

### Cenário: Júlia em operação (Fase 1)

**Premissas:**
- 100 mensagens/dia enviadas
- Média de 500 tokens input por mensagem (contexto + histórico)
- Média de 100 tokens output por mensagem
- 22 dias úteis/mês

**Cálculo mensal:**
- Input: 100 × 500 × 22 = 1.1M tokens/mês
- Output: 100 × 100 × 22 = 220K tokens/mês

| Modelo | Custo Input | Custo Output | **Total/mês** |
|--------|-------------|--------------|---------------|
| Claude Haiku | $0.28 | $0.28 | **$0.56** |
| Claude Sonnet | $3.30 | $3.30 | **$6.60** |
| GPT-4o mini | $0.17 | $0.13 | **$0.30** |
| DeepSeek V3 | $0.31 | $0.09 | **$0.40** |

---

### Cenário: Júlia escalada (1000 médicos ativos)

**Premissas:**
- 1000 mensagens/dia
- 800 tokens input (contexto maior com mais histórico)
- 120 tokens output
- 22 dias úteis/mês

| Modelo | Custo Input | Custo Output | **Total/mês** |
|--------|-------------|--------------|---------------|
| Claude Haiku | $4.40 | $3.30 | **$7.70** |
| Claude Sonnet | $52.80 | $39.60 | **$92.40** |
| GPT-4o mini | $2.64 | $1.58 | **$4.22** |
| DeepSeek V3 | $4.93 | $1.11 | **$6.04** |

---

## Recomendação: Estratégia Híbrida

### Arquitetura proposta

```
┌─────────────────────────────────────────────────────────────┐
│                    ROTEADOR DE MODELO                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Mensagem recebida                                          │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────┐                                        │
│  │ Classificador   │ (regras simples, sem LLM)              │
│  │ de complexidade │                                        │
│  └────────┬────────┘                                        │
│           │                                                 │
│     ┌─────┴─────┐                                           │
│     │           │                                           │
│     ▼           ▼                                           │
│  SIMPLES     COMPLEXO                                       │
│     │           │                                           │
│     ▼           ▼                                           │
│  ┌───────┐  ┌─────────┐                                     │
│  │ Haiku │  │ Sonnet  │                                     │
│  │ $0.25 │  │ $3.00   │                                     │
│  └───────┘  └─────────┘                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Critérios de roteamento

**Usa Haiku (80% das mensagens):**
- Respostas curtas (confirmações, agradecimentos)
- Follow-ups simples
- Perguntas sobre vagas (quando há match claro)
- Coleta de dados básicos

**Usa Sonnet (20% das mensagens):**
- Primeira mensagem (prospecção fria)
- Médico demonstra resistência ou objeção
- Negociação de valores
- Situações emocionais (médico irritado)
- Médicos VIP
- Quando Haiku retorna confiança baixa

### Custo estimado com estratégia híbrida

Para 1000 msgs/dia:
- 800 msgs × Haiku = $6.16/mês
- 200 msgs × Sonnet = $18.48/mês
- **Total: ~$25/mês** (vs $92/mês só Sonnet)

**Economia: 73%**

---

## Decisão Recomendada

### Para MVP (começando hoje)

**Usar: Claude 3.5 Haiku** com fallback para Sonnet

Motivos:
1. Custo baixíssimo para validar a solução
2. Qualidade suficiente para teste de Turing em conversas simples
3. Podemos iterar rapidamente no prompt
4. Fácil migrar para Sonnet se necessário

### Para Produção (após validação)

**Usar: Estratégia híbrida Haiku + Sonnet**

Implementar roteador baseado em:
- Tipo de mensagem
- Histórico do médico
- Confiança do modelo anterior
- Métricas de sucesso por modelo

---

## Próximos Passos

1. [ ] Criar conta na Anthropic API
2. [ ] Obter API key para desenvolvimento
3. [ ] Implementar cliente com retry/fallback
4. [ ] Definir métricas de qualidade para comparação
5. [ ] Testar prompts com ambos os modelos
6. [ ] Implementar logging de custo por conversa

---

## Fontes

- [Anthropic API Pricing](https://docs.anthropic.com/en/docs/about-claude/pricing)
- [OpenAI API Pricing](https://openai.com/api/pricing/)
- [DeepSeek API Pricing](https://api-docs.deepseek.com/quick_start/pricing)
- [LLM API Pricing Comparison 2025](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025)
- [Claude API Cost Guide](https://costgoat.com/pricing/claude-api)
