"""
Detector de objetivo da conversa.

Identifica em que fase a conversa está para adaptar a estratégia.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ObjetivoConversa(str, Enum):
    """Objetivos/fases da conversa."""

    PROSPECTAR = "prospectar"  # Primeiro contato, quebrar gelo
    QUALIFICAR = "qualificar"  # Descobrir interesse, preferências
    OFERTAR = "ofertar"  # Apresentar vagas específicas
    NEGOCIAR = "negociar"  # Resolver objeções, ajustar oferta
    FECHAR = "fechar"  # Confirmar reserva, coletar documentos
    MANTER = "manter"  # Relacionamento pós-venda
    REATIVAR = "reativar"  # Médico inativo/não respondeu
    RECUPERAR = "recuperar"  # Médico com objeção forte


@dataclass
class ResultadoObjetivo:
    """Resultado da detecção de objetivo."""

    objetivo: ObjetivoConversa
    confianca: float
    indicadores: list[str]
    proxima_acao: Optional[str] = None  # Sugestão do que fazer


class DetectorObjetivo:
    """Detecta objetivo da conversa baseado no contexto."""

    # Mapeamento stage -> objetivo
    STAGE_PARA_OBJETIVO = {
        "novo": ObjetivoConversa.PROSPECTAR,
        "lead": ObjetivoConversa.PROSPECTAR,
        "msg_enviada": ObjetivoConversa.QUALIFICAR,
        "aguardando_resposta": ObjetivoConversa.QUALIFICAR,
        "respondeu": ObjetivoConversa.QUALIFICAR,
        "em_conversacao": ObjetivoConversa.OFERTAR,
        "qualificado": ObjetivoConversa.OFERTAR,
        "nao_respondeu": ObjetivoConversa.REATIVAR,
        "inativo": ObjetivoConversa.REATIVAR,
        "reservou": ObjetivoConversa.FECHAR,
        "cadastrado": ObjetivoConversa.MANTER,
        "ativo": ObjetivoConversa.MANTER,
        "perdido": ObjetivoConversa.RECUPERAR,
        "opt_out": ObjetivoConversa.RECUPERAR,  # Não deveria chegar aqui
    }

    # Próximas ações por objetivo
    PROXIMAS_ACOES = {
        ObjetivoConversa.PROSPECTAR: "Apresente-se brevemente, faça uma pergunta aberta para iniciar conversa.",
        ObjetivoConversa.QUALIFICAR: "Descubra preferências: turno, região, tipo de plantão, disponibilidade.",
        ObjetivoConversa.OFERTAR: "Apresente vagas específicas que combinam com o perfil.",
        ObjetivoConversa.NEGOCIAR: "Use técnica LAAR: Listen, Acknowledge, Ask, Respond.",
        ObjetivoConversa.FECHAR: "Confirme a reserva e solicite documentos necessários.",
        ObjetivoConversa.MANTER: "Mantenha relacionamento, pergunte como foi o plantão, ofereça novas oportunidades.",
        ObjetivoConversa.REATIVAR: "Retome contato de forma leve, sem pressão. Pergunte se continua disponível.",
        ObjetivoConversa.RECUPERAR: "Aborde com cuidado, reconheça objeção anterior, ofereça alternativa.",
    }

    def detectar_por_stage(self, stage: str) -> ResultadoObjetivo:
        """
        Detecta objetivo baseado no stage da jornada.

        Args:
            stage: Stage atual do cliente (stage_jornada)

        Returns:
            ResultadoObjetivo
        """
        objetivo = self.STAGE_PARA_OBJETIVO.get(stage, ObjetivoConversa.PROSPECTAR)

        return ResultadoObjetivo(
            objetivo=objetivo,
            confianca=0.85,
            indicadores=[f"stage:{stage}"],
            proxima_acao=self.PROXIMAS_ACOES[objetivo],
        )

    def detectar_por_contexto(
        self,
        mensagens_recentes: list[str],
        tem_vagas_oferecidas: bool = False,
        tem_objecao: bool = False,
        tem_reserva: bool = False,
        dias_desde_ultima_msg: int = 0,
    ) -> ResultadoObjetivo:
        """
        Detecta objetivo baseado no contexto da conversa.

        Args:
            mensagens_recentes: Últimas mensagens
            tem_vagas_oferecidas: Se já ofereceu vagas
            tem_objecao: Se há objeção pendente
            tem_reserva: Se tem reserva ativa
            dias_desde_ultima_msg: Dias desde última mensagem

        Returns:
            ResultadoObjetivo
        """
        indicadores = []

        # 1. Prioridade: objeção pendente -> NEGOCIAR
        if tem_objecao:
            indicadores.append("tem_objecao")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.NEGOCIAR,
                confianca=0.9,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.NEGOCIAR],
            )

        # 2. Tem reserva -> FECHAR
        if tem_reserva:
            indicadores.append("tem_reserva")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.FECHAR,
                confianca=0.9,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.FECHAR],
            )

        # 3. Inativo -> REATIVAR
        if dias_desde_ultima_msg > 7:
            indicadores.append(f"inativo_{dias_desde_ultima_msg}_dias")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.REATIVAR,
                confianca=0.85,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.REATIVAR],
            )

        # 4. Já ofereceu vagas -> OFERTAR ou NEGOCIAR
        if tem_vagas_oferecidas:
            indicadores.append("vagas_oferecidas")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.OFERTAR,
                confianca=0.75,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.OFERTAR],
            )

        # 5. Tem mensagens -> QUALIFICAR
        if mensagens_recentes:
            indicadores.append("tem_historico")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.QUALIFICAR,
                confianca=0.7,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.QUALIFICAR],
            )

        # 6. Default -> PROSPECTAR
        return ResultadoObjetivo(
            objetivo=ObjetivoConversa.PROSPECTAR,
            confianca=0.6,
            indicadores=["primeiro_contato"],
            proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.PROSPECTAR],
        )

    def detectar_por_mensagem(self, mensagem: str) -> ResultadoObjetivo:
        """
        Detecta objetivo baseado na última mensagem do médico.

        Args:
            mensagem: Última mensagem recebida

        Returns:
            ResultadoObjetivo inferido
        """
        mensagem_lower = mensagem.lower()
        indicadores = []

        # Sinais de fechamento
        sinais_fechar = [
            "quero",
            "reserva",
            "confirma",
            "pode ser",
            "aceito",
            "combinado",
            "fechado",
            "beleza",
            "blz",
        ]
        if any(s in mensagem_lower for s in sinais_fechar):
            indicadores.append("sinal_fechamento")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.FECHAR,
                confianca=0.8,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.FECHAR],
            )

        # Sinais de interesse/qualificação
        sinais_qualificar = [
            "como funciona",
            "quais vagas",
            "tem vaga",
            "região",
            "regiao",
            "horário",
            "horario",
            "valor",
            "quanto",
            "especialidade",
        ]
        if any(s in mensagem_lower for s in sinais_qualificar):
            indicadores.append("sinal_interesse")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.QUALIFICAR,
                confianca=0.75,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.QUALIFICAR],
            )

        # Sinais de negociação/objeção
        sinais_negociar = [
            "mas",
            "porém",
            "entretanto",
            "não sei",
            "preciso pensar",
            "depois",
            "talvez",
            "não tenho certeza",
        ]
        if any(s in mensagem_lower for s in sinais_negociar):
            indicadores.append("sinal_negociacao")
            return ResultadoObjetivo(
                objetivo=ObjetivoConversa.NEGOCIAR,
                confianca=0.65,
                indicadores=indicadores,
                proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.NEGOCIAR],
            )

        # Default - manter conversa
        return ResultadoObjetivo(
            objetivo=ObjetivoConversa.QUALIFICAR,
            confianca=0.5,
            indicadores=["inferido"],
            proxima_acao=self.PROXIMAS_ACOES[ObjetivoConversa.QUALIFICAR],
        )

    async def detectar_completo(
        self,
        mensagem: str,
        stage: str,
        historico: list[str] = None,
        tem_vagas_oferecidas: bool = False,
        tem_objecao: bool = False,
        tem_reserva: bool = False,
        dias_inativo: int = 0,
    ) -> ResultadoObjetivo:
        """
        Detecção completa combinando todas as fontes.

        Args:
            mensagem: Última mensagem
            stage: Stage atual
            historico: Mensagens anteriores
            tem_vagas_oferecidas: Se já ofereceu vagas
            tem_objecao: Se detectou objeção
            tem_reserva: Se tem reserva
            dias_inativo: Dias sem interação

        Returns:
            ResultadoObjetivo com maior confiança
        """
        # Coletar resultados de cada fonte
        resultados = []

        # 1. Por stage
        resultado_stage = self.detectar_por_stage(stage)
        resultados.append(resultado_stage)

        # 2. Por contexto
        resultado_contexto = self.detectar_por_contexto(
            mensagens_recentes=historico or [],
            tem_vagas_oferecidas=tem_vagas_oferecidas,
            tem_objecao=tem_objecao,
            tem_reserva=tem_reserva,
            dias_desde_ultima_msg=dias_inativo,
        )
        resultados.append(resultado_contexto)

        # 3. Por mensagem
        if mensagem:
            resultado_mensagem = self.detectar_por_mensagem(mensagem)
            resultados.append(resultado_mensagem)

        # Escolher o de maior confiança
        melhor = max(resultados, key=lambda r: r.confianca)

        # Combinar indicadores
        todos_indicadores = []
        for r in resultados:
            todos_indicadores.extend(r.indicadores)

        return ResultadoObjetivo(
            objetivo=melhor.objetivo,
            confianca=melhor.confianca,
            indicadores=list(set(todos_indicadores)),
            proxima_acao=melhor.proxima_acao,
        )
