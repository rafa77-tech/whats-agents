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


def hospital_tem_endereco_completo(info: InfoHospitalWeb) -> bool:
    """Verifica se o hospital tem endereço completo com lat/long."""
    return (
        info.latitude is not None
        and info.longitude is not None
        and bool(info.cidade)
        and bool(info.estado)
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
            model="claude-haiku-4-5-20251001",
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


async def _checar_duplicata_por_chave(
    hospital_id: UUID, cnes_codigo: Optional[str], google_place_id: Optional[str]
) -> Optional[UUID]:
    """Checa se outro hospital já possui o mesmo cnes_codigo ou google_place_id.

    Returns:
        UUID do hospital destino (existente) se duplicata encontrada, None caso contrário.
    """
    if cnes_codigo:
        existing = (
            supabase.table("hospitais")
            .select("id")
            .eq("cnes_codigo", cnes_codigo)
            .neq("id", str(hospital_id))
            .limit(1)
            .execute()
        )
        if existing.data:
            return UUID(existing.data[0]["id"])

    if google_place_id:
        existing = (
            supabase.table("hospitais")
            .select("id")
            .eq("google_place_id", google_place_id)
            .neq("id", str(hospital_id))
            .limit(1)
            .execute()
        )
        if existing.data:
            return UUID(existing.data[0]["id"])

    return None


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

        # Dedup: checar se outro hospital já tem o mesmo cnes_codigo ou google_place_id
        try:
            merge_destino = await _checar_duplicata_por_chave(
                hospital_id, info.cnes_codigo, info.google_place_id
            )
            if merge_destino:
                await mergear_hospitais(hospital_id, merge_destino)
                logger.info(f"Merge em criar_hospital: {hospital_id} → {merge_destino}")
                return merge_destino
        except Exception as e:
            logger.warning(f"Erro no dedup de criar_hospital: {e}")

        # Sprint 61: Persistir campos de enriquecimento (CNES, Google Places, LLM)
        has_enrichment = any(
            [
                info.cnes_codigo,
                info.google_place_id,
                info.telefone,
                info.latitude is not None,
                info.longitude is not None,
                info.logradouro,
                info.bairro,
                info.cep,
            ]
        )
        if has_enrichment:
            from datetime import datetime, UTC

            updates: dict = {}
            if info.confianca >= 0.8 and info.nome_oficial:
                updates["nome"] = info.nome_oficial
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
            if info.logradouro:
                updates["logradouro"] = info.logradouro
            if info.bairro:
                updates["bairro"] = info.bairro
            if info.cep:
                updates["cep"] = info.cep
            if info.latitude is not None and info.longitude is not None:
                updates["endereco_verificado"] = True
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


async def _buscar_existente(texto: str) -> Optional[ResultadoHospitalAuto]:
    """Busca hospital existente por alias, similaridade ou safety net.

    Tenta, em ordem:
    1. Alias exato
    2. Similaridade (threshold 70%)
    3. Safety net: remove sufixos (" - ", " (", " / ") e re-tenta

    Returns:
        ResultadoHospitalAuto se encontrado, None caso contrário
    """
    from app.services.grupos.normalizador import (
        buscar_hospital_por_alias,
        buscar_hospital_por_similaridade,
    )

    # 1. Alias exato
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

    # 2. Similaridade (threshold alto: 70%)
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

    # 3. Safety net: tentar sem sufixo (setor/ala embutido)
    for separador in [" - ", " (", " / "]:
        if separador in texto:
            texto_base = texto.split(separador)[0].strip()
            if texto_base and len(texto_base) >= 4:
                match_base = await buscar_hospital_por_alias(texto_base)
                if not match_base:
                    match_base = await buscar_hospital_por_similaridade(texto_base, threshold=0.7)
                if match_base:
                    logger.info(
                        f"Hospital match via safety net (sem sufixo '{separador}'): "
                        f"'{texto}' → '{match_base.nome}'"
                    )
                    await _emitir_evento_hospital(
                        EventType.HOSPITAL_REUSED,
                        hospital_id=str(match_base.entidade_id),
                        props={
                            "fonte": "safety_net_sem_sufixo",
                            "score": match_base.score,
                            "texto_original": texto,
                            "texto_base": texto_base,
                            "separador": separador,
                        },
                    )
                    return ResultadoHospitalAuto(
                        hospital_id=match_base.entidade_id,
                        nome=match_base.nome,
                        score=match_base.score,
                        foi_criado=False,
                        fonte="safety_net_sem_sufixo",
                    )

    return None


async def _criar_e_rastrear_hospital(
    info_web: InfoHospitalWeb, alias_original: str, fonte: str, evento_props: Optional[dict] = None
) -> ResultadoHospitalAuto:
    """Cria hospital, marca para revisão se necessário e emite evento.

    Padrão compartilhado entre CNES, Google Places e LLM web.

    Args:
        info_web: Dados do hospital
        alias_original: Nome original da mensagem
        fonte: Identificador da fonte ("cnes", "google_places", "web")
        evento_props: Props adicionais para o evento

    Returns:
        ResultadoHospitalAuto com hospital criado
    """
    hospital_id = await criar_hospital(info_web, alias_original)

    if not hospital_tem_endereco_completo(info_web):
        try:
            supabase.table("hospitais").update({"precisa_revisao": True}).eq(
                "id", str(hospital_id)
            ).execute()
        except Exception:
            pass

    props = {
        "fonte": fonte,
        "nome": info_web.nome_oficial,
        "confianca": info_web.confianca,
    }
    if evento_props:
        props.update(evento_props)

    await _emitir_evento_hospital(
        EventType.HOSPITAL_CREATED,
        hospital_id=str(hospital_id),
        props=props,
    )

    return ResultadoHospitalAuto(
        hospital_id=hospital_id,
        nome=info_web.nome_oficial,
        score=info_web.confianca,
        foi_criado=True,
        fonte=fonte,
    )


async def _buscar_e_criar_via_cnes(
    texto: str, cidade_hint: Optional[str], estado_hint: Optional[str]
) -> Optional[ResultadoHospitalAuto]:
    """Busca hospital no CNES e cria se encontrado."""
    try:
        from app.services.grupos.hospital_cnes import buscar_hospital_cnes

        info_cnes = await buscar_hospital_cnes(texto, cidade_hint, estado_hint or "SP")
        if info_cnes and info_cnes.score >= 0.6:
            info_web = cnes_to_info_web(info_cnes)
            return await _criar_e_rastrear_hospital(
                info_web, texto, "cnes", {"cnes": info_cnes.cnes_codigo}
            )
    except Exception as e:
        logger.warning(f"Erro no lookup CNES, continuando: {e}")

    return None


async def _buscar_e_criar_via_google(
    texto: str, regiao_grupo: str
) -> Optional[ResultadoHospitalAuto]:
    """Busca hospital no Google Places e cria se encontrado."""
    try:
        from app.services.grupos.hospital_google_places import (
            buscar_hospital_google_places,
        )

        info_google = await buscar_hospital_google_places(texto, regiao_grupo)
        if info_google and info_google.confianca >= 0.7:
            info_web = google_to_info_web(info_google)
            return await _criar_e_rastrear_hospital(
                info_web, texto, "google_places", {"place_id": info_google.place_id}
            )
    except Exception as e:
        logger.warning(f"Erro no lookup Google Places, continuando: {e}")

    return None


async def _buscar_e_criar_via_web(texto: str, regiao_grupo: str) -> Optional[ResultadoHospitalAuto]:
    """Busca hospital via LLM (fallback) e cria se encontrado."""
    logger.info(f"Hospital não encontrado em CNES/Google, buscando via LLM: {texto}")

    info = await buscar_hospital_web(texto, regiao_grupo)
    if info and info.confianca >= 0.6:
        return await _criar_e_rastrear_hospital(info, texto, "web")

    return None


async def normalizar_ou_criar_hospital(
    texto: str, regiao_grupo: str = ""
) -> Optional[ResultadoHospitalAuto]:
    """
    Normaliza hospital, criando automaticamente se necessário.

    Estratégias em cascata:
    1. Alias exato / similaridade / safety net
    2. Validação de nome
    3. CNES (grátis, local)
    4. Google Places (pago, dados frescos)
    5. LLM web (fallback)

    Args:
        texto: Nome do hospital extraído
        regiao_grupo: Região do grupo (para contexto)

    Returns:
        ResultadoHospitalAuto ou None
    """
    if not texto:
        return None

    # 1. Buscar hospital existente
    resultado = await _buscar_existente(texto)
    if resultado:
        return resultado

    # 2. Gate de validação ANTES de criar (Sprint 60)
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

    # 4. CNES → Google Places → LLM Web (cascata)
    resultado = await _buscar_e_criar_via_cnes(texto, cidade_hint, estado_hint)
    if resultado:
        return resultado

    resultado = await _buscar_e_criar_via_google(texto, regiao_grupo)
    if resultado:
        return resultado

    resultado = await _buscar_e_criar_via_web(texto, regiao_grupo)
    if resultado:
        return resultado

    # 5. Sem match — enviar para revisão humana
    logger.warning(
        "Hospital não encontrado em nenhuma fonte, requer revisão humana",
        extra={"nome": texto, "regiao": regiao_grupo},
    )
    await _emitir_evento_hospital(
        EventType.HOSPITAL_REJECTED,
        props={"nome": texto, "motivo": "sem_endereco_verificado", "regiao": regiao_grupo},
    )
    return None


# =============================================================================
# Funções de Manutenção
# =============================================================================


async def mergear_hospitais(fonte_id: UUID, destino_id: UUID) -> dict:
    """Mergeia hospital fonte no destino. Move vagas, aliases, grupos."""
    result = supabase.rpc(
        "mergear_hospitais",
        {
            "p_fonte_id": str(fonte_id),
            "p_destino_id": str(destino_id),
        },
    ).execute()
    if not result.data:
        raise Exception("RPC mergear_hospitais retornou vazio")
    logger.info(
        "Hospital mergeado",
        extra={
            "fonte_id": str(fonte_id),
            "destino_id": str(destino_id),
            "resultado": result.data,
        },
    )
    return result.data


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
