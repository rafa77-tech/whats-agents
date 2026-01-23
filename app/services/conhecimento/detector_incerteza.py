"""
Detector de Incerteza para Julia.

Sprint 37 - Epic 5

Detecta quando Julia deve comunicar incerteza sobre informações.
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# Níveis de incerteza por confiança
NIVEL_INCERTEZA = {
    "alta": 0.3,  # Abaixo de 0.3 = incerteza alta
    "moderada": 0.5,  # 0.3 - 0.5 = incerteza moderada
    "baixa": 0.7,  # 0.5 - 0.7 = incerteza baixa
    "nenhuma": 1.0,  # Acima de 0.7 = sem incerteza
}

# Frases para comunicar incerteza
FRASES_INCERTEZA = [
    "Deixa eu confirmar aqui...",
    "To vendo aqui... um segundo",
    "Hmm, deixa eu checar isso",
    "Vou verificar com a equipe",
]


@dataclass
class ResultadoIncerteza:
    """Resultado da análise de incerteza."""

    confianca: float
    deve_comunicar_incerteza: bool
    nivel_incerteza: str  # "alta", "moderada", "baixa", "nenhuma"
    fatores: dict
    sugestao_frase: Optional[str]


class DetectorIncerteza:
    """Detecta e calcula incerteza sobre informações."""

    # Threshold abaixo do qual deve comunicar incerteza
    THRESHOLD_COMUNICAR = NIVEL_INCERTEZA["baixa"]  # 0.7 - Abaixo disso, comunicar
    THRESHOLD_ESCALAR = NIVEL_INCERTEZA["alta"]  # 0.3 - Abaixo disso, considerar escalar

    # Pesos para cada fator na confiança agregada
    PESOS = {
        "dados_vagas": 0.30,
        "dados_hospital": 0.25,
        "dados_medico": 0.20,
        "memorias": 0.15,
        "confrontos": 0.10,
    }

    def __init__(self):
        self.frases_incerteza = FRASES_INCERTEZA

    def calcular_confianca(
        self,
        confianca_vagas: Optional[float] = None,
        confianca_hospital: Optional[float] = None,
        dados_medico_completos: bool = True,
        similaridade_memorias: Optional[float] = None,
        contador_confrontos: int = 0,
    ) -> ResultadoIncerteza:
        """
        Calcula score de confiança agregado.

        Args:
            confianca_vagas: Confiança nos dados de vagas (0.0 - 1.0)
            confianca_hospital: Confiança nos dados do hospital (0.0 - 1.0)
            dados_medico_completos: Se dados do médico estão completos
            similaridade_memorias: Similaridade de memórias encontradas (0.0 - 1.0)
            contador_confrontos: Quantos confrontos já ocorreram

        Returns:
            ResultadoIncerteza com score agregado e recomendações
        """
        fatores = {}

        # Fator 1: Confiança em dados de vagas
        fatores["dados_vagas"] = confianca_vagas if confianca_vagas is not None else 1.0

        # Fator 2: Confiança em dados do hospital
        fatores["dados_hospital"] = (
            confianca_hospital if confianca_hospital is not None else 1.0
        )

        # Fator 3: Dados do médico
        fatores["dados_medico"] = 1.0 if dados_medico_completos else 0.5

        # Fator 4: Similaridade de memórias
        fatores["memorias"] = (
            similaridade_memorias if similaridade_memorias is not None else 0.8
        )

        # Fator 5: Histórico de confrontos (reduz confiança)
        if contador_confrontos == 0:
            fatores["confrontos"] = 1.0
        elif contador_confrontos == 1:
            fatores["confrontos"] = 0.8
        else:
            fatores["confrontos"] = 0.5

        # Calcular confiança agregada com pesos
        confianca_total = sum(
            fatores[fator] * self.PESOS[fator] for fator in self.PESOS
        )

        # Determinar nível de incerteza
        if confianca_total >= self.THRESHOLD_COMUNICAR:
            nivel = "nenhuma"
        elif confianca_total >= self.THRESHOLD_ESCALAR:
            nivel = "baixa" if confianca_total >= 0.5 else "moderada"
        else:
            nivel = "alta"

        # Verificar se deve comunicar incerteza
        deve_comunicar = confianca_total < self.THRESHOLD_COMUNICAR

        # Selecionar frase sugerida se necessário
        sugestao = None
        if deve_comunicar:
            import random

            sugestao = random.choice(self.frases_incerteza)

        logger.debug(
            f"DetectorIncerteza: confianca={confianca_total:.2f}, "
            f"nivel={nivel}, comunicar={deve_comunicar}"
        )

        return ResultadoIncerteza(
            confianca=confianca_total,
            deve_comunicar_incerteza=deve_comunicar,
            nivel_incerteza=nivel,
            fatores=fatores,
            sugestao_frase=sugestao,
        )


# Instância singleton
_detector_incerteza: Optional[DetectorIncerteza] = None


def get_detector_incerteza() -> DetectorIncerteza:
    """Retorna instância singleton do detector."""
    global _detector_incerteza
    if _detector_incerteza is None:
        _detector_incerteza = DetectorIncerteza()
    return _detector_incerteza
