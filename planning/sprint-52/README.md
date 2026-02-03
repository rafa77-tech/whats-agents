# Sprint 52 - Pipeline v3: Extração Inteligente com LLM

**Início:** 03/02/2026
**Chip em foco:** 5511916175810 (Revoluna)
**Status:** 🔄 Em Andamento

---

## Progresso

| Epic | Status | Descrição |
|------|--------|-----------|
| Epic 1: LLM Extrator | ✅ FEITO | `extrator_llm.py` criado e testado |
| Epic 2: Integração Pipeline | ✅ FEITO | Feature flag `PIPELINE_V3_ENABLED` |
| Epic 3: Testes | ✅ FEITO | Bug R$ 202 corrigido |
| Epic 4: Deploy | 📋 Pendente | Aguardando ativação em produção |

---

## Objetivo Estratégico

Substituir extração baseada em regex por LLM unificado que classifica E extrai em uma única chamada. Isso resolve:

1. **Bug dos valores R$ 202** - Regex captura "202" de datas "2026"
2. **Fragilidade do regex** - Padrões quebram com variações de formatação
3. **Contexto perdido** - Regex não entende contexto semântico
4. **Manutenção difícil** - 50+ padrões de especialidades para manter

---

## Motivação (Problemas do v2)

### Bug Identificado em Sprint 51

```
Mensagem: "Vaga 19/01/2026, R$ 2.500"
Extração atual: valor = 202 (capturou "202" de "2026")
Resultado: 1.118 vagas com valor R$ 202
```

### Limitações Estruturais

| Problema | Impacto |
|----------|---------|
| Regex para valores | Falsos positivos em datas, telefones |
| Regex para especialidades | 50+ padrões, fácil de quebrar |
| Múltiplas passagens | Contexto perdido entre estágios |
| Sem entendimento semântico | "5 plantões por R$ 2.500" → não sabe dividir |

---

## Arquitetura Pipeline v3

### Estágios (4 vs 7 do v2)

```
v2: PENDENTE → HEURISTICA → CLASSIFICACAO → EXTRACAO → NORMALIZACAO → DEDUP → IMPORT (7)
v3: PENDENTE → DEDUP → LLM_UNIFICADO → IMPORT (4)
```

### Mudanças Chave

| Estágio | v2 | v3 |
|---------|----|----|
| Dedup | Após extração | **Antes** (economia de tokens) |
| Heurística | Regex separado | **Dentro do LLM** |
| Classificação | LLM separado | **Unificado** |
| Extração | Regex | **LLM com JSON** |
| Normalização | Lookup separado | **LLM retorna normalizado** |

### Prompt Unificado (Classificação + Extração)

```
Você é um especialista em classificação de vagas médicas.

Analise a mensagem e retorne JSON:

{
  "eh_vaga": true/false,
  "confianca": 0.0-1.0,
  "motivo_descarte": "string ou null",

  "dados_extraidos": {
    "hospital": "string ou null",
    "especialidade": "string normalizada",
    "valor": número ou null,
    "data": "YYYY-MM-DD ou null",
    "periodo": "diurno/noturno/12h/24h",
    "observacoes": "string ou null"
  }
}

REGRAS CRÍTICAS:
- valor é o preço POR PLANTÃO, não total
- Se "R$ 10.000 por 5 plantões", valor = 2000
- Números em datas (2026, 19/01) NÃO são valores
- Especialidade deve ser normalizada (ex: "GO" → "Ginecologia e Obstetrícia")
```

---

## Épicos

### Epic 1: LLM Extrator Unificado (P0) ✅ CONCLUÍDO

**Objetivo:** Substituir extração regex por LLM

**Arquivos criados/modificados:**
- `app/services/grupos/extrator_v2/extrator_llm.py` (NOVO)
- `app/services/grupos/extrator_v2/__init__.py` (exports)
- `app/services/grupos/pipeline_worker.py` (método `processar_extracao_v3`)

**Tarefas:**
1. [x] Criar `extrator_llm.py` com prompt unificado
2. [x] Definir schema JSON de resposta
3. [x] Implementar conversão para VagaAtomica
4. [x] Adicionar cache Redis (24h TTL)
5. [x] Testes com mensagens reais

**Resultados dos Testes:**
```
Caso 1 (Bug R$ 202): ✅ CORRIGIDO - valor=None em vez de 202
Caso 2 (Valor real): ✅ R$ 2.500 extraído corretamente
Caso 3 (Não-vaga): ✅ Classificação correta
```

**DoD:**
- [x] Bug R$ 202 eliminado
- [x] Especialidades normalizadas automaticamente
- [x] Cache funcional

---

### Epic 2: Deduplicação Antecipada (P1)

**Objetivo:** Mover dedup para ANTES do LLM (economia de tokens)

**Lógica:**
```python
# Hash da mensagem (texto normalizado)
hash_msg = hashlib.md5(normalizar(texto)).hexdigest()

# Se já processamos mensagem idêntica, pular LLM
if ja_processado(hash_msg):
    return resultado_anterior
```

**Tarefas:**
1. [ ] Criar tabela `mensagens_hash` para cache
2. [ ] Implementar normalização de texto (lowercase, sem emojis, etc)
3. [ ] Mover dedup para antes do LLM no pipeline

**DoD:**
- [ ] Redução de 30%+ em chamadas LLM
- [ ] Métricas de economia de tokens

---

### Epic 3: Observabilidade v3 (P1)

**Objetivo:** Métricas específicas do pipeline v3

**Métricas:**
- Tokens consumidos por mensagem
- Taxa de fallback para regex
- Precisão de extração (amostragem)
- Latência por estágio

**Tarefas:**
1. [ ] Adicionar contador de tokens
2. [ ] Dashboard de métricas v3
3. [ ] Alertas de regressão

---

### Epic 4: Migração Gradual (P2)

**Objetivo:** Rollout seguro v2 → v3

**Estratégia:**
1. Feature flag `PIPELINE_VERSION=v3`
2. A/B test: 10% das mensagens no v3
3. Comparar resultados v2 vs v3
4. Aumentar gradualmente até 100%

**Tarefas:**
1. [ ] Implementar feature flag
2. [ ] Logging para comparação
3. [ ] Dashboard de A/B test
4. [ ] Runbook de rollback

---

## Estimativas

| Epic | Complexidade | Tempo Estimado |
|------|--------------|----------------|
| Epic 1: LLM Extrator | Média | 2-3 horas |
| Epic 2: Dedup Antecipada | Baixa | 1-2 horas |
| Epic 3: Observabilidade | Baixa | 1-2 horas |
| Epic 4: Migração | Média | 2-3 horas |
| **Total** | | **6-10 horas** |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Custo de tokens aumenta | Média | Médio | Dedup antecipada + cache |
| LLM retorna JSON inválido | Baixa | Alto | Fallback para regex v2 |
| Latência aumenta | Média | Médio | Batch processing |
| Regressão na qualidade | Baixa | Alto | A/B test + monitoramento |

---

## Ordem de Implementação Sugerida

1. **Fase 1 (Hoje):** Epic 1 - LLM Extrator
   - Resolve bug R$ 202 imediatamente
   - Maior impacto, menor risco

2. **Fase 2:** Epic 2 - Dedup Antecipada
   - Otimização de custo

3. **Fase 3:** Epic 3 + 4 - Observabilidade + Migração
   - Produção segura

---

## Definition of Done (Sprint)

### Obrigatório (P0)
- [x] LLM extrator funcionando
- [x] Bug R$ 202 corrigido
- [x] Feature flag `PIPELINE_V3_ENABLED`
- [x] Testes passando

### Desejável (P1)
- [ ] Dedup antecipada implementada
- [x] Cache Redis para economia de tokens
- [x] Feature flag para rollback (v2 como fallback)

### Futuro (P2)
- [ ] A/B test completo
- [ ] Dashboard de comparação v2 vs v3

---

## Como Ativar

Para ativar o pipeline v3 em produção:

```bash
# Railway - adicionar variável de ambiente
PIPELINE_V3_ENABLED=true
```

O v3 usa o mesmo fluxo do v2 para persistência (`_criar_vaga_grupo_v2`), garantindo compatibilidade.
