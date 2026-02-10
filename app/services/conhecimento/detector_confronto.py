"""
Detector de Confronto para Julia.

Sprint 37 - Epic 6

Detecta quando médico está confrontando Julia sobre informações.
"""

import logging
import random
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

logger = logging.getLogger(__name__)


# Padrões de confronto de veracidade
PADROES_CONFRONTO = [
    r"não\s+(é|e)\s+verdade",
    r"ta\s+mentindo",
    r"está\s+mentindo",
    r"inventando",
    r"não\s+existe",
    r"nao\s+existe",
    r"isso\s+é\s+mentira",
    r"isso\s+e\s+mentira",
    r"para\s+de\s+mentir",
    r"informação\s+errada",
    r"informacao\s+errada",
    r"ta\s+errado",
    r"está\s+errado",
]

# Padrões de pergunta sobre ser bot
PADROES_PERGUNTA_BOT = [
    r"você\s+(é|e)\s+(um\s+)?(bot|robo|robô|ia|ai)",
    r"vc\s+(é|e)\s+(um\s+)?(bot|robo|robô|ia|ai)",
    r"(é|e)\s+(um\s+)?(bot|robo|robô)",
    r"resposta\s+automática",
    r"resposta\s+automatica",
    r"falando\s+com\s+(uma?\s+)?(ia|ai|robo|robô|maquina|máquina)",
]

# Frases para confronto nível 1 (primeira vez)
FRASES_CONFRONTO_NIVEL_1 = [
    "Hmm, deixa eu verificar aqui...",
    "Vou checar isso com a equipe",
    "Deixa eu confirmar essa informação",
    "Entendi, vou dar uma olhada",
]

# Frases para confronto nível 2 (segunda vez)
FRASES_CONFRONTO_NIVEL_2 = [
    "Entendi sua preocupação, vou confirmar com alguém",
    "Vou passar pra minha supervisora verificar",
    "Deixa eu pedir ajuda da equipe",
]

# Frases para confronto nível 3 (escalar)
FRASES_CONFRONTO_NIVEL_3 = [
    "Vou pedir pra alguém da equipe te ajudar direto",
    "Vou passar pro pessoal te atender melhor",
    "Deixa eu chamar alguém que pode resolver isso",
]

# Frases para resposta sobre ser bot
FRASES_RESPOSTA_BOT = [
    "Haha, por que a pergunta?",
    "Kkk que isso",
    "Por que? To parecendo automatica?",
]


class TipoConfronto(IntEnum):
    """Tipos de confronto detectados."""

    NENHUM = 0
    VERACIDADE = 1  # Médico diz que Julia está mentindo
    BOT = 2  # Médico pergunta se é bot
    COMPETENCIA = 3  # Médico questiona capacidade
    AGRESSIVO = 4  # Médico está agressivo


class NivelConfronto(IntEnum):
    """Níveis de escalação do confronto."""

    NENHUM = 0
    NIVEL_1 = 1  # Primeira vez
    NIVEL_2 = 2  # Segunda vez
    NIVEL_3 = 3  # Terceira vez ou mais (escalar)


@dataclass
class ResultadoConfronto:
    """Resultado da detecção de confronto."""

    tem_confronto: bool
    tipo: TipoConfronto
    nivel: NivelConfronto
    padrao_detectado: Optional[str]
    sugestao_frase: Optional[str]
    deve_escalar: bool


class DetectorConfronto:
    """
    Detecta confrontos em mensagens do médico.

    Níveis de resposta:
    - Nível 1: Primeira vez - verificar informação
    - Nível 2: Segunda vez - escalar para supervisora
    - Nível 3: Terceira vez+ - fazer handoff
    """

    def __init__(self):
        self.padroes_veracidade = [re.compile(p, re.IGNORECASE) for p in PADROES_CONFRONTO]
        self.padroes_bot = [re.compile(p, re.IGNORECASE) for p in PADROES_PERGUNTA_BOT]

    def detectar(
        self,
        mensagem: str,
        contador_confrontos: int = 0,
    ) -> ResultadoConfronto:
        """
        Detecta confronto em uma mensagem.

        Args:
            mensagem: Texto da mensagem do médico
            contador_confrontos: Quantos confrontos já ocorreram na conversa

        Returns:
            ResultadoConfronto com tipo, nível e sugestões
        """
        mensagem_lower = mensagem.lower()

        # Verificar confronto de veracidade
        for padrao in self.padroes_veracidade:
            match = padrao.search(mensagem_lower)
            if match:
                nivel = self._calcular_nivel(contador_confrontos + 1)
                sugestao = self._get_sugestao_veracidade(nivel)

                logger.info(
                    f"DetectorConfronto: VERACIDADE detectado, "
                    f"nivel={nivel.value}, padrao='{match.group()}'"
                )

                return ResultadoConfronto(
                    tem_confronto=True,
                    tipo=TipoConfronto.VERACIDADE,
                    nivel=nivel,
                    padrao_detectado=match.group(),
                    sugestao_frase=sugestao,
                    deve_escalar=nivel == NivelConfronto.NIVEL_3,
                )

        # Verificar pergunta sobre bot
        for padrao in self.padroes_bot:
            match = padrao.search(mensagem_lower)
            if match:
                logger.info(f"DetectorConfronto: BOT detectado, padrao='{match.group()}'")

                return ResultadoConfronto(
                    tem_confronto=True,
                    tipo=TipoConfronto.BOT,
                    nivel=NivelConfronto.NIVEL_1,  # Bot sempre nível 1 (responder com humor)
                    padrao_detectado=match.group(),
                    sugestao_frase=random.choice(FRASES_RESPOSTA_BOT),
                    deve_escalar=False,
                )

        # Nenhum confronto detectado
        return ResultadoConfronto(
            tem_confronto=False,
            tipo=TipoConfronto.NENHUM,
            nivel=NivelConfronto.NENHUM,
            padrao_detectado=None,
            sugestao_frase=None,
            deve_escalar=False,
        )

    def detectar_em_historico(
        self,
        mensagens: list[str],
    ) -> int:
        """
        Conta confrontos em um histórico de mensagens.

        Args:
            mensagens: Lista de mensagens do médico

        Returns:
            Quantidade de confrontos detectados
        """
        contador = 0
        for msg in mensagens:
            resultado = self.detectar(msg, contador_confrontos=0)
            if resultado.tem_confronto and resultado.tipo == TipoConfronto.VERACIDADE:
                contador += 1
        return contador

    def _calcular_nivel(self, contador: int) -> NivelConfronto:
        """Calcula o nível de confronto baseado no contador."""
        if contador <= 0:
            return NivelConfronto.NENHUM
        elif contador == 1:
            return NivelConfronto.NIVEL_1
        elif contador == 2:
            return NivelConfronto.NIVEL_2
        else:
            return NivelConfronto.NIVEL_3

    def _get_sugestao_veracidade(self, nivel: NivelConfronto) -> str:
        """Retorna frase sugerida para confronto de veracidade."""
        if nivel == NivelConfronto.NIVEL_1:
            return random.choice(FRASES_CONFRONTO_NIVEL_1)
        elif nivel == NivelConfronto.NIVEL_2:
            return random.choice(FRASES_CONFRONTO_NIVEL_2)
        else:  # NIVEL_3
            return random.choice(FRASES_CONFRONTO_NIVEL_3)


# Instância singleton
_detector_confronto: Optional[DetectorConfronto] = None


def get_detector_confronto() -> DetectorConfronto:
    """Retorna instância singleton do detector."""
    global _detector_confronto
    if _detector_confronto is None:
        _detector_confronto = DetectorConfronto()
    return _detector_confronto
