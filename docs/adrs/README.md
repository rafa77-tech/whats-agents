# Architecture Decision Records (ADRs)

Registro de decisoes arquiteturais importantes do Agente Julia.

## O que sao ADRs?

Architecture Decision Records (ADRs) documentam decisoes tecnicas significativas feitas durante o desenvolvimento do projeto. Cada ADR captura:

- O contexto que motivou a decisao
- A decisao tomada
- As consequencias (trade-offs positivos e negativos)
- Alternativas consideradas

## Indice de Decisoes

### Decisoes Aceitas

| ADR | Titulo | Data | Sprint | Status |
|-----|--------|------|--------|--------|
| [001](001-hybrid-llm-strategy.md) | Estrategia Hibrida de LLM (80/20 Haiku/Sonnet) | Dez 2025 | Sprint 1-4 | Aceita |
| [002](002-self-hosted-evolution-api.md) | Evolution API Self-Hosted para WhatsApp | Dez 2025 | Sprint 0-1 | Aceita |
| [003](003-pluggable-pipeline.md) | Pipeline de Processamento Plugavel | Jan 2026 | Sprint 10 | Aceita |
| [004](004-business-events-audit.md) | Event Sourcing para Auditoria e Automacao | Jan 2026 | Sprint 17 | Aceita |
| [005](005-pgvector-embeddings.md) | pgvector para Embeddings (nao Pinecone) | Jan 2026 | Sprint 13 | Aceita |

## Como usar este diretorio

1. **Consultar decisoes existentes**: Antes de propor mudancas arquiteturais, revisar os ADRs para entender decisoes previas
2. **Criar novo ADR**: Quando uma decisao arquitetural significativa for tomada, documentar em novo arquivo ADR
3. **Atualizar status**: Se uma decisao for superseded, marcar no ADR original e referenciar o novo

## Template de ADR

```markdown
# ADR-NNN: Titulo da Decisao

- Status: [Proposta | Aceita | Rejeitada | Superseded | Deprecated]
- Data: YYYY-MM-DD
- Sprint: Sprint X
- Decisores: [Nomes ou "Equipe"]

## Contexto

[Descrever o problema ou situacao que motivou a decisao]

## Decisao

[Descrever a decisao tomada e como sera implementada]

## Alternativas Consideradas

1. **Alternativa 1**
   - Pros: ...
   - Cons: ...

2. **Alternativa 2**
   - Pros: ...
   - Cons: ...

## Consequencias

### Positivas
- [Beneficio 1]
- [Beneficio 2]

### Negativas
- [Trade-off 1]
- [Trade-off 2]

### Mitigacoes
- [Como mitigar os trade-offs negativos]

## Referencias

- [Link para codigo relevante]
- [Link para documentacao relacionada]
- [Link para discussoes/issues]
```

## Categorias de Decisoes

### Tecnologia
- ADR-001: Hybrid LLM Strategy
- ADR-002: Self-Hosted Evolution API
- ADR-005: pgvector Embeddings

### Arquitetura
- ADR-003: Pluggable Pipeline
- ADR-004: Business Events (Event Sourcing)

## Referencia Rapida

### Quando criar um ADR?

Crie um ADR quando:
- Escolher uma tecnologia core (banco de dados, framework, LLM provider)
- Definir um padrao arquitetural importante (event sourcing, CQRS, pipeline)
- Fazer um trade-off significativo (custo vs performance, simplicidade vs flexibilidade)
- Tomar decisao que afeta multiplos subsistemas
- Rejeitar uma abordagem alternativa comum (explicar por que)

### Quando NAO criar um ADR?

Nao crie ADR para:
- Detalhes de implementacao que nao afetam arquitetura geral
- Decisoes triviais ou obvias
- Configuracoes que podem ser facilmente revertidas
- Escolhas de naming/style (use CONVENTIONS.md)

## Versionamento

Este diretorio segue versionamento semantico para ADRs:
- Numero do ADR nunca muda (001, 002, etc)
- Status pode mudar (Proposta -> Aceita -> Superseded)
- Atualizacoes sao registradas em secao "Historico de Mudancas" no ADR

---

**Ultimo Update:** 10/02/2026
**Total de ADRs:** 5
**Manutencao:** Engenharia
