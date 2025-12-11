"""
Formatador de respostas para Slack.

Garante que as respostas da Julia sejam naturais, bem formatadas
e sigam a persona definida.
"""
import re
from datetime import datetime
from typing import Any


# =============================================================================
# FORMATACAO BASICA SLACK
# =============================================================================

def bold(texto: str) -> str:
    """Formata texto em negrito."""
    return f"*{texto}*"


def code(texto: str) -> str:
    """Formata texto como codigo (monospace)."""
    return f"`{texto}`"


def quote(texto: str) -> str:
    """Formata texto como citacao."""
    linhas = texto.split("\n")
    return "\n".join(f"> {linha}" for linha in linhas)


def lista(itens: list[str], max_itens: int = 7) -> str:
    """Formata lista com bullets."""
    if len(itens) > max_itens:
        itens_mostrar = itens[:max_itens]
        resto = len(itens) - max_itens
        resultado = "\n".join(f"• {item}" for item in itens_mostrar)
        resultado += f"\n_...e mais {resto}_"
        return resultado
    return "\n".join(f"• {item}" for item in itens)


def lista_numerada(itens: list[str], max_itens: int = 7) -> str:
    """Formata lista numerada."""
    if len(itens) > max_itens:
        itens_mostrar = itens[:max_itens]
        resto = len(itens) - max_itens
        resultado = "\n".join(f"{i+1}. {item}" for i, item in enumerate(itens_mostrar))
        resultado += f"\n_...e mais {resto}_"
        return resultado
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(itens))


# =============================================================================
# FORMATACAO DE DADOS
# =============================================================================

def formatar_telefone(telefone: str) -> str:
    """Formata telefone para exibicao."""
    tel_limpo = re.sub(r'\D', '', telefone)
    if len(tel_limpo) >= 11:
        return f"`{tel_limpo[:2]} {tel_limpo[2:7]}-{tel_limpo[7:]}`"
    elif len(tel_limpo) >= 8:
        return f"`{tel_limpo}`"
    return code(telefone)


def formatar_valor(valor: float | int) -> str:
    """Formata valor monetario."""
    if valor >= 1000:
        return f"R$ {valor:,.0f}".replace(",", ".")
    return f"R$ {valor:.0f}"


def formatar_porcentagem(valor: float) -> str:
    """Formata porcentagem."""
    if valor == int(valor):
        return f"{int(valor)}%"
    return f"{valor:.1f}%"


def formatar_data(data: str | datetime) -> str:
    """Formata data para exibicao."""
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            return data

    return data.strftime("%d/%m")


def formatar_data_hora(data: str | datetime) -> str:
    """Formata data e hora para exibicao."""
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data.replace("Z", "+00:00"))
        except ValueError:
            return data

    return data.strftime("%d/%m %H:%M")


# =============================================================================
# TEMPLATES DE RESPOSTA
# =============================================================================

def template_metricas(metricas: dict, periodo: str) -> str:
    """
    Formata metricas de performance.

    Args:
        metricas: Dict com enviadas, respostas, taxa_resposta, etc
        periodo: Nome do periodo (hoje, semana, etc)

    Returns:
        Mensagem formatada
    """
    enviadas = metricas.get("enviadas", 0)
    respostas = metricas.get("respostas", 0)
    taxa = metricas.get("taxa_resposta", 0)
    positivas = metricas.get("positivas", 0)
    negativas = metricas.get("negativas", 0)
    optouts = metricas.get("optouts", 0)
    reservas = metricas.get("vagas_reservadas", 0)

    # Cabecalho contextual
    if periodo == "hoje":
        if taxa >= 30:
            cabecalho = "Dia bom!"
        elif taxa >= 20:
            cabecalho = "Dia ok"
        else:
            cabecalho = "Dia fraco"
    else:
        cabecalho = f"*{periodo.title()}:*"

    linhas = [cabecalho, ""]

    # Numeros principais
    linhas.append(f"• Enviadas: {enviadas}")
    linhas.append(f"• Respostas: {respostas} ({formatar_porcentagem(taxa)})")

    if positivas > 0 or negativas > 0:
        if positivas > 0:
            linhas.append(f"• Positivas: {positivas}")
        if negativas > 0:
            linhas.append(f"• Negativas: {negativas}")

    if optouts > 0:
        linhas.append(f"• Opt-outs: {optouts}")

    if reservas > 0:
        linhas.append(f"• Vagas fechadas: {reservas}")

    return "\n".join(linhas)


def template_comparacao(resultado: dict) -> str:
    """
    Formata comparacao entre periodos.

    Args:
        resultado: Dict com periodo1, periodo2, variacao

    Returns:
        Mensagem formatada
    """
    p1 = resultado.get("periodo1", {})
    p2 = resultado.get("periodo2", {})
    variacao = resultado.get("variacao", {})

    nome1 = _traduzir_periodo(p1.get("nome", "periodo1"))
    nome2 = _traduzir_periodo(p2.get("nome", "periodo2"))

    m1 = p1.get("metricas", {})
    m2 = p2.get("metricas", {})

    tendencia = variacao.get("tendencia", "estavel")
    emoji = "📈" if tendencia == "melhora" else "📉" if tendencia == "piora" else "➡️"

    linhas = [
        f"*{nome1} vs {nome2}* {emoji}",
        "",
        f"Taxa: {formatar_porcentagem(m1.get('taxa_resposta', 0))} vs {formatar_porcentagem(m2.get('taxa_resposta', 0))} ({variacao.get('taxa_resposta', '0')})",
        f"Envios: {m1.get('enviadas', 0)} vs {m2.get('enviadas', 0)} ({variacao.get('enviadas', '0')})",
        f"Respostas: {m1.get('respostas', 0)} vs {m2.get('respostas', 0)} ({variacao.get('respostas', '0')})",
    ]

    # Comentario contextual
    if tendencia == "melhora":
        linhas.append("")
        linhas.append("Bom trabalho! Tendencia de melhora")
    elif tendencia == "piora":
        linhas.append("")
        linhas.append("Precisa de atencao, tendencia de queda")

    return "\n".join(linhas)


def template_lista_medicos(medicos: list[dict], filtro: str = "") -> str:
    """
    Formata lista de medicos.

    Args:
        medicos: Lista de dicts com nome, telefone, especialidade
        filtro: Tipo de filtro aplicado

    Returns:
        Mensagem formatada
    """
    if not medicos:
        return "Nenhum medico encontrado com esse filtro"

    # Cabecalho contextual
    cabecalhos = {
        "responderam_hoje": "Quem respondeu hoje:",
        "positivos": "Medicos interessados:",
        "sem_resposta": "Sem resposta ainda:",
        "novos": "Medicos novos:",
    }
    cabecalho = cabecalhos.get(filtro, f"{len(medicos)} medicos:")

    linhas = [f"*{cabecalho}*", ""]

    for i, m in enumerate(medicos[:10]):  # Max 10
        nome = m.get("nome", "?")
        telefone = m.get("telefone", "")
        esp = m.get("especialidade", "")

        linha = f"{i+1}. {nome}"
        if telefone:
            linha += f" {formatar_telefone(telefone)}"
        if esp:
            linha += f" - {esp}"

        linhas.append(linha)

    if len(medicos) > 10:
        linhas.append(f"_...e mais {len(medicos) - 10}_")

    return "\n".join(linhas)


def template_lista_vagas(vagas: list[dict]) -> str:
    """
    Formata lista de vagas.

    Args:
        vagas: Lista de dicts com hospital, data, periodo, valor

    Returns:
        Mensagem formatada
    """
    if not vagas:
        return "Nenhuma vaga encontrada"

    linhas = [f"*{len(vagas)} vagas:*", ""]

    for i, v in enumerate(vagas[:7]):  # Max 7
        hospital = v.get("hospital", "?")
        data = formatar_data(v.get("data", ""))
        periodo = v.get("periodo", "")
        valor = v.get("valor", 0)

        linha = f"{i+1}. {bold(hospital)} - {data}"
        if periodo:
            linha += f" ({periodo})"
        if valor:
            linha += f" - {formatar_valor(valor)}"

        linhas.append(linha)

    if len(vagas) > 7:
        linhas.append(f"_...e mais {len(vagas) - 7}_")

    return "\n".join(linhas)


def template_medico_info(medico: dict) -> str:
    """
    Formata informacoes de um medico.

    Args:
        medico: Dict com dados do medico

    Returns:
        Mensagem formatada
    """
    nome = medico.get("nome", "?")
    telefone = medico.get("telefone", "")
    crm = medico.get("crm", "")
    especialidade = medico.get("especialidade", "")
    cidade = medico.get("cidade", "")
    bloqueado = medico.get("bloqueado", False)
    ultima = medico.get("ultima_interacao")

    linhas = [f"*{nome}*"]

    if telefone:
        linhas.append(f"Tel: {formatar_telefone(telefone)}")
    if crm:
        linhas.append(f"CRM: {crm}")
    if especialidade:
        linhas.append(f"Especialidade: {especialidade}")
    if cidade:
        linhas.append(f"Cidade: {cidade}")

    if bloqueado:
        linhas.append("⛔ *Bloqueado*")

    if ultima:
        linhas.append(f"Ultima msg: {formatar_data_hora(ultima)}")

    return "\n".join(linhas)


def template_confirmacao_envio(telefone: str, mensagem: str, nome: str = None) -> str:
    """
    Formata preview de envio para confirmacao.

    Args:
        telefone: Numero do medico
        mensagem: Preview da mensagem
        nome: Nome do medico (opcional)

    Returns:
        Mensagem formatada
    """
    destinatario = nome or formatar_telefone(telefone)

    linhas = [
        f"Vou mandar pro {destinatario}:",
        "",
        quote(mensagem),
        "",
        "Posso enviar?"
    ]

    return "\n".join(linhas)


def template_sucesso_envio(nome: str = None, telefone: str = None) -> str:
    """Formata confirmacao de envio bem sucedido."""
    if nome:
        destinatario = nome
    elif telefone:
        destinatario = formatar_telefone(telefone)
    else:
        destinatario = "o medico"
    return f"Pronto! Mandei pro {destinatario}"


def template_sucesso_bloqueio(nome: str = None, telefone: str = None) -> str:
    """Formata confirmacao de bloqueio."""
    if nome:
        destinatario = nome
    elif telefone:
        destinatario = formatar_telefone(telefone)
    else:
        destinatario = "o medico"
    return f"Bloqueado! Nao vou mais mandar msg pro {destinatario}"


def template_sucesso_desbloqueio(nome: str = None, telefone: str = None) -> str:
    """Formata confirmacao de desbloqueio."""
    if nome:
        destinatario = nome
    elif telefone:
        destinatario = formatar_telefone(telefone)
    else:
        destinatario = "o medico"
    return f"Desbloqueado! {destinatario} pode receber msgs de novo"


def template_sucesso_reserva(vaga: dict, medico: dict) -> str:
    """Formata confirmacao de reserva."""
    hospital = vaga.get("hospital", "?")
    data = formatar_data(vaga.get("data", ""))
    periodo = vaga.get("periodo", "")
    valor = vaga.get("valor", 0)
    nome = medico.get("nome", "o medico")

    linhas = [
        f"Reservado pro {nome}!",
        "",
        f"*{hospital}*",
        f"Data: {data}" + (f" ({periodo})" if periodo else ""),
    ]

    if valor:
        linhas.append(f"Valor: {formatar_valor(valor)}")

    return "\n".join(linhas)


def template_status_sistema(dados: dict) -> str:
    """Formata status do sistema."""
    status = dados.get("status", "?")
    conversas = dados.get("conversas_ativas", 0)
    handoffs = dados.get("handoffs_pendentes", 0)
    vagas = dados.get("vagas_abertas", 0)
    msgs = dados.get("mensagens_hoje", 0)

    emoji_status = "✅" if status == "ativo" else "⏸️" if status == "pausado" else "❓"

    linhas = [
        f"*Status:* {status} {emoji_status}",
        "",
        f"• Conversas ativas: {conversas}",
        f"• Handoffs pendentes: {handoffs}",
        f"• Vagas abertas: {vagas}",
        f"• Msgs hoje: {msgs}",
    ]

    if handoffs > 0:
        linhas.append("")
        linhas.append(f"⚠️ {handoffs} handoff(s) precisando atencao!")

    return "\n".join(linhas)


def template_lista_handoffs(handoffs: list[dict]) -> str:
    """Formata lista de handoffs."""
    if not handoffs:
        return "Nenhum handoff pendente"

    linhas = [f"*{len(handoffs)} handoff(s):*", ""]

    for h in handoffs[:5]:
        nome = h.get("medico", "?")
        telefone = h.get("telefone", "")
        motivo = _traduzir_motivo_handoff(h.get("motivo", ""))
        criado = h.get("criado_em")

        linha = f"• {nome}"
        if telefone:
            linha += f" {formatar_telefone(telefone)}"
        linha += f" - {motivo}"
        if criado:
            linha += f" ({formatar_data_hora(criado)})"

        linhas.append(linha)

    return "\n".join(linhas)


def template_historico(medico: str, mensagens: list[dict]) -> str:
    """Formata historico de conversa."""
    if not mensagens:
        return f"Sem historico com {medico}"

    linhas = [f"*Historico com {medico}:*", ""]

    for m in mensagens[-10:]:  # Ultimas 10
        autor = "Julia" if m.get("autor") == "julia" else "Medico"
        texto = m.get("texto", "")[:100]  # Truncar
        if len(m.get("texto", "")) > 100:
            texto += "..."

        data = formatar_data_hora(m.get("data", "")) if m.get("data") else ""

        linhas.append(f"*{autor}* {data}")
        linhas.append(f"> {texto}")
        linhas.append("")

    return "\n".join(linhas).strip()


# =============================================================================
# TRATAMENTO DE ERROS
# =============================================================================

ERROS_AMIGAVEIS = {
    "medico nao encontrado": "Nao achei ninguem com esse numero/nome",
    "telefone nao informado": "Preciso do telefone pra fazer isso",
    "telefone invalido": "Esse telefone nao parece valido",
    "vaga nao encontrada": "Nao achei essa vaga",
    "medico bloqueado": "Esse medico ta bloqueado, nao posso contatar",
    "whatsapp": "WhatsApp ta com problema, tenta de novo em alguns minutos?",
    "timeout": "Demorou demais pra responder, vou tentar de novo...",
    "erro na api": "Ops, deu um problema aqui. Tenta de novo?",
    "sem permissao": "Nao tenho acesso a isso, fala com o admin",
}


def formatar_erro(erro: str) -> str:
    """
    Converte erro tecnico em mensagem amigavel.

    Args:
        erro: Mensagem de erro original

    Returns:
        Mensagem amigavel
    """
    erro_lower = erro.lower()

    for chave, mensagem in ERROS_AMIGAVEIS.items():
        if chave in erro_lower:
            return mensagem

    # Se nao encontrou mapeamento, retornar versao generica
    if "404" in erro or "not found" in erro_lower:
        return "Nao encontrei o que vc pediu"
    if "500" in erro or "internal" in erro_lower:
        return "Ops, deu um problema aqui. Tenta de novo?"
    if "503" in erro or "unavailable" in erro_lower:
        return "Servico ta fora, tenta de novo em alguns minutos"
    if "timeout" in erro_lower:
        return "Demorou demais, vou tentar de novo..."

    # Fallback
    return f"Ops, deu erro: {erro[:50]}"


# =============================================================================
# HELPERS
# =============================================================================

def _traduzir_periodo(periodo: str) -> str:
    """Traduz nome do periodo para exibicao."""
    traducoes = {
        "hoje": "Hoje",
        "ontem": "Ontem",
        "semana": "Essa semana",
        "semana_passada": "Semana passada",
        "mes": "Esse mes",
        "mes_passado": "Mes passado",
    }
    return traducoes.get(periodo, periodo.title())


def _traduzir_motivo_handoff(motivo: str) -> str:
    """Traduz motivo do handoff para exibicao."""
    traducoes = {
        "pediu_humano": "pediu humano",
        "sentimento_negativo": "irritado",
        "complexo": "caso complexo",
        "confianca_baixa": "incerteza",
        "manual": "manual",
    }
    return traducoes.get(motivo, motivo)
