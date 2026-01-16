# E08: Canal de Ajuda Julia → Gestor

**Fase:** 3 - Interação Gestor
**Estimativa:** 6h
**Prioridade:** Crítica ⭐
**Dependências:** Nenhuma

---

## Objetivo

Implementar canal de comunicação onde Julia pode pedir ajuda ao gestor quando não sabe responder algo factual, evitando alucinações e garantindo respostas corretas.

## Problema

```
Médico: "Esse hospital tem refeição inclusa?"

Julia ATUAL (ruim):
"Sim, tem!" ← ALUCINAÇÃO (Julia não sabe)

Julia NOVA (certo):
"Vou confirmar essa info e já te falo!" ← PAUSA
[Pergunta ao gestor no Slack]
[Gestor responde]
"Tem sim! Refeitório 24h, refeição inclusa" ← RESPOSTA CORRETA
```

---

## Fluxo Completo

```
┌─────────────────────────────────────────────────────────┐
│                    CONVERSA WHATSAPP                    │
│  Médico pergunta algo que Julia não sabe                │
│  Status: ATIVA → AGUARDANDO_GESTOR                      │
└─────────────────────────────────────────────────────────┘
                           │
                           │ Julia detecta que não sabe
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    SLACK (Canal Ajuda)                  │
│  Julia: "🔔 Preciso de ajuda! Dr Carlos perguntou..."   │
│  [5 min timeout]                                        │
│  Se gestor não responde → Lembrete automático           │
└─────────────────────────────────────────────────────────┘
                           │
                           │ Gestor responde
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    CONVERSA WHATSAPP                    │
│  Julia responde ao médico com info correta              │
│  Status: AGUARDANDO_GESTOR → ATIVA                      │
└─────────────────────────────────────────────────────────┘
```

---

## Tarefas

### T1: Criar tabela pedidos_ajuda (30min)

**Migration:** `create_pedidos_ajuda_table`

```sql
-- Migration: create_pedidos_ajuda_table
-- Sprint 32 E08: Canal de ajuda Julia → Gestor

CREATE TABLE IF NOT EXISTS pedidos_ajuda (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    cliente_id UUID NOT NULL REFERENCES clientes(id),

    -- Contexto da pergunta
    pergunta_medico TEXT NOT NULL,
    contexto TEXT,  -- Últimas mensagens da conversa

    -- Categorização
    categoria TEXT NOT NULL,  -- fato_hospital | fato_vaga | negociacao | outro
    entidade_id UUID,  -- hospital_id ou vaga_id (se aplicável)

    -- Status
    status TEXT NOT NULL DEFAULT 'pendente',  -- pendente | respondido | timeout | cancelado
    criado_em TIMESTAMPTZ DEFAULT now(),
    timeout_em TIMESTAMPTZ,  -- Quando fez timeout
    respondido_em TIMESTAMPTZ,

    -- Resposta do gestor
    resposta_gestor TEXT,
    respondido_por TEXT,  -- ID do usuário Slack

    -- Slack
    slack_message_ts TEXT,  -- ID da mensagem no Slack
    slack_thread_ts TEXT,  -- Thread ID

    -- Lembrete
    lembretes_enviados INT DEFAULT 0,
    ultimo_lembrete_em TIMESTAMPTZ,

    CONSTRAINT chk_pedido_status CHECK (status IN ('pendente', 'respondido', 'timeout', 'cancelado')),
    CONSTRAINT chk_pedido_categoria CHECK (categoria IN ('fato_hospital', 'fato_vaga', 'negociacao', 'outro'))
);

-- Índices
CREATE INDEX idx_pedidos_ajuda_pendentes
ON pedidos_ajuda (status, criado_em)
WHERE status = 'pendente';

CREATE INDEX idx_pedidos_ajuda_conversa
ON pedidos_ajuda (conversation_id);

-- Comentários
COMMENT ON TABLE pedidos_ajuda IS 'Pedidos de ajuda de Julia para gestor';
COMMENT ON COLUMN pedidos_ajuda.categoria IS 'fato_hospital: info sobre hospital, fato_vaga: info sobre vaga, negociacao: margem/valor, outro: geral';
```

### T2: Adicionar estado AGUARDANDO_GESTOR às conversas (20min)

**Migration:** `add_aguardando_gestor_status`

```sql
-- Migration: add_aguardando_gestor_status
-- Sprint 32 E08: Novo estado de conversa

-- Adicionar novo valor possível ao status
ALTER TABLE conversations
DROP CONSTRAINT IF EXISTS chk_conversation_status;

ALTER TABLE conversations
ADD CONSTRAINT chk_conversation_status
CHECK (status IN ('ativa', 'pausada', 'aguardando_gestor', 'aguardando_medico', 'finalizada', 'handoff'));

-- Adicionar coluna para ID do pedido de ajuda ativo
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS pedido_ajuda_id UUID REFERENCES pedidos_ajuda(id);

COMMENT ON COLUMN conversations.pedido_ajuda_id IS 'ID do pedido de ajuda ativo (se status=aguardando_gestor)';
```

### T3: Criar serviço de pedidos de ajuda (60min)

**Arquivo:** `app/services/canal_ajuda.py`

```python
"""
Serviço do canal de ajuda Julia → Gestor.

Sprint 32 E08 - Julia pede ajuda quando não sabe responder.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from app.services.supabase import supabase
from app.services.slack import slack_client

logger = logging.getLogger(__name__)

CategoriaPedido = Literal["fato_hospital", "fato_vaga", "negociacao", "outro"]

# Timeout em segundos (5 minutos)
TIMEOUT_SEGUNDOS = 300

# Intervalo entre lembretes (30 minutos)
INTERVALO_LEMBRETE_SEGUNDOS = 1800

# Canal do Slack para pedidos de ajuda
SLACK_CANAL_AJUDA = "#julia-ajuda"


async def criar_pedido_ajuda(
    conversation_id: str,
    cliente_id: str,
    pergunta_medico: str,
    categoria: CategoriaPedido,
    contexto: Optional[str] = None,
    entidade_id: Optional[str] = None,
) -> Optional[str]:
    """
    Cria um pedido de ajuda para o gestor.

    Args:
        conversation_id: ID da conversa
        cliente_id: ID do médico
        pergunta_medico: O que o médico perguntou
        categoria: Tipo do pedido
        contexto: Últimas mensagens para contexto
        entidade_id: ID do hospital/vaga se aplicável

    Returns:
        ID do pedido criado ou None se erro
    """
    try:
        # Buscar dados do médico para contexto
        medico = (
            supabase.table("clientes")
            .select("nome, telefone, especialidade")
            .eq("id", cliente_id)
            .single()
            .execute()
        )

        nome_medico = medico.data.get("nome", "Médico") if medico.data else "Médico"

        # Criar pedido no banco
        response = supabase.table("pedidos_ajuda").insert({
            "conversation_id": conversation_id,
            "cliente_id": cliente_id,
            "pergunta_medico": pergunta_medico,
            "categoria": categoria,
            "contexto": contexto,
            "entidade_id": entidade_id,
            "status": "pendente",
        }).execute()

        if not response.data:
            return None

        pedido_id = response.data[0]["id"]

        # Atualizar conversa para status aguardando_gestor
        supabase.table("conversations").update({
            "status": "aguardando_gestor",
            "pedido_ajuda_id": pedido_id,
        }).eq("id", conversation_id).execute()

        # Enviar mensagem no Slack
        slack_msg = await _enviar_pedido_slack(
            pedido_id=pedido_id,
            nome_medico=nome_medico,
            pergunta=pergunta_medico,
            categoria=categoria,
            contexto=contexto,
        )

        if slack_msg:
            # Salvar IDs do Slack
            supabase.table("pedidos_ajuda").update({
                "slack_message_ts": slack_msg.get("ts"),
                "slack_thread_ts": slack_msg.get("thread_ts"),
            }).eq("id", pedido_id).execute()

        logger.info(f"Pedido de ajuda criado: {pedido_id} para {nome_medico}")

        return pedido_id

    except Exception as e:
        logger.error(f"Erro ao criar pedido de ajuda: {e}")
        return None


async def _enviar_pedido_slack(
    pedido_id: str,
    nome_medico: str,
    pergunta: str,
    categoria: str,
    contexto: Optional[str],
) -> Optional[dict]:
    """Envia pedido de ajuda para o Slack."""
    try:
        emoji = {
            "fato_hospital": "🏥",
            "fato_vaga": "📋",
            "negociacao": "💰",
            "outro": "❓",
        }.get(categoria, "❓")

        texto = (
            f"{emoji} *Preciso de ajuda!*\n\n"
            f"*Médico:* {nome_medico}\n"
            f"*Pergunta:* {pergunta}\n"
            f"*Categoria:* {categoria}\n"
        )

        if contexto:
            texto += f"\n*Contexto:*\n```{contexto[:500]}```\n"

        texto += (
            f"\n_Pedido ID: {pedido_id}_\n"
            f"_Responda nesta thread para Julia enviar ao médico._"
        )

        response = await slack_client.enviar_mensagem(
            canal=SLACK_CANAL_AJUDA,
            texto=texto,
        )

        return response

    except Exception as e:
        logger.error(f"Erro ao enviar pedido para Slack: {e}")
        return None


async def registrar_resposta_gestor(
    pedido_id: str,
    resposta: str,
    respondido_por: str,
) -> bool:
    """
    Registra resposta do gestor ao pedido de ajuda.

    Args:
        pedido_id: ID do pedido
        resposta: Texto da resposta
        respondido_por: ID do usuário Slack

    Returns:
        True se registrou com sucesso
    """
    try:
        # Atualizar pedido
        response = (
            supabase.table("pedidos_ajuda")
            .update({
                "status": "respondido",
                "resposta_gestor": resposta,
                "respondido_por": respondido_por,
                "respondido_em": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", pedido_id)
            .eq("status", "pendente")
            .execute()
        )

        if not response.data:
            logger.warning(f"Pedido {pedido_id} não encontrado ou já respondido")
            return False

        pedido = response.data[0]

        # Atualizar conversa para ativa
        supabase.table("conversations").update({
            "status": "ativa",
            "pedido_ajuda_id": None,
        }).eq("id", pedido["conversation_id"]).execute()

        # Agendar envio da resposta ao médico
        await _agendar_resposta_medico(
            conversation_id=pedido["conversation_id"],
            cliente_id=pedido["cliente_id"],
            resposta=resposta,
        )

        logger.info(f"Resposta registrada para pedido {pedido_id}")

        return True

    except Exception as e:
        logger.error(f"Erro ao registrar resposta: {e}")
        return False


async def _agendar_resposta_medico(
    conversation_id: str,
    cliente_id: str,
    resposta: str,
) -> None:
    """Agenda envio da resposta para o médico."""
    # Enfileirar mensagem de resposta
    supabase.table("fila_mensagens").insert({
        "cliente_id": cliente_id,
        "send_type": "resposta_ajuda",
        "queue_status": "queued",
        "metadata": {
            "conversation_id": conversation_id,
            "resposta_gestor": resposta,
            "contexto": "Julia recebeu resposta do gestor",
        },
    }).execute()


async def processar_timeout_pedido(pedido_id: str) -> bool:
    """
    Processa timeout de um pedido (gestor não respondeu em 5 min).

    Ação: Julia responde "Vou confirmar e já te falo"
    """
    try:
        # Atualizar pedido
        supabase.table("pedidos_ajuda").update({
            "status": "timeout",
            "timeout_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pedido_id).execute()

        # Buscar dados do pedido
        pedido = (
            supabase.table("pedidos_ajuda")
            .select("conversation_id, cliente_id")
            .eq("id", pedido_id)
            .single()
            .execute()
        )

        if pedido.data:
            # Atualizar conversa para status especial
            supabase.table("conversations").update({
                "status": "aguardando_info",  # Esperando info do gestor
            }).eq("id", pedido.data["conversation_id"]).execute()

            # Enfileirar mensagem de timeout
            supabase.table("fila_mensagens").insert({
                "cliente_id": pedido.data["cliente_id"],
                "send_type": "timeout_ajuda",
                "queue_status": "queued",
                "metadata": {
                    "conversation_id": pedido.data["conversation_id"],
                    "pedido_id": pedido_id,
                    "mensagem": "Vou confirmar essa info e já te falo!",
                },
            }).execute()

        return True

    except Exception as e:
        logger.error(f"Erro ao processar timeout: {e}")
        return False


async def enviar_lembrete(pedido_id: str) -> bool:
    """Envia lembrete ao gestor sobre pedido pendente."""
    try:
        # Buscar pedido
        pedido = (
            supabase.table("pedidos_ajuda")
            .select("*")
            .eq("id", pedido_id)
            .single()
            .execute()
        )

        if not pedido.data or pedido.data["status"] != "pendente":
            return False

        # Buscar nome do médico
        medico = (
            supabase.table("clientes")
            .select("nome")
            .eq("id", pedido.data["cliente_id"])
            .single()
            .execute()
        )

        nome = medico.data.get("nome", "Médico") if medico.data else "Médico"

        # Enviar lembrete no Slack (reply na thread)
        await slack_client.enviar_mensagem(
            canal=SLACK_CANAL_AJUDA,
            texto=(
                f"🔔 *Lembrete:* Ainda preciso da resposta!\n\n"
                f"*Médico:* {nome}\n"
                f"*Pergunta:* {pedido.data['pergunta_medico']}\n\n"
                f"_O médico está aguardando._"
            ),
            thread_ts=pedido.data.get("slack_thread_ts"),
        )

        # Atualizar contador de lembretes
        supabase.table("pedidos_ajuda").update({
            "lembretes_enviados": pedido.data["lembretes_enviados"] + 1,
            "ultimo_lembrete_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pedido_id).execute()

        return True

    except Exception as e:
        logger.error(f"Erro ao enviar lembrete: {e}")
        return False


async def buscar_pedidos_pendentes() -> list[dict]:
    """Busca pedidos pendentes para processamento."""
    response = (
        supabase.table("pedidos_ajuda")
        .select("*")
        .eq("status", "pendente")
        .order("criado_em", desc=False)
        .execute()
    )

    return response.data or []
```

### T4: Criar job de monitoramento de timeouts (45min)

**Arquivo:** `app/workers/ajuda_worker.py`

```python
"""
Worker para monitoramento de pedidos de ajuda.

Sprint 32 E08 - Processa timeouts e lembretes.
"""
import logging
from datetime import datetime, timezone, timedelta

from app.services.canal_ajuda import (
    buscar_pedidos_pendentes,
    processar_timeout_pedido,
    enviar_lembrete,
    TIMEOUT_SEGUNDOS,
    INTERVALO_LEMBRETE_SEGUNDOS,
)

logger = logging.getLogger(__name__)


async def processar_pedidos_pendentes() -> dict:
    """
    Processa pedidos pendentes.

    - Verifica timeouts (5 min sem resposta)
    - Envia lembretes (a cada 30 min após timeout)
    """
    stats = {
        "processados": 0,
        "timeouts": 0,
        "lembretes": 0,
    }

    pedidos = await buscar_pedidos_pendentes()
    agora = datetime.now(timezone.utc)

    for pedido in pedidos:
        stats["processados"] += 1

        criado_em = datetime.fromisoformat(
            pedido["criado_em"].replace("Z", "+00:00")
        )
        idade_segundos = (agora - criado_em).total_seconds()

        # Verificar timeout inicial (5 min)
        if idade_segundos > TIMEOUT_SEGUNDOS and not pedido.get("timeout_em"):
            await processar_timeout_pedido(pedido["id"])
            stats["timeouts"] += 1
            continue

        # Verificar se precisa enviar lembrete
        if pedido.get("timeout_em"):
            ultimo_lembrete = pedido.get("ultimo_lembrete_em")

            if ultimo_lembrete:
                ultimo = datetime.fromisoformat(
                    ultimo_lembrete.replace("Z", "+00:00")
                )
                desde_lembrete = (agora - ultimo).total_seconds()
            else:
                desde_lembrete = INTERVALO_LEMBRETE_SEGUNDOS + 1

            if desde_lembrete > INTERVALO_LEMBRETE_SEGUNDOS:
                await enviar_lembrete(pedido["id"])
                stats["lembretes"] += 1

    logger.info(
        f"Pedidos processados: {stats['processados']}, "
        f"timeouts: {stats['timeouts']}, lembretes: {stats['lembretes']}"
    )

    return stats


# Adicionar ao scheduler:
# {
#     "name": "processar_pedidos_ajuda",
#     "function": processar_pedidos_pendentes,
#     "cron": "* * * * *",  # A cada minuto
#     "description": "Processa timeouts e lembretes de pedidos de ajuda",
# }
```

### T5: Integrar com handler do Slack (60min)

**Arquivo:** `app/api/routes/slack.py`

**Adicionar handler para respostas em threads:**

```python
from app.services.canal_ajuda import registrar_resposta_gestor

@router.post("/slack/events")
async def slack_events(request: Request):
    """Handler de eventos do Slack."""
    payload = await request.json()

    # Verificação de challenge (Slack verifica endpoint)
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}

    event = payload.get("event", {})
    event_type = event.get("type")

    # Mensagem em thread (pode ser resposta a pedido de ajuda)
    if event_type == "message" and event.get("thread_ts"):
        await _processar_resposta_thread(event)

    return {"ok": True}


async def _processar_resposta_thread(event: dict):
    """
    Processa mensagem em thread que pode ser resposta a pedido de ajuda.
    """
    thread_ts = event.get("thread_ts")
    texto = event.get("text", "")
    user_id = event.get("user")

    # Ignorar mensagens da própria Julia
    if event.get("bot_id"):
        return

    # Buscar pedido de ajuda pela thread
    from app.services.supabase import supabase

    pedido = (
        supabase.table("pedidos_ajuda")
        .select("id, status")
        .eq("slack_thread_ts", thread_ts)
        .single()
        .execute()
    )

    if not pedido.data:
        return  # Não é uma thread de pedido de ajuda

    if pedido.data["status"] != "pendente":
        return  # Já foi respondido

    # Registrar resposta
    await registrar_resposta_gestor(
        pedido_id=pedido.data["id"],
        resposta=texto,
        respondido_por=user_id,
    )

    # Confirmar no Slack
    from app.services.slack import slack_client

    await slack_client.enviar_mensagem(
        canal=event.get("channel"),
        texto="✅ Resposta registrada! Julia vai enviar ao médico.",
        thread_ts=thread_ts,
    )
```

### T6: Integrar com detecção de "não sei" no agente (45min)

**Arquivo:** `app/services/agente_julia.py`

**Adicionar detecção de quando Julia não sabe:**

```python
from app.services.canal_ajuda import criar_pedido_ajuda

async def processar_resposta_julia(
    resposta: str,
    conversation_id: str,
    cliente_id: str,
    mensagem_medico: str,
    contexto: str,
) -> str:
    """
    Processa resposta de Julia antes de enviar.

    Detecta padrões de "não sei" e aciona canal de ajuda.
    """
    # Padrões que indicam que Julia não sabe
    PADROES_NAO_SEI = [
        "não tenho essa informação",
        "vou verificar",
        "preciso confirmar",
        "deixa eu checar",
        "não sei ao certo",
        "não consigo confirmar",
    ]

    resposta_lower = resposta.lower()

    # Verificar se Julia está admitindo não saber
    for padrao in PADROES_NAO_SEI:
        if padrao in resposta_lower:
            # Detectar categoria baseada na pergunta
            categoria = _detectar_categoria_pergunta(mensagem_medico)

            # Criar pedido de ajuda
            pedido_id = await criar_pedido_ajuda(
                conversation_id=conversation_id,
                cliente_id=cliente_id,
                pergunta_medico=mensagem_medico,
                categoria=categoria,
                contexto=contexto,
            )

            if pedido_id:
                # Substituir resposta por mensagem de espera
                return "Vou confirmar essa info e já te falo!"

    return resposta


def _detectar_categoria_pergunta(pergunta: str) -> str:
    """Detecta categoria da pergunta."""
    pergunta_lower = pergunta.lower()

    # Palavras-chave por categoria
    if any(p in pergunta_lower for p in ["hospital", "refeit", "estacionamento", "vestiário", "estrutura"]):
        return "fato_hospital"

    if any(p in pergunta_lower for p in ["vaga", "plantão", "data", "horário", "turno"]):
        return "fato_vaga"

    if any(p in pergunta_lower for p in ["valor", "preço", "pagar", "negociar", "desconto"]):
        return "negociacao"

    return "outro"
```

### T7: Criar testes (45min)

**Arquivo:** `tests/unit/test_canal_ajuda.py`

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.canal_ajuda import (
    criar_pedido_ajuda,
    registrar_resposta_gestor,
    processar_timeout_pedido,
)


class TestCriarPedidoAjuda:
    """Testes para criação de pedidos de ajuda."""

    @pytest.mark.asyncio
    async def test_cria_pedido_e_atualiza_conversa(self):
        """Deve criar pedido e atualizar status da conversa."""
        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock buscar médico
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "nome": "Dr João"
            }

            # Mock inserir pedido
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "pedido-123"}
            ]

            # Mock update conversa
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

            with patch("app.services.canal_ajuda._enviar_pedido_slack") as mock_slack:
                mock_slack.return_value = {"ts": "123", "thread_ts": "456"}

                pedido_id = await criar_pedido_ajuda(
                    conversation_id="conv-1",
                    cliente_id="med-1",
                    pergunta_medico="Tem refeição inclusa?",
                    categoria="fato_hospital",
                )

                assert pedido_id == "pedido-123"


class TestRegistrarResposta:
    """Testes para registro de respostas."""

    @pytest.mark.asyncio
    async def test_registra_resposta_e_atualiza_conversa(self):
        """Deve registrar resposta e reativar conversa."""
        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock update pedido
            mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                {"conversation_id": "conv-1", "cliente_id": "med-1"}
            ]

            # Mock update conversa
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

            # Mock enfileirar resposta
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{}]

            resultado = await registrar_resposta_gestor(
                pedido_id="pedido-1",
                resposta="Sim, tem refeitório 24h!",
                respondido_por="U123",
            )

            assert resultado is True


class TestTimeout:
    """Testes para processamento de timeout."""

    @pytest.mark.asyncio
    async def test_processa_timeout(self):
        """Deve processar timeout e enfileirar mensagem."""
        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock update pedido
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

            # Mock buscar pedido
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "conversation_id": "conv-1",
                "cliente_id": "med-1",
            }

            # Mock update conversa e enfileirar
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{}]

            resultado = await processar_timeout_pedido("pedido-1")

            assert resultado is True
```

---

## Definition of Done (DoD)

### Critérios Obrigatórios

- [ ] **Tabela pedidos_ajuda criada**
  - [ ] Migration aplicada
  - [ ] Índices funcionando
  - [ ] Constraint de status válida

- [ ] **Status AGUARDANDO_GESTOR na conversa**
  - [ ] Constraint atualizada
  - [ ] Coluna pedido_ajuda_id existe

- [ ] **Criação de pedidos funciona**
  - [ ] `criar_pedido_ajuda()` cria registro
  - [ ] Atualiza status da conversa
  - [ ] Envia mensagem no Slack

- [ ] **Registro de respostas funciona**
  - [ ] Handler de eventos Slack funciona
  - [ ] `registrar_resposta_gestor()` atualiza pedido
  - [ ] Reativa conversa
  - [ ] Enfileira resposta ao médico

- [ ] **Timeout e lembretes funcionam**
  - [ ] Timeout após 5 minutos
  - [ ] Mensagem "Vou confirmar" enviada
  - [ ] Lembretes a cada 30 minutos

- [ ] **Integração com agente**
  - [ ] Detecta padrões de "não sei"
  - [ ] Aciona canal de ajuda automaticamente

- [ ] **Testes passando**
  - [ ] `uv run pytest tests/unit/test_canal_ajuda.py -v` = OK

### Verificação Manual

```bash
# 1. Simular pedido de ajuda
# No Slack, deve aparecer mensagem no canal #julia-ajuda

# 2. Responder na thread
# Julia deve enviar resposta ao médico

# 3. Testar timeout
# Após 5 minutos sem resposta, médico recebe "Vou confirmar"

# 4. Verificar lembretes
# A cada 30 min, lembrete aparece na thread do Slack
```

---

## Notas para o Desenvolvedor

1. **Slack Events API:**
   - Precisa configurar Event Subscriptions no app Slack
   - Eventos necessários: `message.channels`, `message.groups`

2. **Thread vs Canal:**
   - Pedido vai no canal
   - Resposta DEVE ser na thread
   - Isso permite organização

3. **Detecção de "não sei":**
   - Lista de padrões pode crescer
   - Considerar usar LLM para detecção mais robusta

4. **Performance:**
   - Job de timeout roda a cada minuto
   - Verificar se precisa otimizar
