"""
Tipos de abordagem para mensagens WhatsApp.

Define os diferentes tipos de mensagem que a Julia pode enviar,
com prompts especificos e logica de inferencia.
"""
import re
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.core.timezone import agora_brasilia

logger = logging.getLogger(__name__)


class TipoAbordagem(str, Enum):
    """Tipos de abordagem disponíveis."""
    DISCOVERY = "discovery"
    OFERTA = "oferta"
    REATIVACAO = "reativacao"
    FOLLOWUP = "followup"
    CUSTOM = "custom"


# =============================================================================
# PROMPTS POR TIPO
# =============================================================================

PROMPT_DISCOVERY = """Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem de PRIMEIRO CONTATO
para um medico que nunca conversou conosco.

Objetivo: se apresentar e entender se ele tem interesse em fazer plantoes.

Dados do medico:
- Nome: {nome}
- Especialidade: {especialidade}

Regras:
- Seja casual e amigavel
- Use "vc", "pra", "ta" (linguagem informal)
- Nao mencione vagas especificas
- Faca uma pergunta aberta no final
- Quebre em 2-3 mensagens curtas
- Max 4-5 linhas no total

Escreva APENAS a mensagem, sem explicacoes."""

PROMPT_OFERTA = """Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem oferecendo uma
VAGA ESPECIFICA para o medico.

Dados do medico:
- Nome: {nome}

Dados da vaga:
- Hospital: {hospital}
- Data: {data}
- Periodo: {periodo}
- Valor: R$ {valor}
- Especialidade: {especialidade_vaga}

Instrucao adicional do gestor:
{instrucao}

Regras:
- Va direto ao ponto
- Use linguagem informal ("vc", "pra")
- Inclua os detalhes da vaga (local, data, valor)
- Termine perguntando se tem interesse
- Max 4-5 linhas

Escreva APENAS a mensagem, sem explicacoes."""

PROMPT_REATIVACAO = """Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem para REATIVAR
contato com um medico que parou de responder.

Dados do medico:
- Nome: {nome}
- Ultima interacao: {ultima_interacao}

Regras:
- Tom leve e casual, NAO desesperado
- Use "vc", "ta" (linguagem informal)
- Nao pressione nem cobre
- Deixe porta aberta
- Max 3 linhas

Exemplos de tom:
- "Oi Dr! Sumiu hein..."
- "Faz tempo que nao aparece por aqui"
- "Qdo quiser eh so chamar"

Escreva APENAS a mensagem, sem explicacoes."""

PROMPT_FOLLOWUP = """Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem de FOLLOW-UP
continuando uma conversa existente.

Dados do medico:
- Nome: {nome}

Contexto da conversa anterior:
{historico_resumido}

Instrucao do gestor:
{instrucao}

Regras:
- Referencie a conversa anterior naturalmente
- Use linguagem informal
- Ofereca proximos passos claros
- Max 3-4 linhas

Escreva APENAS a mensagem, sem explicacoes."""

PROMPT_CUSTOM = """Voce eh a Julia, escalista da Revoluna. Escreva uma mensagem seguindo
a instrucao especifica do gestor.

Dados do medico:
- Nome: {nome}
- Especialidade: {especialidade}

Instrucao do gestor:
{instrucao}

Regras:
- Siga a instrucao fielmente
- Mantenha o tom da Julia (informal, amigavel)
- Use "vc", "pra", "ta"
- Adapte para soar natural
- Max 4-5 linhas

Escreva APENAS a mensagem, sem explicacoes."""

# Mapeamento tipo -> prompt
PROMPTS = {
    TipoAbordagem.DISCOVERY: PROMPT_DISCOVERY,
    TipoAbordagem.OFERTA: PROMPT_OFERTA,
    TipoAbordagem.REATIVACAO: PROMPT_REATIVACAO,
    TipoAbordagem.FOLLOWUP: PROMPT_FOLLOWUP,
    TipoAbordagem.CUSTOM: PROMPT_CUSTOM,
}


# =============================================================================
# INFERENCIA DE TIPO
# =============================================================================

# Palavras-chave para cada tipo
KEYWORDS_DISCOVERY = [
    "se apresenta", "apresentar", "primeiro contato", "conhecer",
    "descobrir", "discovery", "introducao",
]

KEYWORDS_OFERTA = [
    "oferece", "oferecer", "vaga", "plantao", "oferta",
    "propoe", "propor", "convida", "convidar",
]

KEYWORDS_REATIVACAO = [
    "reativa", "reativar", "sumiu", "faz tempo", "voltou",
    "reaquecer", "retomar contato", "nao responde",
]

KEYWORDS_FOLLOWUP = [
    "follow", "followup", "follow-up", "continua", "continuando",
    "retoma", "retomar conversa", "da sequencia", "lembra",
]


def inferir_tipo(instrucao: str, tem_vaga: bool = False, eh_novo: bool = True) -> TipoAbordagem:
    """
    Infere o tipo de abordagem baseado na instrucao do gestor.

    Args:
        instrucao: Texto da instrucao do gestor
        tem_vaga: Se uma vaga especifica foi mencionada/encontrada
        eh_novo: Se o medico nunca foi contatado antes

    Returns:
        TipoAbordagem inferido
    """
    if not instrucao:
        # Sem instrucao: discovery se novo, followup se existente
        return TipoAbordagem.DISCOVERY if eh_novo else TipoAbordagem.FOLLOWUP

    instrucao_lower = instrucao.lower()

    # Verificar keywords em ordem de prioridade

    # 1. Oferta (se menciona vaga ou keywords de oferta)
    for kw in KEYWORDS_OFERTA:
        if kw in instrucao_lower:
            return TipoAbordagem.OFERTA

    # Se tem vaga explicita, eh oferta
    if tem_vaga:
        return TipoAbordagem.OFERTA

    # 2. Reativacao
    for kw in KEYWORDS_REATIVACAO:
        if kw in instrucao_lower:
            return TipoAbordagem.REATIVACAO

    # 3. Follow-up
    for kw in KEYWORDS_FOLLOWUP:
        if kw in instrucao_lower:
            return TipoAbordagem.FOLLOWUP

    # 4. Discovery
    for kw in KEYWORDS_DISCOVERY:
        if kw in instrucao_lower:
            return TipoAbordagem.DISCOVERY

    # 5. Se tem instrucao especifica mas nao encaixou em nenhum → Custom
    if len(instrucao.split()) > 3:  # Mais que 3 palavras = instrucao especifica
        return TipoAbordagem.CUSTOM

    # 6. Default: discovery para novo, followup para existente
    return TipoAbordagem.DISCOVERY if eh_novo else TipoAbordagem.FOLLOWUP


def obter_prompt(tipo: TipoAbordagem) -> str:
    """
    Retorna o prompt para um tipo de abordagem.

    Args:
        tipo: Tipo de abordagem

    Returns:
        Template do prompt
    """
    return PROMPTS.get(tipo, PROMPT_CUSTOM)


def preparar_prompt(
    tipo: TipoAbordagem,
    nome: str = "Doutor(a)",
    especialidade: str = "",
    instrucao: str = "",
    vaga: dict = None,
    historico: str = "",
    ultima_interacao: str = ""
) -> str:
    """
    Prepara o prompt completo com os dados.

    Args:
        tipo: Tipo de abordagem
        nome: Nome do medico
        especialidade: Especialidade do medico
        instrucao: Instrucao do gestor
        vaga: Dados da vaga (para oferta)
        historico: Historico resumido (para followup)
        ultima_interacao: Data da ultima interacao (para reativacao)

    Returns:
        Prompt formatado
    """
    prompt_template = obter_prompt(tipo)

    # Dados da vaga
    hospital = vaga.get("hospital", "?") if vaga else ""
    data = vaga.get("data", "?") if vaga else ""
    periodo = vaga.get("periodo", "") if vaga else ""
    valor = vaga.get("valor", "?") if vaga else ""
    especialidade_vaga = vaga.get("especialidade", "") if vaga else ""

    # Formatar prompt
    try:
        return prompt_template.format(
            nome=nome or "Doutor(a)",
            especialidade=especialidade or "medico(a)",
            instrucao=instrucao or "",
            hospital=hospital,
            data=data,
            periodo=periodo,
            valor=valor,
            especialidade_vaga=especialidade_vaga,
            historico_resumido=historico or "Sem historico anterior",
            ultima_interacao=ultima_interacao or "ha algum tempo",
        )
    except KeyError as e:
        logger.warning(f"Chave nao encontrada no prompt: {e}")
        return prompt_template


def descrever_tipo(tipo: TipoAbordagem) -> str:
    """
    Retorna descricao amigavel do tipo.

    Args:
        tipo: Tipo de abordagem

    Returns:
        Descricao em portugues
    """
    descricoes = {
        TipoAbordagem.DISCOVERY: "primeiro contato",
        TipoAbordagem.OFERTA: "oferta de vaga",
        TipoAbordagem.REATIVACAO: "reativacao",
        TipoAbordagem.FOLLOWUP: "follow-up",
        TipoAbordagem.CUSTOM: "mensagem personalizada",
    }
    return descricoes.get(tipo, "mensagem")


# =============================================================================
# EXTRAIR DADOS DA INSTRUCAO
# =============================================================================

def extrair_telefone(texto: str) -> str | None:
    """
    Extrai numero de telefone de um texto.

    Args:
        texto: Texto para buscar

    Returns:
        Telefone encontrado ou None
    """
    # Padroes de telefone
    padroes = [
        r'(?:55)?(\d{2})[\s.-]?(\d{4,5})[\s.-]?(\d{4})',  # 11 99999-9999
        r'(\d{10,11})',  # 11999999999
    ]

    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            # Juntar grupos
            telefone = ''.join(match.groups())
            telefone = re.sub(r'\D', '', telefone)
            if len(telefone) >= 10:
                return telefone

    return None


def extrair_hospital(texto: str, hospitais_conhecidos: list[str] = None) -> str | None:
    """
    Extrai nome de hospital de um texto.

    Args:
        texto: Texto para buscar
        hospitais_conhecidos: Lista de hospitais para match

    Returns:
        Hospital encontrado ou None
    """
    texto_lower = texto.lower()

    # Hospitais conhecidos (expandir conforme necessario)
    hospitais = hospitais_conhecidos or [
        "sao luiz", "einstein", "sirio", "oswaldo cruz",
        "santa catarina", "nove de julho", "samaritano",
        "beneficencia", "hcor", "pro matre",
    ]

    for hospital in hospitais:
        if hospital.lower() in texto_lower:
            return hospital.title()

    return None


def extrair_data(texto: str) -> str | None:
    """
    Extrai data de um texto.

    Args:
        texto: Texto para buscar

    Returns:
        Data em formato ISO ou None
    """
    texto_lower = texto.lower()

    # Hoje, amanha, etc
    if "hoje" in texto_lower:
        return agora_brasilia().strftime("%Y-%m-%d")
    if "amanha" in texto_lower or "amanhã" in texto_lower:
        return (agora_brasilia() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Dia especifico: "dia 15", "15/12", "15 de dezembro"
    padroes = [
        r'dia\s+(\d{1,2})(?:/(\d{1,2}))?',  # dia 15 ou dia 15/12
        r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?',  # 15/12 ou 15/12/24
        r'(\d{1,2})\s+de\s+(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)',
    ]

    for padrao in padroes:
        match = re.search(padrao, texto_lower)
        if match:
            grupos = match.groups()
            dia = int(grupos[0])

            # Se tem mes
            if len(grupos) > 1 and grupos[1]:
                if grupos[1].isdigit():
                    mes = int(grupos[1])
                else:
                    meses = {
                        "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
                        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
                        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
                    }
                    mes = meses.get(grupos[1], agora_brasilia().month)
            else:
                mes = agora_brasilia().month

            ano = agora_brasilia().year
            if mes < agora_brasilia().month:
                ano += 1  # Proximo ano se mes ja passou

            try:
                return f"{ano}-{mes:02d}-{dia:02d}"
            except ValueError:
                pass

    return None
