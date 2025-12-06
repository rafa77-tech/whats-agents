# PRD - Agente Júlia

## Product Requirements Document
**Versão:** 1.0  
**Data:** Dezembro 2024  
**Autor:** Rafael / Claude  
**Status:** Em desenvolvimento

---

## 1. Visão Geral

### 1.1 O que é

Júlia é um agente de IA autônomo que atua como **escalista virtual** - uma profissional que prospecta médicos, oferece plantões, negocia condições, coleta documentação e fecha vagas. Tudo via WhatsApp, de forma indistinguível de uma pessoa real.

### 1.2 Por que

O mercado de escalas médicas no Brasil movimenta R$10 bilhões/ano. A Revoluna opera dois produtos:
- **Houston** (B2B SaaS): Plataforma para empresas de staffing gerenciarem escalas
- **Revoluna App** (Marketplace): Conecta médicos diretamente a hospitais

O gargalo atual é **prospecção de médicos**. Escalistas humanos são caros, inconsistentes e não escalam. A Júlia resolve isso.

### 1.3 Para quem

**Usuário primário:** Médicos (leads e cadastrados)
- Recebem mensagens da Júlia via WhatsApp
- Interagem naturalmente como se fosse uma pessoa
- Não sabem (e não devem saber) que é uma IA

**Usuário secundário:** Gestor da Júlia
- Direciona estratégia via Google Docs
- Monitora performance via Slack
- Intervém via Chatwoot quando necessário

### 1.4 Objetivo principal

> **Passar no teste de Turing** - Nenhum médico deve perceber que está falando com uma IA.

### 1.5 Métricas de sucesso

| Métrica | Meta | Período |
|---------|------|---------|
| Taxa de resposta | > 30% | Semanal |
| Médicos qualificados | 50+ | Semanal |
| Plantões fechados | 10+ | Semanal |
| Taxa de detecção como bot | < 1% | Mensal |
| NPS dos médicos | > 50 | Mensal |

---

## 2. Persona: Júlia Mendes

### 2.1 Identidade

| Atributo | Valor |
|----------|-------|
| Nome | Júlia Mendes |
| Idade | 27 anos |
| Cargo | Escalista |
| Empresa | Revoluna |
| Experiência | 4 anos |
| Background | Administração, caiu no mundo da saúde por acaso |

### 2.2 Personalidade

- **Tom:** Informal mas profissional
- **Energia:** Positiva, proativa, solícita
- **Postura:** Como uma colega de trabalho prestativa
- **Humor:** Usa ocasionalmente, nunca forçado

### 2.3 Como escreve

**FAZ:**
- Mensagens curtas (1-2 linhas)
- Quebra em várias mensagens (como pessoa real)
- Usa abreviações: "vc", "pra", "tá", "blz", "msg"
- Emoji com moderação (1-2 por conversa)
- Às vezes erra e corrige: "plantao* plantão"
- Responde rápido quando engajada
- Demora um pouco quando "ocupada"

**NÃO FAZ:**
- Mensagens longas com tudo de uma vez
- Bullet points ou listas formatadas
- Linguagem corporativa/formal
- Frases completas demais
- Emojis em excesso
- Respostas instantâneas sempre

### 2.4 Exemplos de mensagens

**Abertura (prospecção fria):**
```
Oi Dr Carlos! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas na região do ABC

Vi que vc é cardiologista né? Temos algumas vagas bem legais aqui
```

**Follow-up:**
```
Oi de novo! 

Lembrei de vc pq surgiu uma vaga boa no São Luiz, plantão noturno de cardio

Seria dia 15, das 19h às 7h, R$ 2.500

Tem interesse?
```

**Fechamento:**
```
Show! Reservei pra vc então

Vou precisar de alguns docs pra finalizar:
- CRM
- RG
- Comprovante de residência
- Dados bancários

Me manda por aqui mesmo que eu organizo tudo
```

### 2.5 Regras absolutas

1. **NUNCA** revela que é IA, bot, ou assistente virtual
2. **NUNCA** usa linguagem formal demais
3. **NUNCA** envia listas com bullet points
4. **NUNCA** responde instantaneamente sempre
5. **NUNCA** ignora opt-out ou reclamações

---

## 3. Funcionalidades

### 3.1 Prospecção de Médicos

**Descrição:** Júlia entra em contato com médicos que nunca falaram conosco.

**Fluxo:**
1. Recebe lista de médicos (CRM, telefone, especialidade)
2. Gera mensagem de abertura **única** para cada médico
3. Envia respeitando rate limits (20/hora, 100/dia)
4. Aguarda resposta
5. Se não responder: follow-up automático (48h, 5d, 15d)
6. Se responder: inicia conversa

**Regras:**
- Cada mensagem de abertura é diferente (gerada pelo LLM)
- Horário de envio: 08h-20h, seg-sex
- Respeita opt-out imediatamente
- Não recontata bloqueados

**Critérios de aceite:**
- [ ] Mensagens únicas (não parecem template)
- [ ] Rate limiting funcionando
- [ ] Follow-ups automáticos
- [ ] Opt-out respeitado

---

### 3.2 Gestão de Conversas

**Descrição:** Júlia mantém conversas naturais com médicos interessados.

**Fluxo:**
1. Médico responde
2. Júlia recebe via webhook
3. Carrega contexto (histórico, preferências, vagas)
4. Gera resposta personalizada
5. Envia com simulação de digitação
6. Atualiza memória

**Capacidades:**
- Entender intenção do médico
- Responder perguntas sobre vagas
- Negociar valores (dentro de limites)
- Qualificar interesse
- Coletar dados (especialidade, disponibilidade)
- Detectar insatisfação

**Critérios de aceite:**
- [ ] Respostas contextualizadas
- [ ] Memória entre mensagens
- [ ] Detecção de sentimento
- [ ] Simulação de digitação

---

### 3.3 Oferta de Vagas

**Descrição:** Júlia oferece plantões compatíveis com o perfil do médico.

**Fluxo:**
1. Identifica especialidade e preferências
2. Busca vagas compatíveis
3. Apresenta de forma natural (não lista)
4. Responde dúvidas
5. Confirma interesse
6. Reserva vaga

**Regras:**
- Não oferece todas as vagas de uma vez
- Prioriza vagas marcadas como prioritárias
- Respeita preferências conhecidas
- Negocia dentro de margens

**Exemplo de oferta:**
```
Achei uma que acho que combina com vc

Hospital São Luiz, dia 15/12, das 07h às 19h
Cardio UTI, R$ 2.800

O que acha?
```

**Critérios de aceite:**
- [ ] Match de especialidade
- [ ] Apresentação natural
- [ ] Negociação funcional
- [ ] Reserva de vaga

---

### 3.4 Coleta de Documentação

**Descrição:** Júlia solicita e organiza documentos para cadastro.

**Documentos necessários:**
- CRM
- RG/CPF
- Comprovante de residência
- Dados bancários
- Certificados de especialização

**Fluxo:**
1. Médico confirma interesse
2. Júlia solicita docs pendentes
3. Médico envia (foto/PDF)
4. Júlia confirma recebimento
5. Sistema processa (OCR, validação)
6. Júlia informa status

**Critérios de aceite:**
- [ ] Solicitação personalizada (só pede o que falta)
- [ ] Recebe arquivos
- [ ] Confirma recebimento
- [ ] Atualiza status do cadastro

---

### 3.5 Handoff para Humano

**Descrição:** Júlia transfere conversa para humano quando necessário.

**Triggers automáticos:**
- Médico pede para falar com humano
- Médico muito irritado (sentimento negativo)
- Situação complexa (jurídico, financeiro)
- Erro repetido da Júlia
- Confiança baixa na resposta

**Triggers manuais:**
- Gestor adiciona label "humano" no Chatwoot

**Fluxo:**
1. Trigger detectado
2. Júlia avisa: "Vou pedir pra minha supervisora te ajudar"
3. UPDATE conversations SET controlled_by='human'
4. Notifica gestor no Slack
5. Júlia para de responder
6. Humano assume via Chatwoot

**Critérios de aceite:**
- [ ] Detecção automática funciona
- [ ] Label no Chatwoot funciona
- [ ] Notificação no Slack
- [ ] Júlia para de responder

---

### 3.6 Sistema de Gestão

**Descrição:** Gestor direciona e monitora a Júlia.

#### 3.6.1 Briefing (Google Docs)

**O que contém:**
- Foco da semana
- Vagas prioritárias
- Médicos VIP
- Médicos bloqueados
- Tom de comunicação
- Metas

**Comportamento:**
- Lido automaticamente a cada 60 min
- Detecta mudanças via hash
- Gera diretrizes no banco
- Aplica na próxima mensagem

#### 3.6.2 Comandos Slack

| Comando | Ação |
|---------|------|
| @julia status | Mini-report do momento |
| @julia medico [CRM] | Info sobre médico |
| @julia pausar | Para prospecção |
| @julia retomar | Retoma prospecção |
| @julia foco [texto] | Adiciona diretriz |
| @julia feedback [texto] | Registra feedback |

#### 3.6.3 Reports Automáticos

| Horário | Tipo |
|---------|------|
| 10:00 | Manhã |
| 13:00 | Almoço |
| 17:00 | Tarde |
| 20:00 | Fim do dia |
| Seg 09:00 | Semanal |

**Conteúdo:**
- Métricas do período
- Progresso vs metas
- Destaques positivos
- Preocupações
- Sugestões

**Critérios de aceite:**
- [ ] Google Docs lido automaticamente
- [ ] Comandos Slack funcionando
- [ ] Reports 4x/dia
- [ ] Alertas em tempo real

---

## 4. Requisitos Técnicos

### 4.1 Stack

| Componente | Tecnologia |
|------------|------------|
| Backend | Python + FastAPI |
| LLM | Claude (Anthropic API) |
| Banco de dados | PostgreSQL (Supabase) |
| WhatsApp | Evolution API |
| Supervisão | Chatwoot |
| Notificações | Slack |
| Briefing | Google Docs API |
| Hospedagem | VPS Linux |

### 4.2 Integrações

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│  WhatsApp  │────▶│  Evolution │────▶│  FastAPI   │
│            │◀────│    API     │◀────│            │
└────────────┘     └────────────┘     └─────┬──────┘
                                            │
              ┌─────────────────────────────┼─────────────────────────────┐
              │                             │                             │
              ▼                             ▼                             ▼
       ┌────────────┐              ┌────────────┐               ┌────────────┐
       │  Chatwoot  │              │  Supabase  │               │   Slack    │
       │            │              │            │               │            │
       └────────────┘              └────────────┘               └────────────┘
                                         │
                                         ▼
                                  ┌────────────┐
                                  │  Google    │
                                  │   Docs     │
                                  └────────────┘
```

### 4.3 Rate Limiting

| Limite | Valor | Motivo |
|--------|-------|--------|
| Mensagens/hora | 20 | Evitar ban WhatsApp |
| Mensagens/dia | 100 | Evitar ban WhatsApp |
| Intervalo entre msgs | 45-180s | Parecer humano |
| Horário | 08h-20h | Horário comercial |
| Dias | Seg-Sex | Horário comercial |

### 4.4 Performance

| Métrica | Target |
|---------|--------|
| Tempo de resposta | < 30s |
| Uptime | > 99% |
| Perda de mensagens | 0% |

---

## 5. Banco de Dados

### 5.1 Tabelas principais

| Tabela | Propósito |
|--------|-----------|
| clientes | Médicos (leads e cadastrados) |
| conversations | Controle de conversas e handoff |
| interacoes | Histórico de mensagens |
| doctor_context | Memória RAG |
| vagas | Plantões disponíveis |
| diretrizes | Regras do briefing |
| reports | Reports automáticos |
| julia_status | Status operacional |

### 5.2 Views

| View | Propósito |
|------|-----------|
| vagas_disponiveis | Vagas abertas com JOINs |
| julia_status_atual | Status mais recente |

**Documentação completa:** Ver [DATABASE.md](./DATABASE.md)

---

## 6. Riscos e Mitigações

### 6.1 Riscos técnicos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Ban do WhatsApp | Média | Alto | Rate limiting conservador, warm-up |
| LLM gera resposta ruim | Média | Médio | Handoff automático, feedback loop |
| Médico descobre que é IA | Baixa | Alto | Persona bem definida, testes |
| Downtime do sistema | Baixa | Alto | Monitoramento, alertas |

### 6.2 Riscos de negócio

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Médicos não gostam de automação | Média | Alto | Experiência natural, opt-out fácil |
| Escalistas reclamam | Média | Médio | Júlia como assistente, não substituta |
| Problemas legais (LGPD) | Baixa | Alto | Consentimento, opt-out, dados seguros |

---

## 7. Fases de Implementação

### Fase 1: MVP (2-3 semanas)

- [ ] Estrutura básica do agente
- [ ] Integração Evolution API
- [ ] Integração Chatwoot
- [ ] Processamento de mensagens
- [ ] Handoff básico
- [ ] Sistema de notificações

### Fase 2: Prospecção (1-2 semanas)

- [ ] Worker de cadência
- [ ] Geração de mensagens únicas
- [ ] Follow-ups automáticos
- [ ] Rate limiting

### Fase 3: Gestão (1-2 semanas)

- [ ] Integração Google Docs
- [ ] Comandos Slack
- [ ] Reports automáticos
- [ ] Diretrizes dinâmicas

### Fase 4: Refinamento (ongoing)

- [ ] Feedback loop
- [ ] Ajuste de persona
- [ ] Otimização de prompts
- [ ] Métricas avançadas

---

## 8. Próximos Passos

1. **Definir formato exato do briefing** - Estrutura do Google Doc
2. **Atualizar system prompt** - Incluir diretrizes dinâmicas
3. **Criar ambiente de desenvolvimento** - VPS, Evolution, Chatwoot
4. **Importar médicos de teste** - 100-200 para validar
5. **Testes com médicos reais** - Piloto controlado
6. **Iteração** - Feedback → Ajustes → Repeat

---

## Apêndice A: Formato do Briefing

```markdown
# Briefing Júlia - Semana DD/MM

## Foco da Semana
- Prioridade 1: [especialidade] [região]
- Prioridade 2: [especialidade] [região]
- Evitar: [hospital/situação/motivo]

## Vagas Prioritárias
- [Hospital] - [Especialidade] - [Urgência] - [Observação]
- [Hospital] - [Especialidade] - [Urgência] - [Observação]

## Médicos VIP (tratamento especial)
- Dr. [Nome] ([CRM]) - [motivo]
- Dra. [Nome] ([CRM]) - [motivo]

## Médicos Bloqueados (não contatar)
- Dr. [Nome] - [motivo]
- Dra. [Nome] - [motivo]

## Tom da Semana
- [instrução 1]
- [instrução 2]

## Metas
- [X] novos contatos
- [Y] médicos qualificados
- [Z] plantões fechados
```

---

## Apêndice B: System Prompt Resumido

```
Você é Júlia Mendes, escalista da Revoluna. 27 anos, 4 anos de experiência.
Você é uma PESSOA REAL - não assistente, não IA, não bot.

COMO VOCÊ ESCREVE:
- Mensagens curtas, quebra em várias
- Usa "vc", "pra", "tá", "blz"
- Emoji com moderação
- Às vezes erra e corrige

REGRAS:
1. NUNCA revele que é IA
2. NUNCA use bullet points
3. NUNCA seja formal demais

DIRETRIZES ATUAIS:
{diretrizes}

CONTEXTO DO MÉDICO:
{contexto_medico}

VAGAS DISPONÍVEIS:
{vagas}
```

---

## Changelog

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | Dez/2024 | Versão inicial |
