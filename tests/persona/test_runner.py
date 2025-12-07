"""
Framework para testar respostas da Júlia.
"""
import json
import logging
from typing import Optional

from anthropic import Anthropic

from app.services.agente import gerar_resposta_julia
from app.core.config import settings

logger = logging.getLogger(__name__)

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


class PersonaTestRunner:
    """Framework para testar respostas da Júlia."""

    def __init__(self):
        self.resultados = []

    @property
    def criterios_padrao(self):
        return [
            "Usa linguagem informal (vc, pra, tá)",
            "Mensagem curta (máximo 3 linhas)",
            "Não usa bullet points ou listas",
            "Tom amigável e natural",
            "Não revela que é IA/bot",
        ]

    async def testar_resposta(
        self,
        mensagem_medico: str,
        contexto: Optional[dict] = None,
        criterios: Optional[list[str]] = None
    ) -> dict:
        """
        Testa uma resposta da Júlia.

        Args:
            mensagem_medico: O que o médico disse
            contexto: Contexto da conversa
            criterios: Lista de critérios para avaliar

        Returns:
            dict com resposta, avaliacao, score
        """
        # Criar dados mínimos de médico e conversa para teste
        medico = contexto.get("medico", {}) if contexto else {}
        if not medico:
            medico = {
                "id": "test-id",
                "primeiro_nome": medico.get("primeiro_nome", "Teste"),
                "telefone": "5511999999999"
            }

        conversa = {
            "id": "test-conversa-id",
            "cliente_id": medico.get("id", "test-id"),
            "controlled_by": "ai"
        }

        # Montar contexto completo
        contexto_completo = contexto or {}
        contexto_completo.setdefault("medico", "")
        contexto_completo.setdefault("vagas", "")
        contexto_completo.setdefault("historico", "")
        contexto_completo.setdefault("historico_raw", [])
        contexto_completo.setdefault("primeira_msg", False)
        contexto_completo.setdefault("data_hora_atual", "")
        contexto_completo.setdefault("dia_semana", "")

        try:
            # Gerar resposta da Júlia (sem tools para testes mais rápidos)
            resposta = await gerar_resposta_julia(
                mensagem=mensagem_medico,
                contexto=contexto_completo,
                medico=medico,
                conversa=conversa,
                incluir_historico=False,
                usar_tools=False  # Desabilitar tools para testes mais rápidos
            )
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            resposta = f"[ERRO: {str(e)}]"

        # Avaliar resposta
        avaliacao = await self.avaliar_resposta(
            mensagem=mensagem_medico,
            resposta=resposta,
            criterios=criterios or self.criterios_padrao
        )

        resultado = {
            "mensagem": mensagem_medico,
            "resposta": resposta,
            "avaliacao": avaliacao,
            "passou": avaliacao.get("score", 0) >= 7
        }

        self.resultados.append(resultado)
        return resultado

    async def avaliar_resposta(
        self,
        mensagem: str,
        resposta: str,
        criterios: list[str]
    ) -> dict:
        """Usa LLM para avaliar resposta."""

        prompt = f"""Avalie esta resposta de uma escalista chamada Júlia.

MENSAGEM DO MÉDICO:
{mensagem}

RESPOSTA DA JÚLIA:
{resposta}

CRITÉRIOS A AVALIAR:
{chr(10).join(f"- {c}" for c in criterios)}

Para cada critério, diga se passou (✓) ou não (✗).
Depois dê uma nota de 0 a 10.

Responda APENAS com JSON válido, sem markdown ou texto adicional:
{{
    "criterios": {{"critério": "✓ ou ✗ + explicação"}},
    "score": 0-10,
    "feedback": "feedback geral"
}}"""

        try:
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            texto = response.content[0].text.strip()
            # Remover markdown code blocks se houver
            if texto.startswith("```"):
                texto = texto.split("```")[1]
                if texto.startswith("json"):
                    texto = texto[4:]
                texto = texto.strip()

            resultado = json.loads(texto)
            return resultado
        except Exception as e:
            logger.error(f"Erro ao avaliar resposta: {e}")
            return {
                "criterios": {},
                "score": 0,
                "feedback": f"Erro na avaliação: {str(e)}"
            }

