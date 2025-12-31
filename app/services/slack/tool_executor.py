"""
Executor de tools do agente Slack.

Sprint 10 - S10.E2.2
V2 - Governanca (31/12/2025):
- Audit log para comandos criticos
- Broadcast de status em toggles
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.tools.slack import TOOLS_CRITICAS, executar_tool
from app.services.supabase import supabase
from app.services.slack.formatter import (
    formatar_telefone,
    formatar_data,
    formatar_erro,
    template_metricas,
    template_lista_medicos,
    template_lista_vagas,
    template_status_sistema,
    template_lista_handoffs,
    template_medico_info,
    template_historico,
    template_comparacao,
    template_sucesso_envio,
    template_sucesso_bloqueio,
    template_sucesso_desbloqueio,
    template_sucesso_reserva,
)
from app.services.tipos_abordagem import TipoAbordagem, inferir_tipo, descrever_tipo

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executa tools do agente Slack."""

    def __init__(self, user_id: str, channel_id: str = ""):
        """
        Inicializa o executor.

        Args:
            user_id: ID do usuario Slack
            channel_id: ID do canal Slack
        """
        self.user_id = user_id
        self.channel_id = channel_id

    def is_tool_critica(self, tool_name: str, tool_input: dict = None) -> bool:
        """
        Verifica se tool requer confirmacao.

        Para toggle_campanhas e toggle_ponte_externa, status queries
        NÃO requerem confirmação (são read-only).
        """
        if tool_name not in TOOLS_CRITICAS:
            return False

        # Toggle tools: só crítico se está MUDANDO estado
        if tool_name in ["toggle_campanhas", "toggle_ponte_externa"]:
            acao = (tool_input or {}).get("acao", "status")
            return acao in ["on", "off"]  # status query não é crítico

        return True

    async def executar(self, tool_name: str, tool_input: dict) -> dict:
        """
        Executa uma tool.

        Args:
            tool_name: Nome da tool
            tool_input: Parametros da tool

        Returns:
            Resultado da execucao

        V2: Adiciona audit log para comandos criticos.
        """
        logger.info(f"Executando tool: {tool_name} com params {tool_input}")

        result = await executar_tool(tool_name, tool_input, self.user_id, self.channel_id)

        # V2: Audit log para comandos criticos
        if self.is_tool_critica(tool_name, tool_input):
            await self._registrar_audit_log(tool_name, tool_input, result)

            # V2: Broadcast para toggles de modo (NÃO para consultas de status)
            if tool_name in ["pausar_julia", "retomar_julia"]:
                await self._broadcast_status_change(tool_name, tool_input, result)
            elif tool_name in ["toggle_campanhas", "toggle_ponte_externa"]:
                # Só broadcast quando MUDA estado, não quando consulta status
                acao = tool_input.get("acao", "status")
                if acao in ["on", "off"]:
                    await self._broadcast_status_change(tool_name, tool_input, result)

        return result

    async def _registrar_audit_log(self, tool_name: str, tool_input: dict, result: dict):
        """
        V2: Registra audit log para comandos criticos.

        Requisitos de governanca:
        - Quem executou (user_id)
        - O que executou (tool_name + params)
        - Quando executou (timestamp)
        - Resultado (sucesso/erro)
        """
        try:
            supabase.table("slack_comandos").insert({
                "texto_original": f"[AUDIT] {tool_name}",
                "comando": tool_name,
                "argumentos": tool_input,
                "user_id": self.user_id,
                "channel_id": self.channel_id,
                "resposta": json.dumps(result, ensure_ascii=False)[:1000],
                "respondido": True,
                "respondido_em": datetime.now(timezone.utc).isoformat(),
                "erro": None if result.get("success") else result.get("error"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            logger.info(
                f"[AUDIT] {tool_name} executado por {self.user_id}",
                extra={
                    "event": "audit_log",
                    "tool": tool_name,
                    "user_id": self.user_id,
                    "success": result.get("success", False),
                    "params": tool_input
                }
            )
        except Exception as e:
            logger.error(f"Erro ao registrar audit log: {e}")

    async def _broadcast_status_change(self, tool_name: str, tool_input: dict, result: dict):
        """
        V2: Broadcast de mudanca de status no canal.

        Quando alguem muda o modo do sistema (pausar, retomar, toggle),
        todos no canal veem a notificacao.
        """
        from app.services.slack import enviar_slack

        if not result.get("success"):
            return

        # Mapear tool para mensagem de broadcast
        broadcasts = {
            "pausar_julia": "⏸️ *Julia pausada* por <@{user}>",
            "retomar_julia": "▶️ *Julia retomada* por <@{user}>",
            "toggle_campanhas": "🔄 *Campanhas {status}* por <@{user}>",
            "toggle_ponte_externa": "🌉 *Ponte externa {status}* por <@{user}>",
        }

        template = broadcasts.get(tool_name)
        if not template:
            return

        # Determinar status para toggles
        if tool_name == "toggle_campanhas":
            status = "ativadas" if result.get("campanhas_ativas") else "desativadas"
            msg = template.format(user=self.user_id, status=status)
        elif tool_name == "toggle_ponte_externa":
            status = "ativada" if result.get("enabled") else "desativada"
            msg = template.format(user=self.user_id, status=status)
        else:
            msg = template.format(user=self.user_id)

        try:
            await enviar_slack({"text": msg})
            logger.info(f"[BROADCAST] {msg}")
        except Exception as e:
            logger.error(f"Erro ao enviar broadcast: {e}")

    def gerar_preview(self, tool_name: str, tool_input: dict) -> str:
        """
        Gera preview para pedir confirmacao.

        Args:
            tool_name: Nome da tool
            tool_input: Parametros da tool

        Returns:
            Mensagem de preview
        """
        if tool_name == "enviar_mensagem":
            telefone = tool_input.get("telefone", "?")
            instrucao = tool_input.get("instrucao", "")
            tipo_param = tool_input.get("tipo", "")
            tel_fmt = formatar_telefone(telefone)

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
            tel_fmt = formatar_telefone(telefone)
            msg = f"Vou bloquear o {tel_fmt}"
            if motivo:
                msg += f" (motivo: {motivo})"
            msg += ". Confirma?"
            return msg

        elif tool_name == "desbloquear_medico":
            telefone = tool_input.get("telefone", "?")
            tel_fmt = formatar_telefone(telefone)
            return f"Vou desbloquear o {tel_fmt}. Confirma?"

        elif tool_name == "reservar_vaga":
            telefone = tool_input.get("telefone_medico", "?")
            data = tool_input.get("data_vaga", "?")
            tel_fmt = formatar_telefone(telefone)
            data_fmt = formatar_data(data)
            return f"Vou reservar a vaga do dia *{data_fmt}* pro {tel_fmt}. Confirma?"

        elif tool_name == "pausar_julia":
            return "Vou *pausar* os envios automaticos. Confirma?"

        elif tool_name == "retomar_julia":
            return "Vou *retomar* os envios automaticos. Confirma?"

        return "Posso executar essa acao?"

    def formatar_sucesso(self, tool_name: str, result: dict) -> str:
        """
        Formata mensagem de sucesso.

        Args:
            tool_name: Nome da tool
            result: Resultado da execucao

        Returns:
            Mensagem formatada
        """
        if tool_name == "enviar_mensagem":
            return template_sucesso_envio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "bloquear_medico":
            return template_sucesso_bloqueio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "desbloquear_medico":
            return template_sucesso_desbloqueio(
                nome=result.get("nome"),
                telefone=result.get("telefone")
            )

        elif tool_name == "reservar_vaga":
            return template_sucesso_reserva(
                vaga=result.get("vaga", {}),
                medico=result.get("medico", {})
            )

        elif tool_name == "pausar_julia":
            return "⏸️ Pausada! Envios automaticos suspensos"

        elif tool_name == "retomar_julia":
            return "▶️ Retomada! Envios automaticos ativos"

        return "Feito!"

    def formatar_resultado(self, tool_results: list) -> str:
        """
        Formata resultado direto quando LLM falha.

        Args:
            tool_results: Lista de resultados das tools

        Returns:
            Resultado formatado
        """
        partes = []

        for tr in tool_results:
            try:
                result = json.loads(tr["content"])

                if result.get("success"):
                    # Tentar formatar com templates
                    if "metricas" in result:
                        partes.append(template_metricas(
                            result["metricas"],
                            result.get("periodo", "")
                        ))
                    elif "medicos" in result:
                        partes.append(template_lista_medicos(
                            result["medicos"],
                            result.get("filtro", "")
                        ))
                    elif "vagas" in result:
                        partes.append(template_lista_vagas(result["vagas"]))
                    elif "status" in result:
                        partes.append(template_status_sistema(result))
                    elif "handoffs" in result:
                        partes.append(template_lista_handoffs(result["handoffs"]))
                    elif "medico" in result:
                        partes.append(template_medico_info(result["medico"]))
                    elif "mensagens" in result:
                        partes.append(template_historico(
                            result.get("medico", "?"),
                            result["mensagens"]
                        ))
                    elif "variacao" in result:
                        partes.append(template_comparacao(result))
                    else:
                        partes.append("Feito!")
                else:
                    # Formatar erro amigavel
                    erro = result.get("error", "erro desconhecido")
                    partes.append(formatar_erro(erro))

            except Exception:
                partes.append("Processado")

        return "\n\n".join(partes) if partes else "Pronto!"
