"""
Mensagens para external handoff.

Sprint 20 - E03 - Templates e envio.
"""

import logging
from datetime import datetime

from app.services.outbound import send_outbound_message
from app.services.whatsapp import enviar_whatsapp

logger = logging.getLogger(__name__)


def _formatar_data(data_str: str) -> str:
    """
    Formata data para exibicao amigavel.

    Args:
        data_str: Data no formato YYYY-MM-DD

    Returns:
        Data formatada (ex: "15/01 (quarta)")
    """
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d")
        dias_semana = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
        dia_semana = dias_semana[data.weekday()]
        return f"{data.day:02d}/{data.month:02d} ({dia_semana})"
    except Exception:
        return data_str


def _formatar_valor(vaga: dict) -> str:
    """
    Formata valor da vaga para exibicao.

    Args:
        vaga: Dados da vaga

    Returns:
        Valor formatado
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

    return "a combinar"


async def enviar_mensagem_medico(
    cliente_id: str,
    divulgador: dict,
    vaga: dict,
) -> None:
    """
    Envia mensagem ao medico com contato do divulgador.

    Args:
        cliente_id: UUID do medico
        divulgador: Dados do divulgador (nome, telefone, empresa)
        vaga: Dados da vaga
    """
    nome_divulgador = divulgador.get("nome", "o responsavel")
    telefone_divulgador = divulgador.get("telefone", "")
    empresa = divulgador.get("empresa")

    # Montar info do divulgador
    info_empresa = f" ({empresa})" if empresa else ""

    # Formatar telefone para link WhatsApp
    telefone_divulgador.replace("+", "").replace(" ", "").replace("-", "")

    mensagem = (
        f"Perfeito! Reservei essa vaga pra voce.\n\n"
        f"Pra confirmar na escala, fala direto com {nome_divulgador}{info_empresa}: {telefone_divulgador}\n\n"
        f"Me avisa aqui quando fechar!"
    )

    await send_outbound_message(
        cliente_id=cliente_id,
        mensagem=mensagem,
        campanha="handoff_ponte",
    )

    logger.info(f"Mensagem de ponte enviada ao medico {cliente_id[:8]}")


async def enviar_mensagem_divulgador(
    telefone: str,
    medico: dict,
    vaga: dict,
    link_confirmar: str,
    link_nao_confirmar: str,
) -> None:
    """
    Envia mensagem ao divulgador com contato do medico e links.

    Args:
        telefone: Telefone do divulgador
        medico: Dados do medico (nome, telefone)
        vaga: Dados da vaga
        link_confirmar: Link para confirmar
        link_nao_confirmar: Link para nao confirmar
    """
    nome_medico = medico.get("nome", "o medico")
    telefone_medico = medico.get("telefone", "")

    # Dados da vaga
    hospital = vaga.get("hospitais", {}).get("nome", "hospital")
    data = _formatar_data(vaga.get("data", ""))
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = _formatar_valor(vaga)

    mensagem = (
        f"Oi! Tudo bem?\n\n"
        f"Tenho um medico interessado na vaga:\n"
        f"{data} - {periodo} - {hospital}\n"
        f"Valor: {valor}\n\n"
        f"Contato: {nome_medico} - {telefone_medico}\n\n"
        f"Pra eu registrar certinho, me confirma:\n"
        f"Fechou: {link_confirmar}\n"
        f"Nao fechou: {link_nao_confirmar}\n\n"
        f"Ou responde CONFIRMADO / NAO FECHOU aqui."
    )

    # Enviar via WhatsApp
    # Nota: Usar instancia default da Julia
    await enviar_whatsapp(
        numero=telefone,
        mensagem=mensagem,
    )

    logger.info(f"Mensagem de ponte enviada ao divulgador {telefone[-4:]}")


async def enviar_followup_divulgador(
    telefone: str,
    mensagem: str,
) -> None:
    """
    Envia mensagem de follow-up ao divulgador.

    Args:
        telefone: Telefone do divulgador
        mensagem: Mensagem de follow-up
    """
    await enviar_whatsapp(
        numero=telefone,
        mensagem=mensagem,
    )

    logger.info(f"Follow-up enviado ao divulgador {telefone[-4:]}")
