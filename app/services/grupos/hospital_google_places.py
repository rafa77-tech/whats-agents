"""
Busca de hospitais via Google Places Text Search (New).

Sprint 61 - Épico 2: Complemento ao CNES para hospitais não encontrados.
"""

from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.services.http_client import get_http_client

logger = get_logger(__name__)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.rating",
        "places.types",
        "places.addressComponents",
    ]
)

# Centroide de SP como location bias default
SP_CENTER = {"latitude": -23.55, "longitude": -46.63}
SP_RADIUS = 150000.0  # 150km


@dataclass
class InfoGooglePlaces:
    """Dados de hospital do Google Places."""

    place_id: str
    nome: str
    endereco_formatado: str
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    telefone: Optional[str] = None
    rating: Optional[float] = None
    confianca: float = 0.0


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
async def buscar_hospital_google_places(
    nome: str,
    regiao_hint: str = "",
) -> Optional[InfoGooglePlaces]:
    """
    Busca hospital no Google Places Text Search (New).

    Retorna None se:
    - API key não configurada
    - Nenhum resultado encontrado
    - Resultado não é tipo hospital/saúde
    """
    if not settings.GOOGLE_PLACES_API_KEY:
        return None

    query = f"{nome} hospital"
    if regiao_hint:
        query += f" {regiao_hint}"

    body = {
        "textQuery": query,
        "includedType": "hospital",
        "locationBias": {
            "circle": {
                "center": SP_CENTER,
                "radius": SP_RADIUS,
            }
        },
        "maxResultCount": 1,
        "languageCode": "pt-BR",
    }

    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
        "Content-Type": "application/json",
    }

    try:
        client = await get_http_client()
        resp = await client.post(GOOGLE_PLACES_URL, json=body, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

        places = data.get("places", [])
        if not places:
            return None

        place = places[0]
        # Extrair cidade/estado/cep de addressComponents
        cidade, estado, cep = _extrair_endereco(place.get("addressComponents", []))

        location = place.get("location", {})

        # Calcular confiança baseado nos tipos
        types = place.get("types", [])
        health_types = {"hospital", "health", "doctor", "physiotherapist"}
        eh_saude = bool(set(types) & health_types)
        confianca = 0.85 if eh_saude else 0.5

        return InfoGooglePlaces(
            place_id=place.get("id", ""),
            nome=place.get("displayName", {}).get("text", nome),
            endereco_formatado=place.get("formattedAddress", ""),
            cidade=cidade,
            estado=estado,
            cep=cep,
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            telefone=place.get("nationalPhoneNumber"),
            rating=place.get("rating"),
            confianca=confianca,
        )

    except httpx.HTTPStatusError as e:
        logger.warning(f"Erro HTTP Google Places: {e.response.status_code}")
        raise
    except Exception as e:
        logger.warning(f"Erro ao buscar Google Places: {e}", extra={"nome": nome})
        return None


def _extrair_endereco(components: list) -> tuple:
    """Extrai cidade, estado (sigla), CEP dos addressComponents."""
    cidade = None
    estado = None
    cep = None

    for comp in components:
        types = comp.get("types", [])
        text = comp.get("longText", "")
        short = comp.get("shortText", "")

        if "administrative_area_level_2" in types:
            cidade = text
        elif "administrative_area_level_1" in types:
            estado = short  # Sigla: "SP", "RJ"
        elif "postal_code" in types:
            cep = text

    return cidade, estado, cep
