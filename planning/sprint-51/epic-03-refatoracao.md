# Epic 3: Refatoracao e Observabilidade

**Status:** 🔴 Nao Iniciada
**Prioridade:** P1 - Alta

---

## Objetivo

Refatorar o pipeline para:
1. Clareza de codigo e responsabilidades
2. Observabilidade completa
3. Prevencao de regressoes futuras

---

## Stories

### S51.E3.1 - Unificar Logica de Atualizacao

**Objetivo:** Garantir que atualizacoes de estado sejam centralizadas

**Problema Atual:**
- `classificador.py` tem funcoes de atualizacao
- `pipeline_worker.py` nao as utiliza
- `fila.py` tem sincronizacao parcial

**Solucao:**
Criar um unico ponto de atualizacao que seja chamado consistentemente.

**Tarefas:**
1. Criar `app/services/grupos/state_manager.py`
2. Centralizar todas as atualizacoes de estado
3. Refatorar pipeline_worker para usar state_manager
4. Deprecar funcoes duplicadas

**Codigo:**
```python
# app/services/grupos/state_manager.py

class GroupMessageStateManager:
    """Gerencia estado de mensagens de grupo de forma atomica."""

    async def marcar_heuristica_passou(
        self,
        mensagem_id: UUID,
        score: float,
        keywords: list[str]
    ) -> None:
        """Atualiza mensagem apos passar heuristica."""
        await supabase.table("mensagens_grupo").update({
            "passou_heuristica": True,
            "score_heuristica": score,
            "keywords_encontradas": keywords,
            "status": "heuristica_passou",
            "processado_em": datetime.now(UTC).isoformat(),
        }).eq("id", str(mensagem_id)).execute()

    async def marcar_heuristica_rejeitou(
        self,
        mensagem_id: UUID,
        score: float,
        motivo: str
    ) -> None:
        """Atualiza mensagem rejeitada pela heuristica."""
        await supabase.table("mensagens_grupo").update({
            "passou_heuristica": False,
            "score_heuristica": score,
            "motivo_descarte": motivo,
            "status": "heuristica_rejeitou",
            "processado_em": datetime.now(UTC).isoformat(),
        }).eq("id", str(mensagem_id)).execute()

    async def marcar_classificada(
        self,
        mensagem_id: UUID,
        eh_oferta: bool,
        confianca: float
    ) -> None:
        """Atualiza mensagem apos classificacao LLM."""
        status = "classificada_oferta" if eh_oferta else "classificada_nao_oferta"
        await supabase.table("mensagens_grupo").update({
            "eh_oferta": eh_oferta,
            "confianca_classificacao": confianca,
            "status": status,
            "processado_em": datetime.now(UTC).isoformat(),
        }).eq("id", str(mensagem_id)).execute()
```

**DoD:**
- [ ] StateManager criado
- [ ] pipeline_worker refatorado
- [ ] Testes de integracao
- [ ] Funcoes antigas deprecadas

---

### S51.E3.2 - Adicionar Logs Estruturados

**Objetivo:** Ter visibilidade completa do pipeline

**Tarefas:**
1. Adicionar logs em cada estagio
2. Incluir contexto (mensagem_id, grupo_id, etc)
3. Logar decisoes (score, acao, motivo)

**Formato:**
```python
logger.info(
    "pipeline_stage_completed",
    extra={
        "stage": "heuristica",
        "mensagem_id": str(mensagem_id),
        "grupo_id": str(grupo_id),
        "score": score,
        "passou": score >= 0.5,
        "keywords": keywords_encontradas,
        "proxima_acao": acao,
        "duracao_ms": duracao,
    }
)
```

**DoD:**
- [ ] Logs em todos os estagios
- [ ] Formato consistente
- [ ] Contexto completo

---

### S51.E3.3 - Criar Metricas de Pipeline

**Objetivo:** Monitorar saude do pipeline em tempo real

**Metricas:**
1. `grupos_mensagens_recebidas_total` (counter)
2. `grupos_heuristica_passou_total` (counter)
3. `grupos_heuristica_rejeitou_total` (counter)
4. `grupos_classificacao_oferta_total` (counter)
5. `grupos_vagas_extraidas_total` (counter)
6. `grupos_vagas_importadas_total` (counter)
7. `grupos_pipeline_duracao_seconds` (histogram)
8. `grupos_fila_tamanho` (gauge)

**Tarefas:**
1. Adicionar instrumentacao prometheus
2. Exportar metricas em /metrics
3. Criar dashboard Grafana

**DoD:**
- [ ] Metricas instrumentadas
- [ ] Endpoint /metrics funcionando
- [ ] Dashboard criado

---

### S51.E3.4 - Criar Alertas de Inconsistencia

**Objetivo:** Detectar automaticamente quando dados ficam inconsistentes

**Alertas:**
1. `grupos_vagas_sem_classificacao` - Vagas criadas de mensagens sem eh_oferta
2. `grupos_pipeline_bloqueado` - Fila sem progresso por > 1h
3. `grupos_taxa_importacao_baixa` - Taxa < 1% por > 24h

**Implementacao:**
```python
# Verificacao periodica (worker ou cron)
async def verificar_integridade_pipeline():
    # Vagas sem classificacao
    vagas_orfas = await supabase.rpc(
        "count_vagas_sem_classificacao"
    ).execute()

    if vagas_orfas.data > 0:
        await alertar_slack(
            "🚨 Encontradas {} vagas sem classificacao".format(vagas_orfas.data)
        )
```

**DoD:**
- [ ] Verificacoes implementadas
- [ ] Alertas configurados
- [ ] Documentacao de resposta

---

### S51.E3.5 - Documentar Arquitetura do Pipeline

**Objetivo:** Ter documentacao clara para manutencao futura

**Tarefas:**
1. Criar diagrama de arquitetura
2. Documentar cada estagio
3. Documentar decisoes de design
4. Criar runbook de troubleshooting

**Entregaveis:**
- `docs/arquitetura/pipeline-grupos.md`
- Diagrama Mermaid do fluxo
- Runbook de operacao

**DoD:**
- [ ] Documentacao criada
- [ ] Diagrama atualizado
- [ ] Runbook validado

---

## Criterios de Aceite da Sprint

Ao final da Sprint 51, devemos ter:

1. ✅ **Dados Corretos**
   - Dashboard mostrando numeros reais
   - Campos `passou_heuristica` e `eh_oferta` preenchidos
   - Vagas sendo importadas

2. ✅ **Codigo Limpo**
   - StateManager centralizado
   - Responsabilidades claras
   - Sem codigo morto

3. ✅ **Observabilidade**
   - Logs estruturados
   - Metricas exportadas
   - Alertas configurados

4. ✅ **Documentacao**
   - Arquitetura documentada
   - Runbook atualizado
   - Diagramas claros
