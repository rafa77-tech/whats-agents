# Epic 2: Correcoes Criticas do Pipeline

**Status:** ✅ CONCLUÍDO
**Prioridade:** P0 - Bloqueante
**Deploy:** 03/02/2026 17:17 UTC

---

## Objetivo

Corrigir os 3 problemas criticos identificados:
1. **Extrator v2 nao captura especialidade** → Fix urgente
2. **Campos de classificacao nao atualizados** → Dashboard correto
3. **Vagas sendo 100% descartadas** → Importacao funcionando

---

## Stories

### S51.E2.0 - URGENTE: Corrigir Extrator v2 (Especialidade) ✅ FEITO

**Objetivo:** Garantir que o extrator capture a especialidade das mensagens

**Status:** ✅ Corrigido em 02/02/2026

**Arquivos criados/modificados:**
- `app/services/grupos/extrator_v2/extrator_especialidades.py` (NOVO)
- `app/services/grupos/extrator_v2/pipeline.py` (modificado)
- `app/services/grupos/extrator_v2/__init__.py` (modificado)

**O que foi feito:**
1. Criado `extrator_especialidades.py` com 50+ padrões de especialidades médicas
2. Modificado `pipeline.py` para chamar `extrair_especialidades_completo()`
3. Passando especialidades para `gerar_vagas()`

**Teste realizado:**
```
Mensagem: "VAGA PARA MÉDICO(A) - GINECOLOGIA E OBSTETRÍCIA"
Extraido: especialidade_raw = "Ginecologia e Obstetrícia" ✅
```

**Próximo passo:** Deploy para produção e monitorar importações.

**DoD:**
- [x] Especialidade sendo extraida corretamente
- [x] Vagas passando na validacao
- [x] Importacoes voltando a funcionar (deploy 03/02/2026)

---

### S51.E2.1 - Corrigir Atualizacao de Heuristica ✅ FEITO

**Objetivo:** Garantir que `passou_heuristica` seja atualizado apos calcular score

**Status:** ✅ Corrigido em 02/02/2026

**Arquivo:** `app/services/grupos/pipeline_worker.py`

**O que foi feito:**
1. Importado `atualizar_resultado_heuristica` de `classificador.py`
2. Adicionada chamada a `atualizar_resultado_heuristica()` em `processar_pendente()` após calcular score
3. Campos agora preenchidos automaticamente:
   - `passou_heuristica` (bool)
   - `score_heuristica` (float)
   - `keywords_encontradas` (array)
   - `motivo_descarte` (se rejeitado)
   - `processado_em` (timestamp)

**Código Adicionado:**
```python
# Sprint 51 - Fix: Salvar resultado da heurística no banco
await atualizar_resultado_heuristica(
    mensagem_id=mensagem_id,
    resultado=resultado
)
```

**DoD:**
- [x] Campo `passou_heuristica` preenchido para todas mensagens processadas
- [x] Campo `score_heuristica` preenchido
- [x] Campo `keywords_encontradas` preenchido
- [ ] Teste unitario adicionado (pendente)

---

### S51.E2.2 - Corrigir Atualizacao de Classificacao LLM ✅ FEITO

**Objetivo:** Garantir que `eh_oferta` seja atualizado apos classificacao

**Status:** ✅ Corrigido em 02/02/2026

**Arquivo:** `app/services/grupos/pipeline_worker.py`

**O que foi feito:**
1. Importado `atualizar_resultado_classificacao_llm` de `classificador.py`
2. Adicionada chamada a `atualizar_resultado_classificacao_llm()` em `processar_classificacao()` após classificar com LLM
3. Campos agora preenchidos automaticamente:
   - `eh_oferta` (bool)
   - `confianca_classificacao` (float)
   - `processado_em` (timestamp)

**Código Adicionado:**
```python
# Sprint 51 - Fix: Salvar resultado da classificação LLM no banco
await atualizar_resultado_classificacao_llm(
    mensagem_id=mensagem_id,
    resultado=resultado
)
```

**DoD:**
- [x] Campo `eh_oferta` preenchido para todas mensagens classificadas
- [x] Campo `confianca_classificacao` preenchido
- [ ] Teste unitario adicionado (pendente)

---

### S51.E2.3 - Investigar e Corrigir Importacao ✅ FEITO

**Objetivo:** Entender por que vagas nao estao sendo importadas

**Status:** ✅ Corrigido em 03/02/2026

**Causa Raiz Identificada:**
1. `importador.py` (linha 158-159) rejeita vagas sem `especialidade_id`
2. `normalizador.py` faz busca por `alias_normalizado` que e normalizado (sem acentos)
3. PostgreSQL ILIKE nao faz matching accent-insensitive: "obstetricia" != "Obstetrícia"
4. Resultado: especialidades extraidas corretamente mas nao normalizadas → importacao falha

**Solucao Aplicada:**
Adicionados 55 aliases normalizados para todas especialidades na tabela `especialidades_alias`:
```sql
-- Exemplo: "Ginecologia e Obstetrícia" agora tem alias "ginecologia e obstetricia"
INSERT INTO especialidades_alias (especialidade_id, alias, alias_normalizado, ...)
SELECT e.id, e.nome,
       LOWER(TRANSLATE(e.nome, 'áàâã...', 'aaaa...'))
FROM especialidades e
WHERE NOT EXISTS (...);
```

**Aliases Verificados:**
- ✅ "ginecologia e obstetricia" → "Ginecologia e Obstetrícia"
- ✅ "uti" → "Medicina Intensiva"
- ✅ "pronto socorro" → "Medicina de Emergência"
- ✅ "emergencia" → "Medicina de Emergência"
- ✅ Todos os 55 especialidades com alias normalizado

**DoD:**
- [x] Causa raiz identificada
- [x] Correcao implementada (aliases normalizados)
- [ ] Vagas sendo importadas (aguardando deploy)
- [ ] Taxa de importacao > 0% (aguardando deploy)

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
