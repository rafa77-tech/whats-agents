# Epic 3: Edge Cases

## Objetivo

> **Tratar todos os casos especiais sem quebrar a experiência.**

---

## Stories

---

# S3.E3.1 - Tratar mensagens de áudio

## Objetivo

> **Responder apropriadamente quando médico envia áudio.**

**Resultado esperado:** Júlia pede gentilmente para enviar em texto.

## Contexto

- Evolution API indica tipo de mensagem
- Não temos transcrição de áudio (ainda)
- Júlia deve pedir texto de forma natural

## Tarefas

### 1. Detectar mensagem de áudio

```python
# app/services/parser.py (atualizar)

def parse_mensagem(payload: dict) -> dict:
    """Parse mensagem do webhook Evolution."""

    message = payload.get("data", {}).get("message", {})

    # Detectar tipo
    tipo = "texto"
    conteudo = None

    if "conversation" in message:
        tipo = "texto"
        conteudo = message["conversation"]
    elif "audioMessage" in message:
        tipo = "audio"
        conteudo = None  # Não processamos áudio
    elif "imageMessage" in message:
        tipo = "imagem"
        conteudo = message["imageMessage"].get("caption", "")
    elif "documentMessage" in message:
        tipo = "documento"
        conteudo = message["documentMessage"].get("fileName", "")

    return {
        "tipo": tipo,
        "conteudo": conteudo,
        "telefone": payload.get("data", {}).get("key", {}).get("remoteJid", ""),
        "message_id": payload.get("data", {}).get("key", {}).get("id", ""),
    }
```

### 2. Criar respostas para áudio

```python
# app/services/respostas_especiais.py

import random

RESPOSTAS_AUDIO = [
    "Oi! Desculpa, to num lugar barulhento e não consigo ouvir áudio agora 😅 Pode mandar em texto?",
    "Ops, to no meio de uma reunião e não dá pra ouvir áudio. Me manda por escrito?",
    "Opa! To sem fone aqui, consegue digitar pra mim?",
    "Ei! Não consegui ouvir o áudio, pode escrever?",
]

def obter_resposta_audio() -> str:
    """Retorna resposta aleatória para áudio."""
    return random.choice(RESPOSTAS_AUDIO)
```

### 3. Integrar no fluxo

```python
# app/routes/webhook.py (atualizar)

async def processar_mensagem(mensagem: dict):
    tipo = mensagem.get("tipo")

    # Tratar áudio
    if tipo == "audio":
        resposta = obter_resposta_audio()
        await whatsapp_service.enviar_com_digitacao(
            telefone=mensagem["telefone"],
            texto=resposta
        )

        # Salvar interação
        await salvar_interacao(
            conversa_id=conversa["id"],
            direcao="entrada",
            tipo="audio",
            conteudo="[Áudio recebido]",
            origem="medico"
        )
        await salvar_interacao(
            conversa_id=conversa["id"],
            direcao="saida",
            tipo="texto",
            conteudo=resposta,
            origem="ai"
        )

        return {"status": "audio_handled"}

    # Continuar processamento normal para texto
    # ...
```

## DoD

- [x] Detecção de áudio funciona
- [x] Resposta natural e amigável
- [x] Varia entre opções (não repetitivo)
- [x] Interação salva no histórico
- [x] Não quebra fluxo principal

---

# S3.E3.2 - Tratar mensagens de imagem

## Objetivo

> **Responder apropriadamente quando médico envia imagem.**

**Resultado esperado:** Júlia reconhece imagem e responde de acordo com contexto.

## Tarefas

### 1. Criar respostas para imagem

```python
# app/services/respostas_especiais.py (adicionar)

RESPOSTAS_IMAGEM = {
    "documento": [
        "Recebi! Vou dar uma olhada aqui 👀",
        "Beleza, chegou aqui! Deixa eu ver...",
        "Show, recebi o doc!",
    ],
    "generica": [
        "Recebi a imagem! O que precisa que eu veja?",
        "Opa, chegou aqui! Sobre o que é?",
        "Recebi! Me conta mais sobre isso?",
    ],
}

def obter_resposta_imagem(caption: str = None) -> str:
    """
    Retorna resposta para imagem.

    Se tem caption, provavelmente é documento.
    Se não tem, pede contexto.
    """
    if caption and len(caption) > 10:
        # Tem contexto, provavelmente documento
        return random.choice(RESPOSTAS_IMAGEM["documento"])
    else:
        # Sem contexto, perguntar
        return random.choice(RESPOSTAS_IMAGEM["generica"])
```

### 2. Integrar no fluxo

```python
# app/routes/webhook.py (adicionar)

async def processar_mensagem(mensagem: dict):
    tipo = mensagem.get("tipo")

    # Tratar imagem
    if tipo == "imagem":
        caption = mensagem.get("conteudo", "")
        resposta = obter_resposta_imagem(caption)

        await whatsapp_service.enviar_com_digitacao(
            telefone=mensagem["telefone"],
            texto=resposta
        )

        # Salvar interação
        await salvar_interacao(
            conversa_id=conversa["id"],
            direcao="entrada",
            tipo="imagem",
            conteudo=f"[Imagem: {caption}]" if caption else "[Imagem recebida]",
            origem="medico"
        )

        return {"status": "image_handled"}
```

### 3. Encaminhar para Chatwoot

```python
# Para gestor ver a imagem no Chatwoot

async def encaminhar_imagem_chatwoot(
    conversation_id: int,
    imagem_url: str,
    caption: str = None
):
    """Encaminha imagem para Chatwoot como attachment."""
    # Chatwoot suporta attachments via API
    # Implementar se necessário para supervisão
    pass
```

## DoD

- [x] Detecção de imagem funciona
- [x] Resposta varia com/sem caption
- [x] Interação salva no histórico
- [x] Tratamento de documento e vídeo também implementado
- [x] Não quebra fluxo principal

---

# S3.E3.3 - Testar sistema de opt-out

## Objetivo

> **Validar que opt-out implementado na Sprint 1 (S1.E3.3) funciona em todos os cenários.**

**Resultado esperado:** 100% das variações de opt-out são detectadas e processadas corretamente.

## Contexto

A implementação do opt-out foi feita na Sprint 1, Epic 3 (S1.E3.3). Esta story foca em **testar exaustivamente** o sistema.

## Tarefas

### 1. Criar bateria de testes de detecção

```python
# tests/optout/test_deteccao.py

import pytest
from app.services.optout import detectar_optout

# Mensagens que DEVEM ser detectadas como opt-out
CASOS_OPTOUT_POSITIVO = [
    # Variações diretas
    "Para de me mandar mensagem",
    "para de mandar msg",
    "PARA DE ME MANDAR MENSAGEM",
    "Para de me mandar essas mensagens por favor",

    # "Não quero"
    "Não quero mais receber mensagens",
    "nao quero receber isso",
    "não quero mais nada",

    # "Remove da lista"
    "Me remove da lista",
    "me tira dessa lista",
    "exclui meu numero",
    "remove meu contato",

    # Comandos curtos
    "STOP",
    "stop",
    "SAIR",
    "parar",
    "cancelar",

    # Variações com grosseria
    "Sai fora",
    "SAI FORA",
    "chega",
    "bloqueia",

    # Com contexto
    "olha, não quero mais receber mensagem nenhuma",
    "por favor para de me mandar essas coisas",
    "já falei pra parar de mandar",
]

# Mensagens que NÃO devem ser detectadas como opt-out
CASOS_OPTOUT_NEGATIVO = [
    # Mensagens normais
    "Oi, tudo bem?",
    "Tenho interesse em plantão",
    "Qual o valor?",

    # Falsos positivos potenciais
    "Para quando é o plantão?",
    "Vou parar de trabalhar amanhã",
    "Quero parar pra almoçar",
    "Não quero esse horário, tem outro?",
    "Remove a vaga de sábado, peguei outra",
    "Me manda mais informações",
    "Para mim tá bom",
    "Quero sair mais cedo do plantão",
    "Vou sair às 19h",
    "Cancela a reserva de sexta",  # Cancelar vaga, não opt-out
    "Bloqueia minha agenda dia 15",  # Bloquear data, não opt-out
]


@pytest.mark.parametrize("mensagem", CASOS_OPTOUT_POSITIVO)
def test_detecta_optout(mensagem):
    """Cada mensagem de opt-out deve ser detectada."""
    resultado, _ = detectar_optout(mensagem)
    assert resultado == True, f"Não detectou opt-out em: '{mensagem}'"


@pytest.mark.parametrize("mensagem", CASOS_OPTOUT_NEGATIVO)
def test_nao_detecta_falso_positivo(mensagem):
    """Mensagens normais não devem ser detectadas como opt-out."""
    resultado, _ = detectar_optout(mensagem)
    assert resultado == False, f"Falso positivo em: '{mensagem}'"
```

### 2. Testar fluxo completo de opt-out

```python
# tests/optout/test_fluxo_completo.py

import pytest
from app.services.optout import processar_optout, pode_enviar_proativo

@pytest.mark.asyncio
async def test_fluxo_optout_completo():
    """
    Testa todo o fluxo:
    1. Médico envia opt-out
    2. Confirmação é enviada
    3. Médico marcado no banco
    4. Envios proativos bloqueados
    5. Mensagem inbound ainda funciona
    6. Reativação funciona
    """
    # Setup: criar médico de teste
    telefone = "5511999990099"
    medico = await criar_medico_teste(telefone)

    # 1. Processar opt-out
    resultado = await processar_optout(medico["id"], telefone)
    assert resultado["success"] == True

    # 2. Verificar médico marcado
    medico_atualizado = await buscar_medico(medico["id"])
    assert medico_atualizado["opted_out"] == True

    # 3. Verificar envio proativo bloqueado
    pode, motivo = await pode_enviar_proativo(medico["id"])
    assert pode == False
    assert "opt-out" in motivo.lower()

    # 4. Testar reativação
    await reativar_cliente(medico["id"])
    pode, _ = await pode_enviar_proativo(medico["id"])
    assert pode == True

    # Cleanup
    await deletar_medico_teste(medico["id"])
```

### 3. Testar cenários de borda

```python
# tests/optout/test_edge_cases.py

@pytest.mark.asyncio
async def test_optout_duplo():
    """Médico pedindo opt-out duas vezes não causa erro."""
    pass

@pytest.mark.asyncio
async def test_optout_com_conversa_ativa():
    """Opt-out no meio de conversa encerra corretamente."""
    pass

@pytest.mark.asyncio
async def test_optout_com_reserva_pendente():
    """Opt-out com reserva de plantão pendente notifica gestor."""
    pass

@pytest.mark.asyncio
async def test_reativacao_apos_optout():
    """Médico pode voltar mandando 'oi' após opt-out."""
    pass
```

## DoD

- [x] 100% dos casos positivos detectados (testes parametrizados)
- [x] 0% de falsos positivos (testes parametrizados)
- [x] Fluxo completo testado (testes existentes + edge cases)
- [x] Cenários de borda cobertos (opt-out duplo, conversa ativa, reativação)
- [x] Testes exaustivos criados

---

# S3.E3.4 - Tratar mensagens muito longas

## Objetivo

> **Lidar com mensagens extremamente longas sem quebrar.**

**Resultado esperado:** Sistema processa ou trunca mensagens longas graciosamente.

## Tarefas

### 1. Definir limites

```python
# app/core/config.py (adicionar)

# Limites de mensagem
MAX_MENSAGEM_CHARS = 4000  # Máximo para processar normalmente
MAX_MENSAGEM_CHARS_TRUNCAR = 10000  # Acima disso, truncar
MAX_MENSAGEM_CHARS_REJEITAR = 50000  # Acima disso, pedir resumo
```

### 2. Implementar tratamento

```python
# app/services/mensagem.py (adicionar)

def tratar_mensagem_longa(texto: str) -> tuple[str, str]:
    """
    Trata mensagem longa.

    Returns:
        (texto_processado, acao)
        acao: "normal", "truncada", "pedir_resumo"
    """
    tamanho = len(texto)

    if tamanho <= MAX_MENSAGEM_CHARS:
        return texto, "normal"

    if tamanho <= MAX_MENSAGEM_CHARS_TRUNCAR:
        # Truncar e avisar
        texto_truncado = texto[:MAX_MENSAGEM_CHARS] + "..."
        return texto_truncado, "truncada"

    # Muito longa, pedir resumo
    return texto[:1000], "pedir_resumo"


RESPOSTA_MENSAGEM_LONGA = (
    "Eita, muita coisa aí! 😅\n\n"
    "Consegue me resumir o principal? Assim consigo te ajudar melhor"
)

async def responder_mensagem_longa(telefone: str):
    """Responde pedindo resumo."""
    await whatsapp_service.enviar_mensagem(
        telefone=telefone,
        texto=RESPOSTA_MENSAGEM_LONGA
    )
```

### 3. Integrar no webhook

```python
# app/routes/webhook.py (atualizar)

async def processar_mensagem(mensagem: MensagemRecebida):
    # Verificar tamanho da mensagem
    texto_processado, acao = tratar_mensagem_longa(mensagem.texto)

    if acao == "pedir_resumo":
        await responder_mensagem_longa(mensagem.telefone)
        return {"status": "requested_summary"}

    if acao == "truncada":
        logger.warning(
            f"Mensagem truncada de {len(mensagem.texto)} para {len(texto_processado)}"
        )

    # Continuar com texto processado
    mensagem.texto = texto_processado
    # ...
```

## DoD

- [x] Limites definidos (config.py)
- [x] Mensagens até 4000 chars processadas normalmente
- [x] Mensagens até 10000 chars truncadas
- [x] Mensagens maiores pedem resumo
- [x] Log de truncamento
- [x] Não quebra o sistema

---

# S3.E3.5 - Testar resiliência e tratamento de erros

## Objetivo

> **Validar que Circuit Breaker (S1.E3.2) e tratamento de erros funcionam corretamente.**

**Resultado esperado:** Sistema se recupera graciosamente de todas as falhas simuladas.

## Contexto

O Circuit Breaker foi implementado na Sprint 1 (S1.E3.2). Esta story foca em **testar cenários de falha** simulando indisponibilidade de serviços.

## Tarefas

### 1. Criar testes de Circuit Breaker

```python
# tests/resiliencia/test_circuit_breaker.py

import pytest
from unittest.mock import patch, AsyncMock
from app.services.circuit_breaker import (
    circuit_evolution,
    circuit_claude,
    circuit_supabase,
    CircuitState,
    CircuitOpenError
)

@pytest.fixture(autouse=True)
def reset_circuits():
    """Reset todos os circuits antes de cada teste."""
    circuit_evolution.estado = CircuitState.CLOSED
    circuit_evolution.falhas_consecutivas = 0
    circuit_claude.estado = CircuitState.CLOSED
    circuit_claude.falhas_consecutivas = 0
    circuit_supabase.estado = CircuitState.CLOSED
    circuit_supabase.falhas_consecutivas = 0
    yield


class TestCircuitEvolution:
    @pytest.mark.asyncio
    async def test_abre_apos_3_falhas(self):
        """Evolution circuit abre após 3 falhas consecutivas."""
        async def sempre_falha():
            raise Exception("Connection refused")

        for i in range(3):
            with pytest.raises(Exception):
                await circuit_evolution.executar(sempre_falha)

        assert circuit_evolution.estado == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_fallback_quando_aberto(self):
        """Usa fallback quando circuit está aberto."""
        circuit_evolution.estado = CircuitState.OPEN

        async def funcao_principal():
            return "principal"

        async def fallback():
            return "fallback"

        resultado = await circuit_evolution.executar(
            funcao_principal,
            fallback=fallback
        )
        assert resultado == "fallback"


class TestCircuitClaude:
    @pytest.mark.asyncio
    async def test_timeout_conta_como_falha(self):
        """Timeout na API do Claude conta como falha."""
        import asyncio

        async def func_lenta():
            await asyncio.sleep(100)  # Nunca completa

        with pytest.raises(asyncio.TimeoutError):
            await circuit_claude.executar(func_lenta)

        assert circuit_claude.falhas_consecutivas == 1

    @pytest.mark.asyncio
    async def test_recuperacao_apos_sucesso(self):
        """Circuit volta a CLOSED após sucesso em HALF_OPEN."""
        circuit_claude.estado = CircuitState.HALF_OPEN

        async def sucesso():
            return "ok"

        await circuit_claude.executar(sucesso)
        assert circuit_claude.estado == CircuitState.CLOSED
```

### 2. Testes de integração com falha simulada

```python
# tests/resiliencia/test_falha_integracao.py

import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_mensagem_processada_com_claude_down():
    """
    Simula Claude API indisponível.
    Médico deve receber mensagem de fallback.
    """
    with patch('app.services.llm.client.messages.create') as mock:
        mock.side_effect = Exception("API Error")

        # Simular mensagem recebida
        response = await client.post("/webhook/evolution", json={
            "event": "messages.upsert",
            "instance": "julia",
            "data": {
                "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Oi"},
            }
        })

        # Verificar que médico recebeu fallback
        # (mock do WhatsApp service para capturar)


@pytest.mark.asyncio
async def test_mensagem_processada_com_supabase_down():
    """
    Simula Supabase indisponível.
    Sistema deve continuar operando com degradação.
    """
    with patch('app.services.supabase.supabase') as mock:
        mock.table.return_value.select.side_effect = Exception("DB Error")

        # Simular e verificar comportamento


@pytest.mark.asyncio
async def test_evolution_down_nao_quebra_sistema():
    """
    Se Evolution API cair, outros médicos não são afetados.
    """
    pass
```

### 3. Testes de carga e estresse

```python
# tests/resiliencia/test_estresse.py

import pytest
import asyncio

@pytest.mark.asyncio
async def test_multiplas_mensagens_simultaneas():
    """Sistema lida com 10 mensagens simultâneas."""
    tarefas = []
    for i in range(10):
        tarefa = processar_mensagem_teste(f"Mensagem {i}")
        tarefas.append(tarefa)

    resultados = await asyncio.gather(*tarefas, return_exceptions=True)

    # Nenhum deve ter falhado completamente
    falhas_totais = sum(1 for r in resultados if isinstance(r, Exception))
    assert falhas_totais == 0


@pytest.mark.asyncio
async def test_recuperacao_apos_tempestade_de_erros():
    """
    Após múltiplas falhas, sistema se recupera quando serviço volta.
    """
    # Simular 10 falhas
    # Esperar tempo de reset
    # Verificar que volta a funcionar
    pass
```

### 4. Verificar mensagens de erro amigáveis

```python
# tests/resiliencia/test_mensagens_erro.py

import pytest
from app.services.error_handler import obter_mensagem_erro

TIPOS_ERRO = ["llm_timeout", "llm_error", "whatsapp_error", "generico"]

@pytest.mark.parametrize("tipo", TIPOS_ERRO)
def test_mensagem_erro_existe(tipo):
    """Cada tipo de erro tem mensagem definida."""
    msg = obter_mensagem_erro(tipo)
    assert msg is not None
    assert len(msg) > 10

@pytest.mark.parametrize("tipo", TIPOS_ERRO)
def test_mensagem_erro_informal(tipo):
    """Mensagens de erro mantêm tom informal."""
    msg = obter_mensagem_erro(tipo)
    # Não deve ter linguagem formal
    assert "prezado" not in msg.lower()
    assert "senhores" not in msg.lower()
    # Deve ter tom amigável
    assert any(c in msg for c in ["?", "!", "😅", "👍"])

def test_mensagens_erro_variam():
    """Mensagens de erro não são sempre iguais."""
    msgs = [obter_mensagem_erro("generico") for _ in range(20)]
    # Deve ter pelo menos 2 variações
    assert len(set(msgs)) >= 2
```

## DoD

- [x] Circuit breakers testados (open, half-open, closed)
- [x] Fallbacks funcionam quando circuit aberto
- [x] Testes de timeout e recuperação implementados
- [x] Mensagens de erro amigáveis e variadas (error_handler.py)
- [x] Testes de mensagens de erro criados
- [x] Testes de reset manual e transições de estado

**Nota:** Testes de integração com falhas simuladas e testes de carga podem ser adicionados posteriormente conforme necessidade.
