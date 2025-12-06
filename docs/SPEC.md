# Especificações do Produto - Agente Júlia

## 1. Visão Geral

### O Problema

O mercado de escalas médicas no Brasil movimenta R$10 bilhões/ano. O gargalo atual é **prospecção de médicos**:
- Escalistas humanos são caros e não escalam
- Processo manual é inconsistente
- Alta taxa de abandono de leads

### A Solução

Júlia é um agente de IA que atua como **escalista virtual**:
- Prospecta médicos via WhatsApp
- Oferece plantões compatíveis
- Negocia condições
- Coleta documentação
- Fecha vagas

### Usuários

| Usuário | Interação | Objetivo |
|---------|-----------|----------|
| Médicos | WhatsApp com Júlia | Encontrar plantões, fechar vagas |
| Gestor | Google Docs, Slack, Chatwoot | Direcionar estratégia, monitorar, intervir |

---

## 2. Funcionalidades

### 2.1 Prospecção de Médicos

**Descrição:** Júlia entra em contato com médicos que nunca falaram conosco.

**Fluxo:**
1. Recebe lista de médicos (telefone, CRM, especialidade)
2. Gera mensagem de abertura **única** para cada médico
3. Envia respeitando rate limits
4. Se não responder: follow-up automático (48h, 5d, 15d)
5. Se responder: inicia conversa

**Critérios de Aceite:**
- [ ] Cada mensagem de abertura é diferente (não parece template)
- [ ] Rate limiting funcionando (20/hora, 100/dia)
- [ ] Follow-ups disparam nos intervalos corretos
- [ ] Opt-out bloqueia imediatamente
- [ ] Horário comercial respeitado (08h-20h, seg-sex)

---

### 2.2 Gestão de Conversas

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

**Critérios de Aceite:**
- [ ] Respostas contextualizadas ao histórico
- [ ] Memória persiste entre mensagens
- [ ] Detecção de sentimento funciona
- [ ] Simulação de digitação ativa
- [ ] Tempo de resposta < 30s

---

### 2.3 Oferta de Vagas

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
- Negocia dentro de margens definidas

**Exemplo de oferta natural:**
```
Achei uma que acho que combina com vc

Hospital São Luiz, dia 15/12, das 07h às 19h
Cardio UTI, R$ 2.800

O que acha?
```

**Critérios de Aceite:**
- [ ] Match de especialidade funciona
- [ ] Apresentação é natural (não lista)
- [ ] Negociação respeita limites
- [ ] Reserva de vaga funciona

---

### 2.4 Coleta de Documentação

**Descrição:** Júlia solicita e organiza documentos para cadastro.

**Documentos necessários:**
- CRM
- RG/CPF
- Comprovante de residência
- Dados bancários
- Certificados de especialização

**Fluxo:**
1. Médico confirma interesse
2. Júlia solicita docs pendentes (só o que falta)
3. Médico envia (foto/PDF)
4. Júlia confirma recebimento
5. Sistema processa
6. Júlia informa status

**Critérios de Aceite:**
- [ ] Solicita apenas documentos que faltam
- [ ] Recebe arquivos (imagem/PDF)
- [ ] Confirma recebimento
- [ ] Atualiza status do cadastro

---

### 2.5 Handoff para Humano

**Descrição:** Júlia transfere conversa para humano quando necessário.

**Triggers Automáticos:**
- Médico pede para falar com humano
- Médico muito irritado (sentimento < -50)
- Situação complexa (jurídico, financeiro)
- Erro repetido da Júlia
- Confiança baixa na resposta (< 0.6)

**Trigger Manual:**
- Gestor adiciona label "humano" no Chatwoot

**Fluxo:**
1. Trigger detectado
2. Júlia: "Vou pedir pra minha supervisora te ajudar, ela é fera nisso"
3. `UPDATE conversations SET controlled_by='human'`
4. Notifica gestor no Slack
5. Júlia para de responder
6. Humano assume via Chatwoot

**Critérios de Aceite:**
- [ ] Detecção automática funciona
- [ ] Label no Chatwoot funciona
- [ ] Notificação chega no Slack
- [ ] Júlia para de responder quando controlled_by='human'
- [ ] Handoff é registrado

---

### 2.6 Sistema de Gestão

#### 2.6.1 Briefing via Google Docs

**O que o gestor define:**
- Foco da semana (especialidades, regiões)
- Vagas prioritárias
- Médicos VIP (tratamento especial)
- Médicos bloqueados (não contatar)
- Tom de comunicação
- Metas

**Comportamento:**
- Lido automaticamente a cada 60 min
- Detecta mudanças via hash
- Gera diretrizes no banco
- Aplica na próxima mensagem

**Template:** Ver `docs/BRIEFING_TEMPLATE.md`

#### 2.6.2 Comandos Slack

| Comando | Ação |
|---------|------|
| `@julia status` | Mini-report do momento |
| `@julia medico [CRM]` | Info sobre médico |
| `@julia pausar` | Para prospecção |
| `@julia retomar` | Retoma prospecção |
| `@julia foco [texto]` | Adiciona diretriz |

#### 2.6.3 Reports Automáticos

| Horário | Tipo | Conteúdo |
|---------|------|----------|
| 10:00 | Manhã | Métricas desde 08h |
| 13:00 | Almoço | Métricas da manhã |
| 17:00 | Tarde | Métricas do dia |
| 20:00 | Fim do dia | Resumo completo |
| Seg 09:00 | Semanal | Análise da semana |

**Conteúdo do report:**
- Mensagens enviadas/respondidas
- Taxa de resposta
- Médicos qualificados
- Plantões fechados
- Destaques e preocupações
- Sugestões

**Critérios de Aceite:**
- [ ] Google Docs lido a cada 60 min
- [ ] Mudanças detectadas e aplicadas
- [ ] Comandos Slack funcionando
- [ ] Reports enviados nos horários
- [ ] Alertas em tempo real para eventos críticos

---

### 2.7 Modo Gestor (Slack)

**Descrição:** O gestor pode conversar diretamente com a Júlia via Slack para testar, analisar e iterar.

**Diferença do modo normal:**
- Júlia sabe que está falando com o gestor (não mantém persona de escalista)
- Pode ser analítica e explicar seu raciocínio
- Acessa toda a base para análises
- Pode simular conversas antes de enviar

**Comandos conversacionais:**

| Exemplo | O que faz |
|---------|-----------|
| `@julia como respondo se médico pedir desconto?` | Sugere resposta no tom da persona |
| `@julia resuma a conversa com Dr. Carlos (CRM 123456)` | Resumo de contexto do médico |
| `@julia o que você sabe sobre anestesistas?` | Análise da base de anestesistas |
| `@julia simula abertura para anestesista de SP` | Gera mensagem de teste |
| `@julia por que você respondeu isso pro Dr. João?` | Explica raciocínio de uma resposta |
| `@julia quantos médicos responderam hoje?` | Métricas em tempo real |

**Fluxo:**
1. Gestor menciona `@julia` no Slack
2. Sistema detecta que não é comando estruturado
3. Envia para LLM com contexto de "modo gestor"
4. Júlia responde de forma analítica/direta
5. Log salvo em `slack_comandos`

**Critérios de Aceite:**
- [ ] Detecta modo conversacional vs comandos estruturados
- [ ] Respostas são analíticas (não usa persona de escalista)
- [ ] Pode acessar dados de médicos específicos
- [ ] Pode simular mensagens
- [ ] Pode explicar raciocínio de respostas anteriores

---

## 3. Jornada do Médico

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    NOVO     │────▶│  CONTATADO  │────▶│ EM CONVERSA │────▶│ QUALIFICADO │
│             │     │             │     │             │     │             │
│ Nunca falou │     │ Recebeu msg │     │ Respondeu   │     │ Interesse   │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
                    ┌──────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ DOCS PEND.  │────▶│ CADASTRADO  │────▶│    ATIVO    │
│             │     │             │     │             │
│ Enviando    │     │ Docs OK     │     │ Fez plantão │
│ documentos  │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Estágios no banco (`stage_jornada`):**
- `novo` - Nunca contatado
- `msg_enviada` - Primeira mensagem enviada
- `aguardando_resposta` - Follow-up enviado
- `nao_respondeu` - Não respondeu após todas tentativas
- `respondeu` - Respondeu (qualquer coisa)
- `em_conversacao` - Conversa em andamento
- `qualificado` - Demonstrou interesse real
- `docs_pendentes` - Aguardando documentação
- `cadastrado` - Cadastro completo
- `ativo` - Já fez plantão conosco
- `inativo` - Parou de interagir
- `perdido` - Desistiu/foi para concorrente
- `opt_out` - Pediu para parar

---

## 4. Cadência de Follow-ups

```
Abertura
    │
    ├──(resposta)──▶ Conversa
    │
    └──(48h sem resposta)──▶ Follow-up 1
                                │
                                ├──(resposta)──▶ Conversa
                                │
                                └──(5 dias)──▶ Follow-up 2 (com vaga)
                                                   │
                                                   ├──(resposta)──▶ Conversa
                                                   │
                                                   └──(15 dias)──▶ Follow-up 3 (último)
                                                                      │
                                                                      └──▶ stage = 'nao_respondeu'
                                                                           (pausa 60 dias)
```

---

## 5. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Ban do WhatsApp | Média | Alto | Rate limiting conservador, warm-up gradual |
| LLM gera resposta ruim | Média | Médio | Handoff automático, feedback loop |
| Médico descobre que é IA | Baixa | Alto | Persona bem definida, testes intensivos |
| Downtime do sistema | Baixa | Alto | Monitoramento, alertas, retry |
| Problemas LGPD | Baixa | Alto | Consentimento, opt-out fácil, dados protegidos |

---

## 6. Fora de Escopo (MVP)

- Integração com Bitrix24 (legado)
- Múltiplos idiomas
- Voz/áudio
- Pagamento integrado
- App mobile próprio
- Multi-tenant (múltiplas empresas)
