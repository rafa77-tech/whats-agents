# Epic 01: Agente Julia no Slack

## Objetivo

Criar a infraestrutura do agente conversacional que interpreta mensagens em linguagem natural e executa acoes.

## Contexto

Atualmente o Slack usa comandos rigidos (`contata`, `status`, `bloqueia`). Precisamos de um agente que:
1. Recebe mensagem em linguagem natural
2. Interpreta a intencao usando LLM
3. Seleciona e executa tools apropriadas
4. Responde em linguagem natural

## Arquitetura

```
Slack Message
    |
    v
[Webhook /webhook/slack]
    |
    v
[Agente Julia Slack]
    |
    +-- Interpreta intencao (LLM)
    |
    +-- Seleciona tool(s)
    |
    +-- Executa tool(s)
    |
    +-- Formata resposta
    |
    v
[Resposta no Slack]
```

## User Stories

### US-01: Interpretacao de Intencao

**Como** gestor
**Quero** digitar mensagens em linguagem natural
**Para** nao precisar decorar comandos

**Criterios de Aceite:**
- [ ] Julia entende variacoes da mesma intencao:
  - "manda msg pro 11999..." = "contata 11999..." = "fala com 11999..."
- [ ] Julia identifica parametros na mensagem (telefone, nome, etc)
- [ ] Julia pede esclarecimento se a intencao nao esta clara
- [ ] Funciona com portugues informal (vc, pra, ta, etc)

**Exemplos de Input -> Intencao:**
| Input | Intencao | Parametros |
|-------|----------|------------|
| "manda msg pro 11999887766" | enviar_mensagem | telefone=11999887766 |
| "quantos responderam hoje?" | buscar_metricas | periodo=hoje, tipo=respostas |
| "bloqueia esse numero 11988..." | bloquear_medico | telefone=11988... |
| "como ta a Julia?" | status_sistema | - |
| "quem eh o Dr Carlos?" | buscar_medico | nome=Carlos |

**DoD:**
- Testes com 20+ variacoes de frases
- Acuracia > 95% na interpretacao
- Tempo de interpretacao < 2s

---

### US-02: Sistema de Tools

**Como** agente Julia
**Quero** ter acesso a tools de gestao
**Para** executar acoes solicitadas pelo gestor

**Criterios de Aceite:**
- [ ] Tools definidas em formato compativel com Claude
- [ ] Cada tool tem descricao clara do que faz
- [ ] Tools retornam dados estruturados
- [ ] Erros sao tratados graciosamente

**Tools Iniciais:**
```python
tools = [
    {
        "name": "enviar_mensagem",
        "description": "Envia mensagem WhatsApp para um medico",
        "parameters": {
            "telefone": "string - numero do medico",
            "instrucao": "string - o que deve ser dito na mensagem"
        }
    },
    {
        "name": "buscar_metricas",
        "description": "Busca metricas de performance",
        "parameters": {
            "periodo": "string - hoje, semana, mes",
            "tipo": "string - respostas, envios, conversoes"
        }
    },
    # ... mais tools
]
```

**DoD:**
- Minimo 6 tools implementadas
- Cada tool com testes unitarios
- Documentacao de cada tool

---

### US-03: Execucao de Tools

**Como** agente Julia
**Quero** executar tools e obter resultados
**Para** responder ao gestor com informacoes reais

**Criterios de Aceite:**
- [ ] Tools sao executadas de forma assincrona
- [ ] Resultados sao capturados corretamente
- [ ] Erros nao quebram o fluxo
- [ ] Timeout de 30s por tool

**Fluxo:**
```
1. LLM decide usar tool X com params Y
2. Sistema executa tool X(Y)
3. Sistema captura resultado ou erro
4. Resultado volta pro LLM para formatar resposta
```

**DoD:**
- Execucao funciona para todas as tools
- Tratamento de erro em todas as tools
- Logs de execucao para debug

---

### US-04: Contexto de Conversa

**Como** gestor
**Quero** que a Julia lembre do contexto da conversa
**Para** nao precisar repetir informacoes

**Criterios de Aceite:**
- [ ] Julia lembra mensagens anteriores na mesma "sessao"
- [ ] Sessao expira apos 30 min de inatividade
- [ ] Julia usa contexto para resolver referencias ("ele", "esse medico", etc)

**Exemplo:**
```
Gestor: Quantos responderam hoje?
Julia: 12 medicos responderam hoje.

Gestor: Quem sao eles?
Julia: [lista os 12, usando contexto de "responderam hoje"]

Gestor: Manda msg pro primeiro
Julia: [usa contexto para saber quem eh o primeiro da lista]
```

**DoD:**
- Contexto persiste por 30 min
- Resolucao de referencias funciona
- Testes com conversas multi-turno

---

### US-05: Confirmacao de Acoes Criticas

**Como** gestor
**Quero** que a Julia peca confirmacao antes de acoes importantes
**Para** evitar erros por interpretacao errada

**Criterios de Aceite:**
- [ ] Acoes criticas requerem confirmacao:
  - Envio de mensagem
  - Bloqueio de medico
  - Alteracao de status de vaga
- [ ] Julia mostra preview da acao antes de executar
- [ ] Gestor pode confirmar ou cancelar
- [ ] Acoes de leitura nao pedem confirmacao

**Exemplo:**
```
Gestor: Manda msg pro 11999 oferecendo a vaga do Sao Luiz

Julia: Vou mandar essa mensagem pro 11999887766:
       "Oi Dr! Tudo bem? Surgiu uma vaga no Sao Luiz, plantao noturno
       dia 15/12, R$ 2.500. Tem interesse?"

       Posso enviar?

Gestor: Sim

Julia: Enviado!
```

**DoD:**
- Lista de acoes criticas definida
- Fluxo de confirmacao implementado
- Gestor pode editar antes de confirmar

---

## Tarefas Tecnicas

### T01: Criar servico `agente_slack.py`
- [ ] Classe `AgenteSlack` com metodo principal `processar_mensagem()`
- [ ] Integracao com Claude API
- [ ] Sistema de tools
- [ ] Gerenciamento de contexto

### T02: Refatorar `slack_comandos.py`
- [ ] Substituir comandos rigidos por chamada ao agente
- [ ] Manter retrocompatibilidade com comandos antigos (opcional)

### T03: Criar tabela `slack_sessoes`
- [ ] Armazenar contexto de conversa
- [ ] TTL de 30 minutos
- [ ] Historico de mensagens da sessao

### T04: Implementar prompt do agente
- [ ] System prompt definindo persona e capabilities
- [ ] Instrucoes para uso de tools
- [ ] Exemplos de interacoes

### T05: Testes
- [ ] Testes unitarios das tools
- [ ] Testes de integracao do agente
- [ ] Testes de conversas multi-turno

---

## Prompt do Agente (Rascunho)

```
Voce eh a Julia, escalista virtual da Revoluna. O gestor esta conversando
com voce pelo Slack para gerenciar medicos e plantoes.

Voce tem acesso a ferramentas para:
- Enviar mensagens WhatsApp para medicos
- Consultar metricas e dados
- Bloquear/desbloquear medicos
- Gerenciar vagas

Diretrizes:
- Responda de forma natural e amigavel, como uma colega de trabalho
- Use portugues informal (vc, pra, ta, etc)
- Seja concisa nas respostas
- Para acoes que modificam dados, mostre um preview e peca confirmacao
- Se nao entender algo, peca esclarecimento
- Nao invente dados - use as ferramentas para buscar informacoes reais

Contexto da conversa atual:
{historico_mensagens}
```

---

## Estimativa

| Tarefa | Horas |
|--------|-------|
| T01: Servico agente_slack | 3-4h |
| T02: Refatorar slack_comandos | 1-2h |
| T03: Tabela slack_sessoes | 1h |
| T04: Prompt do agente | 1-2h |
| T05: Testes | 2-3h |
| **Total** | **8-12h** |

---

## Dependencias

- Claude API configurada
- Slack Bot funcionando
- Tools implementadas (Epic 02)

## Riscos

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|--------------|---------|-----------|
| LLM interpreta errado | Media | Alto | Confirmacao antes de acoes |
| Latencia alta | Baixa | Medio | Usar Haiku, otimizar prompt |
| Custo de tokens | Media | Medio | Limitar contexto, usar cache |
