"""
Detector de Contradição para Julia.

Sprint 37 - Epic 8

Detecta quando Julia contradiz informações que deu anteriormente.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# Padrões para extrair valores monetários
PADRAO_VALOR = re.compile(r"R\$\s*([\d.,]+)")

# Padrões para extrair hospitais
PADRAO_HOSPITAL = re.compile(
    r"hospital\s+([A-Za-zÀ-ú\s]+?)(?:\s+(?:tem|paga|fica|é|e)|[,.\n])",
    re.IGNORECASE,
)


@dataclass
class ResultadoContradicao:
    """Resultado da detecção de contradição."""

    tem_contradicao: bool
    tipo_contradicao: Optional[str]  # "valor", "hospital", "data", etc.
    valor_anterior: Optional[str]
    valor_atual: Optional[str]
    acao_recomendada: str


class DetectorContradicao:
    """
    Detecta contradições nas respostas de Julia.

    Compara informações entre respostas para identificar
    quando Julia diz algo diferente do que disse antes.
    """

    def __init__(self, conversa_id: Optional[str] = None):
        self.conversa_id = conversa_id
        self.historico_respostas: list[str] = []
        self.valores_mencionados: list[str] = []
        self.hospitais_mencionados: list[str] = []

    def adicionar_resposta(self, resposta: str) -> None:
        """
        Adiciona resposta ao histórico para análise.

        Args:
            resposta: Texto da resposta de Julia
        """
        self.historico_respostas.append(resposta)

        # Extrair valores mencionados
        valores = PADRAO_VALOR.findall(resposta)
        self.valores_mencionados.extend(valores)

        # Extrair hospitais mencionados
        hospitais = PADRAO_HOSPITAL.findall(resposta)
        self.hospitais_mencionados.extend([h.strip() for h in hospitais])

        # Manter apenas últimas 10 respostas
        if len(self.historico_respostas) > 10:
            self.historico_respostas = self.historico_respostas[-10:]

    def detectar(self, resposta_atual: str) -> ResultadoContradicao:
        """
        Detecta contradição em uma resposta.

        Args:
            resposta_atual: Resposta que Julia pretende enviar

        Returns:
            ResultadoContradicao com análise
        """
        if not self.historico_respostas:
            return ResultadoContradicao(
                tem_contradicao=False,
                tipo_contradicao=None,
                valor_anterior=None,
                valor_atual=None,
                acao_recomendada="Continuar normalmente",
            )

        # Verificar contradição de valor
        contradicao_valor = self._verificar_contradicao_valor(resposta_atual)
        if contradicao_valor:
            return contradicao_valor

        # Verificar contradição de hospital
        contradicao_hospital = self._verificar_contradicao_hospital(resposta_atual)
        if contradicao_hospital:
            return contradicao_hospital

        return ResultadoContradicao(
            tem_contradicao=False,
            tipo_contradicao=None,
            valor_anterior=None,
            valor_atual=None,
            acao_recomendada="Continuar normalmente",
        )

    def _verificar_contradicao_valor(self, resposta_atual: str) -> Optional[ResultadoContradicao]:
        """Verifica contradição de valores monetários."""
        valores_atuais = PADRAO_VALOR.findall(resposta_atual)

        if not valores_atuais or not self.valores_mencionados:
            return None

        valor_atual = valores_atuais[0]
        valor_anterior = self.valores_mencionados[-1]

        # Converter para float para comparação
        try:
            v_atual = float(valor_atual.replace(".", "").replace(",", "."))
            v_anterior = float(valor_anterior.replace(".", "").replace(",", "."))

            # Se valores são diferentes por mais de 10%
            if abs(v_atual - v_anterior) / v_anterior > 0.1:
                logger.info(f"DetectorContradicao: VALOR anterior={v_anterior}, atual={v_atual}")
                return ResultadoContradicao(
                    tem_contradicao=True,
                    tipo_contradicao="valor",
                    valor_anterior=f"R$ {valor_anterior}",
                    valor_atual=f"R$ {valor_atual}",
                    acao_recomendada="CONTRADIÇÃO: Esclarecer diferença de valor",
                )
        except (ValueError, ZeroDivisionError):
            pass

        return None

    def _verificar_contradicao_hospital(
        self, resposta_atual: str
    ) -> Optional[ResultadoContradicao]:
        """Verifica contradição de hospital mencionado."""
        hospitais_atuais = PADRAO_HOSPITAL.findall(resposta_atual)

        if not hospitais_atuais or not self.hospitais_mencionados:
            return None

        hospital_atual = hospitais_atuais[0].strip().lower()
        hospital_anterior = self.hospitais_mencionados[-1].lower()

        # Se hospitais são diferentes
        if hospital_atual != hospital_anterior:
            # Verificar se não são variações do mesmo nome
            if not self._sao_mesmo_hospital(hospital_atual, hospital_anterior):
                logger.info(
                    f"DetectorContradicao: HOSPITAL anterior={hospital_anterior}, "
                    f"atual={hospital_atual}"
                )
                return ResultadoContradicao(
                    tem_contradicao=True,
                    tipo_contradicao="hospital",
                    valor_anterior=hospital_anterior.title(),
                    valor_atual=hospital_atual.title(),
                    acao_recomendada="CONTRADIÇÃO: Esclarecer qual hospital",
                )

        return None

    def _sao_mesmo_hospital(self, nome1: str, nome2: str) -> bool:
        """Verifica se dois nomes são do mesmo hospital."""
        # Verificação simples - um contém o outro
        return nome1 in nome2 or nome2 in nome1

    def limpar_historico(self) -> None:
        """Limpa histórico."""
        self.historico_respostas = []
        self.valores_mencionados = []
        self.hospitais_mencionados = []


# Cache de detectores por conversa
_detectores_contradicao: dict[str, DetectorContradicao] = {}


def get_detector_contradicao(conversa_id: str) -> DetectorContradicao:
    """
    Retorna detector de contradição para uma conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        DetectorContradicao específico para a conversa
    """
    if conversa_id not in _detectores_contradicao:
        _detectores_contradicao[conversa_id] = DetectorContradicao(conversa_id)
    return _detectores_contradicao[conversa_id]


def limpar_detector_contradicao(conversa_id: str) -> None:
    """Remove detector de contradição de uma conversa."""
    if conversa_id in _detectores_contradicao:
        del _detectores_contradicao[conversa_id]
