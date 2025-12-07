# Epic 1: Integrações

## Objetivo do Epic

> **Configurar e validar todas as APIs externas necessárias para o projeto.**

Este epic garante que todas as integrações estejam funcionando ANTES de começar a escrever código de negócio. Isso evita surpresas e bloqueios nas próximas sprints.

---

## Stories

1. [S0.E1.1 - Obter API Key Anthropic](#s0e11---obter-api-key-anthropic)
2. [S0.E1.2 - Testar chamada Claude API](#s0e12---testar-chamada-claude-api)
3. [S0.E1.3 - Conectar WhatsApp Evolution](#s0e13---conectar-whatsapp-evolution)
4. [S0.E1.4 - Testar envio/recebimento Evolution](#s0e14---testar-enviorecebimento-evolution)
5. [S0.E1.5 - Configurar conta Chatwoot](#s0e15---configurar-conta-chatwoot)
6. [S0.E1.6 - Criar inbox e testar Chatwoot](#s0e16---criar-inbox-e-testar-chatwoot)
7. [S0.E1.7 - Criar webhook Slack](#s0e17---criar-webhook-slack)
8. [S0.E1.8 - Testar envio Slack](#s0e18---testar-envio-slack)

---

# S0.E1.1 - Obter API Key Anthropic

## Objetivo

> **Criar conta na Anthropic e obter API key para usar o Claude.**

Precisamos da API key para que a Júlia possa gerar respostas usando o Claude. Sem isso, não temos agente.

**Resultado esperado:** Você terá uma API key no formato `sk-ant-...` pronta para usar.

---

## Contexto

- Anthropic é a empresa que desenvolve o Claude
- Usaremos o modelo `claude-3-5-haiku-20241022` (barato e rápido)
- Custo estimado: ~$25/mês para nosso volume
- A API key é **secreta** - nunca commitar no git

---

## Responsável

**Gestor** (requer cartão de crédito)

---

## Pré-requisitos

- Cartão de crédito internacional
- Email corporativo (recomendado)

---

## Tarefas

### 1. Criar conta na Anthropic

1. Acesse: https://console.anthropic.com
2. Clique em "Sign Up"
3. Use email corporativo se possível
4. Confirme o email

### 2. Adicionar método de pagamento

1. Vá em **Settings** → **Billing**
2. Clique em "Add payment method"
3. Adicione cartão de crédito
4. Defina um limite de gastos (sugestão: $50/mês)

### 3. Gerar API Key

1. Vá em **Settings** → **API Keys**
2. Clique em "Create Key"
3. Nome: `julia-producao`
4. Copie a key imediatamente (só aparece uma vez!)
5. Guarde em local seguro (1Password, Bitwarden, etc)

### 4. Comunicar ao Dev

1. Envie a API key de forma segura para o dev
2. **NÃO** envie por Slack/WhatsApp sem criptografia
3. Use: 1Password compartilhado, ou Slack com mensagem autodestrutiva

---

## Como Testar

O Gestor não precisa testar. O Dev validará na story S0.E1.2.

---

## DoD (Definition of Done)

- [x] Conta criada em console.anthropic.com
- [x] Método de pagamento adicionado
- [x] Limite de gastos configurado ($50)
- [x] API Key gerada (formato: `sk-ant-...`)
- [x] API Key guardada em local seguro
- [x] API Key comunicada ao Dev de forma segura

**Status: COMPLETO** ✅

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| Cartão recusado | Tentar outro cartão, verificar limite internacional |
| Não recebo email | Verificar spam, tentar outro email |
| Perdi a API key | Gerar nova key, a antiga para de funcionar |

---
---

# S0.E1.2 - Testar chamada Claude API

## Objetivo

> **Validar que conseguimos chamar a API do Claude e receber respostas.**

Este teste confirma que a API key está funcionando e que conseguimos nos comunicar com o Claude.

**Resultado esperado:** Você executará um comando curl e receberá uma resposta do Claude.

---

## Contexto

- A API do Claude usa REST com JSON
- Autenticação via header `x-api-key`
- Modelo que usaremos: `claude-3-5-haiku-20241022`
- Documentação: https://docs.anthropic.com/claude/reference/messages_post

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S0.E1.1 completa (API key disponível)
- [x] `curl` instalado (padrão no Mac/Linux)

---

## Tarefas

### 1. Configurar variável de ambiente temporária

Abra o terminal e execute (substitua pela key real):

```bash
export ANTHROPIC_API_KEY="sk-ant-sua-key-aqui"
```

### 2. Testar chamada básica

Execute este curl:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Responda apenas: Oi, estou funcionando!"}
    ]
  }'
```

### 3. Verificar resposta

Você deve receber algo como:

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Oi, estou funcionando!"
    }
  ],
  "model": "claude-3-5-haiku-20241022",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 8
  }
}
```

### 4. Testar com system prompt

Teste com um system prompt simples (simula a Júlia):

```bash
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "max_tokens": 200,
    "system": "Você é a Júlia, uma escalista de 27 anos. Responda de forma informal e curta.",
    "messages": [
      {"role": "user", "content": "Oi, tudo bem?"}
    ]
  }'
```

### 5. Documentar resultado

Salve a resposta em um arquivo para referência:

```bash
# Criar diretório de testes se não existir
mkdir -p /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual

# Salvar resultado
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-haiku-20241022",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Diga: teste OK"}]
  }' > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual/claude-test.json

# Verificar
cat /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual/claude-test.json
```

---

## Como Testar

Execute os curls acima. Se receber resposta JSON com `"type": "message"`, está funcionando.

---

## DoD (Definition of Done)

- [x] Curl básico retorna resposta do Claude
- [x] Curl com system prompt retorna resposta informal
- [x] Arquivo `tests/manual/claude-test.json` criado com resposta
- [x] Nenhum erro de autenticação (`401`) ou rate limit (`429`)
- [x] Tempo de resposta < 5 segundos

**Status: COMPLETO** ✅

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `401 Unauthorized` | API key inválida | Verificar key, gerar nova |
| `400 Bad Request` | JSON malformado | Verificar aspas e vírgulas |
| `429 Rate Limited` | Muitas requisições | Esperar 1 minuto |
| `timeout` | Rede lenta | Verificar internet |

---
---

# S0.E1.3 - Conectar WhatsApp Evolution

## Objetivo

> **Conectar um número de WhatsApp à Evolution API para enviar/receber mensagens.**

Este é o canal principal de comunicação da Júlia com os médicos.

**Resultado esperado:** QR code escaneado, número conectado, status "connected" na API.

---

## Contexto

- Evolution API é um gateway open-source para WhatsApp
- Já está rodando via Docker (porta 8080)
- Cada "instância" é uma conexão de um número
- O número conectado será usado pela Júlia

---

## Responsável

**Gestor** (requer acesso físico ao celular)

---

## Pré-requisitos

- [x] Docker Compose rodando (`docker compose ps` mostra evolution-api UP)
- [x] Celular com WhatsApp instalado
- [x] Número que será usado (preferencialmente número novo/teste)

---

## Tarefas

### 1. Verificar se Evolution está rodando

```bash
docker compose ps
# Deve mostrar evolution-api com status "Up"

curl http://localhost:8080/
# Deve retornar informações da API
```

### 2. Acessar o dashboard Evolution

1. Abra no navegador: http://localhost:8080
2. Você verá o painel de gerenciamento

### 3. Obter a API Key do Evolution

```bash
# Ver logs para encontrar a API key gerada
docker compose logs evolution-api | grep -i "api.*key"
```

Ou verifique no arquivo de configuração do Docker.

### 4. Criar instância para Júlia

```bash
# Substitua YOUR_API_KEY pela key encontrada
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "Revoluna",
    "qrcode": true,
    "integration": "WHATSAPP-BAILEYS"
  }'
```

A resposta incluirá um QR code em base64.

### 5. Obter QR Code

```bash
curl -X GET http://localhost:8080/instance/qrcode/Revoluna \
  -H "apikey: YOUR_API_KEY"
```

Ou acesse pelo dashboard: http://localhost:8080 → Instância "Revoluna" → QR Code

### 6. Escanear QR Code

1. Abra o WhatsApp no celular
2. Vá em **Configurações** → **Aparelhos conectados**
3. Toque em **Conectar aparelho**
4. Escaneie o QR code exibido

### 7. Verificar conexão

```bash
curl -X GET http://localhost:8080/instance/connectionState/Revoluna \
  -H "apikey: YOUR_API_KEY"
```

Resposta esperada:
```json
{
  "instance": "Revoluna",
  "state": "open"
}
```

---

## Como Testar

```bash
# Verificar status
curl http://localhost:8080/instance/connectionState/Revoluna \
  -H "apikey: YOUR_API_KEY"

# Deve retornar state: "open"
```

---

## DoD (Definition of Done)

- [x] Evolution API rodando (docker ps mostra UP)
- [x] Instância "Revoluna" criada
- [x] QR code escaneado com sucesso
- [x] Status da instância é "open" ou "connected"
- [x] API key do Evolution documentada (para o dev)

**Status: COMPLETO** ✅

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| QR code não aparece | Reiniciar container: `docker compose restart evolution-api` |
| WhatsApp não conecta | Verificar se número não está em outro dispositivo |
| Estado "close" | Escanear QR novamente |
| Container não inicia | Verificar logs: `docker compose logs evolution-api` |

---
---

# S0.E1.4 - Testar envio/recebimento Evolution

## Objetivo

> **Validar que conseguimos enviar e receber mensagens via Evolution API.**

Este teste confirma que a integração com WhatsApp está funcionando corretamente.

**Resultado esperado:** Enviar mensagem via curl → receber no WhatsApp. Responder no WhatsApp → ver no webhook.

---

## Contexto

- Evolution API usa REST para enviar mensagens
- Recebimento é via webhook (Evolution chama nossa API)
- Formato do número: `5511999999999` (sem +, sem espaços)

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S0.E1.3 completa (WhatsApp conectado)
- [x] Um número de teste para receber mensagens (pode ser seu número pessoal)

---

## Tarefas

### 1. Configurar variáveis

```bash
export EVOLUTION_API_KEY="sua-api-key"
export EVOLUTION_URL="http://localhost:8080"
export TEST_PHONE="5511999999999"  # Número para receber teste
```

### 2. Testar envio de mensagem

```bash
curl -X POST "$EVOLUTION_URL/message/sendText/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"number\": \"$TEST_PHONE\",
    \"text\": \"Teste da Evolution API - $(date)\"
  }"
```

### 3. Verificar recebimento

1. Olhe o WhatsApp no celular de teste
2. A mensagem deve aparecer
3. Se não aparecer, verificar:
   - Número está correto (formato: 5511999999999)
   - Instância está conectada
   - Não há bloqueio entre os números

### 4. Testar presença "online"

```bash
curl -X POST "$EVOLUTION_URL/chat/sendPresence/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"number\": \"$TEST_PHONE\",
    \"presence\": \"available\"
  }"
```

### 5. Testar "digitando"

```bash
curl -X POST "$EVOLUTION_URL/chat/sendPresence/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"number\": \"$TEST_PHONE\",
    \"presence\": \"composing\"
  }"
```

Olhe no WhatsApp - deve mostrar "digitando...".

### 6. Configurar webhook temporário para teste

Vamos usar um serviço de teste de webhook:

1. Acesse: https://webhook.site
2. Copie a URL única gerada (ex: `https://webhook.site/abc-123`)
3. Configure no Evolution:

```bash
curl -X POST "$EVOLUTION_URL/webhook/set/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/SEU-ID-AQUI",
    "enabled": true,
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }'
```

### 7. Testar recebimento de webhook

1. Envie uma mensagem DO celular PARA o número da Júlia
2. Vá no webhook.site
3. Você deve ver a requisição com o payload da mensagem

### 8. Documentar payload do webhook

Salve um exemplo do payload recebido:

```bash
# Criar arquivo com exemplo (copie do webhook.site)
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual/evolution-webhook-example.json << 'EOF'
{
  "event": "messages.upsert",
  "instance": "Revoluna",
  "data": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "ABC123"
    },
    "message": {
      "conversation": "Mensagem de teste"
    },
    "messageTimestamp": 1701888000
  }
}
EOF
```

---

## Como Testar

1. **Envio:** Curl de envio → mensagem chega no WhatsApp ✓
2. **Presença:** Curl de composing → "digitando" aparece ✓
3. **Recebimento:** Mensagem enviada → webhook.site mostra payload ✓

---

## DoD (Definition of Done)

- [x] Mensagem enviada via curl chega no WhatsApp
- [x] Presença "composing" funciona (mostra "digitando")
- [x] Presença "available" funciona
- [x] Webhook configurado recebe mensagens
- [x] Arquivo `tests/manual/evolution-webhook-example.json` criado
- [x] Tempo de envio < 3 segundos

**Status: COMPLETO** ✅

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| Mensagem não chega | Número errado | Verificar formato (5511...) |
| `404 Not Found` | Instância não existe | Criar instância primeiro |
| `401 Unauthorized` | API key errada | Verificar key |
| Webhook não recebe | URL errada | Verificar URL no webhook.site |

---
---

# S0.E1.5 - Configurar conta Chatwoot

## Objetivo

> **Criar conta de administrador no Chatwoot para supervisão das conversas.**

O Chatwoot é onde o gestor irá visualizar e intervir nas conversas da Júlia.

**Resultado esperado:** Conta admin criada, consegue fazer login no painel.

---

## Contexto

- Chatwoot é uma plataforma de atendimento open-source
- Já está rodando via Docker (porta 3000)
- Usaremos para: ver conversas, fazer handoff, adicionar labels

---

## Responsável

**Gestor**

---

## Pré-requisitos

- [x] Docker Compose rodando (`docker compose ps` mostra Chatwoot UP)
- [x] Acesso à máquina local

---

## Tarefas

### 1. Verificar se Chatwoot está rodando

```bash
docker compose ps
# Deve mostrar serviços do Chatwoot com status "Up"

curl http://localhost:3000
# Deve retornar HTML da página de login
```

### 2. Acessar página de setup

1. Abra no navegador: http://localhost:3000
2. Se for primeiro acesso, verá tela de setup
3. Se já existe conta, verá tela de login

### 3. Criar conta de administrador

Se tela de setup:
1. Preencha os dados:
   - **Nome:** Seu nome
   - **Email:** seu.email@revoluna.com
   - **Senha:** senha segura (mínimo 8 caracteres)
   - **Nome da conta:** Revoluna
2. Clique em "Criar conta"

Se já existe conta (tela de login):
- Use as credenciais existentes ou
- Verifique com quem configurou anteriormente

### 4. Fazer login

1. Acesse http://localhost:3000
2. Entre com email e senha
3. Você deve ver o dashboard do Chatwoot

### 5. Explorar o painel

1. Navegue pelo menu lateral
2. Identifique:
   - **Inbox:** Onde ficam os canais de comunicação
   - **Conversations:** Onde ficam as conversas
   - **Contacts:** Lista de contatos
   - **Settings:** Configurações

---

## Como Testar

1. Acesse http://localhost:3000
2. Faça login com suas credenciais
3. Dashboard carrega sem erros

---

## DoD (Definition of Done)

- [x] Chatwoot acessível em http://localhost:3000
- [x] Conta de administrador criada
- [x] Login funciona
- [x] Dashboard carrega corretamente
- [x] Credenciais documentadas (local seguro)

**Status: COMPLETO** ✅

> **Nota:** Usando integração nativa Evolution-Chatwoot (não via API separada)

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| Página não carrega | Verificar Docker: `docker compose ps` |
| Erro de banco | `docker compose exec rails bundle exec rails db:migrate` |
| Esqueci a senha | Reset via console Rails ou recriar |

---
---

# S0.E1.6 - Criar inbox e testar Chatwoot

## Objetivo

> **Criar inbox para WhatsApp e validar que conseguimos gerenciar conversas.**

O inbox é o canal por onde as conversas da Júlia aparecerão.

**Resultado esperado:** Inbox criado, API key gerada, conseguimos criar conversa via API.

---

## Contexto

- Inbox = canal de comunicação no Chatwoot
- Usaremos tipo "API" (não integração nativa)
- Nós sincronizaremos mensagens manualmente via código

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S0.E1.5 completa (conta Chatwoot criada)
- [x] Acesso ao painel Chatwoot
- [x] Integração Evolution-Chatwoot configurada

---

## Tarefas

### 1. Acessar configurações de inbox

1. Faça login no Chatwoot (http://localhost:3000)
2. Vá em **Settings** (ícone de engrenagem)
3. Clique em **Inboxes**
4. Clique em **Add Inbox**

### 2. Criar inbox tipo API

1. Selecione **API** como tipo de canal
2. Preencha:
   - **Channel Name:** Julia WhatsApp
   - **Webhook URL:** `http://host.docker.internal:8000/webhook/chatwoot` (vamos configurar depois)
3. Clique em **Create API Channel**

### 3. Anotar informações do inbox

Após criar, anote:
- **Inbox ID:** número exibido (ex: 1)
- **API Inbox Identifier:** string exibida

### 4. Gerar API Key

1. Clique no seu avatar (canto inferior esquerdo)
2. Vá em **Profile Settings**
3. Role até **Access Token**
4. Copie o token (ou gere um novo)

### 5. Testar API - Listar conversas

```bash
export CHATWOOT_URL="http://localhost:3000"
export CHATWOOT_API_KEY="seu-token-aqui"
export CHATWOOT_ACCOUNT_ID="1"  # Geralmente é 1

curl "$CHATWOOT_URL/api/v1/accounts/$CHATWOOT_ACCOUNT_ID/conversations" \
  -H "api_access_token: $CHATWOOT_API_KEY"
```

Deve retornar lista de conversas (vazia se for primeira vez).

### 6. Testar API - Criar contato

```bash
curl -X POST "$CHATWOOT_URL/api/v1/accounts/$CHATWOOT_ACCOUNT_ID/contacts" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Teste",
    "phone_number": "+5511999999999",
    "identifier": "5511999999999"
  }'
```

Anote o `id` retornado (ex: `"id": 1`).

### 7. Testar API - Criar conversa

```bash
export INBOX_ID="1"  # ID do inbox criado
export CONTACT_ID="1"  # ID do contato criado

curl -X POST "$CHATWOOT_URL/api/v1/accounts/$CHATWOOT_ACCOUNT_ID/conversations" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"inbox_id\": $INBOX_ID,
    \"contact_id\": $CONTACT_ID,
    \"status\": \"open\"
  }"
```

### 8. Testar API - Enviar mensagem

```bash
export CONVERSATION_ID="1"  # ID da conversa criada

curl -X POST "$CHATWOOT_URL/api/v1/accounts/$CHATWOOT_ACCOUNT_ID/conversations/$CONVERSATION_ID/messages" \
  -H "api_access_token: $CHATWOOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Olá, esta é uma mensagem de teste!",
    "message_type": "incoming"
  }'
```

### 9. Verificar no painel

1. Volte ao Chatwoot no navegador
2. Vá em **Conversations**
3. Você deve ver a conversa criada com a mensagem

### 10. Documentar IDs

Salve as informações:

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual/chatwoot-config.json << EOF
{
  "url": "http://localhost:3000",
  "account_id": 1,
  "inbox_id": $INBOX_ID,
  "api_key": "NÃO_COMMITAR_AQUI"
}
EOF
```

---

## Como Testar

1. Lista de conversas retorna sem erro
2. Contato criado aparece em Contacts
3. Conversa criada aparece em Conversations
4. Mensagem aparece na conversa

---

## DoD (Definition of Done)

- [x] Inbox "Julia WhatsApp" criado
- [x] API key gerada
- [x] API de listar conversas funciona
- [x] API de criar contato funciona
- [x] API de criar conversa funciona
- [x] API de enviar mensagem funciona
- [x] Mensagem aparece no painel visual
- [x] Arquivo `tests/manual/chatwoot-config.json` criado (sem a key!)

**Status: COMPLETO** ✅

> **Nota:** Usando integração nativa Evolution-Chatwoot. Inbox criado automaticamente pela integração.
> Conversas do WhatsApp aparecem automaticamente no Chatwoot sem necessidade de sincronização via API.

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `401 Unauthorized` | Token inválido | Gerar novo token |
| `404 Not Found` | Account/Inbox ID errado | Verificar IDs |
| Inbox não aparece | Não foi criado | Criar pelo painel |

---
---

# S0.E1.7 - Criar webhook Slack

## Objetivo

> **Configurar webhook do Slack para receber notificações e reports da Júlia.**

O Slack será usado para alertar o gestor sobre eventos importantes.

**Resultado esperado:** Webhook URL gerado, canal criado para receber mensagens.

---

## Contexto

- Slack Webhooks permitem enviar mensagens para canais
- Usaremos para: reports diários, alertas de handoff, plantões fechados
- Não requer bot completo, só incoming webhook

---

## Responsável

**Gestor**

---

## Pré-requisitos

- [ ] Workspace Slack da empresa
- [ ] Permissão para criar apps no Slack

---

## Tarefas

### 1. Criar canal para Júlia

1. Abra o Slack
2. Clique em **+** ao lado de "Canais"
3. Crie um novo canal:
   - **Nome:** `julia-gestao`
   - **Descrição:** Notificações e reports da Júlia
   - **Privado/Público:** Privado (recomendado)
4. Adicione as pessoas que devem receber notificações

### 2. Criar Slack App

1. Acesse: https://api.slack.com/apps
2. Clique em **Create New App**
3. Escolha **From scratch**
4. Preencha:
   - **App Name:** Julia Bot
   - **Workspace:** Selecione seu workspace
5. Clique em **Create App**

### 3. Ativar Incoming Webhooks

1. No menu lateral, clique em **Incoming Webhooks**
2. Ative o toggle **Activate Incoming Webhooks**
3. Clique em **Add New Webhook to Workspace**
4. Selecione o canal `#julia-gestao`
5. Clique em **Allow**

### 4. Copiar Webhook URL

1. Você verá a URL gerada:
   ```
   https://hooks.slack.com/services/T.../B.../xxxxx
   ```
2. Copie esta URL
3. Guarde em local seguro (é como uma senha!)

### 5. Comunicar ao Dev

1. Envie a webhook URL de forma segura
2. Não commitar no git!

---

## Como Testar

O Gestor pode testar rapidamente:

```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H "Content-Type: application/json" \
  -d '{"text": "Teste de webhook! Se você vê isso, funcionou."}'
```

Verifique se a mensagem aparece no canal `#julia-gestao`.

---

## DoD (Definition of Done)

- [x] Canal `#julia-gestao` criado
- [x] Slack App "Julia Bot" criado
- [x] Incoming Webhook ativado
- [x] Webhook URL gerado (formato: `https://hooks.slack.com/...`)
- [x] Teste básico funciona (mensagem chega no canal)
- [x] URL comunicada ao Dev de forma segura

**Status: COMPLETO** ✅

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| Não consigo criar app | Pedir permissão ao admin do workspace |
| Webhook não aparece | Verificar se ativou o toggle |
| Mensagem não chega | Verificar URL, verificar canal |

---
---

# S0.E1.8 - Testar envio Slack

## Objetivo

> **Validar que conseguimos enviar mensagens formatadas para o Slack.**

Este teste confirma que a integração está pronta para reports e alertas.

**Resultado esperado:** Mensagens formatadas chegam no canal do Slack.

---

## Contexto

- Slack suporta formatação rica via "blocks"
- Usaremos para reports (tabelas, destaques)
- Usaremos para alertas (cores, menções)

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S0.E1.7 completa (webhook URL disponível)
- [x] Acesso ao Slack workspace

---

## Tarefas

### 1. Configurar variável

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/SEU/WEBHOOK/AQUI"
```

### 2. Testar mensagem simples

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"text": "Teste simples - Julia está configurada!"}'
```

### 3. Testar mensagem com formatação

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "blocks": [
      {
        "type": "header",
        "text": {"type": "plain_text", "text": "📊 Report Júlia - Teste"}
      },
      {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Métricas do dia:*\n• Enviadas: 10\n• Respondidas: 3\n• Taxa: 30%"}
      }
    ]
  }'
```

### 4. Testar alerta de handoff

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🚨 Handoff necessário!",
    "attachments": [
      {
        "color": "#ff0000",
        "fields": [
          {"title": "Médico", "value": "Dr. Carlos (CRM 123456)", "short": true},
          {"title": "Motivo", "value": "Médico irritado", "short": true},
          {"title": "Resumo", "value": "Reclamou do valor oferecido e pediu para falar com supervisor"}
        ]
      }
    ]
  }'
```

### 5. Testar notificação de plantão fechado

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "🎉 Plantão fechado!",
    "attachments": [
      {
        "color": "#00ff00",
        "fields": [
          {"title": "Médico", "value": "Dra. Ana Silva", "short": true},
          {"title": "Hospital", "value": "Hospital Brasil", "short": true},
          {"title": "Data", "value": "Sábado, 14/12 - 07h às 19h", "short": true},
          {"title": "Valor", "value": "R$ 2.400", "short": true}
        ]
      }
    ]
  }'
```

### 6. Documentar exemplos

```bash
mkdir -p /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual

cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/manual/slack-examples.md << 'EOF'
# Exemplos de Mensagens Slack

## Mensagem Simples
```json
{"text": "Mensagem aqui"}
```

## Report com Blocks
```json
{
  "blocks": [
    {"type": "header", "text": {"type": "plain_text", "text": "Título"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "*Bold* e _italic_"}}
  ]
}
```

## Alerta com Cor
```json
{
  "attachments": [{"color": "#ff0000", "text": "Alerta vermelho!"}]
}
```
EOF
```

---

## Como Testar

1. Cada curl acima deve resultar em mensagem no Slack
2. Verificar formatação está correta
3. Cores aparecem (vermelho para alerta, verde para sucesso)

---

## DoD (Definition of Done)

- [x] Mensagem simples funciona
- [x] Mensagem com blocks (header, section) funciona
- [x] Alerta com cor vermelha funciona
- [x] Notificação com cor verde funciona
- [x] Arquivo `tests/manual/slack-examples.md` criado
- [x] Todas as mensagens aparecem no canal `#julia-gestao`

**Status: COMPLETO** ✅

---

# Epic 1 Summary

**Status Geral: COMPLETO** ✅

| Story | Status |
|-------|--------|
| S0.E1.1 - Obter API Key Anthropic | ✅ |
| S0.E1.2 - Testar chamada Claude API | ✅ |
| S0.E1.3 - Conectar WhatsApp Evolution | ✅ |
| S0.E1.4 - Testar envio/recebimento Evolution | ✅ |
| S0.E1.5 - Configurar conta Chatwoot | ✅ |
| S0.E1.6 - Criar inbox e testar Chatwoot | ✅ |
| S0.E1.7 - Criar webhook Slack | ✅ |
| S0.E1.8 - Testar envio Slack | ✅ |

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| `invalid_payload` | JSON malformado | Verificar sintaxe |
| `channel_not_found` | Webhook inválido | Recriar webhook |
| Sem resposta | URL errada | Verificar URL completa |
