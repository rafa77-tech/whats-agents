"""
Validacao de output para garantir que Julia nunca revele ser IA.
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class ValidacaoResult:
    """Resultado da validacao."""
    valido: bool
    motivo: Optional[str] = None
    tipo_violacao: Optional[str] = None
    trecho_problematico: Optional[str] = None
    severidade: str = "baixa"  # baixa, media, alta, critica


# Padroes que indicam revelacao de IA
PADROES_REVELACAO_IA = [
    # Mencoes diretas
    (r'\b(sou|como)\s+(uma?\s+)?(ia|intelig[eê]ncia\s+artificial)\b', 'mencao_ia', 'critica'),
    (r'\b(sou|como)\s+(uma?\s+)?(bot|rob[oô]|chatbot)\b', 'mencao_bot', 'critica'),
    (r'\bum\s+bot\b', 'mencao_bot_simples', 'critica'),  # "um bot" isolado
    (r'\b(sou|como)\s+(uma?\s+)?assistente\s+virtual\b', 'mencao_assistente', 'critica'),
    (r'\bassistente\s+de\s+ia\b', 'mencao_assistente_ia', 'critica'),
    (r'\bmodelo\s+de\s+linguagem\b', 'mencao_modelo', 'critica'),
    (r'\b(criado|desenvolvido|treinado)\s+(pela|por)\s+(anthropic|openai|google)\b', 'mencao_empresa', 'critica'),
    (r'\bclaude\b', 'mencao_claude', 'critica'),
    (r'\bgpt\b', 'mencao_gpt', 'critica'),

    # Frases evasivas sobre ser IA
    (r'n[aã]o\s+sou\s+(exatamente\s+)?(uma?\s+)?pessoa', 'evasiva_pessoa', 'alta'),
    (r'n[aã]o\s+tenho\s+(um\s+)?corpo\s+f[ií]sico', 'evasiva_corpo', 'alta'),
    (r'existo\s+apenas\s+(como|no)\s+(texto|digital)', 'evasiva_existencia', 'alta'),
    (r'sou\s+(um\s+)?programa', 'evasiva_programa', 'critica'),
    (r'fui\s+(programad[oa]|criada)\s+para', 'evasiva_programado', 'alta'),

    # Limitacoes de IA
    (r'minhas?\s+capacidades?\s+(s[aã]o|est[aã]o)\s+limitadas?', 'limitacao_ia', 'media'),
    (r'n[aã]o\s+tenho\s+acesso\s+a\s+informa[çc][oõ]es\s+(em\s+tempo\s+real|atuais)', 'limitacao_tempo_real', 'media'),
    (r'meu\s+conhecimento\s+(foi\s+)?cortado\s+em', 'limitacao_conhecimento', 'alta'),
    (r'n[aã]o\s+posso\s+(navegar|acessar)\s+(a\s+)?internet', 'limitacao_internet', 'media'),
    (r'n[aã]o\s+tenho\s+mem[oó]ria\s+de\s+conversas\s+anteriores', 'limitacao_memoria', 'media'),

    # Respostas roboticas
    (r'^(claro|certamente|com\s+prazer)[,!]\s+vou', 'resposta_robotica', 'baixa'),
    (r'como\s+posso\s+ajud[aá]-l[ao]\s+hoje', 'resposta_robotica', 'baixa'),
    (r'estou\s+aqui\s+para\s+ajudar', 'resposta_robotica', 'baixa'),
    (r'fico\s+feliz\s+em\s+ajudar', 'resposta_robotica', 'baixa'),
]


def detectar_revelacao_ia(texto: str) -> ValidacaoResult:
    """
    Detecta se o texto revela que Julia e IA.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes da validacao
    """
    texto_lower = texto.lower()

    for padrao, tipo, severidade in PADROES_REVELACAO_IA:
        match = re.search(padrao, texto_lower)
        if match:
            logger.warning(
                f"Revelacao de IA detectada: tipo={tipo}, "
                f"trecho='{match.group()}'"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Texto revela que Julia e IA ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group(),
                severidade=severidade
            )

    return ValidacaoResult(valido=True)


# Padroes de formato proibido
PADROES_FORMATO_PROIBIDO = [
    # Bullet points e listas
    (r'^\s*[-•*]\s+', 'bullet_point', 'media'),
    (r'^\s*\d+[.)]\s+', 'lista_numerada', 'media'),
    (r'\n\s*[-•*]\s+', 'bullet_point_inline', 'media'),
    (r'\n\s*\d+[.)]\s+', 'lista_inline', 'media'),

    # Markdown
    (r'\*\*[^*]+\*\*', 'markdown_bold', 'baixa'),
    (r'__[^_]+__', 'markdown_bold_alt', 'baixa'),
    (r'`[^`]+`', 'markdown_code', 'baixa'),
    (r'#{1,6}\s+', 'markdown_header', 'media'),
    (r'\[.+\]\(.+\)', 'markdown_link', 'baixa'),

    # Estrutura muito formal
    (r'(prezado|estimado|caro)\s+(dr|doutor|senhor)', 'saudacao_formal', 'media'),
    (r'(atenciosamente|cordialmente|respeitosamente)', 'despedida_formal', 'media'),
]


def detectar_formato_proibido(texto: str) -> ValidacaoResult:
    """
    Detecta formatos proibidos (listas, markdown, etc).

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes
    """
    for padrao, tipo, severidade in PADROES_FORMATO_PROIBIDO:
        match = re.search(padrao, texto, re.MULTILINE | re.IGNORECASE)
        if match:
            logger.warning(
                f"Formato proibido detectado: tipo={tipo}, "
                f"trecho='{match.group()[:50]}'"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Formato proibido ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group()[:100],
                severidade=severidade
            )

    return ValidacaoResult(valido=True)


# Padroes de linguagem corporativa/robotica
PADROES_LINGUAGEM_ROBOTICA = [
    # Muito formal
    (r'gostar[ií]amos?\s+de\s+informar', 'formal_informar', 'media'),
    (r'temos\s+o\s+prazer\s+de', 'formal_prazer', 'media'),
    (r'vimos\s+por\s+meio\s+desta', 'formal_carta', 'alta'),
    (r'segue\s+(em\s+)?anexo', 'formal_anexo', 'media'),
    (r'conforme\s+solicitado', 'formal_solicitado', 'baixa'),

    # Excesso de formalidade
    (r'vossa\s+(senhoria|excel[eê]ncia)', 'formal_vossa', 'alta'),
    (r'mui(to)?\s+respeitosamente', 'formal_respeitosamente', 'media'),
    (r'venho\s+por\s+meio\s+desta', 'formal_venho', 'alta'),

    # Linguagem de servico de atendimento
    (r'sua\s+(liga[çc][aã]o|chamada)\s+[eé]\s+muito\s+importante', 'sac_importante', 'alta'),
    (r'em\s+que\s+posso\s+(lhe\s+)?ser\s+[uú]til', 'sac_util', 'media'),
    (r'agrade[çc]o\s+(a\s+)?sua\s+(prefer[eê]ncia|paci[eê]ncia)', 'sac_agradeco', 'media'),
    (r'obrigad[oa]\s+por\s+entrar\s+em\s+contato', 'sac_contato', 'media'),

    # Linguagem de sistema/processamento
    (r'solicita[çc][aã]o\s+recebida', 'sac_solicitacao', 'alta'),
    (r'aguarde\s+(o\s+)?processamento', 'sac_processamento', 'alta'),
    (r'seu\s+pedido\s+foi\s+(registrado|recebido)', 'sac_pedido', 'media'),
    (r'protocolo\s+(de\s+atendimento|n[uú]mero)', 'sac_protocolo', 'media'),
]


def detectar_linguagem_robotica(texto: str) -> ValidacaoResult:
    """
    Detecta linguagem muito formal ou robotica.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult com detalhes
    """
    texto_lower = texto.lower()

    for padrao, tipo, severidade in PADROES_LINGUAGEM_ROBOTICA:
        match = re.search(padrao, texto_lower)
        if match:
            logger.warning(
                f"Linguagem robotica detectada: tipo={tipo}"
            )
            return ValidacaoResult(
                valido=False,
                motivo=f"Linguagem muito formal/robotica ({tipo})",
                tipo_violacao=tipo,
                trecho_problematico=match.group(),
                severidade=severidade
            )

    return ValidacaoResult(valido=True)


class OutputValidator:
    """
    Validador completo de output.

    Executa todos os validadores em sequencia.
    """

    def __init__(self):
        self.validadores: list[Callable[[str], ValidacaoResult]] = [
            detectar_revelacao_ia,
            detectar_formato_proibido,
            detectar_linguagem_robotica,
        ]
        self.metricas = {
            "total_validacoes": 0,
            "falhas_por_tipo": {},
        }

    def adicionar_validador(
        self,
        validador: Callable[[str], ValidacaoResult]
    ) -> "OutputValidator":
        """Adiciona validador customizado."""
        self.validadores.append(validador)
        return self

    def validar(self, texto: str) -> ValidacaoResult:
        """
        Executa todos os validadores.

        Para no primeiro que falhar (fail-fast).

        Args:
            texto: Texto a validar

        Returns:
            ValidacaoResult (primeiro que falhar ou sucesso)
        """
        self.metricas["total_validacoes"] += 1

        if not texto or not texto.strip():
            return ValidacaoResult(valido=True)

        for validador in self.validadores:
            resultado = validador(texto)

            if not resultado.valido:
                # Registrar metrica
                tipo = resultado.tipo_violacao or "desconhecido"
                self.metricas["falhas_por_tipo"][tipo] = \
                    self.metricas["falhas_por_tipo"].get(tipo, 0) + 1

                return resultado

        return ValidacaoResult(valido=True)

    def get_metricas(self) -> dict:
        """Retorna metricas de validacao."""
        return self.metricas.copy()


# Instancia global
output_validator = OutputValidator()


async def validar_resposta(texto: str) -> ValidacaoResult:
    """
    Funcao helper para validar resposta.

    Args:
        texto: Resposta a validar

    Returns:
        ValidacaoResult
    """
    return output_validator.validar(texto)


async def validar_e_corrigir(
    texto: str,
    tentativas_max: int = 2
) -> tuple[str, bool]:
    """
    Valida e tenta corrigir resposta se invalida.

    Se validacao falhar, tenta:
    1. Remover formatacao proibida
    2. Se ainda falhar, retorna texto original com flag

    Args:
        texto: Resposta a validar
        tentativas_max: Maximo de correcoes

    Returns:
        Tuple (texto_corrigido, foi_modificado)
    """
    resultado = output_validator.validar(texto)

    if resultado.valido:
        return texto, False

    # Tentar corrigir
    texto_corrigido = texto

    for _ in range(tentativas_max):
        # Remover bullets
        texto_corrigido = re.sub(r'^\s*[-•*]\s+', '', texto_corrigido, flags=re.MULTILINE)
        texto_corrigido = re.sub(r'\n\s*[-•*]\s+', '\n', texto_corrigido)

        # Remover listas numeradas
        texto_corrigido = re.sub(r'^\s*\d+[.)]\s+', '', texto_corrigido, flags=re.MULTILINE)

        # Remover markdown
        texto_corrigido = re.sub(r'\*\*([^*]+)\*\*', r'\1', texto_corrigido)
        texto_corrigido = re.sub(r'`([^`]+)`', r'\1', texto_corrigido)
        texto_corrigido = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto_corrigido)

        # Validar novamente
        resultado = output_validator.validar(texto_corrigido)
        if resultado.valido:
            return texto_corrigido, True

    # Se ainda falhar, logar e retornar
    logger.error(
        f"Resposta invalida apos correcoes: {resultado.motivo}. "
        f"Trecho: {resultado.trecho_problematico}"
    )

    # Se for critico (revelacao IA), nao envia
    if resultado.severidade == "critica":
        logger.critical(
            f"BLOQUEADO: Resposta revelaria IA! "
            f"Tipo: {resultado.tipo_violacao}"
        )
        return "", True  # Retorna vazio para nao enviar

    return texto_corrigido, True
