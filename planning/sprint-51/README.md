# Sprint 51 - Pipeline de Grupos: Revisao Arquitetural Completa

**Inicio:** 02/02/2026
**Chip em foco:** 5511916175810 (Revoluna)
**Status:** 🔄 Em Andamento

---

## Objetivo Estrategico

Este pipeline e **critico para o negocio**. Ele alimenta:
- Inteligencia de mercado (precos, tendencias, demanda)
- Analise de concorrencia
- Identificacao de oportunidades
- Metricas de mercado para tomada de decisao

**Esta sprint vai alem de corrigir bugs** - e uma revisao completa para validar se o modelo funciona e e sustentavel.

---

## Protecao do Chip de Grupos (CRITICO!)

O chip **5511916175810** tem acesso a **174 grupos** de WhatsApp. Esse e um ativo valioso que **nao pode ser perdido**.

### Regras de Protecao

| Regra | Descricao |
|-------|-----------|
| **READ-ONLY** | Chip de grupos NUNCA envia mensagens |
| **Sem Julia** | Julia NAO pode usar este chip para prospectar |
| **Isolado** | Deve estar isolado do pool de chips ativos |
| **Monitorado** | Alertas se houver tentativa de envio |

### Implementacao Necessaria

1. **Flag no banco:** `tipo = 'escuta'` ou `modo = 'readonly'`
2. **Validacao no envio:** Bloquear envio se chip for de escuta
3. **Alerta:** Notificar se alguem tentar enviar por este chip
4. **Documentacao:** Deixar claro que este chip e especial

---

## Problemas Identificados

### Problema 1: Extrator v2 Incompleto (URGENTE)

**100% das vagas descartadas** por falta de especialidade.

```
Mensagem: "VAGA PARA MÉDICO - GINECOLOGIA E OBSTETRÍCIA"
Extraido: especialidade_raw = NULL
Resultado: DESCARTADA
```

**Causa:** `extrator_especialidades.py` nao existe. O parser identifica secoes de especialidade mas ninguem as processa.

**Impacto:** Pipeline parado desde 26/01 (7 dias sem importacoes).

### Problema 2: Campos de Classificacao NULL

Campos `passou_heuristica` e `eh_oferta` nunca sao atualizados.

**Causa:** `pipeline_worker.py` calcula os valores mas nao chama as funcoes de atualizacao que existem em `classificador.py`.

**Impacto:** Dashboard mostra zeros, impossivel auditar decisoes.

### Problema 3: Falta de Observabilidade

- Sem logs estruturados por estagio
- Sem metricas de conversao do pipeline
- Sem alertas de anomalias
- Impossivel diagnosticar problemas rapidamente

---

## Perguntas a Responder (Revisao Arquitetural)

### Sobre o Modelo

1. **O pipeline faz sentido?** Mensagem → Heuristica → LLM → Extracao → Normalizacao → Dedup → Import
2. **Vale a pena usar LLM para classificacao?** Ou a heuristica e suficiente?
3. **A taxa de conversao e aceitavel?** Hoje: 3.5% importadas, 50% duplicadas, 44% descartadas
4. **O extrator v2 e melhor que o v1?** Ou devemos reverter?

### Sobre Operacao

5. **Como garantir que o chip de grupos nao seja banido?**
6. **Como monitorar saude do pipeline em tempo real?**
7. **Qual o SLA aceitavel?** (tempo entre mensagem e importacao)
8. **Como detectar regressoes automaticamente?**

### Sobre Dados

9. **Os dados extraidos sao uteis?** Hospital, especialidade, valor, data
10. **Estamos perdendo informacoes importantes?** Contato, observacoes, requisitos
11. **A deduplicacao esta correta?** 50% duplicadas parece muito

---

## Epicos

### Epic 1: Investigacao Profunda ✅
**Arquivo:** `epic-01-investigacao.md`
- Mapear fluxo completo
- Identificar bugs
- Documentar estado atual

### Epic 2: Correcoes Criticas ✅ CONCLUIDO
**Arquivo:** `epic-02-correcoes.md`
- ✅ S51.E2.0: Implementar extracao de especialidades
- ✅ S51.E2.1: Corrigir atualizacao de heuristica
- ✅ S51.E2.2: Corrigir atualizacao de classificacao LLM
- ✅ S51.E2.3: Corrigir normalizacao de especialidades (aliases)
- S51.E2.4: Backfill de dados historicos (pendente)

### Epic 3: Protecao do Chip de Grupos ✅ PARCIAL
**Arquivo:** `epic-03-protecao-chip.md`
- ✅ S51.E3.1: Chip tipo='listener', flags de envio desabilitados
- S51.E3.2: Bloqueio no codigo (pendente)
- S51.E3.3: Alertas de tentativa de envio (pendente)
- S51.E3.4: Documentacao e treinamento (pendente)

### Epic 6: Pipeline v3 (Planejamento) 📋
**Arquivo:** `epic-06-pipeline-v3.md`
- Arquitetura simplificada de 4 estagios
- LLM unificado (classifica + extrai)
- Dedup precoce antes de gastar tokens
- Observabilidade completa

### Epic 4: Observabilidade e Monitoramento
**Arquivo:** `epic-04-observabilidade.md`
- S51.E4.1: Logs estruturados por estagio
- S51.E4.2: Metricas do pipeline (Prometheus)
- S51.E4.3: Dashboard de saude do pipeline
- S51.E4.4: Alertas de anomalias

### Epic 5: Validacao do Modelo
**Arquivo:** `epic-05-validacao-modelo.md`
- S51.E5.1: Analise de taxa de conversao
- S51.E5.2: Comparacao v1 vs v2
- S51.E5.3: Avaliacao de qualidade dos dados
- S51.E5.4: Recomendacoes de ajustes

---

## Metricas do Chip 5810

| Metrica | Valor |
|---------|-------|
| Telefone | 5511916175810 |
| Instance | Revoluna |
| Status | degraded |
| Fase | operacao |
| Tipo | julia (DEVE SER 'escuta') |
| Total Grupos | 174 |
| Total Mensagens | 22.514 |
| Vagas Detectadas | 56.461 |
| Vagas Importadas | 2.004 (3.5%) |
| Ultima Importacao | 26/01/2026 |

---

## Definition of Done

### Correcoes (P0)
- [x] Especialidades sendo extraidas (extrator_especialidades.py)
- [x] Aliases normalizados para especialidades (55 inseridos)
- [x] Heuristica salva no banco (pipeline_worker.py)
- [x] Classificacao LLM salva no banco (pipeline_worker.py)
- [x] Coluna motivo_descarte adicionada (migration 03/02/2026)
- [x] Vagas sendo importadas novamente ✅ FUNCIONANDO
- [x] Chip 5810 protegido contra envio (tipo='listener')

### Observabilidade (P1)
- [ ] Logs estruturados em todos os estagios
- [ ] Metricas exportadas
- [ ] Alertas configurados

### Validacao (P2)
- [ ] Relatorio de analise do modelo
- [ ] Recomendacoes documentadas
- [ ] Decisao sobre v1 vs v2

### Pipeline v3 (Futuro)
- [x] Arquitetura planejada (epic-06-pipeline-v3.md)
- [ ] Implementacao

---

## Riscos

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Ban do chip 5810 | Media | Critico | Implementar protecao read-only |
| Quebrar pipeline em prod | Media | Alto | Testes antes de deploy |
| Dados historicos perdidos | Baixa | Medio | Backfill apos correcoes |
