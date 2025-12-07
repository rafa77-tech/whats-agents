"""
Servico para montagem de contexto do agente.
"""
from typing import Optional
import logging

from app.services.interacao import carregar_historico, formatar_historico_para_llm

logger = logging.getLogger(__name__)


def formatar_contexto_medico(medico: dict) -> str:
    """
    Formata informacoes do medico para o prompt.

    Args:
        medico: Dados do medico do banco

    Returns:
        String formatada
    """
    partes = []

    # Nome
    nome = medico.get("primeiro_nome", "")
    if medico.get("sobrenome"):
        nome += f" {medico['sobrenome']}"

    if nome:
        partes.append(f"Nome: {nome}")

    # Titulo
    if medico.get("titulo"):
        partes.append(f"Titulo: {medico['titulo']}")

    # Especialidade
    if medico.get("especialidade"):
        partes.append(f"Especialidade: {medico['especialidade']}")

    # CRM
    if medico.get("crm"):
        crm = medico["crm"]
        if medico.get("estado"):
            crm = f"CRM-{medico['estado']} {crm}"
        partes.append(f"CRM: {crm}")

    # Cidade
    if medico.get("cidade"):
        partes.append(f"Cidade: {medico['cidade']}")

    # Stage
    if medico.get("stage_jornada"):
        partes.append(f"Status: {medico['stage_jornada']}")

    # Preferencias
    if medico.get("preferencias_detectadas"):
        prefs = medico["preferencias_detectadas"]
        if isinstance(prefs, dict):
            if prefs.get("turnos"):
                partes.append(f"Prefere: {', '.join(prefs['turnos'])}")
            if prefs.get("valor_minimo"):
                partes.append(f"Valor minimo: R$ {prefs['valor_minimo']}")

    return "\n".join(partes) if partes else "Medico novo, sem informacoes ainda."


def formatar_contexto_vagas(vagas: list[dict], limite: int = 3) -> str:
    """
    Formata vagas disponiveis para o prompt.

    Args:
        vagas: Lista de vagas do banco
        limite: Maximo de vagas a mostrar

    Returns:
        String formatada
    """
    if not vagas:
        return "Nenhuma vaga disponivel no momento."

    linhas = []
    for v in vagas[:limite]:
        hospital = v.get("hospitais", {}).get("nome", "Hospital")
        data = v.get("data_plantao", "")
        periodo = v.get("periodos", {}).get("nome", "")
        valor = v.get("valor_min", 0)
        setor = v.get("setores", {}).get("nome", "")

        linha = f"- {hospital}, {data}, {periodo}"
        if setor:
            linha += f", {setor}"
        linha += f", R$ {valor:,.0f}"

        if v.get("prioridade") == "urgente":
            linha += " (URGENTE)"

        linhas.append(linha)

    return "\n".join(linhas)


async def montar_contexto_completo(
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> dict:
    """
    Monta contexto completo para o agente.

    Args:
        medico: Dados do medico
        conversa: Dados da conversa
        vagas: Lista de vagas disponiveis (opcional)

    Returns:
        Dict com todos os contextos formatados
    """
    # Carregar historico
    historico_raw = await carregar_historico(conversa["id"], limite=10)
    historico = formatar_historico_para_llm(historico_raw)

    # Verificar se e primeira mensagem
    primeira_msg = len(historico_raw) == 0

    return {
        "medico": formatar_contexto_medico(medico),
        "historico": historico,
        "historico_raw": historico_raw,
        "vagas": formatar_contexto_vagas(vagas) if vagas else "",
        "primeira_msg": primeira_msg,
        "controlled_by": conversa.get("controlled_by", "ai"),
    }
