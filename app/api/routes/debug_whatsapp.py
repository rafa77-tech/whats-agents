"""
Rotas de teste para validar WhatsApp.
Remover em producao.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.whatsapp import evolution, enviar_whatsapp, mostrar_digitando

router = APIRouter(prefix="/test", tags=["Test"])


class MensagemWhatsAppRequest(BaseModel):
    telefone: str
    texto: str


@router.get("/whatsapp/status")
async def test_whatsapp_status():
    """Verifica status da conexao WhatsApp."""
    try:
        status = await evolution.verificar_conexao()
        return {
            "status": "ok",
            "conexao": status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")


@router.post("/whatsapp/enviar")
async def test_enviar_mensagem(request: MensagemWhatsAppRequest):
    """
    Envia mensagem de teste.
    CUIDADO: Isso envia mensagem real!
    """
    try:
        # Mostrar digitando primeiro
        await mostrar_digitando(request.telefone)

        # Enviar mensagem
        resultado = await enviar_whatsapp(request.telefone, request.texto)

        return {
            "status": "enviado",
            "telefone": request.telefone,
            "resultado": resultado,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
