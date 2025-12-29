# Jull.IA - Resumo para Time de Design

> **Escalista Virtual Autônoma para Staffing Médico**

---

## 🎯 O Que É

**Jull.IA** (Júlia) é uma agente de inteligência artificial autônoma que atua como escalista virtual, prospectando médicos, oferecendo plantões, negociando condições e fechando vagas via WhatsApp. 

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

---

## 💡 O Problema que Resolve

O mercado de escalas médicas no Brasil movimenta **R$ 10 bilhões por ano**. O principal gargalo é a **prospecção de médicos**:

- Escalistas humanos são caros e não escalam
- Processo manual é inconsistente
- Alta taxa de abandono de leads
- Médicos recebem mensagens de staffing o tempo todo (saturação)
- Todos são contatos frios (ninguém conhece a empresa)

**Jull.IA resolve isso** automatizando todo o processo de relacionamento, desde o primeiro contato até o fechamento da vaga.

---

## 🚀 A Solução

Júlia é uma **escalista virtual** que:

✅ **Prospecta médicos** via WhatsApp (contato frio)  
✅ **Oferece plantões** compatíveis com o perfil do médico  
✅ **Negocia valores e datas** de forma natural  
✅ **Gerencia follow-ups** automáticos e inteligentes  
✅ **Fecha vagas** coletando documentação e confirmando reservas  
✅ **Escala para humanos** quando necessário (handoff inteligente)  
✅ **Aprende e se adapta** com cada interação  

---

## 👤 Persona: Júlia Mendes

### Identidade

| Atributo | Valor |
|----------|-------|
| **Nome** | Júlia Mendes |
| **Idade** | 27 anos |
| **Cargo** | Escalista |
| **Empresa** | Revoluna |
| **Experiência** | 4 anos em staffing médico |

### Personalidade e Tom

**Estilo de comunicação:**
- Mensagens **curtas** (1-2 linhas), quebra em várias mensagens
- Tom **informal e natural**: usa "vc", "pra", "tá", "blz", "msg"
- Emojis com **moderação** (1-2 por conversa, máximo)
- Às vezes **erra e corrige**: "plantao* plantão"
- Responde rápido quando engajada, demora quando "ocupada"
- **Nunca** usa bullet points ou listas formatadas
- **Nunca** revela que é IA/bot/assistente virtual

**Exemplo de mensagem:**
```
Oi Dr Carlos! Tudo bem?

Sou a Júlia da Revoluna, a gente trabalha com escalas médicas na região do ABC

Vi que vc é cardiologista né? Temos algumas vagas bem legais aqui
```

---

## ⚡ Principais Features

### 1. **Prospecção Inteligente**
- Envio automático de mensagens de abertura personalizadas
- Cada mensagem é única (não parece template)
- Respeita rate limits do WhatsApp (20/hora, 100/dia)
- Horário comercial (08h-20h, Seg-Sex)
- Delay humanizado entre mensagens (45-180 segundos)

### 2. **Conversação Natural**
- Responde mensagens em tempo real via WhatsApp
- Entende intenção do médico (interesse, objeção, pergunta)
- Busca vagas compatíveis automaticamente
- Negocia valores dentro de limites configurados
- Coleta informações (especialidade, disponibilidade, preferências)

### 3. **Sistema de Memória e Contexto**
- Lembra de conversas anteriores
- Detecta e armazena preferências do médico (turno, região, valor mínimo)
- Usa RAG (Retrieval Augmented Generation) para conhecimento dinâmico
- 529 chunks de conhecimento indexados sobre objeções, perfis e objetivos

### 4. **Gestão de Vagas**
- Busca plantões compatíveis com especialidade e preferências
- Oferece até 3 vagas por vez em formato natural
- Reserva plantões automaticamente quando médico confirma
- Informa detalhes: hospital, data, período, valor

### 5. **Follow-ups Automáticos**
- Sistema inteligente de follow-up em 3 estágios:
  - **Stage 1 (48h)**: Mensagem leve e amigável
  - **Stage 2 (5 dias)**: Oferece nova opção de vaga
  - **Stage 3 (15 dias)**: Última tentativa suave
- Pausa automática após 3 tentativas sem resposta

### 6. **Handoff Inteligente para Humanos**
- Detecta automaticamente quando escalar para humano:
  - Médico pede explicitamente
  - Sentimento muito negativo
  - Questões jurídicas/financeiras
  - Confiança baixa na resposta
- Transição suave: "Vou pedir pra minha supervisora te ajudar"
- Sincronização com Chatwoot para supervisão

### 7. **Detecção de Objeções e Perfis**
- **10 tipos de objeções** detectadas automaticamente:
  - Valor, disponibilidade, distância, confiança, etc.
- **7 perfis de médico** identificados:
  - Negociador, apressado, cauteloso, etc.
- **8 objetivos de conversa** reconhecidos:
  - Buscar vaga, negociar, informar-se, etc.
- Injeção automática de conhecimento relevante no prompt

### 8. **Gestão via Slack (NLP)**
- Gestor interage com Júlia em linguagem natural no Slack
- 14 tools de gestão disponíveis:
  - Enviar mensagens, buscar métricas, bloquear médicos
  - Listar vagas, ver histórico, status do sistema
- Confirmação antes de ações críticas
- Contexto de sessão mantido por 30 minutos

### 9. **Briefing Automático via Google Docs**
- Gestor edita documento Google Docs com diretrizes
- Sincronização automática a cada hora
- Júlia recebe:
  - Foco da semana
  - Vagas prioritárias
  - Médicos VIP e bloqueados
  - Tom a usar
  - Margem de negociação

### 10. **Sistema de Métricas e Monitoramento**
- Taxa de resposta de médicos
- Taxa de conversão (vagas fechadas)
- Taxa de detecção como bot (< 1% meta)
- Tempo de resposta
- Taxa de handoff
- Reports automáticos no Slack (manhã, almoço, tarde, fim do dia)

### 11. **Respeito a Opt-out**
- Detecção automática de pedidos para parar
- Bloqueio imediato e permanente
- Resposta educada: "Entendi, sem problema! Não vou mais te mandar mensagem"

### 12. **Rate Limiting Inteligente**
- Proteção contra ban do WhatsApp
- Limites: 20 msgs/hora, 100 msgs/dia
- Intervalo humanizado entre mensagens
- Horário comercial respeitado
- Pressure score para evitar saturação de médicos

---

## 🛠️ Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| **Backend** | Python 3.13+ / FastAPI |
| **IA/LLM** | Claude 3.5 Haiku (80%) + Claude 4 Sonnet (20%) |
| **Banco de Dados** | Supabase (PostgreSQL + pgvector) |
| **WhatsApp** | Evolution API (multi-device) |
| **Supervisão** | Chatwoot |
| **Notificações** | Slack |
| **Cache/Filas** | Redis |
| **Embeddings** | Voyage AI |

---

## 📊 Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| **Taxa de resposta** | > 30% |
| **Taxa de conversão** | > 10% |
| **Tempo de resposta** | < 30 segundos |
| **Taxa de detecção como bot** | < 1% |
| **Taxa de handoff** | < 5% |
| **NPS dos médicos** | > 8 |

---

## 🎨 Diferenciais para Comunicação Visual

### Conceitos Visuais Fortes

1. **Humanização da IA**
   - Júlia não é um robô, é uma pessoa
   - Tom amigável, profissional mas acessível
   - Representação visual: jovem profissional (27 anos)

2. **Autonomia e Inteligência**
   - Funciona 24/7 sem supervisão constante
   - Aprende e se adapta
   - Toma decisões inteligentes

3. **Eficiência e Escalabilidade**
   - Atende centenas de médicos simultaneamente
   - Reduz custos operacionais drasticamente
   - Não cansa, não erra por fadiga

4. **Naturalidade**
   - Conversas indistinguíveis de humanos
   - Passa no teste de Turing
   - Médicos não percebem que é IA

5. **Confiabilidade**
   - Sistema robusto com circuit breakers
   - Rate limiting para proteção
   - Handoff inteligente quando necessário

---

## 📱 Canais de Comunicação

- **WhatsApp**: Canal principal de interação com médicos
- **Slack**: Gestão e monitoramento pelo time
- **Chatwoot**: Supervisão humana quando necessário
- **Google Docs**: Briefing e diretrizes estratégicas

---

## 🎯 Público-Alvo

### Primário
- **Médicos** (leads e cadastrados)
  - Recebem mensagens da Júlia via WhatsApp
  - Interagem naturalmente como se fosse uma pessoa
  - Não sabem (e não devem saber) que é uma IA

### Secundário
- **Gestores da Revoluna**
  - Direcionam estratégia via Google Docs
  - Monitoram performance via Slack
  - Intervêm via Chatwoot quando necessário

---

## 💼 Contexto de Mercado

- **Mercado**: R$ 10 bilhões/ano em escalas médicas no Brasil
- **Saturação**: Médicos recebem mensagens de staffing constantemente
- **Desafio**: Todos são contatos frios (ninguém conhece a empresa)
- **Diferencial**: Qualidade > quantidade. Uma mensagem mal escrita = bloqueio.

---

## 🚦 Status do Projeto

- **Início**: 05/12/2025
- **Sprint Atual**: 13 - Conhecimento Dinâmico (Completa)
- **Arquivos Python**: 150+
- **Serviços**: 53 módulos
- **Tabelas no banco**: 38
- **Testes**: 567
- **Endpoints API**: 59

---

## 📝 Notas para Design

### Cores e Identidade
- Profissional mas acessível
- Tecnologia sem ser frio/robótico
- Confiança e proximidade
- Jovem (27 anos) mas experiente (4 anos)

### Elementos Visuais
- Evitar representações de robôs ou IA óbvia
- Focar em pessoa profissional, escalista
- WhatsApp como canal principal (verde característico)
- Conexão médico-hospital (cuidado, saúde)

### Mensagens-Chave
- "Escalista virtual autônoma"
- "Conversas naturais, resultados reais"
- "IA que passa no teste de Turing"
- "Autonomia com supervisão inteligente"
- "Eficiência sem perder o toque humano"

---

*Documento gerado para time de design - Dezembro 2025*

