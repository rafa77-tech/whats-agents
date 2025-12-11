# Epic 02: Tools de Gestao

## Objetivo

Implementar as ferramentas (tools) que a Julia pode usar para executar acoes e buscar informacoes.

## Contexto

O agente Julia precisa de tools para interagir com o sistema. Cada tool eh uma funcao que:
1. Recebe parametros estruturados
2. Executa uma acao ou query
3. Retorna resultado estruturado

## Catalogo de Tools

### Categoria: Comunicacao

#### Tool: `enviar_mensagem`

**Descricao:** Envia mensagem WhatsApp para um medico

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| telefone | string | Sim | Numero do medico (com DDD) |
| instrucao | string | Nao | Instrucao sobre o que dizer |
| tipo | string | Nao | discovery, oferta, reativacao, followup |

**Retorno:**
```json
{
  "sucesso": true,
  "mensagem_enviada": "Oi Dr Carlos! Tudo bem?...",
  "medico": "Dr Carlos Silva",
  "telefone": "11999887766"
}
```

**Exemplo de uso:**
```
Gestor: "Manda msg pro 11999 perguntando se ele faz plantao noturno"
Tool call: enviar_mensagem(telefone="11999887766", instrucao="perguntar se faz plantao noturno")
```

---

#### Tool: `buscar_historico_conversa`

**Descricao:** Busca historico de conversas com um medico

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| telefone | string | Sim* | Numero do medico |
| nome | string | Sim* | Nome do medico |
| limite | int | Nao | Quantas mensagens (default: 10) |

*Um dos dois eh obrigatorio

**Retorno:**
```json
{
  "medico": "Dr Carlos Silva",
  "total_interacoes": 15,
  "mensagens": [
    {"data": "2024-12-10", "autor": "julia", "texto": "Oi Dr!..."},
    {"data": "2024-12-10", "autor": "medico", "texto": "Opa, tudo bem..."}
  ]
}
```

---

### Categoria: Metricas

#### Tool: `buscar_metricas`

**Descricao:** Busca metricas de performance da Julia

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| periodo | string | Sim | hoje, ontem, semana, mes |
| tipo | string | Nao | respostas, envios, conversoes, all |

**Retorno:**
```json
{
  "periodo": "hoje",
  "metricas": {
    "mensagens_enviadas": 45,
    "respostas_recebidas": 12,
    "taxa_resposta": 26.7,
    "respostas_positivas": 8,
    "respostas_negativas": 1,
    "opt_outs": 1,
    "vagas_reservadas": 2
  }
}
```

---

#### Tool: `comparar_periodos`

**Descricao:** Compara metricas entre dois periodos

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| periodo1 | string | Sim | Primeiro periodo |
| periodo2 | string | Sim | Segundo periodo |

**Retorno:**
```json
{
  "periodo1": {"nome": "essa semana", "taxa_resposta": 32},
  "periodo2": {"nome": "semana passada", "taxa_resposta": 28},
  "variacao": {
    "taxa_resposta": "+4 pontos",
    "tendencia": "melhora"
  }
}
```

---

### Categoria: Medicos

#### Tool: `buscar_medico`

**Descricao:** Busca informacoes de um medico

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| telefone | string | Sim* | Numero do medico |
| nome | string | Sim* | Nome do medico |
| crm | string | Sim* | CRM do medico |

*Um dos tres eh obrigatorio

**Retorno:**
```json
{
  "id": "uuid",
  "nome": "Dr Carlos Silva",
  "telefone": "11999887766",
  "crm": "123456",
  "especialidade": "Anestesiologia",
  "cidade": "Sao Paulo",
  "status": "ativo",
  "ultima_interacao": "2024-12-10",
  "total_plantoes": 5,
  "preferencias": {
    "turno": "noturno",
    "regiao": "ABC"
  }
}
```

---

#### Tool: `listar_medicos`

**Descricao:** Lista medicos com filtros

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| filtro | string | Nao | responderam_hoje, positivos, sem_resposta, novos |
| especialidade | string | Nao | Filtrar por especialidade |
| limite | int | Nao | Quantos retornar (default: 10) |

**Retorno:**
```json
{
  "total": 12,
  "medicos": [
    {"nome": "Dr Carlos", "telefone": "11999...", "status": "interessado"},
    {"nome": "Dra Maria", "telefone": "11988...", "status": "perguntou_valor"}
  ]
}
```

---

#### Tool: `bloquear_medico`

**Descricao:** Bloqueia medico (opt-out)

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| telefone | string | Sim | Numero do medico |
| motivo | string | Nao | Motivo do bloqueio |

**Retorno:**
```json
{
  "sucesso": true,
  "medico": "Dr Carlos Silva",
  "bloqueado_em": "2024-12-11T10:30:00"
}
```

**ACAO CRITICA:** Requer confirmacao

---

#### Tool: `desbloquear_medico`

**Descricao:** Remove bloqueio de medico

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| telefone | string | Sim | Numero do medico |

**Retorno:**
```json
{
  "sucesso": true,
  "medico": "Dr Carlos Silva"
}
```

---

### Categoria: Vagas

#### Tool: `buscar_vagas`

**Descricao:** Busca vagas disponiveis

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| status | string | Nao | aberta, reservada, fechada |
| hospital | string | Nao | Nome do hospital |
| especialidade | string | Nao | Especialidade |
| data_inicio | string | Nao | Data inicial |
| data_fim | string | Nao | Data final |

**Retorno:**
```json
{
  "total": 45,
  "vagas": [
    {
      "id": "uuid",
      "hospital": "Sao Luiz Morumbi",
      "data": "2024-12-15",
      "periodo": "Noturno",
      "valor": 2500,
      "especialidade": "Anestesiologia",
      "status": "aberta"
    }
  ]
}
```

---

#### Tool: `reservar_vaga`

**Descricao:** Reserva vaga para um medico

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| vaga_id | string | Sim | ID da vaga |
| telefone_medico | string | Sim | Telefone do medico |

**Retorno:**
```json
{
  "sucesso": true,
  "vaga": "Sao Luiz - 15/12 - Noturno",
  "medico": "Dr Carlos Silva",
  "valor": 2500
}
```

**ACAO CRITICA:** Requer confirmacao

---

### Categoria: Sistema

#### Tool: `status_sistema`

**Descricao:** Retorna status geral do sistema

**Parametros:** Nenhum

**Retorno:**
```json
{
  "status": "ativo",
  "conversas_ativas": 5,
  "handoffs_pendentes": 1,
  "vagas_abertas": 45,
  "mensagens_hoje": 23,
  "ultima_sincronizacao_briefing": "2024-12-11T08:00:00"
}
```

---

#### Tool: `buscar_handoffs`

**Descricao:** Lista handoffs pendentes ou recentes

**Parametros:**
| Param | Tipo | Obrigatorio | Descricao |
|-------|------|-------------|-----------|
| status | string | Nao | pendente, resolvido, all |

**Retorno:**
```json
{
  "total": 2,
  "handoffs": [
    {
      "medico": "Dr Carlos",
      "motivo": "pediu_humano",
      "criado_em": "2024-12-11T10:00:00",
      "status": "pendente"
    }
  ]
}
```

---

## User Stories

### US-01: Implementar Tools de Comunicacao

**Como** agente Julia
**Quero** tools para enviar mensagens e ver historico
**Para** interagir com medicos quando o gestor pedir

**Criterios de Aceite:**
- [ ] `enviar_mensagem` funciona com telefone e instrucao
- [ ] `buscar_historico_conversa` retorna ultimas mensagens
- [ ] Tratamento de erros (medico nao encontrado, etc)

**DoD:**
- Tools implementadas e testadas
- Documentacao atualizada

---

### US-02: Implementar Tools de Metricas

**Como** gestor
**Quero** perguntar metricas para a Julia
**Para** acompanhar performance sem abrir dashboards

**Criterios de Aceite:**
- [ ] `buscar_metricas` retorna dados corretos
- [ ] `comparar_periodos` calcula variacoes
- [ ] Periodos suportados: hoje, ontem, semana, mes

**DoD:**
- Tools implementadas e testadas
- Queries SQL otimizadas

---

### US-03: Implementar Tools de Medicos

**Como** gestor
**Quero** buscar e gerenciar medicos via Julia
**Para** nao precisar abrir o sistema

**Criterios de Aceite:**
- [ ] `buscar_medico` encontra por telefone, nome ou CRM
- [ ] `listar_medicos` filtra corretamente
- [ ] `bloquear_medico` e `desbloquear_medico` funcionam
- [ ] Acoes de bloqueio pedem confirmacao

**DoD:**
- Tools implementadas e testadas
- Confirmacao para acoes criticas

---

### US-04: Implementar Tools de Vagas

**Como** gestor
**Quero** consultar e reservar vagas via Julia
**Para** fechar plantoes mais rapido

**Criterios de Aceite:**
- [ ] `buscar_vagas` filtra por hospital, data, status
- [ ] `reservar_vaga` atualiza status corretamente
- [ ] Reserva pede confirmacao

**DoD:**
- Tools implementadas e testadas
- Integracao com tabela de vagas

---

### US-05: Implementar Tools de Sistema

**Como** gestor
**Quero** saber o status do sistema rapidamente
**Para** identificar se algo precisa de atencao

**Criterios de Aceite:**
- [ ] `status_sistema` retorna visao geral
- [ ] `buscar_handoffs` lista pendencias

**DoD:**
- Tools implementadas e testadas

---

## Tarefas Tecnicas

### T01: Criar modulo `app/tools/slack_tools.py`
- [ ] Estrutura base das tools
- [ ] Registro de tools disponiveis
- [ ] Executor de tools

### T02: Implementar tools de comunicacao
- [ ] `enviar_mensagem`
- [ ] `buscar_historico_conversa`

### T03: Implementar tools de metricas
- [ ] `buscar_metricas`
- [ ] `comparar_periodos`

### T04: Implementar tools de medicos
- [ ] `buscar_medico`
- [ ] `listar_medicos`
- [ ] `bloquear_medico`
- [ ] `desbloquear_medico`

### T05: Implementar tools de vagas
- [ ] `buscar_vagas`
- [ ] `reservar_vaga`

### T06: Implementar tools de sistema
- [ ] `status_sistema`
- [ ] `buscar_handoffs`

### T07: Testes
- [ ] Testes unitarios para cada tool
- [ ] Testes de integracao

---

## Estimativa

| Tarefa | Horas |
|--------|-------|
| T01: Modulo base | 1h |
| T02: Tools comunicacao | 1-2h |
| T03: Tools metricas | 1-2h |
| T04: Tools medicos | 1-2h |
| T05: Tools vagas | 1h |
| T06: Tools sistema | 0.5h |
| T07: Testes | 1-2h |
| **Total** | **6-10h** |

---

## Formato das Tools para Claude

```python
SLACK_TOOLS = [
    {
        "name": "enviar_mensagem",
        "description": "Envia mensagem WhatsApp para um medico. Use quando o gestor pedir para contatar, mandar msg, falar com um medico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "telefone": {
                    "type": "string",
                    "description": "Numero do telefone do medico com DDD (ex: 11999887766)"
                },
                "instrucao": {
                    "type": "string",
                    "description": "Instrucao sobre o que deve ser dito na mensagem"
                },
                "tipo": {
                    "type": "string",
                    "enum": ["discovery", "oferta", "reativacao", "followup"],
                    "description": "Tipo de abordagem"
                }
            },
            "required": ["telefone"]
        }
    },
    # ... mais tools
]
```

---

## Acoes Criticas (Requerem Confirmacao)

| Tool | Motivo |
|------|--------|
| `enviar_mensagem` | Envia msg real para medico |
| `bloquear_medico` | Impede contato futuro |
| `reservar_vaga` | Altera status de vaga |

Para essas tools, o agente deve:
1. Mostrar preview da acao
2. Pedir confirmacao (sim/nao)
3. So executar apos confirmacao
