"""
Formatadores de vagas para mensagens.

Sprint 10 - S10.E3.2
"""
from datetime import datetime

from app.config.especialidades import obter_config_especialidade


def formatar_para_mensagem(vaga: dict) -> str:
    """
    Formata vaga para mensagem natural da Julia.

    Args:
        vaga: Dados da vaga com relacionamentos

    Returns:
        String formatada para mensagem
    """
    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor") or 0
    setor = vaga.get("setores", {}).get("nome", "")

    # Formatar data para PT-BR
    if data:
        try:
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            dias_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
            dia_semana = dias_semana[data_obj.weekday()]
            data = f"{dia_semana}, {data_obj.strftime('%d/%m')}"
        except ValueError:
            pass

    partes = [hospital]
    if data:
        partes.append(data)
    if periodo:
        partes.append(periodo.lower())
    if setor:
        partes.append(setor)
    if valor:
        partes.append(f"R$ {valor:,.0f}".replace(",", "."))

    return ", ".join(partes)


def formatar_para_contexto(vagas: list[dict], especialidade: str = None) -> str:
    """
    Formata vagas para incluir no contexto do LLM.

    Args:
        vagas: Lista de vagas
        especialidade: Nome da especialidade (opcional)

    Returns:
        String formatada com vagas
    """
    if not vagas:
        return "Não há vagas disponíveis no momento para esta especialidade."

    config = obter_config_especialidade(especialidade) if especialidade else {}
    nome_display = config.get("nome_display", "médico") if config else "médico"

    texto = f"## Vagas Disponíveis para {nome_display}:\n\n"

    for i, v in enumerate(vagas[:5], 1):
        hospital = v.get("hospitais", {})
        periodo = v.get("periodos", {})
        setor = v.get("setores", {})

        texto += f"""**Vaga {i}:**
- Hospital: {hospital.get('nome', 'N/A')} ({hospital.get('cidade', 'N/A')})
- Data: {v.get('data', 'N/A')}
- Período: {periodo.get('nome', 'N/A')} ({periodo.get('hora_inicio', '')}-{periodo.get('hora_fim', '')})
- Setor: {setor.get('nome', 'N/A')}
- Valor: R$ {v.get('valor', 'N/A')}
- ID: {v.get('id', 'N/A')}
"""

    return texto
