"""
Endpoints para confirmacao de external handoff.

Sprint 20 - E05 - Links de confirmacao.
Sprint 21 - E03 - Rate limiting por IP.
"""

import logging
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from app.services.external_handoff.tokens import (
    validar_token,
    marcar_token_usado,
)
from app.services.external_handoff.repository import buscar_handoff_por_id
from app.services.external_handoff.confirmacao import processar_confirmacao
from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent
from app.services.rate_limit import check_rate_limit, render_rate_limit_page

logger = logging.getLogger(__name__)

# Limites de rate limit para endpoint de confirmacao
CONFIRM_RATE_LIMIT_PER_MIN = 30
CONFIRM_RATE_LIMIT_PER_HOUR = 200

router = APIRouter(prefix="/handoff", tags=["handoff"])


@router.get("/confirm", response_class=HTMLResponse)
async def confirmar_handoff(
    request: Request,
    t: str = Query(..., description="Token JWT de confirmacao"),
):
    """
    Processa confirmacao de handoff via link externo.

    O divulgador clica no link e esta rota:
    1. Verifica rate limit por IP
    2. Valida o token JWT
    3. Verifica se handoff ainda esta pendente
    4. Processa a acao (confirmed/not_confirmed)
    5. Retorna pagina HTML de feedback

    Args:
        request: Request do FastAPI
        t: Token JWT

    Returns:
        HTMLResponse com pagina de feedback
    """
    # Obter IP para rate limit e auditoria
    # Suporte a X-Forwarded-For para proxies
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Verificar rate limit
    allowed, reason, retry_after = await check_rate_limit(
        key=f"handoff_confirm:{client_ip}",
        limit_per_minute=CONFIRM_RATE_LIMIT_PER_MIN,
        limit_per_hour=CONFIRM_RATE_LIMIT_PER_HOUR,
    )

    if not allowed:
        logger.warning(
            f"Rate limit atingido: IP={client_ip}, reason={reason}, retry={retry_after}s"
        )
        return HTMLResponse(
            content=render_rate_limit_page(retry_after),
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

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
    event = BusinessEvent(
        event_type=EventType.HANDOFF_CONFIRM_CLICKED,
        source=EventSource.BACKEND,
        event_props={
            "handoff_id": handoff_id,
            "action": action,
            "jti": jti[:8] if jti else None,
            "ip_address": client_ip,
        },
        dedupe_key=f"handoff_click:{jti}",
    )
    await emit_event(event)

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
        cor = "#10B981"  # Verde
    else:
        titulo = "Registrado!"
        mensagem = "Anotamos que o plantao nao foi fechado."
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
