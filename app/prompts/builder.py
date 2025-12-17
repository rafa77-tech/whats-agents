"""
Builder de prompts - combina partes em prompt final.
"""
import logging
from typing import Optional

from .loader import carregar_prompt, carregar_prompt_especialidade

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Constroi prompt completo para o agente.

    Combina:
    - Prompt base (identidade, tom)
    - Prompt de especialidade (se houver)
    - Instrucoes de tools
    - Diretrizes do gestor
    - Contexto dinamico
    """

    def __init__(self):
        self._prompt_base: Optional[str] = None
        self._prompt_tools: Optional[str] = None
        self._prompt_especialidade: Optional[str] = None
        self._prompt_primeira_msg: Optional[str] = None
        self._diretrizes: str = ""
        self._contexto: str = ""
        self._memorias: str = ""
        self._conhecimento: str = ""  # E03: Conhecimento dinâmico RAG

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

        Returns:
            String com prompt completo
        """
        partes = []

        # 1. Prompt base (obrigatorio)
        if self._prompt_base:
            partes.append(self._prompt_base)
        else:
            logger.warning("Prompt base nao carregado!")

        # 2. Especialidade (se houver)
        if self._prompt_especialidade:
            partes.append(f"\n## ESPECIALIDADE\n{self._prompt_especialidade}")

        # 3. Tools
        if self._prompt_tools:
            partes.append(f"\n{self._prompt_tools}")

        # 4. Conhecimento dinâmico (E03 - situação detectada + RAG)
        if self._conhecimento:
            partes.append(f"\n{self._conhecimento}")

        # 5. Diretrizes do gestor
        if self._diretrizes:
            partes.append(f"\n## DIRETRIZES DO GESTOR (PRIORIDADE MAXIMA)\n{self._diretrizes}")

        # 6. Memorias do medico
        if self._memorias:
            partes.append(f"\n{self._memorias}")

        # 7. Contexto dinamico
        if self._contexto:
            partes.append(f"\n## CONTEXTO DA CONVERSA\n{self._contexto}")

        # 8. Instrucoes de primeira mensagem (se aplicavel)
        if self._prompt_primeira_msg:
            partes.append(f"\n## INSTRUCOES PARA ESTA RESPOSTA\n{self._prompt_primeira_msg}")

        return "\n".join(partes)


async def construir_prompt_julia(
    especialidade_id: str = None,
    diretrizes: str = "",
    contexto: str = "",
    memorias: str = "",
    conhecimento: str = "",
    primeira_msg: bool = False,
) -> str:
    """
    Funcao helper para construir prompt completo.

    Args:
        especialidade_id: ID da especialidade (opcional)
        diretrizes: Diretrizes do gestor
        contexto: Contexto dinamico da conversa
        memorias: Memorias do medico (RAG)
        conhecimento: Conhecimento dinâmico (E03)
        primeira_msg: Se e primeira mensagem

    Returns:
        Prompt completo
    """
    builder = PromptBuilder()

    await builder.com_base()
    await builder.com_tools()

    if especialidade_id:
        await builder.com_especialidade(especialidade_id)

    if primeira_msg:
        await builder.com_primeira_msg()

    builder.com_diretrizes(diretrizes)
    builder.com_contexto(contexto)
    builder.com_memorias(memorias)
    builder.com_conhecimento(conhecimento)

    return builder.build()
