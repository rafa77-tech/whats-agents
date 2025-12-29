# Base de Conhecimento da Julia

> Documentos de referencia para o sistema RAG e prompts da Julia

---

## Estrutura

```
julia/
├── objecoes/           # Tratamento de objecoes e perfis
├── templates/          # Modelos de mensagens e conversas
├── prompts/            # Prompts e protocolos de resposta
└── operacional/        # Metricas, fluxos e operacao
```

---

## Conteudo por Pasta

### objecoes/

| Arquivo | Descricao |
|---------|-----------|
| julia_catalogo_objecoes_respostas.md | 50+ objecoes com respostas estruturadas |
| guia_adaptacao_perfis_medicos.md | 7 perfis de medicos e como adaptar comunicacao |
| julia_triggers_handoff_humano.md | Gatilhos para transferir para humano |
| 3_erros_criticos_medicos_senior.md | Erros a evitar com medicos experientes |

### templates/

| Arquivo | Descricao |
|---------|-----------|
| 220_modelos_mensagens_abertura.md | 220 templates de mensagens de abertura |
| CONVERSAS_REFERENCIA.md | Conversas reais de escalistas como referencia |

### prompts/

| Arquivo | Descricao |
|---------|-----------|
| julia_prompt_negociacao_detalhado.md | Prompts para negociacao de valores |
| julia_sistema_prompts_avancado.md | Sistema avancado de composicao de prompts |
| julia_protocolo_escalacao_automatica.md | Regras de escalacao para humano |

### operacional/

| Arquivo | Descricao |
|---------|-----------|
| fluxo-reativacao.md | Cadencia de follow-up e reativacao |
| metricas-monitoramento.md | Metricas e otimizacao continua |
| julia_fundacao_cientifica.md | Base cientifica do comportamento |
| PREFERENCIAS_MEDICO.md | Sistema de preferencias detectadas |

---

## Uso no Sistema

Estes documentos sao indexados pelo sistema de conhecimento dinamico (Sprint 13) para:
- Injecao automatica de contexto no prompt
- Deteccao de objecoes e respostas apropriadas
- Deteccao de perfil do medico
- Enriquecimento de respostas da Julia

---

*Atualizado em 29/12/2025*
