"""
Validações de negócio para vagas extraídas.

Sprint 14 - E05 - S05.5
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class AlertaVaga:
    """Alerta sobre possível problema na vaga."""

    tipo: str  # "valor_baixo", "valor_alto", "data_proxima", etc
    mensagem: str
    severidade: str  # "info", "warning", "error"


def validar_valor(valor: Optional[int]) -> List[AlertaVaga]:
    """Valida se valor está em range razoável."""
    alertas = []

    if not valor:
        return alertas

    if valor < 500:
        alertas.append(
            AlertaVaga(
                tipo="valor_baixo", mensagem=f"Valor muito baixo: R$ {valor}", severidade="warning"
            )
        )

    if valor > 10000:
        alertas.append(
            AlertaVaga(
                tipo="valor_alto", mensagem=f"Valor muito alto: R$ {valor}", severidade="warning"
            )
        )

    return alertas


def validar_data(data_vaga: Optional[date]) -> List[AlertaVaga]:
    """Valida data da vaga."""
    alertas = []

    if not data_vaga:
        return alertas

    hoje = date.today()
    diff = (data_vaga - hoje).days

    if diff < 0:
        alertas.append(
            AlertaVaga(tipo="data_passada", mensagem="Data já passou", severidade="error")
        )

    if diff == 0:
        alertas.append(
            AlertaVaga(tipo="data_hoje", mensagem="Vaga para hoje - urgente", severidade="info")
        )

    if diff > 30:
        alertas.append(
            AlertaVaga(
                tipo="data_distante", mensagem=f"Vaga para daqui {diff} dias", severidade="info"
            )
        )

    return alertas


def validar_horario(hora_inicio: Optional[str], hora_fim: Optional[str]) -> List[AlertaVaga]:
    """Valida formato e lógica de horários."""
    alertas = []

    pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"

    if hora_inicio and not re.match(pattern, hora_inicio):
        alertas.append(
            AlertaVaga(
                tipo="horario_invalido",
                mensagem=f"Hora início inválida: {hora_inicio}",
                severidade="warning",
            )
        )

    if hora_fim and not re.match(pattern, hora_fim):
        alertas.append(
            AlertaVaga(
                tipo="horario_invalido",
                mensagem=f"Hora fim inválida: {hora_fim}",
                severidade="warning",
            )
        )

    return alertas


def validar_vaga_completa(
    valor: Optional[int],
    data_vaga: Optional[date],
    hora_inicio: Optional[str],
    hora_fim: Optional[str],
) -> List[AlertaVaga]:
    """Executa todas as validações em uma vaga."""
    alertas = []
    alertas.extend(validar_valor(valor))
    alertas.extend(validar_data(data_vaga))
    alertas.extend(validar_horario(hora_inicio, hora_fim))
    return alertas


# Períodos válidos
PERIODOS_VALIDOS = ["Diurno", "Vespertino", "Noturno", "Cinderela"]

# Setores válidos
SETORES_VALIDOS = ["Pronto atendimento", "RPA", "Hospital", "C. Cirúrgico", "SADT"]

# Tipos de vaga válidos
TIPOS_VAGA_VALIDOS = ["Cobertura", "Fixo", "Ambulatorial", "Mensal"]

# Formas de pagamento válidas
FORMAS_PAGAMENTO_VALIDAS = ["Pessoa fisica", "Pessoa jurídica", "CLT", "SCP"]


def validar_campo_enum(
    valor: Optional[str], valores_validos: List[str], campo: str
) -> List[AlertaVaga]:
    """Valida se um campo está entre os valores válidos."""
    alertas = []

    if valor and valor not in valores_validos:
        alertas.append(
            AlertaVaga(
                tipo=f"{campo}_invalido",
                mensagem=f"{campo} não reconhecido: {valor}",
                severidade="info",
            )
        )

    return alertas
