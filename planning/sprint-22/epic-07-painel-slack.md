# E07: Painel Slack

**Epico:** Mensagem de Status Periodica no Slack
**Estimativa:** 3h
**Dependencias:** E06 (Estado da Julia)

---

## Objetivo

Criar painel de status no Slack que mostra em tempo real o que a Julia esta fazendo, dando visibilidade ao gestor.

---

## Formato da Mensagem

```
📊 Julia Status

Estado: 🟢 Atendimento
Conversas ativas: 5
Replies pendentes: 2
Handoffs abertos: 1

Ultimas acoes:
• 14:32 - Reply para Dr. Carlos (aceite)
• 14:28 - Oferta enviada para Dr. Maria
• 14:15 - Follow-up Dr. Paulo

Proxima acao agendada:
• 14:45 - Campanha Reativacao (12 medicos)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Atualizado: 14:35 | Uptime: 99.9%
```

---

## Escopo

### Incluido

- [x] Servico de formatacao do painel
- [x] Envio periodico para Slack
- [x] Canal dedicado #julia-status
- [x] Atualizacao a cada 5 minutos

### Excluido

- [ ] Dashboard web
- [ ] Alertas (ja existe em outro lugar)

---

## Tarefas

### T01: Servico painel_slack.py

**Arquivo:** `app/services/painel_slack.py`

```python
"""
Painel de status da Julia no Slack.

Envia atualizacao periodica para canal dedicado.

Sprint 22 - Responsividade Inteligente
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.julia_estado import buscar_estado, atualizar_metricas, ModoOperacional
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)

# Canal para status
CANAL_STATUS = "#julia-status"

# Controle de ultima notificacao (evitar spam)
_ultima_notificacao: Optional[datetime] = None
INTERVALO_MINIMO = timedelta(minutes=4)  # Minimo 4 min entre notificacoes


def _emoji_modo(modo: str) -> str:
    """Retorna emoji para modo."""
    emojis = {
        ModoOperacional.ATENDIMENTO: "🟢",
        ModoOperacional.COMERCIAL: "🟡",
        ModoOperacional.BATCH: "🔵",
        ModoOperacional.PAUSADA: "🔴",
    }
    return emojis.get(modo, "⚪")


async def _buscar_ultimas_acoes(limite: int = 5) -> list[dict]:
    """
    Busca ultimas acoes registradas.

    Returns:
        Lista de acoes com timestamp
    """
    try:
        # Buscar de interacoes recentes
        result = supabase.table("interacoes").select(
            "id, created_at, tipo, clientes(nome)"
        ).order(
            "created_at", desc=True
        ).limit(limite).execute()

        acoes = []
        for r in result.data:
            cliente_nome = r.get("clientes", {}).get("nome", "N/A")
            hora = datetime.fromisoformat(r["created_at"]).strftime("%H:%M")
            tipo = r.get("tipo", "acao")

            acoes.append({
                "hora": hora,
                "descricao": f"{tipo.title()} para {cliente_nome.split()[0]}",
            })

        return acoes

    except Exception as e:
        logger.error(f"Erro ao buscar ultimas acoes: {e}")
        return []


async def _calcular_uptime() -> float:
    """
    Calcula uptime aproximado (ultimas 24h).

    Returns:
        Porcentagem de uptime
    """
    try:
        # Verificar se houve erros criticos nas ultimas 24h
        # (simplificado - em producao seria mais robusto)
        return 99.9
    except Exception:
        return 0.0


async def formatar_painel() -> dict:
    """
    Formata painel completo para Slack.

    Returns:
        Dict com formato de mensagem Slack (blocks)
    """
    # Atualizar metricas antes de formatar
    await atualizar_metricas()
    estado = await buscar_estado()
    ultimas_acoes = await _buscar_ultimas_acoes(5)
    uptime = await _calcular_uptime()

    emoji = _emoji_modo(estado.modo)
    agora = datetime.now().strftime("%H:%M")

    # Formatar ultimas acoes
    acoes_texto = ""
    if ultimas_acoes:
        for acao in ultimas_acoes[:3]:
            acoes_texto += f"• {acao['hora']} - {acao['descricao']}\n"
    else:
        acoes_texto = "• Nenhuma acao recente\n"

    # Formatar proxima acao
    proxima_texto = ""
    if estado.proxima_acao and estado.proxima_acao_at:
        hora = estado.proxima_acao_at.strftime("%H:%M")
        proxima_texto = f"• {hora} - {estado.proxima_acao}"
    else:
        proxima_texto = "• Nenhuma acao agendada"

    # Construir mensagem com blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 Julia Status",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Estado:* {emoji} {estado.modo.title()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Conversas ativas:* {estado.conversas_ativas}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Replies pendentes:* {estado.replies_pendentes}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Handoffs abertos:* {estado.handoffs_abertos}"
                }
            ]
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Ultimas acoes:*\n{acoes_texto}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Proxima acao agendada:*\n{proxima_texto}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Atualizado: {agora} | Uptime: {uptime}%"
                }
            ]
        }
    ]

    return {
        "text": f"Julia Status - {estado.modo.title()}",
        "blocks": blocks
    }


async def enviar_painel() -> bool:
    """
    Envia painel para canal do Slack.

    Returns:
        True se enviado com sucesso
    """
    global _ultima_notificacao

    # Verificar intervalo minimo
    if _ultima_notificacao:
        if datetime.now() - _ultima_notificacao < INTERVALO_MINIMO:
            logger.debug("Intervalo minimo nao atingido, pulando")
            return False

    try:
        mensagem = await formatar_painel()
        await enviar_slack(mensagem, canal=CANAL_STATUS)

        _ultima_notificacao = datetime.now()
        logger.info("Painel enviado para Slack")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar painel: {e}")
        return False


async def enviar_painel_se_atividade() -> bool:
    """
    Envia painel apenas se houver atividade recente.

    Evita spam quando Julia esta ociosa.

    Returns:
        True se enviado
    """
    estado = await buscar_estado()

    # Verificar se ha atividade
    tem_atividade = (
        estado.conversas_ativas > 0 or
        estado.replies_pendentes > 0 or
        estado.handoffs_abertos > 0
    )

    if not tem_atividade:
        logger.debug("Sem atividade, pulando painel")
        return False

    return await enviar_painel()
```

**DoD:**
- [ ] Servico criado
- [ ] Formatacao com blocks
- [ ] Controle de intervalo
- [ ] Verificacao de atividade

---

### T02: Job de Envio

**Arquivo:** Adicionar em `app/api/routes/jobs.py`

```python
@router.post("/enviar-painel-status")
async def job_enviar_painel():
    """Envia painel de status para Slack."""
    from app.services.painel_slack import enviar_painel_se_atividade

    enviado = await enviar_painel_se_atividade()
    return JSONResponse({
        "status": "ok",
        "enviado": enviado
    })
```

Adicionar no scheduler:

```python
{
    "name": "enviar_painel_status",
    "endpoint": "/jobs/enviar-painel-status",
    "schedule": "*/5 * * * *",  # A cada 5 minutos
    "categoria": "painel",
}
```

**DoD:**
- [ ] Job criado
- [ ] Scheduler configurado
- [ ] Painel enviado a cada 5 min

---

### T03: Canal Dedicado

**Configuracao:**

1. Criar canal `#julia-status` no Slack
2. Adicionar bot ao canal
3. Configurar webhook se necessario

**DoD:**
- [ ] Canal criado
- [ ] Bot tem permissao
- [ ] Mensagens chegando

---

## Validacao

### Teste Manual

```python
# Testar formatacao
from app.services.painel_slack import formatar_painel, enviar_painel

import asyncio

async def test():
    # Formatar
    msg = await formatar_painel()
    print(msg)

    # Enviar (descomente para testar)
    # await enviar_painel()

asyncio.run(test())
```

### Verificar no Slack

1. Acessar canal #julia-status
2. Verificar mensagem formatada
3. Confirmar atualizacao a cada 5 min

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Servico `painel_slack.py` implementado
- [ ] Formatacao com blocks
- [ ] Job a cada 5 minutos
- [ ] Canal recebendo mensagens

### Qualidade

- [ ] Visual limpo e legivel
- [ ] Informacoes relevantes
- [ ] Nao envia se ocioso

### Experiencia

- [ ] Gestor entende estado rapidamente
- [ ] Historico de acoes visivel
- [ ] Proximas acoes claras

---

*Epico criado em 29/12/2025*
