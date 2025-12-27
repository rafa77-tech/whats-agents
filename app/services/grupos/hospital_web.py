"""
Criação automática de hospitais via busca web.

Sprint 14 - E07 - Criação de Hospital via Web
"""

import json
import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.normalizador import normalizar_para_busca

logger = get_logger(__name__)


# =============================================================================
# S07.1 - Busca Web de Hospital
# =============================================================================

@dataclass
class InfoHospitalWeb:
    """Informações do hospital encontradas na web."""
    nome_oficial: str
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    confianca: float = 0.0
    fonte: Optional[str] = None


PROMPT_BUSCA_HOSPITAL = """
Você é um assistente que busca informações sobre hospitais brasileiros.

Dado o nome (possivelmente abreviado ou informal): "{nome_hospital}"
Região provável: {regiao}

Retorne as informações que você conhece sobre este hospital em JSON:

{{
  "encontrado": true/false,
  "nome_oficial": "Nome completo oficial do hospital",
  "logradouro": "Rua/Avenida sem número",
  "numero": "Número",
  "bairro": "Bairro",
  "cidade": "Cidade",
  "estado": "Sigla do estado (SP, RJ, MG, etc)",
  "cep": "CEP no formato 00000-000",
  "confianca": 0.0-1.0 (sua confiança nos dados),
  "fonte": "De onde você conhece essas informações"
}}

Regras:
- Se não reconhecer o hospital, retorne {{"encontrado": false}}
- Apenas retorne dados que você tem certeza
- Campos que não souber, deixe como null
- A confiança deve refletir sua certeza:
  - 0.9+: Hospital muito conhecido, dados oficiais
  - 0.7-0.9: Hospital conhecido, dados prováveis
  - 0.5-0.7: Hospital pouco conhecido, dados inferidos
  - <0.5: Dados muito incertos

Retorne APENAS o JSON, sem explicações.
"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True
)
async def buscar_hospital_web(
    nome_hospital: str,
    regiao_hint: str = ""
) -> Optional[InfoHospitalWeb]:
    """
    Busca informações do hospital usando LLM.

    Args:
        nome_hospital: Nome extraído da mensagem
        regiao_hint: Dica de região (do grupo)

    Returns:
        InfoHospitalWeb ou None
    """
    if not nome_hospital:
        return None

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    prompt = PROMPT_BUSCA_HOSPITAL.format(
        nome_hospital=nome_hospital,
        regiao=regiao_hint or "Brasil"
    )

    try:
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        texto = response.content[0].text.strip()

        # Extrair JSON
        if not texto.startswith("{"):
            match = re.search(r'\{[\s\S]+\}', texto)
            if match:
                texto = match.group()
            else:
                return None

        dados = json.loads(texto)

        if not dados.get("encontrado", False):
            logger.debug(f"Hospital não encontrado na web: {nome_hospital}")
            return None

        return InfoHospitalWeb(
            nome_oficial=dados.get("nome_oficial", nome_hospital),
            logradouro=dados.get("logradouro"),
            numero=dados.get("numero"),
            bairro=dados.get("bairro"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            cep=dados.get("cep"),
            confianca=dados.get("confianca", 0.5),
            fonte=dados.get("fonte")
        )

    except json.JSONDecodeError as e:
        logger.warning(f"Erro ao parsear resposta de busca web: {e}")
        return None
    except anthropic.APIError as e:
        logger.error(f"Erro API Anthropic na busca web: {e}")
        raise
    except Exception as e:
        logger.error(f"Erro inesperado na busca web: {e}")
        return None


# =============================================================================
# S07.2 - Criar Hospital no Banco
# =============================================================================

async def criar_hospital(
    info: InfoHospitalWeb,
    alias_original: str
) -> UUID:
    """
    Cria hospital no banco de dados com dados da web.

    Args:
        info: Informações da web
        alias_original: Nome original da mensagem (para criar alias)

    Returns:
        UUID do hospital criado
    """
    dados_hospital = {
        "nome": info.nome_oficial,
        "logradouro": info.logradouro,
        "numero": info.numero,
        "bairro": info.bairro,
        "cidade": info.cidade or "Não informada",  # Evitar NULL
        "estado": info.estado or "SP",  # Default SP
        "cep": info.cep,
        "criado_automaticamente": True,
        "precisa_revisao": True,  # Sempre revisar criados automaticamente
    }

    # Remover campos None (exceto cidade/estado que têm defaults)
    dados_hospital = {k: v for k, v in dados_hospital.items() if v is not None}

    result = supabase.table("hospitais").insert(dados_hospital).execute()
    hospital_id = UUID(result.data[0]["id"])

    logger.info(f"Hospital criado via web: {hospital_id} - {info.nome_oficial}")

    # Criar alias com nome original
    alias_norm = normalizar_para_busca(alias_original)

    try:
        supabase.table("hospitais_alias").insert({
            "hospital_id": str(hospital_id),
            "alias": alias_original,
            "alias_normalizado": alias_norm,
            "origem": "sistema_auto",
            "criado_por": "busca_web",
            "confianca": info.confianca,
            "confirmado": False,
        }).execute()
    except Exception as e:
        logger.warning(f"Erro ao criar alias original: {e}")

    # Criar alias com nome oficial também (se diferente)
    if info.nome_oficial.lower() != alias_original.lower():
        nome_norm = normalizar_para_busca(info.nome_oficial)
        try:
            supabase.table("hospitais_alias").insert({
                "hospital_id": str(hospital_id),
                "alias": info.nome_oficial,
                "alias_normalizado": nome_norm,
                "origem": "sistema_auto",
                "criado_por": "busca_web",
                "confianca": 1.0,
                "confirmado": False,
            }).execute()
        except Exception as e:
            logger.warning(f"Erro ao criar alias oficial: {e}")

    return hospital_id


# =============================================================================
# S07.3 - Fallback sem Dados Web
# =============================================================================

# Mapa de regiões conhecidas
REGIOES_CONHECIDAS = {
    "abc": ("Santo André", "SP"),
    "abcd": ("Santo André", "SP"),
    "grande abc": ("Santo André", "SP"),
    "sao bernardo": ("São Bernardo do Campo", "SP"),
    "santo andre": ("Santo André", "SP"),
    "sao caetano": ("São Caetano do Sul", "SP"),
    "maua": ("Mauá", "SP"),
    "diadema": ("Diadema", "SP"),
    "sp capital": ("São Paulo", "SP"),
    "sp": ("São Paulo", "SP"),
    "sao paulo": ("São Paulo", "SP"),
    "campinas": ("Campinas", "SP"),
    "santos": ("Santos", "SP"),
    "baixada santista": ("Santos", "SP"),
    "guarulhos": ("Guarulhos", "SP"),
    "osasco": ("Osasco", "SP"),
    "rj": ("Rio de Janeiro", "RJ"),
    "rio": ("Rio de Janeiro", "RJ"),
    "rio de janeiro": ("Rio de Janeiro", "RJ"),
    "niteroi": ("Niterói", "RJ"),
    "bh": ("Belo Horizonte", "MG"),
    "belo horizonte": ("Belo Horizonte", "MG"),
    "curitiba": ("Curitiba", "PR"),
    "porto alegre": ("Porto Alegre", "RS"),
    "brasilia": ("Brasília", "DF"),
    "salvador": ("Salvador", "BA"),
    "recife": ("Recife", "PE"),
    "fortaleza": ("Fortaleza", "CE"),
}


def inferir_cidade_regiao(regiao_grupo: str) -> tuple:
    """
    Tenta inferir cidade/estado da região do grupo.

    Returns:
        Tuple (cidade, estado) ou (None, None)
    """
    if not regiao_grupo:
        return (None, None)

    regiao_norm = normalizar_para_busca(regiao_grupo)

    for key, (cidade, estado) in REGIOES_CONHECIDAS.items():
        if key in regiao_norm:
            return (cidade, estado)

    return (None, None)


async def criar_hospital_minimo(
    nome: str,
    regiao_grupo: str = ""
) -> UUID:
    """
    Cria hospital com dados mínimos.

    Usado quando busca web falha.

    Args:
        nome: Nome do hospital
        regiao_grupo: Região do grupo (para inferir cidade)

    Returns:
        UUID do hospital criado
    """
    cidade, estado = inferir_cidade_regiao(regiao_grupo)

    dados = {
        "nome": nome,
        "cidade": cidade or "Não informada",  # Evitar NULL
        "estado": estado or "SP",  # Default SP
        "criado_automaticamente": True,
        "precisa_revisao": True,  # Sempre precisa revisão
    }

    result = supabase.table("hospitais").insert(dados).execute()
    hospital_id = UUID(result.data[0]["id"])

    # Criar alias
    alias_norm = normalizar_para_busca(nome)
    try:
        supabase.table("hospitais_alias").insert({
            "hospital_id": str(hospital_id),
            "alias": nome,
            "alias_normalizado": alias_norm,
            "origem": "sistema_auto",
            "criado_por": "fallback",
            "confianca": 0.3,  # Baixa confiança
            "confirmado": False,
        }).execute()
    except Exception as e:
        logger.warning(f"Erro ao criar alias fallback: {e}")

    logger.info(f"Hospital mínimo criado: {hospital_id} - {nome}")

    return hospital_id


# =============================================================================
# S07.4 - Função Principal com Criação Automática
# =============================================================================

@dataclass
class ResultadoHospitalAuto:
    """Resultado da normalização com criação automática."""
    hospital_id: UUID
    nome: str
    score: float
    foi_criado: bool
    fonte: str  # "alias_exato", "similaridade", "web", "fallback"


async def normalizar_ou_criar_hospital(
    texto: str,
    regiao_grupo: str = ""
) -> Optional[ResultadoHospitalAuto]:
    """
    Normaliza hospital, criando automaticamente se necessário.

    Args:
        texto: Nome do hospital extraído
        regiao_grupo: Região do grupo (para contexto)

    Returns:
        ResultadoHospitalAuto ou None
    """
    from app.services.grupos.normalizador import (
        buscar_hospital_por_alias,
        buscar_hospital_por_similaridade,
    )

    if not texto:
        return None

    # 1. Buscar alias exato
    match = await buscar_hospital_por_alias(texto)
    if match:
        return ResultadoHospitalAuto(
            hospital_id=match.entidade_id,
            nome=match.nome,
            score=match.score,
            foi_criado=False,
            fonte="alias_exato"
        )

    # 2. Buscar por similaridade (threshold alto: 70%)
    match = await buscar_hospital_por_similaridade(texto, threshold=0.7)
    if match:
        return ResultadoHospitalAuto(
            hospital_id=match.entidade_id,
            nome=match.nome,
            score=match.score,
            foi_criado=False,
            fonte="similaridade"
        )

    # 3. Não encontrou - buscar na web
    logger.info(f"Hospital não encontrado, buscando na web: {texto}")

    info = await buscar_hospital_web(texto, regiao_grupo)

    if info and info.confianca >= 0.6:
        hospital_id = await criar_hospital(info, texto)
        return ResultadoHospitalAuto(
            hospital_id=hospital_id,
            nome=info.nome_oficial,
            score=info.confianca,
            foi_criado=True,
            fonte="web"
        )

    # 4. Fallback - criar com dados mínimos
    hospital_id = await criar_hospital_minimo(texto, regiao_grupo)
    return ResultadoHospitalAuto(
        hospital_id=hospital_id,
        nome=texto,
        score=0.3,
        foi_criado=True,
        fonte="fallback"
    )


# =============================================================================
# Funções de Manutenção
# =============================================================================

async def listar_hospitais_para_revisao(limite: int = 50) -> list:
    """
    Lista hospitais que precisam revisão.
    """
    result = supabase.table("hospitais") \
        .select("id, nome, cidade, estado, criado_automaticamente, created_at") \
        .eq("precisa_revisao", True) \
        .order("created_at", desc=True) \
        .limit(limite) \
        .execute()

    return result.data


async def marcar_hospital_revisado(
    hospital_id: UUID,
    revisado_por: str
) -> bool:
    """
    Marca hospital como revisado.
    """
    from datetime import datetime, UTC

    try:
        supabase.table("hospitais") \
            .update({
                "precisa_revisao": False,
                "revisado_em": datetime.now(UTC).isoformat(),
                "revisado_por": revisado_por,
            }) \
            .eq("id", str(hospital_id)) \
            .execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar hospital revisado: {e}")
        return False
