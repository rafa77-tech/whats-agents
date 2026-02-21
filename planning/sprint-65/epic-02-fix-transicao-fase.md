# EPICO 02: Fix Transicao de Fase

## Prioridade: P0 (Critico)

## Contexto

Chips nao progridem de fase porque: (a) warming_day nunca e atualizado, (b) idade e calculada com created_at ao inves de warming_started_at, e (c) fases a partir de expansao exigem grupos_count >= 1 mas ENTRAR_GRUPO e stub. Apos Epic 01 desbloquear CONVERSA_PAR, os chips precisam conseguir progredir.

## Escopo

- **Incluido**: Fix warming_day, fix timestamp, relaxar criterios de grupos, testes
- **Excluido**: Reimplementar stubs de grupo (sprint futura), mudancas na logica de trust score

## Dependencias

- **Epic 01** — CONVERSA_PAR precisa funcionar para gerar metricas que habilitam transicao

---

## Tarefa 1: Fix calculo de idade na transicao

### Objetivo

Usar `warming_started_at` ao inves de `created_at` para calcular dias de warmup.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/orchestrator.py` |

### Implementacao

Linha 271 de `orchestrator.py`:

```python
# ANTES (bugado):
created_at = datetime.fromisoformat(chip["created_at"].replace("Z", "+00:00"))
idade_dias = (agora_brasilia() - created_at).days

# DEPOIS (corrigido):
warming_started = chip.get("warming_started_at")
if not warming_started:
    # Fallback: se warming_started_at nao existe, usar fase_iniciada_em ou created_at
    warming_started = chip.get("fase_iniciada_em") or chip.get("created_at")

warming_started_dt = datetime.fromisoformat(
    str(warming_started).replace("Z", "+00:00")
)
idade_dias = (agora_brasilia() - warming_started_dt).days
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_verificar_transicao_usa_warming_started_at` — chip criado ha 60 dias mas warmup iniciado ha 2 dias nao transiciona
- [ ] `test_verificar_transicao_fallback_fase_iniciada_em` — sem warming_started_at usa fase_iniciada_em
- [ ] `test_verificar_transicao_fallback_created_at` — sem ambos usa created_at
- [ ] `test_verificar_transicao_dias_minimos_atendidos` — chip com dias suficientes transiciona

### Definition of Done

- [ ] `warming_started_at` usado como referencia primaria
- [ ] Fallback chain: warming_started_at → fase_iniciada_em → created_at
- [ ] Testes passando (4+)
- [ ] Cobertura >90% no metodo `verificar_transicao`

### Estimativa

1.5 horas

---

## Tarefa 2: Implementar atualizacao de warming_day

### Objetivo

Calcular e atualizar `warming_day` a cada ciclo de warmup, permitindo que o sistema saiba em que dia de aquecimento cada chip esta.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/orchestrator.py` |

### Implementacao

Adicionar metodo `_atualizar_warming_days()` no orchestrator e chamar no inicio do `ciclo_warmup()`:

```python
async def _atualizar_warming_days(self):
    """Atualiza warming_day para todos os chips em warmup."""
    chips_result = (
        supabase.table("chips")
        .select("id, warming_started_at")
        .in_("status", ["warming", "active"])
        .not_.is_("warming_started_at", "null")
        .execute()
    )

    agora = agora_brasilia()
    for chip in chips_result.data or []:
        warming_started = datetime.fromisoformat(
            chip["warming_started_at"].replace("Z", "+00:00")
        )
        warming_day = (agora - warming_started).days

        supabase.table("chips").update(
            {"warming_day": warming_day}
        ).eq("id", chip["id"]).execute()

    logger.info(
        f"[Orchestrator] warming_day atualizado para "
        f"{len(chips_result.data or [])} chips"
    )
```

Chamar no `ciclo_warmup()` logo apos `_garantir_planejamento_diario()`:

```python
async def ciclo_warmup(self):
    async with self._ciclo_lock:
        # 1. Garantir planejamento
        planejados = await self._garantir_planejamento_diario()

        # 2. Atualizar warming_day (NOVO)
        await self._atualizar_warming_days()

        # 3. Buscar e executar atividades...
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_atualizar_warming_days_calcula_corretamente` — chip iniciado ha 5 dias recebe warming_day=5
- [ ] `test_atualizar_warming_days_ignora_sem_warming_started` — chip sem warming_started_at e ignorado
- [ ] `test_atualizar_warming_days_apenas_warming_active` — chips provisioned/degraded nao atualizados

**Integracao:**
- [ ] `test_ciclo_warmup_atualiza_warming_days` — apos ciclo, warming_day reflete dias reais

### Definition of Done

- [ ] `_atualizar_warming_days()` implementado e integrado no ciclo
- [ ] warming_day atualizado a cada ciclo de 5 minutos
- [ ] Testes passando (4+)
- [ ] Log informa quantos chips atualizados

### Estimativa

2 horas

---

## Tarefa 3: Relaxar criterios de grupos nas transicoes

### Objetivo

Remover `grupos_min` dos criterios de transicao enquanto ENTRAR_GRUPO nao estiver implementado. Sem isso, nenhum chip consegue passar de expansao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/orchestrator.py` |

### Implementacao

Nas linhas 78-114, zerar `grupos_min` em todas as fases:

```python
# ANTES:
FaseWarmup.EXPANSAO: CriteriosTransicao(
    dias_minimos=7,
    msgs_enviadas_min=50,
    msgs_recebidas_min=25,
    taxa_resposta_min=0.4,
    trust_score_min=55,
    conversas_bidirecionais_min=10,
    grupos_min=1,  # ← bloqueia transicao
),

# DEPOIS:
FaseWarmup.EXPANSAO: CriteriosTransicao(
    dias_minimos=7,
    msgs_enviadas_min=50,
    msgs_recebidas_min=25,
    taxa_resposta_min=0.4,
    trust_score_min=55,
    conversas_bidirecionais_min=10,
    grupos_min=0,  # Relaxado: ENTRAR_GRUPO nao implementado (ver Sprint XX)
),
```

Aplicar o mesmo para PRE_OPERACAO (grupos_min=2→0), TESTE_GRADUACAO (3→0), OPERACAO (3→0).

**Compensacao:** Para manter rigor, aumentar `conversas_bidirecionais_min` em +5 nas fases afetadas:
- EXPANSAO: 10 → 12
- PRE_OPERACAO: 15 → 18
- TESTE_GRADUACAO: 20 → 23
- OPERACAO: 25 → 28

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_transicao_expansao_sem_grupos` — chip sem grupos mas com conversas bidirecionais suficientes transiciona
- [ ] `test_transicao_pre_operacao_sem_grupos` — idem para pre_operacao
- [ ] `test_criterios_compensados` — conversas_bidirecionais_min aumentado nas fases afetadas

### Definition of Done

- [ ] `grupos_min=0` em todas as fases
- [ ] `conversas_bidirecionais_min` compensado (+5 em fases com grupos_min anterior > 0)
- [ ] Comentario explicativo em cada mudanca referenciando sprint futura
- [ ] Testes passando (3+)

### Estimativa

1 hora

---

## Tarefa 4: Teste de integracao do fluxo de transicao

### Objetivo

Validar que um chip consegue progredir de setup ate primeiros_contatos com as correcoes aplicadas.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `tests/services/warmer/test_transicao_integration.py` |

### Implementacao

```python
async def test_transicao_setup_para_primeiros_contatos():
    """
    Cenario: Chip em setup com warming_started_at ha 2 dias,
    metricas suficientes (msgs, trust, conversas).
    Espera: verificar_transicao retorna "primeiros_contatos".
    """

async def test_transicao_bloqueada_por_dias_insuficientes():
    """
    Cenario: Chip com warming_started_at hoje (dia 0),
    metricas ok mas dias_minimos nao atingido.
    Espera: verificar_transicao retorna None.
    """

async def test_transicao_bloqueada_por_metricas():
    """
    Cenario: Chip com dias suficientes mas msgs_enviadas_total=0.
    Espera: verificar_transicao retorna None.
    """
```

### Testes Obrigatorios

**Integracao:**
- [ ] `test_transicao_setup_para_primeiros_contatos` — transicao valida
- [ ] `test_transicao_bloqueada_por_dias_insuficientes` — sem dias suficientes
- [ ] `test_transicao_bloqueada_por_metricas` — sem metricas suficientes
- [ ] `test_transicao_nao_acontece_em_operacao` — chip em operacao retorna None

### Definition of Done

- [ ] 4 testes de integracao passando
- [ ] Fluxo cobre validacao de dias, metricas e fase terminal

### Estimativa

1.5 horas
