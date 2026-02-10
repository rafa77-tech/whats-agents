"""
Agente Helena - Analytics e Gestão via Slack.

Sprint 47: Agente com capacidade de SQL dinâmico.
Helena funciona APENAS no Slack, nunca no WhatsApp.
"""

import json
import logging
from datetime import datetime

import anthropic

from app.core.config import settings
from app.services.helena.session import SessionManager
from app.services.helena.prompts import montar_prompt_helena

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5
MAX_RETRIES_INCOMPLETO = 2

# Padrões que indicam resposta incompleta
PADROES_INCOMPLETOS = [
    ":",
    "...",
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
    "consultando",
]


class AgenteHelena:
    """Agente de analytics para Slack."""

    def __init__(self, user_id: str, channel_id: str):
        """
        Inicializa agente Helena.

        Args:
            user_id: ID do usuário Slack
            channel_id: ID do canal Slack
        """
        self.user_id = user_id
        self.channel_id = channel_id
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.session = SessionManager(user_id, channel_id)
        self._tools = None

    def _get_tools(self) -> list:
        """Lazy load das tools para evitar import circular."""
        if self._tools is None:
            from app.tools.helena import HELENA_TOOLS

            self._tools = HELENA_TOOLS
        return self._tools

    async def processar_mensagem(self, texto: str) -> str:
        """
        Processa mensagem do usuário.

        Args:
            texto: Texto da mensagem (sem menção @Helena)

        Returns:
            Resposta formatada para Slack
        """
        logger.info(f"Helena processando: {texto[:100]}...")

        # Carregar sessão
        await self.session.carregar()
        self.session.adicionar_mensagem("user", texto)

        try:
            # Chamar LLM
            resposta = await self._chamar_llm()

            # Salvar sessão
            await self.session.salvar()

            return resposta

        except anthropic.APIError as e:
            logger.error(f"Erro API Anthropic: {e}")
            return "Ops, tive um problema técnico. Tenta de novo em alguns segundos?"

        except Exception as e:
            logger.exception(f"Erro ao processar mensagem Helena: {e}")
            return "Desculpa, algo deu errado. Pode repetir a pergunta?"

    async def _chamar_llm(self, retry_count: int = 0) -> str:
        """
        Chama Claude com tools.

        Args:
            retry_count: Número de retries para respostas incompletas

        Returns:
            Resposta final formatada
        """
        # Preparar contexto
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M (%A)")
        system_prompt = montar_prompt_helena(data_hora)

        # Chamar Claude
        response = self.client.messages.create(
            model=settings.LLM_MODEL,  # claude-3-5-haiku ou equivalente
            max_tokens=2048,
            system=system_prompt,
            tools=self._get_tools(),
            messages=self.session.mensagens,
        )

        return await self._processar_resposta(response, retry_count)

    async def _processar_resposta(self, response: anthropic.types.Message, retry_count: int) -> str:
        """
        Processa resposta do LLM, executando tools se necessário.

        Args:
            response: Resposta do Claude
            retry_count: Contador de retries

        Returns:
            Texto final da resposta
        """
        from app.tools.helena import executar_tool

        texto_resposta = ""
        tool_calls = []

        # Extrair texto e tool_use
        for block in response.content:
            if block.type == "text":
                texto_resposta += block.text
            elif block.type == "tool_use":
                tool_calls.append(block)

        # Se não há tools, verificar se resposta está completa
        if not tool_calls:
            if self._resposta_incompleta(texto_resposta, response.stop_reason):
                if retry_count < MAX_RETRIES_INCOMPLETO:
                    logger.debug(f"Resposta incompleta, retry {retry_count + 1}")
                    self.session.adicionar_mensagem("assistant", texto_resposta)
                    self.session.adicionar_mensagem(
                        "user",
                        "Use a tool apropriada para buscar os dados e me responda com números concretos.",
                    )
                    return await self._chamar_llm(retry_count + 1)

            self.session.adicionar_mensagem("assistant", texto_resposta)
            return texto_resposta

        # Executar tools (máximo MAX_TOOL_ITERATIONS)
        iteration = 0
        while tool_calls and iteration < MAX_TOOL_ITERATIONS:
            iteration += 1

            tool_results = []
            for tool_call in tool_calls:
                logger.info(f"Helena executando tool: {tool_call.name}")

                result = await executar_tool(
                    tool_call.name,
                    tool_call.input,
                    self.user_id,
                    self.channel_id,
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

                # Salvar no contexto para referência futura
                self.session.atualizar_contexto(
                    f"ultima_{tool_call.name}",
                    result,
                )

            # Adicionar tool calls e results ao histórico
            # Converter content blocks para formato serializável
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            self.session.adicionar_mensagem("assistant", assistant_content)
            self.session.adicionar_mensagem("user", tool_results)

            # Continuar conversa com resultados
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M (%A)")
            response = self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=2048,
                system=montar_prompt_helena(data_hora),
                tools=self._get_tools(),
                messages=self.session.mensagens,
            )

            # Extrair nova resposta
            texto_resposta = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    texto_resposta += block.text
                elif block.type == "tool_use":
                    tool_calls.append(block)

        # Resposta final
        self.session.adicionar_mensagem("assistant", texto_resposta)
        return texto_resposta

    def _resposta_incompleta(self, texto: str, stop_reason: str) -> bool:
        """Verifica se resposta parece incompleta."""
        if stop_reason == "tool_use":
            return False

        texto_lower = texto.lower().strip()
        for padrao in PADROES_INCOMPLETOS:
            if texto_lower.endswith(padrao):
                return True

        return False
