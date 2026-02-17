"""
Extrator LLM Unificado - Pipeline v3.

Sprint 52 - Substitui extratores regex por LLM que classifica E extrai em uma única chamada.

Vantagens:
- Resolve bug R$ 202 (regex capturava "202" de "2026")
- Entende contexto semântico
- Uma única chamada LLM (vs 2 no v2: classificação + extração separadas)
- Normaliza especialidades automaticamente
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Optional
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.redis import cache_get, cache_set
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    DiaSemana,
    Periodo,
    ResultadoExtracaoV2,
    HospitalExtraido,
    EspecialidadeExtraida,
)

logger = get_logger(__name__)


# =============================================================================
# Constantes
# =============================================================================

CACHE_TTL = 86400  # 24 horas
CACHE_PREFIX = "grupo:extracao_llm:"

# Especialidades válidas para normalização
ESPECIALIDADES_VALIDAS = [
    "Acupuntura",
    "Alergia e Imunologia",
    "Anestesiologia",
    "Angiologia",
    "Cardiologia",
    "Cirurgia Cardiovascular",
    "Cirurgia da Mão",
    "Cirurgia de Cabeça e Pescoço",
    "Cirurgia do Aparelho Digestivo",
    "Cirurgia Geral",
    "Cirurgia Oncológica",
    "Cirurgia Pediátrica",
    "Cirurgia Plástica",
    "Cirurgia Torácica",
    "Cirurgia Vascular",
    "Clínica Médica",
    "Coloproctologia",
    "Dermatologia",
    "Endocrinologia e Metabologia",
    "Endoscopia",
    "Gastroenterologia",
    "Generalista",
    "Genética Médica",
    "Geriatria",
    "Ginecologia e Obstetrícia",
    "Hematologia e Hemoterapia",
    "Homeopatia",
    "Infectologia",
    "Mastologia",
    "Medicina de Emergência",
    "Medicina de Família",
    "Medicina do Trabalho",
    "Medicina do Tráfego",
    "Medicina Esportiva",
    "Medicina Física e Reabilitação",
    "Medicina Intensiva",
    "Medicina Legal e Perícia Médica",
    "Medicina Nuclear",
    "Medicina Preventiva e Social",
    "Nefrologia",
    "Neonatologia",
    "Neurocirurgia",
    "Neurologia",
    "Nutrologia",
    "Oftalmologia",
    "Oncologia Clínica",
    "Ortopedia e Traumatologia",
    "Otorrinolaringologia",
    "Patologia",
    "Patologia Clínica",
    "Pediatria",
    "Pneumologia",
    "Psiquiatria",
    "Radiologia e Diagnóstico por Imagem",
    "Radioterapia",
    "Reumatologia",
    "Urologia",
]

# Prompt unificado para classificação + extração
PROMPT_EXTRACAO_UNIFICADA = """Você é um especialista em análise de vagas médicas de plantão.

Analise a mensagem abaixo e extraia as informações de vagas de plantão médico.

MENSAGEM:
```
{texto}
```

CONTEXTO:
- Grupo: {nome_grupo}
- Remetente: {nome_contato}
- Data de referência: {data_referencia}

REGRAS CRÍTICAS:
1. VALOR é o preço POR PLANTÃO individual, não o total
   - "R$ 10.000 por 5 plantões" → valor = 2000 (dividir pelo número de plantões)
   - "R$ 7.500 pelos 3 plantões" → valor = 2500 (dividir: 7500/3)
   - "R$ 2.500" para uma vaga → valor = 2500
   - Se não mencionar valor, valor = null
   - IMPORTANTE: Se o valor é claramente um TOTAL para múltiplos plantões, DIVIDA!

2. NUNCA confunda números de datas com valores
   - "19/01/2026" são DATAS, não valores
   - "202" ou "2026" isolados são provavelmente partes de datas
   - "02/2026" é uma data (fevereiro de 2026), NÃO R$ 202
   - Valores monetários têm "R$", "reais", ou contexto claro de pagamento

3. ESPECIALIDADE deve ser normalizada para uma das seguintes:
{especialidades}

   - "GO", "gineco", "obstetrícia" → "Ginecologia e Obstetrícia"
   - "CM", "clínica", "clinico geral" → "Clínica Médica"
   - "UTI", "intensivista" → "Medicina Intensiva"
   - "PS", "pronto socorro", "emergência" → "Medicina de Emergência"
   - "Pediatra", "ped" → "Pediatria"
   - "Ortopedista", "orto" → "Ortopedia e Traumatologia"

4. PERÍODO deve ser um dos seguintes:
   - "manha" (07:00-13:00)
   - "tarde" (13:00-19:00)
   - "noite" ou "noturno" (19:00-07:00)
   - "diurno" ou "SD" (07:00-19:00, 12h)
   - "cinderela" (19:00-01:00)

5. HOSPITAL deve ser o nome de um estabelecimento de saúde real:
   - Hospitais, UPAs, UBSs, clínicas, prontos-socorros, maternidades, centros médicos
   - NÃO use nomes de pessoas ou contatos como hospital (ex: "Dr. Fulano", "Maria:")
   - NÃO use especialidades médicas como hospital (ex: "Cardiologia", "Ortopedia")
   - NÃO use fragmentos de texto, empresas não-médicas ou palavras genéricas
   - Se não conseguir identificar o hospital com certeza, use null no campo "hospital"

6. Uma mensagem pode ter MÚLTIPLAS VAGAS se mencionar:
   - Múltiplas datas
   - Múltiplos períodos
   - Múltiplos hospitais

Retorne APENAS um JSON válido no formato:
{{
  "eh_vaga": true/false,
  "confianca": 0.0 a 1.0,
  "motivo_descarte": "string explicando por que não é vaga" ou null,
  "vagas": [
    {{
      "hospital": "Nome do hospital ou local",
      "especialidade": "Especialidade normalizada da lista acima",
      "data": "YYYY-MM-DD",
      "dia_semana": "segunda/terca/quarta/quinta/sexta/sabado/domingo",
      "periodo": "manha/tarde/noite/diurno/noturno/cinderela",
      "hora_inicio": "HH:MM" ou null,
      "hora_fim": "HH:MM" ou null,
      "valor": número inteiro em reais ou null,
      "contato_nome": "Nome do contato" ou null,
      "contato_whatsapp": "Telefone" ou null,
      "observacoes": "Informações adicionais" ou null
    }}
  ]
}}

Se NÃO for uma vaga de plantão médico, retorne:
{{
  "eh_vaga": false,
  "confianca": 0.0 a 1.0,
  "motivo_descarte": "Explicação do motivo",
  "vagas": []
}}"""


# =============================================================================
# Tipos
# =============================================================================


@dataclass
class ResultadoExtracaoLLM:
    """Resultado da extração via LLM."""

    eh_vaga: bool
    confianca: float
    motivo_descarte: Optional[str] = None
    vagas: List[dict] = field(default_factory=list)
    tokens_usados: int = 0
    do_cache: bool = False
    erro: Optional[str] = None


# =============================================================================
# Cache
# =============================================================================


def _hash_texto(texto: str) -> str:
    """Gera hash do texto normalizado para cache."""
    # Normaliza: lowercase, remove espaços extras
    normalizado = " ".join(texto.lower().split())
    return hashlib.md5(normalizado.encode()).hexdigest()


async def buscar_extracao_cache(texto: str) -> Optional[ResultadoExtracaoLLM]:
    """Busca extração no cache."""
    try:
        chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"
        dados = await cache_get(chave)
        if dados:
            dados = json.loads(dados)
            return ResultadoExtracaoLLM(
                eh_vaga=dados["eh_vaga"],
                confianca=dados["confianca"],
                motivo_descarte=dados.get("motivo_descarte"),
                vagas=dados.get("vagas", []),
                tokens_usados=0,
                do_cache=True,
            )
    except Exception as e:
        logger.warning(f"Erro ao buscar cache de extração: {e}")
    return None


async def salvar_extracao_cache(texto: str, resultado: ResultadoExtracaoLLM) -> None:
    """Salva extração no cache."""
    try:
        chave = f"{CACHE_PREFIX}{_hash_texto(texto)}"
        dados = json.dumps(
            {
                "eh_vaga": resultado.eh_vaga,
                "confianca": resultado.confianca,
                "motivo_descarte": resultado.motivo_descarte,
                "vagas": resultado.vagas,
            }
        )
        await cache_set(chave, dados, CACHE_TTL)
    except Exception as e:
        logger.warning(f"Erro ao salvar cache de extração: {e}")


# =============================================================================
# LLM
# =============================================================================


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
async def _chamar_llm_extracao(prompt: str) -> tuple:
    """Chama o LLM para extração com retry."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1500,  # Mais tokens para extração completa
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    resposta_texto = response.content[0].text.strip()
    tokens_usados = response.usage.input_tokens + response.usage.output_tokens

    return resposta_texto, tokens_usados


def _parsear_resposta_extracao(texto: str) -> ResultadoExtracaoLLM:
    """Parseia resposta JSON do LLM."""
    texto = texto.strip()

    # Remove markdown code blocks se presentes
    if texto.startswith("```"):
        # Remove ```json ou ``` do início
        texto = texto.split("\n", 1)[1] if "\n" in texto else texto[3:]
    if texto.endswith("```"):
        texto = texto[:-3]

    texto = texto.strip()

    # Tenta encontrar JSON no texto
    if texto.startswith("{"):
        dados = json.loads(texto)
    else:
        import re

        match = re.search(r"\{[\s\S]*\}", texto)
        if match:
            dados = json.loads(match.group())
        else:
            raise json.JSONDecodeError("JSON não encontrado", texto, 0)

    return ResultadoExtracaoLLM(
        eh_vaga=dados.get("eh_vaga", False),
        confianca=float(dados.get("confianca", 0.0)),
        motivo_descarte=dados.get("motivo_descarte"),
        vagas=dados.get("vagas", []),
    )


async def extrair_com_llm(
    texto: str,
    nome_grupo: str = "",
    nome_contato: str = "",
    data_referencia: Optional[date] = None,
    usar_cache: bool = True,
) -> ResultadoExtracaoLLM:
    """
    Extrai dados de vagas usando LLM.

    Args:
        texto: Texto da mensagem
        nome_grupo: Nome do grupo
        nome_contato: Nome de quem enviou
        data_referencia: Data de referência para "hoje"/"amanhã"
        usar_cache: Se deve usar cache

    Returns:
        ResultadoExtracaoLLM com classificação e dados extraídos
    """
    # Verificar cache
    if usar_cache:
        cached = await buscar_extracao_cache(texto)
        if cached:
            logger.debug(f"Extração LLM do cache: eh_vaga={cached.eh_vaga}")
            return cached

    # Formatar lista de especialidades para o prompt
    especialidades_str = "\n".join(f"   - {e}" for e in ESPECIALIDADES_VALIDAS)

    prompt = PROMPT_EXTRACAO_UNIFICADA.format(
        texto=texto,
        nome_grupo=nome_grupo or "Desconhecido",
        nome_contato=nome_contato or "Desconhecido",
        data_referencia=(data_referencia or date.today()).isoformat(),
        especialidades=especialidades_str,
    )

    try:
        resposta_texto, tokens_usados = await _chamar_llm_extracao(prompt)
        resultado = _parsear_resposta_extracao(resposta_texto)
        resultado.tokens_usados = tokens_usados

        # Salvar no cache
        if usar_cache:
            await salvar_extracao_cache(texto, resultado)

        logger.info(
            f"Extração LLM: eh_vaga={resultado.eh_vaga}, "
            f"vagas={len(resultado.vagas)}, tokens={tokens_usados}"
        )

        return resultado

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear JSON do LLM: {e}")
        return ResultadoExtracaoLLM(
            eh_vaga=False, confianca=0.0, motivo_descarte="erro_parse_json", erro=str(e)
        )
    except anthropic.APIError as e:
        logger.error(f"Erro API Anthropic na extração: {e}")
        return ResultadoExtracaoLLM(
            eh_vaga=False, confianca=0.0, motivo_descarte="erro_api", erro=str(e)
        )
    except Exception as e:
        logger.exception(f"Erro inesperado na extração LLM: {e}")
        return ResultadoExtracaoLLM(
            eh_vaga=False, confianca=0.0, motivo_descarte="erro_desconhecido", erro=str(e)
        )


# =============================================================================
# Conversão para tipos v2
# =============================================================================


def _dia_semana_from_str(dia: str) -> DiaSemana:
    """Converte string para DiaSemana."""
    mapa = {
        "segunda": DiaSemana.SEGUNDA,
        "terca": DiaSemana.TERCA,
        "terça": DiaSemana.TERCA,
        "quarta": DiaSemana.QUARTA,
        "quinta": DiaSemana.QUINTA,
        "sexta": DiaSemana.SEXTA,
        "sabado": DiaSemana.SABADO,
        "sábado": DiaSemana.SABADO,
        "domingo": DiaSemana.DOMINGO,
    }
    return mapa.get(dia.lower(), DiaSemana.SEGUNDA)


def _periodo_from_str(periodo: str) -> Periodo:
    """Converte string para Periodo."""
    mapa = {
        "manha": Periodo.MANHA,
        "manhã": Periodo.MANHA,
        "tarde": Periodo.TARDE,
        "noite": Periodo.NOITE,
        "noturno": Periodo.NOTURNO,
        "diurno": Periodo.DIURNO,
        "cinderela": Periodo.CINDERELA,
    }
    return mapa.get(periodo.lower(), Periodo.DIURNO)


def _parse_time(hora_str: Optional[str]) -> Optional[time]:
    """Converte string HH:MM para time."""
    if not hora_str:
        return None
    try:
        parts = hora_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _parse_date(data_str: Optional[str]) -> Optional[date]:
    """Converte string YYYY-MM-DD para date."""
    if not data_str:
        return None
    try:
        parts = data_str.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def converter_para_vagas_atomicas(
    resultado: ResultadoExtracaoLLM,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
) -> List[VagaAtomica]:
    """
    Converte resultado do LLM para lista de VagaAtomica.

    Args:
        resultado: Resultado da extração LLM
        mensagem_id: ID da mensagem original
        grupo_id: ID do grupo

    Returns:
        Lista de VagaAtomica
    """
    vagas = []

    for vaga_dict in resultado.vagas:
        try:
            data_vaga = _parse_date(vaga_dict.get("data"))
            if not data_vaga:
                logger.warning(f"Vaga sem data válida: {vaga_dict}")
                continue

            hospital = vaga_dict.get("hospital")
            if not hospital:
                logger.warning(f"Vaga sem hospital: {vaga_dict}")
                continue

            vaga = VagaAtomica(
                data=data_vaga,
                dia_semana=_dia_semana_from_str(vaga_dict.get("dia_semana", "segunda")),
                periodo=_periodo_from_str(vaga_dict.get("periodo", "diurno")),
                valor=vaga_dict.get("valor") or 0,
                hospital_raw=hospital,
                hora_inicio=_parse_time(vaga_dict.get("hora_inicio")),
                hora_fim=_parse_time(vaga_dict.get("hora_fim")),
                especialidade_raw=vaga_dict.get("especialidade"),
                contato_nome=vaga_dict.get("contato_nome"),
                contato_whatsapp=vaga_dict.get("contato_whatsapp"),
                observacoes=vaga_dict.get("observacoes"),
                confianca_geral=resultado.confianca,
                mensagem_id=mensagem_id,
                grupo_id=grupo_id,
            )
            vagas.append(vaga)

        except Exception as e:
            logger.warning(f"Erro ao converter vaga: {e}, dados: {vaga_dict}")
            continue

    return vagas


# =============================================================================
# Função principal de extração v3
# =============================================================================


async def extrair_vagas_v3(
    texto: str,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
    nome_grupo: str = "",
    nome_contato: str = "",
    data_referencia: Optional[date] = None,
) -> ResultadoExtracaoV2:
    """
    Extrai vagas usando LLM unificado (Pipeline v3).

    Esta função substitui extrair_vagas_v2 quando PIPELINE_V3_ENABLED=true.

    Args:
        texto: Texto da mensagem
        mensagem_id: ID da mensagem
        grupo_id: ID do grupo
        nome_grupo: Nome do grupo
        nome_contato: Nome do remetente
        data_referencia: Data de referência

    Returns:
        ResultadoExtracaoV2 compatível com o pipeline existente
    """
    import time as time_module

    inicio = time_module.time()

    # Validação inicial
    if not texto or not texto.strip():
        return ResultadoExtracaoV2(erro="mensagem_vazia", tempo_processamento_ms=0)

    # Extrair via LLM
    resultado_llm = await extrair_com_llm(
        texto=texto,
        nome_grupo=nome_grupo,
        nome_contato=nome_contato,
        data_referencia=data_referencia,
    )

    # Se não é vaga, retornar erro
    if not resultado_llm.eh_vaga:
        return ResultadoExtracaoV2(
            erro=resultado_llm.motivo_descarte or "nao_eh_vaga",
            tempo_processamento_ms=int((time_module.time() - inicio) * 1000),
            tokens_usados=resultado_llm.tokens_usados,
        )

    # Se teve erro no LLM
    if resultado_llm.erro:
        return ResultadoExtracaoV2(
            erro=f"erro_llm: {resultado_llm.erro}",
            tempo_processamento_ms=int((time_module.time() - inicio) * 1000),
            tokens_usados=resultado_llm.tokens_usados,
        )

    # Converter para VagaAtomica
    vagas = converter_para_vagas_atomicas(resultado_llm, mensagem_id=mensagem_id, grupo_id=grupo_id)

    if not vagas:
        return ResultadoExtracaoV2(
            erro="sem_vagas_validas",
            tempo_processamento_ms=int((time_module.time() - inicio) * 1000),
            tokens_usados=resultado_llm.tokens_usados,
        )

    # Construir resultado compatível com v2
    tempo_ms = int((time_module.time() - inicio) * 1000)

    # Extrair hospitais e especialidades únicos para metadados
    hospitais = []
    especialidades = []
    hospitais_vistos = set()
    especialidades_vistas = set()

    for vaga in vagas:
        if vaga.hospital_raw and vaga.hospital_raw not in hospitais_vistos:
            hospitais_vistos.add(vaga.hospital_raw)
            hospitais.append(
                HospitalExtraido(nome=vaga.hospital_raw, confianca=resultado_llm.confianca)
            )

        if vaga.especialidade_raw and vaga.especialidade_raw not in especialidades_vistas:
            especialidades_vistas.add(vaga.especialidade_raw)
            especialidades.append(
                EspecialidadeExtraida(
                    nome=vaga.especialidade_raw, confianca=resultado_llm.confianca
                )
            )

    return ResultadoExtracaoV2(
        vagas=vagas,
        hospitais=hospitais,
        especialidades=especialidades,
        total_vagas=len(vagas),
        tempo_processamento_ms=tempo_ms,
        tokens_usados=resultado_llm.tokens_usados,
        warnings=["extrator_v3_llm"]
        if not resultado_llm.do_cache
        else ["extrator_v3_llm", "do_cache"],
    )
