# Epic 07: Job de Follow-up e Expiracao

## Objetivo

Criar job que processa follow-ups pendentes e expira handoffs que ultrapassaram o prazo.

## Contexto

O sistema precisa:
1. Enviar follow-up apos 2h sem resposta do divulgador
2. Enviar segundo follow-up apos 24h
3. Expirar handoff apos 48h
4. Liberar vaga quando expira
5. Notificar medico quando expira

---

## Story 7.1: Job de Processamento

### Objetivo
Criar job que roda periodicamente para processar handoffs.

### Arquivo: `app/workers/handoff_processor.py`

```python
"""
Job de processamento de handoffs (follow-up e expiracao).

Sprint 20 - E07 - Automacao de follow-up.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from app.services.external_handoff.repository import (
    listar_handoffs_pendentes,
    atualizar_status_handoff,
)
from app.services.external_handoff.followup import enviar_followup
from app.services.business_events import emit_event, EventType
from app.services.supabase import supabase
from app.services.outbound import send_outbound_message
from app.services.slack.notificador import notificar_slack

logger = logging.getLogger(__name__)

# Configuracoes de tempo
FOLLOWUP_1_HORAS = 2   # Primeiro follow-up apos 2h
FOLLOWUP_2_HORAS = 24  # Segundo follow-up apos 24h
EXPIRACAO_HORAS = 48   # Expira apos 48h
MAX_FOLLOWUPS = 3      # Maximo de follow-ups


async def processar_handoffs_pendentes() -> dict:
    """
    Processa todos os handoffs pendentes.

    Fluxo:
    1. Busca handoffs com status 'pending' ou 'contacted'
    2. Para cada handoff:
       - Se passou de 48h: expira
       - Se passou de 24h e followup_count < 2: envia follow-up 2
       - Se passou de 2h e followup_count == 0: envia follow-up 1

    Returns:
        Dict com estatisticas do processamento
    """
    logger.info("Iniciando processamento de handoffs pendentes")

    stats = {
        "total_processados": 0,
        "followups_enviados": 0,
        "expirados": 0,
        "erros": 0,
    }

    try:
        handoffs = await listar_handoffs_pendentes()
        logger.info(f"Encontrados {len(handoffs)} handoffs pendentes")

        now = datetime.now(timezone.utc)

        for handoff in handoffs:
            try:
                resultado = await _processar_handoff(handoff, now)
                stats["total_processados"] += 1

                if resultado == "followup":
                    stats["followups_enviados"] += 1
                elif resultado == "expired":
                    stats["expirados"] += 1

            except Exception as e:
                logger.error(f"Erro ao processar handoff {handoff['id']}: {e}")
                stats["erros"] += 1

        logger.info(f"Processamento concluido: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Erro no job de handoffs: {e}")
        raise


async def _processar_handoff(handoff: dict, now: datetime) -> str:
    """
    Processa um handoff individual.

    Args:
        handoff: Dados do handoff
        now: Timestamp atual

    Returns:
        'followup', 'expired', ou 'noop'
    """
    handoff_id = handoff["id"]
    reserved_until = handoff.get("reserved_until")
    followup_count = handoff.get("followup_count", 0)
    last_followup_at = handoff.get("last_followup_at")
    created_at = handoff.get("created_at")

    # Converter timestamps
    if isinstance(reserved_until, str):
        reserved_until = datetime.fromisoformat(reserved_until.replace("Z", "+00:00"))
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    if last_followup_at and isinstance(last_followup_at, str):
        last_followup_at = datetime.fromisoformat(last_followup_at.replace("Z", "+00:00"))

    # Verificar expiracao
    if now >= reserved_until:
        await _expirar_handoff(handoff)
        return "expired"

    # Calcular horas desde criacao
    horas_desde_criacao = (now - created_at).total_seconds() / 3600

    # Verificar se deve enviar follow-up
    if followup_count >= MAX_FOLLOWUPS:
        return "noop"

    # Follow-up 1: apos 2h
    if followup_count == 0 and horas_desde_criacao >= FOLLOWUP_1_HORAS:
        await _enviar_followup(handoff, 1)
        return "followup"

    # Follow-up 2: apos 24h
    if followup_count == 1 and horas_desde_criacao >= FOLLOWUP_2_HORAS:
        await _enviar_followup(handoff, 2)
        return "followup"

    # Follow-up 3: apos 36h (se configurado)
    if followup_count == 2 and horas_desde_criacao >= 36:
        await _enviar_followup(handoff, 3)
        return "followup"

    return "noop"


async def _enviar_followup(handoff: dict, numero: int) -> None:
    """
    Envia mensagem de follow-up para o divulgador.

    Args:
        handoff: Dados do handoff
        numero: Numero do follow-up (1, 2, 3)
    """
    handoff_id = handoff["id"]
    divulgador_nome = handoff.get("divulgador_nome", "")
    divulgador_telefone = handoff.get("divulgador_telefone")

    logger.info(f"Enviando follow-up {numero} para handoff {handoff_id[:8]}")

    # Montar mensagem baseada no numero do follow-up
    if numero == 1:
        mensagem = (
            f"Oi {divulgador_nome}! Tudo bem?\n\n"
            "Conseguiu falar com o medico sobre aquele plantao?\n\n"
            "Me avisa aqui se fechou ou nao, pra eu atualizar"
        )
    elif numero == 2:
        mensagem = (
            f"Oi {divulgador_nome}!\n\n"
            "Ainda to aguardando retorno sobre o plantao.\n"
            "O medico ta interessado, me ajuda aqui?\n\n"
            "Responde CONFIRMADO se fechou ou NAO FECHOU se nao rolou"
        )
    else:
        mensagem = (
            f"Ultimo aviso {divulgador_nome}!\n\n"
            "Se eu nao tiver retorno, vou liberar o medico pra outras vagas.\n\n"
            "CONFIRMADO ou NAO FECHOU?"
        )

    # Enviar via sistema de outbound
    from app.services.external_handoff.messaging import enviar_mensagem_divulgador

    try:
        await enviar_mensagem_divulgador(
            telefone=divulgador_telefone,
            mensagem=mensagem,
        )

        # Atualizar contador de follow-ups
        supabase.table("external_handoffs") \
            .update({
                "followup_count": numero,
                "last_followup_at": datetime.now(timezone.utc).isoformat(),
            }) \
            .eq("id", handoff_id) \
            .execute()

        # Emitir evento
        await emit_event(
            EventType.HANDOFF_FOLLOWUP_SENT,
            {
                "handoff_id": handoff_id,
                "followup_number": numero,
                "divulgador_telefone": divulgador_telefone[-4:],  # Ultimos 4 digitos
            }
        )

        logger.info(f"Follow-up {numero} enviado para handoff {handoff_id[:8]}")

    except Exception as e:
        logger.error(f"Erro ao enviar follow-up: {e}")
        raise


async def _expirar_handoff(handoff: dict) -> None:
    """
    Expira um handoff e libera a vaga.

    Args:
        handoff: Dados do handoff
    """
    handoff_id = handoff["id"]
    vaga_id = handoff["vaga_id"]
    cliente_id = handoff["cliente_id"]

    logger.info(f"Expirando handoff {handoff_id[:8]}")

    # Atualizar handoff
    await atualizar_status_handoff(
        handoff_id=handoff_id,
        novo_status="expired",
        expired_at=datetime.now(timezone.utc),
    )

    # Liberar vaga
    supabase.table("vagas") \
        .update({"status": "aberta"}) \
        .eq("id", vaga_id) \
        .execute()

    logger.info(f"Vaga {vaga_id} liberada")

    # Emitir evento
    await emit_event(
        EventType.HANDOFF_EXPIRED,
        {
            "handoff_id": handoff_id,
            "vaga_id": vaga_id,
            "followup_count": handoff.get("followup_count", 0),
        }
    )

    # Notificar Slack
    await notificar_slack(
        f":hourglass: *Handoff Expirado*\n"
        f"Divulgador: {handoff.get('divulgador_nome')}\n"
        f"Follow-ups enviados: {handoff.get('followup_count', 0)}\n"
        f"Vaga liberada: {vaga_id[:8]}...",
        canal="vagas"
    )

    # Notificar medico
    try:
        await send_outbound_message(
            cliente_id=cliente_id,
            mensagem=(
                "Oi! Infelizmente o divulgador nao retornou sobre o plantao.\n\n"
                "Vou liberar a vaga. Quer que eu procure outras opcoes pra voce?"
            ),
            campanha="handoff_expired",
        )
    except Exception as e:
        logger.error(f"Erro ao notificar medico {cliente_id}: {e}")
```

### DoD

- [ ] Job `processar_handoffs_pendentes` criado
- [ ] Logica de follow-up implementada
- [ ] Logica de expiracao implementada
- [ ] Eventos emitidos corretamente

---

## Story 7.2: Repository - Listar Pendentes

### Objetivo
Adicionar funcao para listar handoffs pendentes.

### Arquivo: `app/services/external_handoff/repository.py`

```python
# Adicionar funcao:

async def listar_handoffs_pendentes() -> List[dict]:
    """
    Lista todos os handoffs com status pendente ou contacted.

    Returns:
        Lista de handoffs
    """
    try:
        response = supabase.table("external_handoffs") \
            .select("*") \
            .in_("status", ["pending", "contacted"]) \
            .order("created_at", desc=False) \
            .execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar handoffs pendentes: {e}")
        return []
```

### DoD

- [ ] Funcao `listar_handoffs_pendentes` criada
- [ ] Retorna handoffs pending e contacted
- [ ] Ordenado por criacao (mais antigos primeiro)

---

## Story 7.3: Scheduler

### Objetivo
Configurar job para rodar periodicamente.

### Arquivo: `app/workers/scheduler.py`

```python
# Adicionar ao scheduler existente:

from app.workers.handoff_processor import processar_handoffs_pendentes

# Adicionar job que roda a cada 10 minutos
@scheduler.scheduled_job('interval', minutes=10, id='handoff_processor')
async def job_processar_handoffs():
    """Job de processamento de handoffs (follow-up e expiracao)."""
    try:
        stats = await processar_handoffs_pendentes()
        logger.info(f"Handoff processor: {stats}")
    except Exception as e:
        logger.error(f"Erro no job de handoffs: {e}")
```

### DoD

- [ ] Job configurado no scheduler
- [ ] Intervalo de 10 minutos
- [ ] Logging de estatisticas

---

## Story 7.4: Testes do Job

### Arquivo: `tests/workers/test_handoff_processor.py`

```python
"""Testes para job de processamento de handoffs."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.workers.handoff_processor import (
    processar_handoffs_pendentes,
    _processar_handoff,
    FOLLOWUP_1_HORAS,
    FOLLOWUP_2_HORAS,
    EXPIRACAO_HORAS,
)


class TestProcessarHandoff:
    """Testes de processamento individual."""

    @pytest.mark.asyncio
    async def test_envia_followup_1_apos_2h(self):
        """Deve enviar follow-up 1 apos 2 horas."""
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=3)  # 3h atras
        reserved_until = now + timedelta(hours=45)  # Ainda valido

        handoff = {
            "id": "handoff-123",
            "vaga_id": "vaga-456",
            "cliente_id": "cliente-789",
            "divulgador_telefone": "11999998888",
            "divulgador_nome": "Joao",
            "created_at": created_at.isoformat(),
            "reserved_until": reserved_until.isoformat(),
            "followup_count": 0,
            "last_followup_at": None,
        }

        with patch(
            "app.workers.handoff_processor._enviar_followup",
            new_callable=AsyncMock
        ) as mock_followup:
            resultado = await _processar_handoff(handoff, now)

            assert resultado == "followup"
            mock_followup.assert_called_once_with(handoff, 1)

    @pytest.mark.asyncio
    async def test_envia_followup_2_apos_24h(self):
        """Deve enviar follow-up 2 apos 24 horas."""
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=25)
        reserved_until = now + timedelta(hours=23)

        handoff = {
            "id": "handoff-123",
            "vaga_id": "vaga-456",
            "cliente_id": "cliente-789",
            "divulgador_telefone": "11999998888",
            "divulgador_nome": "Joao",
            "created_at": created_at.isoformat(),
            "reserved_until": reserved_until.isoformat(),
            "followup_count": 1,  # Ja enviou o primeiro
            "last_followup_at": (now - timedelta(hours=22)).isoformat(),
        }

        with patch(
            "app.workers.handoff_processor._enviar_followup",
            new_callable=AsyncMock
        ) as mock_followup:
            resultado = await _processar_handoff(handoff, now)

            assert resultado == "followup"
            mock_followup.assert_called_once_with(handoff, 2)

    @pytest.mark.asyncio
    async def test_expira_apos_48h(self):
        """Deve expirar handoff apos 48 horas."""
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=49)
        reserved_until = now - timedelta(hours=1)  # Ja passou

        handoff = {
            "id": "handoff-123",
            "vaga_id": "vaga-456",
            "cliente_id": "cliente-789",
            "divulgador_telefone": "11999998888",
            "divulgador_nome": "Joao",
            "created_at": created_at.isoformat(),
            "reserved_until": reserved_until.isoformat(),
            "followup_count": 2,
            "last_followup_at": (now - timedelta(hours=24)).isoformat(),
        }

        with patch(
            "app.workers.handoff_processor._expirar_handoff",
            new_callable=AsyncMock
        ) as mock_expirar:
            resultado = await _processar_handoff(handoff, now)

            assert resultado == "expired"
            mock_expirar.assert_called_once_with(handoff)

    @pytest.mark.asyncio
    async def test_noop_se_nao_precisa_acao(self):
        """Nao deve fazer nada se ainda cedo para follow-up."""
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=1)  # Apenas 1h atras
        reserved_until = now + timedelta(hours=47)

        handoff = {
            "id": "handoff-123",
            "vaga_id": "vaga-456",
            "cliente_id": "cliente-789",
            "divulgador_telefone": "11999998888",
            "divulgador_nome": "Joao",
            "created_at": created_at.isoformat(),
            "reserved_until": reserved_until.isoformat(),
            "followup_count": 0,
            "last_followup_at": None,
        }

        resultado = await _processar_handoff(handoff, now)
        assert resultado == "noop"


class TestProcessarTodos:
    """Testes do job completo."""

    @pytest.mark.asyncio
    async def test_processa_multiplos_handoffs(self):
        """Deve processar todos os handoffs pendentes."""
        handoffs = [
            {"id": "h1", "status": "pending"},
            {"id": "h2", "status": "contacted"},
        ]

        with patch(
            "app.workers.handoff_processor.listar_handoffs_pendentes",
            new_callable=AsyncMock,
            return_value=handoffs
        ), patch(
            "app.workers.handoff_processor._processar_handoff",
            new_callable=AsyncMock,
            return_value="noop"
        ) as mock_processar:
            stats = await processar_handoffs_pendentes()

            assert stats["total_processados"] == 2
            assert mock_processar.call_count == 2
```

### DoD

- [ ] Testes de follow-up 1 (2h)
- [ ] Testes de follow-up 2 (24h)
- [ ] Testes de expiracao (48h)
- [ ] Testes de noop (sem acao necessaria)
- [ ] Testes de processamento em lote

---

## Checklist do Epico

- [ ] **S20.E07.1** - Job de processamento criado
- [ ] **S20.E07.2** - Repository atualizado
- [ ] **S20.E07.3** - Scheduler configurado
- [ ] **S20.E07.4** - Testes passando
- [ ] Follow-up 1 enviado apos 2h
- [ ] Follow-up 2 enviado apos 24h
- [ ] Expiracao apos 48h funcionando
- [ ] Vaga liberada ao expirar
- [ ] Medico notificado ao expirar
- [ ] Eventos emitidos corretamente

---

## Timeline de Follow-up

```
T+0h    : Handoff criado, msg enviada ao divulgador
T+2h    : Follow-up 1 (se nao respondeu)
T+24h   : Follow-up 2 + alerta Slack
T+36h   : Follow-up 3 (ultimo aviso)
T+48h   : Expira handoff, libera vaga, notifica medico
```

---

## Mensagens de Follow-up

### Follow-up 1 (T+2h)
```
Oi {NOME}! Tudo bem?

Conseguiu falar com o medico sobre aquele plantao?

Me avisa aqui se fechou ou nao, pra eu atualizar
```

### Follow-up 2 (T+24h)
```
Oi {NOME}!

Ainda to aguardando retorno sobre o plantao.
O medico ta interessado, me ajuda aqui?

Responde CONFIRMADO se fechou ou NAO FECHOU se nao rolou
```

### Follow-up 3 (T+36h)
```
Ultimo aviso {NOME}!

Se eu nao tiver retorno, vou liberar o medico pra outras vagas.

CONFIRMADO ou NAO FECHOU?
```

---

## Monitoramento

```sql
-- Handoffs que vao expirar nas proximas 2h
SELECT id, divulgador_nome, reserved_until, followup_count
FROM external_handoffs
WHERE status IN ('pending', 'contacted')
AND reserved_until < now() + interval '2 hours'
ORDER BY reserved_until;

-- Estatisticas de follow-ups
SELECT
    followup_count,
    COUNT(*) as total,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 3600) as horas_media
FROM external_handoffs
WHERE status IN ('confirmed', 'not_confirmed', 'expired')
GROUP BY followup_count;
```
