"""
Human Simulator - Simula comportamento humano no WhatsApp.

Evita detecção de automação através de:
- Delays variáveis baseados em tamanho da mensagem
- Indicador de "digitando" antes de enviar
- Marcação de leitura com atraso natural
- Pausas aleatórias entre ações
- Variações de horário realistas
"""
import random
import asyncio
import logging
from typing import Optional
from datetime import datetime, time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TypingSpeed(str, Enum):
    """Velocidades de digitação simuladas."""
    RAPIDO = "rapido"      # 300+ CPM (chars per minute)
    NORMAL = "normal"      # 200-300 CPM
    LENTO = "lento"        # 100-200 CPM
    MUITO_LENTO = "muito_lento"  # <100 CPM


@dataclass
class HumanProfile:
    """Perfil de comportamento humano."""
    typing_speed: TypingSpeed = TypingSpeed.NORMAL
    read_delay_min: float = 1.0      # Segundos antes de marcar lido
    read_delay_max: float = 5.0
    think_delay_min: float = 2.0     # Segundos "pensando" antes de digitar
    think_delay_max: float = 8.0
    typo_chance: float = 0.05        # Chance de "errar" e corrigir
    emoji_chance: float = 0.1        # Chance de adicionar emoji casual
    break_chance: float = 0.02       # Chance de pausar (simula distração)
    break_duration_min: float = 10.0
    break_duration_max: float = 60.0


# Perfis predefinidos
PROFILES = {
    "julia_engajada": HumanProfile(
        typing_speed=TypingSpeed.RAPIDO,
        read_delay_min=0.5,
        read_delay_max=2.0,
        think_delay_min=1.0,
        think_delay_max=4.0,
        typo_chance=0.03,
        emoji_chance=0.15,
        break_chance=0.01,
    ),
    "julia_normal": HumanProfile(
        typing_speed=TypingSpeed.NORMAL,
        read_delay_min=1.0,
        read_delay_max=4.0,
        think_delay_min=2.0,
        think_delay_max=6.0,
        typo_chance=0.05,
        emoji_chance=0.1,
        break_chance=0.02,
    ),
    "julia_ocupada": HumanProfile(
        typing_speed=TypingSpeed.LENTO,
        read_delay_min=5.0,
        read_delay_max=30.0,
        think_delay_min=10.0,
        think_delay_max=60.0,
        typo_chance=0.07,
        emoji_chance=0.05,
        break_chance=0.05,
    ),
    "warmup_cuidadoso": HumanProfile(
        typing_speed=TypingSpeed.LENTO,
        read_delay_min=3.0,
        read_delay_max=10.0,
        think_delay_min=5.0,
        think_delay_max=15.0,
        typo_chance=0.02,
        emoji_chance=0.08,
        break_chance=0.01,
    ),
}


class HumanSimulator:
    """Simulador de comportamento humano."""

    # Chars por minuto por velocidade
    CPM_RANGES = {
        TypingSpeed.RAPIDO: (300, 400),
        TypingSpeed.NORMAL: (200, 300),
        TypingSpeed.LENTO: (100, 200),
        TypingSpeed.MUITO_LENTO: (50, 100),
    }

    # Horários de atividade (8h-20h com variação)
    HORARIO_INICIO = time(8, 0)
    HORARIO_FIM = time(20, 0)

    # Emojis casuais que Julia usa
    EMOJIS_CASUAIS = ["😊", "👍", "✨", "💪", "🙌", "😄", "👏"]

    def __init__(self, profile: Optional[HumanProfile] = None):
        """
        Inicializa simulador.

        Args:
            profile: Perfil de comportamento (usa julia_normal se não especificado)
        """
        self.profile = profile or PROFILES["julia_normal"]

    async def calcular_delay_digitacao(self, mensagem: str) -> float:
        """
        Calcula delay de digitação baseado no tamanho da mensagem.

        Args:
            mensagem: Texto a ser "digitado"

        Returns:
            Segundos de delay
        """
        chars = len(mensagem)

        # CPM com variação aleatória
        cpm_min, cpm_max = self.CPM_RANGES[self.profile.typing_speed]
        cpm = random.uniform(cpm_min, cpm_max)

        # Tempo base em segundos
        tempo_base = (chars / cpm) * 60

        # Adicionar variação natural (+/- 20%)
        variacao = random.uniform(0.8, 1.2)
        tempo_final = tempo_base * variacao

        # Mínimo de 0.5s, máximo de 120s
        return max(0.5, min(120.0, tempo_final))

    async def calcular_delay_leitura(self, mensagem: str) -> float:
        """
        Calcula delay antes de marcar mensagem como lida.

        Args:
            mensagem: Texto recebido

        Returns:
            Segundos de delay
        """
        # Base do perfil
        base = random.uniform(
            self.profile.read_delay_min,
            self.profile.read_delay_max
        )

        # Mensagens maiores demoram mais para "ler"
        chars = len(mensagem)
        leitura_extra = chars / 500  # ~500 chars por segundo de leitura

        return base + leitura_extra

    async def calcular_delay_pensamento(self) -> float:
        """
        Calcula delay de "pensamento" antes de começar a digitar.

        Returns:
            Segundos de delay
        """
        base = random.uniform(
            self.profile.think_delay_min,
            self.profile.think_delay_max
        )

        # Chance de pausa extra (distração)
        if random.random() < self.profile.break_chance:
            pausa = random.uniform(
                self.profile.break_duration_min,
                self.profile.break_duration_max
            )
            logger.debug(f"[HumanSim] Simulando pausa de {pausa:.1f}s")
            base += pausa

        return base

    def esta_em_horario_comercial(self) -> bool:
        """Verifica se está em horário comercial."""
        agora = datetime.now().time()

        # Variação de +/- 30 minutos
        inicio_variado = time(
            self.HORARIO_INICIO.hour,
            random.randint(0, 30)
        )
        fim_variado = time(
            self.HORARIO_FIM.hour,
            random.randint(0, 30)
        )

        return inicio_variado <= agora <= fim_variado

    def eh_dia_util(self) -> bool:
        """Verifica se é dia útil (segunda a sexta)."""
        return datetime.now().weekday() < 5

    def pode_enviar_agora(self) -> bool:
        """Verifica se pode enviar mensagem agora."""
        return self.esta_em_horario_comercial() and self.eh_dia_util()

    def adicionar_variacao_texto(self, texto: str) -> str:
        """
        Adiciona variações naturais ao texto.

        Args:
            texto: Texto original

        Returns:
            Texto com possíveis variações
        """
        resultado = texto

        # Chance de adicionar emoji casual no final
        if random.random() < self.profile.emoji_chance:
            if not any(emoji in texto for emoji in self.EMOJIS_CASUAIS):
                emoji = random.choice(self.EMOJIS_CASUAIS)
                resultado = f"{resultado} {emoji}"

        return resultado

    async def simular_digitacao_completa(
        self,
        mensagem: str,
        callback_typing: Optional[callable] = None,
    ) -> dict:
        """
        Simula ciclo completo de digitação.

        Args:
            mensagem: Texto a enviar
            callback_typing: Função async para enviar indicador de digitação

        Returns:
            dict com delays aplicados e mensagem final
        """
        resultado = {
            "delay_pensamento": 0,
            "delay_digitacao": 0,
            "delay_total": 0,
            "mensagem_final": mensagem,
            "typing_enviado": False,
        }

        # 1. Delay de pensamento
        delay_pensamento = await self.calcular_delay_pensamento()
        resultado["delay_pensamento"] = delay_pensamento

        logger.debug(f"[HumanSim] Pensando por {delay_pensamento:.1f}s")
        await asyncio.sleep(delay_pensamento)

        # 2. Enviar indicador de digitação
        if callback_typing:
            try:
                await callback_typing()
                resultado["typing_enviado"] = True
                logger.debug("[HumanSim] Indicador de digitação enviado")
            except Exception as e:
                logger.warning(f"[HumanSim] Erro ao enviar typing: {e}")

        # 3. Delay de digitação
        delay_digitacao = await self.calcular_delay_digitacao(mensagem)
        resultado["delay_digitacao"] = delay_digitacao

        logger.debug(f"[HumanSim] Digitando por {delay_digitacao:.1f}s")
        await asyncio.sleep(delay_digitacao)

        # 4. Variações no texto
        resultado["mensagem_final"] = self.adicionar_variacao_texto(mensagem)

        resultado["delay_total"] = delay_pensamento + delay_digitacao

        logger.info(
            f"[HumanSim] Ciclo completo: {resultado['delay_total']:.1f}s "
            f"para {len(mensagem)} chars"
        )

        return resultado

    async def simular_leitura(
        self,
        mensagem: str,
        callback_read: Optional[callable] = None,
    ) -> float:
        """
        Simula leitura de mensagem recebida.

        Args:
            mensagem: Texto recebido
            callback_read: Função async para marcar como lido

        Returns:
            Delay aplicado em segundos
        """
        delay = await self.calcular_delay_leitura(mensagem)

        logger.debug(f"[HumanSim] Lendo por {delay:.1f}s")
        await asyncio.sleep(delay)

        if callback_read:
            try:
                await callback_read()
                logger.debug("[HumanSim] Marcado como lido")
            except Exception as e:
                logger.warning(f"[HumanSim] Erro ao marcar lido: {e}")

        return delay

    def calcular_proximo_horario_envio(self) -> datetime:
        """
        Calcula próximo horário válido para envio.

        Returns:
            datetime do próximo momento válido
        """
        agora = datetime.now()

        # Se pode enviar agora, retorna agora
        if self.pode_enviar_agora():
            return agora

        # Senão, calcula próximo horário válido
        if agora.time() >= self.HORARIO_FIM:
            # Depois do expediente - próximo dia útil às 8h
            proximo = agora.replace(
                hour=self.HORARIO_INICIO.hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )

            # Avançar para próximo dia útil
            from datetime import timedelta
            proximo += timedelta(days=1)
            while proximo.weekday() >= 5:  # Sábado ou domingo
                proximo += timedelta(days=1)

            return proximo

        elif agora.time() < self.HORARIO_INICIO:
            # Antes do expediente - hoje às 8h
            return agora.replace(
                hour=self.HORARIO_INICIO.hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )

        else:
            # Final de semana - próxima segunda
            from datetime import timedelta
            proximo = agora
            while proximo.weekday() >= 5:
                proximo += timedelta(days=1)

            return proximo.replace(
                hour=self.HORARIO_INICIO.hour,
                minute=random.randint(0, 30),
                second=0,
                microsecond=0
            )


# Instância padrão
human_simulator = HumanSimulator()


def get_simulator(profile_name: str = "julia_normal") -> HumanSimulator:
    """
    Obtém simulador com perfil específico.

    Args:
        profile_name: Nome do perfil (julia_engajada, julia_normal, julia_ocupada, warmup_cuidadoso)

    Returns:
        HumanSimulator configurado
    """
    profile = PROFILES.get(profile_name, PROFILES["julia_normal"])
    return HumanSimulator(profile)


async def simular_envio_natural(
    mensagem: str,
    callback_typing: Optional[callable] = None,
    callback_send: Optional[callable] = None,
    profile_name: str = "julia_normal",
) -> dict:
    """
    Função de conveniência para simular envio natural.

    Args:
        mensagem: Texto a enviar
        callback_typing: Função para enviar indicador de digitação
        callback_send: Função para enviar mensagem
        profile_name: Perfil de comportamento

    Returns:
        dict com resultado da simulação
    """
    simulator = get_simulator(profile_name)

    resultado = await simulator.simular_digitacao_completa(
        mensagem,
        callback_typing
    )

    if callback_send:
        try:
            await callback_send(resultado["mensagem_final"])
            resultado["enviado"] = True
        except Exception as e:
            logger.error(f"[HumanSim] Erro ao enviar: {e}")
            resultado["enviado"] = False
            resultado["erro"] = str(e)

    return resultado
