# EPICO 01: Fix Pairing Engine & Scheduler

## Prioridade: P0 (Critico)

## Contexto

O sistema de warmup esta 100% quebrado porque o pairing engine filtra chips por `status = "connected"`, um valor que nenhum chip no banco possui. Alem disso, o scheduler agenda atividades stub (ENTRAR_GRUPO, MENSAGEM_GRUPO, ATUALIZAR_PERFIL) que sempre falham, degradando trust score e desperdicando slots de atividade.

## Escopo

- **Incluido**: Fix do filtro de status no pairing engine, remocao de stubs do scheduler, testes
- **Excluido**: Implementacao real de ENTRAR_GRUPO/MENSAGEM_GRUPO (sprint futura), mudancas no trust score engine

---

## Tarefa 1: Fix filtro de status no Pairing Engine

### Objetivo

Corrigir `_carregar_chips_disponiveis()` para buscar chips com status reais do banco.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/pairing_engine.py` |

### Implementacao

Linha 109 de `pairing_engine.py`:

```python
# ANTES (bugado):
.eq("status", "connected")

# DEPOIS (corrigido):
.in_("status", ["warming", "active"])
```

**Nota:** Nao incluir "degraded" nem "provisioned" — chips degradados nao devem participar de warmup ativo, e provisionados ainda nao iniciaram.

**Decisao de design:** Se no futuro for necessario incluir "degraded", deve ser avaliado caso a caso. O status "degraded" indica problemas (trust baixo ou muitos erros) e incluir esses chips pode contaminar pares saudaveis.

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_carregar_chips_disponiveis_status_warming` — chips com status "warming" retornados
- [ ] `test_carregar_chips_disponiveis_status_active` — chips com status "active" retornados
- [ ] `test_carregar_chips_disponiveis_exclui_degraded` — chips com status "degraded" excluidos
- [ ] `test_carregar_chips_disponiveis_exclui_provisioned` — chips com status "provisioned" excluidos
- [ ] `test_carregar_chips_disponiveis_exclui_listener` — chips tipo "listener" excluidos (regressao)

**Integracao:**
- [ ] `test_encontrar_par_com_chips_warming` — encontra par entre 2+ chips warming
- [ ] `test_encontrar_par_retorna_none_sem_chips` — retorna None quando pool vazio

### Definition of Done

- [ ] Filtro `.in_("status", ["warming", "active"])` aplicado
- [ ] Testes unitarios passando (5+)
- [ ] Teste de integracao passando (2+)
- [ ] Log `[Pairing] X chips disponiveis para pareamento` mostra >0 quando ha chips warming/active
- [ ] Cobertura >90% no metodo `_carregar_chips_disponiveis`

### Estimativa

2 horas (fix simples + testes extensivos)

---

## Tarefa 2: Remover stubs do scheduler (ATIVIDADES_POR_FASE)

### Objetivo

Remover atividades nao implementadas do config ATIVIDADES_POR_FASE para que o scheduler so agende trabalho real.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/scheduler.py` |
| Modificar | `app/services/warmer/executor.py` |

### Implementacao

Em `scheduler.py` linhas 54-106, remover tipos stub de todas as fases:

```python
# ANTES:
"expansao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.ENTRAR_GRUPO,      # ← stub, remover
        TipoAtividade.MARCAR_LIDO,
        TipoAtividade.ENVIAR_MIDIA,
    ],
    ...
},
"pre_operacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.MENSAGEM_GRUPO,    # ← stub, remover
        TipoAtividade.ENVIAR_MIDIA,
        TipoAtividade.ATUALIZAR_PERFIL,  # ← stub, remover
    ],
    ...
},
"teste_graduacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.MENSAGEM_GRUPO,    # ← stub, remover
        TipoAtividade.ENVIAR_MIDIA,
    ],
    ...
},
"operacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.MENSAGEM_GRUPO,    # ← stub, remover
    ],
    ...
},

# DEPOIS:
"expansao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.MARCAR_LIDO,
        TipoAtividade.ENVIAR_MIDIA,
    ],
    ...
},
"pre_operacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.ENVIAR_MIDIA,
        TipoAtividade.MARCAR_LIDO,
    ],
    ...
},
"teste_graduacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.ENVIAR_MIDIA,
        TipoAtividade.MARCAR_LIDO,
    ],
    ...
},
"operacao": {
    "atividades": [
        TipoAtividade.CONVERSA_PAR,
        TipoAtividade.MARCAR_LIDO,
    ],
    ...
},
```

Em `executor.py`, manter os stubs (entrar_grupo, mensagem_grupo, atualizar_perfil) por backward compatibility caso sejam chamados manualmente, mas adicionar log WARNING ao inves de DEBUG:

```python
async def _executar_entrar_grupo(chip: dict) -> bool:
    logger.warning(
        f"[WarmupExecutor] entrar_grupo chamado mas nao implementado. "
        f"chip={chip['telefone'][-4:]}. Esta atividade nao deveria ser agendada."
    )
    return False
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_atividades_por_fase_sem_stubs` — nenhuma fase contem ENTRAR_GRUPO, MENSAGEM_GRUPO ou ATUALIZAR_PERFIL
- [ ] `test_todas_fases_tem_conversa_par` — CONVERSA_PAR presente em todas as fases
- [ ] `test_planejar_dia_so_atividades_reais` — planejar_dia() gera apenas atividades implementadas

**Regressao:**
- [ ] `test_executor_stub_retorna_false` — stubs continuam retornando False se chamados diretamente

### Definition of Done

- [ ] ENTRAR_GRUPO, MENSAGEM_GRUPO, ATUALIZAR_PERFIL removidos de ATIVIDADES_POR_FASE
- [ ] Stubs em executor.py com log WARNING (nao DEBUG)
- [ ] Testes passando (4+)
- [ ] Scheduler so agenda CONVERSA_PAR, MARCAR_LIDO e ENVIAR_MIDIA

### Estimativa

1 hora

---

## Tarefa 3: Validacao end-to-end do pairing + scheduler

### Objetivo

Criar teste de integracao que simula um ciclo completo: scheduler agenda → executor busca par → par encontrado → atividade marcada como executada.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `tests/services/warmer/test_pairing_scheduler_integration.py` |

### Implementacao

```python
async def test_ciclo_conversa_par_end_to_end():
    """
    Cenario: 2 chips em warming/primeiros_contatos,
    scheduler agenda CONVERSA_PAR,
    pairing engine encontra par,
    atividade executada com sucesso (mock no envio).
    """
    # Setup: 2 chips com status="warming", fase="primeiros_contatos"
    # Mock: enviar_via_chip retorna MessageResult(success=True)
    # Act: planejar_dia → executar atividade
    # Assert: par encontrado, atividade marcada "executada"
```

### Testes Obrigatorios

**Integracao:**
- [ ] `test_ciclo_conversa_par_end_to_end` — fluxo completo com mock de envio
- [ ] `test_ciclo_sem_par_disponivel` — apenas 1 chip → fallback para marcar_lido
- [ ] `test_ciclo_chip_desconectado` — chip evolution desconectado → atividade falha graciosamente

### Definition of Done

- [ ] 3 testes de integracao passando
- [ ] Teste end-to-end cobre o fluxo scheduler → pairing → executor
- [ ] Nenhum acesso real a APIs externas (mocks)

### Estimativa

2 horas
