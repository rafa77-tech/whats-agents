# Sprint 8: Evolucao Arquitetural - Persona & Extensibilidade

## Objetivo

> **Preparar a arquitetura para producao: memoria de longo prazo, pipeline extensivel, prompts dinamicos e validacao de output.**

Este sprint foi criado apos analise da arquitetura atual. O codigo funciona para MVP mas precisa de refatoracoes para:
1. Manter persona convincente ao longo do tempo (memoria)
2. Permitir adicionar funcionalidades sem editar webhook monolitico
3. Testar variacoes de prompt sem deploy
4. Garantir que Julia nunca revele que e IA

---

## Pre-requisitos

Antes de iniciar esta sprint, verificar:

| Requisito | Status | Notas |
|-----------|--------|-------|
| Redis rodando | Necessario | Cache de prompts e aberturas |
| Supabase com pgvector | Necessario | Busca semantica de memorias |
| Voyage AI API key | Necessario | Embeddings (VOYAGE_API_KEY) |
| Anthropic API key | Necessario | Claude para LLM |

### Configuracao de Ambiente

```bash
# Adicionar ao .env
VOYAGE_API_KEY=pa-...        # Obter em: dash.voyageai.com
ANTHROPIC_API_KEY=sk-ant-... # Ja deve estar configurado

# Instalar dependencia
uv add voyageai
```

### Decisao Tecnica: Embeddings

**Escolha: Voyage AI voyage-3.5-lite** (recomendado pela Anthropic)

| Criterio | Voyage | OpenAI |
|----------|--------|--------|
| Preco | $0.02/1M tokens | $0.02/1M tokens |
| Qualidade | +6.34% superior | baseline |
| Contexto | 32K tokens | 8K tokens |
| Dimensoes | 1024 | 1536 |
| Parceria Anthropic | ✅ | ❌ |

---

## Gaps Identificados

| # | Gap | Prioridade | Impacto |
|---|-----|------------|---------|
| 1 | Tool `salvar_memoria` ausente | P0 | Julia nao salva preferencias durante conversa |
| 2 | RAG com doctor_context nao implementado | P0 | Julia nao lembra contexto entre conversas |
| 3 | Webhook monolitico (436 linhas) | P1 | Dificil adicionar funcionalidades |
| 4 | Prompts hardcoded | P1 | Impossivel testar variacoes |
| 5 | Sem validacao de output | P1 | Risco de revelar que e IA |
| 6 | Aberturas repetitivas | P2 | Medicos percebem padrao robotico |

---

## Epicos

| # | Epico | Stories | Prioridade | Status |
|---|-------|---------|------------|--------|
| 01 | Tool salvar_memoria | 4 | P0 | Pendente |
| 02 | Memoria de Longo Prazo (RAG) | 5 | P0 | Pendente |
| 03 | Pipeline de Processamento | 6 | P1 | Pendente |
| 04 | Sistema de Prompts Dinamico | 4 | P1 | Pendente |
| 05 | Validacao de Output | 4 | P1 | Pendente |
| 06 | Variacoes de Abertura | 3 | P2 | Pendente |

---

## Dependencias

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORDEM DE IMPLEMENTACAO                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  P0 (Criticos - fazer primeiro):                                │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │ Epic 01:         │───▶│ Epic 02:         │                   │
│  │ Tool salvar_     │    │ Memoria RAG      │                   │
│  │ memoria          │    │ (usa a tool)     │                   │
│  └──────────────────┘    └──────────────────┘                   │
│                                                                  │
│  P1 (Importantes - podem ser paralelos):                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Epic 03:     │  │ Epic 04:     │  │ Epic 05:     │          │
│  │ Pipeline     │  │ Prompts      │  │ Validacao    │          │
│  │              │  │ Dinamicos    │  │ Output       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                │                  │                    │
│         └────────────────┴──────────────────┘                   │
│                          │                                       │
│                          ▼                                       │
│  P2 (Melhorias):                                                │
│  ┌──────────────────┐                                           │
│  │ Epic 06:         │                                           │
│  │ Variacoes        │                                           │
│  │ Abertura         │                                           │
│  └──────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Criterios de Saida do Sprint

- [ ] Tool `salvar_memoria` funcionando e registrada no agente
- [ ] RAG busca contexto relevante de conversas anteriores
- [ ] Webhook refatorado em pipeline com pre/pos processadores
- [ ] Prompts carregados do banco com suporte a versoes
- [ ] Validacao impede envio de mensagens que revelam IA
- [ ] Aberturas variam entre 10+ templates
- [ ] Testes de regressao passando

---

## Arquivos a Criar/Modificar

| Arquivo | Acao | Epico |
|---------|------|-------|
| `app/tools/memoria.py` | Criar | 01 |
| `app/services/embedding.py` | Criar | 01 |
| `app/services/memoria.py` | Criar | 02 |
| `app/pipeline/__init__.py` | Criar | 03 |
| `app/pipeline/processor.py` | Criar | 03 |
| `app/pipeline/pre_processors.py` | Criar | 03 |
| `app/pipeline/post_processors.py` | Criar | 03 |
| `app/prompts/builder.py` | Criar | 04 |
| `app/prompts/loader.py` | Criar | 04 |
| `app/services/validacao_output.py` | Criar | 05 |
| `app/templates/aberturas.py` | Criar | 06 |
| `app/services/abertura.py` | Criar | 06 |
| `app/api/routes/webhook.py` | Modificar | 03 |
| `app/services/agente.py` | Modificar | 01, 02 |
| `app/services/contexto.py` | Modificar | 02 |
| `app/core/prompts.py` | Modificar | 04 |

---

## Estimativas

| Epico | Complexidade | Horas Estimadas |
|-------|--------------|-----------------|
| 01 | Media | 3h |
| 02 | Alta | 6h |
| 03 | Alta | 8h |
| 04 | Media | 4h |
| 05 | Media | 3h |
| 06 | Baixa | 2h |
| **Total** | - | **~26h** |

---

## Metricas de Sucesso

| Metrica | Antes | Meta |
|---------|-------|------|
| Preferencias lembradas entre conversas | 0% | 90%+ |
| Linhas no webhook.py | 436 | <100 |
| Tempo para adicionar nova funcionalidade | ~2h | ~30min |
| Prompts testados sem deploy | 0 | Ilimitado |
| Mensagens que revelam IA (escapam) | Desconhecido | 0 |
| Aberturas unicas | 3-4 | 15+ |
