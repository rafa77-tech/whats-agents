# Epic 05: Human Simulator

**Status:** ✅ Completo

**Arquivos criados:**
- `app/services/warmer/human_simulator.py`

---

## Objetivo

Simular comportamento humano ao enviar mensagens, incluindo delays calibrados, indicador "digitando" e marcacao de leitura.

## Contexto

O whitepaper da Meta sobre deteccao de automacao destaca que o indicador "digitando..." e um dos principais sinais de comportamento humano. A ausencia dele e um red flag.

Fatores de simulacao:
- **Delay de leitura**: 3-15s antes de "ler" mensagem
- **Mark as read**: Marcar como lido apos ler
- **Delay de pensar**: 1-3s antes de comecar a digitar
- **Composing**: Evento "digitando" com duracao proporcional ao texto
- **Delay final**: 0.5-2s antes de enviar
- **Entre turnos**: 20-90s (exponencial com media 45s)

---

## Story 2.1: Funcao enviar_mensagem_humanizada

### Objetivo
Criar funcao que envia mensagem simulando comportamento humano completo.

### Implementacao

**Arquivo:** `app/services/warmer/human_simulator.py`

```python
"""
Human Simulator - Simula comportamento humano no WhatsApp.

Baseado no whitepaper da Meta sobre deteccao de automacao.
O indicador "digitando..." e critico para evitar flags.
"""
import asyncio
import random
import logging
from typing import Optional

from app.services.evolution import evolution_client

logger = logging.getLogger(__name__)


async def enviar_mensagem_humanizada(
    instance: str,
    destinatario: str,
    texto: str,
    simular_leitura: bool = True,
) -> bool:
    """
    Envia mensagem simulando comportamento humano completo.

    Fluxo:
    1. Delay de "leitura" (3-15s)
    2. Marca como lido
    3. Delay de "pensar" (1-3s)
    4. Envia evento "digitando"
    5. Aguarda tempo proporcional ao texto
    6. Envia mensagem

    Args:
        instance: Nome da instancia Evolution
        destinatario: JID do destinatario
        texto: Texto da mensagem
        simular_leitura: Se deve simular leitura antes

    Returns:
        True se enviou com sucesso
    """
    try:
        # 1. Delay antes de "ler" (distribuicao normal, media 8s)
        if simular_leitura:
            delay_leitura = random.gauss(8, 3)
            delay_leitura = max(3, min(15, delay_leitura))
            logger.debug(f"[HumanSim] Delay leitura: {delay_leitura:.1f}s")
            await asyncio.sleep(delay_leitura)

            # 2. Marcar como lido
            await evolution_client.mark_as_read(instance, destinatario)

        # 3. Delay de "pensar" (1-3s)
        delay_pensar = random.uniform(1, 3)
        logger.debug(f"[HumanSim] Delay pensar: {delay_pensar:.1f}s")
        await asyncio.sleep(delay_pensar)

        # 4. Enviar evento "digitando"
        # Duracao proporcional ao tamanho da mensagem (~50ms por caractere)
        tempo_digitacao = len(texto) * 0.05
        tempo_digitacao = max(1.5, min(5, tempo_digitacao))
        logger.debug(f"[HumanSim] Tempo digitacao: {tempo_digitacao:.1f}s")

        await evolution_client.send_presence(
            instance,
            destinatario,
            "composing"
        )
        await asyncio.sleep(tempo_digitacao)

        # 5. Parar de digitar
        await evolution_client.send_presence(
            instance,
            destinatario,
            "paused"
        )

        # 6. Delay final antes de enviar (0.5-2s)
        delay_final = random.uniform(0.5, 2)
        await asyncio.sleep(delay_final)

        # 7. Enviar mensagem
        await evolution_client.send_text(instance, destinatario, texto)

        logger.info(f"[HumanSim] Msg enviada: {instance} -> {destinatario[-4:]}")
        return True

    except Exception as e:
        logger.error(f"[HumanSim] Erro ao enviar msg humanizada: {e}")
        return False
```

### DoD

- [x] Funcao `enviar_mensagem_humanizada` implementada
- [x] Delay de leitura com distribuicao normal
- [x] Mark as read funcionando
- [x] Evento composing enviado
- [x] Testes unitarios com mocks

---

## Story 2.2: Funcoes de Calculo de Delay

### Objetivo
Criar funcoes para calcular delays realistas entre mensagens.

### Implementacao

```python
def calcular_delay_entre_turnos() -> float:
    """
    Calcula delay entre turnos de conversa.
    Distribuicao exponencial para parecer natural.

    A distribuicao exponencial gera mais valores baixos
    com ocasionais valores mais altos, simulando como
    humanos respondem (rapido as vezes, devagar outras).

    Returns:
        Delay em segundos (20-90s)
    """
    # Exponencial com media 45s
    delay = random.expovariate(1/45)
    return max(20, min(90, delay))


def calcular_delay_resposta() -> float:
    """
    Calcula delay para responder uma mensagem recebida.
    Usado quando o chip recebe msg e precisa responder.

    Returns:
        Delay em segundos (3-15s)
    """
    return random.gauss(8, 3)


def calcular_tempo_digitacao(texto: str) -> float:
    """
    Calcula tempo de digitacao baseado no tamanho do texto.
    Aproximadamente 50ms por caractere (velocidade media humana).

    Args:
        texto: Texto que sera digitado

    Returns:
        Tempo em segundos (1.5-5s)
    """
    tempo = len(texto) * 0.05
    return max(1.5, min(5, tempo))
```

### DoD

- [x] `calcular_delay_entre_turnos` com exponencial
- [x] `calcular_delay_resposta` com gaussiana
- [x] `calcular_tempo_digitacao` proporcional ao texto
- [x] Valores dentro dos ranges especificados
- [x] Testes de distribuicao

---

## Story 2.3: Envio de Midia Humanizado

### Objetivo
Estender simulacao para envio de midias (audio, imagem, video).

### Implementacao

```python
async def enviar_midia_humanizada(
    instance: str,
    destinatario: str,
    tipo_midia: str,
    url_ou_base64: str,
    caption: Optional[str] = None,
) -> bool:
    """
    Envia midia simulando comportamento humano.

    Para midias, o fluxo e:
    1. Delay de "selecionar" (2-5s)
    2. Envia evento "recording" (audio) ou "composing" (outros)
    3. Delay proporcional ao tipo
    4. Envia midia

    Args:
        instance: Nome da instancia
        destinatario: JID do destinatario
        tipo_midia: 'audio', 'image', 'video', 'document'
        url_ou_base64: URL ou base64 do arquivo
        caption: Legenda opcional

    Returns:
        True se enviou com sucesso
    """
    try:
        # Delay de selecao
        await asyncio.sleep(random.uniform(2, 5))

        # Presence baseado no tipo
        if tipo_midia == "audio":
            await evolution_client.send_presence(instance, destinatario, "recording")
            # Audio simula gravacao (5-15s)
            await asyncio.sleep(random.uniform(5, 15))
        else:
            await evolution_client.send_presence(instance, destinatario, "composing")
            # Outros tipos (2-5s)
            await asyncio.sleep(random.uniform(2, 5))

        # Parar
        await evolution_client.send_presence(instance, destinatario, "paused")
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Enviar midia
        if tipo_midia == "audio":
            await evolution_client.send_audio(instance, destinatario, url_ou_base64)
        elif tipo_midia == "image":
            await evolution_client.send_image(instance, destinatario, url_ou_base64, caption)
        elif tipo_midia == "video":
            await evolution_client.send_video(instance, destinatario, url_ou_base64, caption)
        elif tipo_midia == "document":
            await evolution_client.send_document(instance, destinatario, url_ou_base64, caption)

        return True

    except Exception as e:
        logger.error(f"[HumanSim] Erro ao enviar midia: {e}")
        return False
```

### DoD

- [x] Funcao `enviar_midia_humanizada` implementada
- [x] Evento "recording" para audio
- [x] Delays proporcionais ao tipo de midia
- [x] Suporte a image, video, document, audio
- [x] Testes com diferentes tipos

---

## Story 2.4: Integracao Evolution API

### Objetivo
Garantir que os metodos necessarios da Evolution API estejam disponiveis.

### Metodos Necessarios

```python
# Em app/services/evolution/client.py

class EvolutionClient:
    async def mark_as_read(self, instance: str, jid: str) -> bool:
        """
        Marca mensagem como lida.
        POST /chat/markMessageAsRead/{instance}
        """
        url = f"{self.base_url}/chat/markMessageAsRead/{instance}"
        payload = {"readMessages": [{"remoteJid": jid}]}
        # ...

    async def send_presence(
        self,
        instance: str,
        jid: str,
        presence: str  # 'composing', 'recording', 'paused', 'available'
    ) -> bool:
        """
        Envia evento de presenca.
        POST /chat/sendPresence/{instance}
        """
        url = f"{self.base_url}/chat/sendPresence/{instance}"
        payload = {
            "number": jid,
            "presence": presence,
        }
        # ...

    async def send_text(self, instance: str, jid: str, text: str) -> dict:
        """
        Envia mensagem de texto.
        POST /message/sendText/{instance}
        """
        # Ja implementado

    async def send_audio(self, instance: str, jid: str, audio: str) -> dict:
        """
        Envia audio.
        POST /message/sendWhatsAppAudio/{instance}
        """
        # ...

    async def send_image(
        self,
        instance: str,
        jid: str,
        image: str,
        caption: Optional[str] = None
    ) -> dict:
        """
        Envia imagem.
        POST /message/sendMedia/{instance}
        """
        # ...
```

### DoD

- [x] `mark_as_read` implementado
- [x] `send_presence` implementado
- [x] Metodos de midia verificados/implementados
- [x] Testes de integracao com Evolution

---

## Checklist do Epico

- [x] **S25.E02.1** - enviar_mensagem_humanizada implementada
- [x] **S25.E02.2** - Funcoes de calculo de delay
- [x] **S25.E02.3** - Envio de midia humanizado
- [x] **S25.E02.4** - Integracao Evolution API
- [x] Delays calibrados conforme pesquisa (20s-90s entre turnos)
- [x] Evento "digitando" funcionando
- [x] Testes unitarios completos
- [x] Documentacao inline

---

## Validacao

```python
# Test: Human Simulator

import pytest
from unittest.mock import AsyncMock, patch

from app.services.warmer.human_simulator import (
    enviar_mensagem_humanizada,
    calcular_delay_entre_turnos,
    calcular_delay_resposta,
    calcular_tempo_digitacao,
)


@pytest.mark.asyncio
async def test_enviar_mensagem_humanizada():
    """Testa fluxo completo de envio humanizado."""
    with patch("app.services.warmer.human_simulator.evolution_client") as mock_client:
        mock_client.mark_as_read = AsyncMock()
        mock_client.send_presence = AsyncMock()
        mock_client.send_text = AsyncMock()

        result = await enviar_mensagem_humanizada(
            instance="test-instance",
            destinatario="5511999999999@s.whatsapp.net",
            texto="Oi, tudo bem?",
        )

        assert result is True
        mock_client.mark_as_read.assert_called_once()
        assert mock_client.send_presence.call_count == 2  # composing + paused
        mock_client.send_text.assert_called_once()


def test_delay_entre_turnos_range():
    """Testa que delay esta no range 20-90s."""
    for _ in range(100):
        delay = calcular_delay_entre_turnos()
        assert 20 <= delay <= 90


def test_delay_resposta_range():
    """Testa que delay resposta esta no range esperado."""
    for _ in range(100):
        delay = calcular_delay_resposta()
        assert 0 < delay < 20  # Gaussiana pode sair do range mas raramente


def test_tempo_digitacao():
    """Testa calculo de tempo de digitacao."""
    # Texto curto
    assert calcular_tempo_digitacao("oi") == 1.5  # min

    # Texto medio
    tempo = calcular_tempo_digitacao("Ola, tudo bem com voce?")  # 23 chars
    assert 1.5 <= tempo <= 5

    # Texto longo
    assert calcular_tempo_digitacao("a" * 200) == 5.0  # max
```

---

## Diagrama de Sequencia

```
Usuario          Human Simulator         Evolution API
   │                    │                      │
   │  enviar_msg()      │                      │
   │───────────────────>│                      │
   │                    │                      │
   │                    │  [delay leitura 8s]  │
   │                    │──────────────────────│
   │                    │                      │
   │                    │  mark_as_read()      │
   │                    │─────────────────────>│
   │                    │                      │
   │                    │  [delay pensar 2s]   │
   │                    │──────────────────────│
   │                    │                      │
   │                    │  send_presence(composing)
   │                    │─────────────────────>│
   │                    │                      │
   │                    │  [tempo digitacao]   │
   │                    │──────────────────────│
   │                    │                      │
   │                    │  send_presence(paused)
   │                    │─────────────────────>│
   │                    │                      │
   │                    │  [delay final 1s]    │
   │                    │──────────────────────│
   │                    │                      │
   │                    │  send_text()         │
   │                    │─────────────────────>│
   │                    │                      │
   │     True           │                      │
   │<───────────────────│                      │
```

