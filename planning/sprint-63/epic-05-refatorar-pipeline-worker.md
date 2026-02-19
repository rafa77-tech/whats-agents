# EPICO 05: Refatorar pipeline_worker.py

## Prioridade: P2 (Medio)

## Contexto

`pipeline_worker.py` tem duplicacao significativa entre os tres metodos de extracao (v1, v2, v3):
- Fetch de mensagem do banco (identico nos 3)
- Fan-out cap (implementado 3x identicamente na Sprint 63)
- Criacao de vagas_grupo (identico v2/v3)
- Tratamento de erro (identico nos 3)

Apos remocao do extrator v1 (Epic 03), v1 pode ser eliminado. Restam v2 e v3 com codigo duplicado.

## Escopo

- **Incluido**: Extrair helpers compartilhados, eliminar duplicacao v2/v3
- **Excluido**: Mudar logica de negocio, alterar estagios do pipeline

---

## Tarefa 1: Extrair helper de fetch + fan-out

### Objetivo

Criar funcao compartilhada para o padrao "buscar mensagem → chamar extrator → aplicar fan-out cap → criar vagas".

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/pipeline_worker.py` |

### Implementacao

```python
async def _fetch_mensagem(self, mensagem_id: UUID) -> dict | None:
    """Busca dados da mensagem no banco."""
    result = supabase.table("mensagens_grupo").select("*").eq("id", str(mensagem_id)).single().execute()
    return result.data

def _aplicar_fan_out_cap(self, vagas: list, mensagem_id: UUID, label: str = "") -> list:
    """Limita vagas ao MAX_VAGAS_POR_MENSAGEM."""
    if len(vagas) > MAX_VAGAS_POR_MENSAGEM:
        logger.warning(
            f"{label}Mensagem {mensagem_id} gerou {len(vagas)} vagas, "
            f"limitando a {MAX_VAGAS_POR_MENSAGEM}"
        )
        return vagas[:MAX_VAGAS_POR_MENSAGEM]
    return vagas
```

Refatorar `processar_extracao_v2` e `processar_extracao_v3` para usar esses helpers.

### Testes Obrigatorios

**Unitarios:**
- [ ] _fetch_mensagem retorna dados corretos
- [ ] _aplicar_fan_out_cap limita quando excede
- [ ] _aplicar_fan_out_cap nao altera quando dentro do limite
- [ ] Pipeline v2 funciona com helpers
- [ ] Pipeline v3 funciona com helpers

### Definition of Done

- [ ] Zero duplicacao entre v2 e v3 para fetch, fan-out, e criacao de vagas
- [ ] Testes existentes passando
- [ ] Novos testes para helpers

### Estimativa

3 pontos

---

## Tarefa 2: Mover feature flags para constantes de modulo

### Objetivo

Feature flags `PIPELINE_V3_ENABLED` e `EXTRATOR_V2_ENABLED` sao lidas via `os.environ.get` dentro de funcoes, causando overhead e dificultando testes.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/pipeline_worker.py` |

### Implementacao

```python
# No topo do modulo:
PIPELINE_V3_ENABLED = os.environ.get("PIPELINE_V3_ENABLED", "true").lower() == "true"
EXTRATOR_V2_ENABLED = os.environ.get("EXTRATOR_V2_ENABLED", "true").lower() == "true"
```

### Testes Obrigatorios

- [ ] Testes com patch de constante em vez de patch.dict(os.environ)
- [ ] Comportamento identico ao anterior

### Definition of Done

- [ ] Feature flags como constantes
- [ ] Testes atualizados
- [ ] Zero os.environ.get dentro de funcoes

### Estimativa

1 ponto
