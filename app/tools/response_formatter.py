"""
Formatador de respostas de tools.

Sprint 31 - S31.E5.3

Centraliza a formatação de respostas das tools para o LLM,
garantindo consistência e facilitando manutenção.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResponse:
    """Resposta padronizada de uma tool."""

    success: bool = True
    error: Optional[str] = None
    data: dict = field(default_factory=dict)
    mensagem_sugerida: Optional[str] = None
    instrucao: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Converte para dict para retorno da tool."""
        result = {"success": self.success}

        if self.error:
            result["error"] = self.error

        if self.data:
            result.update(self.data)

        if self.mensagem_sugerida:
            result["mensagem_sugerida"] = self.mensagem_sugerida

        if self.instrucao:
            result["instrucao"] = self.instrucao

        return result


class VagasResponseFormatter:
    """
    Formatador de respostas para tools de vagas.

    Responsabilidades:
    - Formatar vagas para resumo
    - Gerar mensagens sugeridas
    - Gerar instruções para o LLM
    """

    @staticmethod
    def formatar_valor_display(vaga: dict) -> str:
        """
        Formata valor para exibição na resposta da tool.

        Args:
            vaga: Dados da vaga

        Returns:
            String formatada para exibição
        """
        valor_tipo = vaga.get("valor_tipo", "fixo")
        valor = vaga.get("valor")
        valor_minimo = vaga.get("valor_minimo")
        valor_maximo = vaga.get("valor_maximo")

        if valor_tipo == "fixo" and valor:
            return f"R$ {valor:,.0f}".replace(",", ".")

        elif valor_tipo == "faixa":
            if valor_minimo and valor_maximo:
                return f"R$ {valor_minimo:,.0f} a R$ {valor_maximo:,.0f}".replace(",", ".")
            elif valor_minimo:
                return f"a partir de R$ {valor_minimo:,.0f}".replace(",", ".")
            elif valor_maximo:
                return f"ate R$ {valor_maximo:,.0f}".replace(",", ".")

        elif valor_tipo == "a_combinar":
            return "a combinar"

        if valor:
            return f"R$ {valor:,.0f}".replace(",", ".")

        return "nao informado"

    def formatar_vagas_resumo(
        self,
        vagas: list[dict],
        especialidade_nome: Optional[str] = None
    ) -> list[dict]:
        """
        Formata lista de vagas para resumo da tool.

        Args:
            vagas: Lista de vagas com dados relacionados
            especialidade_nome: Nome da especialidade (fallback)

        Returns:
            Lista de dicts com dados resumidos
        """
        resumo = []

        for v in vagas:
            hospitais = v.get("hospitais") or {}
            periodos = v.get("periodos") or {}
            setores = v.get("setores") or {}
            especialidades = v.get("especialidades") or {}

            resumo.append({
                # UUID PARA USO INTERNO - use este ID ao chamar criar_handoff_externo
                "VAGA_ID_PARA_HANDOFF": v.get("id"),
                "hospital": hospitais.get("nome") if isinstance(hospitais, dict) else None,
                "cidade": hospitais.get("cidade") if isinstance(hospitais, dict) else None,
                "data": v.get("data"),
                "periodo": periodos.get("nome") if isinstance(periodos, dict) else None,
                # Campos de valor expandidos (Sprint 19)
                "valor": v.get("valor"),
                "valor_minimo": v.get("valor_minimo"),
                "valor_maximo": v.get("valor_maximo"),
                "valor_tipo": v.get("valor_tipo", "fixo"),
                "valor_display": self.formatar_valor_display(v),
                "setor": setores.get("nome") if isinstance(setores, dict) else None,
                "especialidade": (
                    (especialidades.get("nome") if isinstance(especialidades, dict) else None)
                    or especialidade_nome
                ),
            })

        return resumo

    def construir_instrucao_vagas(
        self,
        especialidade_nome: str,
        especialidade_diferente: bool = False,
        especialidade_cadastrada: Optional[str] = None
    ) -> str:
        """
        Constrói instrução base para apresentação de vagas.

        Args:
            especialidade_nome: Nome da especialidade buscada
            especialidade_diferente: Se é diferente da cadastrada
            especialidade_cadastrada: Nome da especialidade cadastrada

        Returns:
            Instrução formatada para o LLM
        """
        instrucao = (
            f"Estas vagas sao de {especialidade_nome}. "
            "Apresente as vagas de forma natural, uma por vez. "
            "SEMPRE mencione a DATA do plantao (dia/mes). "
            "\n\n"
            "CRITICO - HANDOFF:\n"
            "- Cada vaga tem um campo 'VAGA_ID_PARA_HANDOFF' (UUID)\n"
            "- Quando o medico aceitar ('fechou', 'quero essa'), use criar_handoff_externo\n"
            "- O parametro vaga_id DEVE ser o valor de VAGA_ID_PARA_HANDOFF\n"
            "- NUNCA pergunte o ID ao medico - voce ja tem nos dados acima\n"
            "- NUNCA invente IDs - use EXATAMENTE o UUID que esta em VAGA_ID_PARA_HANDOFF\n"
            "\n"
            "IMPORTANTE: Para vagas 'a combinar', informe que o valor sera negociado com o responsavel. "
            "Nao invente valores - use apenas o que esta nos dados da vaga."
        )

        # Alerta se especialidade diferente da cadastrada
        if especialidade_diferente and especialidade_cadastrada:
            alerta = (
                f"ALERTA: O medico pediu vagas de {especialidade_nome}, mas o cadastro dele e {especialidade_cadastrada}. "
                f"Mencione naturalmente que encontrou vagas de {especialidade_nome} como ele pediu, "
                f"mas confirme se ele tambem atua nessa area ou se quer ver vagas de {especialidade_cadastrada}. "
            )
            instrucao = alerta + instrucao

        return instrucao

    def mensagem_sem_vagas(
        self,
        especialidade_nome: str,
        total_sem_filtros: int = 0,
        filtros_aplicados: Optional[list[str]] = None,
        especialidade_diferente: bool = False,
        especialidade_cadastrada: Optional[str] = None
    ) -> str:
        """
        Gera mensagem sugerida quando não há vagas.

        Args:
            especialidade_nome: Nome da especialidade buscada
            total_sem_filtros: Total antes dos filtros
            filtros_aplicados: Lista de filtros aplicados
            especialidade_diferente: Se especialidade é diferente da cadastrada
            especialidade_cadastrada: Nome da especialidade cadastrada

        Returns:
            Mensagem sugerida
        """
        # Se havia vagas mas os filtros eliminaram tudo
        if total_sem_filtros > 0 and filtros_aplicados:
            return (
                f"Nao encontrei vagas de {especialidade_nome} com {' e '.join(filtros_aplicados)}. "
                f"Mas tem {total_sem_filtros} vagas de {especialidade_nome} no geral. Quer ver?"
            )

        # Se buscou especialidade diferente da cadastrada e não encontrou
        if especialidade_diferente and especialidade_cadastrada:
            return (
                f"Nao tenho vaga de {especialidade_nome} no momento. "
                f"Mas vi que voce e de {especialidade_cadastrada} - quer que eu veja as vagas dessa especialidade?"
            )

        # Mensagem padrão
        return f"Nao tem vaga de {especialidade_nome} no momento. Mas assim que surgir algo, te aviso!"

    def mensagem_especialidade_nao_encontrada(self, especialidade: str) -> str:
        """Mensagem quando especialidade não existe."""
        return f"Nao conheco a especialidade '{especialidade}'. Pode confirmar o nome?"

    def mensagem_especialidade_nao_identificada(self) -> str:
        """Mensagem quando médico não tem especialidade."""
        return "Qual especialidade voce quer buscar? Me fala que eu procuro pra voce"

    def mensagem_erro_generico(self) -> str:
        """Mensagem de erro genérico."""
        return "Tive um probleminha aqui, me da um minuto que ja te mostro as vagas"


class ReservaResponseFormatter:
    """
    Formatador de respostas para reserva de plantão.
    """

    @staticmethod
    def construir_instrucao_confirmacao(vaga: dict, hospital_data: dict) -> str:
        """
        Constrói instrução de confirmação baseada no tipo de valor.

        Args:
            vaga: Dados da vaga
            hospital_data: Dados do hospital

        Returns:
            Instrução para o LLM
        """
        valor_tipo = vaga.get("valor_tipo", "fixo")
        endereco = hospital_data.get("endereco_formatado") or "endereco nao disponivel"

        instrucao = "Confirme a reserva mencionando o hospital, data e periodo. "

        if valor_tipo == "fixo":
            valor = vaga.get("valor")
            if valor:
                instrucao += f"Mencione o valor de R$ {valor}. "
        elif valor_tipo == "faixa":
            instrucao += "Mencione que o valor sera dentro da faixa acordada. "
        elif valor_tipo == "a_combinar":
            instrucao += (
                "Informe que o valor sera combinado diretamente com o hospital/gestor. "
                "Pergunte se o medico tem alguma expectativa de valor para repassar. "
            )

        instrucao += f"Se o medico perguntar o endereco, use: {endereco}"

        return instrucao

    @staticmethod
    def construir_instrucao_ponte_externa(
        vaga: dict,
        hospital_data: dict,
        ponte_externa: dict,
        medico: dict,
    ) -> str:
        """
        Constrói instrução de confirmação para vaga com ponte externa.

        Sprint 20 - Marketplace assistido.

        Args:
            vaga: Dados da vaga
            hospital_data: Dados do hospital
            ponte_externa: Resultado da criação da ponte
            medico: Dados do médico

        Returns:
            Instrução para o LLM
        """
        divulgador = ponte_externa.get("divulgador", {})
        divulgador_nome = divulgador.get("nome", "o responsavel")
        divulgador_tel = divulgador.get("telefone", "")
        divulgador_empresa = divulgador.get("empresa", "")

        # Montar info do divulgador
        info_divulgador = divulgador_nome
        if divulgador_empresa:
            info_divulgador += f" ({divulgador_empresa})"

        instrucao = (
            f"IMPORTANTE: Esta vaga e de um divulgador externo ({info_divulgador}). "
            f"Voce JA ENTROU EM CONTATO com ele e passou os dados do medico.\n\n"
            f"Informe ao medico que:\n"
            f"1. Voce reservou a vaga\n"
            f"2. Ja contatou o responsavel ({divulgador_nome})"
        )

        if divulgador_tel:
            instrucao += f"\n3. Passe o contato: {divulgador_tel}"

        instrucao += (
            "\n\nPeca para o medico confirmar aqui quando fechar o plantao. "
            "Fale de forma natural, como se voce tivesse acabado de fazer a ponte entre eles."
        )

        # Adicionar info de valor se aplicável
        valor_tipo = vaga.get("valor_tipo", "fixo")
        if valor_tipo == "a_combinar":
            instrucao += (
                "\n\nComo o valor e 'a combinar', mencione que o medico deve "
                "negociar diretamente com o divulgador."
            )

        return instrucao


# Singleton factories
_vagas_formatter: Optional[VagasResponseFormatter] = None
_reserva_formatter: Optional[ReservaResponseFormatter] = None


def get_vagas_formatter() -> VagasResponseFormatter:
    """Retorna instância singleton do formatter de vagas."""
    global _vagas_formatter
    if _vagas_formatter is None:
        _vagas_formatter = VagasResponseFormatter()
    return _vagas_formatter


def get_reserva_formatter() -> ReservaResponseFormatter:
    """Retorna instância singleton do formatter de reserva."""
    global _reserva_formatter
    if _reserva_formatter is None:
        _reserva_formatter = ReservaResponseFormatter()
    return _reserva_formatter
