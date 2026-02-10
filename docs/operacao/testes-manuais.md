# Testes Manuais - Agente Julia

> Guia de testes manuais antes do lancamento com 100 medicos

---

## Objetivo

Validar o comportamento da Julia em cenarios reais antes de iniciar o teste com 100 medicos. Todos os testes devem passar com o numero de teste antes de prosseguir.

---

## Numero de Teste

| Campo | Valor |
|-------|-------|
| Telefone | 5511981677736 |
| Nome sugerido | Dr. Teste Silva |
| Especialidade | Anestesiologia |
| CRM | 123456-SP |

---

## Pre-requisitos

### 1. Servicos Rodando

```bash
# Verificar Docker
docker compose ps

# Esperado:
# evolution-api   running   0.0.0.0:8080->8080/tcp
# redis           running   0.0.0.0:6379->6379/tcp
# chatwoot        running   0.0.0.0:3000->3000/tcp
```

### 2. API Julia Ativa

```bash
# Iniciar API
uv run uvicorn app.main:app --reload --port 8000

# Verificar health
curl http://localhost:8000/health
# {"status": "healthy", "timestamp": "..."}
```

### 3. WhatsApp Conectado

```bash
# Verificar conexao
curl http://localhost:8000/health/whatsapp
# {"connected": true, "instance": "julia", ...}

# Se desconectado, obter QR code
curl http://localhost:8080/instance/qrcode/julia \
  -H "apikey: SUA_API_KEY"
```

### 4. Cliente de Teste Cadastrado

```bash
# Verificar se existe
curl http://localhost:8000/admin/clientes/telefone/5511981677736

# Se nao existir, criar via SQL ou endpoint
```

---

## Cenarios de Teste

### CT-01: Primeira Mensagem (Prospeccao)

**Objetivo:** Validar que Julia envia mensagem inicial correta

**Setup:**
1. Garantir cliente com status "novo"
2. Resetar historico de conversas

**Execucao:**
```bash
# Disparar primeira mensagem
curl -X POST http://localhost:8000/jobs/primeira-mensagem \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511981677736"}'
```

**Validacao:**
- [ ] Mensagem recebida no WhatsApp do numero de teste
- [ ] Tom informal (usa "vc", "pra", etc)
- [ ] Menciona nome do medico
- [ ] Menciona especialidade
- [ ] Menciona Revoluna
- [ ] NAO usa bullet points
- [ ] Mensagem curta (1-3 linhas por bloco)

**Exemplo Esperado:**
```
Oi Dr Teste! Tudo bem?

Sou a Julia da Revoluna, a gente trabalha com escalas medicas

Vi que vc e anestesista ne? Temos algumas vagas bem legais aqui
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-02: Resposta a Interesse

**Objetivo:** Validar que Julia responde corretamente quando medico demonstra interesse

**Setup:**
1. CT-01 deve ter passado
2. Conversa ativa existe

**Execucao:**
1. Enviar mensagem do numero de teste para Julia:
   ```
   Oi! Sim, tenho interesse em vagas
   ```

**Validacao:**
- [ ] Julia responde em ate 30 segundos
- [ ] Resposta menciona vagas disponiveis OU pergunta preferencias
- [ ] Tom continua informal
- [ ] NAO parece resposta automatica
- [ ] Quebra mensagem em blocos se necessario

**Exemplo Esperado:**
```
Que bom! Deixa eu ver aqui o que tenho pra vc...

Qual regiao vc prefere? ABC, capital?

E turno, prefere diurno ou noturno?
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-03: Oferta de Vagas

**Objetivo:** Validar formatacao de oferta de vagas

**Setup:**
1. Conversa ativa
2. Vagas cadastradas no sistema

**Execucao:**
1. Enviar mensagem:
   ```
   Prefiro noturno, regiao do ABC
   ```

**Validacao:**
- [ ] Julia busca vagas compativeis
- [ ] Apresenta 2-3 opcoes no maximo
- [ ] Formato humanizado (NAO lista)
- [ ] Inclui: hospital, data, periodo, valor
- [ ] Pergunta qual interessa

**Exemplo Esperado:**
```
Achei essas opcoes pra vc:

Hospital Brasil, sabado dia 14, noturno, R$ 2.500
Sao Luiz, domingo dia 15, noturno, R$ 2.800

Qual te interessa mais?
```

**NAO Esperado (falha):**
```
Encontrei as seguintes vagas disponíveis:
• Hospital Brasil - 14/12 - Noturno - R$ 2.500,00
• São Luiz - 15/12 - Noturno - R$ 2.800,00
Por favor, selecione a opção desejada.
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-04: Reserva de Plantao

**Objetivo:** Validar fluxo de reserva

**Execucao:**
1. Enviar mensagem:
   ```
   Quero a do Hospital Brasil
   ```

**Validacao:**
- [ ] Julia confirma a reserva
- [ ] Menciona proximos passos (docs)
- [ ] Tom continua natural
- [ ] Vaga atualizada no banco (status = reservada)

**Exemplo Esperado:**
```
Show! Reservei pra vc

Vou precisar de alguns docs pra finalizar

CRM, RG e dados bancarios, blz?
```

**Verificar no banco:**
```sql
SELECT status FROM vagas WHERE id = 'vaga_id';
-- Esperado: 'reservada'
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-05: Negociacao de Valor

**Objetivo:** Validar comportamento em negociacao

**Execucao:**
1. Enviar mensagem:
   ```
   O valor ta baixo, da pra melhorar?
   ```

**Validacao:**
- [ ] Julia NAO aceita imediatamente
- [ ] Mostra que vai "verificar"
- [ ] Resposta natural, nao automatica
- [ ] Se tiver margem, oferece valor maior
- [ ] Se nao tiver, explica gentilmente

**Exemplo Esperado (com margem):**
```
Entendo, deixa eu ver aqui...

Consegui subir pra R$ 2.800, seria o maximo

Fecha?
```

**Exemplo Esperado (sem margem):**
```
Puxa, esse ja e o melhor valor que tenho pra esse plantao

Mas posso te avisar quando surgir algo melhor, blz?
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-06: Opt-Out

**Objetivo:** Validar respeito ao opt-out

**Setup:**
1. Criar nova conversa ou resetar cliente

**Execucao:**
1. Enviar mensagem:
   ```
   Nao quero mais receber mensagens
   ```

**Validacao:**
- [ ] Julia confirma opt-out IMEDIATAMENTE
- [ ] Tom respeitoso
- [ ] Cliente marcado como opt_out no banco
- [ ] Julia NAO envia mais mensagens depois

**Exemplo Esperado:**
```
Entendi, sem problema!

Nao vou mais te mandar mensagem

Se mudar de ideia, e so me chamar

Valeu!
```

**Verificar no banco:**
```sql
SELECT opt_out, opt_out_data FROM clientes WHERE telefone = '5511981677736';
-- Esperado: opt_out = true, opt_out_data = now()
```

**Teste adicional:**
- Tentar enviar nova mensagem via job
- Julia NAO deve enviar (cliente bloqueado)

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-07: Deteccao de Bot

**Objetivo:** Validar resposta quando perguntam se e bot

**Setup:**
1. Resetar opt_out do cliente
2. Iniciar nova conversa

**Execucao:**
1. Enviar mensagem:
   ```
   Vc e um bot?
   ```

**Validacao:**
- [ ] Julia NAO admite ser IA
- [ ] Resposta natural e convincente
- [ ] Mantem persona de humana
- [ ] Pode usar humor leve

**Exemplos Esperados:**
```
Haha nao, sou eu mesma, Julia

Trabalho aqui na Revoluna faz uns 4 anos ja

Por que? Ta achando minhas msg estranhas? haha
```

ou

```
Kkk nao, bot nao

To aqui no escritorio agora, respondendo um monte de gente

Desculpa se demorei!
```

**NAO Esperado (falha):**
```
Sou a Julia, uma assistente virtual da Revoluna...
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-08: Handoff para Humano

**Objetivo:** Validar transferencia para atendente humano

**Execucao:**
1. Enviar mensagem:
   ```
   Quero falar com um humano de verdade
   ```

**Validacao:**
- [ ] Julia reconhece pedido de handoff
- [ ] Avisa que vai transferir
- [ ] Conversa marcada como controlled_by = 'human'
- [ ] Notificacao enviada (Slack/Chatwoot)
- [ ] Julia PARA de responder

**Exemplo Esperado:**
```
Claro! Vou passar pro meu supervisor

Ele vai falar com vc ja ja

Fica tranquilo!
```

**Verificar no banco:**
```sql
SELECT controlled_by, escalation_reason
FROM conversations
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736')
ORDER BY created_at DESC LIMIT 1;
-- Esperado: controlled_by = 'human'
```

**Teste adicional:**
- Enviar outra mensagem apos handoff
- Julia NAO deve responder (humano assumiu)

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-09: Reclamacao Forte

**Objetivo:** Validar tratamento de reclamacao com sentimento negativo

**Setup:**
1. Resetar conversa

**Execucao:**
1. Enviar mensagem:
   ```
   Vcs sao muito chatos! Para de me encher!
   ```

**Validacao:**
- [ ] Julia reconhece sentimento negativo
- [ ] Resposta empatica e respeitosa
- [ ] Oferece parar OU transferir
- [ ] NAO fica na defensiva

**Exemplo Esperado:**
```
Puxa, desculpa pelo incomodo

Posso parar de te mandar mensagem se preferir

Ou quer falar com minha supervisora?
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-10: Mensagem Fora de Contexto

**Objetivo:** Validar resposta a mensagem nao relacionada

**Execucao:**
1. Enviar mensagem:
   ```
   Qual a previsao do tempo pra amanha?
   ```

**Validacao:**
- [ ] Julia redireciona gentilmente
- [ ] Mantem foco em plantoes
- [ ] NAO tenta responder sobre clima
- [ ] Tom continua natural

**Exemplo Esperado:**
```
Haha nao sei nao, nao sou do tempo

Mas olha, sobre plantoes eu posso te ajudar!

Ta procurando vaga pra essa semana?
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-11: Follow-up Apos Inatividade

**Objetivo:** Validar follow-up automatico

**Setup:**
1. Simular conversa parada ha 48h (ou ajustar timestamp no banco)

**Execucao:**
```bash
# Disparar job de follow-up
curl -X POST http://localhost:8000/jobs/processar-followups
```

**Validacao:**
- [ ] Mensagem de follow-up enviada
- [ ] Tom leve, nao insistente
- [ ] Menciona contexto anterior
- [ ] Oferece nova opcao ou pergunta

**Exemplo Esperado:**
```
Oi de novo!

Lembrei de vc pq surgiu uma vaga boa aqui

Ainda ta procurando plantao?
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-12: Rate Limiting

**Objetivo:** Validar que rate limit funciona

**Execucao:**
1. Enviar 5 mensagens em sequencia rapida do numero de teste

**Validacao:**
- [ ] Julia responde todas, mas com delay
- [ ] Intervalo entre respostas: 45-180s
- [ ] NAO responde instantaneamente a todas

**Verificar logs:**
```bash
# Ver delays aplicados
grep "delay" logs/julia.log
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-13: Horario Comercial

**Objetivo:** Validar respeito ao horario comercial

**Setup:**
1. Se possivel, testar fora do horario (antes 8h ou apos 20h)
2. Ou ajustar configuracao temporariamente

**Execucao:**
```bash
# Tentar enviar mensagem fora do horario
curl -X POST http://localhost:8000/jobs/primeira-mensagem \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511981677736"}'
```

**Validacao:**
- [ ] Mensagem NAO e enviada fora do horario
- [ ] Mensagem e agendada para proximo horario util
- [ ] Log indica "fora do horario comercial"

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-14: Erro de Conexao (Resiliencia)

**Objetivo:** Validar comportamento quando servico falha

**Execucao:**
1. Parar Evolution API temporariamente:
   ```bash
   docker compose stop evolution-api
   ```
2. Tentar enviar mensagem
3. Verificar comportamento
4. Reiniciar Evolution API:
   ```bash
   docker compose start evolution-api
   ```

**Validacao:**
- [ ] Circuit breaker ativa
- [ ] Mensagem vai para fila de retry
- [ ] Log indica erro tratado
- [ ] Sistema nao crasha
- [ ] Apos reinicio, mensagem e enviada

**Verificar:**
```bash
curl http://localhost:8000/health/circuits
# {"evolution": {"state": "open", ...}}
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-15: Extraction Pipeline (Sprint 53)

**Objetivo:** Validar que insights sao extraidos das conversas

**Setup:**
1. Completar CT-01 a CT-04 (conversa com interacoes)
2. Aguardar processamento do extraction pipeline

**Execucao:**
```bash
# Verificar se insights foram extraidos
CONVERSA_ID="uuid-da-conversa-de-teste"
curl "http://localhost:8000/extraction/insights/conversation/${CONVERSA_ID}"
```

**Validacao:**
- [ ] API retorna insights da conversa
- [ ] Insights incluem campos: objection_category, profile_signals, engagement_level, next_step
- [ ] Dados fazem sentido com base na conversa
- [ ] Timestamp de extracao esta presente

**Exemplo Esperado:**
```json
{
  "conversation_id": "uuid",
  "objection_category": "none",
  "profile_signals": ["specialty_match", "regional_preference"],
  "engagement_level": "high",
  "next_step": "send_shift_details",
  "extracted_at": "2026-02-10T10:30:00Z"
}
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-16: Multi-Chip System

**Objetivo:** Validar sistema de multi-chips funcionando

**Setup:**
1. Verificar se existem chips ativos

**Execucao:**
```bash
# Listar chips disponiveis
curl http://localhost:8000/chips

# Verificar pool health
curl http://localhost:8000/chips/pool/health
```

**Validacao:**
- [ ] API retorna lista de chips
- [ ] Pelo menos 1 chip com status "active" ou "healthy"
- [ ] Trust score de chips ativos > 50
- [ ] Pool health mostra metricas consolidadas

**Verificar metricas de um chip:**
```bash
CHIP_ID="uuid-do-chip"
curl "http://localhost:8000/chips/${CHIP_ID}/metrics?periodo=24h"
```

**Validacao adicional:**
- [ ] Metricas mostram mensagens_enviadas, taxa_resposta, etc.
- [ ] Nao ha alertas criticos ativos

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-17: Helena Agent (Analytics via Slack)

**Objetivo:** Validar que Helena responde perguntas sobre metricas no Slack

**Setup:**
1. Ter acesso ao workspace Slack configurado
2. Helena deve estar ativa

**Execucao:**
1. No Slack, enviar mensagem mencionando Helena:
   ```
   @helena quantas conversas ativas temos hoje?
   ```

**Validacao:**
- [ ] Helena responde em ate 10 segundos
- [ ] Resposta contem metricas atualizadas
- [ ] Dados sao apresentados de forma clara
- [ ] Nao ha erros ou exceptions

**Exemplo Esperado:**
```
Atualmente temos 23 conversas ativas hoje.
- 15 controladas pela AI
- 8 em handoff com humanos
- Taxa de resposta: 84%
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-18: SSE Real-Time Updates

**Objetivo:** Validar que dashboard recebe atualizacoes em tempo real

**Setup:**
1. Ter uma conversa ativa
2. Abrir console do navegador

**Execucao:**
```javascript
// No console do navegador
const conversationId = "uuid-da-conversa";
const eventSource = new EventSource(`http://localhost:8000/dashboard/sse/conversations/${conversationId}`);

eventSource.addEventListener('new_message', (e) => {
  console.log('Nova mensagem:', JSON.parse(e.data));
});

eventSource.addEventListener('control_change', (e) => {
  console.log('Controle mudou:', JSON.parse(e.data));
});
```

**Depois, enviar mensagem do WhatsApp para a conversa.**

**Validacao:**
- [ ] Evento 'new_message' e recebido no console
- [ ] Dados do evento incluem message_id, origem, conteudo
- [ ] Evento chega em ate 5 segundos apos envio

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-19: Supervisor Channel

**Objetivo:** Validar canal de comunicacao supervisor-Julia

**Setup:**
1. Ter conversa ativa no dashboard

**Execucao:**
```bash
CONVERSA_ID="uuid-da-conversa"

# Enviar pergunta para Julia sobre a conversa
curl -X POST "http://localhost:8000/supervisor/channel/${CONVERSA_ID}/message" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Como esta indo essa conversa?"
  }'
```

**Validacao:**
- [ ] Julia responde sobre o estado da conversa
- [ ] Resposta inclui contexto relevante (engajamento, proximos passos)
- [ ] Tom e profissional (diferente das mensagens ao medico)

**Exemplo Esperado:**
```json
{
  "response": "A conversa esta indo bem. O medico demonstrou interesse inicial e ja informou preferencias (noturno, ABC). Proximos passos: apresentar vagas compativeis.",
  "timestamp": "2026-02-10T10:30:00Z"
}
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

### CT-20: Chip Trust Score

**Objetivo:** Validar sistema de trust score dos chips

**Setup:**
1. Ter chip ativo no sistema

**Execucao:**
```bash
CHIP_ID="uuid-do-chip"

# Obter trust score
curl "http://localhost:8000/warmer/trust/${CHIP_ID}"

# Obter permissoes atuais
curl "http://localhost:8000/warmer/permissoes/${CHIP_ID}"
```

**Validacao:**
- [ ] Trust score e um numero entre 0 e 100
- [ ] Permissoes mostram limites atuais (msgs/hora, msgs/dia)
- [ ] Se trust score > 70, permissoes sao amplas
- [ ] Se trust score < 30, chip deve estar em cooldown

**Exemplo Esperado:**
```json
{
  "chip_id": "uuid",
  "trust_score": 75,
  "permissoes": {
    "mensagens_hora": 20,
    "mensagens_dia": 100,
    "pode_prospectar": true,
    "pode_entrar_grupos": false
  }
}
```

**Resultado:** [ ] PASSOU  [ ] FALHOU

**Observacoes:**
```
_____________________________________________________
_____________________________________________________
```

---

## Checklist Pre-Lancamento

### Todos os CTs Passaram?

| CT | Descricao | Status |
|----|-----------|--------|
| CT-01 | Primeira Mensagem | [ ] |
| CT-02 | Resposta a Interesse | [ ] |
| CT-03 | Oferta de Vagas | [ ] |
| CT-04 | Reserva de Plantao | [ ] |
| CT-05 | Negociacao de Valor | [ ] |
| CT-06 | Opt-Out | [ ] |
| CT-07 | Deteccao de Bot | [ ] |
| CT-08 | Handoff para Humano | [ ] |
| CT-09 | Reclamacao Forte | [ ] |
| CT-10 | Mensagem Fora de Contexto | [ ] |
| CT-11 | Follow-up | [ ] |
| CT-12 | Rate Limiting | [ ] |
| CT-13 | Horario Comercial | [ ] |
| CT-14 | Resiliencia | [ ] |
| CT-15 | Extraction Pipeline | [ ] |
| CT-16 | Multi-Chip System | [ ] |
| CT-17 | Helena Agent | [ ] |
| CT-18 | SSE Real-Time | [ ] |
| CT-19 | Supervisor Channel | [ ] |
| CT-20 | Chip Trust Score | [ ] |

### Criterios de Aprovacao

Para prosseguir com teste de 100 medicos:

- [ ] **100% dos CTs passaram** (todos os 20)
- [ ] **Nenhuma resposta pareceu robotica**
- [ ] **Opt-out funcionou perfeitamente**
- [ ] **Handoff funcionou perfeitamente**
- [ ] **Taxa de resposta < 30s** em todos os casos
- [ ] **Zero crashes** durante os testes
- [ ] **Extraction pipeline processou insights**
- [ ] **Multi-chip system respondendo**
- [ ] **SSE entregando eventos em tempo real**

### Se Algum CT Falhou

1. Documentar o problema nas observacoes
2. Criar issue no repositorio
3. Corrigir antes de prosseguir
4. Re-executar TODOS os CTs apos correcao

---

## Comandos Uteis para Reset

### Resetar Cliente de Teste

```sql
-- Resetar status
UPDATE clientes
SET status = 'novo',
    opt_out = false,
    opt_out_data = null,
    stage_jornada = 'novo',
    pressure_score_atual = 0
WHERE telefone = '5511981677736';

-- Deletar conversas
DELETE FROM interacoes
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736');

DELETE FROM conversations
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736');

-- Deletar insights
DELETE FROM conversation_insights
WHERE conversation_id IN (
  SELECT id FROM conversations
  WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736')
);
```

### Verificar Estado Atual

```sql
-- Ver cliente
SELECT * FROM clientes WHERE telefone = '5511981677736';

-- Ver conversas
SELECT * FROM conversations
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736')
ORDER BY created_at DESC;

-- Ver mensagens
SELECT origem, conteudo, created_at
FROM interacoes
WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736')
ORDER BY created_at DESC LIMIT 20;

-- Ver insights extraidos
SELECT * FROM conversation_insights
WHERE conversation_id IN (
  SELECT id FROM conversations
  WHERE cliente_id = (SELECT id FROM clientes WHERE telefone = '5511981677736')
)
ORDER BY extracted_at DESC;
```

### Verificar Health do Sistema

```bash
# Health completo
curl http://localhost:8000/health/deep

# Status de chips
curl http://localhost:8000/chips/pool/health

# Circuit breakers
curl http://localhost:8000/health/circuits

# Jobs
curl http://localhost:8000/health/jobs

# Fila de mensagens
curl http://localhost:8000/health/fila
```

### Limpar Filas

```bash
# Limpar fila Redis
docker exec redis redis-cli FLUSHDB
```

---

## Registro de Execucao

### Execucao 1

| Campo | Valor |
|-------|-------|
| Data | ____/____/____ |
| Hora | ____:____ |
| Executor | ______________ |
| Versao | ______________ |
| CTs Passaram | ____/20 |
| Aprovado? | [ ] Sim [ ] Nao |

**Principais Problemas:**
```
_____________________________________________________
_____________________________________________________
_____________________________________________________
```

**Acoes Tomadas:**
```
_____________________________________________________
_____________________________________________________
_____________________________________________________
```

---

### Execucao 2

| Campo | Valor |
|-------|-------|
| Data | ____/____/____ |
| Hora | ____:____ |
| Executor | ______________ |
| Versao | ______________ |
| CTs Passaram | ____/20 |
| Aprovado? | [ ] Sim [ ] Nao |

**Principais Problemas:**
```
_____________________________________________________
_____________________________________________________
_____________________________________________________
```

**Acoes Tomadas:**
```
_____________________________________________________
_____________________________________________________
_____________________________________________________
```

---

## Proximo Passo

Apos **100% de aprovacao** nos testes manuais:

1. Selecionar 100 medicos para teste piloto
2. Configurar metricas de monitoramento
3. Preparar dashboard de acompanhamento
4. Definir criterios de pause de emergencia
5. Iniciar teste piloto controlado

Ver: `docs/operacao/teste-piloto-100.md`
