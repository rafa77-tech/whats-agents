# Epic 08: Multi-Provider Support

**Status:** Pendente
**Estimativa:** 4 horas
**Prioridade:** Alta
**Dependencia:** E01-E06 (infraestrutura multi-chip)
**Responsavel:** Dev

---

## Objetivo

Criar sistema de **abstração de providers WhatsApp** para suportar múltiplas APIs:
- Evolution API (atual)
- Z-API (novo)
- Preparado para futuros providers

### Contexto

| Provider | Tipo | Uso Atual |
|----------|------|-----------|
| Evolution API | Self-hosted | Julia principal + warming |
| Z-API | SaaS (pago) | 1 instância existente |

### Benefícios

- Pool de chips heterogêneo (mix de providers)
- Redundância (se um provider falha, outros continuam)
- Flexibilidade para adicionar novos providers
- Aproveitar instância Z-API já paga

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROVIDER ABSTRACTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  WhatsAppProvider (ABC)                  │   │
│  │                                                          │   │
│  │  + send_text(phone, message) -> MessageResult           │   │
│  │  + send_media(phone, media_url, caption) -> Result      │   │
│  │  + get_status() -> ConnectionStatus                     │   │
│  │  + is_connected() -> bool                               │   │
│  │  + get_qr_code() -> Optional[str]                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│              │                            │                     │
│              ▼                            ▼                     │
│  ┌─────────────────────┐      ┌─────────────────────┐         │
│  │  EvolutionProvider  │      │     ZApiProvider    │         │
│  │                     │      │                     │         │
│  │  base_url           │      │  instance_id        │         │
│  │  api_key            │      │  token              │         │
│  │  instance_name      │      │  client_token       │         │
│  └─────────────────────┘      └─────────────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Comparação de APIs

### Enviar Texto

| Aspecto | Evolution API | Z-API |
|---------|---------------|-------|
| Endpoint | `POST /message/sendText/{instance}` | `POST /instances/{id}/token/{token}/send-text` |
| Auth | Header `apikey` | Header `Client-Token` |
| Body phone | `number` | `phone` |
| Body text | `text` | `message` |
| Response ID | `key.id` | `messageId` |

### Webhooks

| Evento | Evolution API | Z-API |
|--------|---------------|-------|
| Msg recebida | `MESSAGES_UPSERT` | Webhook "Receive" |
| Status msg | `MESSAGES_UPDATE` | Webhook "Status" |
| Conexão | `CONNECTION_UPDATE` | Webhook "Disconnected" |

---

## Stories

### S8.1: Migration - Adicionar campo provider

**Objetivo:** Adicionar coluna `provider` na tabela `chips`.

```sql
-- Migration: add_provider_to_chips
ALTER TABLE chips
ADD COLUMN provider TEXT NOT NULL DEFAULT 'evolution';

-- Valores: 'evolution', 'z-api', 'cloud-api' (futuro)
COMMENT ON COLUMN chips.provider IS 'WhatsApp API provider: evolution, z-api';

-- Index para queries por provider
CREATE INDEX idx_chips_provider ON chips(provider);
```

**Critério de Aceite:**
- [ ] Coluna adicionada com default 'evolution'
- [ ] Chips existentes mantêm funcionamento

---

### S8.2: Provider Interface (ABC)

**Objetivo:** Criar interface abstrata para providers.

```python
# app/services/whatsapp_providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class ProviderType(str, Enum):
    EVOLUTION = "evolution"
    ZAPI = "z-api"

@dataclass
class MessageResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None

@dataclass
class ConnectionStatus:
    connected: bool
    state: str  # 'open', 'close', 'connecting'
    qr_code: Optional[str] = None

class WhatsAppProvider(ABC):
    """Interface abstrata para providers WhatsApp."""

    provider_type: ProviderType

    @abstractmethod
    async def send_text(self, phone: str, message: str) -> MessageResult:
        """Envia mensagem de texto."""
        pass

    @abstractmethod
    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image"
    ) -> MessageResult:
        """Envia mídia (imagem, documento, áudio)."""
        pass

    @abstractmethod
    async def get_status(self) -> ConnectionStatus:
        """Retorna status da conexão."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Verifica se está conectado."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Desconecta a instância."""
        pass
```

**Critério de Aceite:**
- [ ] Interface criada em `app/services/whatsapp_providers/base.py`
- [ ] Tipos de retorno bem definidos

---

### S8.3: Evolution Provider

**Objetivo:** Adaptar código Evolution existente para interface.

```python
# app/services/whatsapp_providers/evolution.py

from app.services.whatsapp_providers.base import (
    WhatsAppProvider, ProviderType, MessageResult, ConnectionStatus
)
from app.core.config import settings
import httpx

class EvolutionProvider(WhatsAppProvider):
    """Provider para Evolution API."""

    provider_type = ProviderType.EVOLUTION

    def __init__(self, instance_name: str):
        self.instance_name = instance_name
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY

    @property
    def headers(self) -> dict:
        return {"apikey": self.api_key}

    async def send_text(self, phone: str, message: str) -> MessageResult:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance_name}",
                headers=self.headers,
                json={"number": phone, "text": message}
            )

            if response.status_code == 200:
                data = response.json()
                return MessageResult(
                    success=True,
                    message_id=data.get("key", {}).get("id")
                )
            return MessageResult(success=False, error=response.text)

    async def get_status(self) -> ConnectionStatus:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/instance/connectionState/{self.instance_name}",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                state = data.get("state", "close")
                return ConnectionStatus(
                    connected=(state == "open"),
                    state=state,
                    qr_code=data.get("qrcode")
                )
            return ConnectionStatus(connected=False, state="error")

    # ... outros métodos
```

**Critério de Aceite:**
- [ ] EvolutionProvider implementa WhatsAppProvider
- [ ] Funcionalidade existente preservada
- [ ] Testes passando

---

### S8.4: Z-API Provider

**Objetivo:** Implementar provider para Z-API.

```python
# app/services/whatsapp_providers/zapi.py

from app.services.whatsapp_providers.base import (
    WhatsAppProvider, ProviderType, MessageResult, ConnectionStatus
)
import httpx

class ZApiProvider(WhatsAppProvider):
    """Provider para Z-API."""

    provider_type = ProviderType.ZAPI
    BASE_URL = "https://api.z-api.io"

    def __init__(self, instance_id: str, token: str, client_token: str):
        self.instance_id = instance_id
        self.token = token
        self.client_token = client_token

    @property
    def base_endpoint(self) -> str:
        return f"{self.BASE_URL}/instances/{self.instance_id}/token/{self.token}"

    @property
    def headers(self) -> dict:
        return {"Client-Token": self.client_token}

    async def send_text(self, phone: str, message: str) -> MessageResult:
        # Formatar telefone (remover +, espaços, etc)
        phone_clean = "".join(filter(str.isdigit, phone))

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_endpoint}/send-text",
                headers=self.headers,
                json={
                    "phone": phone_clean,
                    "message": message
                }
            )

            if response.status_code == 200:
                data = response.json()
                return MessageResult(
                    success=True,
                    message_id=data.get("messageId")
                )
            return MessageResult(success=False, error=response.text)

    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: str = None,
        media_type: str = "image"
    ) -> MessageResult:
        phone_clean = "".join(filter(str.isdigit, phone))

        endpoint_map = {
            "image": "send-image",
            "document": "send-document",
            "audio": "send-audio",
            "video": "send-video",
        }
        endpoint = endpoint_map.get(media_type, "send-image")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_endpoint}/{endpoint}",
                headers=self.headers,
                json={
                    "phone": phone_clean,
                    "image": media_url,  # Z-API usa 'image' para URL
                    "caption": caption or ""
                }
            )

            if response.status_code == 200:
                data = response.json()
                return MessageResult(
                    success=True,
                    message_id=data.get("messageId")
                )
            return MessageResult(success=False, error=response.text)

    async def get_status(self) -> ConnectionStatus:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_endpoint}/status",
                headers=self.headers
            )

            if response.status_code == 200:
                data = response.json()
                connected = data.get("connected", False)
                return ConnectionStatus(
                    connected=connected,
                    state="open" if connected else "close"
                )
            return ConnectionStatus(connected=False, state="error")

    async def is_connected(self) -> bool:
        status = await self.get_status()
        return status.connected

    async def disconnect(self) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_endpoint}/disconnect",
                headers=self.headers
            )
            return response.status_code == 200
```

**Critério de Aceite:**
- [ ] ZApiProvider implementa WhatsAppProvider
- [ ] Envia texto com sucesso
- [ ] Envia mídia com sucesso
- [ ] Verifica status de conexão

---

### S8.5: Provider Factory

**Objetivo:** Factory para criar provider correto baseado no chip.

```python
# app/services/whatsapp_providers/__init__.py

from typing import Dict, Optional
from app.services.whatsapp_providers.base import WhatsAppProvider, ProviderType
from app.services.whatsapp_providers.evolution import EvolutionProvider
from app.services.whatsapp_providers.zapi import ZApiProvider

# Cache de providers (evita criar múltiplas instâncias)
_provider_cache: Dict[str, WhatsAppProvider] = {}

def get_provider(chip: dict) -> WhatsAppProvider:
    """
    Retorna provider apropriado para o chip.

    Args:
        chip: Dict com dados do chip (da tabela chips)

    Returns:
        WhatsAppProvider configurado
    """
    chip_id = chip["id"]

    # Retornar do cache se existir
    if chip_id in _provider_cache:
        return _provider_cache[chip_id]

    provider_type = chip.get("provider", "evolution")

    if provider_type == "evolution":
        provider = EvolutionProvider(
            instance_name=chip["instance_name"]
        )
    elif provider_type == "z-api":
        provider = ZApiProvider(
            instance_id=chip["zapi_instance_id"],
            token=chip["zapi_token"],
            client_token=chip["zapi_client_token"]
        )
    else:
        raise ValueError(f"Provider desconhecido: {provider_type}")

    _provider_cache[chip_id] = provider
    return provider

def clear_provider_cache(chip_id: Optional[str] = None):
    """Limpa cache de providers."""
    if chip_id:
        _provider_cache.pop(chip_id, None)
    else:
        _provider_cache.clear()
```

**Critério de Aceite:**
- [ ] Factory retorna provider correto
- [ ] Cache funciona corretamente
- [ ] Erro claro para provider desconhecido

---

### S8.6: Atualizar Chip Selector

**Objetivo:** Usar provider abstraction no selector.

```python
# Atualizar app/services/chips/selector.py

from app.services.whatsapp_providers import get_provider

async def enviar_mensagem_chip(chip: dict, phone: str, message: str) -> dict:
    """Envia mensagem usando o provider correto do chip."""
    provider = get_provider(chip)
    result = await provider.send_text(phone, message)

    return {
        "success": result.success,
        "message_id": result.message_id,
        "error": result.error,
        "provider": provider.provider_type.value
    }
```

**Critério de Aceite:**
- [ ] Selector usa provider abstraction
- [ ] Mensagens enviadas corretamente por ambos providers

---

### S8.7: Migration para campos Z-API

**Objetivo:** Adicionar campos específicos do Z-API na tabela chips.

```sql
-- Migration: add_zapi_fields
ALTER TABLE chips
ADD COLUMN zapi_instance_id TEXT,
ADD COLUMN zapi_token TEXT,
ADD COLUMN zapi_client_token TEXT;

COMMENT ON COLUMN chips.zapi_instance_id IS 'Z-API: Instance ID';
COMMENT ON COLUMN chips.zapi_token IS 'Z-API: Token da instância';
COMMENT ON COLUMN chips.zapi_client_token IS 'Z-API: Client Token da conta';
```

**Critério de Aceite:**
- [ ] Campos adicionados
- [ ] Chips Evolution não afetados (campos NULL)

---

## Configuração Z-API

Para adicionar um chip Z-API, será necessário:

```
ZAPI_INSTANCE_ID=xxx      # ID da instância no painel Z-API
ZAPI_TOKEN=xxx            # Token da instância
ZAPI_CLIENT_TOKEN=xxx     # Token da conta (header Client-Token)
```

Esses valores são encontrados no painel Z-API em:
- Admin > Instância > Configurações

---

## Checklist Final

- [ ] **S8.1** - Migration provider column
- [ ] **S8.2** - Interface WhatsAppProvider
- [ ] **S8.3** - EvolutionProvider
- [ ] **S8.4** - ZApiProvider
- [ ] **S8.5** - Provider Factory
- [ ] **S8.6** - Atualizar Chip Selector
- [ ] **S8.7** - Migration campos Z-API
- [ ] Testes de integração
- [ ] Documentação atualizada

---

## Referências

- [Z-API Docs - Enviar Texto](https://developer.z-api.io/en/message/send-message-text)
- [Z-API Docs - Webhooks](https://developer.z-api.io/en/webhooks/introduction)
- [Z-API GitHub](https://github.com/z-api)

---

*Epic criado em 12/01/2026*
*Autor: Claude + Rafael*
