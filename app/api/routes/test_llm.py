"""
Rotas de teste para validar LLM.
Remover em producao.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.llm import gerar_resposta
from app.core.prompts import montar_prompt_julia
from app.services.agente import gerar_resposta_julia

router = APIRouter(prefix="/test", tags=["Test"])


class MensagemRequest(BaseModel):
    mensagem: str
    usar_persona: bool = True


class JuliaRequest(BaseModel):
    mensagem: str
    nome_medico: Optional[str] = "Carlos"
    especialidade: Optional[str] = "Anestesiologista"
    primeira_msg: bool = False


@router.post("/llm/resposta")
async def test_llm_resposta(request: MensagemRequest):
    """Testa geracao de resposta."""
    try:
        system = montar_prompt_julia() if request.usar_persona else None
        resposta = await gerar_resposta(
            mensagem=request.mensagem,
            system_prompt=system,
        )
        return {
            "status": "ok",
            "mensagem_entrada": request.mensagem,
            "resposta": resposta,
            "persona_ativa": request.usar_persona,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro LLM: {str(e)}")


@router.post("/llm/julia")
async def test_julia_resposta(request: JuliaRequest):
    """
    Testa resposta da Julia com contexto completo.

    Simula uma conversa real com contexto de medico.
    """
    try:
        # Montar contexto simulado
        contexto = {
            "medico": f"Nome: Dr(a) {request.nome_medico}\nEspecialidade: {request.especialidade}",
            "historico": "Nenhuma mensagem anterior." if request.primeira_msg else "",
            "historico_raw": [],
            "vagas": "",
            "primeira_msg": request.primeira_msg,
        }

        resposta = await gerar_resposta_julia(
            mensagem=request.mensagem,
            contexto=contexto,
            incluir_historico=False
        )

        return {
            "status": "ok",
            "mensagem_entrada": request.mensagem,
            "resposta_julia": resposta,
            "contexto_usado": {
                "medico": request.nome_medico,
                "especialidade": request.especialidade,
                "primeira_msg": request.primeira_msg,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Julia: {str(e)}")


@router.get("/llm/health")
async def test_llm_health():
    """Testa se LLM esta respondendo."""
    try:
        resposta = await gerar_resposta(
            mensagem="Diga apenas: OK",
            system_prompt="Responda exatamente o que foi pedido.",
        )
        return {
            "status": "healthy",
            "resposta": resposta,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")
