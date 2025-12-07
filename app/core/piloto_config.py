"""
Configurações específicas do piloto.
"""
from dataclasses import dataclass


@dataclass
class PilotoConfig:
    """Configurações específicas do piloto."""

    # Limites de envio
    MAX_PRIMEIROS_CONTATOS_DIA: int = 50
    INTERVALO_ENTRE_ENVIOS_SEGUNDOS: int = 300  # 5 minutos

    # Horário de envio
    HORA_INICIO: int = 8
    HORA_FIM: int = 18

    # Rate limiting de respostas (mais conservador)
    MAX_RESPOSTAS_HORA: int = 15
    MAX_RESPOSTAS_DIA: int = 80


# Instância global
piloto_config = PilotoConfig()

