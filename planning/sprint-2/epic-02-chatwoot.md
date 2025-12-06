# Epic 2: Integração Chatwoot

## Objetivo

> **Gestor consegue ver todas as conversas da Júlia em tempo real no Chatwoot.**

---

## Stories

---

# S2.E2.1 - Sincronizar conversas → Chatwoot

## Objetivo

> **Criar conversa no Chatwoot quando nova conversa iniciar no WhatsApp.**

**Resultado esperado:** Toda nova conversa aparece automaticamente no Chatwoot.

## Contexto

- Chatwoot usa conceito de "conversation" associada a "contact" e "inbox"
- Precisamos criar a conversation via API quando médico inicia chat
- Guardar `chatwoot_conversation_id` na nossa tabela `conversations`

## Tarefas

### 1. Criar serviço Chatwoot

```python
# app/services/chatwoot.py

import httpx
from app.core.config import settings

class ChatwootService:
    def __init__(self):
        self.base_url = settings.CHATWOOT_URL
        self.api_token = settings.CHATWOOT_API_TOKEN
        self.account_id = settings.CHATWOOT_ACCOUNT_ID
        self.inbox_id = settings.CHATWOOT_INBOX_ID

    @property
    def headers(self):
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json"
        }

    async def criar_conversa(
        self,
        contact_id: int,
        source_id: str = None
    ) -> dict:
        """
        Cria nova conversa no Chatwoot.

        Args:
            contact_id: ID do contato no Chatwoot
            source_id: ID externo (ex: telefone WhatsApp)

        Returns:
            Dados da conversa criada
        """
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations"

        payload = {
            "inbox_id": self.inbox_id,
            "contact_id": contact_id,
        }

        if source_id:
            payload["source_id"] = source_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


chatwoot_service = ChatwootService()
```

### 2. Integrar na criação de conversa

```python
# app/services/conversa.py (atualizar)

from app.services.chatwoot import chatwoot_service

async def buscar_ou_criar_conversa(cliente_id: str, telefone: str) -> dict:
    """Busca ou cria conversa, sincronizando com Chatwoot."""

    # Buscar conversa ativa existente
    response = (
        supabase.table("conversations")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("status", "ativa")
        .execute()
    )

    if response.data:
        return response.data[0]

    # Criar nova conversa
    conversa = (
        supabase.table("conversations")
        .insert({
            "cliente_id": cliente_id,
            "status": "ativa",
            "controlled_by": "ai"
        })
        .execute()
    ).data[0]

    # Sincronizar com Chatwoot
    try:
        # Buscar contact_id do Chatwoot (já deve existir)
        cliente = await buscar_cliente(cliente_id)
        chatwoot_contact_id = cliente.get("chatwoot_contact_id")

        if chatwoot_contact_id:
            chatwoot_conv = await chatwoot_service.criar_conversa(
                contact_id=chatwoot_contact_id,
                source_id=telefone
            )

            # Salvar ID do Chatwoot
            supabase.table("conversations").update({
                "chatwoot_conversation_id": chatwoot_conv["id"]
            }).eq("id", conversa["id"]).execute()

            conversa["chatwoot_conversation_id"] = chatwoot_conv["id"]

    except Exception as e:
        logger.error(f"Erro ao criar conversa Chatwoot: {e}")
        # Não falha a operação principal

    return conversa
```

## DoD

- [ ] Serviço `ChatwootService` criado
- [ ] Método `criar_conversa()` implementado
- [ ] Conversa criada no Chatwoot quando inicia no WhatsApp
- [ ] `chatwoot_conversation_id` salvo na tabela `conversations`
- [ ] Erro no Chatwoot não quebra fluxo principal

---

# S2.E2.2 - Sincronizar mensagens → Chatwoot

## Objetivo

> **Enviar cada mensagem trocada para o Chatwoot em tempo real.**

**Resultado esperado:** Gestor vê todas as mensagens na interface do Chatwoot.

## Contexto

- Mensagens do médico = incoming
- Mensagens da Júlia = outgoing
- Usar API de messages do Chatwoot

## Tarefas

### 1. Adicionar método de envio de mensagem

```python
# app/services/chatwoot.py (adicionar)

async def enviar_mensagem(
    self,
    conversation_id: int,
    content: str,
    message_type: str = "incoming",
    private: bool = False
) -> dict:
    """
    Envia mensagem para conversa no Chatwoot.

    Args:
        conversation_id: ID da conversa no Chatwoot
        content: Texto da mensagem
        message_type: "incoming" (médico) ou "outgoing" (Júlia)
        private: Se é nota interna (não visível)

    Returns:
        Dados da mensagem criada
    """
    url = (
        f"{self.base_url}/api/v1/accounts/{self.account_id}"
        f"/conversations/{conversation_id}/messages"
    )

    payload = {
        "content": content,
        "message_type": message_type,
        "private": private
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
```

### 2. Sincronizar mensagem recebida

```python
# app/routes/webhook.py (atualizar)

async def processar_mensagem(mensagem: MensagemRecebida):
    # ... código existente ...

    # Após salvar interação, enviar para Chatwoot
    if conversa.get("chatwoot_conversation_id"):
        try:
            await chatwoot_service.enviar_mensagem(
                conversation_id=conversa["chatwoot_conversation_id"],
                content=mensagem.texto,
                message_type="incoming"
            )
        except Exception as e:
            logger.error(f"Erro ao enviar msg para Chatwoot: {e}")
```

### 3. Sincronizar resposta da Júlia

```python
# app/services/agente.py (atualizar)

async def processar_e_responder(
    conversa: dict,
    mensagem: str,
    contexto: dict
) -> str:
    # ... gerar resposta ...

    # Enviar para WhatsApp
    await whatsapp_service.enviar_mensagem(
        telefone=contexto["medico"]["telefone"],
        texto=resposta
    )

    # Sincronizar com Chatwoot
    if conversa.get("chatwoot_conversation_id"):
        try:
            await chatwoot_service.enviar_mensagem(
                conversation_id=conversa["chatwoot_conversation_id"],
                content=resposta,
                message_type="outgoing"
            )
        except Exception as e:
            logger.error(f"Erro ao sincronizar resposta Chatwoot: {e}")

    return resposta
```

## DoD

- [ ] Método `enviar_mensagem()` implementado
- [ ] Mensagens do médico aparecem como "incoming"
- [ ] Mensagens da Júlia aparecem como "outgoing"
- [ ] Sincronização acontece em tempo real
- [ ] Erros não quebram fluxo principal

---

# S2.E2.3 - Criar contatos no Chatwoot

## Objetivo

> **Criar contato no Chatwoot quando médico é cadastrado.**

**Resultado esperado:** Médico aparece como contato no Chatwoot com dados básicos.

## Tarefas

### 1. Adicionar método de criação de contato

```python
# app/services/chatwoot.py (adicionar)

async def criar_contato(
    self,
    nome: str,
    telefone: str,
    email: str = None,
    custom_attributes: dict = None
) -> dict:
    """
    Cria contato no Chatwoot.

    Args:
        nome: Nome do contato
        telefone: Telefone com código do país
        email: Email opcional
        custom_attributes: Dados extras (especialidade, CRM, etc)

    Returns:
        Dados do contato criado
    """
    url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts"

    payload = {
        "inbox_id": self.inbox_id,
        "name": nome,
        "phone_number": telefone,
    }

    if email:
        payload["email"] = email

    if custom_attributes:
        payload["custom_attributes"] = custom_attributes

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["payload"]["contact"]
```

### 2. Integrar na criação de médico

```python
# app/services/medico.py (atualizar)

async def buscar_ou_criar_medico(telefone: str, nome: str = None) -> dict:
    """Busca ou cria médico, sincronizando com Chatwoot."""

    # Buscar existente
    response = (
        supabase.table("clientes")
        .select("*")
        .eq("telefone", telefone)
        .execute()
    )

    if response.data:
        return response.data[0]

    # Criar novo médico
    medico = (
        supabase.table("clientes")
        .insert({
            "telefone": telefone,
            "primeiro_nome": nome or "Médico",
            "status": "novo"
        })
        .execute()
    ).data[0]

    # Criar contato no Chatwoot
    try:
        chatwoot_contact = await chatwoot_service.criar_contato(
            nome=medico["primeiro_nome"],
            telefone=telefone,
            custom_attributes={
                "cliente_id": medico["id"],
                "status": "novo"
            }
        )

        # Salvar ID do Chatwoot
        supabase.table("clientes").update({
            "chatwoot_contact_id": chatwoot_contact["id"]
        }).eq("id", medico["id"]).execute()

        medico["chatwoot_contact_id"] = chatwoot_contact["id"]

    except Exception as e:
        logger.error(f"Erro ao criar contato Chatwoot: {e}")

    return medico
```

### 3. Atualizar contato quando dados mudam

```python
async def atualizar_contato_chatwoot(
    self,
    contact_id: int,
    nome: str = None,
    custom_attributes: dict = None
) -> dict:
    """Atualiza dados do contato no Chatwoot."""
    url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/{contact_id}"

    payload = {}
    if nome:
        payload["name"] = nome
    if custom_attributes:
        payload["custom_attributes"] = custom_attributes

    async with httpx.AsyncClient() as client:
        response = await client.patch(
            url,
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
```

## DoD

- [ ] Método `criar_contato()` implementado
- [ ] Médico criado no Chatwoot automaticamente
- [ ] `chatwoot_contact_id` salvo na tabela `clientes`
- [ ] Custom attributes incluem dados úteis (CRM, especialidade)
- [ ] Método de atualização implementado

---

# S2.E2.4 - Webhook labels do Chatwoot

## Objetivo

> **Receber notificação quando gestor adiciona label no Chatwoot.**

**Resultado esperado:** Sistema detecta label "humano" e ativa handoff.

## Contexto

- Chatwoot envia webhooks para eventos
- Precisamos ouvir `conversation_updated` com labels
- Label "humano" = trigger de handoff

## Tarefas

### 1. Criar endpoint de webhook

```python
# app/routes/chatwoot.py

from fastapi import APIRouter, Request, HTTPException
from app.services.handoff import iniciar_handoff

router = APIRouter(prefix="/chatwoot", tags=["chatwoot"])

@router.post("/webhook")
async def chatwoot_webhook(request: Request):
    """
    Recebe webhooks do Chatwoot.

    Eventos importantes:
    - conversation_updated: Labels alteradas
    - message_created: Nova mensagem (do gestor)
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event = payload.get("event")

    if event == "conversation_updated":
        await processar_conversation_updated(payload)
    elif event == "message_created":
        await processar_message_created(payload)

    return {"status": "ok"}


async def processar_conversation_updated(payload: dict):
    """Processa atualização de conversa (labels)."""
    conversation = payload.get("conversation", {})
    labels = conversation.get("labels", [])
    conversation_id = conversation.get("id")

    # Verificar se label "humano" foi adicionada
    if "humano" in labels:
        # Buscar nossa conversa pelo chatwoot_conversation_id
        response = (
            supabase.table("conversations")
            .select("*")
            .eq("chatwoot_conversation_id", conversation_id)
            .execute()
        )

        if response.data:
            conversa = response.data[0]
            if conversa["controlled_by"] != "human":
                await iniciar_handoff(
                    conversa_id=conversa["id"],
                    motivo="Label humano adicionada no Chatwoot",
                    trigger_type="manual"
                )
```

### 2. Processar mensagem do gestor

```python
async def processar_message_created(payload: dict):
    """
    Processa mensagem criada no Chatwoot.

    Se for do gestor (não da Júlia), encaminhar para WhatsApp.
    """
    message = payload.get("message", {})
    conversation = payload.get("conversation", {})

    # Ignorar mensagens privadas (notas internas)
    if message.get("private"):
        return

    # Ignorar mensagens outgoing (da Júlia)
    if message.get("message_type") == "outgoing":
        # Verificar se foi a Júlia ou o gestor
        sender = message.get("sender", {})
        if sender.get("type") == "user":  # Agente humano
            await encaminhar_para_whatsapp(conversation, message)


async def encaminhar_para_whatsapp(conversation: dict, message: dict):
    """Encaminha mensagem do gestor para WhatsApp."""
    conversation_id = conversation.get("id")

    # Buscar nossa conversa
    response = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("chatwoot_conversation_id", conversation_id)
        .execute()
    )

    if not response.data:
        return

    conversa = response.data[0]
    telefone = conversa["clientes"]["telefone"]

    # Enviar para WhatsApp
    await whatsapp_service.enviar_mensagem(
        telefone=telefone,
        texto=message["content"]
    )

    # Salvar interação
    supabase.table("interacoes").insert({
        "conversa_id": conversa["id"],
        "direcao": "saida",
        "tipo": "texto",
        "conteudo": message["content"],
        "origem": "humano"
    }).execute()
```

### 3. Registrar rota no main.py

```python
# app/main.py (adicionar)
from app.routes.chatwoot import router as chatwoot_router

app.include_router(chatwoot_router)
```

## DoD

- [ ] Endpoint `/chatwoot/webhook` criado
- [ ] Evento `conversation_updated` processado
- [ ] Label "humano" detectada corretamente
- [ ] Handoff iniciado quando label adicionada
- [ ] Mensagens do gestor encaminhadas para WhatsApp

---

# S2.E2.5 - Testar fluxo completo Chatwoot

## Objetivo

> **Validar integração completa Chatwoot em ambiente real.**

**Resultado esperado:** Fluxo médico → Júlia → Chatwoot funciona sem erros.

## Tarefas

### 1. Configurar webhook no Chatwoot

```
1. Acessar Chatwoot (http://localhost:3000)
2. Settings → Integrations → Configure Webhooks
3. Adicionar URL: https://seu-dominio.com/chatwoot/webhook
4. Selecionar eventos:
   - conversation_updated
   - message_created
5. Salvar
```

### 2. Teste de sincronização

```
CENÁRIO 1: Nova conversa
1. Enviar "Oi" pelo WhatsApp para Júlia
2. Verificar se conversa aparece no Chatwoot
3. Verificar se mensagem "Oi" aparece
4. Verificar se resposta da Júlia aparece

CENÁRIO 2: Label humano
1. No Chatwoot, adicionar label "humano" à conversa
2. Verificar se conversa mudou para controlled_by = "human"
3. Enviar nova mensagem pelo WhatsApp
4. Verificar se Júlia NÃO responde

CENÁRIO 3: Gestor responde
1. No Chatwoot, escrever mensagem na conversa
2. Verificar se mensagem chega no WhatsApp do médico
3. Verificar se interação salva com origem = "humano"
```

### 3. Script de teste automatizado

```python
# tests/test_chatwoot_integration.py

import pytest
from app.services.chatwoot import chatwoot_service

@pytest.mark.asyncio
async def test_criar_contato():
    """Testa criação de contato no Chatwoot."""
    contato = await chatwoot_service.criar_contato(
        nome="Dr. Teste",
        telefone="+5511999999999"
    )
    assert contato["id"] is not None
    assert contato["name"] == "Dr. Teste"

@pytest.mark.asyncio
async def test_criar_conversa():
    """Testa criação de conversa no Chatwoot."""
    # Primeiro criar contato
    contato = await chatwoot_service.criar_contato(
        nome="Dr. Teste Conversa",
        telefone="+5511988888888"
    )

    conversa = await chatwoot_service.criar_conversa(
        contact_id=contato["id"]
    )
    assert conversa["id"] is not None

@pytest.mark.asyncio
async def test_enviar_mensagem():
    """Testa envio de mensagem no Chatwoot."""
    # Criar contato e conversa primeiro
    contato = await chatwoot_service.criar_contato(
        nome="Dr. Teste Msg",
        telefone="+5511977777777"
    )
    conversa = await chatwoot_service.criar_conversa(
        contact_id=contato["id"]
    )

    mensagem = await chatwoot_service.enviar_mensagem(
        conversation_id=conversa["id"],
        content="Mensagem de teste",
        message_type="incoming"
    )
    assert mensagem["id"] is not None
```

## DoD

- [ ] Webhook configurado no Chatwoot
- [ ] Nova conversa aparece automaticamente
- [ ] Mensagens sincronizam em tempo real
- [ ] Label "humano" ativa handoff
- [ ] Mensagem do gestor chega no WhatsApp
- [ ] Testes automatizados passam
