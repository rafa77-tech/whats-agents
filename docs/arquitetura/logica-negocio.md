# Logica de Negocio

> Fluxos de negocio e regras do Agente Julia

---

## Visao Geral do Negocio

### O que e Staffing Medico?

Staffing medico e o processo de preencher escalas de plantoes hospitalares com medicos qualificados.

**Ciclo tipico:**
1. Hospital define escala mensal (X medicos, periodo Y, dias Z)
2. Ideal: preencher com 30 dias de antecedencia
3. Urgencia cresce conforme data se aproxima
4. Fontes de urgencia: escala nao fechada, medico doente, cancelamento

### Papel da Julia

Julia e uma **escalista virtual** que:
- Prospecta medicos (contato frio)
- Oferece plantoes compativeis
- Negocia valores/datas
- Gerencia follow-ups
- Fecha vagas

---

## Funil de Conversao

```
┌─────────────────────────────────────────────────────────────┐
│                         NOVO                                 │
│              Medico entra no sistema                         │
│                      (100%)                                  │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGUARDANDO_RESPOSTA                       │
│              Julia enviou primeira mensagem                  │
│                      (100%)                                  │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│   NAO_RESPONDEU      │ │      RESPONDEU       │ │      OPT_OUT         │
│   Sem resposta 15d   │ │   Medico respondeu   │ │   Pediu parar        │
│       (40%)          │ │       (30%)          │ │       (5%)           │
└──────────────────────┘ └──────────┬───────────┘ └──────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │        EM_CONVERSACAO           │
                    │    Conversa ativa com Julia     │
                    │            (25%)                │
                    └─────────────────┬───────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│     QUALIFICADO      │ │       INATIVO        │ │       PERDIDO        │
│  Tem interesse real  │ │   Parou de responder │ │   Nao tem interesse  │
│       (15%)          │ │       (8%)           │ │       (2%)           │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
                    │
                    ▼
┌──────────────────────┐
│      CADASTRADO      │
│ Fez cadastro no app  │
│       (10%)          │
└──────────────────────┘
                    │
                    ▼
┌──────────────────────┐
│        ATIVO         │
│   Faz plantoes       │
│       (8%)           │
└──────────────────────┘
```

---

## Fluxos Principais

### Fluxo 1: Primeira Mensagem (Prospeccao)

```
1. Selecionar medicos elegíveis:
   - Especialidade compatível
   - Regiao compatível
   - Nao bloqueado
   - Nao opt-out
   - pressure_score < 70

2. Montar mensagem personalizada:
   - Nome do medico
   - Especialidade
   - Regiao de atuacao
   - Tom informal

3. Verificar rate limit:
   - < 20 msgs/hora
   - < 100 msgs/dia
   - Horario comercial

4. Agendar envio:
   - Delay aleatorio (45-180s)
   - Fila de mensagens

5. Atualizar stage:
   - novo -> aguardando_resposta
   - Incrementar pressure_score
```

**Exemplo de mensagem:**

```
Oi Dr Carlos! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas na regiao do ABC

Vi que vc e anestesista ne? Temos algumas vagas bem legais aqui
```

### Fluxo 2: Resposta do Medico

```
1. Receber mensagem via webhook

2. Detectar intencao:
   - Interesse em vaga
   - Pergunta sobre valor
   - Disponibilidade
   - Opt-out
   - Reclamacao

3. Se OPT-OUT:
   - Marcar cliente como opt_out
   - Enviar confirmacao
   - Encerrar conversa

4. Se HANDOFF necessario:
   - Detectar trigger
   - Transferir para humano
   - Notificar gestor

5. Se INTERESSE:
   - Buscar vagas compativeis
   - Formatar opcoes
   - Enviar com delay humanizado

6. Atualizar contexto:
   - Salvar preferencias detectadas
   - Atualizar stage_jornada
   - Registrar interacao
```

### Fluxo 3: Oferta de Vaga

```
1. Identificar interesse:
   - Perguntou sobre vagas
   - Respondeu positivamente

2. Buscar vagas compativeis:
   - Especialidade do medico
   - Preferencias conhecidas (turno, regiao, valor)
   - Status = aberta
   - Data >= hoje

3. Formatar mensagem:
   - Maximo 3 vagas por vez
   - Formato humano (nao lista)
   - Incluir: hospital, data, periodo, valor

4. Enviar com tool call:
   - Tool: buscar_vagas
   - LLM formata resposta natural
```

**Exemplo:**

```
Show! Deixa eu ver aqui...

Olha, tenho essas opcoes pra vc:

Hospital Brasil, sabado dia 14, noturno, R$ 2.500
Sao Luiz, domingo dia 15, diurno, R$ 2.200

Qual te interessa mais?
```

### Fluxo 4: Reserva de Plantao

```
1. Medico confirma interesse:
   - "Quero a do Hospital Brasil"
   - "Pode reservar pra mim"

2. Validar disponibilidade:
   - Vaga ainda aberta?
   - Medico nao tem conflito?

3. Reservar vaga:
   - Tool: reservar_plantao
   - Status: aberta -> reservada
   - Associar cliente_id

4. Confirmar ao medico:
   - Detalhes do plantao
   - Proximos passos

5. Notificar gestor:
   - Slack notification
   - Dashboard update
```

### Fluxo 5: Follow-up

```
Stages de follow-up (medico nao respondeu):

Stage 1 (48h):
- Mensagem leve
- "Oi! Vi que nao conseguimos falar..."
- Tom amigavel

Stage 2 (5 dias):
- Oferecer nova opcao
- "Surgiu uma vaga interessante..."
- Tom moderado

Stage 3 (15 dias):
- Ultima tentativa
- "Tudo bem? Faz tempo que nao falo com vc..."
- Tom suave

Apos Stage 3:
- Mover para "nao_respondeu"
- Pausar por 60 dias
- Depois volta para "recontato"
```

### Fluxo 6: Handoff para Humano

**Triggers automaticos:**

| Trigger | Exemplo | Acao |
|---------|---------|------|
| Explicito | "Quero falar com humano" | Handoff imediato |
| Juridico | "Vou processar", "meu advogado" | Handoff + alerta |
| Sentimento negativo | Insultos, reclamacoes fortes | Handoff + cuidado |
| Confianca baixa | LLM incerto | Handoff preventivo |

**Processo:**

```
1. Detectar trigger

2. Avisar medico:
   "Vou pedir pra minha supervisora te ajudar,
    ela vai falar com vc ja ja"

3. Atualizar banco:
   - controlled_by = 'human'
   - Registrar handoff

4. Notificar:
   - Slack urgente
   - Chatwoot sync

5. Pausar Julia:
   - Nao responder mais
   - Aguardar humano assumir
```

---

## Regras de Negocio

### Rate Limiting

| Regra | Valor | Motivo |
|-------|-------|--------|
| Msgs/hora | 20 | Evitar ban WhatsApp |
| Msgs/dia | 100 | Evitar ban WhatsApp |
| Intervalo | 45-180s | Parecer humano |
| Horario | 8h-20h | Horario comercial |
| Dias | Seg-Sex | Horario comercial |

### Pressure Score

Mede saturacao do medico com mensagens:

```
Score 0-100:
- 0-40: OK, pode contatar
- 41-70: Cuidado, espaçar contatos
- 71-90: Alta saturacao, evitar
- 91-100: Saturado, nao contatar

Incrementos:
- Primeira mensagem: +25 pontos
- Follow-up: +15 pontos
- Campanha: +20 pontos

Decrementos:
- Cada dia sem contato: -5 pontos
- Resposta positiva: -20 pontos
```

### Preferencias do Medico

Detectadas automaticamente das conversas:

```python
preferencias_detectadas = {
    "turnos": ["noturno", "diurno"],
    "regioes": ["ABC", "Capital"],
    "valor_minimo": 2000,
    "hospitais_preferidos": ["Hospital Brasil"],
    "dias_preferidos": ["sabado", "domingo"]
}
```

### VIP e Bloqueados

Via briefing do gestor:

```
Medicos VIP:
- Tratamento especial
- Prioridade em vagas
- Notificar gestor de interacoes

Medicos Bloqueados:
- Nao contatar
- Motivo registrado
- Pode ser temporario
```

---

## Metricas de Sucesso

### KPIs Principais

| Metrica | Meta | Descricao |
|---------|------|-----------|
| Taxa resposta | > 30% | Medicos que respondem |
| Taxa conversao | > 10% | Medicos que fecham vaga |
| Tempo resposta | < 30s | Latencia do agente |
| Taxa deteccao bot | < 1% | Medicos que percebem IA |
| Taxa handoff | < 5% | Escalacoes para humano |
| NPS medicos | > 8 | Satisfacao |

### Metricas Operacionais

| Metrica | Alerta |
|---------|--------|
| Error rate | > 5% |
| Latencia LLM | > 5s |
| Circuit open | any |
| Opt-out rate | > 10% |

---

## Campanhas

### Tipos de Campanha

| Tipo | Objetivo | Frequencia |
|------|----------|------------|
| Discovery | Conhecer medico | 1x |
| Oferta | Oferecer vaga | Quando tem vaga |
| Reativacao | Retomar contato | Apos 60d |
| Feedback | Coletar opiniao | Pos-plantao |

### Segmentacao

```python
# Exemplo de filtros
segmento = {
    "especialidade": ["anestesiologia", "cardiologia"],
    "estado": ["SP"],
    "cidade": ["Santo Andre", "Sao Bernardo"],
    "status": ["novo", "respondeu"],
    "pressure_score_max": 70
}
```

---

## Integracao com Gestor

### Briefing via Google Docs

Gestor edita documento com:
- Foco da semana
- Vagas prioritarias
- Medicos VIP
- Medicos bloqueados
- Tom a usar
- Margem de negociacao

Sistema sincroniza a cada hora.

### Reports Automaticos

| Report | Horario | Conteudo |
|--------|---------|----------|
| Manha | 10h | Metricas da manha |
| Almoco | 13h | Metricas do periodo |
| Tarde | 17h | Metricas da tarde |
| Fim dia | 20h | Resumo do dia |
| Semanal | Segunda 9h | Consolidado semana |

### Feedback Loop

```
1. Gestor avalia conversa no Chatwoot
2. Marca como positivo/negativo
3. Adiciona correcoes
4. Sistema coleta feedback
5. Atualiza prompt semanalmente
```

---

**Validado em 10/02/2026**
