# Sprint 51 - Pipeline de Grupos WhatsApp: Investigacao e Refatoracao

**Inicio:** 02/02/2026
**Chip em foco:** 5511916175810 (Revoluna)
**Status:** 🔄 Em Andamento

---

## Resumo Executivo

**3 problemas criticos identificados:**

1. **Extrator v2 nao captura especialidade** → 100% das vagas descartadas
2. **Campos de classificacao nao atualizados** → Dashboard mostra zeros
3. **Pipeline parado desde 26/01** → Nenhuma importacao em 7 dias

---

## Contexto

Durante analise do dashboard de grupos (/grupos), foram identificadas inconsistencias graves nos dados do pipeline:

### Problema 1: Dashboard Mostra Zeros

| Metrica | Valor no Dashboard | Realidade |
|---------|-------------------|-----------|
| Mensagens Recebidas | 1.381 | OK |
| Passou Heuristica | 0 | ❌ Campos NULL |
| Classificadas como Oferta | 0 | ❌ Campos NULL |
| Vagas Extraidas | 3.503 | OK (mas sem especialidade) |
| Dados Minimos OK | 3.503 (100%) | OK |
| Vagas Importadas | 0 | ❌ Todas descartadas |

### Problema 2: Campos de Classificacao NULL

- **22.514 mensagens** com `passou_heuristica = NULL`
- **22.514 mensagens** com `eh_oferta = NULL`
- Campos existem mas `pipeline_worker.py` **nao os atualiza**

### Problema 3: Extrator Falha em Capturar Especialidade (CRITICO!)

**100% das vagas das ultimas 24h descartadas** com motivo:
```
validacao_falhou: especialidade_id ausente
```

Exemplo de mensagem com especialidade clara:
```
🔔 *VAGA PARA MÉDICO(A) - GINECOLOGIA E OBSTETRÍCIA*
📍 *Cianorte - PR*
...
```

Mas a vaga extraida tem `especialidade_raw = NULL`!

### Causa Raiz Confirmada

O pipeline atual:
1. ✅ Recebe mensagem e salva em `mensagens_grupo`
2. ✅ Calcula score de heuristica
3. ❌ **NAO atualiza** `passou_heuristica` na mensagem
4. ✅ Chama LLM para classificacao (se necessario)
5. ❌ **NAO atualiza** `eh_oferta` na mensagem
6. ⚠️ Extrai vagas mas **SEM especialidade**
7. ❌ Vagas descartadas por falta de `especialidade_id`

---

## Objetivo da Sprint

1. **Entender completamente** o pipeline atual de grupos
2. **Corrigir** a sincronizacao de campos (`passou_heuristica`, `eh_oferta`)
3. **Investigar** por que vagas nao estao sendo importadas
4. **Refatorar** para garantir integridade de dados
5. **Adicionar observabilidade** para monitoramento do pipeline

---

## Metricas do Chip 5810

| Metrica | Valor |
|---------|-------|
| Telefone | 5511916175810 |
| Instance | Revoluna |
| Status | degraded |
| Fase | operacao |
| Tipo | julia |
| Total Grupos | 174 |
| Total Mensagens | 22.514 |
| Total Ofertas Detectadas | 56.461 |
| Total Vagas Importadas | 2.004 |
| Taxa Importacao | 3.5% |

---

## Epicos

### Epic 1: Investigacao Profunda
**Arquivo:** `epic-01-investigacao.md`
- Mapear fluxo completo do pipeline
- Identificar pontos de falha
- Documentar estado atual

### Epic 2: Correcoes Criticas
**Arquivo:** `epic-02-correcoes.md`
- Corrigir sincronizacao de campos
- Corrigir fluxo de importacao
- Adicionar validacoes

### Epic 3: Refatoracao e Observabilidade
**Arquivo:** `epic-03-refatoracao.md`
- Refatorar pipeline para clareza
- Adicionar metricas e logs
- Criar alertas de inconsistencia

---

## Arquivos-Chave do Pipeline

| Arquivo | Responsabilidade |
|---------|-----------------|
| `app/api/routes/webhook.py` | Recebe mensagens Evolution |
| `app/pipeline/processors/ingestao_grupo.py` | Detecta grupo e enfileira |
| `app/services/grupos/ingestor.py` | Salva mensagem inicial |
| `app/services/grupos/heuristica.py` | Filtro por regex/keywords |
| `app/services/grupos/classificador.py` | Funcoes de atualizacao (NAO USADAS) |
| `app/services/grupos/classificador_llm.py` | Classificacao LLM |
| `app/services/grupos/extrator.py` | Extracao de dados |
| `app/services/grupos/pipeline_worker.py` | Orquestra estagios |
| `app/workers/grupos_worker.py` | Loop de processamento |
| `app/services/grupos/fila.py` | Gerencia fila |

---

## Definition of Done

- [ ] Pipeline documentado com diagramas
- [ ] Campos `passou_heuristica` e `eh_oferta` sendo atualizados corretamente
- [ ] Vagas sendo importadas para tabela final
- [ ] Metricas do dashboard refletindo realidade
- [ ] Observabilidade adicionada (logs estruturados)
- [ ] Testes de integracao do pipeline
- [ ] Backfill de dados historicos (opcional)

---

## Dependencias

- Acesso ao banco de producao (Supabase)
- Ambiente de desenvolvimento configurado
- Conhecimento do fluxo Evolution API → Python → Supabase

---

## Riscos

| Risco | Mitigacao |
|-------|-----------|
| Quebrar pipeline em producao | Fazer alteracoes incrementais |
| Perda de dados historicos | Manter campos NULL existentes |
| Impacto em performance | Monitorar latencia |
