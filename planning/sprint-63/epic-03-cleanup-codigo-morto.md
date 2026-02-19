# EPICO 03: Cleanup Codigo Morto

## Prioridade: P1 (Alto)

## Contexto

A auditoria identificou ~900 linhas de codigo morto no pipeline de grupos:
- `extrator.py` (638 linhas): extrator v1 inteiro, so acessivel se BOTH v2 e v3 estiverem desabilitados
- `processar_batch_deduplicacao` em `deduplicador.py` (~70 linhas): funcao batch orfao, nunca chamada pelo worker
- `processar_batch_importacao` em `importador.py` (~60 linhas): funcao batch orfao, nunca chamada

Codigo morto adiciona complexidade cognitiva, confunde novos devs, e acumula divida tecnica.

## Escopo

- **Incluido**: Remover extrator v1, funcoes batch orfas, imports mortos
- **Excluido**: Refatorar extrator v2/v3 (epic 05), refatorar hospital_web (epic 06)

---

## Tarefa 1: Remover extrator v1

### Objetivo

Deletar `app/services/grupos/extrator.py` (638 linhas) e remover todos os imports/referencias.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Deletar | `app/services/grupos/extrator.py` |
| Modificar | `app/services/grupos/pipeline_worker.py` (remover import e metodo v1) |
| Verificar | `tests/grupos/` (remover testes do extrator v1 se existirem) |

### Implementacao

1. Verificar que nenhum import ativo referencia `extrator.py`:
   ```bash
   grep -r "from app.services.grupos.extrator import" app/ --include="*.py"
   grep -r "from app.services.grupos import extrator" app/ --include="*.py"
   ```

2. Remover `processar_extracao` (metodo v1) do `PipelineGrupos` se existir fallback
3. Remover feature flag `EXTRATOR_V2_ENABLED` se v1 era o unico fallback
4. Deletar arquivo

### Testes Obrigatorios

**Unitarios:**
- [ ] Pipeline funciona sem extrator v1
- [ ] Nenhum import quebrado apos remocao
- [ ] Feature flag removida ou atualizada

### Definition of Done

- [ ] `extrator.py` deletado
- [ ] Zero imports restantes para `extrator.py`
- [ ] Testes existentes passando
- [ ] `grep -r "extrator.py" app/` retorna vazio

### Estimativa

1 ponto

---

## Tarefa 2: Remover funcoes batch orfas

### Objetivo

Remover `processar_batch_deduplicacao` de `deduplicador.py` e `processar_batch_importacao` de `importador.py`. Ambas sao reliquias do design pre-worker que nunca sao chamadas.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/deduplicador.py` |
| Modificar | `app/services/grupos/importador.py` |

### Implementacao

1. Verificar que nenhum codigo chama essas funcoes:
   ```bash
   grep -r "processar_batch_deduplicacao" app/ --include="*.py"
   grep -r "processar_batch_importacao" app/ --include="*.py"
   ```

2. Remover funcoes e imports associados

### Testes Obrigatorios

- [ ] Nenhum teste existente quebra
- [ ] grep confirma zero referencias

### Definition of Done

- [ ] Funcoes removidas
- [ ] Zero referencias restantes
- [ ] Testes passando

### Estimativa

0.5 pontos
