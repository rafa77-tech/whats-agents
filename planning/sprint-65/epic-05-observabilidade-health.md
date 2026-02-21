# EPICO 05: Observabilidade & Health Check

## Prioridade: P2 (Medio)

## Contexto

O warmup system nao tem mecanismo de health check unificado. O unico jeito de saber se esta funcionando e olhar manualmente no banco. Este epico adiciona um endpoint `/warmer/health` que retorna status real do pool e taxa de sucesso por tipo de atividade, alem de metricas estruturadas nos logs.

## Escopo

- **Incluido**: Endpoint /warmer/health, metricas por tipo de atividade, log estruturado, daily summary
- **Excluido**: Dashboard visual (seria Sprint futura), alertas Slack automaticos (ja existe early_warning)

## Dependencias

- **Epics 01-03** — Sistema deve estar funcionando para metricas terem sentido

---

## Tarefa 1: Endpoint /warmer/health

### Objetivo

Criar endpoint que retorna diagnostico completo do pool de warmup em um unico request.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/api/routes/warmer.py` |
| Criar | `app/services/warmer/health.py` |

### Implementacao

```python
# app/services/warmer/health.py

async def diagnostico_warmup() -> dict:
    """
    Retorna diagnostico completo do pool de warmup.

    Returns:
        Dict com:
        - pool: resumo de chips por status/fase
        - atividades_hoje: taxa de sucesso por tipo
        - alertas_ativos: contagem de alertas nao resolvidos
        - health_status: "healthy" | "degraded" | "critical"
    """
    # 1. Pool summary
    pool = supabase.rpc("_warmup_pool_summary").execute()

    # 2. Atividades de hoje
    atividades = supabase.table("warmup_schedule").select(
        "tipo, status"
    ).gte("created_at", hoje_inicio()).execute()

    # Calcular taxa de sucesso por tipo
    por_tipo = {}
    for a in atividades.data or []:
        tipo = a["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = {"total": 0, "sucesso": 0, "falha": 0}
        por_tipo[tipo]["total"] += 1
        if a["status"] == "executada":
            por_tipo[tipo]["sucesso"] += 1
        elif a["status"] == "falhou":
            por_tipo[tipo]["falha"] += 1

    for tipo, stats in por_tipo.items():
        stats["taxa_sucesso"] = (
            round(stats["sucesso"] / stats["total"] * 100, 1)
            if stats["total"] > 0 else 0
        )

    # 3. Alertas ativos
    alertas = supabase.table("chip_alerts").select(
        "id", count="exact"
    ).eq("resolved", False).execute()

    # 4. Determinar health status
    taxa_conversa_par = por_tipo.get("CONVERSA_PAR", {}).get("taxa_sucesso", 0)
    chips_warming = len([...])  # chips em warming/active

    if taxa_conversa_par >= 80 and chips_warming > 0:
        health = "healthy"
    elif taxa_conversa_par >= 50:
        health = "degraded"
    else:
        health = "critical"

    return {
        "health_status": health,
        "pool": pool,
        "atividades_hoje": por_tipo,
        "alertas_ativos": alertas.count or 0,
        "timestamp": agora_brasilia().isoformat(),
    }
```

Rota em `warmer.py`:

```python
@router.get("/health")
async def warmer_health():
    """Health check do sistema de warmup."""
    from app.services.warmer.health import diagnostico_warmup
    return await diagnostico_warmup()
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_diagnostico_healthy` — pool com chips ok e taxa >80% retorna "healthy"
- [ ] `test_diagnostico_degraded` — taxa entre 50-80% retorna "degraded"
- [ ] `test_diagnostico_critical` — taxa <50% ou 0 chips retorna "critical"
- [ ] `test_diagnostico_sem_atividades` — sem atividades hoje nao quebra

**Integracao:**
- [ ] `test_endpoint_warmer_health` — GET /warmer/health retorna 200 com estrutura esperada

### Definition of Done

- [ ] GET /warmer/health retorna JSON com health_status, pool, atividades_hoje, alertas_ativos
- [ ] health_status reflete estado real: healthy (>80% CONVERSA_PAR), degraded (50-80%), critical (<50%)
- [ ] Testes passando (5+)
- [ ] Endpoint documentado na rota com docstring

### Estimativa

3 horas

---

## Tarefa 2: Metricas estruturadas nos logs do ciclo

### Objetivo

Adicionar log estruturado ao final de cada ciclo_warmup com resumo de execucao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/orchestrator.py` |

### Implementacao

Ao final de `ciclo_warmup()`, antes do log de conclusao:

```python
# Dentro de ciclo_warmup(), apos executar todas as atividades:
executadas = sum(1 for a in resultados if a.get("success"))
falhas = sum(1 for a in resultados if not a.get("success"))
total = len(resultados)

logger.info(
    f"[Orchestrator] Ciclo concluido: "
    f"{executadas}/{total} OK, {falhas} falhas, "
    f"{planejados} auto-planejadas",
    extra={
        "warmup_cycle": {
            "atividades_total": total,
            "atividades_ok": executadas,
            "atividades_falha": falhas,
            "auto_planejadas": planejados,
            "transicoes": transicoes_count,
        }
    }
)
```

Para isso, coletar resultados durante o loop de execucao:

```python
# Substituir o loop atual:
resultados = []
for atividade in atividades:
    try:
        resultado = await self.executar_atividade(atividade)
        resultados.append(resultado)
    except Exception as e:
        logger.error(f"[Orchestrator] Erro: {e}", exc_info=True)
        resultados.append({"success": False, "error": str(e)})
    await asyncio.sleep(2)
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_ciclo_loga_resumo_com_contagem` — verifica que log de conclusao inclui contagens
- [ ] `test_ciclo_loga_zero_quando_vazio` — sem atividades, log mostra 0/0

### Definition of Done

- [ ] Log de conclusao do ciclo inclui total/ok/falha/planejadas/transicoes
- [ ] Resultados coletados durante execucao (nao descartados)
- [ ] Testes passando (2+)

### Estimativa

1 hora

---

## Tarefa 3: Incluir warming_day no status do pool

### Objetivo

Adicionar informacao de warming_day no endpoint existente `/warmer/status` e no novo `/warmer/health`.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/orchestrator.py` (metodo obter_status_pool) |

### Implementacao

No `obter_status_pool()`, incluir warming_day nos dados retornados por chip:

```python
# Adicionar ao select:
.select("id, telefone, status, fase_warmup, trust_score, trust_level, "
        "warming_day, msgs_enviadas_hoje, evolution_connected, provider")
```

E incluir no resumo:

```python
# No retorno:
"chips": [
    {
        "telefone_masked": chip["telefone"][-4:],
        "status": chip["status"],
        "fase": chip["fase_warmup"],
        "warming_day": chip.get("warming_day", 0),
        "trust": chip.get("trust_score", 0),
        "msgs_hoje": chip.get("msgs_enviadas_hoje", 0),
        "connected": chip.get("evolution_connected", False),
    }
    for chip in chips
],
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_status_pool_inclui_warming_day` — warming_day presente no retorno de cada chip

### Definition of Done

- [ ] warming_day visivel em /warmer/status e /warmer/health
- [ ] Teste passando

### Estimativa

30 minutos
