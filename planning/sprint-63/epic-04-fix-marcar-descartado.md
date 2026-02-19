# EPICO 04: Fix marcar_como_descartado Bypass

## Prioridade: P1 (Alto)

## Contexto

A funcao `marcar_como_descartado` em `fila.py:359` faz UPDATE direto no banco em vez de usar `atualizar_estagio`. Isso significa que:
1. `mensagens_grupo.status` nao e sincronizado
2. Metricas de descarte ficam inconsistentes
3. Log de auditoria e incompleto

Compare com `marcar_como_finalizado` (linha 355) que corretamente usa `atualizar_estagio`.

## Escopo

- **Incluido**: Refatorar `marcar_como_descartado` para usar `atualizar_estagio`
- **Excluido**: Mudar `atualizar_estagio` em si

---

## Tarefa 1: Corrigir marcar_como_descartado

### Objetivo

Fazer `marcar_como_descartado` usar `atualizar_estagio` para manter consistencia.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/grupos/fila.py` |

### Implementacao

```python
# ANTES (linha 359):
async def marcar_como_descartado(item_id: UUID, motivo: str) -> None:
    """Marca item como descartado."""
    supabase.table("fila_processamento_grupos").update(
        {
            "estagio": EstagioPipeline.DESCARTADO.value,
            "ultimo_erro": f"descartado: {motivo}",
            "updated_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(item_id)).execute()

# DEPOIS:
async def marcar_como_descartado(item_id: UUID, motivo: str) -> None:
    """Marca item como descartado."""
    await atualizar_estagio(
        item_id=item_id,
        novo_estagio=EstagioPipeline.DESCARTADO,
        erro=f"descartado: {motivo}",
    )
```

### Testes Obrigatorios

**Unitarios:**
- [ ] marcar_como_descartado chama atualizar_estagio
- [ ] Motivo e preservado no campo erro
- [ ] mensagens_grupo.status e atualizado (via atualizar_estagio)

### Definition of Done

- [ ] Funcao refatorada
- [ ] Testes passando
- [ ] Consistencia com marcar_como_finalizado

### Estimativa

0.5 pontos
