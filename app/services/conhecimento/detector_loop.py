"""
Detector de Loop de Repetição para Julia.

Sprint 37 - Epic 7

Detecta quando Julia está repetindo respostas similares (loop).
"""
import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ResultadoLoop:
    """Resultado da detecção de loop."""

    em_loop: bool
    respostas_similares: int
    similaridade_max: float
    deve_intervir: bool
    acao_recomendada: str


class DetectorLoop:
    """
    Detecta loops de repetição nas respostas de Julia.

    Um loop é detectado quando Julia dá respostas muito similares
    repetidamente, indicando que não está progredindo na conversa.
    """

    # Threshold de similaridade para considerar respostas iguais
    THRESHOLD_SIMILARIDADE = 0.8

    # Quantidade mínima de respostas similares para detectar loop
    THRESHOLD_LOOP = 2

    # Quantidade de respostas similares para requerer intervenção
    THRESHOLD_INTERVENCAO = 3

    def __init__(self, conversa_id: Optional[str] = None):
        self.conversa_id = conversa_id
        self.historico_respostas: list[str] = []

    def adicionar_resposta(self, resposta: str) -> None:
        """
        Adiciona resposta ao histórico para análise.

        Args:
            resposta: Texto da resposta de Julia
        """
        self.historico_respostas.append(resposta)
        # Manter apenas últimas 10 respostas
        if len(self.historico_respostas) > 10:
            self.historico_respostas = self.historico_respostas[-10:]

    def detectar(self, resposta_atual: str) -> ResultadoLoop:
        """
        Detecta se resposta atual indica loop.

        Args:
            resposta_atual: Resposta que Julia pretende enviar

        Returns:
            ResultadoLoop com análise de loop
        """
        if not self.historico_respostas:
            return ResultadoLoop(
                em_loop=False,
                respostas_similares=0,
                similaridade_max=0.0,
                deve_intervir=False,
                acao_recomendada="Continuar normalmente",
            )

        # Calcular similaridade com respostas anteriores
        similaridades = []
        for resposta_anterior in self.historico_respostas:
            sim = self._calcular_similaridade(resposta_atual, resposta_anterior)
            similaridades.append(sim)

        # Contar respostas similares
        respostas_similares = sum(
            1 for sim in similaridades if sim >= self.THRESHOLD_SIMILARIDADE
        )
        similaridade_max = max(similaridades) if similaridades else 0.0

        # Detectar loop
        em_loop = respostas_similares >= self.THRESHOLD_LOOP
        deve_intervir = respostas_similares >= self.THRESHOLD_INTERVENCAO

        # Determinar ação recomendada
        if deve_intervir:
            acao = "INTERVENÇÃO NECESSÁRIA: Variar abordagem ou escalar"
        elif em_loop:
            acao = "Tentar resposta diferente"
        else:
            acao = "Continuar normalmente"

        logger.debug(
            f"DetectorLoop: similares={respostas_similares}, "
            f"max_sim={similaridade_max:.2f}, loop={em_loop}"
        )

        return ResultadoLoop(
            em_loop=em_loop,
            respostas_similares=respostas_similares,
            similaridade_max=similaridade_max,
            deve_intervir=deve_intervir,
            acao_recomendada=acao,
        )

    def limpar_historico(self) -> None:
        """Limpa histórico de respostas."""
        self.historico_respostas = []

    def _calcular_similaridade(self, texto1: str, texto2: str) -> float:
        """
        Calcula similaridade entre dois textos.

        Usa SequenceMatcher para comparação fuzzy.
        """
        # Normalizar textos
        t1 = texto1.lower().strip()
        t2 = texto2.lower().strip()

        return SequenceMatcher(None, t1, t2).ratio()


# Cache de detectores por conversa
_detectores_loop: dict[str, DetectorLoop] = {}


def get_detector_loop(conversa_id: str) -> DetectorLoop:
    """
    Retorna detector de loop para uma conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        DetectorLoop específico para a conversa
    """
    if conversa_id not in _detectores_loop:
        _detectores_loop[conversa_id] = DetectorLoop(conversa_id)
    return _detectores_loop[conversa_id]


def limpar_detector_loop(conversa_id: str) -> None:
    """Remove detector de loop de uma conversa."""
    if conversa_id in _detectores_loop:
        del _detectores_loop[conversa_id]
