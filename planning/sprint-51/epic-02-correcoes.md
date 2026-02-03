# Epic 2: Correcoes Criticas do Pipeline

**Status:** 🔴 Nao Iniciada
**Prioridade:** P0 - Bloqueante

---

## Objetivo

Corrigir os 3 problemas criticos identificados:
1. **Extrator v2 nao captura especialidade** → Fix urgente
2. **Campos de classificacao nao atualizados** → Dashboard correto
3. **Vagas sendo 100% descartadas** → Importacao funcionando

---

## Stories

### S51.E2.0 - URGENTE: Corrigir Extrator v2 (Especialidade)

**Objetivo:** Garantir que o extrator capture a especialidade das mensagens

**Arquivo:** `app/services/grupos/extrator_v2/`

**Evidencia do bug:**
```
Mensagem: "VAGA PARA MÉDICO(A) - GINECOLOGIA E OBSTETRÍCIA"
Extraido: especialidade_raw = NULL
Resultado: 100% das vagas descartadas
```

**Tarefas:**
1. Investigar `extrator_v2/` para entender logica de extracao
2. Identificar por que `especialidade_raw` retorna NULL
3. Corrigir extracao de especialidade
4. Testar com mensagens reais
5. Deploy e monitorar

**DoD:**
- [ ] Especialidade sendo extraida corretamente
- [ ] Vagas passando na validacao
- [ ] Importacoes voltando a funcionar

---

### S51.E2.1 - Corrigir Atualizacao de Heuristica

**Objetivo:** Garantir que `passou_heuristica` seja atualizado apos calcular score

**Arquivo:** `app/services/grupos/pipeline_worker.py`

**Tarefas:**
1. Localizar funcao `processar_pendente()`
2. Apos calcular score, chamar `atualizar_resultado_heuristica()`
3. Garantir que campos sejam preenchidos:
   - `passou_heuristica` (bool)
   - `score_heuristica` (float)
   - `keywords_encontradas` (array)
   - `motivo_descarte` (se rejeitado)

**Codigo Esperado:**
```python
async def processar_pendente(item):
    resultado_heuristica = await calcular_score_heuristica(texto)

    # ADICIONAR: Salvar resultado no banco
    await atualizar_resultado_heuristica(
        mensagem_id=item.mensagem_id,
        resultado=resultado_heuristica
    )

    if resultado_heuristica.score < 0.5:
        return ResultadoPipeline(acao="descartar")
    # ... resto do codigo
```

**DoD:**
- [ ] Campo `passou_heuristica` preenchido para todas mensagens processadas
- [ ] Campo `score_heuristica` preenchido
- [ ] Campo `keywords_encontradas` preenchido
- [ ] Teste unitario adicionado

---

### S51.E2.2 - Corrigir Atualizacao de Classificacao LLM

**Objetivo:** Garantir que `eh_oferta` seja atualizado apos classificacao

**Arquivo:** `app/services/grupos/pipeline_worker.py`

**Tarefas:**
1. Localizar funcao `processar_classificacao()`
2. Apos chamar LLM, chamar `atualizar_resultado_classificacao_llm()`
3. Garantir que campos sejam preenchidos:
   - `eh_oferta` (bool)
   - `confianca_classificacao` (float)

**Codigo Esperado:**
```python
async def processar_classificacao(item):
    resultado_llm = await classificar_com_llm(texto)

    # ADICIONAR: Salvar resultado no banco
    await atualizar_resultado_classificacao_llm(
        mensagem_id=item.mensagem_id,
        resultado=resultado_llm
    )

    if resultado_llm.eh_oferta and resultado_llm.confianca >= threshold:
        return ResultadoPipeline(acao="extrair")
    # ... resto do codigo
```

**DoD:**
- [ ] Campo `eh_oferta` preenchido para todas mensagens classificadas
- [ ] Campo `confianca_classificacao` preenchido
- [ ] Teste unitario adicionado

---

### S51.E2.3 - Investigar e Corrigir Importacao

**Objetivo:** Entender por que vagas nao estao sendo importadas

**Tarefas:**
1. Verificar se estagio IMPORTACAO esta sendo executado
2. Verificar funcao `processar_importacao()`
3. Identificar condicoes que impedem importacao
4. Corrigir fluxo

**Investigacao:**
```sql
-- Ver estagios das vagas na fila
SELECT estagio, COUNT(*)
FROM fila_processamento_grupos
GROUP BY estagio;

-- Ver status das vagas
SELECT status, COUNT(*)
FROM vagas_grupo
GROUP BY status;
```

**DoD:**
- [ ] Causa raiz identificada
- [ ] Correcao implementada
- [ ] Vagas sendo importadas
- [ ] Taxa de importacao > 0%

---

### S51.E2.4 - Backfill de Mensagens Existentes

**Objetivo:** Preencher campos NULL em mensagens historicas

**Tarefas:**
1. Criar script de backfill
2. Usar vagas_grupo para inferir classificacao
3. Atualizar mensagens que geraram vagas

**Script:**
```sql
-- Se mensagem gerou vaga, entao passou heuristica e eh oferta
UPDATE mensagens_grupo m
SET
    passou_heuristica = true,
    eh_oferta = true
FROM vagas_grupo v
WHERE v.mensagem_id = m.id
  AND m.passou_heuristica IS NULL;
```

**DoD:**
- [ ] Script de backfill criado
- [ ] Dados historicos atualizados
- [ ] Dashboard mostrando numeros corretos

---

## Validacao

Apos todas as correcoes, verificar:

```sql
-- Deve retornar dados reais, nao zeros
SELECT
    COUNT(*) as total_mensagens,
    COUNT(*) FILTER (WHERE passou_heuristica = true) as passou_heuristica,
    COUNT(*) FILTER (WHERE eh_oferta = true) as eh_oferta
FROM mensagens_grupo
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Deve ter vagas importadas
SELECT
    COUNT(*) as total_vagas,
    COUNT(*) FILTER (WHERE status = 'importada') as importadas
FROM vagas_grupo
WHERE created_at >= NOW() - INTERVAL '24 hours';
```

---

## Riscos e Mitigacao

| Risco | Mitigacao |
|-------|-----------|
| Impacto em performance | Usar batch updates |
| Erro em producao | Testar em staging primeiro |
| Dados inconsistentes | Validar apos cada mudanca |
