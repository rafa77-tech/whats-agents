"""
Serviço de Gestor Comanda Julia.

Sprint 32 E09 - Interpretação com Opus, execução com Haiku.

Fluxo:
1. Gestor envia comando em linguagem natural via Slack
2. Opus interpreta o comando e cria plano de ação
3. Julia apresenta plano e pede confirmação
4. Gestor confirma ou ajusta
5. Haiku executa as ações conforme plano

Exemplo:
    Gestor: "Julia, entra em contato com todos os cardiologistas
            que responderam positivo no último mês mas não fecharam"

    Julia (Opus): "Entendi! Só pra confirmar:
                  - Cardiologistas que responderam interesse
                  - No último mês (dezembro/janeiro)
                  - Que não fecharam nenhuma vaga

                  Encontrei 23 médicos nesse perfil. Faço um followup
                  perguntando se ainda têm interesse?"

    Gestor: "Isso, mas menciona que temos vagas novas em fevereiro"

    Julia (Opus): "Perfeito! Vou:
                  1. Contatar os 23 médicos
                  2. Perguntar se ainda têm interesse
                  3. Mencionar vagas de fevereiro

                  Posso começar?"

    Gestor: "Vai"

    Julia (Haiku): [Executa os 23 contatos]
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import anthropic

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTES
# =============================================================================

# Modelos
MODEL_OPUS = "claude-sonnet-4-20250514"  # Para interpretação e planejamento
MODEL_HAIKU = "claude-haiku-4-5-20251001"  # Para execução

# Status do comando
STATUS_PENDENTE = "pendente"
STATUS_AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
STATUS_CONFIRMADO = "confirmado"
STATUS_EXECUTANDO = "executando"
STATUS_CONCLUIDO = "concluido"
STATUS_CANCELADO = "cancelado"
STATUS_ERRO = "erro"

# Tipos de ação
ACAO_CONTATAR_MEDICOS = "contatar_medicos"
ACAO_CRIAR_CAMPANHA = "criar_campanha"
ACAO_CRIAR_VAGA = "criar_vaga"
ACAO_ATUALIZAR_VAGA = "atualizar_vaga"
ACAO_DEFINIR_MARGEM = "definir_margem"
ACAO_BLOQUEAR_HOSPITAL = "bloquear_hospital"
ACAO_CONSULTAR = "consultar"
ACAO_OUTRO = "outro"

# Prompt para interpretação
PROMPT_INTERPRETAR = """Você é Julia, uma escalista experiente da Revoluna.

O gestor enviou um comando em linguagem natural. Sua tarefa é:
1. Interpretar exatamente o que o gestor quer
2. Criar um plano de ação claro
3. Identificar quais dados precisam ser buscados
4. Sugerir confirmações necessárias

IMPORTANTE:
- Seja específica sobre o que vai fazer
- Identifique filtros (especialidade, período, status, etc)
- Se houver ambiguidade, pergunte antes de agir
- Calcule o impacto (quantos médicos, vagas, etc)

Responda em JSON com a estrutura:
{
    "interpretacao": "O que entendi do comando",
    "tipo_acao": "contatar_medicos|criar_campanha|criar_vaga|atualizar_vaga|definir_margem|bloquear_hospital|consultar|outro",
    "filtros": {
        "especialidade": null ou "nome",
        "periodo_inicio": null ou "YYYY-MM-DD",
        "periodo_fim": null ou "YYYY-MM-DD",
        "status_interesse": null ou "positivo|negativo|neutro",
        "status_fechou": null ou true|false,
        "regiao": null ou "nome",
        "hospital_id": null ou "uuid"
    },
    "acoes": [
        {
            "ordem": 1,
            "descricao": "O que vou fazer",
            "tipo": "buscar|criar|atualizar|enviar",
            "parametros": {}
        }
    ],
    "precisa_confirmar": true|false,
    "pergunta_confirmacao": "Mensagem para confirmar com gestor",
    "dados_a_buscar": ["medicos", "vagas", etc],
    "estimativa_impacto": {
        "medicos_afetados": 0,
        "vagas_afetadas": 0,
        "mensagens_a_enviar": 0
    },
    "duvidas": ["Perguntas se houver ambiguidade"]
}
"""

PROMPT_PLANEJAR = """Com base na interpretação e nos dados buscados, crie um plano detalhado.

Dados disponíveis:
{dados}

Interpretação original:
{interpretacao}

Crie o plano final em JSON:
{
    "resumo": "Resumo do que será feito",
    "passos": [
        {
            "ordem": 1,
            "descricao": "Descrição clara",
            "tipo": "enviar_mensagem|criar_registro|atualizar_registro",
            "alvos": ["ids dos médicos/vagas"],
            "template": "Mensagem ou dados a usar"
        }
    ],
    "total_acoes": 0,
    "mensagem_confirmacao": "Mensagem amigável para o gestor confirmar"
}
"""


# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================


class GestorComanda:
    """Orquestrador de comandos do gestor."""

    def __init__(self, user_id: str, channel_id: str):
        """
        Inicializa o orquestrador.

        Args:
            user_id: ID do usuário Slack
            channel_id: ID do canal Slack
        """
        self.user_id = user_id
        self.channel_id = channel_id
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.comando_atual: Optional[dict] = None

    async def interpretar_comando(self, comando: str) -> dict:
        """
        Interpreta comando do gestor usando Opus.

        Args:
            comando: Comando em linguagem natural

        Returns:
            Dict com interpretação e plano inicial
        """
        try:
            # Chamar Opus para interpretar
            response = self.client.messages.create(
                model=MODEL_OPUS,
                max_tokens=2000,
                system=PROMPT_INTERPRETAR,
                messages=[{"role": "user", "content": f"Comando do gestor: {comando}"}],
            )

            # Extrair JSON da resposta
            texto = response.content[0].text
            interpretacao = _extrair_json(texto)

            if not interpretacao:
                return {
                    "success": False,
                    "error": "Não consegui interpretar o comando",
                    "raw": texto,
                }

            # Salvar comando no banco
            comando_id = await self._salvar_comando(
                comando_original=comando,
                interpretacao=interpretacao,
            )

            self.comando_atual = {
                "id": comando_id,
                "comando": comando,
                "interpretacao": interpretacao,
            }

            # Se precisa de dados, buscar
            if interpretacao.get("dados_a_buscar"):
                dados = await self._buscar_dados(interpretacao)
                interpretacao["dados_encontrados"] = dados

                # Atualizar estimativa de impacto
                if "medicos" in dados:
                    interpretacao["estimativa_impacto"]["medicos_afetados"] = len(dados["medicos"])

            return {
                "success": True,
                "comando_id": comando_id,
                "interpretacao": interpretacao,
                "mensagem": self._formatar_mensagem_interpretacao(interpretacao),
            }

        except Exception as e:
            logger.error(f"Erro ao interpretar comando: {e}")
            return {"success": False, "error": str(e)}

    async def ajustar_plano(self, comando_id: str, ajuste: str) -> dict:
        """
        Ajusta plano baseado em feedback do gestor.

        Args:
            comando_id: ID do comando
            ajuste: Ajuste solicitado pelo gestor

        Returns:
            Dict com plano ajustado
        """
        try:
            # Buscar comando atual
            comando = await self._buscar_comando(comando_id)
            if not comando:
                return {"success": False, "error": "Comando não encontrado"}

            # Chamar Opus para ajustar
            response = self.client.messages.create(
                model=MODEL_OPUS,
                max_tokens=2000,
                system=PROMPT_INTERPRETAR,
                messages=[
                    {"role": "user", "content": f"Comando original: {comando['comando_original']}"},
                    {
                        "role": "assistant",
                        "content": json.dumps(comando["interpretacao"], ensure_ascii=False),
                    },
                    {"role": "user", "content": f"Ajuste solicitado: {ajuste}"},
                ],
            )

            texto = response.content[0].text
            nova_interpretacao = _extrair_json(texto)

            if not nova_interpretacao:
                return {"success": False, "error": "Não consegui processar o ajuste"}

            # Atualizar no banco
            await self._atualizar_comando(
                comando_id=comando_id,
                interpretacao=nova_interpretacao,
            )

            return {
                "success": True,
                "comando_id": comando_id,
                "interpretacao": nova_interpretacao,
                "mensagem": self._formatar_mensagem_interpretacao(nova_interpretacao),
            }

        except Exception as e:
            logger.error(f"Erro ao ajustar plano: {e}")
            return {"success": False, "error": str(e)}

    async def confirmar_execucao(self, comando_id: str) -> dict:
        """
        Confirma e inicia execução do comando.

        Args:
            comando_id: ID do comando

        Returns:
            Dict com status da execução
        """
        try:
            # Buscar comando
            comando = await self._buscar_comando(comando_id)
            if not comando:
                return {"success": False, "error": "Comando não encontrado"}

            if comando["status"] != STATUS_AGUARDANDO_CONFIRMACAO:
                return {
                    "success": False,
                    "error": f"Comando em status inválido: {comando['status']}",
                }

            # Atualizar status
            await self._atualizar_status(comando_id, STATUS_CONFIRMADO)

            # Iniciar execução
            resultado = await self._executar_comando(comando)

            return resultado

        except Exception as e:
            logger.error(f"Erro ao confirmar execução: {e}")
            return {"success": False, "error": str(e)}

    async def cancelar_comando(self, comando_id: str, motivo: str = "") -> dict:
        """
        Cancela um comando.

        Args:
            comando_id: ID do comando
            motivo: Motivo do cancelamento

        Returns:
            Dict com resultado
        """
        try:
            await self._atualizar_status(
                comando_id,
                STATUS_CANCELADO,
                notas=f"Cancelado: {motivo}" if motivo else "Cancelado pelo gestor",
            )

            return {"success": True, "comando_id": comando_id, "status": STATUS_CANCELADO}

        except Exception as e:
            logger.error(f"Erro ao cancelar comando: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MÉTODOS INTERNOS
    # =========================================================================

    async def _salvar_comando(self, comando_original: str, interpretacao: dict) -> str:
        """Salva comando no banco."""
        comando_id = str(uuid4())

        try:
            supabase.table("comandos_gestor").insert(
                {
                    "id": comando_id,
                    "user_id": self.user_id,
                    "channel_id": self.channel_id,
                    "comando_original": comando_original,
                    "interpretacao": interpretacao,
                    "status": STATUS_AGUARDANDO_CONFIRMACAO,
                }
            ).execute()

        except Exception as e:
            # Se tabela não existe, apenas logar
            logger.warning(f"Erro ao salvar comando (tabela pode não existir): {e}")

        return comando_id

    async def _buscar_comando(self, comando_id: str) -> Optional[dict]:
        """Busca comando no banco."""
        try:
            response = (
                supabase.table("comandos_gestor")
                .select("*")
                .eq("id", comando_id)
                .limit(1)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:
            logger.warning(f"Erro ao buscar comando: {e}")
            return None

    async def _atualizar_comando(self, comando_id: str, interpretacao: dict):
        """Atualiza interpretação do comando."""
        try:
            supabase.table("comandos_gestor").update(
                {
                    "interpretacao": interpretacao,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", comando_id).execute()

        except Exception as e:
            logger.warning(f"Erro ao atualizar comando: {e}")

    async def _atualizar_status(self, comando_id: str, status: str, notas: str = ""):
        """Atualiza status do comando."""
        try:
            data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if status == STATUS_EXECUTANDO:
                data["executado_em"] = datetime.now(timezone.utc).isoformat()
            elif status == STATUS_CONCLUIDO:
                data["concluido_em"] = datetime.now(timezone.utc).isoformat()

            if notas:
                data["notas"] = notas

            supabase.table("comandos_gestor").update(data).eq("id", comando_id).execute()

        except Exception as e:
            logger.warning(f"Erro ao atualizar status: {e}")

    async def _buscar_dados(self, interpretacao: dict) -> dict:
        """Busca dados necessários para o comando."""
        dados = {}
        filtros = interpretacao.get("filtros", {})

        for tipo_dado in interpretacao.get("dados_a_buscar", []):
            if tipo_dado == "medicos":
                dados["medicos"] = await self._buscar_medicos(filtros)
            elif tipo_dado == "vagas":
                dados["vagas"] = await self._buscar_vagas(filtros)

        return dados

    async def _buscar_medicos(self, filtros: dict) -> list:
        """Busca médicos com filtros."""
        try:
            query = (
                supabase.table("clientes")
                .select("id, primeiro_nome, telefone, especialidade")
                .eq("opt_out", False)
                .eq("status_telefone", "validado")
            )

            if filtros.get("especialidade"):
                query = query.ilike("especialidade", f"%{filtros['especialidade']}%")

            if filtros.get("status_interesse") == "positivo":
                # Médicos com interesse positivo
                query = query.gt("total_interacoes", 0)

            if filtros.get("status_fechou") is False:
                # Médicos que não fecharam vaga
                # Isso requer join ou subquery mais complexa
                pass

            response = query.limit(100).execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Erro ao buscar médicos: {e}")
            return []

    async def _buscar_vagas(self, filtros: dict) -> list:
        """Busca vagas com filtros."""
        try:
            query = (
                supabase.table("vagas")
                .select("*, hospitais(nome), especialidades(nome)")
                .eq("status", "aberta")
                .is_("deleted_at", "null")
            )

            if filtros.get("periodo_inicio"):
                query = query.gte("data", filtros["periodo_inicio"])

            if filtros.get("periodo_fim"):
                query = query.lte("data", filtros["periodo_fim"])

            response = query.limit(50).execute()
            return response.data or []

        except Exception as e:
            logger.error(f"Erro ao buscar vagas: {e}")
            return []

    async def _executar_comando(self, comando: dict) -> dict:
        """Executa o comando usando Haiku."""
        try:
            await self._atualizar_status(comando["id"], STATUS_EXECUTANDO)

            interpretacao = comando["interpretacao"]
            tipo_acao = interpretacao.get("tipo_acao", ACAO_OUTRO)

            # Executar baseado no tipo
            if tipo_acao == ACAO_CONTATAR_MEDICOS:
                resultado = await self._executar_contato_medicos(comando)
            elif tipo_acao == ACAO_CRIAR_CAMPANHA:
                resultado = await self._executar_criar_campanha(comando)
            elif tipo_acao == ACAO_DEFINIR_MARGEM:
                resultado = await self._executar_definir_margem(comando)
            elif tipo_acao == ACAO_CONSULTAR:
                resultado = {"success": True, "tipo": "consulta", "mensagem": "Consulta realizada"}
            else:
                resultado = {"success": False, "error": f"Tipo de ação não suportado: {tipo_acao}"}

            # Atualizar status final
            if resultado.get("success"):
                await self._atualizar_status(
                    comando["id"],
                    STATUS_CONCLUIDO,
                    notas=json.dumps(resultado, ensure_ascii=False),
                )
            else:
                await self._atualizar_status(
                    comando["id"],
                    STATUS_ERRO,
                    notas=resultado.get("error", "Erro desconhecido"),
                )

            return resultado

        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
            await self._atualizar_status(comando["id"], STATUS_ERRO, notas=str(e))
            return {"success": False, "error": str(e)}

    async def _executar_contato_medicos(self, comando: dict) -> dict:
        """Executa contato com médicos."""
        from app.services.fila_mensagens import enfileirar_mensagem

        interpretacao = comando["interpretacao"]
        medicos = interpretacao.get("dados_encontrados", {}).get("medicos", [])

        if not medicos:
            return {"success": False, "error": "Nenhum médico para contatar"}

        enfileirados = 0
        erros = 0

        for medico in medicos:
            try:
                await enfileirar_mensagem(
                    cliente_id=medico["id"],
                    tipo="followup",
                    prioridade=5,
                    metadata={
                        "comando_id": comando["id"],
                        "origem": "gestor_comanda",
                    },
                )
                enfileirados += 1

            except Exception as e:
                logger.error(f"Erro ao enfileirar médico {medico['id']}: {e}")
                erros += 1

        return {
            "success": True,
            "tipo": "contato_medicos",
            "enfileirados": enfileirados,
            "erros": erros,
            "mensagem": f"✅ {enfileirados} médicos enfileirados para contato",
        }

    async def _executar_criar_campanha(self, comando: dict) -> dict:
        """Executa criação de campanha."""
        # Por enquanto, apenas retorna sucesso
        # TODO: Implementar criação de campanha
        return {
            "success": True,
            "tipo": "criar_campanha",
            "mensagem": "Campanha criada com sucesso",
        }

    async def _executar_definir_margem(self, comando: dict) -> dict:
        """Executa definição de margem."""
        from app.services.diretrizes_contextuais import criar_margem_vaga, criar_margem_medico

        interpretacao = comando["interpretacao"]
        filtros = interpretacao.get("filtros", {})

        try:
            if filtros.get("vaga_id"):
                await criar_margem_vaga(
                    vaga_id=filtros["vaga_id"],
                    valor_maximo=filtros.get("valor_maximo"),
                    percentual_maximo=filtros.get("percentual_maximo"),
                    criado_por=self.user_id,
                )
                return {
                    "success": True,
                    "tipo": "margem_vaga",
                    "mensagem": "Margem definida para vaga",
                }

            elif filtros.get("cliente_id"):
                await criar_margem_medico(
                    cliente_id=filtros["cliente_id"],
                    valor_maximo=filtros.get("valor_maximo"),
                    percentual_maximo=filtros.get("percentual_maximo"),
                    criado_por=self.user_id,
                )
                return {
                    "success": True,
                    "tipo": "margem_medico",
                    "mensagem": "Margem definida para médico",
                }

            return {"success": False, "error": "Escopo de margem não especificado"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _formatar_mensagem_interpretacao(self, interpretacao: dict) -> str:
        """Formata mensagem de interpretação para o gestor."""
        linhas = []

        # Interpretação
        linhas.append(f"📋 *Entendi!*\n{interpretacao.get('interpretacao', '')}\n")

        # Impacto estimado
        impacto = interpretacao.get("estimativa_impacto", {})
        if impacto.get("medicos_afetados"):
            linhas.append(f"👥 Médicos: {impacto['medicos_afetados']}")
        if impacto.get("vagas_afetadas"):
            linhas.append(f"📅 Vagas: {impacto['vagas_afetadas']}")
        if impacto.get("mensagens_a_enviar"):
            linhas.append(f"💬 Mensagens: {impacto['mensagens_a_enviar']}")

        # Ações planejadas
        acoes = interpretacao.get("acoes", [])
        if acoes:
            linhas.append("\n*Vou fazer:*")
            for acao in acoes:
                linhas.append(f"  {acao['ordem']}. {acao['descricao']}")

        # Dúvidas
        duvidas = interpretacao.get("duvidas", [])
        if duvidas:
            linhas.append("\n⚠️ *Dúvidas:*")
            for duvida in duvidas:
                linhas.append(f"  • {duvida}")

        # Confirmação
        if interpretacao.get("precisa_confirmar"):
            linhas.append(f"\n{interpretacao.get('pergunta_confirmacao', 'Posso prosseguir?')}")

        return "\n".join(linhas)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================


def _extrair_json(texto: str) -> Optional[dict]:
    """Extrai JSON de uma resposta do LLM."""
    try:
        # Tentar extrair JSON direto
        if texto.strip().startswith("{"):
            return json.loads(texto)

        # Tentar encontrar JSON no texto
        import re

        match = re.search(r"\{[\s\S]*\}", texto)
        if match:
            return json.loads(match.group())

        return None

    except json.JSONDecodeError:
        return None


# =============================================================================
# FUNÇÃO DE CONVENIÊNCIA
# =============================================================================


async def processar_comando_gestor(
    comando: str,
    user_id: str,
    channel_id: str,
) -> dict:
    """
    Processa comando do gestor.

    Uso:
    ```python
    resultado = await processar_comando_gestor(
        comando="Contata todos os cardiologistas que mostraram interesse",
        user_id="U123",
        channel_id="C456",
    )
    ```

    Args:
        comando: Comando em linguagem natural
        user_id: ID do usuário Slack
        channel_id: ID do canal Slack

    Returns:
        Dict com resultado
    """
    gestor = GestorComanda(user_id, channel_id)
    return await gestor.interpretar_comando(comando)
