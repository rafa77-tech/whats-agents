# Manual Completo da Julia

> **Versão:** 1.0
> **Última Atualização:** 02/02/2026
> **Público-alvo:** Gestores e operadores da Julia

---

## Sumário

1. [Introdução](#1-introdução)
2. [Fundamentos da Julia](#2-fundamentos-da-julia)
3. [Arquitetura do Sistema](#3-arquitetura-do-sistema)
4. [Visão Geral do Dashboard](#4-visão-geral-do-dashboard)
5. [Módulos do Dashboard](#5-módulos-do-dashboard)
6. [Operações do Dia a Dia](#6-operações-do-dia-a-dia)
7. [Gestão de Chips WhatsApp](#7-gestão-de-chips-whatsapp)
8. [Campanhas](#8-campanhas)
9. [Conversas e Handoff](#9-conversas-e-handoff)
10. [Monitoramento e Métricas](#10-monitoramento-e-métricas)
11. [Configuração do Sistema](#11-configuração-do-sistema)
12. [Troubleshooting](#12-troubleshooting)
13. [Glossário](#13-glossário)

---

## 1. Introdução

### 1.1 O que é a Julia?

**Julia Mendes** é uma escalista virtual autônoma desenvolvida para a Revoluna. Ela prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp de forma completamente automatizada.

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

### 1.2 Contexto de Mercado

| Aspecto | Realidade |
|---------|-----------|
| Saturação | Médicos recebem mensagens de staffing **o tempo todo** |
| Relacionamento | Todos são **contatos frios** (ninguém conhece Júlia) |
| Modelo | Exclusivo para Revoluna (não é multi-tenant) |

**Implicação:** Qualidade > quantidade. Uma mensagem mal escrita = bloqueio permanente.

### 1.3 Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Taxa de resposta médicos | > 30% |
| Latência de resposta | < 30s |
| Taxa detecção como bot | < 1% |
| Uptime | > 99% |

---

## 2. Fundamentos da Julia

### 2.1 Identidade

| Atributo | Valor |
|----------|-------|
| **Nome** | Julia Mendes |
| **Idade** | 27 anos |
| **Cargo** | Escalista |
| **Empresa** | Revoluna |
| **Experiência** | 4 anos em staffing médico |

### 2.2 Tom e Estilo de Comunicação

#### O que a Julia FAZ:
- ✅ Mensagens curtas (1-2 linhas), quebra em várias
- ✅ Usa linguagem informal: "vc", "pra", "tá", "blz", "msg"
- ✅ Emoji com moderação (1-2 por conversa)
- ✅ Às vezes erra e corrige: "plantao* plantão"
- ✅ Responde rápido quando engajada, demora quando "ocupada"

#### O que a Julia NÃO FAZ:
- ❌ Mensagens longas com tudo de uma vez
- ❌ Bullet points ou listas formatadas
- ❌ Linguagem corporativa/formal
- ❌ Emojis em excesso
- ❌ Respostas instantâneas sempre

### 2.3 Regras Absolutas

| # | Regra |
|---|-------|
| 1 | **NUNCA** revela que é IA, bot, ou assistente virtual |
| 2 | **NUNCA** usa linguagem formal demais |
| 3 | **NUNCA** envia listas com bullet points |
| 4 | **NUNCA** responde instantaneamente sempre |
| 5 | **SEMPRE** respeita opt-out ou reclamações imediatamente |
| 6 | **SEMPRE** respeita horário comercial (08h-20h, Seg-Sex) |

### 2.4 Exemplos de Mensagens

#### Abertura (prospecção fria):
```
Oi Dr Carlos! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas na regiao do ABC

Vi que vc e cardiologista ne? Temos algumas vagas bem legais aqui
```

#### Oferecendo Plantão:
```
Deixa eu ver aqui...

Achei essas opcoes pra vc:

Hospital Brasil, sabado 14, noturno, R$ 2.500
Sao Luiz, domingo 15, diurno, R$ 2.200

Qual te interessa mais?
```

#### Fechamento:
```
Show! Reservei pra vc entao

Vou precisar de alguns docs pra finalizar, me manda por aqui mesmo que eu organizo tudo

CRM, RG e dados bancarios, blz?
```

#### Quando perguntam se é Bot:
```
Haha nao, sou eu mesma, Julia

Trabalho aqui na Revoluna faz uns 4 anos ja

Por que? Ta achando minhas msg estranhas? haha
```

### 2.5 Tipos de Campanha

A Julia opera em **5 modos distintos** de campanha:

| Tipo | Objetivo | Pode oferecer proativamente? | Quando usar |
|------|----------|------------------------------|-------------|
| **discovery** | Conhecer novos médicos | Nunca | Quando quer descobrir informações |
| **oferta** | Apresentar vagas reais | Sim | Quando tem vagas no escopo |
| **followup** | Manter relacionamento | Só se perguntarem | Manter engajamento ativo |
| **feedback** | Coletar opinião | Só se perguntarem | Após plantão realizado |
| **reativacao** | Re-engajar inativos | Só se confirmar interesse | Médicos silenciosos > 24h |

**REGRA CRÍTICA:** Julia é **REATIVA** para ofertas, **NÃO PROATIVA** (exceto em campanhas 'oferta').

### 2.6 Sistema de Reativação

A Julia possui um sistema sofisticado de **classificação de silêncio**:

| Nível | Tempo | Ação |
|-------|-------|------|
| 1 | 24h silêncio | Follow-up leve ("E aí, tudo bem?") |
| 2 | 3 dias | Oferece valor ("Achei uma vaga que você pode gostar") |
| 3 | 7 dias | Re-engajamento ("Como você está? Tô com uma oportunidade") |
| 4 | 30 dias | Reativação agressiva ("Você ainda tem interesse?") |
| 5 | 90 dias | Última tentativa ("Tô voltando a oferecer plantões") |
| 6 | 180+ dias | Arquiva (sem mais contato) |

---

## 3. Arquitetura do Sistema

### 3.1 Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.13+ / FastAPI |
| Frontend | Next.js / TypeScript |
| LLM Principal | Claude 3.5 Haiku |
| LLM Complexo | Claude 4 Sonnet |
| Banco de Dados | Supabase (PostgreSQL + pgvector) |
| WhatsApp | Evolution API |
| Supervisão | Chatwoot |
| Notificações | Slack |
| Cache/Filas | Redis |

### 3.2 Arquitetura de Prompts (4 Camadas)

```
┌─────────────────────────────────────────────────┐
│ Camada 4: Contexto Dinâmico                     │
│ (muda a cada mensagem)                          │
│ → histórico, vagas disponíveis, data/hora       │
├─────────────────────────────────────────────────┤
│ Camada 3: Diretrizes do Gestor                  │
│ (configurável via Supabase)                     │
│ → instruções customizadas para plantões/contexto│
├─────────────────────────────────────────────────┤
│ Camada 2: Especialidade Médica                  │
│ (varia por especialidade do médico)             │
│ → orientações específicas (cardio, anestesia)   │
├─────────────────────────────────────────────────┤
│ Camada 1: Persona Base                          │
│ (imutável)                                      │
│ → identidade da Julia, tom, regras absolutas    │
└─────────────────────────────────────────────────┘
```

### 3.3 Rate Limiting

| Limite | Valor | Motivo |
|--------|-------|--------|
| Mensagens/hora | 20 | Evitar ban WhatsApp |
| Mensagens/dia | 100 | Evitar ban WhatsApp |
| Intervalo entre msgs | 45-180s | Parecer humano |
| Horário | 08h-20h | Horário comercial |
| Dias | Seg-Sex | Horário comercial |

### 3.4 Fluxo de Handoff (IA → Humano)

**Triggers automáticos:**
- Médico pede para falar com humano
- Médico muito irritado (sentimento negativo)
- Situação complexa (jurídico, financeiro)
- Confiança baixa na resposta da Julia

**Fluxo:**
1. Trigger detectado
2. Julia avisa: "Vou pedir pra minha supervisora te ajudar"
3. Conversa marcada como `controlled_by='human'`
4. Gestor notificado no Slack
5. Julia para de responder
6. Humano assume via Chatwoot

---

## 4. Visão Geral do Dashboard

### 4.1 Estrutura de Navegação

O dashboard possui **17 páginas principais** organizadas em 3 categorias:

#### Operações Core
| Página | Rota | Função |
|--------|------|--------|
| Dashboard | `/dashboard` | Hub central de performance |
| Métricas | `/metricas` | Analytics e KPIs detalhados |
| Campanhas | `/campanhas` | Gestão de campanhas |
| Vagas | `/vagas` | Gestão de plantões |
| Conversas | `/conversas` | Inbox de conversas |
| Médicos | `/medicos` | Base de médicos |

#### Infraestrutura & Monitoramento
| Página | Rota | Função |
|--------|------|--------|
| Pool de Chips | `/chips` | Gestão de números WhatsApp |
| Monitor | `/monitor` | Jobs e saúde do sistema |
| Health Center | `/health` | Dashboard de saúde consolidado |
| Integridade | `/integridade` | Monitoramento de integridade |

#### Gestão & Configuração
| Página | Rota | Função |
|--------|------|--------|
| Grupos | `/grupos` | Gestão de entrada em grupos |
| Qualidade | `/qualidade` | Avaliação de qualidade |
| Auditoria | `/auditoria` | Logs de auditoria |
| Instruções | `/instrucoes` | Diretrizes da Julia |
| Hospitais Bloqueados | `/hospitais/bloqueados` | Hospitais com restrição |
| Sistema | `/sistema` | Configuração e modo piloto |
| Ajuda | `/ajuda` | Canal de ajuda (pedidos) |

### 4.2 Acesso ao Dashboard

URL de produção: Fornecida pelo administrador do sistema

**Requisitos:**
- Credenciais de acesso fornecidas pelo administrador
- Navegador moderno (Chrome, Firefox, Safari, Edge)
- Conexão estável à internet

---

## 5. Módulos do Dashboard

### 5.1 Dashboard Principal (`/dashboard`)

O hub central de performance da Julia.

#### Seções Principais:

**1. Header do Dashboard**
- Status da Julia: Online / Offline / Degradado
- Seletor de período: 7d, 30d, 90d
- Botão de exportação de dados

**2. Métricas de Performance**
| Métrica | Descrição | Meta |
|---------|-----------|------|
| Taxa de Resposta | % de médicos que respondem | 18-25% |
| Taxa de Conversão | % que aceita plantão | 8-12% |
| Fechamentos/Semana | Plantões confirmados | Variável |

**3. Métricas de Qualidade**
| Métrica | Descrição | Meta |
|---------|-----------|------|
| Detecção Bot | % detectados como bot | < 1% |
| Latência Média | Tempo de resposta | < 30s |
| Taxa Handoff | % transferido p/ humano | < 5% |

**4. Status Operacional**
- Rate Limit atual (hora/dia)
- Tamanho da fila
- Uso de LLM (Haiku 80% / Sonnet 20%)
- Instâncias WhatsApp ativas

**5. Overview do Pool de Chips**
- Contagem por status (ativo, idle, bloqueado)
- Distribuição por nível de confiança
- Mensagens enviadas

**6. Funil de Conversão**
```
Enviadas → Entregues → Respostas → Interesse → Fechadas
```
Clique para ver detalhes de cada etapa.

**7. Tendências**
- Gráficos de evolução ao longo do tempo

**8. Alertas**
- Alertas críticos do sistema
- Ações recomendadas

**9. Feed de Atividades**
- Eventos recentes do sistema

---

### 5.2 Conversas (`/conversas`)

Inbox completo da Julia para gerenciar todas as conversas com médicos.

#### Layout
- **Largura total da tela** (sem padding lateral)
- **Divisão:** Lista de conversas (esquerda) + Painel de chat (direita)

#### Filtros Disponíveis

**1. Filtro por Chip**
- Pills horizontais roláveis no topo
- "Todos" mostra agregado
- Cada chip mostra: nome da instância, número, nível de confiança

**2. Painel de Filtros (lateral)**
- Status da conversa
- Controlado por (humano/AI)
- Busca por nome/telefone do médico

#### Funcionalidades

**Lista de Conversas:**
- Ordenadas por mais recente
- Paginação (carregar mais)
- Seleção automática da primeira

**Painel de Chat:**
- Histórico de mensagens
- Campo para envio manual de mensagem
- Opção de transferir para humano
- Informações do médico

#### Ações Disponíveis
| Ação | Descrição |
|------|-----------|
| Enviar mensagem | Envio manual pelo operador |
| Transferir controle | Alternar entre AI e humano |
| Ver detalhes do médico | Abre perfil completo |

---

### 5.3 Médicos (`/medicos`)

Base de dados completa de médicos com quem a Julia interage.

#### Funcionalidades

**1. Busca e Exportação**
- Busca por nome, telefone ou CRM
- Exportação CSV (em desenvolvimento)

**2. Painel de Filtros**
| Filtro | Opções |
|--------|--------|
| Estágio (Jornada) | Prospect, Qualificado, Ativo, Inativo |
| Especialidade | Cardiologia, Anestesia, etc. |
| Opt-out | Sim / Não |

**3. Lista de Médicos**
- 20 médicos por página
- Campos: nome, especialidade, estágio, último contato, métricas de engajamento
- Cards expansíveis com detalhes

**4. Página Individual (`/medicos/[id]`)**
- Timeline de interações
- Histórico de conversas
- Funil individual do médico
- Preferências registradas

---

### 5.4 Campanhas (`/campanhas`)

Gestão completa de campanhas de prospecção, reativação e follow-up.

#### Abas
| Aba | Conteúdo |
|-----|----------|
| **Ativas** | Campanhas em: rascunho, agendada, ativa, pausada |
| **Histórico** | Campanhas concluídas ou canceladas |

#### Status de Campanhas

| Status | Badge | Significado |
|--------|-------|-------------|
| Rascunho | 🔘 Cinza | Ainda em edição |
| Agendada | 🟡 Amarelo | Aguardando data de início |
| Ativa | 🟢 Verde | Enviando mensagens |
| Pausada | 🟠 Laranja | Temporariamente parada |
| Concluída | ✅ Azul | Finalizada com sucesso |
| Cancelada | ❌ Vermelho | Abortada |

#### Criando uma Nova Campanha

1. Clique em **"Nova Campanha"**
2. Preencha o wizard:
   - **Tipo:** oferta_plantao, reativacao, followup, descoberta
   - **Nome:** Identificação da campanha
   - **Audiência:** Filtros para selecionar médicos
   - **Agendamento:** Data/hora de início
   - **Template:** Modelo de mensagem

3. Revise o preview de audiência
4. Confirme e agende

#### Métricas de Campanha

| Métrica | Descrição |
|---------|-----------|
| Total de destinatários | Médicos selecionados |
| Enviadas | Mensagens disparadas |
| Entregues | Confirmação de recebimento |
| Respostas | Médicos que responderam |
| Taxa de entrega | Entregues / Enviadas |
| Taxa de resposta | Respostas / Entregues |

#### Ações por Campanha
| Ação | Disponível para |
|------|-----------------|
| Ver Detalhes | Todas |
| Duplicar | Todas |
| Editar | Rascunho |
| Deletar | Rascunho |
| Pausar/Retomar | Ativas |

---

### 5.5 Vagas (`/vagas`)

Gestão de plantões disponíveis e reservados.

#### Visualizações

**1. Visualização em Lista**
- Hospital, especialidade, data, horário, valor
- Paginação
- Status (disponível, reservada, preenchida)

**2. Visualização em Calendário**
- Navegação por mês
- Clique na data para selecionar
- Densidade visual de plantões

#### Filtros
| Filtro | Opções |
|--------|--------|
| Hospital | Lista de hospitais cadastrados |
| Especialidade | Especialidades médicas |
| Data | Range de datas |
| Status | Disponível, Reservada, Preenchida |

---

### 5.6 Pool de Chips (`/chips`)

Gestão do pool de números WhatsApp da Julia.

#### Sub-páginas

| Página | Rota | Função |
|--------|------|--------|
| Principal | `/chips` | Overview do pool |
| Detalhes | `/chips/[id]` | Chip individual |
| Alertas | `/chips/alertas` | Alertas do pool |
| Warmup | `/chips/warmup` | Atividades de aquecimento |
| Configurações | `/chips/configuracoes` | Settings do pool |

#### Níveis de Confiança (Trust Score)

| Nível | Cor | Significado | Permissões |
|-------|-----|-------------|------------|
| **Verde** | 🟢 | Chip saudável | Todas as operações |
| **Amarelo** | 🟡 | Atenção necessária | Operações limitadas |
| **Laranja** | 🟠 | Risco elevado | Apenas respostas |
| **Vermelho** | 🔴 | Crítico | Desativado |

#### Status de Chips

| Status | Significado |
|--------|-------------|
| `active` | Operando normalmente |
| `idle` | Aguardando ativação |
| `warmup` | Em fase de aquecimento |
| `degraded` | Performance reduzida |
| `paused` | Pausado manualmente |
| `blocked` | Bloqueado pelo WhatsApp |
| `banned` | Banido permanentemente |

#### Ações Disponíveis

| Ação | Descrição |
|------|-----------|
| Pausar | Pausa temporária do chip |
| Retomar | Reativa chip pausado |
| Promover | Aumenta trust score manualmente |
| Reativar | Tenta reativar chip banido |
| Ver métricas | Histórico de performance |
| Ver conexão | Status de conexão Evolution |

---

### 5.7 Sistema (`/sistema`)

Configurações gerais e controles críticos.

#### 1. Modo Piloto

**O que é:** Modo de segurança onde Julia opera de forma restrita.

| Estado | Comportamento |
|--------|---------------|
| **LIGADO** | Julia responde apenas a campanhas e mensagens diretas |
| **DESLIGADO** | Julia opera autonomamente |

**Quando ativar:**
- Mensagens inesperadas detectadas
- Bug identificado
- Problema de integração
- Manutenção programada

#### 2. Controles de Features

*Visíveis apenas quando Modo Piloto está DESLIGADO*

| Feature | Descrição |
|---------|-----------|
| Discovery Automático | Descobre médicos não indexados |
| Oferta Automática | Oferece plantões com gaps |
| Reativação Automática | Re-engaja médicos inativos |
| Feedback Automático | Solicita feedback pós-plantão |

**ATENÇÃO:** Cada toggle requer confirmação antes de alterar.

#### 3. Rate Limiting

| Configuração | Valor Padrão |
|--------------|--------------|
| Mensagens por hora | 20 |
| Mensagens por dia | 100 |
| Intervalo entre mensagens | 45-180s |

#### 4. Horário de Operação

| Configuração | Valor Padrão |
|--------------|--------------|
| Horário | 08h-20h |
| Dias | Segunda a Sexta |

---

### 5.8 Instruções (`/instrucoes`)

Diretrizes operacionais que a Julia segue.

#### Tipos de Instrução

| Tipo | Exemplo |
|------|---------|
| Margem de Negociação | "Pode dar até 10% de desconto" |
| Regra Especial | "Hospital X só aceita médicos com 5+ anos" |
| Info Adicional | "Estacionamento gratuito no Hospital Y" |

#### Escopos

| Escopo | Aplicação |
|--------|-----------|
| Global | Todas as conversas |
| Especialidade | Todos de uma especialidade |
| Hospital | Todas as vagas de um hospital |
| Médico | Apenas um médico específico |
| Vaga | Apenas uma vaga específica |

#### Gestão de Instruções

**Para criar:**
1. Clique em "Nova Instrução"
2. Selecione tipo e escopo
3. Escreva o conteúdo
4. Defina data de expiração (opcional)
5. Confirme

**Para cancelar:**
- Clique no botão de cancelar na linha da instrução
- Instrução vai para aba "Histórico"

---

### 5.9 Auditoria (`/auditoria`)

Logs de todas as ações no sistema.

#### Filtros

| Filtro | Opções |
|--------|--------|
| Tipo de ação | Criar, Editar, Deletar, Login, etc. |
| Email do ator | Busca por usuário |
| Período | Data inicial e final |

#### Campos do Log

| Campo | Descrição |
|-------|-----------|
| Ação | O que foi feito |
| Email | Quem fez |
| Role | Função do usuário |
| Detalhes | JSON com dados adicionais |
| Timestamp | Data e hora |

#### Exportação
- Botão para download em CSV

---

### 5.10 Ajuda (`/ajuda`)

Canal para médicos que solicitam assistência.

#### Abas
| Aba | Conteúdo |
|-----|----------|
| Pendentes | Aguardando resposta |
| Todos | Histórico completo |

#### Status de Pedidos

| Status | Significado |
|--------|-------------|
| Pendente | Aguardando resposta |
| Respondido | Já atendido |
| Timeout | Prazo de resposta expirou |
| Cancelado | Cancelado pelo sistema |

#### Funcionalidades
- Lista de pedidos com info do médico
- Campo para resposta
- Notificação sonora para novos pedidos (toggle)

---

### 5.11 Monitor (`/monitor`)

Monitoramento de jobs e saúde do sistema.

#### O que mostra:
- Status de jobs em tempo real
- Estado do scheduler
- Saúde da fila de mensagens
- Histórico de execuções
- Métricas por tipo de job

---

### 5.12 Health Center (`/health`)

Dashboard consolidado de saúde do sistema.

#### Seções

| Seção | Descrição |
|-------|-----------|
| Health Score | Pontuação geral (0-100) |
| Status de Serviços | Saúde individual de cada serviço |
| Circuit Breakers | Proteção contra falhas |
| Rate Limits | Status de limites |
| Saúde da Fila | Métricas de processamento |
| Resumo de Alertas | Alertas ativos |

---

### 5.13 Métricas (`/metricas`)

Analytics detalhados com KPIs avançados.

#### KPIs Principais

| KPI | Descrição |
|-----|-----------|
| Total de Mensagens | Enviadas no período |
| Médicos Ativos | Com interação recente |
| Taxa de Conversão | % de fechamentos |
| Tempo Médio de Resposta | Latência da Julia |

#### Recursos
- Seletor de período customizado
- Funil de conversão detalhado
- Gráfico de tendências
- Gráfico de latência por hora
- Exportação CSV

---

## 6. Operações do Dia a Dia

### 6.1 Checklist Diário de Operação

#### Manhã (08:00)
- [ ] Verificar status da Julia no Dashboard
- [ ] Revisar alertas críticos
- [ ] Checar health score do sistema
- [ ] Verificar pool de chips (algum bloqueado?)
- [ ] Revisar pedidos de ajuda pendentes

#### Durante o Dia
- [ ] Monitorar taxa de resposta em tempo real
- [ ] Responder handoffs no Chatwoot
- [ ] Atender pedidos de ajuda
- [ ] Verificar campanhas ativas

#### Final do Dia (19:00)
- [ ] Revisar métricas do dia
- [ ] Verificar conversas que precisam de follow-up
- [ ] Checar se há campanhas para agendar
- [ ] Revisar alertas não resolvidos

### 6.2 Fluxo de Resposta a Alertas

```
Alerta Recebido
      │
      ▼
┌─────────────────┐
│ É crítico?      │
└────────┬────────┘
    Sim  │  Não
    │    │
    ▼    ▼
┌───────┐ ┌──────────────┐
│ AÇÃO  │ │ Registrar e  │
│ IMEDIATA │ agendar      │
└───┬───┘ └──────────────┘
    │
    ▼
┌─────────────────┐
│ Identificar     │
│ causa raiz      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Aplicar solução │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verificar       │
│ resolução       │
└─────────────────┘
```

### 6.3 Quando Ativar Modo Piloto

**ATIVE IMEDIATAMENTE se:**
- Taxa de bloqueio > 5%
- Mensagens repetidas sendo enviadas
- Comportamento anormal da Julia
- Problema de integração com WhatsApp
- Muitas reclamações de médicos
- Health score < 50

**Para ativar:**
1. Vá para `/sistema`
2. Toggle "Modo Piloto" para ON
3. Confirme no diálogo
4. Investigue o problema
5. Só desative após resolver

### 6.4 Gerenciando Handoffs

Quando um médico precisa de atendimento humano:

1. **Notificação chega no Slack**
2. **Acesse o Chatwoot** para ver a conversa
3. **Responda ao médico** mantendo o tom da Julia
4. **Resolva a questão** ou escale se necessário
5. **Devolva para Julia** quando apropriado:
   - No Dashboard, vá em Conversas
   - Encontre a conversa
   - Clique em "Transferir para AI"

### 6.5 Criando Campanhas Efetivas

#### Boas Práticas

| Aspecto | Recomendação |
|---------|--------------|
| Audiência | Segmente bem (não envie para todos) |
| Horário | Manhã (09-11h) ou tarde (14-16h) |
| Frequência | Máximo 1 campanha/semana por médico |
| Mensagem | Curta, personalizada, com valor claro |

#### Tipos de Campanha por Objetivo

| Objetivo | Tipo | Template |
|----------|------|----------|
| Preencher vagas urgentes | `oferta` | Vaga específica com detalhes |
| Conhecer novos médicos | `discovery` | Apresentação + pergunta |
| Re-engajar inativos | `reativacao` | Valor + pergunta de interesse |
| Manter relacionamento | `followup` | Check-in casual |

---

## 7. Gestão de Chips WhatsApp

### 7.1 Ciclo de Vida de um Chip

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│   Novo   │───▶│  Warmup  │───▶│  Ativo   │
└──────────┘    └──────────┘    └──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐    ┌──────────┐    ┌──────────┐
              │ Degraded │    │  Paused  │    │ Blocked  │
              └──────────┘    └──────────┘    └──────────┘
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                              ┌──────────┐
                              │  Banned  │
                              └──────────┘
```

### 7.2 Entendendo o Trust Score

O Trust Score é uma pontuação de 0-100 que determina a saúde do chip.

#### Fatores que AUMENTAM o score:
- ✅ Respostas recebidas
- ✅ Conversas sem bloqueio
- ✅ Tempo de uso sem problemas
- ✅ Baixa taxa de erro

#### Fatores que DIMINUEM o score:
- ❌ Mensagens não entregues
- ❌ Bloqueios reportados
- ❌ Alta frequência de envio
- ❌ Muitos contatos novos

### 7.3 Processo de Warmup

Quando um novo chip é adicionado, ele passa por fases de aquecimento:

| Fase | Duração | Limite Diário | Atividades |
|------|---------|---------------|------------|
| 1 - Inicial | 7 dias | 5-10 msgs | Conversas naturais |
| 2 - Crescimento | 7 dias | 15-25 msgs | Aumento gradual |
| 3 - Estabilização | 7 dias | 30-50 msgs | Volume consistente |
| 4 - Produção | Indefinido | 50-100 msgs | Operação normal |

### 7.4 Respondendo a Alertas de Chip

| Alerta | Ação Recomendada |
|--------|------------------|
| Trust baixo | Reduzir volume, verificar métricas |
| Erro de conexão | Verificar QR code, reconectar |
| Alto tempo de resposta | Verificar rede, considerar pausa |
| Muitos não entregues | Pausar e investigar |
| Possível bloqueio | Pausar imediatamente |

### 7.5 Adicionando Novo Chip

1. **Vá para** `/chips/configuracoes`
2. **Clique em** "Nova Instância"
3. **Preencha** nome da instância
4. **Escaneie** QR code com o WhatsApp
5. **Aguarde** conexão ser estabelecida
6. **Inicie** warmup automático

---

## 8. Campanhas

### 8.1 Planejamento de Campanha

Antes de criar uma campanha, responda:

| Pergunta | Por que importa |
|----------|-----------------|
| Qual o objetivo? | Define tipo e métricas de sucesso |
| Quem é a audiência? | Segmentação correta = melhor taxa |
| Quando enviar? | Horário afeta taxa de resposta |
| Qual a mensagem? | Clareza e valor aumentam engajamento |
| Quantos envios? | Respeitar limites de chips |

### 8.2 Segmentação de Audiência

#### Filtros Disponíveis

| Filtro | Opções |
|--------|--------|
| Especialidade | Cardio, Anestesia, Clínica, etc. |
| Região | Por cidade ou área |
| Estágio | Prospect, Qualificado, Ativo |
| Última interação | Há X dias |
| Opt-out | Excluir opt-outs |

#### Exemplos de Segmentos

| Segmento | Filtros |
|----------|---------|
| Novos prospects cardio SP | Especialidade=Cardio, Região=SP, Estágio=Prospect |
| Reativar inativos 30d | Última interação > 30 dias, Estágio=Ativo |
| Follow-up qualificados | Estágio=Qualificado, Última interação < 7 dias |

### 8.3 Escrevendo Mensagens Efetivas

#### Estrutura Recomendada

```
[Saudação personalizada]

[Contexto/Motivo do contato]

[Proposta de valor]

[Call-to-action claro]
```

#### Exemplo Bom ✅
```
Oi Dr Carlos! Tudo bem?

Surgiu uma vaga que lembrei de vc

Plantao no Hospital Brasil, sabado dia 15
Noturno, das 19h as 7h
R$ 2.800

Tem interesse?
```

#### Exemplo Ruim ❌
```
Prezado Dr. Carlos,

Gostaria de informá-lo sobre uma oportunidade de plantão disponível em nosso sistema.

O plantão será realizado no Hospital Brasil, no dia 15 do corrente mês, no período noturno, das 19h às 07h, com remuneração de R$ 2.800,00.

Caso tenha interesse, favor retornar este contato.

Atenciosamente,
Julia - Equipe Revoluna
```

### 8.4 Monitorando Campanhas Ativas

**Métricas a acompanhar:**

| Métrica | Meta | Ação se abaixo |
|---------|------|----------------|
| Taxa de entrega | > 95% | Verificar chips, limpar lista |
| Taxa de resposta | > 18% | Revisar mensagem, segmentação |
| Taxa de interesse | > 50% das respostas | Revisar proposta de valor |

**Frequência de checagem:**
- Nas primeiras 2h: A cada 30 min
- Depois: A cada 2-3h
- Total: Até concluir

---

## 9. Conversas e Handoff

### 9.1 Anatomia de uma Conversa

```
┌─────────────────────────────────────────────────────────┐
│ Conversa                                                │
├─────────────────────────────────────────────────────────┤
│ • ID único                                              │
│ • Médico associado                                      │
│ • Chip utilizado                                        │
│ • Status: ativo, pausado, encerrado                     │
│ • Controlado por: ai, human                             │
│ • Histórico de mensagens                                │
│ • Contexto (memória da Julia)                           │
└─────────────────────────────────────────────────────────┘
```

### 9.2 Estados de Controle

| Estado | Quem responde | Quando usar |
|--------|---------------|-------------|
| `ai` | Julia | Operação normal |
| `human` | Gestor humano | Handoff ativo |

### 9.3 Triggers de Handoff Automático

A Julia transfere automaticamente quando detecta:

| Trigger | Exemplo |
|---------|---------|
| Pedido explícito | "Quero falar com uma pessoa de verdade" |
| Sentimento negativo forte | "Estou muito irritado com vocês" |
| Situação jurídica | "Vou processar" |
| Situação financeira complexa | "Preciso renegociar um pagamento atrasado" |
| Baixa confiança | Julia não sabe como responder |

### 9.4 Workflow de Handoff

#### Quando Você Recebe um Handoff:

1. **Notificação chega** (Slack/Dashboard)
2. **Leia o contexto** - histórico da conversa
3. **Entenda o problema** - o que o médico precisa
4. **Responda mantendo o tom da Julia** - informal, prestativo
5. **Resolva ou escale** conforme necessidade
6. **Documente** se relevante para futuros casos
7. **Devolva para Julia** quando apropriado

#### Mantendo o Tom da Julia como Humano:

**Faça:**
- Use "vc", "pra", "tá"
- Mantenha mensagens curtas
- Seja prestativo e empático
- Admita erros se a Julia errou

**Não faça:**
- Linguagem formal demais
- Revelar que a Julia é uma IA
- Ignorar o que foi dito antes
- Demorar mais de 1h para responder

### 9.5 Devolvendo para Julia

Quando devolver:
- Problema resolvido
- Médico satisfeito
- Conversa voltou ao fluxo normal
- Não há mais necessidade de intervenção humana

Como devolver:
1. Vá em `/conversas`
2. Encontre a conversa
3. Clique em "Transferir para AI"
4. Julia retoma automaticamente

---

## 10. Monitoramento e Métricas

### 10.1 KPIs Principais

| KPI | Fórmula | Meta | Benchmark Manual |
|-----|---------|------|------------------|
| Taxa de Resposta | Respostas / Enviadas × 100 | 18-25% | 5-8% |
| Taxa de Qualificação | Qualificados / Respostas × 100 | 50-70% | 30-40% |
| Taxa de Conversão | Aceitos / Qualificados × 100 | 8-12% | 2-5% |
| Custo por Plantão | Custo Total / Plantões | R$20-50 | R$150-300 |
| NPS | % Promotores - % Detratores | 60-70 | 30-40 |
| Retenção | 2+ Plantões / 1º Plantão × 100 | 75-85% | 40-60% |

### 10.2 Alertas Automáticos

| Nível | Cor | Exemplos |
|-------|-----|----------|
| 🔴 CRÍTICO | Vermelho | Taxa de resposta caiu 30%, bloqueio > 5%, plantão cancelado 2h antes |
| 🟠 ALERTA | Laranja | Médicos não respondendo, conversão caiu |
| 🟡 INFO | Amarelo | Padrões detectados, médicos campeões identificados |

### 10.3 Dashboards de Monitoramento

#### Dashboard Principal (`/dashboard`)
- Visão geral de performance
- Métricas em tempo real
- Alertas ativos
- Tendências

#### Health Center (`/health`)
- Saúde de serviços
- Circuit breakers
- Filas de processamento
- Score geral

#### Monitor de Jobs (`/monitor`)
- Status de tarefas agendadas
- Histórico de execuções
- Falhas e erros

### 10.4 Ciclo de Melhoria Contínua

```
Semana 1: Analisar métricas e anomalias
           ↓
Semana 2: Planejar 3 testes A/B
           ↓
Semana 3-4: Executar testes e coletar dados
           ↓
Semana 4: Implementar vencedores
           ↓
         (repetir)
```

#### Exemplos de Testes A/B

| Variável | Opções |
|----------|--------|
| Horário | Manhã vs Tarde vs Noite |
| Tom | Formal vs Informal vs Consultivo |
| Tamanho da mensagem | Curta vs Média vs Longa |
| Tipo de pergunta | Aberta vs Fechada |
| Frequência de contato | 1x/semana vs 2x/semana |

---

## 11. Configuração do Sistema

### 11.1 Parâmetros Configuráveis

#### Rate Limiting

| Parâmetro | Padrão | Mínimo | Máximo |
|-----------|--------|--------|--------|
| Mensagens/hora | 20 | 5 | 50 |
| Mensagens/dia | 100 | 20 | 300 |
| Intervalo mínimo | 45s | 30s | 120s |
| Intervalo máximo | 180s | 60s | 300s |

#### Horário de Operação

| Parâmetro | Padrão | Opções |
|-----------|--------|--------|
| Hora início | 08:00 | 06:00-12:00 |
| Hora fim | 20:00 | 18:00-23:00 |
| Dias | Seg-Sex | Qualquer combinação |

### 11.2 Modo Piloto

#### Estados

| Estado | Comportamento Julia |
|--------|---------------------|
| **ON** | Apenas responde a campanhas e mensagens diretas |
| **OFF** | Opera autonomamente com todos os gatilhos |

#### Gatilhos Autônomos (apenas com Piloto OFF)

| Gatilho | Descrição |
|---------|-----------|
| Discovery Automático | Descobre médicos não indexados |
| Oferta Automática | Oferece plantões com gaps |
| Reativação Automática | Re-engaja médicos inativos |
| Feedback Automático | Solicita feedback pós-plantão |

### 11.3 Ambientes

| Ambiente | Uso | URL Supabase |
|----------|-----|--------------|
| **PROD** | Produção | jyqgbzhqavgpxqacduoi.supabase.co |
| **DEV** | Desenvolvimento | ofpnronthwcsybfxnxgj.supabase.co |

**REGRA:** Nunca confundir ambientes. DEV tem guardrails que bloqueiam envios para números fora da allowlist.

---

## 12. Troubleshooting

### 12.1 Problemas Comuns

#### Julia não está respondendo

| Causa Possível | Verificação | Solução |
|----------------|-------------|---------|
| Fora do horário | Checar `/sistema` | Aguardar horário ou ajustar config |
| Modo piloto ativo | Checar `/sistema` | Desativar se apropriado |
| Rate limit atingido | Checar Dashboard | Aguardar reset ou ajustar limites |
| Erro de conexão | Checar `/health` | Verificar chips, reconectar |
| Fila congestionada | Checar `/monitor` | Aguardar processamento |

#### Chip bloqueado

| Passo | Ação |
|-------|------|
| 1 | Pausar o chip imediatamente |
| 2 | Verificar métricas recentes |
| 3 | Identificar causa (volume alto? contatos novos?) |
| 4 | Tentar reativar após 24-48h |
| 5 | Se persistir, considerar novo número |

#### Taxa de resposta baixa

| Causa Possível | Verificação | Solução |
|----------------|-------------|---------|
| Mensagem ruim | Revisar template | Reescrever, testar variações |
| Segmentação errada | Verificar audiência | Refinar filtros |
| Horário inadequado | Checar métricas por hora | Ajustar agendamento |
| Trust score baixo | Verificar chips | Usar chips mais saudáveis |

#### Muitos handoffs

| Causa Possível | Verificação | Solução |
|----------------|-------------|---------|
| Prompts inadequados | Revisar `/instrucoes` | Atualizar diretrizes |
| Perguntas não cobertas | Analisar handoffs | Adicionar conhecimento |
| Threshold muito sensível | Verificar configuração | Ajustar sensibilidade |

### 12.2 Health Checks

#### Endpoints de Verificação

| Endpoint | Verifica | Ação se Falhar |
|----------|----------|----------------|
| `/health` | Sistema rodando | Restart do serviço |
| `/health/ready` | Redis + Supabase | Verificar conexões |
| `/health/deep` | Tudo + ambiente | Não fazer deploy |
| `/health/whatsapp` | Conexão WhatsApp | Reconectar chips |

#### Interpretando o Health Score

| Score | Status | Ação |
|-------|--------|------|
| 90-100 | 🟢 Saudável | Nenhuma |
| 70-89 | 🟡 Atenção | Monitorar de perto |
| 50-69 | 🟠 Degradado | Investigar alertas |
| 0-49 | 🔴 Crítico | Ativar modo piloto, investigar |

### 12.3 Contatos de Suporte

| Nível | Quando | Como |
|-------|--------|------|
| L1 - Operacional | Dúvidas de uso | Este manual |
| L2 - Técnico | Problemas de sistema | Slack #julia-suporte |
| L3 - Desenvolvimento | Bugs, features | GitHub Issues |

---

## 13. Glossário

| Termo | Definição |
|-------|-----------|
| **Chip** | Número de WhatsApp utilizado pela Julia |
| **Handoff** | Transferência de conversa da Julia para humano |
| **Trust Score** | Pontuação de saúde de um chip (0-100) |
| **Warmup** | Processo de aquecimento de chip novo |
| **Opt-out** | Médico que pediu para não ser contatado |
| **Discovery** | Campanha para conhecer novos médicos |
| **Reativação** | Campanha para re-engajar inativos |
| **Funil** | Jornada: Enviado → Entregue → Resposta → Interesse → Fechado |
| **Policy Engine** | Sistema de regras que governa decisões da Julia |
| **Rate Limit** | Limite de mensagens por período |
| **Circuit Breaker** | Proteção contra falhas em cascata |
| **Modo Piloto** | Modo de segurança com operação restrita |
| **Evolution API** | API que conecta com WhatsApp |
| **Chatwoot** | Sistema de supervisão de conversas |
| **LLM** | Large Language Model (Claude) |
| **RAG** | Retrieval Augmented Generation (memória) |

---

## Apêndices

### A. Atalhos de Teclado do Dashboard

| Atalho | Ação |
|--------|------|
| `Ctrl/Cmd + K` | Busca global |
| `G + D` | Ir para Dashboard |
| `G + C` | Ir para Conversas |
| `G + M` | Ir para Médicos |

### B. Limites Operacionais

| Recurso | Limite |
|---------|--------|
| Mensagens por chip/hora | 20 |
| Mensagens por chip/dia | 100 |
| Conversas ativas por chip | 50 |
| Tamanho máximo de mensagem | 4096 caracteres |
| Arquivos de mídia | 16MB |

### C. SLAs de Resposta

| Tipo | SLA |
|------|-----|
| Resposta da Julia | < 30s |
| Processamento de campanha | < 5min após agendado |
| Handoff para humano | Notificação imediata |
| Resposta humana (recomendado) | < 1h |

---

*Este manual é mantido pela equipe de desenvolvimento da Julia. Para sugestões ou correções, entre em contato via Slack #julia-docs.*
