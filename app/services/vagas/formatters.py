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
    # Tratamento seguro de objetos relacionados que podem ser None
    hospitais = vaga.get("hospitais") or {}
    periodos = vaga.get("periodos") or {}
    setores = vaga.get("setores") or {}

    hospital = hospitais.get("nome", "Hospital") if isinstance(hospitais, dict) else "Hospital"
    data = vaga.get("data", "")
    periodo = periodos.get("nome", "") if isinstance(periodos, dict) else ""
    vaga.get("valor") or 0
    setor = setores.get("nome", "") if isinstance(setores, dict) else ""

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

    # Formatar valor baseado no tipo (Sprint 19)
    valor_str = formatar_valor_para_mensagem(vaga)
    if valor_str:
        partes.append(valor_str)

    return ", ".join(partes)


def formatar_valor_para_mensagem(vaga: dict) -> str:
    """
    Formata valor da vaga para mensagem natural.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada ou vazio
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo:,.0f} a {valor_maximo:,.0f}".replace(",", ".")
        elif valor_minimo:
            return f"a partir de R$ {valor_minimo:,.0f}".replace(",", ".")
        elif valor_maximo:
            return f"ate R$ {valor_maximo:,.0f}".replace(",", ".")

    elif valor_tipo == "a_combinar":
        return "valor a combinar"

    # Fallback: valor sem tipo definido
    if valor:
        return f"R$ {valor:,.0f}".replace(",", ".")

    return ""


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
        # Tratamento seguro de objetos relacionados que podem ser None
        hospital = v.get("hospitais") or {}
        periodo = v.get("periodos") or {}
        setor = v.get("setores") or {}

        # Extrair valores com segurança
        hospital_nome = hospital.get("nome", "N/A") if isinstance(hospital, dict) else "N/A"
        hospital_cidade = hospital.get("cidade", "N/A") if isinstance(hospital, dict) else "N/A"
        periodo_nome = periodo.get("nome", "N/A") if isinstance(periodo, dict) else "N/A"
        periodo_inicio = periodo.get("hora_inicio", "") if isinstance(periodo, dict) else ""
        periodo_fim = periodo.get("hora_fim", "") if isinstance(periodo, dict) else ""
        setor_nome = setor.get("nome", "N/A") if isinstance(setor, dict) else "N/A"

        # Formatar valor baseado no tipo (Sprint 19)
        valor_display = _formatar_valor_contexto(v)

        # Label de criticidade para o LLM
        criticidade = v.get("criticidade", "normal")
        criticidade_label = _formatar_criticidade_contexto(criticidade)

        texto += f"""**Vaga {i}:**{criticidade_label}
- Hospital: {hospital_nome} ({hospital_cidade})
- Data: {v.get("data", "N/A")}
- Período: {periodo_nome} ({periodo_inicio}-{periodo_fim})
- Setor: {setor_nome}
- Valor: {valor_display}
- ID: {v.get("id", "N/A")}
"""

    return texto


def _formatar_criticidade_contexto(criticidade: str) -> str:
    """
    Formata criticidade para contexto do LLM.

    Args:
        criticidade: Nivel de criticidade da vaga

    Returns:
        String formatada para contexto (vazio para normal)
    """
    if criticidade == "urgente":
        return " [URGENTE]"
    elif criticidade == "critica":
        return " [CRITICA - PRIORIDADE MAXIMA]"
    return ""


def _formatar_valor_contexto(vaga: dict) -> str:
    """
    Formata valor para contexto do LLM.

    Args:
        vaga: Dados da vaga

    Returns:
        String formatada para contexto
    """
    valor_tipo = vaga.get("valor_tipo", "fixo")
    valor = vaga.get("valor")
    valor_minimo = vaga.get("valor_minimo")
    valor_maximo = vaga.get("valor_maximo")

    if valor_tipo == "fixo" and valor:
        return f"R$ {valor} (fixo)"

    elif valor_tipo == "faixa":
        if valor_minimo and valor_maximo:
            return f"R$ {valor_minimo} a R$ {valor_maximo} (faixa)"
        elif valor_minimo:
            return f"A partir de R$ {valor_minimo}"
        elif valor_maximo:
            return f"Ate R$ {valor_maximo}"
        return "Faixa nao definida"

    elif valor_tipo == "a_combinar":
        return "A COMBINAR - informar medico que valor sera negociado"

    # Fallback
    if valor:
        return f"R$ {valor}"

    return "N/A"
