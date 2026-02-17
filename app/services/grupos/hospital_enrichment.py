"""
Enriquecimento batch de hospitais com CNES + Google Places.

Sprint 61 - Épico 4: Job one-shot para enriquecer hospitais existentes.
"""

import asyncio
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.hospital_cnes import buscar_hospital_cnes, InfoCNES
from app.services.grupos.hospital_google_places import buscar_hospital_google_places

logger = get_logger(__name__)


@dataclass
class ResultadoEnriquecimento:
    """Resultado do enriquecimento batch."""

    total: int = 0
    enriquecidos_cnes: int = 0
    enriquecidos_google: int = 0
    ja_enriquecidos: int = 0
    sem_match: int = 0
    erros: int = 0
    erros_detalhe: list = field(default_factory=list)


async def enriquecer_hospitais_batch(
    limite: int = 1000,
    apenas_sem_enriquecimento: bool = True,
) -> ResultadoEnriquecimento:
    """
    Enriquece hospitais existentes com CNES + Google Places.

    Para cada hospital:
    1. Buscar no CNES por nome + cidade
    2. Se não encontrar, buscar no Google Places
    3. Atualizar dados (endereço, coordenadas, telefone, cnes_codigo)
    """
    resultado = ResultadoEnriquecimento()

    # Buscar hospitais para enriquecer
    query = supabase.table("hospitais").select("id, nome, cidade, estado")
    if apenas_sem_enriquecimento:
        query = query.is_("enriched_at", "null")
    query = query.order("created_at").limit(limite)

    resp = query.execute()
    hospitais = resp.data or []
    resultado.total = len(hospitais)

    logger.info(f"Iniciando enriquecimento de {len(hospitais)} hospitais")

    for i, h in enumerate(hospitais):
        try:
            hospital_id = h["id"]
            nome = h["nome"]
            cidade = h["cidade"]
            estado = h["estado"] or "SP"

            # 1. Tentar CNES
            info_cnes = await buscar_hospital_cnes(nome, cidade, estado)
            if info_cnes and info_cnes.score >= 0.4:
                await _aplicar_enriquecimento_cnes(hospital_id, info_cnes)
                resultado.enriquecidos_cnes += 1
                logger.info(
                    f"[{i + 1}/{len(hospitais)}] CNES match: {nome} -> "
                    f"{info_cnes.nome_oficial} (score={info_cnes.score:.2f})"
                )
                continue

            # 2. Tentar Google Places
            info_google = await buscar_hospital_google_places(nome, cidade)
            if info_google and info_google.confianca >= 0.6:
                await _aplicar_enriquecimento_google(hospital_id, info_google)
                resultado.enriquecidos_google += 1
                logger.info(
                    f"[{i + 1}/{len(hospitais)}] Google match: {nome} -> {info_google.nome}"
                )
                await asyncio.sleep(0.5)  # Rate limit Google
                continue

            resultado.sem_match += 1
            logger.debug(f"[{i + 1}/{len(hospitais)}] Sem match: {nome}")

        except Exception as e:
            resultado.erros += 1
            resultado.erros_detalhe.append(f"{h['nome']}: {e}")
            logger.warning(f"Erro ao enriquecer {h['nome']}: {e}")

    logger.info(
        f"Enriquecimento completo: CNES={resultado.enriquecidos_cnes}, "
        f"Google={resultado.enriquecidos_google}, sem_match={resultado.sem_match}, "
        f"erros={resultado.erros}"
    )

    return resultado


async def _aplicar_enriquecimento_cnes(hospital_id: str, info: InfoCNES) -> None:
    """Aplica dados CNES no hospital."""
    from datetime import datetime, UTC

    updates: dict = {
        "cnes_codigo": info.cnes_codigo,
        "enriched_at": datetime.now(UTC).isoformat(),
        "enriched_by": "cnes_batch",
    }
    if info.logradouro:
        updates["logradouro"] = info.logradouro
    if info.numero:
        updates["numero"] = info.numero
    if info.bairro:
        updates["bairro"] = info.bairro
    if info.cep:
        updates["cep"] = info.cep
    if info.telefone:
        updates["telefone"] = info.telefone
    if info.latitude is not None:
        updates["latitude"] = info.latitude
    if info.longitude is not None:
        updates["longitude"] = info.longitude

    supabase.table("hospitais").update(updates).eq("id", hospital_id).execute()


async def _aplicar_enriquecimento_google(hospital_id: str, info) -> None:
    """Aplica dados Google Places no hospital."""
    from datetime import datetime, UTC

    updates: dict = {
        "google_place_id": info.place_id,
        "enriched_at": datetime.now(UTC).isoformat(),
        "enriched_by": "google_batch",
    }
    if info.cidade:
        updates["cidade"] = info.cidade
    if info.estado:
        updates["estado"] = info.estado
    if info.cep:
        updates["cep"] = info.cep
    if info.telefone:
        updates["telefone"] = info.telefone
    if info.latitude is not None:
        updates["latitude"] = info.latitude
    if info.longitude is not None:
        updates["longitude"] = info.longitude

    supabase.table("hospitais").update(updates).eq("id", hospital_id).execute()
