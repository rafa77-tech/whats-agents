"""
Helpers para extrair contexto de eventos de negocio.

Sprint 17 - E04
"""

from typing import List


def extrair_vagas_do_contexto(
    tool_calls: List[dict],
    resposta_agente: str = "",
) -> List[str]:
    """
    Extrai vaga_ids do contexto da interacao.

    Args:
        tool_calls: Lista de tool calls feitos pelo agente
        resposta_agente: Resposta final do agente (opcional)

    Returns:
        Lista de vaga_ids mencionados/oferecidos
    """
    vaga_ids = []

    for call in tool_calls:
        tool_name = call.get("name", "")
        result = call.get("result", {})

        if tool_name == "buscar_vagas":
            # Vagas retornadas pela busca
            for vaga in result.get("vagas", []):
                if vaga.get("id"):
                    vaga_ids.append(vaga["id"])

        elif tool_name == "reservar_plantao":
            # Vaga reservada
            if result.get("vaga_id"):
                vaga_ids.append(result["vaga_id"])
            if result.get("id"):
                vaga_ids.append(result["id"])

    return list(set(vaga_ids))  # Dedupe


def tem_mencao_oportunidade(resposta: str) -> bool:
    """
    Verifica se a resposta menciona oportunidades genericas.

    Usado para decidir entre offer_made vs offer_teaser_sent.
    Se menciona oportunidade mas sem vaga especifica, e teaser.

    Args:
        resposta: Texto da resposta do agente

    Returns:
        True se menciona oportunidades genericas
    """
    termos = [
        "temos vagas",
        "temos oportunidades",
        "surgiu uma vaga",
        "apareceu plantão",
        "apareceu plantao",
        "tem interesse",
        "posso te passar",
        "temos plantões",
        "temos plantoes",
        "vagas disponíveis",
        "vagas disponiveis",
        "oportunidades na região",
        "oportunidades na regiao",
    ]

    resposta_lower = resposta.lower()
    return any(termo in resposta_lower for termo in termos)


def tem_link_app_revoluna(resposta: str) -> bool:
    """
    Verifica se a resposta contém links do app Revoluna.

    Usado para detectar automaticamente quando Julia envia os links
    e emitir o evento APP_DOWNLOAD_SENT.

    Args:
        resposta: Texto da resposta do agente

    Returns:
        True se contém links do app (iOS ou Android)
    """
    links_app = [
        "apps.apple.com/br/app/revoluna",
        "play.google.com/store/apps/details?id=com.mycompany.revoluna",
    ]

    resposta_lower = resposta.lower()
    return any(link.lower() in resposta_lower for link in links_app)


def detectar_trigger_app_download(mensagem_medico: str) -> str | None:
    """
    Detecta qual trigger levou ao envio dos links do app.

    Analisa a mensagem do médico para identificar a intenção.

    Args:
        mensagem_medico: Última mensagem do médico

    Returns:
        Tipo de trigger ou None se não identificado
    """
    msg_lower = mensagem_medico.lower()

    # Padrões de interesse demonstrado
    interesse_patterns = [
        "quero saber mais",
        "conta mais",
        "me conta",
        "me interessei",
        "interessante",
        "como funciona",
        "como que funciona",
        "me fala mais",
        "quero conhecer",
        "pode me contar",
    ]

    # Padrões de pergunta sobre vagas
    vagas_patterns = [
        "onde vejo",
        "como vejo",
        "tem site",
        "tem app",
        "tem aplicativo",
        "como acesso",
        "onde acesso",
        "como consulto",
    ]

    # Padrões de querer cadastrar
    cadastro_patterns = [
        "como me cadastro",
        "quero me cadastrar",
        "quero me inscrever",
        "como faço parte",
        "como entro",
        "quero participar",
    ]

    if any(p in msg_lower for p in cadastro_patterns):
        return "quer_cadastrar"
    if any(p in msg_lower for p in vagas_patterns):
        return "perguntou_vagas"
    if any(p in msg_lower for p in interesse_patterns):
        return "interesse_demonstrado"

    return None
