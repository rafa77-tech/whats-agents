# EPICO 04: Chip Z-API Recovery

## Prioridade: P1 (Alto)

## Contexto

O chip principal `...8618` (active, operacao, trust 85) esta desconectado com erro "Event loop is closed" e 24 erros nas ultimas 24h. Este e o chip mais maduro do pool. Alem disso, nao existe verificacao de conexao para chips Z-API — apenas Evolution tem `evolution_connected` check.

## Escopo

- **Incluido**: Diagnostico e reconexao do chip z-api, adicionar connection check para z-api no executor
- **Excluido**: Migracao de provider (z-api → evolution), mudancas na infra Z-API

---

## Tarefa 1: Diagnosticar e reconectar chip Z-API

### Objetivo

Investigar o erro "Event loop is closed" no chip `...8618` e reconectar.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Verificar | `app/services/whatsapp_providers/zapi.py` |
| Verificar | Supabase: tabela `chips` registro do chip |

### Implementacao

**Passo 1 — Diagnostico:**
```sql
-- Verificar estado completo do chip
SELECT * FROM chips WHERE telefone LIKE '%8618';

-- Verificar ultimos erros
SELECT * FROM chip_interactions
WHERE chip_id = (SELECT id FROM chips WHERE telefone LIKE '%8618')
AND sucesso = false
ORDER BY created_at DESC LIMIT 20;
```

**Passo 2 — Verificar credenciais Z-API:**
- Confirmar que `zapi_instance_id` e `zapi_token` estao validos
- Testar conexao manualmente via curl:
```bash
curl -X GET "https://api.z-api.io/instances/{instance_id}/token/{token}/status" \
  -H "Client-Token: {client_token}"
```

**Passo 3 — Reconectar:**
- Se credenciais validas: resetar estado no banco
```sql
UPDATE chips SET
  erros_ultimas_24h = 0,
  ultimo_erro_codigo = NULL,
  ultimo_erro_msg = NULL,
  ultimo_erro_em = NULL,
  cooldown_until = NULL,
  circuit_breaker_ativo = false,
  circuit_breaker_desde = NULL
WHERE telefone LIKE '%8618';
```
- Se credenciais invalidas: gerar novo token via dashboard Z-API

**Passo 4 — Verificar conectividade:**
- Enviar mensagem de teste via endpoint `/warmer/ciclo`
- Verificar logs para resultado

### Testes Obrigatorios

Nao aplicavel (operacional).

### Definition of Done

- [ ] Causa raiz do "Event loop is closed" identificada
- [ ] Chip reconectado e enviando mensagens com sucesso
- [ ] erros_ultimas_24h zerado
- [ ] Pelo menos 1 CONVERSA_PAR bem-sucedido apos reconexao

### Estimativa

1.5 horas

---

## Tarefa 2: Connection check para chips Z-API

### Objetivo

Adicionar verificacao de conexao para chips Z-API no executor, similar ao que ja existe para Evolution.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/executor.py` |
| Modificar | `app/services/whatsapp_providers/zapi.py` |

### Implementacao

**Opcao A (recomendada — lightweight check):**

Verificar se o chip tem erros recentes ao inves de fazer health check HTTP (que adicionaria latencia):

```python
# Em executor.py, _executar_conversa_par():
provider_tipo = chip.get("provider") or "evolution"

if provider_tipo == "evolution" and not chip.get("evolution_connected"):
    logger.warning(f"[WarmupExecutor] Chip {chip['telefone'][-4:]} evolution desconectado")
    return False

# NOVO: Check para Z-API
if provider_tipo == "z-api":
    ultimo_erro = chip.get("ultimo_erro_em")
    if ultimo_erro:
        from datetime import datetime, timedelta
        erro_dt = datetime.fromisoformat(str(ultimo_erro).replace("Z", "+00:00"))
        if (agora_brasilia() - erro_dt) < timedelta(minutes=15):
            logger.warning(
                f"[WarmupExecutor] Chip Z-API {chip['telefone'][-4:]} com erro recente "
                f"({chip.get('ultimo_erro_msg', 'N/A')}), skip"
            )
            return False
```

**Atualizar `_buscar_chip()`** para incluir `ultimo_erro_em` e `ultimo_erro_msg` no select (se ainda nao incluidos).

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_zapi_skip_erro_recente` — chip z-api com erro ha 5 min retorna False
- [ ] `test_zapi_executa_erro_antigo` — chip z-api com erro ha 30 min executa normalmente
- [ ] `test_zapi_executa_sem_erros` — chip z-api sem erros executa normalmente
- [ ] `test_evolution_check_nao_afetado` — evolution continua usando evolution_connected

### Definition of Done

- [ ] Chips Z-API com erro nos ultimos 15 min pulados automaticamente
- [ ] Log WARNING indica motivo do skip
- [ ] `_buscar_chip()` retorna campos de erro
- [ ] Testes passando (4+)

### Estimativa

1.5 horas
