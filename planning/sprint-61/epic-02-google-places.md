# EPICO 2: Google Places API

## Contexto

CNES cobre bem hospitais publicos e grandes privados, mas pode nao ter clinicas pequenas ou estabelecimentos recentes. Google Places API (New) complementa com dados atualizados, incluindo coordenadas, telefone e rating.

**Objetivo:** Criar servico de busca no Google Places Text Search (New) para hospitais brasileiros, com fallback gracioso quando API key nao configurada.

## Escopo

- **Incluido:**
  - Configuracao `GOOGLE_PLACES_API_KEY` em `config.py`
  - Servico `hospital_google_places.py` com busca Text Search
  - Parsing de `addressComponents` para extrair cidade/estado/CEP
  - Feature flag natural (key vazia = skip)

- **Excluido:**
  - Google Places Details (busca por place_id) — futuro
  - Geocoding reverso
  - Caching de resultados Google (futuro)
  - Interface de busca Google no dashboard

---

## Tarefa 2.1: Configuracao — Google Places API Key

### Objetivo

Adicionar configuracao para Google Places API key.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/core/config.py` (1 linha) |

### Implementacao

Adicionar na classe `Settings`, apos as variaveis de Voyage AI:

```python
# Google Places (Sprint 61)
GOOGLE_PLACES_API_KEY: str = ""
```

### Definition of Done

- [ ] Variavel adicionada em `config.py`
- [ ] `.env.example` atualizado com `GOOGLE_PLACES_API_KEY=`

---

## Tarefa 2.2: Servico Google Places — hospital_google_places.py

### Objetivo

Criar servico que busca hospitais no Google Places Text Search (New) e retorna dados estruturados.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `app/services/grupos/hospital_google_places.py` (~120 linhas) |

### Implementacao

```python
"""
Busca de hospitais via Google Places Text Search (New).

Sprint 61 - Epico 2: Complemento ao CNES para hospitais nao encontrados.
"""

import httpx
from dataclasses import dataclass
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.nationalPhoneNumber",
    "places.rating",
    "places.types",
    "places.addressComponents",
])

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
    - API key nao configurada
    - Nenhum resultado encontrado
    - Resultado nao eh tipo hospital/saude
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(GOOGLE_PLACES_URL, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        places = data.get("places", [])
        if not places:
            return None

        place = places[0]
        # Extrair cidade/estado/cep de addressComponents
        cidade, estado, cep = _extrair_endereco(place.get("addressComponents", []))

        location = place.get("location", {})

        # Calcular confianca baseado nos tipos
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
```

**Notas:**
- Custo: ~$0.032/request (Text Search New)
- `includedType: "hospital"` filtra apenas estabelecimentos de saude
- Se `GOOGLE_PLACES_API_KEY` vazio, retorna `None` (feature flag natural)

### Testes Obrigatorios

**Unitarios:**
- [ ] Retorna None quando API key vazia
- [ ] Retorna InfoGooglePlaces com dados corretos (mock httpx)
- [ ] Retorna None quando nenhum resultado
- [ ] `_extrair_endereco` parseia addressComponents corretamente

### Definition of Done

- [ ] Arquivo `hospital_google_places.py` criado
- [ ] Feature flag natural (key vazia = skip)
- [ ] Retry com tenacity (2 tentativas)
- [ ] Testes unitarios passando

---

## Dependencias

Nenhuma — pode ser implementado em paralelo com Epico 1.

## Risco: BAIXO

Google Places API e estavel e bem documentada. Unico risco e o usuario nao ter API key configurada, mas o fallback gracioso garante que o pipeline continua funcionando.
