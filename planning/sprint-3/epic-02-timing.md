# Epic 2: Humanização de Timing

## Objetivo

> **Fazer Júlia parecer humana no tempo de resposta e comportamento.**

---

## Stories

---

# S3.E2.1 - Implementar delay variável

## Objetivo

> **Criar sistema de delay que simula tempo de leitura e resposta humana.**

**Resultado esperado:** Respostas não são instantâneas, tempo varia naturalmente.

## Contexto

Humanos:
- Levam tempo para ler a mensagem
- Pensam antes de responder
- Variam o tempo dependendo da complexidade
- Às vezes respondem rápido, às vezes demoram

## Tarefas

### 1. Criar calculador de delay

```python
# app/services/timing.py

import random
from datetime import datetime, time

def calcular_delay_resposta(
    mensagem: str,
    hora_atual: datetime = None
) -> float:
    """
    Calcula delay apropriado para resposta.

    Fatores:
    - Tamanho da mensagem (mais texto = mais tempo lendo)
    - Complexidade (pergunta vs afirmação)
    - Hora do dia (mais lento no início/fim do dia)
    - Variação aleatória (parecer humano)

    Returns:
        Delay em segundos (20-90s tipicamente)
    """
    hora_atual = hora_atual or datetime.now()
    base_delay = 20  # Mínimo 20 segundos

    # Fator: tamanho da mensagem
    palavras = len(mensagem.split())
    tempo_leitura = palavras * 0.3  # ~0.3s por palavra

    # Fator: complexidade
    eh_pergunta = '?' in mensagem
    tem_numeros = any(c.isdigit() for c in mensagem)
    complexidade = 0
    if eh_pergunta:
        complexidade += 5
    if tem_numeros:
        complexidade += 3
    if len(mensagem) > 200:
        complexidade += 5

    # Fator: hora do dia
    hora = hora_atual.hour
    fator_hora = 1.0
    if hora < 9:  # Início do dia - mais lenta
        fator_hora = 1.3
    elif hora > 18:  # Fim do dia - mais lenta
        fator_hora = 1.2
    elif 12 <= hora <= 14:  # Horário de almoço
        fator_hora = 1.4

    # Calcular delay base
    delay = base_delay + tempo_leitura + complexidade

    # Aplicar fator de hora
    delay *= fator_hora

    # Adicionar variação aleatória (±30%)
    variacao = random.uniform(0.7, 1.3)
    delay *= variacao

    # Limitar entre 20s e 120s
    return max(20, min(120, delay))
```

### 2. Integrar no fluxo de resposta

```python
# app/services/agente.py (atualizar)

import asyncio
from app.services.timing import calcular_delay_resposta

async def processar_e_responder(
    conversa: dict,
    mensagem: str,
    contexto: dict
) -> str:
    """Processa mensagem com delay humanizado."""

    # Calcular delay ANTES de processar
    delay = calcular_delay_resposta(mensagem)

    # Marcar como lida imediatamente
    await whatsapp_service.marcar_como_lida(mensagem_id)

    # Mostrar online
    await whatsapp_service.enviar_presenca("available")

    # Processar em paralelo com parte do delay
    tempo_inicio = time.time()

    # Gerar resposta (enquanto "lê" a mensagem)
    resposta = await gerar_resposta(mensagem, contexto)

    # Calcular tempo restante de delay
    tempo_processamento = time.time() - tempo_inicio
    delay_restante = max(0, delay - tempo_processamento)

    # Aguardar delay restante (simulando "pensar")
    if delay_restante > 5:
        # Mostrar "digitando" antes de enviar
        await asyncio.sleep(delay_restante - 5)
        await whatsapp_service.enviar_presenca("composing")
        await asyncio.sleep(5)
    else:
        await asyncio.sleep(delay_restante)

    # Enviar resposta
    await whatsapp_service.enviar_mensagem(
        telefone=contexto["medico"]["telefone"],
        texto=resposta
    )

    return resposta
```

### 3. Adicionar logging de timing

```python
# app/services/timing.py (adicionar)

import logging

logger = logging.getLogger(__name__)

def log_timing(mensagem: str, delay: float, tempo_real: float):
    """Loga métricas de timing para análise."""
    logger.info(
        "Timing de resposta",
        extra={
            "delay_calculado": delay,
            "tempo_real": tempo_real,
            "tamanho_mensagem": len(mensagem),
            "palavras": len(mensagem.split())
        }
    )
```

## DoD

- [ ] Calculador de delay implementado
- [ ] Delay varia entre 20-120 segundos
- [ ] Fatores de complexidade funcionam
- [ ] Fator de hora do dia funciona
- [ ] Variação aleatória implementada
- [ ] Integrado no fluxo de resposta

---

# S3.E2.2 - Simular tempo de digitação

## Objetivo

> **Mostrar "digitando" por tempo proporcional ao tamanho da resposta.**

**Resultado esperado:** Médico vê "digitando" por tempo realista antes da mensagem.

## Tarefas

### 1. Calcular tempo de digitação

```python
# app/services/timing.py (adicionar)

def calcular_tempo_digitacao(texto: str) -> float:
    """
    Calcula tempo realista de digitação.

    Humano médio digita ~40 palavras/minuto no celular.
    Com correções e pensamento: ~30 palavras/minuto.

    Returns:
        Tempo em segundos
    """
    palavras = len(texto.split())
    caracteres = len(texto)

    # Base: 30 palavras por minuto = 2 segundos por palavra
    tempo_base = palavras * 2

    # Ajuste para emojis (mais rápido)
    emojis = sum(1 for c in texto if ord(c) > 127000)
    tempo_base -= emojis * 1  # Emoji é rápido

    # Ajuste para abreviações (mais rápido)
    abreviacoes = texto.count("vc") + texto.count("pra") + texto.count("tá")
    tempo_base -= abreviacoes * 0.5

    # Mínimo 3s, máximo 15s por mensagem
    return max(3, min(15, tempo_base))
```

### 2. Implementar digitação realista

```python
# app/services/whatsapp.py (atualizar)

async def enviar_com_digitacao(
    self,
    telefone: str,
    texto: str,
    tempo_digitacao: float = None
) -> dict:
    """
    Envia mensagem com simulação de digitação.

    1. Mostra "composing" (digitando)
    2. Aguarda tempo proporcional
    3. Envia mensagem
    """
    tempo = tempo_digitacao or calcular_tempo_digitacao(texto)

    # Iniciar "digitando"
    await self.enviar_presenca("composing", telefone)

    # Aguardar tempo de digitação
    await asyncio.sleep(tempo)

    # Enviar mensagem
    return await self.enviar_mensagem(telefone, texto)
```

### 3. Atualizar fluxo principal

```python
# app/services/agente.py (atualizar)

async def enviar_resposta(
    telefone: str,
    resposta: str
) -> dict:
    """Envia resposta com timing humanizado."""

    tempo_digitacao = calcular_tempo_digitacao(resposta)

    return await whatsapp_service.enviar_com_digitacao(
        telefone=telefone,
        texto=resposta,
        tempo_digitacao=tempo_digitacao
    )
```

## DoD

- [ ] Calculador de tempo de digitação funciona
- [ ] "Digitando" mostrado antes de cada mensagem
- [ ] Tempo proporcional ao tamanho
- [ ] Mínimo 3s, máximo 15s por mensagem
- [ ] Integrado no fluxo de envio

---

# S3.E2.3 - Quebrar mensagens longas

## Objetivo

> **Dividir respostas longas em várias mensagens curtas.**

**Resultado esperado:** Mensagens longas viram sequência de mensagens curtas naturais.

## Contexto

Humanos no WhatsApp:
- Raramente escrevem mensagens longas
- Quebram pensamento em várias mensagens
- Enviam uma atrás da outra rapidamente
- Às vezes pausam entre mensagens

## Tarefas

### 1. Criar quebrador de mensagens

```python
# app/services/mensagem.py

import re

def quebrar_mensagem(texto: str, max_chars: int = 150) -> list[str]:
    """
    Quebra mensagem longa em várias curtas.

    Regras:
    - Máximo 150 caracteres por mensagem
    - Quebra em pontos naturais (., !, ?)
    - Mantém emojis com o texto anterior
    - Não quebra no meio de palavras

    Returns:
        Lista de mensagens curtas
    """
    if len(texto) <= max_chars:
        return [texto]

    mensagens = []
    resto = texto

    while resto:
        if len(resto) <= max_chars:
            mensagens.append(resto.strip())
            break

        # Encontrar ponto de quebra
        # Prioridade: ponto final, exclamação, interrogação, vírgula
        ponto_quebra = -1

        for separador in ['. ', '! ', '? ', ', ', ' ']:
            # Procurar última ocorrência antes do limite
            idx = resto.rfind(separador, 0, max_chars)
            if idx > 0:
                ponto_quebra = idx + len(separador) - 1
                break

        if ponto_quebra == -1:
            # Forçar quebra no limite
            ponto_quebra = max_chars

        # Extrair mensagem
        msg = resto[:ponto_quebra].strip()
        resto = resto[ponto_quebra:].strip()

        if msg:
            mensagens.append(msg)

    return mensagens
```

### 2. Enviar sequência com delays

```python
# app/services/agente.py (adicionar)

import random

async def enviar_mensagens_sequencia(
    telefone: str,
    mensagens: list[str]
) -> list[dict]:
    """
    Envia sequência de mensagens com timing natural.

    Entre mensagens:
    - Delay curto (1-3s) para continuação
    - Delay médio (3-5s) para novo pensamento
    """
    resultados = []

    for i, msg in enumerate(mensagens):
        # Calcular delay entre mensagens
        if i > 0:
            # Se começa com minúscula, é continuação (delay curto)
            if msg[0].islower():
                delay = random.uniform(1, 3)
            else:
                delay = random.uniform(3, 5)

            await asyncio.sleep(delay)

        # Enviar com digitação
        resultado = await whatsapp_service.enviar_com_digitacao(
            telefone=telefone,
            texto=msg
        )
        resultados.append(resultado)

    return resultados
```

### 3. Integrar no fluxo

```python
# app/services/agente.py (atualizar)

async def processar_e_responder(
    conversa: dict,
    mensagem: str,
    contexto: dict
) -> str:
    # ... código existente ...

    # Quebrar resposta se necessário
    mensagens = quebrar_mensagem(resposta)

    if len(mensagens) == 1:
        await enviar_resposta(telefone, resposta)
    else:
        await enviar_mensagens_sequencia(telefone, mensagens)

    return resposta
```

## DoD

- [ ] Função de quebra implementada
- [ ] Máximo 150 caracteres por mensagem
- [ ] Quebra em pontos naturais
- [ ] Delay entre mensagens da sequência
- [ ] Delay varia (continuação vs novo pensamento)
- [ ] Integrado no fluxo de resposta

---

# S3.E2.4 - Respeitar horário comercial

## Objetivo

> **Júlia só responde em horário comercial (8h-20h, seg-sex).**

**Resultado esperado:** Mensagens fora do horário são processadas no próximo horário comercial.

## Tarefas

### 1. Criar verificador de horário

```python
# app/services/timing.py (adicionar)

from datetime import datetime, time, timedelta

HORARIO_INICIO = time(8, 0)   # 8h
HORARIO_FIM = time(20, 0)     # 20h
DIAS_UTEIS = [0, 1, 2, 3, 4]  # Segunda a sexta

def esta_em_horario_comercial(dt: datetime = None) -> bool:
    """
    Verifica se está em horário comercial.

    Horário: 8h-20h, segunda a sexta
    """
    dt = dt or datetime.now()

    # Verificar dia da semana
    if dt.weekday() not in DIAS_UTEIS:
        return False

    # Verificar hora
    hora_atual = dt.time()
    return HORARIO_INICIO <= hora_atual <= HORARIO_FIM


def proximo_horario_comercial(dt: datetime = None) -> datetime:
    """
    Retorna próximo horário comercial disponível.
    """
    dt = dt or datetime.now()

    while True:
        # Se é dia útil
        if dt.weekday() in DIAS_UTEIS:
            # Se antes do horário de início
            if dt.time() < HORARIO_INICIO:
                return dt.replace(
                    hour=HORARIO_INICIO.hour,
                    minute=HORARIO_INICIO.minute,
                    second=0
                )
            # Se dentro do horário
            elif dt.time() <= HORARIO_FIM:
                return dt
            # Se depois do horário (vai para próximo dia)

        # Avançar para próximo dia às 8h
        dt = (dt + timedelta(days=1)).replace(
            hour=HORARIO_INICIO.hour,
            minute=HORARIO_INICIO.minute,
            second=0
        )
```

### 2. Criar fila de mensagens pendentes

```python
# app/services/fila_mensagens.py

from datetime import datetime
from app.core.supabase import supabase
from app.services.timing import proximo_horario_comercial

async def agendar_resposta(
    conversa_id: str,
    mensagem: str,
    resposta: str,
    agendar_para: datetime
) -> dict:
    """
    Agenda resposta para envio posterior.
    """
    return (
        supabase.table("mensagens_agendadas")
        .insert({
            "conversa_id": conversa_id,
            "mensagem_original": mensagem,
            "resposta": resposta,
            "agendar_para": agendar_para.isoformat(),
            "status": "pendente"
        })
        .execute()
    ).data[0]


async def processar_mensagens_agendadas():
    """
    Job que processa mensagens agendadas.

    Executar via cron a cada minuto.
    """
    agora = datetime.now()

    # Buscar mensagens prontas para envio
    response = (
        supabase.table("mensagens_agendadas")
        .select("*, conversations(*, clientes(*))")
        .eq("status", "pendente")
        .lte("agendar_para", agora.isoformat())
        .execute()
    )

    for msg in response.data:
        try:
            conversa = msg["conversations"]
            telefone = conversa["clientes"]["telefone"]

            # Enviar resposta
            await whatsapp_service.enviar_com_digitacao(
                telefone=telefone,
                texto=msg["resposta"]
            )

            # Marcar como enviada
            supabase.table("mensagens_agendadas").update({
                "status": "enviada",
                "enviada_em": datetime.now().isoformat()
            }).eq("id", msg["id"]).execute()

        except Exception as e:
            logger.error(f"Erro ao enviar msg agendada: {e}")
```

### 3. Integrar verificação no webhook

```python
# app/routes/webhook.py (atualizar)

from app.services.timing import esta_em_horario_comercial, proximo_horario_comercial

async def processar_mensagem(mensagem: MensagemRecebida):
    # ... código existente ...

    # Verificar horário comercial
    if not esta_em_horario_comercial():
        # Gerar resposta mas agendar para depois
        resposta = await gerar_resposta(mensagem.texto, contexto)

        proximo_horario = proximo_horario_comercial()
        await agendar_resposta(
            conversa_id=conversa["id"],
            mensagem=mensagem.texto,
            resposta=resposta,
            agendar_para=proximo_horario
        )

        logger.info(
            f"Mensagem agendada para {proximo_horario}",
            extra={"conversa_id": conversa["id"]}
        )
        return {"status": "scheduled", "para": proximo_horario.isoformat()}

    # Processar normalmente
    # ...
```

### 4. Criar tabela de mensagens agendadas

```sql
-- migration: criar_tabela_mensagens_agendadas.sql

CREATE TABLE mensagens_agendadas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversa_id UUID REFERENCES conversations(id),
    mensagem_original TEXT,
    resposta TEXT,
    agendar_para TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente',
    enviada_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mensagens_agendadas_status
ON mensagens_agendadas(status, agendar_para);
```

## DoD

- [ ] Verificador de horário comercial funciona
- [ ] Horário: 8h-20h, segunda a sexta
- [ ] Mensagens fora do horário são agendadas
- [ ] Job processa mensagens agendadas
- [ ] Tabela de agendamento criada
- [ ] Logs indicam agendamento
