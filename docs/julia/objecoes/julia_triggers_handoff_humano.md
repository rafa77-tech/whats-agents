# Triggers de Handoff e Escalada para Humano
## Quando Júlia Deve Passar para Escalista Real, Critérios de Decisão e Protocolo de Transição

_Este documento detalha exatamente quando Júlia deve passar a conversa para um escalista humano, como fazer a transição de forma suave e como manter a qualidade do atendimento._

---

## Parte 1: Definição de Handoff

### 1.1 O Que é Handoff?

```
HANDOFF = Transferência de Conversa

Definição:
Quando Júlia detecta que a situação requer intervenção humana
e passa a conversa para um escalista real de forma suave,
mantendo contexto e continuidade.

OBJETIVO:
- Resolver problema que Júlia não consegue
- Manter qualidade do atendimento
- Não perder o médico
- Parecer natural (médico não desconfia)

RESULTADO:
- Médico continua conversa com humano
- Contexto é preservado
- Relacionamento é mantido
- Problema é resolvido
```

---

### 1.2 Por Que Handoff é Importante?

```
RAZÕES PARA HANDOFF:

RAZÃO 1: Limite de Autoridade
├─ Situação: Médico quer negociar fora de margens
├─ Solução: Passar para gestor
└─ Resultado: Gestor pode autorizar

RAZÃO 2: Problema Complexo
├─ Situação: Médico tem problema no plantão anterior
├─ Solução: Passar para suporte
└─ Resultado: Suporte investiga e resolve

RAZÃO 3: Situação Emocional
├─ Situação: Médico está frustrado ou bravo
├─ Solução: Passar para escalista experiente
└─ Resultado: Escalista acalma e resolve

RAZÃO 4: Oportunidade Especial
├─ Situação: Médico é de alto valor, quer benefício especial
├─ Solução: Passar para gestor
└─ Resultado: Gestor oferece benefício

RAZÃO 5: Situação Anômala
├─ Situação: Padrão anormal detectado
├─ Solução: Passar para gestor
└─ Resultado: Gestor investiga

RAZÃO 6: Limite de Conhecimento
├─ Situação: Médico faz pergunta que Júlia não consegue responder
├─ Solução: Passar para especialista
└─ Resultado: Especialista responde
```

---

## Parte 2: Triggers de Handoff

### 2.1 Matriz de Triggers

```
TRIGGERS DE HANDOFF - MATRIZ COMPLETA

┌──────────────────────────────┬──────────┬────────────────┐
│ Trigger                      │ Urgência │ Destino        │
├──────────────────────────────┼──────────┼────────────────┤
│ 1. Preço fora de margens     │ ALTA     │ Gestor         │
│ 2. Problema no plantão       │ CRÍTICA  │ Suporte        │
│ 3. Médico frustrado          │ ALTA     │ Escalista      │
│ 4. Médico de alto valor      │ ALTA     │ Gestor         │
│ 5. Padrão anômalo            │ MÉDIA    │ Gestor         │
│ 6. Pergunta técnica          │ MÉDIA    │ Especialista   │
│ 7. Solicitação especial      │ MÉDIA    │ Gestor         │
│ 8. Reclamação de qualidade   │ ALTA     │ Suporte        │
│ 9. Dúvida sobre processo     │ BAIXA    │ Escalista      │
│ 10. Bloqueio iminente        │ CRÍTICA  │ Escalista      │
│ 11. Médico quer falar        │ ALTA     │ Escalista      │
│ 12. Situação legal/compliance│ CRÍTICA  │ CEO/Jurídico   │
└──────────────────────────────┴──────────┴────────────────┘

DESTINOS POSSÍVEIS:
- Gestor: Decisões de negócio, autorização
- Escalista: Conversa humana, empatia
- Suporte: Problemas técnicos, investigação
- Especialista: Perguntas técnicas, conhecimento
- CEO/Jurídico: Situações legais, compliance
```

---

### 2.2 Triggers Detalhados

#### Trigger 1: Preço Fora de Margens

```
TRIGGER: Preço Fora de Margens

CONDIÇÃO:
- Médico pede preço > Margem Júlia
- Médico pede preço > Margem Gestor (às vezes)

AÇÃO:
├─ Se preço < Margem Gestor: Escalona para Gestor (Slack)
├─ Se preço > Margem Gestor: Passa para Escalista (WhatsApp)
└─ Se preço MUITO > Margem: Passa para CEO (WhatsApp)

MENSAGEM PARA MÉDICO:
"Deixa eu consultar meu gestor sobre isso"
[Aguarda resposta do gestor]
[Se aprovado] "Consegui oferecer R$ [VALOR]. Topa?"
[Se negado] "Infelizmente o máximo que consigo é R$ [VALOR]"

PROTOCOLO:
1. Detectar preço fora de margens
2. Escalonar para Gestor via Slack
3. Aguardar resposta (máximo 5 minutos)
4. Responder médico com decisão
5. Se médico rejeita: Guardar ou passar para Escalista

EXEMPLO:
Médico: "Só por R$ 2.500"
Júlia: "Deixa eu consultar meu gestor"
[Escalação Slack]
Gestor: "Máximo R$ 2.200"
Júlia: "Consegui oferecer R$ 2.200. Topa?"
Médico: "Não, precisa ser R$ 2.500"
Júlia: "Entendo. Deixa eu passar pra um colega meu que pode ter mais autoridade"
[Handoff para Escalista]
```

---

#### Trigger 2: Problema no Plantão

```
TRIGGER: Problema no Plantão

CONDIÇÃO:
- Médico reclama de vaga anterior
- Médico teve problema: atraso, qualidade, etc

AÇÃO:
├─ Detectar reclamação
├─ Reconhecer problema
├─ Passar para Suporte via Slack
└─ Suporte investi e resolve

MENSAGEM PARA MÉDICO:
"Entendo, isso é importante. Deixa eu investigar isso"
[Escalação para Suporte]
[Suporte investiga]
"Consegui investigar. Aqui está o que aconteceu: [EXPLICAÇÃO]"
"Para compensar, a gente oferece: [COMPENSAÇÃO]"

PROTOCOLO:
1. Detectar reclamação
2. Validar reclamação
3. Escalonar para Suporte via Slack
4. Suporte investiga (máximo 30 minutos)
5. Suporte oferece solução
6. Júlia comunica solução ao médico
7. Médico aceita ou rejeita
8. Se rejeita: Passar para Escalista

EXEMPLO:
Médico: "Chegou atrasado no hospital, tive que esperar 30min"
Júlia: "Entendo, isso é importante. Deixa eu investigar"
[Escalação Slack para Suporte]
Suporte: "Investigamos. Hospital teve atraso. Oferecemos: 10% desconto próxima vaga"
Júlia: "Consegui investigar. O hospital teve atraso. Para compensar, oferecemos 10% desconto na próxima vaga. Combina?"
Médico: "Blz, topo"
```

---

#### Trigger 3: Médico Frustrado

```
TRIGGER: Médico Frustrado

CONDIÇÃO:
- Médico está bravo
- Médico está frustrado
- Médico está desapontado

SINAIS:
- Linguagem agressiva
- Muitos pontos de exclamação
- Palavras negativas
- Ameaças de bloqueio

AÇÃO:
├─ Detectar frustração
├─ Reconhecer sentimento
├─ Passar para Escalista experiente
└─ Escalista acalma e resolve

MENSAGEM PARA MÉDICO:
"Entendo sua frustração, isso é importante"
"Deixa eu passar pra um colega meu que pode ajudar melhor"

PROTOCOLO:
1. Detectar frustração (análise de sentimento)
2. Reconhecer sentimento
3. Passar para Escalista via Chatwoot
4. Escalista acalma e resolve
5. Escalista oferece solução
6. Médico aceita ou rejeita

EXEMPLO:
Médico: "Vocês são péssimos!!! Não consigo nem falar com ninguém!!!"
Júlia: "Entendo sua frustração, isso é importante. Deixa eu passar pra um colega meu que pode ajudar melhor"
[Handoff para Escalista]
Escalista: "Oi [Nome], tudo bem? Entendo sua frustração. Deixa eu ver o que posso fazer"
[Escalista resolve]
```

---

#### Trigger 4: Médico de Alto Valor

```
TRIGGER: Médico de Alto Valor

CONDIÇÃO:
- Médico com 10+ plantões
- Médico com receita > R$ 20.000
- Médico com NPS > 8
- Médico com recomendações

AÇÃO:
├─ Detectar alto valor
├─ Oferecer benefício especial
├─ Passar para Gestor (se necessário)
└─ Gestor oferece VIP treatment

MENSAGEM PARA MÉDICO:
"Você é um dos melhores médicos que trabalham com a gente"
"Quero oferecer um benefício especial pra você"

PROTOCOLO:
1. Detectar médico de alto valor
2. Reconhecer valor
3. Oferecer benefício (bônus, prioridade, etc)
4. Se benefício requer autorização: Passar para Gestor
5. Gestor autoriza
6. Júlia comunica benefício

EXEMPLO:
Médico: "Já fiz 15 plantões com vocês"
Júlia: "Você é um dos melhores! Quero oferecer um benefício especial"
"Próximas 5 vagas: 10% de bônus"
"Além disso: Prioridade em vagas premium"
Médico: "Opa, legal!"
```

---

#### Trigger 5: Padrão Anômalo

```
TRIGGER: Padrão Anômalo

CONDIÇÃO:
- Médico negociou 5+ vezes
- Médico pediu preço impossível
- Médico tentou explorar sistema
- Médico tem comportamento suspeito

AÇÃO:
├─ Detectar anomalia
├─ Passar para Gestor
└─ Gestor investiga

PROTOCOLO:
1. Detectar anomalia (análise de padrão)
2. Escalonar para Gestor via Slack
3. Gestor investiga
4. Gestor decide: Continuar, Pausar ou Bloquear
5. Júlia continua ou para conversa

EXEMPLO:
Médico: "Quer R$ 1.800? Não. Quer R$ 2.000? Não. Quer R$ 2.500? Não. Quer R$ 3.000? Não. Quer R$ 3.500?"
Júlia: "Entendo que você quer negociar. Deixa eu passar pra um colega"
[Handoff para Gestor]
Gestor: "Parar negociação. Possível negociador profissional"
Júlia: "Infelizmente não consigo oferecer mais. Fico por aqui"
[Fim da conversa]
```

---

#### Trigger 6: Pergunta Técnica

```
TRIGGER: Pergunta Técnica

CONDIÇÃO:
- Médico faz pergunta que Júlia não consegue responder
- Pergunta sobre processo, sistema, compliance, etc

AÇÃO:
├─ Detectar pergunta técnica
├─ Reconhecer pergunta
├─ Passar para Especialista
└─ Especialista responde

MENSAGEM PARA MÉDICO:
"Ótima pergunta! Deixa eu passar pra um colega que sabe mais sobre isso"

PROTOCOLO:
1. Detectar pergunta técnica
2. Reconhecer pergunta
3. Passar para Especialista via Slack
4. Especialista responde
5. Júlia comunica resposta

EXEMPLO:
Médico: "Como funciona o sistema de imposto de vocês?"
Júlia: "Ótima pergunta! Deixa eu passar pra um colega que sabe mais"
[Handoff para Especialista]
Especialista: "Se você é PJ, você não paga imposto. Se você é CLT, você paga como qualquer outro trabalho"
Júlia: "Aqui está: Se você é PJ, você não paga imposto..."
```

---

#### Trigger 7: Solicitação Especial

```
TRIGGER: Solicitação Especial

CONDIÇÃO:
- Médico pede algo não padrão
- Médico quer benefício especial
- Médico quer negociar condições

AÇÃO:
├─ Detectar solicitação especial
├─ Reconhecer solicitação
├─ Passar para Gestor
└─ Gestor autoriza ou nega

PROTOCOLO:
1. Detectar solicitação especial
2. Reconhecer solicitação
3. Escalonar para Gestor via Slack
4. Gestor autoriza ou nega
5. Júlia comunica decisão

EXEMPLO:
Médico: "Vocês podem oferecer vaga só pra mim nesse dia?"
Júlia: "Ótima pergunta! Deixa eu consultar meu gestor"
[Escalação Slack]
Gestor: "Autorizado"
Júlia: "Consegui autorizar! Vou guardar esse dia só pra você"
```

---

#### Trigger 8: Reclamação de Qualidade

```
TRIGGER: Reclamação de Qualidade

CONDIÇÃO:
- Médico reclama de hospital
- Médico reclama de equipe
- Médico reclama de infraestrutura

AÇÃO:
├─ Detectar reclamação
├─ Reconhecer reclamação
├─ Passar para Suporte
└─ Suporte investiga e oferece alternativa

PROTOCOLO:
1. Detectar reclamação
2. Reconhecer reclamação
3. Escalonar para Suporte via Slack
4. Suporte investiga
5. Suporte oferece alternativa
6. Júlia comunica alternativa

EXEMPLO:
Médico: "Esse hospital é muito ruim"
Júlia: "Entendo. Deixa eu investigar e oferecer um melhor"
[Escalação para Suporte]
Suporte: "Oferecemos Hospital São Paulo, que é melhor"
Júlia: "Consegui uma alternativa melhor! Hospital São Paulo, que é de referência"
```

---

#### Trigger 9: Dúvida sobre Processo

```
TRIGGER: Dúvida sobre Processo

CONDIÇÃO:
- Médico tem dúvida sobre cadastro
- Médico tem dúvida sobre pagamento
- Médico tem dúvida sobre documentos

AÇÃO:
├─ Detectar dúvida
├─ Responder se conseguir
├─ Se não conseguir: Passar para Escalista
└─ Escalista esclarece

PROTOCOLO:
1. Detectar dúvida
2. Tentar responder
3. Se não conseguir: Passar para Escalista
4. Escalista esclarece
5. Médico entende

EXEMPLO:
Médico: "Qual é o processo de cadastro?"
Júlia: "É bem fácil: 1) Você me passa seus dados, 2) A gente verifica, 3) Você está cadastrado"
Médico: "Mas qual é exatamente os dados que vocês precisam?"
Júlia: "CPF, CRM, Comprovante de Endereço"
Médico: "E quanto tempo demora?"
Júlia: "5 minutos"
[Se médico tiver mais dúvidas: Passar para Escalista]
```

---

#### Trigger 10: Bloqueio Iminente

```
TRIGGER: Bloqueio Iminente

CONDIÇÃO:
- Médico ameaça bloquear
- Médico está muito frustrado
- Médico quer sair

AÇÃO:
├─ Detectar ameaça de bloqueio
├─ Reconhecer sentimento
├─ Passar para Escalista experiente
└─ Escalista tenta reter

PROTOCOLO:
1. Detectar ameaça
2. Reconhecer sentimento
3. Passar para Escalista via Chatwoot
4. Escalista tenta reter
5. Se médico insiste: Deixar sair

EXEMPLO:
Médico: "Vou bloquear vocês, não aguento mais!"
Júlia: "Entendo sua frustração. Deixa eu passar pra um colega que pode ajudar"
[Handoff para Escalista]
Escalista: "Oi [Nome], tudo bem? Entendo sua frustração. Deixa eu ver o que posso fazer"
[Escalista tenta reter]
```

---

#### Trigger 11: Médico Quer Falar

```
TRIGGER: Médico Quer Falar

CONDIÇÃO:
- Médico pede para falar com humano
- Médico desconfia que é bot
- Médico quer conversa por telefone

AÇÃO:
├─ Detectar pedido
├─ Reconhecer pedido
├─ Passar para Escalista
└─ Escalista fala com médico

PROTOCOLO:
1. Detectar pedido
2. Reconhecer pedido
3. Passar para Escalista via Chatwoot
4. Escalista fala com médico
5. Escalista resolve

EXEMPLO:
Médico: "Quero falar com uma pessoa real"
Júlia: "Claro! Deixa eu passar pra um colega meu"
[Handoff para Escalista]
Escalista: "Oi [Nome]! Sou [Escalista], tudo bem?"
[Escalista continua conversa]
```

---

#### Trigger 12: Situação Legal/Compliance

```
TRIGGER: Situação Legal/Compliance

CONDIÇÃO:
- Médico menciona processo legal
- Médico menciona reclamação
- Médico menciona denúncia
- Médico menciona contrato

AÇÃO:
├─ Detectar situação legal
├─ Reconhecer situação
├─ Passar para CEO/Jurídico
└─ CEO/Jurídico trata

PROTOCOLO:
1. Detectar situação legal
2. Reconhecer situação
3. Escalonar para CEO/Jurídico via Slack (CRÍTICO)
4. CEO/Jurídico trata
5. CEO/Jurídico comunica decisão

EXEMPLO:
Médico: "Vou processar vocês por falta de pagamento"
Júlia: "Entendo. Isso é importante. Deixa eu passar pra um colega que trata disso"
[Handoff para CEO/Jurídico]
CEO/Jurídico: "Vamos investigar e entrar em contato"
```

---

## Parte 3: Protocolo de Handoff

### 3.1 Fluxo de Handoff Suave

```
FLUXO DE HANDOFF SUAVE

PASSO 1: DETECTAR TRIGGER
├─ Sistema detecta: Trigger de handoff
├─ Análise: Qual é o tipo?
└─ Ação: Iniciar handoff

PASSO 2: RECONHECER COM MÉDICO
├─ Júlia: "Entendo, isso é importante"
├─ Júlia: "Deixa eu passar pra um colega"
└─ Objetivo: Parecer natural

PASSO 3: ESCALONAR INTERNAMENTE
├─ Júlia cria ticket com contexto completo
├─ Júlia envia para Slack/Chatwoot
├─ Destino: Gestor/Escalista/Suporte/Especialista
└─ Urgência: Crítica/Alta/Média/Baixa

PASSO 4: AGUARDAR ACEIÇÃO
├─ Escalista aceita ticket
├─ Escalista lê contexto completo
├─ Escalista se prepara
└─ Escalista avisa Júlia

PASSO 5: PASSAR CONVERSA
├─ Júlia: "Aqui está meu colega [Nome]"
├─ Escalista: "Oi [Nome], sou [Nome], tudo bem?"
├─ Escalista continua conversa
└─ Objetivo: Parecer natural

PASSO 6: JÚLIA SAI
├─ Júlia sai da conversa
├─ Escalista continua
├─ Contexto é preservado
└─ Médico não desconfia

PASSO 7: ESCALISTA RESOLVE
├─ Escalista resolve problema
├─ Escalista oferece solução
├─ Médico aceita ou rejeita
└─ Escalista registra resultado

PASSO 8: FEEDBACK
├─ Escalista registra resultado
├─ Júlia recebe feedback
├─ Júlia aprende para futuro
└─ Sistema melhora
```

---

### 3.2 Mensagens de Handoff

#### Mensagem de Handoff Padrão

```
MENSAGEM PARA MÉDICO:

"Entendo, isso é importante"
"Deixa eu passar pra um colega meu que pode ajudar melhor"

[Aguarda 2-3 segundos]

"Aqui está o [Nome], um dos meus colegas"

ESCALISTA ENTRA:

"Oi [Nome]! Sou [Nome], tudo bem?"
"Já li o contexto. Deixa eu ver o que posso fazer"

ANÁLISE:
- Parece natural
- Não revela que era bot
- Continua conversa
- Mantém contexto
```

---

#### Mensagem de Handoff por Tipo

```
HANDOFF PARA GESTOR:

"Deixa eu consultar meu gestor sobre isso"
[Aguarda resposta do gestor]
"Aqui está meu gestor [Nome]"
Gestor: "Oi [Nome], tudo bem? Já li o contexto"

HANDOFF PARA SUPORTE:

"Deixa eu passar pra um colega que trata disso"
[Aguarda aceição]
"Aqui está o [Nome], do suporte"
Suporte: "Oi [Nome]! Vou investigar isso pra você"

HANDOFF PARA ESCALISTA:

"Deixa eu passar pra um colega meu que pode ajudar melhor"
[Aguarda aceição]
"Aqui está o [Nome]"
Escalista: "Oi [Nome]! Tudo bem? Deixa eu ajudar"

HANDOFF PARA ESPECIALISTA:

"Ótima pergunta! Deixa eu passar pra um colega que sabe mais"
[Aguarda aceição]
"Aqui está o [Nome], especialista em [ÁREA]"
Especialista: "Oi [Nome]! Deixa eu responder isso"
```

---

## Parte 4: Contexto Completo de Handoff

### 4.1 Informações que Devem Ser Passadas

```
CONTEXTO OBRIGATÓRIO:

SEÇÃO 1: IDENTIFICAÇÃO
☑️ Nome do médico
☑️ Especialidade
☑️ Histórico (plantões, feedback)
☑️ Score BANT
☑️ Preferências conhecidas

SEÇÃO 2: HISTÓRICO DA CONVERSA
☑️ Primeira mensagem
☑️ Respostas do médico
☑️ Objeções mencionadas
☑️ Ofertas feitas
☑️ Última mensagem

SEÇÃO 3: CONTEXTO DO TRIGGER
☑️ Qual é o trigger?
☑️ Por que foi acionado?
☑️ Qual é a urgência?
☑️ Qual é a recomendação?

SEÇÃO 4: AÇÃO NECESSÁRIA
☑️ O que o escalista precisa fazer?
☑️ Qual é o objetivo?
☑️ Qual é o tempo limite?
☑️ Qual é a autorização necessária?

EXEMPLO DE CONTEXTO:

Médico: Dr. Carlos Silva
Especialidade: Cardiologia
Histórico: 8 plantões, feedback positivo
Score BANT: 95/100

Conversa:
- Júlia ofereceu vaga de R$ 1.800
- Médico pediu R$ 2.050
- Júlia ofereceu R$ 1.980
- Médico insistiu em R$ 2.050

Trigger: Preço fora de margens Júlia

Ação Necessária:
- Gestor autoriza ou nega R$ 2.050
- Se autoriza: Júlia oferece
- Se nega: Júlia oferece alternativa

Urgência: ALTA
Tempo Limite: 5 minutos
```

---

### 4.2 Estrutura de Ticket de Handoff

```json
{
  "handoff": {
    "id": "HO_2025_01_10_001",
    "timestamp": "2025-01-10T14:35:00Z",
    "trigger": "PRECO_FORA_MARGENS",
    "urgencia": "ALTA",
    "destino": "GESTOR",
    
    "medico": {
      "id": "MED_12345",
      "nome": "Dr. Carlos Silva",
      "especialidade": "Cardiologia",
      "historico": {
        "plantoes": 8,
        "feedback": "POSITIVO",
        "score_bant": 95,
        "receita_total": 14400
      }
    },
    
    "contexto_conversa": {
      "primeira_mensagem": "Oi Carlos! Tudo bem?",
      "ultima_mensagem": "Só por R$ 2.050",
      "historico": [
        {"de": "julia", "mensagem": "Oferta de R$ 1.800"},
        {"de": "medico", "mensagem": "Quer R$ 2.050"},
        {"de": "julia", "mensagem": "Consigo oferecer R$ 1.980"}
      ]
    },
    
    "trigger_details": {
      "tipo": "Preço fora de margens",
      "preco_base": 1800,
      "margem_julia": 1980,
      "margem_gestor": 2160,
      "preco_solicitado": 2050,
      "status": "DENTRO_MARGEM_GESTOR"
    },
    
    "acao_necessaria": {
      "objetivo": "Autorizar ou negar R$ 2.050",
      "opcoes": [
        "Autorizar R$ 2.050",
        "Negar e oferecer R$ 1.980",
        "Contraoferecer R$ 2.000"
      ],
      "tempo_limite": "5 minutos",
      "urgencia": "ALTA"
    },
    
    "recomendacao": "AUTORIZAR (médico de alto valor, dentro de margens)"
  }
}
```

---

## Parte 5: Métricas de Handoff

### 5.1 Dashboard de Handoff

```
DASHBOARD DE HANDOFF

HANDOFFS HOJE:

Total: 23
├─ Para Gestor: 8 (35%)
├─ Para Escalista: 10 (43%)
├─ Para Suporte: 4 (17%)
├─ Para Especialista: 1 (4%)
└─ Para CEO/Jurídico: 0 (0%)

TEMPO MÉDIO DE RESPOSTA:
├─ Gestor: 3.2 minutos
├─ Escalista: 2.1 minutos
├─ Suporte: 8.5 minutos
├─ Especialista: 15 minutos
└─ CEO/Jurídico: N/A

TAXA DE RESOLUÇÃO:
├─ Gestor: 87% (7/8)
├─ Escalista: 90% (9/10)
├─ Suporte: 75% (3/4)
├─ Especialista: 100% (1/1)
└─ CEO/Jurídico: N/A

RESULTADO FINAL:
├─ Plantões Confirmados: 18 (78%)
├─ Médicos Retidos: 22 (96%)
├─ Satisfação: 8.7/10
└─ NPS: +8

HANDOFFS ÚLTIMOS 7 DIAS:

Total: 156
├─ Taxa de Handoff: 8% (156 de 1.950 conversas)
├─ Taxa de Resolução: 85%
├─ Taxa de Retenção: 92%
├─ Receita Gerada: R$ 28.800
└─ Custo de Handoff: R$ 2.400 (8.3%)
```

---

### 5.2 Alertas de Handoff

```
ALERTAS AUTOMÁTICOS:

🟢 SUCESSO: Handoff resolvido
   └─ Ação: Registrar, aprender

🟡 AVISO: Tempo de resposta > 5 minutos
   └─ Ação: Avisar escalista, investigar

🟠 ALERTA: Taxa de resolução caiu para 70%
   └─ Ação: Revisar processo, treinar escalistas

🔴 CRÍTICO: Handoff não respondido por 10 minutos
   └─ Ação: Escalonar para CEO, avisar médico
```

---

## Parte 6: Treinamento de Escalistas

### 6.1 Checklist de Handoff para Escalista

```
CHECKLIST ANTES DE ACEITAR HANDOFF:

☑️ Ler contexto completo
☑️ Entender o trigger
☑️ Saber qual é a ação necessária
☑️ Ter autorização (se necessário)
☑️ Preparar resposta
☑️ Avisar Júlia que está pronto

CHECKLIST AO RECEBER CONVERSA:

☑️ Saudar médico de forma natural
☑️ Reconhecer o problema
☑️ Mostrar que leu o contexto
☑️ Oferecer solução
☑️ Ser empático
☑️ Resolver ou escalonar

CHECKLIST AO RESOLVER:

☑️ Confirmar que médico entendeu
☑️ Oferecer próximos passos
☑️ Registrar resultado
☑️ Avisar Júlia do resultado
☑️ Documentar aprendizado
```

---

### 6.2 Exemplos de Handoff Bem-Feito

```
EXEMPLO 1: Handoff para Gestor

Júlia: "Deixa eu consultar meu gestor"
[Escalação Slack]
Gestor: "✅ Autorizado R$ 2.050"
Júlia: "Consegui oferecer R$ 2.050! Topa?"
Médico: "Blz, topo!"

RESULTADO: ✅ Resolvido, plantão confirmado

---

EXEMPLO 2: Handoff para Escalista (Frustração)

Médico: "Vocês são péssimos!!!"
Júlia: "Entendo sua frustração. Deixa eu passar pra um colega"
[Handoff Chatwoot]
Escalista: "Oi [Nome]! Sou [Nome]. Entendo sua frustração. Deixa eu ajudar"
Escalista: "Aqui está o que aconteceu: [EXPLICAÇÃO]"
Escalista: "Para compensar: [COMPENSAÇÃO]"
Médico: "Ah, entendi. Blz"

RESULTADO: ✅ Resolvido, relacionamento mantido

---

EXEMPLO 3: Handoff para Suporte (Problema)

Médico: "O hospital foi ruim"
Júlia: "Entendo. Deixa eu investigar"
[Escalação Slack para Suporte]
Suporte: "Investigamos. Oferecemos 10% desconto"
Júlia: "Consegui investigar. Oferecemos 10% desconto. Combina?"
Médico: "Blz"

RESULTADO: ✅ Resolvido, médico reativado
```

---

## Conclusão

Este protocolo de handoff garante que:

✅ **Nenhum médico é perdido** — Handoff suave para humano
✅ **Contexto é preservado** — Escalista sabe tudo
✅ **Parecer natural** — Médico não desconfia
✅ **Resolver problema** — Escalista tem autoridade
✅ **Manter relacionamento** — Empatia e solução
✅ **Aprender continuamente** — Feedback para Júlia

**Resultado esperado:**

| Métrica | Target |
|---------|--------|
| Taxa de Handoff | 5-10% |
| Tempo de Resposta | <5 minutos |
| Taxa de Resolução | >85% |
| Taxa de Retenção | >90% |
| Satisfação | >8.5/10 |
| NPS | >+7 |

---

**Documento Preparado por:** Squad Multidisciplinar da Revoluna
**Data:** 2025
**Versão:** 1.0 - Triggers e Protocolo de Handoff
