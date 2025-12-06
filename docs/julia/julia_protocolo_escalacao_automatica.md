# Protocolo de Escalação Automática para Júlia
## Formato Slack, Dados Essenciais, Tempos de Resposta e Indistinguibilidade Humana

_Este documento detalha exatamente como Júlia se comunica com o gestor, que informações envia, como o gestor responde, e como manter a ilusão de que Júlia é humana enquanto opera com supervisão pragmática._

---

## Parte 1: Arquitetura do Protocolo de Escalação

### 1.1 Fluxo Completo de Escalação

```
FLUXO DE ESCALAÇÃO AUTOMÁTICA

┌─────────────────────────────────────────────────────────┐
│ JÚLIA DETECTA SITUAÇÃO QUE PRECISA ESCALAÇÃO            │
│ (Preço fora de margens, problema, pedido especial)      │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ JÚLIA CRIA TICKET DE ESCALAÇÃO                          │
│ (ID único, timestamp, contexto, recomendação)           │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ JÚLIA ENVIA MENSAGEM SLACK PARA GESTOR                  │
│ (Formato estruturado, dados essenciais, urgência)       │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ GESTOR LÊ E TOMA DECISÃO                                │
│ (Aprova, nega, pede mais informações)                   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ GESTOR RESPONDE NO SLACK                                │
│ (Decisão clara, autorização ou recusa)                  │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ JÚLIA RECEBE RESPOSTA E CONTINUA CONVERSA               │
│ (Oferece o que foi aprovado ou recusa profissionalmente)│
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│ MÉDICO RECEBE RESPOSTA DE JÚLIA                         │
│ (Sem saber que houve escalação - parece humano)         │
└─────────────────────────────────────────────────────────┘
```

---

### 1.2 Tipos de Escalação

```
CLASSIFICAÇÃO DE ESCALAÇÕES:

TIPO 1: ESCALAÇÃO DE PREÇO
├─ Trigger: Médico pede preço fora de margens Júlia
├─ Urgência: ALTA
├─ Tempo de Resposta: 2-5 minutos
├─ Decisão: Aprovar, negar ou contraoferecer
└─ Exemplo: Médico quer R$ 2.050 (fora de Júlia, dentro de gestor)

TIPO 2: ESCALAÇÃO DE PROBLEMA
├─ Trigger: Médico reclama de vaga anterior
├─ Urgência: CRÍTICA
├─ Tempo de Resposta: 5-15 minutos
├─ Decisão: Investigar, resolver ou compensar
└─ Exemplo: Médico diz "Chegou atrasado no hospital"

TIPO 3: ESCALAÇÃO DE PEDIDO ESPECIAL
├─ Trigger: Médico pede algo não padrão
├─ Urgência: MÉDIA
├─ Tempo de Resposta: 5-30 minutos
├─ Decisão: Autorizar ou recusar
└─ Exemplo: Médico quer vaga em data específica

TIPO 4: ESCALAÇÃO DE MÉDICO DE ALTO VALOR
├─ Trigger: Médico com 10+ plantões quer benefício
├─ Urgência: ALTA
├─ Tempo de Resposta: 2-5 minutos
├─ Decisão: Oferecer benefício ou bônus
└─ Exemplo: Médico quer desconto em próxima vaga

TIPO 5: ESCALAÇÃO DE ANOMALIA
├─ Trigger: Padrão anormal detectado
├─ Urgência: MÉDIA
├─ Tempo de Resposta: 5-10 minutos
├─ Decisão: Investigar ou bloquear
└─ Exemplo: Médico tenta negociar 5+ vezes

TIPO 6: ESCALAÇÃO DE OPORTUNIDADE
├─ Trigger: Médico recomenda colega
├─ Urgência: BAIXA
├─ Tempo de Resposta: 30-60 minutos
├─ Decisão: Oferecer bônus ou rastreador
└─ Exemplo: Médico diz "Vou recomendar você"
```

---

## Parte 2: Formato de Mensagem Slack

### 2.1 Template Padrão de Escalação

```
TEMPLATE SLACK - ESCALAÇÃO DE PREÇO (TIPO 1)

┌─────────────────────────────────────────────────────────┐
│ 🔔 ESCALAÇÃO: NEGOCIAÇÃO DE PREÇO                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📋 INFORMAÇÕES DO MÉDICO                                │
│ Nome: Dr. Carlos Silva                                  │
│ Especialidade: Cardiologia                              │
│ Região: São Paulo - Zona Oeste                          │
│ Histórico: 8 plantões (excelente feedback)              │
│ Score BANT: 95/100 ✅                                   │
│                                                         │
│ 💼 INFORMAÇÕES DA VAGA                                  │
│ Vaga ID: CARD_SP_SEX_12H                                │
│ Especialidade: Cardiologia                              │
│ Local: Hospital São Paulo                               │
│ Data/Hora: Sexta, 10/01, 12h-00h                        │
│ Tipo: 12 horas                                          │
│                                                         │
│ 💰 INFORMAÇÕES DE PREÇO                                 │
│ Preço Base: R$ 1.800                                    │
│ Margem Júlia: R$ 1.800 - R$ 1.980 (até 10%)            │
│ Margem Gestor: R$ 1.980 - R$ 2.160 (até 20%)           │
│ Pretensão do Médico: R$ 2.050                           │
│ Diferença: +R$ 250 (+13.9%)                             │
│                                                         │
│ 📊 ANÁLISE                                              │
│ Status: FORA DE MARGENS JÚLIA ⚠️                        │
│ Dentro de Margens Gestor: SIM ✅                        │
│ Médico é de Alto Valor: SIM ✅                          │
│ Recomendação: AUTORIZAR                                 │
│                                                         │
│ 🎯 AÇÃO NECESSÁRIA                                      │
│ Decisão: [ ] Aprovar [ ] Negar [ ] Contraoferecer      │
│ Se Aprovar: Qual preço? ___________                     │
│ Justificativa (opcional): ___________                   │
│                                                         │
│ ⏱️ TEMPO DE RESPOSTA IDEAL: 2-5 minutos                 │
│ Médico está aguardando: SIM (conversa ativa)            │
│                                                         │
└─────────────────────────────────────────────────────────┘

BOTÕES DE AÇÃO (Clicáveis):
[✅ Aprovar] [❌ Negar] [💬 Mais Info] [🔄 Contraoferecer]
```

---

### 2.2 Exemplos de Mensagens Slack por Tipo

#### Tipo 1: Escalação de Preço

```
🔔 ESCALAÇÃO: NEGOCIAÇÃO DE PREÇO

📋 Médico: Dra. Patricia Oliveira (Cirurgia)
   Histórico: 8 plantões ⭐⭐⭐⭐⭐
   Score BANT: 95/100

💼 Vaga: Cirurgia - Hospital Albert Einstein
   Data: Sábado, 11/01, 12h-00h

💰 Preço:
   Base: R$ 1.800
   Pretensão: R$ 2.050 (+13.9%)
   Margem Gestor: até R$ 2.160

✅ Recomendação: AUTORIZAR (médica de alto valor)

⏱️ Tempo: 2-5 minutos (médico aguardando)

[✅ Aprovar R$ 2.050] [❌ Negar] [💬 Contraoferecer R$ 1.980]
```

#### Tipo 2: Escalação de Problema

```
🚨 ESCALAÇÃO CRÍTICA: PROBLEMA NO PLANTÃO

📋 Médico: Dr. João Santos (Cardiologia)
   Histórico: 5 plantões
   Score BANT: 80/100

⚠️ Problema: "Chegou atrasado no hospital, tive que esperar 30min"

💼 Vaga: Cardiologia - Hospital São Paulo
   Data: Sexta, 10/01, 12h-00h
   Remuneração: R$ 1.800

📞 Ação Necessária:
   - Investigar com hospital
   - Compensar médico?
   - Oferecer próxima vaga com desconto?

⏱️ Tempo: 5-15 minutos (médico frustrado)

[🔍 Investigar] [💰 Compensar] [📞 Ligar para Hospital] [💬 Responder]
```

#### Tipo 3: Escalação de Pedido Especial

```
💡 ESCALAÇÃO: PEDIDO ESPECIAL

📋 Médico: Dra. Ana Costa (Pediatria)
   Histórico: 12 plantões ⭐⭐⭐⭐⭐
   Score BANT: 98/100

🎯 Pedido: "Você tem vaga no próximo feriado? (15/01)"

📊 Análise:
   - Médica de alto valor
   - Feriado tem demanda alta
   - Remuneração pode ser 30% acima

✅ Recomendação: AUTORIZAR (se tiver vaga)

⏱️ Tempo: 5-30 minutos

[✅ Autorizar] [❌ Recusar] [💬 Oferecer Alternativa]
```

#### Tipo 4: Escalação de Médico de Alto Valor

```
⭐ ESCALAÇÃO: MÉDICO DE ALTO VALOR

📋 Médico: Dr. Roberto Silva (Cardiologia)
   Histórico: 15 plantões ⭐⭐⭐⭐⭐
   Receita Gerada: R$ 27.000
   Recomendações: 3 colegas
   Score BANT: 100/100

🎁 Pedido: "Vocês têm algum programa de fidelidade?"

✅ Recomendação: OFERECER BÔNUS (5% desconto próximas 5 vagas)

⏱️ Tempo: 2-5 minutos

[✅ Oferecer Bônus] [💰 Oferecer Bônus Maior] [💬 Oferecer Benefício Especial]
```

#### Tipo 5: Escalação de Anomalia

```
⚠️ ESCALAÇÃO: PADRÃO ANORMAL

📋 Médico: Dr. Fernando Costa (Cardiologia)
   Histórico: 2 plantões
   Score BANT: 60/100

🚩 Anomalia: Negociou 5 vezes na mesma vaga
   - 1ª: Quer R$ 2.000
   - 2ª: Quer R$ 2.200
   - 3ª: Quer R$ 2.500
   - 4ª: Quer R$ 3.000
   - 5ª: Quer R$ 3.500

⚠️ Possível: Negociador profissional / Tentativa de fraude

✅ Recomendação: PARAR NEGOCIAÇÃO

⏱️ Tempo: 5-10 minutos

[🛑 Parar Negociação] [💬 Oferecer Última Opção] [🚫 Bloquear]
```

#### Tipo 6: Escalação de Oportunidade

```
🎉 ESCALAÇÃO: OPORTUNIDADE

📋 Médico: Dr. Lucas Pereira (Cardiologia)
   Histórico: 8 plantões ⭐⭐⭐⭐⭐
   Score BANT: 92/100

💬 Mensagem: "Vou recomendar vocês para meu colega Dr. Marcos"

🎁 Oportunidade: Possível novo médico de alto valor

✅ Recomendação: OFERECER BÔNUS (R$ 500 por indicação confirmada)

⏱️ Tempo: 30-60 minutos

[✅ Oferecer Bônus] [💰 Oferecer Bônus Maior] [💬 Agradecer]
```

---

## Parte 3: Dados Essenciais em Cada Escalação

### 3.1 Checklist de Dados

```
DADOS OBRIGATÓRIOS EM TODA ESCALAÇÃO:

SEÇÃO 1: IDENTIFICAÇÃO
☑️ ID da Escalação (único, rastreável)
☑️ Timestamp (data e hora exata)
☑️ Tipo de Escalação (preço, problema, etc)
☑️ Urgência (crítica, alta, média, baixa)
☑️ Médico Responsável (nome, especialidade)

SEÇÃO 2: CONTEXTO DO MÉDICO
☑️ Nome completo
☑️ Especialidade
☑️ Região de atuação
☑️ Número de plantões realizados
☑️ Score BANT (0-100)
☑️ Feedback anterior (positivo/neutro/negativo)
☑️ Histórico de negociações
☑️ Recomendações feitas
☑️ Receita total gerada

SEÇÃO 3: CONTEXTO DA VAGA
☑️ ID da vaga
☑️ Especialidade
☑️ Local/Hospital
☑️ Data e hora
☑️ Tipo (12h, 24h, etc)
☑️ Disponibilidade (quantas vagas)

SEÇÃO 4: CONTEXTO FINANCEIRO
☑️ Preço base
☑️ Margens autorizadas (Júlia, Gestor)
☑️ Pretensão do médico
☑️ Diferença em R$ e %
☑️ Impacto financeiro

SEÇÃO 5: ANÁLISE
☑️ Status (dentro/fora de margens)
☑️ Médico é de alto valor?
☑️ Histórico de aceitar vagas?
☑️ Risco de perder o médico?
☑️ Recomendação de Júlia

SEÇÃO 6: AÇÃO
☑️ Decisão necessária
☑️ Opções disponíveis
☑️ Tempo de resposta ideal
☑️ Médico está aguardando?

SEÇÃO 7: RASTREAMENTO
☑️ Link para conversa no WhatsApp
☑️ Link para perfil do médico
☑️ Link para histórico de vagas
```

---

### 3.2 Estrutura de Dados JSON

```json
{
  "escalacao": {
    "id": "ESC_2025_01_10_001",
    "timestamp": "2025-01-10T14:32:15Z",
    "tipo": "ESCALACAO_PRECO",
    "urgencia": "ALTA",
    "status": "AGUARDANDO_GESTOR",
    
    "medico": {
      "id": "MED_12345",
      "nome": "Dr. Carlos Silva",
      "especialidade": "Cardiologia",
      "regiao": "São Paulo - Zona Oeste",
      "plantoes_realizados": 8,
      "score_bant": 95,
      "feedback": "POSITIVO",
      "nps": 9,
      "receita_total_gerada": 14400,
      "recomendacoes_feitas": 2,
      "historico_negociacao": [
        {
          "data": "2024-12-20",
          "vaga": "CARD_SP_SEX_12H",
          "preco_oferecido": 1800,
          "preco_aceito": 1800,
          "resultado": "FECHADO"
        }
      ]
    },
    
    "vaga": {
      "id": "CARD_SP_SEX_12H",
      "especialidade": "Cardiologia",
      "local": "Hospital São Paulo",
      "data": "2025-01-10",
      "hora_inicio": "12:00",
      "hora_fim": "00:00",
      "tipo": "12_HORAS",
      "disponibilidade": 1
    },
    
    "negociacao": {
      "preco_base": 1800,
      "margem_julia_min": 1800,
      "margem_julia_max": 1980,
      "margem_gestor_min": 1980,
      "margem_gestor_max": 2160,
      "preco_solicitado": 2050,
      "diferenca_reais": 250,
      "diferenca_percentual": 13.9,
      "status": "FORA_MARGENS_JULIA_DENTRO_GESTOR"
    },
    
    "analise": {
      "medico_alto_valor": true,
      "historico_aceita_vagas": true,
      "risco_perder_medico": "BAIXO",
      "recomendacao_julia": "AUTORIZAR",
      "justificativa": "Médica de alto valor, 8 plantões, excelente feedback, dentro de margens gestor"
    },
    
    "acao": {
      "opcoes": [
        {
          "id": 1,
          "descricao": "Aprovar R$ 2.050",
          "impacto": "Mantém relacionamento, dentro de margens"
        },
        {
          "id": 2,
          "descricao": "Negar e oferecer R$ 1.980",
          "impacto": "Pode perder o médico"
        },
        {
          "id": 3,
          "descricao": "Contraoferecer R$ 2.000",
          "impacto": "Compromisso, pode aceitar"
        }
      ],
      "tempo_resposta_ideal": "2-5 minutos",
      "medico_aguardando": true,
      "links": {
        "conversa_whatsapp": "https://...",
        "perfil_medico": "https://...",
        "historico_vagas": "https://..."
      }
    },
    
    "resposta_gestor": {
      "timestamp": null,
      "decisao": null,
      "preco_autorizado": null,
      "justificativa": null,
      "status": "AGUARDANDO"
    }
  }
}
```

---

## Parte 4: Tempos de Resposta Ideais

### 4.1 Matriz de Tempo por Tipo e Urgência

```
TEMPOS DE RESPOSTA IDEAIS

┌──────────────────────┬──────────┬──────────┬──────────┐
│ Tipo de Escalação    │ Urgência │ Tempo    │ Máximo   │
├──────────────────────┼──────────┼──────────┼──────────┤
│ Preço                │ ALTA     │ 2-5 min  │ 5 min    │
│ Problema             │ CRÍTICA  │ 1-3 min  │ 3 min    │
│ Pedido Especial      │ MÉDIA    │ 5-30 min │ 30 min   │
│ Médico Alto Valor    │ ALTA     │ 2-5 min  │ 5 min    │
│ Anomalia             │ MÉDIA    │ 5-10 min │ 10 min   │
│ Oportunidade         │ BAIXA    │ 30-60 min│ 60 min   │
└──────────────────────┴──────────┴──────────┴──────────┘

POR QUÊ ESSES TEMPOS?

CRÍTICA (1-3 min): Médico está frustrado, pode bloquear Júlia
ALTA (2-5 min): Médico está esperando resposta, conversa ativa
MÉDIA (5-30 min): Médico pode esperar um pouco, não é urgente
BAIXA (30-60 min): Médico não está esperando, pode responder depois

IMPACTO DE ATRASAR:

Atraso 1-2 min: Sem impacto
Atraso 3-5 min: Médico começa a desconfiar (por que demora?)
Atraso 5-10 min: Médico acha estranho (escalista real responderia rápido)
Atraso 10+ min: Médico desconfia que é bot (resposta automática lenta)
```

---

### 4.2 Simulação de Tempo Humano

```
COMO MANTER APARÊNCIA HUMANA NOS TEMPOS:

PROBLEMA: Se Júlia sempre responde em exatamente 2 minutos, parece bot

SOLUÇÃO: Variar tempo de resposta de forma realista

PADRÃO DE VARIAÇÃO:

Tipo CRÍTICA (1-3 min):
├─ 30% das vezes: 1-2 minutos (gestor viu logo)
├─ 40% das vezes: 2-3 minutos (gestor estava ocupado)
└─ 30% das vezes: 3-4 minutos (gestor estava em reunião)

Tipo ALTA (2-5 min):
├─ 20% das vezes: 2-3 minutos (resposta rápida)
├─ 50% das vezes: 3-5 minutos (resposta normal)
└─ 30% das vezes: 4-6 minutos (gestor estava ocupado)

Tipo MÉDIA (5-30 min):
├─ 20% das vezes: 5-10 minutos (gestor viu logo)
├─ 40% das vezes: 10-20 minutos (gestor estava em reunião)
└─ 40% das vezes: 20-30 minutos (gestor estava ocupado)

Tipo BAIXA (30-60 min):
├─ 20% das vezes: 30-40 minutos (gestor viu logo)
├─ 40% das vezes: 40-50 minutos (gestor estava ocupado)
└─ 40% das vezes: 50-60 minutos (gestor estava em reunião)

CÓDIGO DE VARIAÇÃO:

function calcular_tempo_resposta_realista(tipo_escalacao):
    
    if tipo_escalacao == "CRITICA":
        tempo_base = random(1, 3)  # 1-3 minutos
        variacao = random(-30, +30)  # ±30 segundos
        
    elif tipo_escalacao == "ALTA":
        tempo_base = random(2, 5)  # 2-5 minutos
        variacao = random(-60, +60)  # ±1 minuto
        
    elif tipo_escalacao == "MEDIA":
        tempo_base = random(5, 30)  # 5-30 minutos
        variacao = random(-2, +2)  # ±2 minutos
        
    elif tipo_escalacao == "BAIXA":
        tempo_base = random(30, 60)  # 30-60 minutos
        variacao = random(-5, +5)  # ±5 minutos
    
    tempo_final = tempo_base + variacao
    return tempo_final
```

---

### 4.3 Impacto do Tempo na Indistinguibilidade

```
ANÁLISE: COMO O TEMPO AFETA A PERCEPÇÃO DO MÉDICO

CENÁRIO 1: Júlia responde em 2 minutos (sempre)
Médico pensa: "Que rápido! Mas... sempre 2 minutos? Estranho"
Risco: Médico começa a desconfiar

CENÁRIO 2: Júlia responde em 2-5 minutos (variável)
Médico pensa: "Normal, escalista real respondendo"
Risco: Baixo

CENÁRIO 3: Júlia responde em 10+ minutos
Médico pensa: "Que demora! Escalista real seria mais rápido"
Risco: Médico fica frustrado

CENÁRIO 4: Júlia responde em 30 segundos
Médico pensa: "Muito rápido, deve ser bot"
Risco: Médico desconfia

CONCLUSÃO: Variabilidade realista é essencial para indistinguibilidade
```

---

## Parte 5: Fluxo Completo de Escalação com Tempos

### 5.1 Exemplo Prático Completo

```
ESCALAÇÃO COMPLETA: NEGOCIAÇÃO DE PREÇO

TIMESTAMP 14:32:15 - Médico envia mensagem
┌─────────────────────────────────────────┐
│ Médico: "Só por R$ 2.050"               │
│ Base: R$ 1.800                          │
│ Margem Júlia: até R$ 1.980              │
│ Margem Gestor: até R$ 2.160             │
└─────────────────────────────────────────┘

TIMESTAMP 14:32:20 - Júlia detecta escalação
├─ Preço R$ 2.050 > Margem Júlia R$ 1.980? SIM
├─ Preço R$ 2.050 < Margem Gestor R$ 2.160? SIM
└─ AÇÃO: ESCALONAR PARA GESTOR

TIMESTAMP 14:32:25 - Júlia cria ticket
├─ ID: ESC_2025_01_10_001
├─ Tipo: ESCALACAO_PRECO
├─ Urgência: ALTA
├─ Status: AGUARDANDO_GESTOR
└─ Médico: Dr. Carlos Silva (score 95)

TIMESTAMP 14:32:30 - Júlia envia Slack
┌─────────────────────────────────────────┐
│ 🔔 ESCALAÇÃO: NEGOCIAÇÃO DE PREÇO       │
│                                         │
│ Médico: Dr. Carlos Silva                │
│ Histórico: 8 plantões ⭐⭐⭐⭐⭐         │
│ Score BANT: 95/100                      │
│                                         │
│ Vaga: Cardiologia - Hospital São Paulo  │
│ Data: Sexta, 10/01, 12h-00h             │
│                                         │
│ Preço:                                  │
│ Base: R$ 1.800                          │
│ Pretensão: R$ 2.050 (+13.9%)            │
│ Margem Gestor: até R$ 2.160             │
│                                         │
│ ✅ Recomendação: AUTORIZAR              │
│                                         │
│ ⏱️ Tempo: 2-5 minutos                   │
│                                         │
│ [✅ Aprovar] [❌ Negar] [💬 Contraoferecer]
└─────────────────────────────────────────┘

TIMESTAMP 14:33:00 - Gestor recebe notificação
├─ Slack notifica: "Nova escalação"
├─ Gestor abre Slack
└─ Gestor lê contexto

TIMESTAMP 14:33:45 - Gestor toma decisão
├─ Gestor pensa: "Médica de alto valor, dentro de margens"
├─ Gestor clica: [✅ Aprovar R$ 2.050]
└─ Gestor responde no Slack

TIMESTAMP 14:34:00 - Júlia recebe resposta
┌─────────────────────────────────────────┐
│ Gestor: "✅ Aprovado R$ 2.050"          │
│ Justificativa: "Médica de alto valor"   │
└─────────────────────────────────────────┘

TIMESTAMP 14:34:05 - Júlia continua conversa
├─ Júlia aguardou 1 minuto 35 segundos
├─ (Tempo realista para "consultar gestor")
└─ Júlia responde ao médico

TIMESTAMP 14:34:10 - Médico recebe resposta
┌─────────────────────────────────────────┐
│ Júlia: "Consegui oferecer R$ 2.050!     │
│ Topa?"                                  │
│                                         │
│ [Médico não sabe que houve escalação]   │
│ [Parece que Júlia consultou rapidamente]│
└─────────────────────────────────────────┘

TIMESTAMP 14:34:15 - Médico responde
┌─────────────────────────────────────────┐
│ Médico: "Blz, topo!"                    │
└─────────────────────────────────────────┘

TIMESTAMP 14:34:20 - Júlia fecha
┌─────────────────────────────────────────┐
│ Júlia: "Ótimo! Deixa eu confirmar       │
│ com o hospital"                         │
│                                         │
│ [PLANTÃO CONFIRMADO]                    │
└─────────────────────────────────────────┘

RESULTADO:
✅ Escalação bem-sucedida
✅ Médico não desconfiou
✅ Tempo total: 2 minutos (realista)
✅ Tempo de "consulta": 1 minuto 35 segundos (humano)
✅ Plantão confirmado em R$ 2.050
```

---

## Parte 6: Dashboard de Escalações para Gestor

### 6.1 Painel em Tempo Real

```
DASHBOARD GESTOR - ESCALAÇÕES

┌─────────────────────────────────────────────────────────┐
│ ESCALAÇÕES ATIVAS (AGUARDANDO RESPOSTA)                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 1️⃣  CRÍTICA - Problema no Plantão                       │
│    Médico: Dr. João Santos                              │
│    Problema: "Chegou atrasado no hospital"              │
│    Tempo Aguardando: 2 minutos ⏱️                       │
│    Ação: [🔍 Investigar] [💰 Compensar] [💬 Responder] │
│                                                         │
│ 2️⃣  ALTA - Negociação de Preço                          │
│    Médico: Dra. Patricia Oliveira                       │
│    Pretensão: R$ 2.050 (margem até R$ 2.160)           │
│    Tempo Aguardando: 1 minuto ⏱️                        │
│    Ação: [✅ Aprovar] [❌ Negar] [💬 Contraoferecer]    │
│                                                         │
│ 3️⃣  MÉDIA - Pedido Especial                             │
│    Médico: Dra. Ana Costa                               │
│    Pedido: "Vaga no feriado (15/01)"                    │
│    Tempo Aguardando: 5 minutos ⏱️                       │
│    Ação: [✅ Autorizar] [❌ Recusar]                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

ESCALAÇÕES RESOLVIDAS (ÚLTIMAS 24H)

✅ 12 Escalações Resolvidas
├─ Aprovadas: 9 (75%)
├─ Negadas: 2 (17%)
├─ Contraproposta: 1 (8%)
└─ Tempo Médio de Resposta: 3.2 minutos

ESTATÍSTICAS

Escalações por Tipo:
├─ Preço: 8 (67%)
├─ Problema: 2 (17%)
├─ Pedido Especial: 1 (8%)
├─ Médico Alto Valor: 1 (8%)
└─ Anomalia: 0 (0%)

Taxa de Aprovação: 75%
Taxa de Negação: 17%
Taxa de Contraoferta: 8%

Receita Gerada por Escalações: R$ 18.450
Tempo Médio de Resposta: 3.2 minutos
Médicos Retidos por Escalação: 11/12 (92%)
```

---

### 6.2 Configurações de Alerta

```
ALERTAS AUTOMÁTICOS PARA GESTOR

🔴 ALERTA CRÍTICO: Escalação aguardando >3 minutos
   └─ Ação: Notificação sonora + Push notification

🟠 ALERTA ALTO: Escalação aguardando >5 minutos
   └─ Ação: Notificação visual + Slack

🟡 ALERTA MÉDIO: 3+ escalações simultâneas
   └─ Ação: Notificação Slack

🟢 ALERTA BAIXO: Escalação resolvida com sucesso
   └─ Ação: Log registrado

⚠️ ALERTA ESPECIAL: Médico de alto valor escalado
   └─ Ação: Notificação prioritária + Slack

🚨 ALERTA CRÍTICO: Anomalia detectada
   └─ Ação: Notificação imediata + Slack
```

---

## Parte 7: Protocolo de Resposta do Gestor

### 7.1 Guia de Decisão Rápida

```
ÁRVORE DE DECISÃO DO GESTOR

ESCALAÇÃO RECEBIDA
        │
        ▼
┌─────────────────────────────────┐
│ Qual é o tipo?                  │
└─────────────────────────────────┘
    │   │   │   │   │   │
    │   │   │   │   │   └─ OPORTUNIDADE
    │   │   │   │   └─ ANOMALIA
    │   │   │   └─ MÉDICO ALTO VALOR
    │   │   └─ PEDIDO ESPECIAL
    │   └─ PROBLEMA
    └─ PREÇO

┌─────────────────────────────────┐
│ TIPO: PREÇO                     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ Médico é de alto valor?         │
└─────────────────────────────────┘
    │   │
    │   └─ NÃO → Negar ou Contraoferecer
    │
    └─ SIM
        │
        ▼
    ┌─────────────────────────────────┐
    │ Preço está dentro de margens?   │
    └─────────────────────────────────┘
        │   │
        │   └─ NÃO → Negar
        │
        └─ SIM → Aprovar

┌─────────────────────────────────┐
│ TIPO: PROBLEMA                  │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ Qual é o problema?              │
└─────────────────────────────────┘
    │   │   │
    │   │   └─ Outro → Investigar
    │   └─ Qualidade → Compensar
    └─ Logística → Investigar com Hospital

┌─────────────────────────────────┐
│ TIPO: PEDIDO ESPECIAL           │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ Temos vaga disponível?          │
└─────────────────────────────────┘
    │   │
    │   └─ NÃO → Recusar ou Guardar
    │
    └─ SIM
        │
        ▼
    ┌─────────────────────────────────┐
    │ Médico é de alto valor?         │
    └─────────────────────────────────┘
        │   │
        │   └─ NÃO → Recusar
        │
        └─ SIM → Autorizar
```

---

### 7.2 Respostas Padrão do Gestor

```
RESPOSTAS PADRÃO PARA SLACK

APROVAÇÃO DE PREÇO:
"✅ Aprovado R$ [VALOR]. Médica de alto valor, ótimo feedback."

NEGAÇÃO DE PREÇO:
"❌ Negar. Muito acima de margens. Contraoferecer R$ [VALOR]."

CONTRAOFERTA:
"💬 Contraoferecer R$ [VALOR]. Se não aceitar, guardar."

INVESTIGAÇÃO DE PROBLEMA:
"🔍 Vou investigar com o hospital. Volta em 10 min."

COMPENSAÇÃO:
"💰 Oferecer desconto 10% próxima vaga. Manter relacionamento."

AUTORIZAÇÃO DE PEDIDO:
"✅ Autorizado. Temos vaga disponível. Oferecer."

RECUSA DE PEDIDO:
"❌ Recusar. Sem vagas disponíveis. Guardar para futuro."

OPORTUNIDADE:
"🎉 Oferecer bônus R$ 500 por indicação confirmada."

ANOMALIA:
"⚠️ Parar negociação. Possível negociador profissional."
```

---

## Parte 8: Manutenção da Indistinguibilidade Humana

### 8.1 Estratégias para Parecer Humano

```
ESTRATÉGIA 1: VARIAÇÃO DE TEMPO
├─ Nunca responder em tempo exato
├─ Adicionar variação aleatória
├─ Simular "gestor ocupado"
└─ Resultado: Parece humano

ESTRATÉGIA 2: VARIAÇÃO DE ESTILO
├─ Às vezes resposta curta: "✅ Aprovado"
├─ Às vezes resposta longa: "✅ Aprovado. Médica de alto valor..."
├─ Às vezes com emoji: "✅ Aprovado!"
├─ Às vezes sem emoji: "Aprovado"
└─ Resultado: Parece humano

ESTRATÉGIA 3: OCASIONAL DEMORA
├─ 10% das vezes: Atrasar 2-3 minutos
├─ Justificativa: "Estava em reunião"
├─ Resultado: Parece que gestor estava ocupado

ESTRATÉGIA 4: OCASIONAL DÚVIDA
├─ 5% das vezes: Pedir mais informações
├─ Exemplo: "Qual é o feedback anterior desse médico?"
├─ Resultado: Parece que gestor está pensando

ESTRATÉGIA 5: OCASIONAL CONSULTA
├─ 3% das vezes: "Deixa eu consultar o CEO"
├─ Resultado: Parece que há hierarquia real

ESTRATÉGIA 6: OCASIONAL ERRO
├─ 1% das vezes: Digitar errado e corrigir
├─ Exemplo: "Aprovdo... Aprovado"
├─ Resultado: Parece humano

ESTRATÉGIA 7: PERSONALIDADE
├─ Usar emojis ocasionalmente
├─ Fazer piadas ocasionalmente
├─ Ser entusiasmado ocasionalmente
├─ Resultado: Parece que gestor tem personalidade
```

---

### 8.2 O Que NÃO Fazer

```
❌ NUNCA responder em tempo exato (sempre 2 minutos)
❌ NUNCA responder instantaneamente (<30 segundos)
❌ NUNCA responder sempre com mesmo estilo
❌ NUNCA usar sempre mesmos emojis
❌ NUNCA usar sempre mesma quantidade de palavras
❌ NUNCA responder sem variação de tom
❌ NUNCA ser perfeitamente consistente
❌ NUNCA parecer muito rápido
❌ NUNCA parecer muito lento
❌ NUNCA ser muito formal ou muito informal
```

---

## Parte 9: Casos de Uso Avançados

### 9.1 Escalação em Cascata

```
CENÁRIO: Médico quer R$ 3.000 (muito fora de margens)

PASSO 1: Júlia escalona para Gestor
Júlia: "Deixa eu consultar meu gestor"
Gestor recebe: "Médico quer R$ 3.000 (muito acima)"

PASSO 2: Gestor nega
Gestor: "❌ Negar. Fora de autoridade"

PASSO 3: Júlia oferece alternativa
Júlia: "Infelizmente não consigo oferecer R$ 3.000"

PASSO 4: Médico insiste
Médico: "Mas e se eu fizer 2 plantões?"

PASSO 5: Júlia escalona novamente (novo contexto)
Júlia: "Deixa eu ver se temos 2 vagas"
Gestor recebe: "Médico quer 2 plantões por R$ 1.500 cada"

PASSO 6: Gestor aprova
Gestor: "✅ Aprovado. 2 plantões por R$ 1.500 cada"

PASSO 7: Júlia fecha
Júlia: "Ótimo! 2 plantões por R$ 1.500 cada. Topa?"
```

---

### 9.2 Escalação com Múltiplos Gestores

```
CENÁRIO: Decisão muito importante

PASSO 1: Júlia escalona para Gestor
Gestor 1: "Preciso consultar o CEO"

PASSO 2: Gestor escalona para CEO
CEO: "✅ Aprovado com condições"

PASSO 3: Gestor responde para Júlia
Gestor 1: "✅ Aprovado com condições: [...]"

PASSO 4: Júlia continua conversa
Júlia: "Consegui oferecer com algumas condições"
```

---

## Conclusão

Este protocolo garante que:

✅ **Escalações são eficientes** — Gestor recebe tudo que precisa
✅ **Tempos são realistas** — Médico não desconfia
✅ **Decisões são rápidas** — Não perde oportunidades
✅ **Relacionamentos são mantidos** — Mesmo quando nega
✅ **Júlia parece humana** — Variação em tudo
✅ **Supervisão é pragmática** — Gestor tem controle total

**Resultado:** Júlia opera com autonomia, mas com supervisão clara, mantendo a ilusão de ser uma escalista real.

---

**Documento Preparado por:** Squad Multidisciplinar da Revoluna
**Data:** 2025
**Versão:** 1.0 - Protocolo Completo de Escalação Automática
