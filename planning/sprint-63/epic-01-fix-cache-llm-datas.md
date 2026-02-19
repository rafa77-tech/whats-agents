# EPICO 01: Fix Cache LLM + Datas

## Prioridade: P0 (Critico) — Bug de Producao

## Contexto

O extrator LLM (`extrator_llm.py`) usa cache Redis com chave baseada apenas no hash do texto da mensagem. Quando a mesma mensagem e processada em datas diferentes (ex: "plantao amanha"), o cache retorna o resultado anterior com data absoluta errada (ex: 2023-02-20 em vez de 2026-02-20). Isso faz TODAS as vagas serem descartadas por "data no passado".

**Evidencia:** Dashboard mostra 7 vagas extraidas, todas descartadas com motivo "data no passado". Uma vaga do UPA VERGUEIRO tinha data `2023-02-20`.

## Escopo

- **Incluido**: Corrigir chave de cache para incluir data_referencia, invalidar cache antigo
- **Excluido**: Refatorar extrator_datas.py (parsing de datas relativas funciona corretamente)

---

## Tarefa 1: Incluir data_referencia na chave de cache

### Objetivo

Alterar as funcoes `buscar_extracao_cache` e `salvar_extracao_cache` para incluir `data_referencia` na chave, evitando que resultados com datas relativas ("amanha", "proximo sabado") retornem valores absolutos errados.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/extrator_v2/extrator_llm.py` |

### Implementacao

```python
# ANTES (linha 266):
chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"

# DEPOIS:
def _chave_cache(texto: str, data_referencia: date | None = None) -> str:
    """Gera chave de cache incluindo data de referencia."""
    sufixo_data = data_referencia.isoformat() if data_referencia else "sem_data"
    return f"{CACHE_PREFIX}{_hash_texto(texto)}:{sufixo_data}"
```

Alterar `buscar_extracao_cache(texto)` para `buscar_extracao_cache(texto, data_referencia)`.
Alterar `salvar_extracao_cache(texto, resultado)` para `salvar_extracao_cache(texto, resultado, data_referencia)`.

Propagar `data_referencia` nos call sites dentro de `classificar_e_extrair_llm`.

### Testes Obrigatorios

**Unitarios:**
- [ ] Cache com mesma mensagem em datas diferentes retorna resultados diferentes
- [ ] Cache com mesma mensagem na mesma data retorna cache hit
- [ ] Cache sem data_referencia usa sufixo "sem_data"
- [ ] _chave_cache gera chaves distintas para datas distintas

**Integracao:**
- [ ] Fluxo completo: extrai vaga com "amanha", muda data_referencia, re-extrai e obtem data correta

### Definition of Done

- [ ] Chave de cache inclui data_referencia
- [ ] Call sites atualizados para passar data_referencia
- [ ] Cache antigo expira naturalmente (TTL 24h)
- [ ] Testes unitarios passando
- [ ] Teste de integracao passando

### Estimativa

2 pontos

---

## Tarefa 2: Validar que data_referencia chega ao extrator

### Objetivo

Verificar e corrigir a cadeia de propagacao de `data_referencia` desde o pipeline_worker ate o extrator LLM.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Verificar | `app/services/grupos/pipeline_worker.py` |
| Verificar | `app/services/grupos/extrator_v2/extrator_llm.py` |
| Verificar | `app/services/grupos/extrator_v2/pipeline_extracao.py` |

### Implementacao

Rastrear o fluxo:
1. `pipeline_worker.processar_extracao` → `extrair_dados_mensagem_v2`
2. `extrair_dados_mensagem_v2` → `classificar_e_extrair_llm`
3. `classificar_e_extrair_llm` → `buscar_extracao_cache` (aqui precisa do data_referencia)

Garantir que `data_referencia = date.today()` (ou `agora_brasilia().date()`) e passado em toda a cadeia.

### Testes Obrigatorios

**Unitarios:**
- [ ] pipeline_worker passa data_referencia ao extrator
- [ ] extrator propaga data_referencia ao cache

### Definition of Done

- [ ] data_referencia propagado corretamente em toda a cadeia
- [ ] Sem valores None onde deveria ter data
- [ ] Testes passando

### Estimativa

1 ponto
