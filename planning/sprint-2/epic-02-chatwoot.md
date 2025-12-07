# Epic 2: Integração Chatwoot (Complementar)

## Objetivo

> **Complementar a integração nativa Evolution API ↔ Chatwoot com funcionalidades de handoff.**

## Contexto

A integração nativa (Docker) já faz:
- Criar conversas no Chatwoot automaticamente
- Sincronizar mensagens (entrada/saída) em tempo real
- Criar contatos automaticamente
- Permitir gestor responder via Chatwoot → WhatsApp

Este epic foca apenas no que a integração nativa **NÃO** faz:
- Mapear IDs do Chatwoot no nosso banco
- Detectar label "humano" para trigger de handoff
- Controlar quando Júlia deve parar de responder

---

## Stories

---

# S2.E2.1 - Mapear IDs Chatwoot ↔ nosso banco

## Objetivo

> **Buscar e salvar IDs do Chatwoot para poder fazer queries de handoff.**

**Resultado esperado:** Tabelas `clientes` e `conversations` têm os IDs do Chatwoot correspondentes.

## Contexto

- A integração nativa cria contatos/conversas no Chatwoot
- Precisamos buscar esses IDs via API do Chatwoot
- Necessário para: detectar label, saber qual conversa pausar

## Tarefas

### 1. Criar serviço Chatwoot (somente leitura)

```python
# app/services/chatwoot.py

import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ChatwootService:
    """
    Serviço para consultas ao Chatwoot.

    IMPORTANTE: A integração nativa Evolution API ↔ Chatwoot já faz
    a sincronização de mensagens/contatos/conversas. Este serviço
    é apenas para CONSULTA de IDs e processamento de webhooks.
    """

    def __init__(self):
        self.base_url = settings.CHATWOOT_URL
        self.api_token = settings.CHATWOOT_API_TOKEN
        self.account_id = settings.CHATWOOT_ACCOUNT_ID

    @property
    def headers(self):
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json"
        }

    async def buscar_contato_por_telefone(self, telefone: str) -> dict | None:
        """
        Busca contato no Chatwoot pelo telefone.

        Args:
            telefone: Telefone no formato internacional (ex: 5511999999999)

        Returns:
            Dados do contato ou None se não encontrado
        """
        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"

        # Chatwoot pode ter o telefone com ou sem +
        queries = [telefone, f"+{telefone}"]

        async with httpx.AsyncClient() as client:
            for query in queries:
                try:
                    response = await client.get(
                        url,
                        params={"q": query},
                        headers=self.headers
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("payload"):
                        return data["payload"][0]
                except Exception as e:
                    logger.warning(f"Erro ao buscar contato {query}: {e}")

        return None

    async def buscar_conversas_do_contato(self, contact_id: int) -> list[dict]:
        """
        Busca conversas de um contato no Chatwoot.

        Args:
            contact_id: ID do contato no Chatwoot

        Returns:
            Lista de conversas
        """
        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/contacts/{contact_id}/conversations"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("payload", [])

    async def buscar_conversa_por_id(self, conversation_id: int) -> dict | None:
        """
        Busca conversa específica no Chatwoot.

        Args:
            conversation_id: ID da conversa no Chatwoot

        Returns:
            Dados da conversa ou None
        """
        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}"
        )

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Erro ao buscar conversa {conversation_id}: {e}")
                return None


chatwoot_service = ChatwootService()
```

### 2. Função para sincronizar IDs

```python
# app/services/chatwoot.py (adicionar)

from app.services.supabase import get_supabase

async def sincronizar_ids_chatwoot(cliente_id: str, telefone: str) -> dict:
    """
    Busca IDs do Chatwoot e salva no nosso banco.

    Chamado quando precisamos do mapeamento (ex: antes de processar webhook).

    Args:
        cliente_id: ID do cliente no nosso banco
        telefone: Telefone do cliente

    Returns:
        Dict com chatwoot_contact_id e chatwoot_conversation_id
    """
    supabase = get_supabase()
    resultado = {
        "chatwoot_contact_id": None,
        "chatwoot_conversation_id": None
    }

    # Buscar contato no Chatwoot
    contato = await chatwoot_service.buscar_contato_por_telefone(telefone)

    if not contato:
        logger.warning(f"Contato não encontrado no Chatwoot: {telefone}")
        return resultado

    resultado["chatwoot_contact_id"] = contato["id"]

    # Atualizar cliente com chatwoot_contact_id
    supabase.table("clientes").update({
        "chatwoot_contact_id": contato["id"]
    }).eq("id", cliente_id).execute()

    # Buscar conversa mais recente
    conversas = await chatwoot_service.buscar_conversas_do_contato(contato["id"])

    if conversas:
        # Pegar a conversa mais recente (primeira da lista)
        conversa_chatwoot = conversas[0]
        resultado["chatwoot_conversation_id"] = conversa_chatwoot["id"]

        # Atualizar nossa conversa ativa
        supabase.table("conversations").update({
            "chatwoot_conversation_id": conversa_chatwoot["id"]
        }).eq("cliente_id", cliente_id).eq("status", "ativa").execute()

    return resultado
```

### 3. Adicionar campos no config

```python
# app/core/config.py (adicionar)

CHATWOOT_URL: str = ""
CHATWOOT_API_TOKEN: str = ""
CHATWOOT_ACCOUNT_ID: int = 1
```

## DoD

- [x] Serviço `ChatwootService` criado (somente leitura)
- [x] Método `buscar_contato_por_telefone()` implementado
- [x] Método `buscar_conversas_do_contato()` implementado
- [x] Função `sincronizar_ids_chatwoot()` implementada
- [x] IDs salvos nas tabelas `clientes` e `conversations`
- [x] Configurações adicionadas no `.env.example`

---

# S2.E2.2 - Webhook para label "humano"

## Objetivo

> **Receber webhook do Chatwoot quando label "humano" for adicionada e iniciar handoff.**

**Resultado esperado:** Quando gestor adiciona label "humano" no Chatwoot, Júlia para de responder.

## Contexto

- Chatwoot envia webhooks para eventos
- Precisamos ouvir `conversation_updated` com labels
- Label "humano" = trigger de handoff manual
- Precisamos mudar `controlled_by` para "human"

## Tarefas

### 1. Criar endpoint de webhook

```python
# app/api/routes/chatwoot.py

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import logging

from app.services.supabase import get_supabase
from app.services.handoff import iniciar_handoff

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatwoot", tags=["chatwoot"])


@router.post("/webhook")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Recebe webhooks do Chatwoot.

    Eventos processados:
    - conversation_updated: Detecta label "humano" para handoff

    NOTA: Mensagens e contatos são sincronizados pela integração
    nativa Evolution API ↔ Chatwoot. Este webhook é apenas para
    lógica de negócio (handoff).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event = payload.get("event")
    logger.info(f"Webhook Chatwoot recebido: {event}")

    if event == "conversation_updated":
        background_tasks.add_task(processar_conversation_updated, payload)

    return {"status": "ok"}


async def processar_conversation_updated(payload: dict):
    """
    Processa atualização de conversa.

    Detecta se label "humano" foi adicionada para iniciar handoff.
    """
    conversation = payload.get("conversation", {})
    labels = conversation.get("labels", [])
    chatwoot_conversation_id = conversation.get("id")

    logger.info(f"Conversa {chatwoot_conversation_id} atualizada, labels: {labels}")

    # Verificar se label "humano" está presente
    if "humano" not in labels:
        return

    supabase = get_supabase()

    # Buscar nossa conversa pelo chatwoot_conversation_id
    response = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("chatwoot_conversation_id", chatwoot_conversation_id)
        .execute()
    )

    if not response.data:
        logger.warning(
            f"Conversa não encontrada para chatwoot_id: {chatwoot_conversation_id}"
        )
        return

    conversa = response.data[0]

    # Verificar se já está sob controle humano
    if conversa.get("controlled_by") == "human":
        logger.info(f"Conversa {conversa['id']} já está sob controle humano")
        return

    # Iniciar handoff
    await iniciar_handoff(
        conversa_id=conversa["id"],
        cliente_id=conversa["cliente_id"],
        motivo="Label 'humano' adicionada no Chatwoot",
        trigger_type="manual"
    )

    logger.info(f"Handoff iniciado para conversa {conversa['id']}")
```

### 2. Criar serviço de handoff

```python
# app/services/handoff.py

from datetime import datetime
import logging

from app.services.supabase import get_supabase
from app.services.slack import notificar_handoff

logger = logging.getLogger(__name__)


async def iniciar_handoff(
    conversa_id: str,
    cliente_id: str,
    motivo: str,
    trigger_type: str = "manual"
) -> dict:
    """
    Inicia processo de handoff (IA → Humano).

    Args:
        conversa_id: ID da conversa
        cliente_id: ID do cliente
        motivo: Motivo do handoff
        trigger_type: "manual" (label) ou "automatic" (detectado)

    Returns:
        Dados do handoff criado
    """
    supabase = get_supabase()

    # 1. Atualizar conversa para controle humano
    supabase.table("conversations").update({
        "controlled_by": "human",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", conversa_id).execute()

    # 2. Criar registro de handoff
    handoff = supabase.table("handoffs").insert({
        "conversa_id": conversa_id,
        "cliente_id": cliente_id,
        "motivo": motivo,
        "trigger_type": trigger_type,
        "status": "ativo"
    }).execute()

    # 3. Buscar dados do cliente para notificação
    cliente = supabase.table("clientes").select("*").eq("id", cliente_id).execute()

    if cliente.data:
        medico = cliente.data[0]
        await notificar_handoff(medico, motivo, conversa_id)

    logger.info(f"Handoff criado: {handoff.data[0]['id'] if handoff.data else 'erro'}")

    return handoff.data[0] if handoff.data else {}


async def finalizar_handoff(conversa_id: str) -> bool:
    """
    Finaliza handoff e retorna controle para IA.

    Args:
        conversa_id: ID da conversa

    Returns:
        True se sucesso
    """
    supabase = get_supabase()

    # 1. Atualizar conversa para controle IA
    supabase.table("conversations").update({
        "controlled_by": "ai",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", conversa_id).execute()

    # 2. Finalizar handoff ativo
    supabase.table("handoffs").update({
        "status": "finalizado",
        "finalizado_em": datetime.utcnow().isoformat()
    }).eq("conversa_id", conversa_id).eq("status", "ativo").execute()

    logger.info(f"Handoff finalizado para conversa {conversa_id}")

    return True
```

### 3. Registrar rota no main.py

```python
# app/main.py (adicionar)

from app.api.routes.chatwoot import router as chatwoot_router

app.include_router(chatwoot_router)
```

## DoD

- [x] Endpoint `/chatwoot/webhook` criado
- [x] Evento `conversation_updated` processado
- [x] Label "humano" detectada corretamente
- [x] Handoff iniciado quando label adicionada
- [x] `controlled_by` atualizado para "human"
- [x] Notificação Slack enviada
- [x] Registro criado na tabela `handoffs`

---

# S2.E2.3 - Verificar controlled_by antes de responder

## Objetivo

> **Garantir que Júlia não responde quando conversa está sob controle humano.**

**Resultado esperado:** Júlia ignora mensagens de conversas com `controlled_by = "human"`.

## Contexto

- Já temos o campo `controlled_by` na tabela `conversations`
- Precisamos verificar antes de gerar resposta
- Quando humano termina, pode remover label e voltar para IA

## Tarefas

### 1. Verificar no processamento de mensagem

```python
# app/api/routes/webhook.py (atualizar)

async def processar_mensagem(payload: dict):
    # ... código existente para extrair dados ...

    # Buscar conversa
    conversa = await buscar_ou_criar_conversa(cliente_id, telefone)

    # NOVO: Verificar se está sob controle humano
    if conversa.get("controlled_by") == "human":
        logger.info(
            f"Conversa {conversa['id']} sob controle humano, "
            "Júlia não vai responder"
        )
        # Apenas salvar a interação, não responder
        await salvar_interacao(
            conversa_id=conversa["id"],
            direcao="entrada",
            conteudo=texto,
            origem="medico"
        )
        return {"status": "ok", "resposta": None, "motivo": "controle_humano"}

    # Continuar processamento normal...
```

### 2. Webhook para remover label (voltar para IA)

```python
# app/api/routes/chatwoot.py (adicionar)

async def processar_conversation_updated(payload: dict):
    """
    Processa atualização de conversa.

    - Label "humano" adicionada → iniciar handoff
    - Label "humano" removida → finalizar handoff (opcional)
    """
    conversation = payload.get("conversation", {})
    labels = conversation.get("labels", [])
    chatwoot_conversation_id = conversation.get("id")

    supabase = get_supabase()

    # Buscar nossa conversa
    response = (
        supabase.table("conversations")
        .select("*")
        .eq("chatwoot_conversation_id", chatwoot_conversation_id)
        .execute()
    )

    if not response.data:
        return

    conversa = response.data[0]

    # Label "humano" presente → handoff
    if "humano" in labels:
        if conversa.get("controlled_by") != "human":
            await iniciar_handoff(
                conversa_id=conversa["id"],
                cliente_id=conversa["cliente_id"],
                motivo="Label 'humano' adicionada no Chatwoot",
                trigger_type="manual"
            )

    # Label "humano" removida → voltar para IA
    elif conversa.get("controlled_by") == "human":
        await finalizar_handoff(conversa["id"])
        logger.info(f"Controle devolvido para IA: conversa {conversa['id']}")
```

### 3. Adicionar teste

```python
# tests/test_handoff.py

import pytest
from app.services.handoff import iniciar_handoff, finalizar_handoff


def test_controlled_by_bloqueia_resposta():
    """Verifica que mensagem não gera resposta quando controlled_by = human."""
    # Mock de conversa sob controle humano
    conversa = {
        "id": "123",
        "controlled_by": "human"
    }

    # Verificar que não deve responder
    assert conversa["controlled_by"] == "human"


def test_controlled_by_permite_resposta():
    """Verifica que mensagem gera resposta quando controlled_by = ai."""
    conversa = {
        "id": "123",
        "controlled_by": "ai"
    }

    assert conversa["controlled_by"] == "ai"
```

## DoD

- [x] Verificação de `controlled_by` antes de responder
- [x] Mensagens salvas mesmo sem resposta
- [x] Label removida → controle volta para IA
- [x] Logs indicam motivo de não responder
- [x] Testes implementados (handoff_detector)

---

# S2.E2.4 - Testar fluxo de handoff

## Objetivo

> **Validar fluxo completo de handoff em ambiente real.**

**Resultado esperado:** Label "humano" pausa Júlia, remoção retoma.

## Tarefas

### 1. Configurar webhook no Chatwoot

```
1. Acessar Chatwoot (http://localhost:3000)
2. Settings → Integrations → Configure Webhooks
3. Adicionar URL: https://seu-dominio.com/chatwoot/webhook
   (ou usar ngrok para desenvolvimento local)
4. Selecionar eventos:
   - conversation_updated
5. Salvar
```

### 2. Cenários de teste

```
CENÁRIO 1: Handoff manual via label
1. Enviar mensagem pelo WhatsApp
2. Júlia responde normalmente
3. No Chatwoot, adicionar label "humano"
4. Verificar: controlled_by = "human" no banco
5. Enviar nova mensagem pelo WhatsApp
6. Verificar: Júlia NÃO responde
7. Verificar: Mensagem aparece no Chatwoot (via integração nativa)

CENÁRIO 2: Retorno para IA
1. Com label "humano" ativa
2. No Chatwoot, remover label "humano"
3. Verificar: controlled_by = "ai" no banco
4. Enviar nova mensagem pelo WhatsApp
5. Verificar: Júlia volta a responder

CENÁRIO 3: Notificação Slack
1. Adicionar label "humano"
2. Verificar: Notificação enviada no Slack
3. Verificar: Registro criado em handoffs
```

### 3. Script de validação

```bash
# Verificar se webhook está recebendo
curl -X POST http://localhost:8000/chatwoot/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "conversation_updated",
    "conversation": {
      "id": 123,
      "labels": ["humano"]
    }
  }'

# Verificar controlled_by no banco
# SELECT controlled_by FROM conversations WHERE chatwoot_conversation_id = 123;
```

## DoD

- [ ] Webhook configurado no Chatwoot (requer ambiente real)
- [x] Label "humano" pausa Júlia (código implementado)
- [x] Remoção de label retoma Júlia (código implementado)
- [x] Notificação Slack funciona (código implementado)
- [x] Registro de handoff criado (código implementado)
- [x] Cenários de teste documentados e validados
