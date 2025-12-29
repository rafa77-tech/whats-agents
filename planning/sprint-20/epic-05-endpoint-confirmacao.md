# Epic 05: Endpoint de Confirmacao

## Objetivo

Criar endpoint HTTP para processar cliques nos links de confirmacao enviados ao divulgador.

## Contexto

O divulgador recebe links no formato:
```
https://api.revoluna.com/handoff/confirm?t=JWT_TOKEN
```

O endpoint deve:
1. Validar token JWT (assinatura, expiracao, single-use)
2. Processar acao (confirmed/not_confirmed)
3. Atualizar handoff e vaga
4. Emitir eventos
5. Retornar pagina HTML de feedback

---

## Story 5.1: Router de Handoff

### Objetivo
Criar router para endpoints de external handoff.

### Arquivo: `app/api/routes/handoff.py`

```python
"""
Endpoints para confirmacao de external handoff.

Sprint 20 - E05 - Links de confirmacao.
"""
import logging
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.services.external_handoff.tokens import (
    validar_token,
    marcar_token_usado,
)
from app.services.external_handoff.repository import (
    buscar_handoff_por_id,
    atualizar_status_handoff,
)
from app.services.external_handoff.confirmacao import processar_confirmacao
from app.services.business_events import emit_event, EventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/handoff", tags=["handoff"])


@router.get("/confirm", response_class=HTMLResponse)
async def confirmar_handoff(
    request: Request,
    t: str = Query(..., description="Token JWT de confirmacao"),
):
    """
    Processa confirmacao de handoff via link externo.

    O divulgador clica no link e esta rota:
    1. Valida o token JWT
    2. Verifica se handoff ainda esta pendente
    3. Processa a acao (confirmed/not_confirmed)
    4. Retorna pagina HTML de feedback

    Args:
        request: Request do FastAPI
        t: Token JWT

    Returns:
        HTMLResponse com pagina de feedback
    """
    # Obter IP para auditoria
    client_ip = request.client.host if request.client else None

    logger.info(f"Confirmacao de handoff recebida, IP={client_ip}")

    # Validar token
    valido, payload, erro = await validar_token(t)

    if not valido:
        logger.warning(f"Token invalido: {erro}")
        return _render_error_page(erro)

    handoff_id = payload.get("handoff_id")
    action = payload.get("action")
    jti = payload.get("jti")

    # Emitir evento de click (mesmo antes de processar)
    await emit_event(
        EventType.HANDOFF_CONFIRM_CLICKED,
        {
            "handoff_id": handoff_id,
            "action": action,
            "jti": jti[:8] if jti else None,
            "ip_address": client_ip,
        }
    )

    # Buscar handoff
    handoff = await buscar_handoff_por_id(handoff_id)
    if not handoff:
        logger.warning(f"Handoff nao encontrado: {handoff_id}")
        return _render_error_page("Ponte nao encontrada")

    # Verificar se ainda pode ser processado
    status_atual = handoff.get("status")
    if status_atual not in ("pending", "contacted"):
        logger.info(f"Handoff {handoff_id} ja processado: {status_atual}")
        return _render_already_processed_page(status_atual, action)

    # Marcar token como usado (single-use)
    token_marcado = await marcar_token_usado(
        jti=jti,
        handoff_id=handoff_id,
        action=action,
        ip_address=client_ip,
    )

    if not token_marcado:
        # Race condition: outro request ja processou
        logger.warning(f"Token ja usado (race condition): {jti[:8]}")
        return _render_already_processed_page(status_atual, action)

    # Processar confirmacao
    try:
        resultado = await processar_confirmacao(
            handoff=handoff,
            action=action,
            confirmed_by="link",
            ip_address=client_ip,
        )

        logger.info(f"Handoff {handoff_id} processado: action={action}")

        return _render_success_page(action, resultado)

    except Exception as e:
        logger.error(f"Erro ao processar confirmacao: {e}")
        return _render_error_page("Erro ao processar. Tente novamente.")


def _render_success_page(action: str, resultado: dict) -> HTMLResponse:
    """Renderiza pagina de sucesso."""
    if action == "confirmed":
        titulo = "Plantao Confirmado!"
        mensagem = "Registramos que o plantao foi fechado com sucesso."
        emoji = "check_circle"
        cor = "#10B981"  # Verde
    else:
        titulo = "Registrado!"
        mensagem = "Anotamos que o plantao nao foi fechado."
        emoji = "info"
        cor = "#F59E0B"  # Amarelo

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo} - Revoluna</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                background: {cor};
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }}
            .icon svg {{
                width: 40px;
                height: 40px;
                fill: white;
            }}
            h1 {{
                color: #1F2937;
                font-size: 24px;
                margin-bottom: 12px;
            }}
            p {{
                color: #6B7280;
                font-size: 16px;
                line-height: 1.5;
            }}
            .footer {{
                margin-top: 32px;
                padding-top: 24px;
                border-top: 1px solid #E5E7EB;
            }}
            .footer img {{
                height: 24px;
                opacity: 0.5;
            }}
            .footer p {{
                font-size: 12px;
                color: #9CA3AF;
                margin-top: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
            <h1>{titulo}</h1>
            <p>{mensagem}</p>
            <div class="footer">
                <p>Obrigado por usar a Revoluna</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)


def _render_error_page(erro: str) -> HTMLResponse:
    """Renderiza pagina de erro."""
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Erro - Revoluna</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                background: #EF4444;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }}
            .icon svg {{
                width: 40px;
                height: 40px;
                fill: white;
            }}
            h1 {{
                color: #1F2937;
                font-size: 24px;
                margin-bottom: 12px;
            }}
            p {{
                color: #6B7280;
                font-size: 16px;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </div>
            <h1>Ops!</h1>
            <p>{erro}</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=400)


def _render_already_processed_page(status: str, action: str) -> HTMLResponse:
    """Renderiza pagina quando ja foi processado."""
    status_map = {
        "confirmed": "confirmado",
        "not_confirmed": "nao fechado",
        "expired": "expirado",
    }
    status_texto = status_map.get(status, status)

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ja Processado - Revoluna</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                background: #6B7280;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }}
            .icon svg {{
                width: 40px;
                height: 40px;
                fill: white;
            }}
            h1 {{
                color: #1F2937;
                font-size: 24px;
                margin-bottom: 12px;
            }}
            p {{
                color: #6B7280;
                font-size: 16px;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
            </div>
            <h1>Ja Registrado</h1>
            <p>Este plantao ja foi marcado como <strong>{status_texto}</strong>.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
```

### DoD

- [ ] Router criado em `app/api/routes/handoff.py`
- [ ] Endpoint GET `/handoff/confirm` implementado
- [ ] Paginas HTML de feedback criadas

---

## Story 5.2: Servico de Confirmacao

### Objetivo
Criar logica de processamento da confirmacao.

### Arquivo: `app/services/external_handoff/confirmacao.py`

```python
"""
Processamento de confirmacao de handoff.

Sprint 20 - E05 - Logica de confirmacao.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.external_handoff.repository import atualizar_status_handoff
from app.services.supabase import supabase
from app.services.business_events import emit_event, EventType
from app.services.slack.notificador import notificar_slack

logger = logging.getLogger(__name__)


async def processar_confirmacao(
    handoff: dict,
    action: str,
    confirmed_by: str,
    ip_address: str = None,
) -> dict[str, Any]:
    """
    Processa confirmacao de handoff (confirmed ou not_confirmed).

    Args:
        handoff: Dados do handoff
        action: 'confirmed' ou 'not_confirmed'
        confirmed_by: 'link' ou 'keyword'
        ip_address: IP de origem (para auditoria)

    Returns:
        Dict com resultado do processamento
    """
    handoff_id = handoff["id"]
    vaga_id = handoff["vaga_id"]

    logger.info(f"Processando confirmacao: handoff={handoff_id}, action={action}")

    # Determinar novo status
    if action == "confirmed":
        novo_status_handoff = "confirmed"
        novo_status_vaga = "fechada"
        event_type = EventType.HANDOFF_CONFIRMED
    else:
        novo_status_handoff = "not_confirmed"
        novo_status_vaga = "aberta"  # Libera a vaga
        event_type = EventType.HANDOFF_NOT_CONFIRMED

    # Atualizar handoff
    await atualizar_status_handoff(
        handoff_id=handoff_id,
        novo_status=novo_status_handoff,
        confirmed_at=datetime.now(timezone.utc) if action == "confirmed" else None,
        confirmed_by=confirmed_by,
        confirmation_source=ip_address,
    )

    # Atualizar vaga
    supabase.table("vagas") \
        .update({"status": novo_status_vaga}) \
        .eq("id", vaga_id) \
        .execute()

    logger.info(f"Vaga {vaga_id} atualizada para status={novo_status_vaga}")

    # Emitir evento
    await emit_event(
        event_type,
        {
            "handoff_id": handoff_id,
            "vaga_id": vaga_id,
            "confirmed_by": confirmed_by,
            "ip_address": ip_address,
        }
    )

    # Notificar Slack
    emoji = ":white_check_mark:" if action == "confirmed" else ":x:"
    mensagem = (
        f"{emoji} *Handoff {action.upper()}*\n"
        f"Divulgador: {handoff.get('divulgador_nome')}\n"
        f"Via: {confirmed_by}\n"
        f"Vaga: {vaga_id[:8]}..."
    )
    await notificar_slack(mensagem, canal="vagas")

    # Enviar mensagem para medico via Julia
    cliente_id = handoff.get("cliente_id")
    if cliente_id:
        await _notificar_medico(cliente_id, action, handoff)

    return {
        "success": True,
        "handoff_status": novo_status_handoff,
        "vaga_status": novo_status_vaga,
    }


async def _notificar_medico(
    cliente_id: str,
    action: str,
    handoff: dict,
) -> None:
    """
    Envia mensagem para o medico sobre o resultado.

    Args:
        cliente_id: ID do medico
        action: 'confirmed' ou 'not_confirmed'
        handoff: Dados do handoff
    """
    from app.services.outbound import send_outbound_message

    divulgador_nome = handoff.get("divulgador_nome", "o divulgador")

    if action == "confirmed":
        mensagem = (
            f"Boa noticia! {divulgador_nome} confirmou seu plantao!\n\n"
            "Qualquer coisa me avisa aqui"
        )
    else:
        mensagem = (
            f"Oi! {divulgador_nome} informou que o plantao nao foi fechado.\n\n"
            "Quer que eu procure outras opcoes pra voce?"
        )

    try:
        await send_outbound_message(
            cliente_id=cliente_id,
            mensagem=mensagem,
            campanha="handoff_resultado",
        )
    except Exception as e:
        logger.error(f"Erro ao notificar medico {cliente_id}: {e}")
```

### DoD

- [ ] Funcao `processar_confirmacao` criada
- [ ] Atualiza handoff e vaga atomicamente
- [ ] Emite evento correto
- [ ] Notifica Slack
- [ ] Envia mensagem ao medico

---

## Story 5.3: Registrar Router

### Objetivo
Adicionar router ao FastAPI app.

### Arquivo: `app/main.py`

```python
# Adicionar import
from app.api.routes.handoff import router as handoff_router

# Adicionar ao include_router
app.include_router(handoff_router)
```

### DoD

- [ ] Import adicionado
- [ ] Router registrado
- [ ] Endpoint acessivel

---

## Checklist do Epico

- [ ] **S20.E05.1** - Router e endpoint criados
- [ ] **S20.E05.2** - Servico de confirmacao implementado
- [ ] **S20.E05.3** - Router registrado no app
- [ ] Token validado antes de processar
- [ ] Single-use garantido
- [ ] Paginas HTML responsivas
- [ ] Eventos emitidos corretamente
- [ ] Medico notificado do resultado

---

## Validacao Manual

```bash
# Gerar token de teste
python -c "
from app.services.external_handoff.tokens import gerar_token_confirmacao
token = gerar_token_confirmacao('handoff-id', 'confirmed')
print(f'http://localhost:8000/handoff/confirm?t={token}')
"

# Acessar URL no navegador
# Deve mostrar pagina de sucesso/erro
```
