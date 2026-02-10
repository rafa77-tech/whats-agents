"""
Agente Julia para Slack.

Orquestrador principal que usa SessionManager e ToolExecutor.
Sprint 10 - S10.E2.2
"""

import json
import logging
from datetime import datetime, timezone

import anthropic

from app.core.config import settings
from app.tools.slack import SLACK_TOOLS
from app.services.slack.session import SessionManager
from app.services.slack.tool_executor import ToolExecutor
from app.services.slack.prompts import SYSTEM_PROMPT_AGENTE
from app.services.slack.formatter import formatar_erro

logger = logging.getLogger(__name__)


# Padrões que indicam resposta incompleta (LLM ia continuar mas parou)
PADROES_INCOMPLETO = [
    ":",  # "Vou verificar o que temos na semana:"
    "...",  # Reticências
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
]

# Máximo de retries para respostas incompletas
MAX_RETRIES_INCOMPLETO = 2


class AgenteSlack:
    """Agente conversacional da Julia para Slack."""

    def __init__(self, user_id: str, channel_id: str):
        """
        Inicializa o agente.

        Args:
            user_id: ID do usuario Slack
            channel_id: ID do canal Slack
        """
        self.user_id = user_id
        self.channel_id = channel_id
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.session = SessionManager(user_id, channel_id)
        self.executor = ToolExecutor(user_id, channel_id)

    # =========================================================================
    # PROPRIEDADES DE COMPATIBILIDADE (backward compat para testes)
    # =========================================================================

    @property
    def mensagens(self) -> list:
        """Backward compat: acesso a session.mensagens."""
        return self.session.mensagens

    @mensagens.setter
    def mensagens(self, value: list) -> None:
        """Backward compat: setar session.mensagens."""
        self.session.mensagens = value

    @property
    def sessao(self):
        """Backward compat: acesso a session.sessao."""
        return self.session.sessao

    @sessao.setter
    def sessao(self, value) -> None:
        """Backward compat: setar session.sessao."""
        self.session.sessao = value

    async def _carregar_sessao(self):
        """Backward compat: chama session.carregar()."""
        return await self.session.carregar()

    async def _criar_sessao(self):
        """Backward compat: chama session.criar()."""
        return await self.session.criar()

    async def _salvar_sessao(self):
        """Backward compat: chama session.salvar()."""
        return await self.session.salvar()

    def _gerar_preview_confirmacao(self, tool_name: str, tool_input: dict) -> str:
        """Backward compat: chama executor.gerar_preview()."""
        return self.executor.gerar_preview(tool_name, tool_input)

    def _formatar_sucesso(self, tool_name: str, result: dict) -> str:
        """Backward compat: chama executor.formatar_sucesso()."""
        return self.executor.formatar_sucesso(tool_name, result)

    def _formatar_resultado_direto(self, tool_results: list) -> str:
        """Backward compat: chama executor.formatar_resultado()."""
        return self.executor.formatar_resultado(tool_results)

    async def processar_mensagem(self, texto: str) -> str:
        """
        Processa mensagem do gestor e retorna resposta.

        Args:
            texto: Mensagem do gestor

        Returns:
            Resposta da Julia
        """
        # Carregar ou criar sessao
        await self.session.carregar()

        # Adicionar mensagem do usuario ao historico
        self.session.adicionar_mensagem("user", texto)

        # Verificar se eh confirmacao de acao pendente
        if self.session.get_acao_pendente():
            resposta = await self._processar_confirmacao(texto)
            if resposta:
                return resposta

        # Verificar se tem briefing aguardando aprovacao
        resposta_briefing = await self._verificar_briefing_pendente(texto)
        if resposta_briefing:
            await self.session.salvar()
            return resposta_briefing

        # Chamar LLM com tools
        resposta = await self._chamar_llm()

        # Salvar sessao atualizada
        await self.session.salvar()

        return resposta

    async def _chamar_llm(self, retry_count: int = 0) -> str:
        """
        Chama o LLM com as tools disponiveis.

        Args:
            retry_count: Número de retries já realizados (para respostas incompletas)
        """
        # Preparar contexto
        contexto = self._preparar_contexto()

        # System prompt com contexto
        system = SYSTEM_PROMPT_AGENTE.format(contexto=contexto)

        try:
            # Primeira chamada
            response = self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=1024,
                system=system,
                tools=SLACK_TOOLS,
                messages=self.session.mensagens,
            )

            # Processar resposta (pode ter tool_use)
            return await self._processar_resposta(response, retry_count)

        except anthropic.APIError as e:
            logger.error(f"Erro na API Anthropic: {e}")
            return "Ops, tive um problema aqui. Tenta de novo?"

    def _resposta_parece_incompleta(self, texto: str, stop_reason: str) -> bool:
        """
        Detecta se a resposta do LLM parece incompleta.

        Isso acontece quando o LLM gera texto que parece indicar
        que vai continuar (ex: "Vou verificar:") mas para sem
        emitir tool_use.

        Args:
            texto: Texto da resposta
            stop_reason: Razão da parada (end_turn, tool_use, etc)

        Returns:
            True se parece incompleta
        """
        if not texto or stop_reason == "tool_use":
            return False

        texto_lower = texto.lower().strip()

        # Verificar padrões que indicam resposta incompleta
        for padrao in PADROES_INCOMPLETO:
            if texto_lower.endswith(padrao):
                logger.warning(
                    f"Resposta parece incompleta: termina com '{padrao}' "
                    f"(stop_reason={stop_reason})"
                )
                return True

        return False

    async def _processar_resposta(self, response, retry_count: int = 0) -> str:
        """
        Processa resposta do LLM, executando tools se necessario.

        Args:
            response: Resposta da API Anthropic
            retry_count: Número de retries já realizados

        Returns:
            Texto final para o usuario
        """
        # Coletar partes da resposta
        texto_resposta = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                texto_resposta += block.text
            elif block.type == "tool_use":
                tool_calls.append(block)

        # Verificar stop_reason
        stop_reason = getattr(response, "stop_reason", "unknown")

        # Se nao tem tool calls, verificar se resposta está incompleta
        if not tool_calls:
            # Detectar resposta incompleta e fazer retry
            if self._resposta_parece_incompleta(texto_resposta, stop_reason):
                if retry_count < MAX_RETRIES_INCOMPLETO:
                    logger.info(
                        f"Resposta incompleta detectada, fazendo retry "
                        f"({retry_count + 1}/{MAX_RETRIES_INCOMPLETO})"
                    )

                    # Adicionar resposta parcial e pedir continuação
                    self.session.adicionar_mensagem("assistant", texto_resposta)
                    self.session.adicionar_mensagem(
                        "user",
                        "Use a tool apropriada para buscar os dados e me responda com os números.",
                    )

                    # Retry
                    return await self._chamar_llm(retry_count + 1)
                else:
                    # Retry já foi feito mas ainda está incompleto
                    # Retornar mensagem de fallback
                    logger.warning(
                        f"Resposta ainda incompleta após {retry_count} retry(s), usando fallback"
                    )
                    fallback = (
                        "Desculpa, tive um probleminha pra buscar esses dados. "
                        "Tenta perguntar de novo de forma mais específica?"
                    )
                    self.session.adicionar_mensagem("assistant", fallback)
                    return fallback

            # Resposta normal
            self.session.adicionar_mensagem("assistant", texto_resposta)
            return texto_resposta

        # Processar tool calls
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input
            tool_id = tool_call.id

            # Verificar se eh acao critica que precisa confirmacao
            if self.executor.is_tool_critica(tool_name, tool_input):
                # Guardar acao pendente e pedir confirmacao
                self.session.set_acao_pendente(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_id": tool_id,
                        "preview": texto_resposta,
                    }
                )
                # Retornar preview pedindo confirmacao
                return (
                    texto_resposta
                    if texto_resposta
                    else self.executor.gerar_preview(tool_name, tool_input)
                )

            # Executar tool
            result = await self.executor.executar(tool_name, tool_input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

            # Salvar no contexto
            self.session.atualizar_contexto(f"ultimo_{tool_name}", result)

        # Adicionar resposta do assistant com tool_use
        self.session.adicionar_mensagem("assistant", response.content)

        # Adicionar resultados das tools
        self.session.adicionar_mensagem("user", tool_results)

        # Chamar LLM novamente para formatar resposta
        try:
            final_response = self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT_AGENTE.format(contexto=self._preparar_contexto()),
                tools=SLACK_TOOLS,
                messages=self.session.mensagens,
            )

            # Extrair texto da resposta final
            texto_final = ""
            for block in final_response.content:
                if block.type == "text":
                    texto_final += block.text

            self.session.adicionar_mensagem("assistant", texto_final)
            return texto_final

        except Exception as e:
            logger.error(f"Erro ao formatar resposta: {e}")
            # Retornar resultado direto se falhar
            return self.executor.formatar_resultado(tool_results)

    async def _processar_confirmacao(self, texto: str) -> str | None:
        """
        Processa resposta de confirmacao do usuario.

        Args:
            texto: Mensagem do usuario

        Returns:
            Resposta se foi confirmacao, None se nao
        """
        texto_lower = texto.lower().strip()
        acao = self.session.get_acao_pendente()

        if not acao:
            return None

        # Palavras de confirmacao
        confirmacoes = [
            "sim",
            "s",
            "yes",
            "y",
            "ok",
            "pode",
            "manda",
            "envia",
            "blz",
            "beleza",
            "confirma",
            "confirmo",
        ]
        cancelamentos = ["nao", "n", "no", "cancela", "para", "nope", "deixa"]

        eh_confirmacao = any(c in texto_lower for c in confirmacoes)
        eh_cancelamento = any(c in texto_lower for c in cancelamentos)

        if eh_confirmacao:
            # Executar acao pendente
            result = await self.executor.executar(acao["tool_name"], acao["tool_input"])

            # Limpar acao pendente
            self.session.set_acao_pendente(None)

            # Salvar no contexto
            self.session.atualizar_contexto(f"ultimo_{acao['tool_name']}", result)

            # Formatar resposta de sucesso ou erro amigavel
            if result.get("success"):
                return self.executor.formatar_sucesso(acao["tool_name"], result)
            else:
                return formatar_erro(result.get("error", "erro desconhecido"))

        elif eh_cancelamento:
            self.session.set_acao_pendente(None)
            return "Blz, cancelado!"

        # Nao foi confirmacao nem cancelamento, continuar conversa normal
        return None

    async def _verificar_briefing_pendente(self, texto: str) -> str | None:
        """
        Verifica se tem briefing aguardando aprovacao e processa resposta.

        Args:
            texto: Mensagem do usuario

        Returns:
            Resposta se processou briefing, None se nao tinha pendente
        """
        try:
            from app.services.briefing_aprovacao import get_aprovacao_service, StatusAprovacao

            service = get_aprovacao_service()
            briefing = await service.buscar_pendente(self.channel_id)

            if not briefing:
                return None

            # Tem briefing pendente - processar resposta
            logger.info(f"Briefing pendente encontrado: {briefing.doc_nome}")

            status, mensagem = await service.processar_resposta(briefing, texto)

            # Se foi aprovado, guardar no contexto
            if status == StatusAprovacao.APROVADO:
                self.session.atualizar_contexto(
                    "briefing_aprovado",
                    {"id": briefing.id, "doc_nome": briefing.doc_nome, "doc_id": briefing.doc_id},
                )

            return mensagem

        except Exception as e:
            logger.error(f"Erro ao verificar briefing pendente: {e}")
            return None

    def _preparar_contexto(self) -> str:
        """Prepara contexto para o system prompt."""
        partes = []

        # Data/hora atual
        agora = datetime.now(timezone.utc)
        partes.append(f"Data/hora: {agora.strftime('%d/%m/%Y %H:%M')} UTC")

        # Resultados anteriores relevantes
        contexto = self.session.get_contexto()

        if "ultimo_buscar_metricas" in contexto:
            metricas = contexto["ultimo_buscar_metricas"]
            if metricas.get("success"):
                m = metricas.get("metricas", {})
                partes.append(
                    f"Ultima busca de metricas: {m.get('respostas', 0)} "
                    f"respostas de {m.get('enviadas', 0)} envios"
                )

        if "ultimo_listar_medicos" in contexto:
            lista = contexto["ultimo_listar_medicos"]
            if lista.get("success"):
                medicos = lista.get("medicos", [])
                if medicos:
                    nomes = ", ".join([m.get("nome", "?") for m in medicos[:5]])
                    partes.append(f"Ultima lista de medicos: {nomes}")

        if "ultimo_buscar_vagas" in contexto:
            vagas = contexto["ultimo_buscar_vagas"]
            if vagas.get("success"):
                partes.append(f"Vagas encontradas: {vagas.get('total', 0)}")

        return "\n".join(partes) if partes else "Inicio de sessao"


# =============================================================================
# FUNCAO PRINCIPAL
# =============================================================================


async def processar_mensagem_slack(texto: str, channel: str, user: str) -> str:
    """
    Processa mensagem do Slack usando o agente.

    Args:
        texto: Texto da mensagem
        channel: ID do canal
        user: ID do usuario

    Returns:
        Resposta da Julia
    """
    agente = AgenteSlack(user_id=user, channel_id=channel)
    return await agente.processar_mensagem(texto)
