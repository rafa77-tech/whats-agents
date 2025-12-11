# Epic 04: Tipos de Campanha/Abordagem

## Objetivo

Permitir que o gestor instrua a Julia sobre **como** abordar um medico, com diferentes tipos de mensagem para diferentes situacoes.

## Contexto

Nem toda primeira mensagem eh igual. Dependendo do contexto:
- Medico novo (nunca conversamos) → Discovery
- Vaga especifica disponivel → Oferta
- Medico sumiu (nao responde ha tempo) → Reativacao
- Continuando conversa anterior → Follow-up
- Instrucao livre do gestor → Custom

## Tipos de Abordagem

### 1. Discovery (Descoberta)

**Quando usar:** Primeiro contato com medico desconhecido

**Objetivo:** Apresentar a Julia/Revoluna e entender interesse

**Exemplo de instrucao:**
```
Gestor: Manda msg pro 11999 se apresentando
```

**Mensagem gerada:**
```
Oi Dr! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas na regiao

Vi que vc eh anestesista ne? Temos vagas legais aqui, posso te contar mais?
```

**Caracteristicas:**
- Tom amigavel e leve
- Apresenta quem eh
- Pergunta aberta para iniciar conversa
- Nao menciona vaga especifica

---

### 2. Oferta (Vaga Especifica)

**Quando usar:** Tem uma vaga especifica para oferecer

**Objetivo:** Apresentar oportunidade concreta

**Exemplo de instrucao:**
```
Gestor: Oferece pro 11999 a vaga do Sao Luiz dia 15
```

**Mensagem gerada:**
```
Oi Dr Carlos! Tudo bem?

Surgiu uma vaga boa aqui pro Sao Luiz Morumbi

Plantao noturno dia 15/12, das 19h as 7h
Valor: R$ 2.500

Tem interesse?
```

**Caracteristicas:**
- Vai direto ao ponto
- Detalhes da vaga (local, data, horario, valor)
- Call-to-action claro

---

### 3. Reativacao

**Quando usar:** Medico que parou de responder

**Objetivo:** Retomar contato de forma natural

**Exemplo de instrucao:**
```
Gestor: Tenta reativar o 11999, faz tempo que nao fala com a gente
```

**Mensagem gerada:**
```
Oi Dr Carlos! Sumiu hein

Faz tempo que nao aparece por aqui, ta tudo bem?

Qdo quiser voltar a fazer plantao eh so me chamar!
```

**Caracteristicas:**
- Tom casual, nao desesperado
- Nao pressiona
- Deixa porta aberta

---

### 4. Follow-up

**Quando usar:** Continuando conversa existente

**Objetivo:** Dar sequencia natural

**Exemplo de instrucao:**
```
Gestor: Manda follow-up pro 11999 sobre a vaga que ele perguntou
```

**Mensagem gerada (com contexto):**
```
Oi Dr Carlos!

Lembrei de vc por causa daquela vaga do Sao Luiz que vc perguntou

Ainda tem disponivel, dia 15/12. Quer que eu reserve?
```

**Caracteristicas:**
- Referencia conversa anterior
- Usa contexto do historico
- Oferece acao concreta

---

### 5. Custom (Instrucao Livre)

**Quando usar:** Gestor quer algo especifico

**Objetivo:** Executar instrucao customizada

**Exemplo de instrucao:**
```
Gestor: Manda pro 11999 perguntando se ele conhece algum colega
        anestesista que faz plantao
```

**Mensagem gerada:**
```
Oi Dr Carlos! Tudo bem?

Deixa eu te perguntar uma coisa...

Vc conhece algum colega anestesista que curte fazer plantao?
To com umas vagas boas aqui e queria indicacoes

Se tiver alguem, me passa o contato que eu falo com ele!
```

**Caracteristicas:**
- Segue instrucao do gestor
- Mantém tom da Julia
- Adapta para soar natural

---

## User Stories

### US-01: Selecao de Tipo de Abordagem

**Como** gestor
**Quero** que a Julia identifique o tipo de abordagem pelo contexto
**Para** nao precisar especificar sempre

**Criterios de Aceite:**
- [ ] Julia infere tipo pela instrucao:
  - "se apresenta" → Discovery
  - "oferece vaga" → Oferta
  - "reativa" / "faz tempo" → Reativacao
  - "follow-up" / "continua" → Follow-up
- [ ] Instrucoes especificas → Custom
- [ ] Gestor pode forcar tipo se quiser

**Exemplos de Inferencia:**
| Instrucao | Tipo Inferido |
|-----------|---------------|
| "manda msg pro 11999" | Discovery (padrao) |
| "oferece a vaga do Sao Luiz" | Oferta |
| "tenta contato de novo" | Reativacao |
| "pergunta se ele tem interesse" | Follow-up |
| "pergunta se conhece colegas" | Custom |

**DoD:**
- Logica de inferencia implementada
- Testes com 20+ variacoes

---

### US-02: Geracao de Mensagem por Tipo

**Como** Julia
**Quero** gerar mensagens adequadas para cada tipo
**Para** abordar medicos de forma efetiva

**Criterios de Aceite:**
- [ ] Cada tipo tem template/prompt especifico
- [ ] Mensagens seguem persona da Julia
- [ ] Usa dados do medico quando disponiveis (nome, especialidade)
- [ ] Usa dados da vaga quando relevante

**DoD:**
- Prompts para cada tipo definidos
- Mensagens testadas e validadas

---

### US-03: Preview e Edicao

**Como** gestor
**Quero** ver e editar a mensagem antes de enviar
**Para** garantir que esta adequada

**Criterios de Aceite:**
- [ ] Julia mostra preview da mensagem
- [ ] Gestor pode pedir ajuste ("mais curta", "menciona o valor", etc)
- [ ] Gestor pode aprovar e enviar

**Exemplo:**
```
Gestor: Manda msg pro 11999 oferecendo vaga no Sao Luiz

Julia: Vou mandar assim:

> "Oi Dr Carlos! Tudo bem?
> Surgiu uma vaga no Sao Luiz, plantao noturno dia 15/12,
> R$ 2.500. Tem interesse?"

Posso enviar?

Gestor: Menciona que eh anestesia

Julia: Ajustei:

> "Oi Dr Carlos! Tudo bem?
> Surgiu uma vaga de anestesia no Sao Luiz, plantao noturno
> dia 15/12, R$ 2.500. Tem interesse?"

Agora sim?
```

**DoD:**
- Fluxo de edicao implementado
- Julia interpreta ajustes

---

### US-04: Contexto do Medico

**Como** Julia
**Quero** usar informacoes do medico na mensagem
**Para** personalizar a abordagem

**Criterios de Aceite:**
- [ ] Usa nome quando disponivel
- [ ] Usa especialidade quando relevante
- [ ] Usa historico para follow-ups
- [ ] Usa preferencias se conhecidas

**Dados Usados:**
| Dado | Uso |
|------|-----|
| Nome | "Oi Dr Carlos!" |
| Especialidade | "Vi que vc eh anestesista" |
| Ultima conversa | "Lembrei de vc por causa daquela vaga..." |
| Preferencias | "Sei que vc prefere noturno..." |

**DoD:**
- Integracao com dados do medico
- Mensagens personalizadas testadas

---

## Tarefas Tecnicas

### T01: Definir prompts por tipo
- [ ] Prompt Discovery
- [ ] Prompt Oferta
- [ ] Prompt Reativacao
- [ ] Prompt Follow-up
- [ ] Prompt Custom

### T02: Implementar logica de inferencia de tipo
- [ ] Parser de instrucao
- [ ] Mapeamento instrucao → tipo
- [ ] Override manual

### T03: Integrar com geracao de mensagem
- [ ] Passar tipo para agente WhatsApp
- [ ] Incluir contexto relevante (vaga, historico)

### T04: Fluxo de preview/edicao
- [ ] Mostrar preview no Slack
- [ ] Interpretar pedidos de ajuste
- [ ] Regenerar mensagem

### T05: Testes
- [ ] Testes de inferencia de tipo
- [ ] Testes de geracao por tipo
- [ ] Testes de edicao

---

## Estimativa

| Tarefa | Horas |
|--------|-------|
| T01: Prompts | 1h |
| T02: Inferencia de tipo | 1h |
| T03: Integracao | 0.5h |
| T04: Preview/edicao | 1h |
| T05: Testes | 0.5h |
| **Total** | **3-4h** |

---

## Prompts por Tipo (Rascunho)

### Discovery
```
Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem de PRIMEIRO CONTATO
para um medico que nunca conversou conosco.

Objetivo: se apresentar e entender se ele tem interesse em fazer plantoes.

Dados do medico:
- Nome: {nome}
- Especialidade: {especialidade}

Regras:
- Seja casual e amigavel
- Nao mencione vagas especificas
- Faca uma pergunta aberta
- Max 3-4 linhas
```

### Oferta
```
Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem oferecendo uma
VAGA ESPECIFICA para o medico.

Dados do medico:
- Nome: {nome}

Dados da vaga:
- Hospital: {hospital}
- Data: {data}
- Periodo: {periodo}
- Valor: {valor}
- Especialidade: {especialidade}

Regras:
- Va direto ao ponto
- Inclua todos os detalhes da vaga
- Termine com call-to-action
- Max 4-5 linhas
```

### Reativacao
```
Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem para REATIVAR
contato com um medico que parou de responder.

Dados do medico:
- Nome: {nome}
- Ultima interacao: {ultima_interacao}

Regras:
- Tom leve, nao desesperado
- Nao pressione
- Deixe porta aberta
- Max 3 linhas
```

### Follow-up
```
Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem de FOLLOW-UP
continuando uma conversa existente.

Dados do medico:
- Nome: {nome}

Contexto da conversa:
{historico_resumido}

Instrucao do gestor:
{instrucao}

Regras:
- Referencie a conversa anterior
- Seja natural
- Ofereca proximos passos
- Max 3-4 linhas
```

### Custom
```
Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem seguindo
a instrucao especifica do gestor.

Dados do medico:
- Nome: {nome}

Instrucao do gestor:
{instrucao}

Regras:
- Siga a instrucao fielmente
- Mantenha o tom da Julia
- Adapte para soar natural
- Max 4-5 linhas
```
