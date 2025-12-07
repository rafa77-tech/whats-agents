# Epic 1: Webhook & Recebimento

## Objetivo do Epic

> **Receber mensagens do WhatsApp via Evolution API e preparar para processamento.**

Este epic estabelece a entrada de dados: quando um médico envia mensagem, precisamos capturar e preparar para a Júlia responder.

---

## Stories

1. [S1.E1.1 - Criar endpoint webhook Evolution](#s1e11---criar-endpoint-webhook-evolution)
2. [S1.E1.2 - Parser de mensagens recebidas](#s1e12---parser-de-mensagens-recebidas)
3. [S1.E1.3 - Marcar como lida + presença online](#s1e13---marcar-como-lida--presença-online)
4. [S1.E1.4 - Mostrar "digitando"](#s1e14---mostrar-digitando)
5. [S1.E1.5 - Ignorar mensagens próprias e grupos](#s1e15---ignorar-mensagens-próprias-e-grupos)

---

# S1.E1.1 - Criar endpoint webhook Evolution

## Objetivo

> **Criar endpoint que recebe webhooks da Evolution API quando chegam mensagens.**

A Evolution API envia um POST para nosso servidor sempre que uma mensagem chega. Precisamos de um endpoint para receber isso.

**Resultado esperado:** Endpoint `/webhook/evolution` que recebe e loga mensagens da Evolution.

---

## Contexto

- Evolution envia POST com payload JSON
- Eventos que nos interessam: `messages.upsert`, `connection.update`
- O endpoint deve responder rápido (200 OK) para não bloquear

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Sprint 0 completa
- [ ] Evolution API configurada com webhook apontando para nossa API

---

## Tarefas

### 1. Criar schema do payload Evolution

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/schemas/evolution.py << 'EOF'
"""
Schemas para payloads da Evolution API.
"""
from pydantic import BaseModel
from typing import Optional, Any


class MessageKey(BaseModel):
    """Identificador da mensagem."""
    remoteJid: str  # Número do remetente (5511999999999@s.whatsapp.net)
    fromMe: bool  # Se foi enviada por nós
    id: str  # ID único da mensagem


class MessageContent(BaseModel):
    """Conteúdo da mensagem."""
    conversation: Optional[str] = None  # Texto simples
    extendedTextMessage: Optional[dict] = None  # Texto com preview
    imageMessage: Optional[dict] = None
    audioMessage: Optional[dict] = None
    documentMessage: Optional[dict] = None
    # Adicionar outros tipos conforme necessário


class MessageData(BaseModel):
    """Dados da mensagem recebida."""
    key: MessageKey
    message: Optional[MessageContent] = None
    messageTimestamp: Optional[int] = None
    pushName: Optional[str] = None  # Nome do contato


class EvolutionWebhookPayload(BaseModel):
    """Payload completo do webhook Evolution."""
    event: str  # Tipo de evento (messages.upsert, connection.update, etc)
    instance: str  # Nome da instância (Revoluna)
    data: Any  # Dados variam por tipo de evento


class ConnectionUpdate(BaseModel):
    """Dados de atualização de conexão."""
    state: str  # open, close, connecting
    statusReason: Optional[int] = None
EOF
```

### 2. Criar rota de webhook

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/api/routes/webhook.py << 'EOF'
"""
Endpoints de webhook para integrações externas.
"""
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.schemas.evolution import EvolutionWebhookPayload

router = APIRouter(prefix="/webhook", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/evolution")
async def evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recebe webhooks da Evolution API.

    Responde imediatamente com 200 e processa em background
    para não bloquear a Evolution.
    """
    try:
        # Parsear payload
        payload = await request.json()
        logger.info(f"Webhook Evolution recebido: {payload.get('event')}")

        # Validar estrutura básica
        event = payload.get("event")
        instance = payload.get("instance")
        data = payload.get("data")

        if not event or not instance:
            logger.warning(f"Payload inválido: {payload}")
            return JSONResponse({"status": "invalid_payload"}, status_code=400)

        # Processar por tipo de evento
        if event == "messages.upsert":
            # Agendar processamento em background
            background_tasks.add_task(processar_mensagem, data)
            logger.info(f"Mensagem agendada para processamento")

        elif event == "connection.update":
            logger.info(f"Status conexão: {data}")

        else:
            logger.debug(f"Evento ignorado: {event}")

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        # Ainda retorna 200 para não causar retry da Evolution
        return JSONResponse({"status": "error", "message": str(e)})


async def processar_mensagem(data: dict):
    """
    Processa mensagem recebida.
    Será expandido nas próximas stories.
    """
    logger.info(f"Processando mensagem: {data}")
    # TODO: Implementar processamento completo
    pass
EOF
```

### 3. Configurar logging

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/core/logging.py << 'EOF'
"""
Configuração de logging.
"""
import logging
import sys


def setup_logging():
    """Configura logging da aplicação."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduzir verbosidade de libs externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Chamar no startup
setup_logging()
EOF
```

### 4. Registrar rota no main.py

Adicione no `app/main.py`:

```python
from app.api.routes import health, test_db, test_llm, test_whatsapp, webhook

# ...

app.include_router(webhook.router)
```

### 5. Configurar webhook na Evolution

```bash
# Atualizar webhook para apontar para nossa API
curl -X POST "http://localhost:8080/webhook/set/Revoluna" \
  -H "apikey: $AUTHENTICATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:8000/webhook/evolution",
    "enabled": true,
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }'
```

**Nota:** Use `host.docker.internal` se FastAPI roda fora do Docker. Se roda no Docker, use o nome do serviço ou IP interno.

### 6. Testar webhook

```bash
# 1. Inicie a API
uv run uvicorn app.main:app --reload --port 8000

# 2. Observe os logs

# 3. Envie uma mensagem para o número da Júlia via WhatsApp

# 4. Verifique se aparece no log:
# "Webhook Evolution recebido: messages.upsert"
# "Mensagem agendada para processamento"
```

---

## Como Testar

1. Enviar mensagem WhatsApp → log mostra "Webhook Evolution recebido"
2. Endpoint retorna 200 rapidamente (< 100ms)
3. Payload é logado corretamente

---

## DoD (Definition of Done)

- [x] Arquivo `app/schemas/evolution.py` criado
- [x] Arquivo `app/api/routes/webhook.py` criado
- [x] Endpoint `/webhook/evolution` registrado
- [x] Webhook configurado na Evolution (apontando para FastAPI)
- [x] Mensagem enviada → aparece no log ✅ Testado em 2025-12-07
- [x] Resposta do endpoint é 200 OK
- [x] Não há erros no log ✅ Testado em 2025-12-07

---

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| Webhook não chega | URL errada | Verificar URL na Evolution |
| Connection refused | FastAPI não acessível | Usar `host.docker.internal` ou IP correto |
| Timeout | Processamento lento | Usar background_tasks |

---
---

# S1.E1.2 - Parser de mensagens recebidas

## Objetivo

> **Extrair informações úteis do payload da Evolution: telefone, texto, tipo de mensagem.**

O payload da Evolution é complexo. Precisamos extrair só o que importa.

**Resultado esperado:** Função que recebe payload e retorna objeto estruturado com telefone, texto, etc.

---

## Contexto

- Telefone vem no formato `5511999999999@s.whatsapp.net`
- Texto pode vir em `conversation` ou `extendedTextMessage.text`
- Precisamos identificar tipo: texto, áudio, imagem, etc

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S1.E1.1 completa

---

## Tarefas

### 1. Criar modelo de mensagem parseada

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/schemas/mensagem.py << 'EOF'
"""
Schema para mensagem parseada (nosso formato interno).
"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class MensagemRecebida(BaseModel):
    """Mensagem recebida e parseada do WhatsApp."""

    # Identificação
    telefone: str  # Formato: 5511999999999
    message_id: str  # ID único da mensagem
    from_me: bool  # Se foi enviada por nós

    # Conteúdo
    tipo: Literal["texto", "audio", "imagem", "documento", "outro"]
    texto: Optional[str] = None  # Texto da mensagem (se houver)

    # Metadados
    nome_contato: Optional[str] = None  # Nome salvo no WhatsApp
    timestamp: datetime

    # Flags
    is_grupo: bool = False  # Se veio de grupo
    is_status: bool = False  # Se é status/story


class MensagemParaEnviar(BaseModel):
    """Mensagem a ser enviada."""
    telefone: str
    texto: str
EOF
```

### 2. Criar função de parsing

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/app/services/parser.py << 'EOF'
"""
Parser de mensagens da Evolution API.
"""
from datetime import datetime
from typing import Optional
import logging

from app.schemas.mensagem import MensagemRecebida

logger = logging.getLogger(__name__)


def extrair_telefone(jid: str) -> str:
    """
    Extrai número de telefone do JID do WhatsApp.

    Exemplo:
        "5511999999999@s.whatsapp.net" -> "5511999999999"
        "5511999999999-123456@g.us" -> "5511999999999" (grupo)
    """
    if not jid:
        return ""

    # Remover sufixo
    telefone = jid.split("@")[0]

    # Se for grupo, pegar só o primeiro número
    if "-" in telefone:
        telefone = telefone.split("-")[0]

    return telefone


def is_grupo(jid: str) -> bool:
    """Verifica se JID é de grupo."""
    return "@g.us" in jid if jid else False


def is_status(jid: str) -> bool:
    """Verifica se é status/story."""
    return "status@broadcast" in jid if jid else False


def extrair_texto(message: dict) -> Optional[str]:
    """
    Extrai texto da mensagem.
    WhatsApp tem vários formatos possíveis.
    """
    if not message:
        return None

    # Texto simples
    if "conversation" in message:
        return message["conversation"]

    # Texto com preview de link
    if "extendedTextMessage" in message:
        return message["extendedTextMessage"].get("text")

    # Legenda de imagem
    if "imageMessage" in message:
        return message["imageMessage"].get("caption")

    # Legenda de documento
    if "documentMessage" in message:
        return message["documentMessage"].get("caption")

    # Legenda de vídeo
    if "videoMessage" in message:
        return message["videoMessage"].get("caption")

    return None


def identificar_tipo(message: dict) -> str:
    """Identifica o tipo de mensagem."""
    if not message:
        return "outro"

    if "conversation" in message or "extendedTextMessage" in message:
        return "texto"
    elif "audioMessage" in message:
        return "audio"
    elif "imageMessage" in message:
        return "imagem"
    elif "documentMessage" in message:
        return "documento"
    elif "videoMessage" in message:
        return "video"
    elif "stickerMessage" in message:
        return "sticker"
    else:
        return "outro"


def parsear_mensagem(data: dict) -> Optional[MensagemRecebida]:
    """
    Converte payload da Evolution para nosso formato interno.

    Args:
        data: Payload do evento messages.upsert

    Returns:
        MensagemRecebida ou None se não for válida
    """
    try:
        # Extrair estrutura
        key = data.get("key", {})
        message = data.get("message", {})

        jid = key.get("remoteJid", "")
        from_me = key.get("fromMe", False)
        message_id = key.get("id", "")

        # Validar campos obrigatórios
        if not jid or not message_id:
            logger.warning(f"Mensagem sem JID ou ID: {data}")
            return None

        # Verificar se é grupo ou status
        if is_grupo(jid):
            logger.debug(f"Mensagem de grupo ignorada: {jid}")
            return MensagemRecebida(
                telefone=extrair_telefone(jid),
                message_id=message_id,
                from_me=from_me,
                tipo=identificar_tipo(message),
                texto=extrair_texto(message),
                nome_contato=data.get("pushName"),
                timestamp=datetime.fromtimestamp(data.get("messageTimestamp", 0)),
                is_grupo=True,
            )

        if is_status(jid):
            logger.debug("Status/story ignorado")
            return MensagemRecebida(
                telefone=extrair_telefone(jid),
                message_id=message_id,
                from_me=from_me,
                tipo="outro",
                timestamp=datetime.now(),
                is_status=True,
            )

        # Mensagem normal
        return MensagemRecebida(
            telefone=extrair_telefone(jid),
            message_id=message_id,
            from_me=from_me,
            tipo=identificar_tipo(message),
            texto=extrair_texto(message),
            nome_contato=data.get("pushName"),
            timestamp=datetime.fromtimestamp(data.get("messageTimestamp", 0)),
        )

    except Exception as e:
        logger.error(f"Erro ao parsear mensagem: {e}")
        return None
EOF
```

### 3. Atualizar webhook para usar parser

Edite `app/api/routes/webhook.py`:

```python
from app.services.parser import parsear_mensagem

async def processar_mensagem(data: dict):
    """Processa mensagem recebida."""
    # Parsear mensagem
    mensagem = parsear_mensagem(data)

    if not mensagem:
        logger.warning("Mensagem não pôde ser parseada")
        return

    logger.info(
        f"Mensagem parseada: "
        f"tel={mensagem.telefone}, "
        f"tipo={mensagem.tipo}, "
        f"from_me={mensagem.from_me}, "
        f"texto={mensagem.texto[:50] if mensagem.texto else 'N/A'}..."
    )

    # TODO: Continuar processamento
```

### 4. Criar testes unitários

```bash
cat > /Users/rafaelpivovar/Documents/Projetos/whatsapp-api/tests/test_parser.py << 'EOF'
"""
Testes do parser de mensagens.
"""
import pytest
from app.services.parser import (
    extrair_telefone,
    is_grupo,
    extrair_texto,
    identificar_tipo,
    parsear_mensagem,
)


class TestExtrairTelefone:
    def test_numero_normal(self):
        assert extrair_telefone("5511999999999@s.whatsapp.net") == "5511999999999"

    def test_grupo(self):
        assert extrair_telefone("5511999999999-123456@g.us") == "5511999999999"

    def test_vazio(self):
        assert extrair_telefone("") == ""
        assert extrair_telefone(None) == ""


class TestIsGrupo:
    def test_grupo(self):
        assert is_grupo("123@g.us") == True

    def test_individual(self):
        assert is_grupo("123@s.whatsapp.net") == False


class TestExtrairTexto:
    def test_conversation(self):
        msg = {"conversation": "Oi, tudo bem?"}
        assert extrair_texto(msg) == "Oi, tudo bem?"

    def test_extended(self):
        msg = {"extendedTextMessage": {"text": "Link: http://..."}}
        assert extrair_texto(msg) == "Link: http://..."

    def test_imagem_com_caption(self):
        msg = {"imageMessage": {"caption": "Foto do hospital"}}
        assert extrair_texto(msg) == "Foto do hospital"

    def test_sem_texto(self):
        msg = {"audioMessage": {}}
        assert extrair_texto(msg) == None


class TestIdentificarTipo:
    def test_texto(self):
        assert identificar_tipo({"conversation": "oi"}) == "texto"

    def test_audio(self):
        assert identificar_tipo({"audioMessage": {}}) == "audio"

    def test_imagem(self):
        assert identificar_tipo({"imageMessage": {}}) == "imagem"


class TestParsearMensagem:
    def test_mensagem_completa(self):
        data = {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False,
                "id": "ABC123"
            },
            "message": {
                "conversation": "Oi, tenho interesse em plantão"
            },
            "messageTimestamp": 1701888000,
            "pushName": "Dr. Carlos"
        }

        msg = parsear_mensagem(data)

        assert msg is not None
        assert msg.telefone == "5511999999999"
        assert msg.tipo == "texto"
        assert msg.texto == "Oi, tenho interesse em plantão"
        assert msg.from_me == False
        assert msg.nome_contato == "Dr. Carlos"
        assert msg.is_grupo == False
EOF
```

### 5. Rodar testes

```bash
uv run pytest tests/test_parser.py -v
```

---

## Como Testar

1. Testes unitários passam
2. Enviar mensagem texto → log mostra tipo="texto"
3. Enviar áudio → log mostra tipo="audio"
4. Telefone é extraído corretamente

---

## DoD (Definition of Done)

- [x] Schema `MensagemRecebida` criado
- [x] Função `parsear_mensagem()` implementada
- [x] Função `extrair_telefone()` implementada
- [x] Função `identificar_tipo()` implementada
- [x] Testes unitários criados e passando (34 testes)
- [x] Log mostra mensagem parseada corretamente ✅ Testado em 2025-12-07

---
---

# S1.E1.3 - Marcar como lida + presença online

## Objetivo

> **Quando receber mensagem, marcar como lida e mostrar status "online".**

Isso faz a conversa parecer mais natural - o médico vê que a mensagem foi lida.

**Resultado esperado:** Após receber mensagem, ela é marcada com ✓✓ azul e status mostra "online".

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S1.E1.2 completa

---

## Tarefas

### 1. Adicionar funções no serviço WhatsApp

Já temos as funções em `app/services/whatsapp.py`. Agora vamos usá-las.

### 2. Atualizar processamento de mensagem

Edite `app/api/routes/webhook.py`:

```python
from app.services.whatsapp import evolution, mostrar_online
from app.services.parser import parsear_mensagem

async def processar_mensagem(data: dict):
    """Processa mensagem recebida."""
    mensagem = parsear_mensagem(data)

    if not mensagem:
        return

    # Ignorar mensagens próprias
    if mensagem.from_me:
        logger.debug("Ignorando mensagem própria")
        return

    # Ignorar grupos
    if mensagem.is_grupo:
        logger.debug("Ignorando mensagem de grupo")
        return

    # Ignorar status
    if mensagem.is_status:
        logger.debug("Ignorando status")
        return

    logger.info(f"Processando mensagem de {mensagem.telefone}: {mensagem.texto}")

    try:
        # 1. Marcar como lida
        await evolution.marcar_como_lida(
            mensagem.telefone,
            mensagem.message_id
        )
        logger.debug("Mensagem marcada como lida")

        # 2. Mostrar online
        await mostrar_online(mensagem.telefone)
        logger.debug("Presença online enviada")

        # TODO: Continuar processamento (digitando, resposta)

    except Exception as e:
        logger.error(f"Erro ao processar: {e}")
```

### 3. Testar

1. Envie mensagem para a Júlia
2. Observe se os ✓✓ ficam azuis
3. Observe se o status muda para "online"

---

## DoD (Definition of Done)

- [x] Código para marcar como lida implementado (`evolution.marcar_como_lida()`)
- [x] Código para mostrar online implementado (`mostrar_online()`)
- [x] Mensagem recebida é marcada como lida (✓✓ azul) ✅ Testado em 2025-12-07
- [x] Status mostra "online" após receber mensagem ✅ Testado em 2025-12-07
- [ ] Funciona consistentemente em 5 testes seguidos - pendente validação

---
---

# S1.E1.4 - Mostrar "digitando"

## Objetivo

> **Mostrar "digitando..." enquanto a Júlia processa a resposta.**

Isso dá tempo para o LLM processar e parece mais natural.

**Resultado esperado:** Médico vê "digitando..." por alguns segundos antes da resposta chegar.

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S1.E1.3 completa

---

## Tarefas

### 1. Atualizar processamento para mostrar digitando

Edite `app/api/routes/webhook.py`:

```python
import asyncio
from app.services.whatsapp import mostrar_digitando

async def processar_mensagem(data: dict):
    # ... código anterior ...

    try:
        # 1. Marcar como lida
        await evolution.marcar_como_lida(mensagem.telefone, mensagem.message_id)

        # 2. Mostrar online
        await mostrar_online(mensagem.telefone)

        # 3. Pequena pausa (simula leitura)
        await asyncio.sleep(1)

        # 4. Mostrar digitando
        await mostrar_digitando(mensagem.telefone)
        logger.debug("Presença 'digitando' enviada")

        # TODO: Gerar e enviar resposta

    except Exception as e:
        logger.error(f"Erro: {e}")
```

### 2. Manter "digitando" durante processamento

O status "digitando" expira após alguns segundos. Se o LLM demorar, precisamos reenviar:

```python
async def manter_digitando(telefone: str, duracao_max: int = 30):
    """
    Mantém status 'digitando' por até X segundos.
    Útil enquanto aguarda resposta do LLM.
    """
    inicio = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - inicio < duracao_max:
        await mostrar_digitando(telefone)
        await asyncio.sleep(5)  # Reenviar a cada 5s
```

---

## DoD (Definition of Done)

- [x] Código para mostrar digitando implementado (`mostrar_digitando()`)
- [x] Função `manter_digitando()` implementada
- [x] Status "digitando..." aparece antes da resposta ✅ Testado em 2025-12-07
- [ ] Digitando se mantém enquanto processa - pendente (Epic 2 - LLM)
- [x] Não há erro se digitando for chamado múltiplas vezes ✅ Testado em 2025-12-07

---
---

# S1.E1.5 - Ignorar mensagens próprias e grupos

## Objetivo

> **Filtrar mensagens que não devem ser processadas: enviadas por nós, de grupos, status.**

Evita loops infinitos e processamento desnecessário.

**Resultado esperado:** Apenas mensagens de contatos individuais enviadas PARA nós são processadas.

---

## Responsável

**Dev**

---

## Pré-requisitos

- [x] Story S1.E1.2 completa

---

## Tarefas

### 1. Já implementado no S1.E1.2

O código do parser já identifica `from_me`, `is_grupo`, e `is_status`.
No processamento, já filtramos:

```python
if mensagem.from_me:
    return

if mensagem.is_grupo:
    return

if mensagem.is_status:
    return
```

### 2. Adicionar mais validações

```python
def deve_processar(mensagem: MensagemRecebida) -> bool:
    """Verifica se mensagem deve ser processada."""

    # Ignorar nossas próprias mensagens
    if mensagem.from_me:
        return False

    # Ignorar grupos
    if mensagem.is_grupo:
        return False

    # Ignorar status/stories
    if mensagem.is_status:
        return False

    # Ignorar se não tem telefone válido
    if not mensagem.telefone or len(mensagem.telefone) < 10:
        return False

    # Ignorar certos tipos de mensagem (opcional)
    # if mensagem.tipo in ["sticker", "outro"]:
    #     return False

    return True
```

### 3. Testar cenários

1. Enviar mensagem DO número da Júlia → não processa
2. Enviar em grupo que Júlia está → não processa
3. Postar status → não processa
4. Enviar mensagem individual PARA Júlia → processa

---

## DoD (Definition of Done)

- [x] Função `deve_processar()` implementada
- [x] Filtro de mensagens próprias implementado (`from_me`)
- [x] Filtro de grupos implementado (`is_grupo`)
- [x] Filtro de status/stories implementado (`is_status`)
- [x] Testes unitários para `deve_processar()` passando
- [x] Mensagens próprias não são processadas ✅ Testado em 2025-12-07
- [ ] Mensagens de grupos não são processadas - pendente teste
- [ ] Status/stories não são processados - pendente teste
- [x] Log indica claramente quando ignora mensagem ✅ (usa logger.debug)
- [x] Apenas mensagens válidas chegam ao processamento ✅ Testado em 2025-12-07
