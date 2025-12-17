# Sprint 13: Conhecimento Dinâmico (RAG para Prompts)

## Objetivo

Implementar sistema de conhecimento dinâmico que injeta contexto relevante nos prompts da Julia baseado na situação da conversa, usando RAG sobre a documentação de treinamento.

## Problema que Resolve

A Julia atual tem prompts estáticos e genéricos. A documentação de treinamento (`docs/julia/`) contém conhecimento rico sobre:
- 6 perfis de médico com abordagens específicas
- 50+ objeções catalogadas com respostas
- 3 erros críticos com médicos sênior
- Conversas de referência reais
- Framework LAAR para objeções

**Esse conhecimento precisa ser injetado dinamicamente, não em um prompt gigante.**

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                    FLUXO DE MENSAGEM                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Mensagem chega                                           │
│           │                                                  │
│           ▼                                                  │
│  2. Detectar situação ──────────────────────────────────┐    │
│     - Tipo de objeção?                                  │    │
│     - Perfil do médico?                                 │    │
│     - Objetivo da conversa?                             │    │
│           │                                             │    │
│           ▼                                             │    │
│  3. Buscar conhecimento relevante (RAG) ◄───────────────┘    │
│     - Embeddings da docs/julia/                              │
│     - Top-K chunks mais relevantes                           │
│           │                                                  │
│           ▼                                                  │
│  4. Injetar no contexto do prompt                            │
│     - Adiciona ao PromptBuilder                              │
│     - Mantém prompt base pequeno                             │
│           │                                                  │
│           ▼                                                  │
│  5. LLM gera resposta com contexto rico                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Épicos

| Épico | Nome | Stories | Descrição |
|-------|------|---------|-----------|
| E01 | Indexação Base de Conhecimento | 4 | Indexar docs/julia/ como embeddings |
| E02 | Detectores de Situação | 4 | Identificar objeções, perfil, objetivo |
| E03 | Injeção Dinâmica | 4 | Integrar com PromptBuilder |
| E04 | Testes e Métricas | 4 | Validar qualidade e performance |

**Total:** 16 stories

## Dependências

- Sprint 8 (Memória RAG) - Sistema de embeddings já existe
- Voyage AI - API de embeddings configurada
- Supabase pgvector - Busca vetorial funcionando

## Ordem de Execução

```
E01 (Indexação) ─────► E02 (Detectores) ─────► E03 (Injeção) ─────► E04 (Testes)
     │                      │                       │
     │                      │                       │
     ▼                      ▼                       ▼
 Base de dados         Classificação          Prompt enriquecido
 de conhecimento       automática             com conhecimento
```

## Critérios de Aceite da Sprint

- [ ] Documentação `docs/julia/` indexada como embeddings
- [ ] Detector identifica objeções com >80% precisão
- [ ] Detector identifica perfil de médico (6 tipos)
- [ ] Contexto relevante injetado em <200ms
- [ ] Qualidade de resposta mensurável melhorada
- [ ] Métricas de uso do conhecimento disponíveis

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Latência alta do RAG | Média | Alto | Cache de embeddings, busca assíncrona |
| Contexto irrelevante injetado | Média | Médio | Threshold de similaridade, validação |
| Custo de embeddings | Baixa | Médio | Batch processing, cache agressivo |

## Métricas de Sucesso

| Métrica | Baseline | Meta |
|---------|----------|------|
| Precisão detecção objeções | N/A | >80% |
| Precisão detecção perfil | N/A | >70% |
| Latência adicional | 0ms | <200ms |
| Taxa de uso do conhecimento | 0% | >50% das respostas |

## Arquivos a Criar

```
app/
├── services/
│   ├── conhecimento/
│   │   ├── __init__.py
│   │   ├── indexador.py      # E01: Indexação de docs
│   │   ├── buscador.py       # E01: Busca semântica
│   │   ├── detector_objecao.py    # E02: Detecta objeções
│   │   ├── detector_perfil.py     # E02: Detecta perfil médico
│   │   ├── detector_objetivo.py   # E02: Detecta objetivo conversa
│   │   ├── orquestrador.py        # E02: Orquestra detectores
│   │   └── injetor.py             # E03: Injeta no prompt
│   │
│   └── contexto.py           # E03: Modificar para usar injetor
│
├── prompts/
│   └── builder.py            # E03: Método com_conhecimento()
│
tests/
├── conhecimento/
│   ├── test_indexador.py
│   ├── test_buscador.py
│   ├── test_detector_objecao.py
│   ├── test_detector_perfil.py
│   ├── test_detector_objetivo.py
│   ├── test_orquestrador.py
│   └── test_injetor.py
```

## Timeline Sugerido

- **E01:** 1-2 dias (indexação é straightforward)
- **E02:** 2-3 dias (detectores precisam tuning)
- **E03:** 1-2 dias (integração)
- **E04:** 1-2 dias (testes e ajustes)

**Total estimado:** 5-9 dias
