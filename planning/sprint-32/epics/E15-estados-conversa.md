# E15 - Estados de Conversa

**Sprint:** 32 - Redesign de Campanhas e Comportamento Julia
**Fase:** 4 - Arquitetura de Dados
**Dependências:** E08 (Canal de Ajuda)
**Estimativa:** 3h

---

## Objetivo

Implementar sistema de **estados de conversa** que permite Julia pausar conversas enquanto aguarda informações externas (gestor, sistema, etc.).

---

## Problema Atual

A tabela `conversations` tem apenas `controlled_by`:
- `julia` - Julia responde
- `human` - Humano assumiu (handoff)

Não há como representar estados intermediários como:
- Julia perguntou algo ao gestor e está aguardando
- Julia enviou mensagem e está esperando resposta do médico
- Conversa pausada temporariamente

---

## Solução

Adicionar campo `status` com estados mais granulares:

```
ESTADOS DA CONVERSA:

ATIVA
├── Julia responde normalmente
└── controlled_by = julia

AGUARDANDO_MEDICO
├── Julia enviou mensagem e espera resposta
├── controlled_by = julia (responderá quando médico responder)
└── Não envia follow-up automático por X minutos

AGUARDANDO_GESTOR
├── Julia pediu ajuda ao gestor
├── controlled_by = julia
├── Julia NÃO responde ao médico até gestor responder
└── Timeout de 5 min → responde "vou confirmar"

PAUSADA
├── Conversa temporariamente pausada (ex: fora de horário)
├── controlled_by = julia
└── Retoma automaticamente

HANDOFF
├── Transferida para humano
└── controlled_by = human
```

---

## Tasks

### T1: Criar migration para status (30min)

**Migration:** `adicionar_status_conversa`

```sql
-- Migration: adicionar_status_conversa
-- Adiciona estados granulares para conversas

-- 1. Criar tipo enum para status
CREATE TYPE status_conversa AS ENUM (
    'ativa',
    'aguardando_medico',
    'aguardando_gestor',
    'aguardando_info',
    'pausada',
    'handoff',
    'encerrada'
);

-- 2. Adicionar coluna status
ALTER TABLE conversations
ADD COLUMN status status_conversa NOT NULL DEFAULT 'ativa';

-- 3. Adicionar metadados do status
ALTER TABLE conversations
ADD COLUMN status_desde TIMESTAMPTZ,
ADD COLUMN status_motivo TEXT,
ADD COLUMN status_contexto JSONB;

-- 4. Índice para busca por status
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_status_desde ON conversations(status_desde);

-- 5. Comentários
COMMENT ON COLUMN conversations.status IS 'Estado atual da conversa';
COMMENT ON COLUMN conversations.status_desde IS 'Quando entrou neste status';
COMMENT ON COLUMN conversations.status_motivo IS 'Motivo da mudança de status';
COMMENT ON COLUMN conversations.status_contexto IS 'Dados extras (pedido_ajuda_id, etc.)';

-- 6. Migrar controlled_by existentes
UPDATE conversations
SET status = CASE
    WHEN controlled_by = 'human' THEN 'handoff'::status_conversa
    ELSE 'ativa'::status_conversa
END,
status_desde = updated_at
WHERE status IS NULL OR status = 'ativa';

-- 7. Trigger para atualizar status_desde
CREATE OR REPLACE FUNCTION update_status_desde()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        NEW.status_desde = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_status_desde
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_status_desde();
```

---

### T2: Criar enum e serviço de status (1h)

**Arquivo:** `app/services/conversas/status.py`

```python
"""
Gerenciamento de status de conversas.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from app.services.supabase import supabase
from app.core.logging import get_logger

logger = get_logger(__name__)


class StatusConversa(str, Enum):
    """Estados possíveis de uma conversa."""
    ATIVA = "ativa"
    AGUARDANDO_MEDICO = "aguardando_medico"
    AGUARDANDO_GESTOR = "aguardando_gestor"
    AGUARDANDO_INFO = "aguardando_info"
    PAUSADA = "pausada"
    HANDOFF = "handoff"
    ENCERRADA = "encerrada"


class TransicaoInvalida(Exception):
    """Transição de status não permitida."""
    pass


# Transições permitidas
TRANSICOES_PERMITIDAS = {
    StatusConversa.ATIVA: [
        StatusConversa.AGUARDANDO_MEDICO,
        StatusConversa.AGUARDANDO_GESTOR,
        StatusConversa.PAUSADA,
        StatusConversa.HANDOFF,
        StatusConversa.ENCERRADA,
    ],
    StatusConversa.AGUARDANDO_MEDICO: [
        StatusConversa.ATIVA,
        StatusConversa.AGUARDANDO_GESTOR,
        StatusConversa.HANDOFF,
        StatusConversa.ENCERRADA,
    ],
    StatusConversa.AGUARDANDO_GESTOR: [
        StatusConversa.ATIVA,
        StatusConversa.AGUARDANDO_INFO,
        StatusConversa.HANDOFF,
    ],
    StatusConversa.AGUARDANDO_INFO: [
        StatusConversa.ATIVA,
        StatusConversa.AGUARDANDO_GESTOR,
        StatusConversa.HANDOFF,
    ],
    StatusConversa.PAUSADA: [
        StatusConversa.ATIVA,
        StatusConversa.HANDOFF,
        StatusConversa.ENCERRADA,
    ],
    StatusConversa.HANDOFF: [
        StatusConversa.ATIVA,  # Humano devolve para Julia
    ],
    StatusConversa.ENCERRADA: [],  # Estado final
}


def pode_transicionar(de: StatusConversa, para: StatusConversa) -> bool:
    """
    Verifica se transição é permitida.

    Args:
        de: Status atual
        para: Status desejado

    Returns:
        True se transição é válida
    """
    permitidos = TRANSICOES_PERMITIDAS.get(de, [])
    return para in permitidos


async def atualizar_status(
    conversa_id: str,
    novo_status: StatusConversa,
    motivo: str | None = None,
    contexto: dict | None = None,
    forcar: bool = False
) -> dict:
    """
    Atualiza status de uma conversa.

    Args:
        conversa_id: ID da conversa
        novo_status: Novo status
        motivo: Motivo da mudança
        contexto: Dados extras (pedido_ajuda_id, etc.)
        forcar: Se True, ignora validação de transição

    Returns:
        Conversa atualizada

    Raises:
        TransicaoInvalida: Se transição não é permitida
    """
    # Buscar conversa atual
    resultado = supabase.table("conversations").select(
        "id, status, controlled_by"
    ).eq("id", conversa_id).single().execute()

    if not resultado.data:
        raise ValueError(f"Conversa {conversa_id} não encontrada")

    status_atual = StatusConversa(resultado.data["status"])

    # Validar transição
    if not forcar and not pode_transicionar(status_atual, novo_status):
        raise TransicaoInvalida(
            f"Transição de {status_atual.value} para {novo_status.value} não permitida"
        )

    # Atualizar controlled_by se necessário
    controlled_by = resultado.data["controlled_by"]
    if novo_status == StatusConversa.HANDOFF:
        controlled_by = "human"
    elif novo_status in (StatusConversa.ATIVA, StatusConversa.AGUARDANDO_MEDICO):
        controlled_by = "julia"

    # Executar atualização
    update_data = {
        "status": novo_status.value,
        "status_motivo": motivo,
        "status_contexto": contexto,
        "controlled_by": controlled_by,
        "updated_at": datetime.utcnow().isoformat()
    }

    resultado = supabase.table("conversations").update(update_data).eq(
        "id", conversa_id
    ).execute()

    if resultado.data:
        logger.info(
            f"Status conversa {conversa_id}: {status_atual.value} → {novo_status.value}"
            f" (motivo: {motivo})"
        )
        return resultado.data[0]

    raise ValueError("Erro ao atualizar status")


async def buscar_status(conversa_id: str) -> dict:
    """
    Busca status atual de uma conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        {status, status_desde, status_motivo, status_contexto}
    """
    resultado = supabase.table("conversations").select(
        "status, status_desde, status_motivo, status_contexto"
    ).eq("id", conversa_id).single().execute()

    return resultado.data


async def pausar_para_gestor(
    conversa_id: str,
    pedido_ajuda_id: str,
    pergunta: str
) -> dict:
    """
    Pausa conversa aguardando resposta do gestor.

    Args:
        conversa_id: ID da conversa
        pedido_ajuda_id: ID do pedido de ajuda
        pergunta: Pergunta que foi feita ao gestor

    Returns:
        Conversa atualizada
    """
    return await atualizar_status(
        conversa_id=conversa_id,
        novo_status=StatusConversa.AGUARDANDO_GESTOR,
        motivo="Aguardando resposta do gestor",
        contexto={
            "pedido_ajuda_id": pedido_ajuda_id,
            "pergunta": pergunta,
            "aguardando_desde": datetime.utcnow().isoformat()
        }
    )


async def retomar_apos_gestor(
    conversa_id: str,
    resposta_gestor: str | None = None
) -> dict:
    """
    Retoma conversa após resposta do gestor.

    Args:
        conversa_id: ID da conversa
        resposta_gestor: Resposta recebida (opcional)

    Returns:
        Conversa atualizada
    """
    return await atualizar_status(
        conversa_id=conversa_id,
        novo_status=StatusConversa.ATIVA,
        motivo="Gestor respondeu",
        contexto={"resposta_gestor": resposta_gestor} if resposta_gestor else None
    )


async def marcar_aguardando_info(
    conversa_id: str,
    info_pendente: str
) -> dict:
    """
    Marca conversa como aguardando informação (timeout do gestor).

    Args:
        conversa_id: ID da conversa
        info_pendente: Descrição da informação pendente

    Returns:
        Conversa atualizada
    """
    return await atualizar_status(
        conversa_id=conversa_id,
        novo_status=StatusConversa.AGUARDANDO_INFO,
        motivo="Timeout - gestor não respondeu",
        contexto={"info_pendente": info_pendente}
    )


async def listar_conversas_por_status(
    status: StatusConversa,
    limite: int = 100
) -> list[dict]:
    """
    Lista conversas em determinado status.

    Args:
        status: Status a filtrar
        limite: Máximo de resultados

    Returns:
        Lista de conversas
    """
    resultado = supabase.table("conversations").select(
        "id, cliente_id, status, status_desde, status_contexto"
    ).eq("status", status.value).order(
        "status_desde", desc=True
    ).limit(limite).execute()

    return resultado.data or []


async def listar_aguardando_gestor_timeout(
    timeout_minutos: int = 5
) -> list[dict]:
    """
    Lista conversas aguardando gestor há mais de X minutos.

    Args:
        timeout_minutos: Tempo limite em minutos

    Returns:
        Conversas que passaram do timeout
    """
    limite = datetime.utcnow() - timedelta(minutes=timeout_minutos)

    resultado = supabase.table("conversations").select(
        "id, cliente_id, status_desde, status_contexto"
    ).eq("status", StatusConversa.AGUARDANDO_GESTOR.value).lt(
        "status_desde", limite.isoformat()
    ).execute()

    return resultado.data or []
```

---

### T3: Integrar com fluxo de mensagens (45min)

Modificar processador de mensagens para respeitar status.

**Arquivo:** `app/services/mensagens/processador.py` (modificar)

```python
# Adicionar import
from app.services.conversas.status import (
    StatusConversa,
    buscar_status,
    atualizar_status
)


async def processar_mensagem_entrada(
    conversa_id: str,
    mensagem: str,
    cliente_id: str
) -> dict:
    """
    Processa mensagem recebida do médico.

    Verifica status antes de processar.
    """
    # 1. Buscar status atual
    status_info = await buscar_status(conversa_id)
    status = StatusConversa(status_info["status"])

    # 2. Comportamento baseado no status
    if status == StatusConversa.HANDOFF:
        # Conversa com humano - não processa
        logger.info(f"Conversa {conversa_id} em handoff - ignorando para Julia")
        return {"processado": False, "motivo": "handoff"}

    if status == StatusConversa.AGUARDANDO_GESTOR:
        # Julia está esperando gestor - guarda mensagem mas não responde ainda
        logger.info(f"Conversa {conversa_id} aguardando gestor - mensagem enfileirada")
        await _enfileirar_mensagem_pendente(conversa_id, mensagem)
        return {"processado": False, "motivo": "aguardando_gestor"}

    if status == StatusConversa.PAUSADA:
        # Retomar automaticamente quando médico manda mensagem
        logger.info(f"Conversa {conversa_id} retomando de pausa")
        await atualizar_status(
            conversa_id=conversa_id,
            novo_status=StatusConversa.ATIVA,
            motivo="Médico enviou mensagem"
        )

    if status == StatusConversa.AGUARDANDO_INFO:
        # Médico mandou mensagem enquanto Julia esperava info do gestor
        # Retomar conversa normalmente (gestor pode responder depois)
        await atualizar_status(
            conversa_id=conversa_id,
            novo_status=StatusConversa.ATIVA,
            motivo="Médico continuou conversa"
        )

    # 3. Processar normalmente
    return await _processar_mensagem_normal(conversa_id, mensagem, cliente_id)


async def _enfileirar_mensagem_pendente(conversa_id: str, mensagem: str) -> None:
    """Guarda mensagem para processar quando gestor responder."""
    # Implementar fila de mensagens pendentes
    pass
```

---

### T4: Criar worker de timeout (45min)

Worker que processa conversas em timeout de gestor.

**Arquivo:** `app/workers/status_timeout.py`

```python
"""
Worker para processar timeouts de status.
"""
import asyncio
from datetime import datetime, timedelta
from app.services.conversas.status import (
    StatusConversa,
    listar_aguardando_gestor_timeout,
    marcar_aguardando_info
)
from app.services.whatsapp.sender import enviar_mensagem
from app.services.slack.notificador import enviar_lembrete_gestor
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

TIMEOUT_GESTOR_MINUTOS = 5
INTERVALO_LEMBRETE_MINUTOS = 30


async def processar_timeouts_gestor():
    """
    Processa conversas aguardando gestor há mais de 5 minutos.

    1. Envia mensagem ao médico: "Vou confirmar essa info"
    2. Muda status para AGUARDANDO_INFO
    3. Envia lembrete ao gestor no Slack
    """
    conversas = await listar_aguardando_gestor_timeout(TIMEOUT_GESTOR_MINUTOS)

    for conversa in conversas:
        try:
            await _processar_timeout_conversa(conversa)
        except Exception as e:
            logger.error(f"Erro ao processar timeout {conversa['id']}: {e}")


async def _processar_timeout_conversa(conversa: dict) -> None:
    """Processa timeout de uma conversa."""
    conversa_id = conversa["id"]
    cliente_id = conversa["cliente_id"]
    contexto = conversa.get("status_contexto", {})
    pergunta = contexto.get("pergunta", "uma informação")

    logger.info(f"Timeout de gestor para conversa {conversa_id}")

    # 1. Enviar mensagem ao médico
    await enviar_mensagem(
        cliente_id=cliente_id,
        mensagem="Vou confirmar essa info e já te falo!"
    )

    # 2. Atualizar status
    await marcar_aguardando_info(
        conversa_id=conversa_id,
        info_pendente=pergunta
    )

    # 3. Enviar lembrete ao gestor
    pedido_ajuda_id = contexto.get("pedido_ajuda_id")
    if pedido_ajuda_id:
        await enviar_lembrete_gestor(
            pedido_ajuda_id=pedido_ajuda_id,
            mensagem=f"Ainda preciso da resposta sobre: {pergunta}"
        )


async def processar_lembretes_pendentes():
    """
    Envia lembretes para pedidos de ajuda não respondidos.

    Roda a cada 30 minutos.
    """
    from app.services.slack.ajuda_repositorio import listar_pedidos_pendentes

    pedidos = await listar_pedidos_pendentes(
        timeout_minutos=INTERVALO_LEMBRETE_MINUTOS
    )

    for pedido in pedidos:
        try:
            await enviar_lembrete_gestor(
                pedido_ajuda_id=pedido["id"],
                mensagem=f"Lembrete: {pedido['pergunta_original']}"
            )
        except Exception as e:
            logger.error(f"Erro ao enviar lembrete {pedido['id']}: {e}")


async def iniciar_worker_timeout():
    """Inicia worker de timeout."""
    logger.info("Worker de timeout de status iniciado")

    while True:
        try:
            await processar_timeouts_gestor()
            await asyncio.sleep(60)  # Verifica a cada 1 minuto

        except Exception as e:
            logger.error(f"Erro no worker de timeout: {e}")
            await asyncio.sleep(30)


# Registrar no scheduler
def registrar_jobs_status(scheduler):
    """Registra jobs de status no scheduler."""

    # Verificar timeouts a cada minuto
    scheduler.add_job(
        processar_timeouts_gestor,
        "interval",
        minutes=1,
        id="status_timeout_gestor"
    )

    # Enviar lembretes a cada 30 minutos
    scheduler.add_job(
        processar_lembretes_pendentes,
        "interval",
        minutes=30,
        id="status_lembretes_pendentes"
    )
```

---

### T5: Criar testes (30min)

**Arquivo:** `tests/conversas/test_status.py`

```python
"""
Testes para gerenciamento de status de conversas.
"""
import pytest
from datetime import datetime, timedelta
from app.services.conversas.status import (
    StatusConversa,
    pode_transicionar,
    atualizar_status,
    pausar_para_gestor,
    retomar_apos_gestor,
    listar_aguardando_gestor_timeout,
    TransicaoInvalida
)


class TestTransicoes:
    """Testes de transições de status."""

    def test_ativa_para_aguardando_gestor(self):
        """Transição permitida."""
        assert pode_transicionar(
            StatusConversa.ATIVA,
            StatusConversa.AGUARDANDO_GESTOR
        ) is True

    def test_ativa_para_handoff(self):
        """Transição permitida."""
        assert pode_transicionar(
            StatusConversa.ATIVA,
            StatusConversa.HANDOFF
        ) is True

    def test_encerrada_para_ativa(self):
        """Transição NÃO permitida."""
        assert pode_transicionar(
            StatusConversa.ENCERRADA,
            StatusConversa.ATIVA
        ) is False

    def test_aguardando_gestor_para_ativa(self):
        """Transição permitida (gestor respondeu)."""
        assert pode_transicionar(
            StatusConversa.AGUARDANDO_GESTOR,
            StatusConversa.ATIVA
        ) is True


class TestAtualizarStatus:
    """Testes de atualização de status."""

    @pytest.mark.asyncio
    async def test_atualizar_para_aguardando_gestor(self, supabase_mock, conversa_ativa):
        """Atualiza status para aguardando gestor."""
        resultado = await atualizar_status(
            conversa_id=conversa_ativa["id"],
            novo_status=StatusConversa.AGUARDANDO_GESTOR,
            motivo="Pedido de ajuda"
        )

        assert resultado["status"] == "aguardando_gestor"
        assert resultado["status_motivo"] == "Pedido de ajuda"

    @pytest.mark.asyncio
    async def test_transicao_invalida_erro(self, supabase_mock, conversa_encerrada):
        """Transição inválida lança exceção."""
        with pytest.raises(TransicaoInvalida):
            await atualizar_status(
                conversa_id=conversa_encerrada["id"],
                novo_status=StatusConversa.ATIVA
            )

    @pytest.mark.asyncio
    async def test_forcar_transicao(self, supabase_mock, conversa_encerrada):
        """Força transição mesmo se inválida."""
        resultado = await atualizar_status(
            conversa_id=conversa_encerrada["id"],
            novo_status=StatusConversa.ATIVA,
            forcar=True
        )

        assert resultado["status"] == "ativa"


class TestPausarParaGestor:
    """Testes de pausa para gestor."""

    @pytest.mark.asyncio
    async def test_pausar_com_contexto(self, supabase_mock, conversa_ativa):
        """Pausa conversa com contexto de pedido."""
        resultado = await pausar_para_gestor(
            conversa_id=conversa_ativa["id"],
            pedido_ajuda_id="pedido-123",
            pergunta="Tem estacionamento?"
        )

        assert resultado["status"] == "aguardando_gestor"
        assert resultado["status_contexto"]["pedido_ajuda_id"] == "pedido-123"
        assert resultado["status_contexto"]["pergunta"] == "Tem estacionamento?"


class TestRetomar:
    """Testes de retomada."""

    @pytest.mark.asyncio
    async def test_retomar_apos_resposta(self, supabase_mock, conversa_aguardando_gestor):
        """Retoma conversa após gestor responder."""
        resultado = await retomar_apos_gestor(
            conversa_id=conversa_aguardando_gestor["id"],
            resposta_gestor="Sim, tem estacionamento gratuito"
        )

        assert resultado["status"] == "ativa"
        assert resultado["controlled_by"] == "julia"


class TestTimeout:
    """Testes de timeout."""

    @pytest.mark.asyncio
    async def test_listar_timeout(self, supabase_mock, conversas_aguardando_gestor):
        """Lista conversas em timeout."""
        # Assume que fixture tem conversas criadas há mais de 5 min
        resultado = await listar_aguardando_gestor_timeout(timeout_minutos=5)

        assert len(resultado) > 0
        for conv in resultado:
            assert conv["status"] == "aguardando_gestor"
```

---

## DoD (Definition of Done)

### Funcional
- [ ] Enum `status_conversa` criado no banco
- [ ] Coluna `status` adicionada com default 'ativa'
- [ ] Colunas de metadados (status_desde, status_motivo, status_contexto)
- [ ] Trigger de `status_desde` funcionando
- [ ] Conversas existentes migradas (handoff → controlled_by=human)

### Serviço
- [ ] Transições validadas
- [ ] `pausar_para_gestor()` funcionando
- [ ] `retomar_apos_gestor()` funcionando
- [ ] `marcar_aguardando_info()` funcionando

### Worker
- [ ] Timeout de 5 minutos detectado
- [ ] Mensagem "Vou confirmar" enviada
- [ ] Lembrete ao gestor enviado
- [ ] Lembrete a cada 30 minutos

### Testes
- [ ] Testes de transições
- [ ] Testes de timeout
- [ ] Testes de retomada

### Verificação Manual

1. **Simular pedido de ajuda:**
   ```python
   await pausar_para_gestor(
       conversa_id="conv-123",
       pedido_ajuda_id="pedido-456",
       pergunta="Hospital tem wifi?"
   )
   ```

2. **Verificar status:**
   ```sql
   SELECT status, status_desde, status_motivo, status_contexto
   FROM conversations
   WHERE id = 'conv-123';
   ```

3. **Simular timeout (esperar 5+ min):**
   Verificar que:
   - Médico recebeu "Vou confirmar essa info"
   - Status mudou para `aguardando_info`
   - Gestor recebeu lembrete no Slack

4. **Simular resposta do gestor:**
   ```python
   await retomar_apos_gestor(
       conversa_id="conv-123",
       resposta_gestor="Sim, tem wifi gratuito"
   )
   ```
   Verificar que status voltou para `ativa`.

---

## Diagrama de Estados

```
                    ┌──────────────────┐
                    │      ATIVA       │
                    │  (Julia responde)│
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌─────────────┐
│AGUARDANDO_    │  │   AGUARDANDO_   │  │   HANDOFF   │
│   MEDICO      │  │     GESTOR      │  │  (humano)   │
└───────┬───────┘  └────────┬────────┘  └──────┬──────┘
        │                   │                   │
        │           ┌───────┴───────┐          │
        │           │               │          │
        │           ▼               ▼          │
        │   ┌───────────────┐  timeout        │
        │   │    ATIVA      │    5min         │
        │   │(gestor resp.) │      │          │
        │   └───────────────┘      ▼          │
        │                   ┌─────────────┐   │
        │                   │AGUARDANDO_  │   │
        │                   │   INFO      │   │
        │                   └──────┬──────┘   │
        │                          │          │
        └──────────────────────────┴──────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    ENCERRADA     │
                    └──────────────────┘
```

---

## Notas para Dev

1. **controlled_by vs status:** Manter ambos sincronizados
   - `handoff` → `controlled_by=human`
   - Outros → `controlled_by=julia`
2. **Timeout:** Job roda a cada 1 minuto verificando `status_desde`
3. **Mensagens pendentes:** Quando status=AGUARDANDO_GESTOR, mensagens do médico são enfileiradas
4. **Retomada:** Quando status volta para ATIVA, processar mensagens pendentes
5. **Lembrete:** Máximo de 3 lembretes por pedido de ajuda

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Timeouts processados em < 1 min | 99% |
| Conversas retomadas após gestor | > 90% |
| Médicos que recebem "vou confirmar" | 100% dos timeouts |
