"""
Criação automática de hospitais via busca web.

Sprint 14 - E07 - Criação de Hospital via Web
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.grupos.hospital_cnes import InfoCNES
    from app.services.grupos.hospital_google_places import InfoGooglePlaces
from uuid import UUID

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.normalizador import normalizar_para_busca
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event

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
    # Sprint 61 — Enriquecimento CNES + Google Places
    cnes_codigo: Optional[str] = None
    google_place_id: Optional[str] = None
    telefone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def cnes_to_info_web(info: "InfoCNES") -> InfoHospitalWeb:
    """Converte dados CNES para InfoHospitalWeb."""
    return InfoHospitalWeb(
        nome_oficial=info.nome_oficial,
        logradouro=info.logradouro,
        numero=info.numero,
        bairro=info.bairro,
        cidade=info.cidade,
        estado=info.estado,
        cep=info.cep,
        confianca=min(info.score + 0.2, 1.0),
        fonte="cnes",
        cnes_codigo=info.cnes_codigo,
        telefone=info.telefone,
        latitude=info.latitude,
        longitude=info.longitude,
    )


def google_to_info_web(info: "InfoGooglePlaces") -> InfoHospitalWeb:
    """Converte dados Google Places para InfoHospitalWeb."""
    return InfoHospitalWeb(
        nome_oficial=info.nome,
        cidade=info.cidade,
        estado=info.estado,
        cep=info.cep,
        confianca=info.confianca,
        fonte="google_places",
        google_place_id=info.place_id,
        telefone=info.telefone,
        latitude=info.latitude,
        longitude=info.longitude,
    )


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


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
async def buscar_hospital_web(
    nome_hospital: str, regiao_hint: str = ""
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
        nome_hospital=nome_hospital, regiao=regiao_hint or "Brasil"
    )

    try:
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        texto = response.content[0].text.strip()

        # Extrair JSON
        if not texto.startswith("{"):
            match = re.search(r"\{[\s\S]+\}", texto)
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
            fonte=dados.get("fonte"),
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


async def criar_hospital(info: InfoHospitalWeb, alias_original: str) -> UUID:
    """
    Cria hospital no banco de dados com dados da web.

    Usa RPC atômica para evitar race conditions (Sprint 60 - Épico 2).

    Args:
        info: Informações da web
        alias_original: Nome original da mensagem (para criar alias)

    Returns:
        UUID do hospital criado ou reutilizado
    """
    alias_norm = normalizar_para_busca(alias_original)

    result = supabase.rpc(
        "buscar_ou_criar_hospital",
        {
            "p_nome": info.nome_oficial,
            "p_alias_normalizado": alias_norm,
            "p_cidade": info.cidade or "Não informada",
            "p_estado": info.estado or "SP",
            "p_confianca": info.confianca,
            "p_criado_por": "busca_web",
        },
    ).execute()

    if not result.data:
        raise Exception("RPC buscar_ou_criar_hospital retornou vazio")

    row = result.data[0]
    hospital_id = UUID(row["out_hospital_id"])

    if row["out_foi_criado"]:
        logger.info(
            "Hospital criado via web (RPC)",
            extra={"hospital_id": str(hospital_id), "nome": info.nome_oficial},
        )

        # Sprint 61: Persistir campos de enriquecimento (CNES, Google Places)
        if info.cnes_codigo or info.google_place_id or info.telefone:
            from datetime import datetime, UTC

            updates: dict = {}
            if info.cnes_codigo:
                updates["cnes_codigo"] = info.cnes_codigo
            if info.google_place_id:
                updates["google_place_id"] = info.google_place_id
            if info.telefone:
                updates["telefone"] = info.telefone
            if info.latitude is not None:
                updates["latitude"] = info.latitude
            if info.longitude is not None:
                updates["longitude"] = info.longitude
            if updates:
                updates["enriched_at"] = datetime.now(UTC).isoformat()
                updates["enriched_by"] = info.fonte or "pipeline"
                try:
                    supabase.table("hospitais").update(updates).eq("id", str(hospital_id)).execute()
                except Exception as e:
                    logger.warning(f"Erro ao salvar enriquecimento: {e}")

        # Criar alias adicional com nome oficial (se diferente do original)
        if info.nome_oficial.lower() != alias_original.lower():
            nome_norm = normalizar_para_busca(info.nome_oficial)
            try:
                supabase.table("hospitais_alias").insert(
                    {
                        "hospital_id": str(hospital_id),
                        "alias": info.nome_oficial,
                        "alias_normalizado": nome_norm,
                        "origem": "sistema_auto",
                        "criado_por": "busca_web",
                        "confianca": 1.0,
                        "confirmado": False,
                    }
                ).execute()
            except Exception as e:
                logger.warning(f"Erro ao criar alias oficial: {e}")
    else:
        logger.info(
            "Hospital reutilizado via RPC",
            extra={
                "hospital_id": str(hospital_id),
                "nome": row["out_nome"],
                "alias_buscado": alias_original,
            },
        )

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


async def criar_hospital_minimo(nome: str, regiao_grupo: str = "") -> UUID:
    """
    Cria hospital com dados mínimos.

    Usa RPC atômica para evitar race conditions (Sprint 60 - Épico 2).
    Usado quando busca web falha.

    Args:
        nome: Nome do hospital
        regiao_grupo: Região do grupo (para inferir cidade)

    Returns:
        UUID do hospital criado ou reutilizado
    """
    cidade, estado = inferir_cidade_regiao(regiao_grupo)
    alias_norm = normalizar_para_busca(nome)

    result = supabase.rpc(
        "buscar_ou_criar_hospital",
        {
            "p_nome": nome,
            "p_alias_normalizado": alias_norm,
            "p_cidade": cidade or "Não informada",
            "p_estado": estado or "SP",
            "p_confianca": 0.3,
            "p_criado_por": "fallback",
        },
    ).execute()

    if not result.data:
        raise Exception("RPC buscar_ou_criar_hospital retornou vazio")

    row = result.data[0]
    hospital_id = UUID(row["out_hospital_id"])

    if row["out_foi_criado"]:
        logger.info(
            "Hospital mínimo criado (RPC)",
            extra={"hospital_id": str(hospital_id), "nome": nome},
        )
    else:
        logger.info(
            "Hospital reutilizado (fallback RPC)",
            extra={"hospital_id": str(hospital_id), "nome": row["out_nome"]},
        )

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
    fonte: str  # "alias_exato", "similaridade", "cnes", "google_places", "web", "fallback"


async def _emitir_evento_hospital(
    event_type: EventType,
    hospital_id: Optional[str] = None,
    props: Optional[dict] = None,
) -> None:
    """Emite evento de qualidade de hospital (fire-and-forget)."""
    try:
        await emit_event(
            BusinessEvent(
                event_type=event_type,
                source=EventSource.SYSTEM,
                hospital_id=hospital_id,
                event_props=props or {},
            )
        )
    except Exception as e:
        logger.warning(f"Erro ao emitir evento hospital: {e}")


async def normalizar_ou_criar_hospital(
    texto: str, regiao_grupo: str = ""
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
        await _emitir_evento_hospital(
            EventType.HOSPITAL_REUSED,
            hospital_id=str(match.entidade_id),
            props={"fonte": "alias_exato", "score": match.score, "texto_original": texto},
        )
        return ResultadoHospitalAuto(
            hospital_id=match.entidade_id,
            nome=match.nome,
            score=match.score,
            foi_criado=False,
            fonte="alias_exato",
        )

    # 2. Buscar por similaridade (threshold alto: 70%)
    match = await buscar_hospital_por_similaridade(texto, threshold=0.7)
    if match:
        await _emitir_evento_hospital(
            EventType.HOSPITAL_REUSED,
            hospital_id=str(match.entidade_id),
            props={"fonte": "similaridade", "score": match.score, "texto_original": texto},
        )
        return ResultadoHospitalAuto(
            hospital_id=match.entidade_id,
            nome=match.nome,
            score=match.score,
            foi_criado=False,
            fonte="similaridade",
        )

    # Gate de validação ANTES de criar (Sprint 60 - Épico 1)
    from app.services.grupos.hospital_validator import validar_nome_hospital

    validacao = validar_nome_hospital(texto)
    if not validacao.valido:
        logger.warning(
            "Hospital rejeitado pelo validador",
            extra={"nome": texto, "motivo": validacao.motivo},
        )
        await _emitir_evento_hospital(
            EventType.HOSPITAL_REJECTED,
            props={"nome": texto, "motivo": validacao.motivo},
        )
        return None

    # 3. Inferir cidade/estado da região do grupo
    cidade_hint, estado_hint = inferir_cidade_regiao(regiao_grupo)

    # 4. Buscar no CNES (grátis, local)
    try:
        from app.services.grupos.hospital_cnes import buscar_hospital_cnes

        info_cnes = await buscar_hospital_cnes(texto, cidade_hint, estado_hint or "SP")
        if info_cnes and info_cnes.score >= 0.6:
            info_web = cnes_to_info_web(info_cnes)
            hospital_id = await criar_hospital(info_web, texto)
            await _emitir_evento_hospital(
                EventType.HOSPITAL_CREATED,
                hospital_id=str(hospital_id),
                props={
                    "fonte": "cnes",
                    "nome": info_web.nome_oficial,
                    "confianca": info_web.confianca,
                    "cnes": info_cnes.cnes_codigo,
                },
            )
            return ResultadoHospitalAuto(
                hospital_id=hospital_id,
                nome=info_web.nome_oficial,
                score=info_web.confianca,
                foi_criado=True,
                fonte="cnes",
            )
    except Exception as e:
        logger.warning(f"Erro no lookup CNES, continuando: {e}")

    # 5. Buscar no Google Places (pago, mas dados frescos)
    try:
        from app.services.grupos.hospital_google_places import (
            buscar_hospital_google_places,
        )

        info_google = await buscar_hospital_google_places(texto, regiao_grupo)
        if info_google and info_google.confianca >= 0.7:
            info_web = google_to_info_web(info_google)
            hospital_id = await criar_hospital(info_web, texto)
            await _emitir_evento_hospital(
                EventType.HOSPITAL_CREATED,
                hospital_id=str(hospital_id),
                props={
                    "fonte": "google_places",
                    "nome": info_web.nome_oficial,
                    "confianca": info_web.confianca,
                    "place_id": info_google.place_id,
                },
            )
            return ResultadoHospitalAuto(
                hospital_id=hospital_id,
                nome=info_web.nome_oficial,
                score=info_web.confianca,
                foi_criado=True,
                fonte="google_places",
            )
    except Exception as e:
        logger.warning(f"Erro no lookup Google Places, continuando: {e}")

    # 6. Buscar na web (LLM - fallback)
    logger.info(f"Hospital não encontrado em CNES/Google, buscando via LLM: {texto}")

    info = await buscar_hospital_web(texto, regiao_grupo)

    if info and info.confianca >= 0.6:
        hospital_id = await criar_hospital(info, texto)
        await _emitir_evento_hospital(
            EventType.HOSPITAL_CREATED,
            hospital_id=str(hospital_id),
            props={"fonte": "web", "nome": info.nome_oficial, "confianca": info.confianca},
        )
        return ResultadoHospitalAuto(
            hospital_id=hospital_id,
            nome=info.nome_oficial,
            score=info.confianca,
            foi_criado=True,
            fonte="web",
        )

    # 7. Fallback - criar com dados mínimos
    hospital_id = await criar_hospital_minimo(texto, regiao_grupo)
    await _emitir_evento_hospital(
        EventType.HOSPITAL_CREATED,
        hospital_id=str(hospital_id),
        props={"fonte": "fallback", "nome": texto, "confianca": 0.3},
    )
    return ResultadoHospitalAuto(
        hospital_id=hospital_id, nome=texto, score=0.3, foi_criado=True, fonte="fallback"
    )


# =============================================================================
# Funções de Manutenção
# =============================================================================


async def listar_hospitais_para_revisao(limite: int = 50) -> list:
    """
    Lista hospitais que precisam revisão.
    """
    result = (
        supabase.table("hospitais")
        .select("id, nome, cidade, estado, criado_automaticamente, created_at")
        .eq("precisa_revisao", True)
        .order("created_at", desc=True)
        .limit(limite)
        .execute()
    )

    return result.data


async def marcar_hospital_revisado(hospital_id: UUID, revisado_por: str) -> bool:
    """
    Marca hospital como revisado.
    """
    from datetime import datetime, UTC

    try:
        supabase.table("hospitais").update(
            {
                "precisa_revisao": False,
                "revisado_em": datetime.now(UTC).isoformat(),
                "revisado_por": revisado_por,
            }
        ).eq("id", str(hospital_id)).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar hospital revisado: {e}")
        return False
