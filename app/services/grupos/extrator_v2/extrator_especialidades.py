"""
Extrator de especialidades médicas.

Sprint 51 - Correção urgente: especialidade não estava sendo extraída.

Extrai especialidades de seções de texto usando padrões conhecidos.
"""

import re
from typing import List, Optional

from app.core.logging import get_logger
from app.services.grupos.extrator_v2.types import EspecialidadeExtraida

logger = get_logger(__name__)


# =============================================================================
# Mapeamento de Especialidades
# =============================================================================

# Padrões de especialidades com variações comuns
ESPECIALIDADES_PATTERNS = {
    # Clínica Médica
    r"\bcl[ií]nica\s*m[eé]dica\b": "Clínica Médica",
    r"\b(?<!\w)cm(?!\w)": "Clínica Médica",
    r"\bcl[ií]nico\s*geral\b": "Clínica Médica",
    # Pediatria
    r"\bpediatria\b": "Pediatria",
    r"\bpediatra\b": "Pediatria",
    r"\b(?<!\w)ped(?!\w)": "Pediatria",
    # Ginecologia e Obstetrícia
    r"\bginecologia\s*(?:e|\/|\s)\s*obstetr[ií]cia\b": "Ginecologia e Obstetrícia",
    r"\bgo\b": "Ginecologia e Obstetrícia",
    r"\bgineco(?:logia)?\b": "Ginecologia",
    r"\bobstetr[ií]cia\b": "Obstetrícia",
    r"\bobstetra\b": "Obstetrícia",
    # Ortopedia
    r"\bortopedia\b": "Ortopedia",
    r"\bortopedista\b": "Ortopedia",
    r"\b(?<!\w)orto(?!\w)": "Ortopedia",
    # Cardiologia
    r"\bcardiologia\b": "Cardiologia",
    r"\bcardiologista\b": "Cardiologia",
    r"\b(?<!\w)cardio(?!\w)": "Cardiologia",
    # Cirurgia Geral
    r"\bcirurgia\s*geral\b": "Cirurgia Geral",
    r"\bcirurgi[aã]o\s*geral\b": "Cirurgia Geral",
    r"\b(?<!\w)cg(?!\w)": "Cirurgia Geral",
    # Neurologia
    r"\bneurologia\b": "Neurologia",
    r"\bneurologista\b": "Neurologia",
    r"\b(?<!\w)neuro(?!\w)": "Neurologia",
    # Psiquiatria
    r"\bpsiquiatria\b": "Psiquiatria",
    r"\bpsiquiatra\b": "Psiquiatria",
    r"\b(?<!\w)psiq(?!\w)": "Psiquiatria",
    # Anestesiologia
    r"\banestesiologia\b": "Anestesiologia",
    r"\banestesista\b": "Anestesiologia",
    r"\b(?<!\w)anestesio(?!\w)": "Anestesiologia",
    # Emergência/Urgência
    r"\bemerg[eê]ncia\b": "Emergência",
    r"\burg[eê]ncia\b": "Urgência",
    r"\bps\b": "Pronto Socorro",
    r"\bpronto\s*socorro\b": "Pronto Socorro",
    r"\bpronto\s*atendimento\b": "Pronto Atendimento",
    # UTI
    r"\buti\b": "UTI",
    r"\bterapia\s*intensiva\b": "UTI",
    r"\bintensivista\b": "UTI",
    # Outras especialidades comuns
    r"\bdermatologia\b": "Dermatologia",
    r"\boftalmologia\b": "Oftalmologia",
    r"\botorrinolaringologia\b": "Otorrinolaringologia",
    r"\botorrino\b": "Otorrinolaringologia",
    r"\burologia\b": "Urologia",
    r"\bnefrologia\b": "Nefrologia",
    r"\bgastroenterologia\b": "Gastroenterologia",
    r"\bgastro\b": "Gastroenterologia",
    r"\bpneumologia\b": "Pneumologia",
    r"\bendocrinologia\b": "Endocrinologia",
    r"\breumatologia\b": "Reumatologia",
    r"\bhematologia\b": "Hematologia",
    r"\boncologia\b": "Oncologia",
    r"\bgeriatria\b": "Geriatria",
    r"\bneonatologia\b": "Neonatologia",
    r"\binfectologia\b": "Infectologia",
    # Exames/Procedimentos
    r"\bultrass?onografia\b": "Ultrassonografia",
    r"\busg\b": "Ultrassonografia",
    r"\bendoscopia\b": "Endoscopia",
    r"\bcolonoscopia\b": "Colonoscopia",
    r"\bradiologia\b": "Radiologia",
    r"\btomografia\b": "Tomografia",
    r"\bressonância\b": "Ressonância",
}

# Compilar patterns
COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), nome) for pattern, nome in ESPECIALIDADES_PATTERNS.items()
]


def extrair_especialidades(secoes: List[str]) -> List[EspecialidadeExtraida]:
    """
    Extrai especialidades de uma lista de seções de texto.

    Args:
        secoes: Lista de strings com possíveis especialidades

    Returns:
        Lista de EspecialidadeExtraida encontradas
    """
    if not secoes:
        return []

    especialidades_encontradas: List[EspecialidadeExtraida] = []
    nomes_vistos: set = set()  # Para evitar duplicatas

    # Juntar todas as seções em um texto para análise
    texto_completo = " ".join(secoes)

    for pattern, nome in COMPILED_PATTERNS:
        if pattern.search(texto_completo):
            # Evitar duplicatas
            if nome not in nomes_vistos:
                nomes_vistos.add(nome)
                especialidades_encontradas.append(
                    EspecialidadeExtraida(
                        nome=nome,
                        confianca=0.8 if len(nome) > 3 else 0.6,  # Abreviações têm menos confiança
                    )
                )

    if especialidades_encontradas:
        logger.debug(f"Especialidades extraídas: {[e.nome for e in especialidades_encontradas]}")

    return especialidades_encontradas


def extrair_especialidade_do_titulo(texto: str) -> Optional[EspecialidadeExtraida]:
    """
    Extrai especialidade de um título de vaga.

    Procura padrões como:
    - "VAGA PARA MÉDICO - GINECOLOGIA"
    - "Plantão de PEDIATRIA"
    - "Médico CARDIOLOGISTA"

    Args:
        texto: Texto completo da mensagem

    Returns:
        EspecialidadeExtraida se encontrada no título, None caso contrário
    """
    # Padrões de título
    titulo_patterns = [
        r"vaga\s+(?:para\s+)?m[eé]dico[a]?\s*[-–:]\s*(.+?)(?:\n|$)",
        r"plant[aã]o\s+(?:de\s+)?(.+?)(?:\n|$)",
        r"m[eé]dico[a]?\s+(.+?)(?:\n|$)",
        r"\*(.+?)\*",  # Texto em negrito no WhatsApp
    ]

    for pattern in titulo_patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            possivel_especialidade = match.group(1).strip()
            # Verificar se o texto capturado contém uma especialidade conhecida
            especialidades = extrair_especialidades([possivel_especialidade])
            if especialidades:
                return especialidades[0]

    return None


def extrair_especialidades_completo(
    secoes_especialidade: List[str], texto_completo: str
) -> List[EspecialidadeExtraida]:
    """
    Extração completa de especialidades.

    Combina múltiplas estratégias:
    1. Extrai das seções identificadas pelo parser
    2. Extrai do título da mensagem
    3. Extrai do texto completo como fallback

    Args:
        secoes_especialidade: Seções identificadas pelo parser
        texto_completo: Texto completo da mensagem

    Returns:
        Lista de especialidades encontradas (sem duplicatas)
    """
    nomes_vistos: set = set()
    resultado: List[EspecialidadeExtraida] = []

    def adicionar(especialidade: EspecialidadeExtraida) -> None:
        if especialidade.nome not in nomes_vistos:
            nomes_vistos.add(especialidade.nome)
            resultado.append(especialidade)

    # 1. Extrair das seções identificadas
    for esp in extrair_especialidades(secoes_especialidade):
        adicionar(esp)

    # 2. Extrair do título
    esp_titulo = extrair_especialidade_do_titulo(texto_completo)
    if esp_titulo:
        adicionar(esp_titulo)

    # 3. Fallback: extrair do texto completo se ainda não encontrou
    if not resultado:
        for esp in extrair_especialidades([texto_completo]):
            adicionar(esp)

    if resultado:
        logger.info(f"Especialidades encontradas: {[e.nome for e in resultado]}")
    else:
        logger.warning("Nenhuma especialidade encontrada na mensagem")

    return resultado
