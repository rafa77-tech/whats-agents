"""
Agente Julia para Slack.

Interpreta mensagens em linguagem natural e executa acoes
usando tools de gestao.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import anthropic

from app.core.config import settings
from app.services.supabase import supabase
from app.tools.slack_tools import SLACK_TOOLS, TOOLS_CRITICAS, executar_tool
from app.services import slack_formatter as fmt
from app.services.tipos_abordagem import TipoAbordagem, inferir_tipo, descrever_tipo

logger = logging.getLogger(__name__)

# Timeout de sessao em minutos
SESSION_TIMEOUT_MINUTES = 30


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Voce eh a Julia, escalista virtual da Revoluna. O gestor esta conversando com voce pelo Slack para gerenciar medicos e plantoes.

## Sua Personalidade
- Voce eh uma colega de trabalho, nao um assistente formal
- Use portugues informal: "vc", "pra", "ta", "blz"
- Seja concisa - respostas curtas e diretas
- Use emoji com moderacao (1-2 por conversa no maximo)
- Responda como se estivesse conversando ao lado do gestor no escritorio

## Suas Capacidades
Voce tem acesso a ferramentas para:
- Enviar mensagens WhatsApp para medicos
- Consultar metricas e dados de performance
- Buscar informacoes de medicos
- Bloquear/desbloquear medicos
- Consultar e reservar vagas
- Ver status do sistema e handoffs

## Regras Importantes

1. **Acoes Criticas** - Para acoes que modificam dados, SEMPRE:
   - Mostre um preview claro do que vai fazer
   - Peca confirmacao explicita ("posso enviar?", "confirma?")
   - So execute apos o gestor confirmar

2. **Acoes de Leitura** - Para consultas, execute direto:
   - Buscar metricas
   - Listar medicos
   - Ver status
   - Buscar vagas

3. **Dados Reais** - NUNCA invente dados:
   - Use as ferramentas para buscar informacoes
   - Se nao encontrar, diga que nao encontrou

4. **Respostas** - Formate bem:
   - Use *negrito* para destaques
   - Use listas com • para itens
   - Limite listas a 5-7 itens
   - Para mais itens, pergunte se quer ver mais

5. **Contexto** - Use o historico da conversa:
   - Resolva referencias ("ele", "esse medico", "a vaga")
   - Lembre de resultados anteriores da sessao

## Exemplos de Respostas

Ao enviar mensagem (antes de confirmar):
"Vou mandar essa msg pro 11999887766:

> Oi Dr Carlos! Tudo bem?...

Posso enviar?"

Ao mostrar metricas:
"Hoje tivemos 12 respostas de 45 envios (27%)
• 8 interessados
• 3 neutros
• 1 opt-out"

Quando nao entender:
"Nao entendi bem... vc quer que eu:
1. Mande msg pro medico?
2. Busque info sobre ele?"

## Contexto Atual
{contexto}"""


# =============================================================================
# CLASSE DO AGENTE
# =============================================================================

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
        self.sessao = None
        self.mensagens = []

    async def processar_mensagem(self, texto: str) -> str:
        """
        Processa mensagem do gestor e retorna resposta.

        Args:
            texto: Mensagem do gestor

        Returns:
            Resposta da Julia
        """
        # Carregar ou criar sessao
        await self._carregar_sessao()

        # Adicionar mensagem do usuario ao historico
        self.mensagens.append({
            "role": "user",
            "content": texto
        })

        # Verificar se eh confirmacao de acao pendente
        if self.sessao and self.sessao.get("acao_pendente"):
            resposta = await self._processar_confirmacao(texto)
            if resposta:
                return resposta

        # Chamar LLM com tools
        resposta = await self._chamar_llm()

        # Salvar sessao atualizada
        await self._salvar_sessao()

        return resposta

    async def _carregar_sessao(self):
        """Carrega sessao existente ou cria nova."""
        try:
            result = supabase.table("slack_sessoes").select("*").eq(
                "user_id", self.user_id
            ).eq("channel_id", self.channel_id).execute()

            if result.data:
                sessao = result.data[0]
                expires_at = datetime.fromisoformat(sessao["expires_at"].replace("Z", "+00:00"))

                # Verificar se expirou
                if expires_at > datetime.now(timezone.utc):
                    self.sessao = sessao
                    self.mensagens = sessao.get("mensagens", [])
                    logger.info(f"Sessao carregada para {self.user_id}")
                else:
                    # Sessao expirada, criar nova
                    await self._criar_sessao()
            else:
                await self._criar_sessao()

        except Exception as e:
            logger.error(f"Erro ao carregar sessao: {e}")
            await self._criar_sessao()

    async def _criar_sessao(self):
        """Cria nova sessao."""
        self.sessao = {
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "mensagens": [],
            "contexto": {},
            "acao_pendente": None
        }
        self.mensagens = []
        logger.info(f"Nova sessao criada para {self.user_id}")

    async def _salvar_sessao(self):
        """Salva sessao no banco."""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

            # Limitar historico a ultimas 20 mensagens
            mensagens_limitadas = self.mensagens[-20:] if len(self.mensagens) > 20 else self.mensagens

            data = {
                "user_id": self.user_id,
                "channel_id": self.channel_id,
                "mensagens": mensagens_limitadas,
                "contexto": self.sessao.get("contexto", {}),
                "acao_pendente": self.sessao.get("acao_pendente"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat()
            }

            # Upsert
            supabase.table("slack_sessoes").upsert(
                data,
                on_conflict="user_id,channel_id"
            ).execute()

        except Exception as e:
            logger.error(f"Erro ao salvar sessao: {e}")

    async def _chamar_llm(self) -> str:
        """Chama o LLM com as tools disponiveis."""
        # Preparar contexto
        contexto = self._preparar_contexto()

        # System prompt com contexto
        system = SYSTEM_PROMPT.format(contexto=contexto)

        try:
            # Primeira chamada
            response = self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=1024,
                system=system,
                tools=SLACK_TOOLS,
                messages=self.mensagens
            )

            # Processar resposta (pode ter tool_use)
            return await self._processar_resposta(response)

        except anthropic.APIError as e:
            logger.error(f"Erro na API Anthropic: {e}")
            return "Ops, tive um problema aqui. Tenta de novo?"

    async def _processar_resposta(self, response) -> str:
        """
        Processa resposta do LLM, executando tools se necessario.

        Args:
            response: Resposta da API Anthropic

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

        # Se nao tem tool calls, retornar texto
        if not tool_calls:
            self.mensagens.append({
                "role": "assistant",
                "content": texto_resposta
            })
            return texto_resposta

        # Processar tool calls
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input
            tool_id = tool_call.id

            logger.info(f"Tool call: {tool_name} com params {tool_input}")

            # Verificar se eh acao critica que precisa confirmacao
            if tool_name in TOOLS_CRITICAS:
                # Guardar acao pendente e pedir confirmacao
                self.sessao["acao_pendente"] = {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_id": tool_id,
                    "preview": texto_resposta
                }
                # Retornar preview pedindo confirmacao
                return texto_resposta if texto_resposta else self._gerar_preview_confirmacao(tool_name, tool_input)

            # Executar tool
            result = await executar_tool(tool_name, tool_input, self.user_id)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(result, ensure_ascii=False)
            })

            # Salvar no contexto
            self.sessao["contexto"][f"ultimo_{tool_name}"] = result

        # Adicionar resposta do assistant com tool_use
        self.mensagens.append({
            "role": "assistant",
            "content": response.content
        })

        # Adicionar resultados das tools
        self.mensagens.append({
            "role": "user",
            "content": tool_results
        })

        # Chamar LLM novamente para formatar resposta
        try:
            final_response = self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT.format(contexto=self._preparar_contexto()),
                tools=SLACK_TOOLS,
                messages=self.mensagens
            )

            # Extrair texto da resposta final
            texto_final = ""
            for block in final_response.content:
                if block.type == "text":
                    texto_final += block.text

            self.mensagens.append({
                "role": "assistant",
                "content": texto_final
            })

            return texto_final

        except Exception as e:
            logger.error(f"Erro ao formatar resposta: {e}")
            # Retornar resultado direto se falhar
            return self._formatar_resultado_direto(tool_results)

    async def _processar_confirmacao(self, texto: str) -> str | None:
        """
        Processa resposta de confirmacao do usuario.

        Args:
            texto: Mensagem do usuario

        Returns:
            Resposta se foi confirmacao, None se nao
        """
        texto_lower = texto.lower().strip()
        acao = self.sessao.get("acao_pendente")

        if not acao:
            return None

        # Palavras de confirmacao
        confirmacoes = ["sim", "s", "yes", "y", "ok", "pode", "manda", "envia", "blz", "beleza", "confirma", "confirmo"]
        cancelamentos = ["nao", "n", "no", "cancela", "para", "nope", "deixa"]

        eh_confirmacao = any(c in texto_lower for c in confirmacoes)
        eh_cancelamento = any(c in texto_lower for c in cancelamentos)

        if eh_confirmacao:
            # Executar acao pendente
            result = await executar_tool(
                acao["tool_name"],
                acao["tool_input"],
                self.user_id
            )

            # Limpar acao pendente
            self.sessao["acao_pendente"] = None

            # Salvar no contexto
            self.sessao["contexto"][f"ultimo_{acao['tool_name']}"] = result

            # Formatar resposta de sucesso ou erro amigavel
            if result.get("success"):
                return self._formatar_sucesso(acao["tool_name"], result)
            else:
                return fmt.formatar_erro(result.get("error", "erro desconhecido"))

        elif eh_cancelamento:
            self.sessao["acao_pendente"] = None
            return "Blz, cancelado!"

        # Nao foi confirmacao nem cancelamento, continuar conversa normal
        return None

    def _preparar_contexto(self) -> str:
        """Prepara contexto para o system prompt."""
        partes = []

        # Data/hora atual
        agora = datetime.now(timezone.utc)
        partes.append(f"Data/hora: {agora.strftime('%d/%m/%Y %H:%M')} UTC")

        # Resultados anteriores relevantes
        contexto = self.sessao.get("contexto", {}) if self.sessao else {}

        if "ultimo_buscar_metricas" in contexto:
            metricas = contexto["ultimo_buscar_metricas"]
            if metricas.get("success"):
                m = metricas.get("metricas", {})
                partes.append(f"Ultima busca de metricas: {m.get('respostas', 0)} respostas de {m.get('enviadas', 0)} envios")

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

    def _gerar_preview_confirmacao(self, tool_name: str, tool_input: dict) -> str:
        """Gera preview para pedir confirmacao."""
        if tool_name == "enviar_mensagem":
            telefone = tool_input.get("telefone", "?")
            instrucao = tool_input.get("instrucao", "")
            tipo_param = tool_input.get("tipo", "")
            tel_fmt = fmt.formatar_telefone(telefone)

            # Inferir tipo se nao especificado
            if tipo_param:
                tipo_desc = descrever_tipo(TipoAbordagem(tipo_param))
            else:
                tipo_inferido = inferir_tipo(instrucao)
                tipo_desc = descrever_tipo(tipo_inferido)

            msg = f"Vou mandar msg pro {tel_fmt} (*{tipo_desc}*)"
            if instrucao:
                msg += f":\n\n> {instrucao}"
            msg += "\n\nPosso enviar?"
            return msg

        elif tool_name == "bloquear_medico":
            telefone = tool_input.get("telefone", "?")
            motivo = tool_input.get("motivo", "")
            tel_fmt = fmt.formatar_telefone(telefone)
            msg = f"Vou bloquear o {tel_fmt}"
            if motivo:
                msg += f" (motivo: {motivo})"
            msg += ". Confirma?"
            return msg

        elif tool_name == "desbloquear_medico":
            telefone = tool_input.get("telefone", "?")
            tel_fmt = fmt.formatar_telefone(telefone)
            return f"Vou desbloquear o {tel_fmt}. Confirma?"

        elif tool_name == "reservar_vaga":
            telefone = tool_input.get("telefone_medico", "?")
            data = tool_input.get("data_vaga", "?")
            tel_fmt = fmt.formatar_telefone(telefone)
            data_fmt = fmt.formatar_data(data)
            return f"Vou reservar a vaga do dia *{data_fmt}* pro {tel_fmt}. Confirma?"

        elif tool_name == "pausar_julia":
            return "Vou *pausar* os envios automaticos. Confirma?"

        elif tool_name == "retomar_julia":
            return "Vou *retomar* os envios automaticos. Confirma?"

        return "Posso executar essa acao?"

    def _formatar_sucesso(self, tool_name: str, result: dict) -> str:
        """Formata mensagem de sucesso usando templates."""
        if tool_name == "enviar_mensagem":
            return fmt.template_sucesso_envio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "bloquear_medico":
            return fmt.template_sucesso_bloqueio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "desbloquear_medico":
            return fmt.template_sucesso_desbloqueio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "reservar_vaga":
            return fmt.template_sucesso_reserva(
                vaga=result.get("vaga", {}),
                medico=result.get("medico", {})
            )

        elif tool_name == "pausar_julia":
            return "⏸️ Pausada! Envios automaticos suspensos"

        elif tool_name == "retomar_julia":
            return "▶️ Retomada! Envios automaticos ativos"

        return "Feito!"

    def _formatar_resultado_direto(self, tool_results: list) -> str:
        """Formata resultado direto quando LLM falha."""
        partes = []
        for tr in tool_results:
            try:
                result = json.loads(tr["content"])
                if result.get("success"):
                    # Tentar formatar com templates
                    if "metricas" in result:
                        partes.append(fmt.template_metricas(
                            result["metricas"],
                            result.get("periodo", "")
                        ))
                    elif "medicos" in result:
                        partes.append(fmt.template_lista_medicos(
                            result["medicos"],
                            result.get("filtro", "")
                        ))
                    elif "vagas" in result:
                        partes.append(fmt.template_lista_vagas(result["vagas"]))
                    elif "status" in result:
                        partes.append(fmt.template_status_sistema(result))
                    elif "handoffs" in result:
                        partes.append(fmt.template_lista_handoffs(result["handoffs"]))
                    elif "medico" in result:
                        partes.append(fmt.template_medico_info(result["medico"]))
                    elif "mensagens" in result:
                        partes.append(fmt.template_historico(
                            result.get("medico", "?"),
                            result["mensagens"]
                        ))
                    elif "variacao" in result:
                        partes.append(fmt.template_comparacao(result))
                    else:
                        partes.append("Feito!")
                else:
                    # Formatar erro amigavel
                    erro = result.get("error", "erro desconhecido")
                    partes.append(fmt.formatar_erro(erro))
            except Exception:
                partes.append("Processado")
        return "\n\n".join(partes) if partes else "Pronto!"


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
