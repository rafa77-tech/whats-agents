# E05: Racionalizacao de Jobs

**Epico:** Ajustar Frequencias e Criar Janelas
**Estimativa:** 2h
**Dependencias:** E01 (Migrations)

---

## Objetivo

Racionalizar a execucao de jobs para reduzir ruido operacional, criar janelas de execucao e garantir que atendimento nunca compete com batch.

---

## Estado Atual vs Novo

| Job | Frequencia Atual | Frequencia Nova | Justificativa |
|-----|------------------|-----------------|---------------|
| processar_mensagens_agendadas | 1 min | 1 min | Critico, manter |
| processar_campanhas_agendadas | 1 min | Janelas (3x/dia) | Nao precisa ser continuo |
| processar_grupos | 5 min | 15 min | Grupos sao lentos |
| verificar_whatsapp | 1 min | 5 min | Status nao muda rapido |
| verificar_alertas | 15 min | 30 min | Alertas nao urgentes |
| verificar_alertas_grupos | 15 min | 30 min | Idem |
| processar_followups | 10h | 10h, 16h | 2x/dia suficiente |
| processar_handoffs | 10 min | 15 min | Pode ser menos frequente |
| sincronizar_briefing | 1h | 1h | Manter |
| sincronizar_templates | 6h | 6h | Manter |

---

## Janelas de Campanhas

Em vez de rodar campanhas continuamente, criar janelas:

| Janela | Horario | Tipo |
|--------|---------|------|
| Manha | 10:00 | Discovery, Reativacao |
| Pos-almoco | 14:00 | Ofertas |
| Fim tarde | 17:00 | Follow-ups, Feedback |

**Fora dessas janelas:** Campanhas pausadas (apenas atendimento).

---

## Escopo

### Incluido

- [x] Atualizar frequencias no scheduler
- [x] Criar sistema de janelas
- [x] Flag de pausa para campanhas
- [x] Log de execucao para debug

### Excluido

- [ ] Mudancas na logica dos jobs
- [ ] Novos jobs

---

## Tarefas

### T01: Atualizar Scheduler

**Arquivo:** `app/workers/scheduler.py`

```python
JOBS = [
    # =========================================================================
    # CRITICOS - Manter frequencia alta
    # =========================================================================
    {
        "name": "processar_mensagens_agendadas",
        "endpoint": "/jobs/processar-mensagens-agendadas",
        "schedule": "* * * * *",  # A cada minuto
        "categoria": "critico",
    },

    # =========================================================================
    # CAMPANHAS - Janelas especificas
    # =========================================================================
    {
        "name": "processar_campanhas_manha",
        "endpoint": "/jobs/processar-campanhas-agendadas",
        "schedule": "0 10 * * 1-5",  # 10:00 seg-sex
        "categoria": "campanha",
    },
    {
        "name": "processar_campanhas_tarde",
        "endpoint": "/jobs/processar-campanhas-agendadas",
        "schedule": "0 14 * * 1-5",  # 14:00 seg-sex
        "categoria": "campanha",
    },
    {
        "name": "processar_campanhas_fim",
        "endpoint": "/jobs/processar-campanhas-agendadas",
        "schedule": "0 17 * * 1-5",  # 17:00 seg-sex
        "categoria": "campanha",
    },

    # =========================================================================
    # FOLLOW-UPS - 2x por dia
    # =========================================================================
    {
        "name": "processar_followups_manha",
        "endpoint": "/jobs/processar-followups",
        "schedule": "0 10 * * 1-5",  # 10:00 seg-sex
        "categoria": "followup",
    },
    {
        "name": "processar_followups_tarde",
        "endpoint": "/jobs/processar-followups",
        "schedule": "0 16 * * 1-5",  # 16:00 seg-sex
        "categoria": "followup",
    },

    # =========================================================================
    # MONITORAMENTO - Frequencia reduzida
    # =========================================================================
    {
        "name": "verificar_whatsapp",
        "endpoint": "/jobs/verificar-whatsapp",
        "schedule": "*/5 * * * *",  # A cada 5 minutos (era 1)
        "categoria": "monitoramento",
    },
    {
        "name": "verificar_alertas",
        "endpoint": "/jobs/verificar-alertas",
        "schedule": "*/30 * * * *",  # A cada 30 minutos (era 15)
        "categoria": "monitoramento",
    },
    {
        "name": "verificar_alertas_grupos",
        "endpoint": "/jobs/verificar-alertas-grupos",
        "schedule": "*/30 * * * *",  # A cada 30 minutos (era 15)
        "categoria": "monitoramento",
    },

    # =========================================================================
    # GRUPOS - Frequencia reduzida
    # =========================================================================
    {
        "name": "processar_grupos",
        "endpoint": "/jobs/processar-grupos",
        "schedule": "*/15 * * * *",  # A cada 15 minutos (era 5)
        "categoria": "grupos",
    },

    # =========================================================================
    # HANDOFFS - Frequencia reduzida
    # =========================================================================
    {
        "name": "processar_handoffs",
        "endpoint": "/jobs/processar-handoffs",
        "schedule": "*/15 * * * *",  # A cada 15 minutos (era 10)
        "categoria": "handoff",
    },

    # =========================================================================
    # RETOMADAS - 08:00 seg-sex
    # =========================================================================
    {
        "name": "processar_retomadas",
        "endpoint": "/jobs/processar-retomadas",
        "schedule": "0 8 * * 1-5",  # 08:00 seg-sex
        "categoria": "retomada",
    },

    # =========================================================================
    # BATCH/MANUTENCAO - Horarios especificos
    # =========================================================================
    {
        "name": "sincronizar_briefing",
        "endpoint": "/jobs/sincronizar-briefing",
        "schedule": "0 * * * *",  # A cada hora
        "categoria": "sync",
    },
    {
        "name": "sincronizar_templates",
        "endpoint": "/jobs/sync-templates",
        "schedule": "0 6 * * *",  # 06:00
        "categoria": "sync",
    },
    {
        "name": "doctor_state_manutencao_diaria",
        "endpoint": "/jobs/doctor-state-manutencao-diaria",
        "schedule": "0 3 * * *",  # 03:00
        "categoria": "manutencao",
    },
    {
        "name": "avaliar_conversas_pendentes",
        "endpoint": "/jobs/avaliar-conversas-pendentes",
        "schedule": "0 2 * * *",  # 02:00
        "categoria": "manutencao",
    },
    {
        "name": "limpar_grupos_finalizados",
        "endpoint": "/jobs/limpar-grupos-finalizados",
        "schedule": "0 3 * * *",  # 03:00
        "categoria": "manutencao",
    },
    {
        "name": "consolidar_metricas_grupos",
        "endpoint": "/jobs/consolidar-metricas-grupos",
        "schedule": "0 1 * * *",  # 01:00
        "categoria": "manutencao",
    },

    # =========================================================================
    # REPORTS - Manter
    # =========================================================================
    {
        "name": "report_manha",
        "endpoint": "/jobs/report-periodo?tipo=manha",
        "schedule": "0 10 * * *",
        "categoria": "report",
    },
    {
        "name": "report_almoco",
        "endpoint": "/jobs/report-periodo?tipo=almoco",
        "schedule": "0 13 * * *",
        "categoria": "report",
    },
    {
        "name": "report_tarde",
        "endpoint": "/jobs/report-periodo?tipo=tarde",
        "schedule": "0 17 * * *",
        "categoria": "report",
    },
    {
        "name": "report_fim_dia",
        "endpoint": "/jobs/report-periodo?tipo=fim_dia",
        "schedule": "0 20 * * *",
        "categoria": "report",
    },
    {
        "name": "report_semanal",
        "endpoint": "/jobs/report-semanal",
        "schedule": "0 9 * * 1",  # Segunda 09:00
        "categoria": "report",
    },

    # =========================================================================
    # CONFIRMACAO PLANTAO
    # =========================================================================
    {
        "name": "processar_confirmacao_plantao",
        "endpoint": "/jobs/processar-confirmacao-plantao",
        "schedule": "0 * * * *",  # A cada hora
        "categoria": "confirmacao",
    },
]
```

**DoD:**
- [ ] Scheduler atualizado com novas frequencias
- [ ] Campanhas em janelas (10h, 14h, 17h)
- [ ] Follow-ups 2x/dia
- [ ] Monitoramento reduzido
- [ ] Categorias definidas

---

### T02: Documentar Mudancas

**Arquivo:** `docs/jobs-schedule.md`

```markdown
# Schedule de Jobs

## Visao Geral

| Categoria | Jobs | Frequencia |
|-----------|------|------------|
| Critico | 1 | A cada minuto |
| Campanha | 3 | Janelas 10h, 14h, 17h |
| Follow-up | 2 | 10h e 16h |
| Monitoramento | 3 | 5-30 min |
| Grupos | 1 | 15 min |
| Handoff | 1 | 15 min |
| Sync | 2 | 1h e 6h |
| Manutencao | 4 | Madrugada |
| Report | 5 | Horarios fixos |

## Timeline Diario

```
06:00 - sync_templates
08:00 - processar_retomadas
10:00 - campanhas_manha, followups_manha, report_manha
13:00 - report_almoco
14:00 - campanhas_tarde
16:00 - followups_tarde
17:00 - campanhas_fim, report_tarde
20:00 - report_fim_dia

01:00 - consolidar_metricas
02:00 - avaliar_conversas
03:00 - manutencao, limpar_grupos

Continuo:
- mensagens_agendadas (1 min)
- verificar_whatsapp (5 min)
- grupos (15 min)
- handoffs (15 min)
- alertas (30 min)
- briefing (1h)
```

## Reducao de Ruido

Antes: ~60 execucoes/hora
Depois: ~20 execucoes/hora

**Economia: 67% menos wake-ups**
```

**DoD:**
- [ ] Documentacao criada
- [ ] Timeline visual
- [ ] Comparativo antes/depois

---

## Validacao

### Verificar Novas Frequencias

```bash
# Listar jobs configurados
uv run python -c "
from app.workers.scheduler import JOBS

for job in JOBS:
    print(f\"{job['name']:40} {job['schedule']:20} {job.get('categoria', 'N/A')}\")
"
```

### Query de Execucoes

```sql
-- Execucoes por categoria (hoje)
SELECT
    -- Extrair categoria do job_name
    CASE
        WHEN job_name LIKE '%campanha%' THEN 'campanha'
        WHEN job_name LIKE '%followup%' THEN 'followup'
        WHEN job_name LIKE '%grupo%' THEN 'grupos'
        ELSE 'outros'
    END as categoria,
    COUNT(*) as execucoes,
    COUNT(*) / 24.0 as por_hora
FROM job_executions
WHERE executed_at >= CURRENT_DATE
GROUP BY 1
ORDER BY execucoes DESC;
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Scheduler atualizado
- [ ] Campanhas em janelas
- [ ] Follow-ups 2x/dia
- [ ] Monitoramento reduzido
- [ ] Zero quebras em jobs criticos

### Qualidade

- [ ] Documentacao atualizada
- [ ] Categorias claras
- [ ] Logs indicam categoria

### Performance

- [ ] Reducao de 50%+ em wake-ups
- [ ] Atendimento nao impactado

---

*Epico criado em 29/12/2025*
