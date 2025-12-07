"""
Serviço de timing para humanização de respostas.
Simula comportamento humano no tempo de resposta e digitação.
"""
import random
import logging
import time
from datetime import datetime, time as dt_time, timedelta

logger = logging.getLogger(__name__)

# Horário comercial
HORARIO_INICIO = dt_time(8, 0)   # 8h
HORARIO_FIM = dt_time(20, 0)     # 20h
DIAS_UTEIS = [0, 1, 2, 3, 4]  # Segunda a sexta (0=segunda)


def calcular_delay_resposta(
    mensagem: str,
    hora_atual: datetime = None
) -> float:
    """
    Calcula delay apropriado para resposta.

    Fatores:
    - Tamanho da mensagem (mais texto = mais tempo lendo)
    - Complexidade (pergunta vs afirmação)
    - Hora do dia (mais lento no início/fim do dia)
    - Variação aleatória (parecer humano)

    Args:
        mensagem: Mensagem recebida
        hora_atual: Hora atual (opcional, usa datetime.now() se None)

    Returns:
        Delay em segundos (20-120s tipicamente)
    """
    hora_atual = hora_atual or datetime.now()
    base_delay = 20  # Mínimo 20 segundos

    # Fator: tamanho da mensagem
    palavras = len(mensagem.split())
    tempo_leitura = palavras * 0.3  # ~0.3s por palavra

    # Fator: complexidade
    eh_pergunta = '?' in mensagem
    tem_numeros = any(c.isdigit() for c in mensagem)
    complexidade = 0
    if eh_pergunta:
        complexidade += 5
    if tem_numeros:
        complexidade += 3
    if len(mensagem) > 200:
        complexidade += 5

    # Fator: hora do dia
    hora = hora_atual.hour
    fator_hora = 1.0
    if hora < 9:  # Início do dia - mais lenta
        fator_hora = 1.3
    elif hora > 18:  # Fim do dia - mais lenta
        fator_hora = 1.2
    elif 12 <= hora <= 14:  # Horário de almoço
        fator_hora = 1.4

    # Calcular delay base
    delay = base_delay + tempo_leitura + complexidade

    # Aplicar fator de hora
    delay *= fator_hora

    # Adicionar variação aleatória (±30%)
    variacao = random.uniform(0.7, 1.3)
    delay *= variacao

    # Limitar entre 20s e 120s
    return max(20, min(120, delay))


def calcular_tempo_digitacao(texto: str) -> float:
    """
    Calcula tempo realista de digitação.

    Humano médio digita ~40 palavras/minuto no celular.
    Com correções e pensamento: ~30 palavras/minuto.

    Args:
        texto: Texto a ser digitado

    Returns:
        Tempo em segundos
    """
    palavras = len(texto.split())
    caracteres = len(texto)

    # Base: 30 palavras por minuto = 2 segundos por palavra
    tempo_base = palavras * 2

    # Ajuste para emojis (mais rápido)
    # Emojis estão na faixa Unicode > 127000
    emojis = sum(1 for c in texto if ord(c) > 127000)
    tempo_base -= emojis * 1  # Emoji é rápido

    # Ajuste para abreviações (mais rápido)
    abreviacoes = texto.count("vc") + texto.count("pra") + texto.count("tá")
    tempo_base -= abreviacoes * 0.5

    # Mínimo 3s, máximo 15s por mensagem
    return max(3, min(15, tempo_base))


def log_timing(mensagem: str, delay: float, tempo_real: float):
    """
    Loga métricas de timing para análise.

    Args:
        mensagem: Mensagem recebida
        delay: Delay calculado
        tempo_real: Tempo real de processamento
    """
    logger.info(
        "Timing de resposta",
        extra={
            "delay_calculado": delay,
            "tempo_real": tempo_real,
            "tamanho_mensagem": len(mensagem),
            "palavras": len(mensagem.split())
        }
    )


def esta_em_horario_comercial(dt: datetime = None) -> bool:
    """
    Verifica se está em horário comercial.

    Horário: 8h-20h, segunda a sexta

    Args:
        dt: Data/hora a verificar (opcional, usa datetime.now() se None)

    Returns:
        True se está em horário comercial
    """
    dt = dt or datetime.now()

    # Verificar dia da semana
    if dt.weekday() not in DIAS_UTEIS:
        return False

    # Verificar hora
    hora_atual = dt.time()
    return HORARIO_INICIO <= hora_atual <= HORARIO_FIM


def proximo_horario_comercial(dt: datetime = None) -> datetime:
    """
    Retorna próximo horário comercial disponível.

    Args:
        dt: Data/hora de referência (opcional, usa datetime.now() se None)

    Returns:
        Próximo datetime em horário comercial
    """
    dt = dt or datetime.now()

    while True:
        # Se é dia útil
        if dt.weekday() in DIAS_UTEIS:
            # Se antes do horário de início
            if dt.time() < HORARIO_INICIO:
                return dt.replace(
                    hour=HORARIO_INICIO.hour,
                    minute=HORARIO_INICIO.minute,
                    second=0,
                    microsecond=0
                )
            # Se dentro do horário
            elif dt.time() <= HORARIO_FIM:
                return dt
            # Se depois do horário (vai para próximo dia)

        # Avançar para próximo dia às 8h
        dt = (dt + timedelta(days=1)).replace(
            hour=HORARIO_INICIO.hour,
            minute=HORARIO_INICIO.minute,
            second=0,
            microsecond=0
        )

