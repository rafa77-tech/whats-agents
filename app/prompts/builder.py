"""
Builder de prompts - combina partes em prompt final.

Sprint 32 E02: Adicionado suporte a contexto de campanha.
"""
import logging
from datetime import datetime
from typing import Optional, Literal

from .loader import (
    carregar_prompt,
    carregar_prompt_especialidade,
    buscar_prompt_por_tipo_campanha,
)

logger = logging.getLogger(__name__)

# Tipos de campanha válidos
CampaignType = Literal["discovery", "oferta", "followup", "feedback", "reativacao"]


def _formatar_data(data_iso: str) -> str:
    """
    Converte data ISO para formato brasileiro.

    Args:
        data_iso: Data no formato YYYY-MM-DD

    Returns:
        Data no formato DD/MM/YYYY
    """
    try:
        dt = datetime.fromisoformat(data_iso)
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return data_iso


def _formatar_escopo_vagas(offer_scope: Optional[dict]) -> str:
    """
    Formata escopo de vagas para injeção no prompt.

    Args:
        offer_scope: Dict com filtros de vagas

    Returns:
        String formatada para o prompt

    Exemplo de input:
        {
            "especialidade": "cardiologia",
            "periodo_inicio": "2026-03-01",
            "periodo_fim": "2026-03-31",
            "hospital_id": None,
            "regiao": "grande_sp"
        }
    """
    if not offer_scope:
        return "ESCOPO: Nenhum escopo definido - NÃO oferte vagas."

    linhas = ["ESCOPO PERMITIDO:"]

    if offer_scope.get("especialidade"):
        linhas.append(f"- Especialidade: {offer_scope['especialidade'].title()}")

    if offer_scope.get("periodo_inicio") and offer_scope.get("periodo_fim"):
        inicio = _formatar_data(offer_scope["periodo_inicio"])
        fim = _formatar_data(offer_scope["periodo_fim"])
        linhas.append(f"- Período: {inicio} a {fim}")

    if offer_scope.get("hospital_id"):
        # Nome do hospital deve ser passado no escopo ou buscado externamente
        hospital_nome = offer_scope.get("hospital_nome", "Hospital específico")
        linhas.append(f"- Hospital: {hospital_nome}")
    else:
        linhas.append("- Hospital: Qualquer hospital disponível")

    if offer_scope.get("regiao"):
        linhas.append(f"- Região: {offer_scope['regiao']}")

    linhas.append("")
    linhas.append("IMPORTANTE: Só apresente vagas que estejam DENTRO deste escopo.")

    return "\n".join(linhas)


def _formatar_margem_negociacao(negotiation_margin: Optional[dict]) -> str:
    """
    Formata margem de negociação para injeção no prompt.

    Args:
        negotiation_margin: Dict com regras de negociação

    Exemplo de input:
        {
            "tipo": "percentual",
            "valor": 15,
            "escopo": "vaga",
            "vaga_id": 123
        }
        ou
        {
            "tipo": "valor_maximo",
            "valor": 3000,
            "escopo": "medico",
            "cliente_id": "uuid"
        }
    """
    if not negotiation_margin:
        return (
            "MARGEM DE NEGOCIAÇÃO: Não definida.\n"
            "Se o médico pedir negociação de valor, diga que o valor é fechado.\n"
            "Se ele insistir muito, acione o canal de ajuda."
        )

    tipo = negotiation_margin.get("tipo")
    valor = negotiation_margin.get("valor")

    if tipo == "percentual":
        return (
            f"MARGEM DE NEGOCIAÇÃO:\n"
            f"Você pode negociar até {valor}% acima do valor base.\n"
            f"Se o médico pedir aumento, pode oferecer até esse limite.\n"
            f"Acima disso, diga que precisa confirmar com a supervisão."
        )
    elif tipo == "valor_maximo":
        valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return (
            f"MARGEM DE NEGOCIAÇÃO:\n"
            f"Você pode negociar até R$ {valor_formatado}.\n"
            f"Se o médico pedir mais que isso, diga que precisa confirmar."
        )
    else:
        return "MARGEM DE NEGOCIAÇÃO: Formato não reconhecido. Não negocie valores."


class PromptBuilder:
    """
    Constroi prompt completo para o agente.

    Combina:
    - Prompt base (identidade, tom)
    - Prompt de especialidade (se houver)
    - Instrucoes de tools
    - Diretrizes do gestor
    - Contexto dinamico
    - Contexto de campanha (Sprint 32 E02)
    """

    def __init__(self):
        self._prompt_base: Optional[str] = None
        self._prompt_tools: Optional[str] = None
        self._prompt_especialidade: Optional[str] = None
        self._prompt_primeira_msg: Optional[str] = None
        self._prompt_campanha: Optional[str] = None  # Sprint 32 E02
        self._diretrizes: str = ""
        self._contexto: str = ""
        self._memorias: str = ""
        self._conhecimento: str = ""  # E03: Conhecimento dinâmico RAG
        self._policy_constraints: str = ""  # E06: Constraints da Policy Engine

        # Sprint 32 E02: Contexto de campanha
        self._campaign_type: Optional[str] = None
        self._campaign_objective: Optional[str] = None
        self._campaign_rules: Optional[list[str]] = None
        self._offer_scope: Optional[dict] = None
        self._negotiation_margin: Optional[dict] = None

    async def com_base(self) -> "PromptBuilder":
        """Carrega prompt base."""
        self._prompt_base = await carregar_prompt("julia_base")
        return self

    async def com_tools(self) -> "PromptBuilder":
        """Carrega instrucoes de tools."""
        self._prompt_tools = await carregar_prompt("julia_tools")
        return self

    async def com_especialidade(self, especialidade_id: str) -> "PromptBuilder":
        """Carrega prompt de especialidade."""
        if especialidade_id:
            self._prompt_especialidade = await carregar_prompt_especialidade(especialidade_id)
        return self

    async def com_primeira_msg(self) -> "PromptBuilder":
        """Carrega instrucoes para primeira mensagem."""
        self._prompt_primeira_msg = await carregar_prompt("julia_primeira_msg")
        return self

    def com_diretrizes(self, diretrizes: str) -> "PromptBuilder":
        """Adiciona diretrizes do gestor."""
        self._diretrizes = diretrizes
        return self

    def com_contexto(self, contexto: str) -> "PromptBuilder":
        """Adiciona contexto dinamico."""
        self._contexto = contexto
        return self

    def com_memorias(self, memorias: str) -> "PromptBuilder":
        """Adiciona memorias do medico."""
        self._memorias = memorias
        return self

    def com_conhecimento(self, conhecimento: str) -> "PromptBuilder":
        """
        Adiciona conhecimento dinâmico (E03).

        O conhecimento é gerado pelo OrquestradorConhecimento
        baseado na situação detectada (objeção, perfil, objetivo).

        Args:
            conhecimento: Resumo formatado do orquestrador
        """
        self._conhecimento = conhecimento
        return self

    def com_policy_constraints(self, constraints: str) -> "PromptBuilder":
        """
        Adiciona constraints da Policy Engine (E06 - Sprint 15).

        Os constraints vêm do PolicyDecide e definem o que a Julia
        PODE e NÃO PODE fazer nesta resposta.

        IMPORTANTE: Esta seção tem PRIORIDADE MÁXIMA no prompt.

        Args:
            constraints: Texto de constraints do PolicyDecision
        """
        self._policy_constraints = constraints
        return self

    # === Sprint 32 E02: Métodos de contexto de campanha ===

    async def com_campanha(
        self,
        campaign_type: str,
        campaign_objective: Optional[str] = None,
        campaign_rules: Optional[list[str]] = None,
        offer_scope: Optional[dict] = None,
        negotiation_margin: Optional[dict] = None,
    ) -> "PromptBuilder":
        """
        Configura contexto de campanha.

        Carrega prompt específico do tipo e armazena dados para injeção.

        Args:
            campaign_type: discovery | oferta | followup | feedback | reativacao
            campaign_objective: Objetivo em linguagem natural
            campaign_rules: Lista de regras específicas
            offer_scope: Escopo de vagas permitidas (para oferta)
            negotiation_margin: Margem de negociação

        Returns:
            self para encadeamento
        """
        self._campaign_type = campaign_type
        self._campaign_objective = campaign_objective
        self._campaign_rules = campaign_rules
        self._offer_scope = offer_scope
        self._negotiation_margin = negotiation_margin

        # Carregar prompt específico do tipo de campanha
        prompt = await buscar_prompt_por_tipo_campanha(campaign_type)
        if prompt:
            self._prompt_campanha = prompt
        else:
            logger.warning(
                f"Prompt julia_{campaign_type} não encontrado, usando fallback"
            )

        return self

    def com_escopo_vagas(self, offer_scope: dict) -> "PromptBuilder":
        """
        Define escopo de vagas para campanha de oferta.

        Args:
            offer_scope: Dict com filtros de vagas

        Returns:
            self para encadeamento
        """
        self._offer_scope = offer_scope
        return self

    def com_margem_negociacao(self, negotiation_margin: dict) -> "PromptBuilder":
        """
        Define margem de negociação.

        Args:
            negotiation_margin: Dict com tipo e valor da margem

        Returns:
            self para encadeamento
        """
        self._negotiation_margin = negotiation_margin
        return self

    async def com_conhecimento_automatico(
        self,
        mensagem: str,
        historico: list[str] = None,
        dados_cliente: dict = None,
        stage: str = "novo",
    ) -> "PromptBuilder":
        """
        Detecta situação e busca conhecimento automaticamente.

        Args:
            mensagem: Última mensagem do médico
            historico: Mensagens anteriores
            dados_cliente: Dados do cliente
            stage: Stage atual da jornada

        Returns:
            self para encadeamento
        """
        from app.services.conhecimento import OrquestradorConhecimento

        orquestrador = OrquestradorConhecimento()
        contexto = await orquestrador.analisar_situacao(
            mensagem=mensagem,
            historico=historico,
            dados_cliente=dados_cliente,
            stage=stage,
        )
        self._conhecimento = contexto.resumo
        return self

    def build(self) -> str:
        """
        Monta prompt final.

        Ordem de montagem (Sprint 32 E02 atualizado):
        0. Policy constraints (prioridade máxima)
        1. Prompt base
        2. Prompt de campanha (se definido) OU primeira_msg legado
        3. Objetivo da campanha
        4. Escopo de vagas (se oferta)
        5. Margem de negociação
        6. Regras específicas da campanha
        7. Especialidade
        8. Tools
        9. Conhecimento dinâmico
        10. Diretrizes do gestor
        11. Memórias do médico
        12. Contexto da conversa

        Returns:
            String com prompt completo
        """
        partes = []

        # 0. Policy constraints (PRIORIDADE MÁXIMA - Sprint 15)
        if self._policy_constraints:
            partes.append(f"## DIRETRIZES DE POLÍTICA (PRIORIDADE MÁXIMA)\n\n{self._policy_constraints}\n\n---")

        # 1. Prompt base (obrigatorio)
        if self._prompt_base:
            partes.append(self._prompt_base)
        else:
            logger.warning("Prompt base nao carregado!")

        # 2. Prompt de campanha (Sprint 32 E02) OU primeira_msg legado
        if self._prompt_campanha:
            partes.append(f"\n## COMPORTAMENTO DESTA CAMPANHA\n{self._prompt_campanha}")
        elif self._prompt_primeira_msg:
            partes.append(f"\n## INSTRUCOES PARA ESTA RESPOSTA\n{self._prompt_primeira_msg}")

        # 3. Objetivo da campanha (Sprint 32 E02)
        if self._campaign_objective:
            partes.append(f"\n## OBJETIVO DESTA CONVERSA\n{self._campaign_objective}")

        # 4. Escopo de vagas - só para ofertas (Sprint 32 E02)
        if self._campaign_type == "oferta" or self._offer_scope:
            escopo_formatado = _formatar_escopo_vagas(self._offer_scope)
            partes.append(f"\n## {escopo_formatado}")

        # 5. Margem de negociação (Sprint 32 E02)
        if self._negotiation_margin is not None:
            margem_formatada = _formatar_margem_negociacao(self._negotiation_margin)
            partes.append(f"\n## {margem_formatada}")

        # 6. Regras específicas da campanha (Sprint 32 E02)
        if self._campaign_rules:
            regras_formatadas = "\n".join(f"- {r}" for r in self._campaign_rules)
            partes.append(f"\n## REGRAS ESPECÍFICAS\n{regras_formatadas}")

        # 7. Especialidade (se houver)
        if self._prompt_especialidade:
            partes.append(f"\n## ESPECIALIDADE\n{self._prompt_especialidade}")

        # 8. Tools
        if self._prompt_tools:
            partes.append(f"\n{self._prompt_tools}")

        # 9. Conhecimento dinâmico (E03 - situação detectada + RAG)
        if self._conhecimento:
            partes.append(f"\n{self._conhecimento}")

        # 10. Diretrizes do gestor
        if self._diretrizes:
            partes.append(f"\n## DIRETRIZES DO GESTOR (PRIORIDADE MAXIMA)\n{self._diretrizes}")

        # 11. Memorias do medico
        if self._memorias:
            partes.append(f"\n{self._memorias}")

        # 12. Contexto dinamico
        if self._contexto:
            partes.append(f"\n## CONTEXTO DA CONVERSA\n{self._contexto}")

        return "\n".join(partes)


async def construir_prompt_julia(
    # === Sprint 32 E02: Novos parâmetros de campanha ===
    campaign_type: Optional[str] = None,
    campaign_objective: Optional[str] = None,
    campaign_rules: Optional[list[str]] = None,
    offer_scope: Optional[dict] = None,
    negotiation_margin: Optional[dict] = None,
    # === Parâmetros existentes (mantidos para compatibilidade) ===
    especialidade_id: str = None,
    diretrizes: str = "",
    contexto: str = "",
    memorias: str = "",
    conhecimento: str = "",
    primeira_msg: bool = False,
    policy_constraints: str = "",
) -> str:
    """
    Funcao helper para construir prompt completo.

    Sprint 32 E02: Adicionado suporte a contexto de campanha.

    Args:
        campaign_type: Tipo da campanha (discovery, oferta, followup, feedback, reativacao)
        campaign_objective: Objetivo da campanha em linguagem natural
        campaign_rules: Lista de regras específicas da campanha
        offer_scope: Escopo de vagas permitidas (para campanhas de oferta)
        negotiation_margin: Margem de negociação (percentual ou valor máximo)
        especialidade_id: ID da especialidade (opcional)
        diretrizes: Diretrizes do gestor
        contexto: Contexto dinamico da conversa
        memorias: Memorias do medico (RAG)
        conhecimento: Conhecimento dinâmico (E03)
        primeira_msg: Se e primeira mensagem (legado, preferir campaign_type)
        policy_constraints: Constraints da Policy Engine (E06)

    Returns:
        Prompt completo

    Exemplos:
        # Campanha de discovery
        prompt = await construir_prompt_julia(campaign_type="discovery")

        # Campanha de oferta com escopo
        prompt = await construir_prompt_julia(
            campaign_type="oferta",
            offer_scope={"especialidade": "cardiologia", "regiao": "sp"},
            negotiation_margin={"tipo": "percentual", "valor": 15}
        )

        # Comportamento legado (sem tipo de campanha)
        prompt = await construir_prompt_julia(primeira_msg=True)
    """
    builder = PromptBuilder()

    await builder.com_base()
    await builder.com_tools()

    if especialidade_id:
        await builder.com_especialidade(especialidade_id)

    # Sprint 32 E02: Priorizar campaign_type sobre primeira_msg
    if campaign_type:
        await builder.com_campanha(
            campaign_type=campaign_type,
            campaign_objective=campaign_objective,
            campaign_rules=campaign_rules,
            offer_scope=offer_scope,
            negotiation_margin=negotiation_margin,
        )
    elif primeira_msg:
        # Comportamento legado para compatibilidade
        await builder.com_primeira_msg()

    builder.com_diretrizes(diretrizes)
    builder.com_contexto(contexto)
    builder.com_memorias(memorias)
    builder.com_conhecimento(conhecimento)
    builder.com_policy_constraints(policy_constraints)

    return builder.build()
