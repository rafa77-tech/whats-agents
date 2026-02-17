"""
Testes para busca de hospitais via Google Places.

Sprint 61 - Épico 2.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.grupos.hospital_google_places import (
    InfoGooglePlaces,
    buscar_hospital_google_places,
    _extrair_endereco,
    GOOGLE_PLACES_URL,
    FIELD_MASK,
)


# =====================================================================
# Fixtures
# =====================================================================


GOOGLE_PLACES_RESPONSE = {
    "places": [
        {
            "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "displayName": {"text": "Hospital São Luiz Morumbi"},
            "formattedAddress": "R. Eng. Oscar Americano, 840 - Morumbi, São Paulo - SP, 05605-050",
            "location": {"latitude": -23.5989, "longitude": -46.7234},
            "nationalPhoneNumber": "(11) 3093-1100",
            "rating": 4.2,
            "types": ["hospital", "health", "point_of_interest"],
            "addressComponents": [
                {"types": ["administrative_area_level_2"], "longText": "São Paulo", "shortText": "São Paulo"},
                {"types": ["administrative_area_level_1"], "longText": "São Paulo", "shortText": "SP"},
                {"types": ["postal_code"], "longText": "05605-050", "shortText": "05605-050"},
                {"types": ["route"], "longText": "Rua Engenheiro Oscar Americano", "shortText": "R. Eng. Oscar Americano"},
            ],
        }
    ]
}


@pytest.fixture
def mock_settings_with_key():
    """Mock settings com API key configurada."""
    with patch("app.services.grupos.hospital_google_places.settings") as mock:
        mock.GOOGLE_PLACES_API_KEY = "test-api-key-123"
        yield mock


@pytest.fixture
def mock_settings_no_key():
    """Mock settings sem API key."""
    with patch("app.services.grupos.hospital_google_places.settings") as mock:
        mock.GOOGLE_PLACES_API_KEY = ""
        yield mock


# =====================================================================
# _extrair_endereco
# =====================================================================


class TestExtrairEndereco:
    """Testes do parser de addressComponents."""

    def test_extrai_cidade_estado_cep(self):
        """Deve extrair cidade, estado e CEP corretamente."""
        components = [
            {"types": ["administrative_area_level_2"], "longText": "São Paulo", "shortText": "São Paulo"},
            {"types": ["administrative_area_level_1"], "longText": "São Paulo", "shortText": "SP"},
            {"types": ["postal_code"], "longText": "05605-050", "shortText": "05605-050"},
        ]

        cidade, estado, cep = _extrair_endereco(components)

        assert cidade == "São Paulo"
        assert estado == "SP"
        assert cep == "05605-050"

    def test_retorna_none_quando_vazio(self):
        """Deve retornar None para todos os campos quando lista vazia."""
        cidade, estado, cep = _extrair_endereco([])

        assert cidade is None
        assert estado is None
        assert cep is None

    def test_parcial_sem_cep(self):
        """Deve retornar None para CEP quando ausente."""
        components = [
            {"types": ["administrative_area_level_2"], "longText": "Campinas", "shortText": "Campinas"},
            {"types": ["administrative_area_level_1"], "longText": "São Paulo", "shortText": "SP"},
        ]

        cidade, estado, cep = _extrair_endereco(components)

        assert cidade == "Campinas"
        assert estado == "SP"
        assert cep is None

    def test_ignora_tipos_irrelevantes(self):
        """Deve ignorar componentes com tipos não relevantes."""
        components = [
            {"types": ["route"], "longText": "Rua ABC", "shortText": "R. ABC"},
            {"types": ["street_number"], "longText": "123", "shortText": "123"},
            {"types": ["country"], "longText": "Brasil", "shortText": "BR"},
        ]

        cidade, estado, cep = _extrair_endereco(components)

        assert cidade is None
        assert estado is None
        assert cep is None


# =====================================================================
# buscar_hospital_google_places
# =====================================================================


class TestBuscarHospitalGooglePlaces:
    """Testes da busca Google Places."""

    @pytest.mark.asyncio
    async def test_retorna_none_sem_api_key(self, mock_settings_no_key):
        """Deve retornar None quando GOOGLE_PLACES_API_KEY vazio."""
        resultado = await buscar_hospital_google_places("Hospital São Luiz")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_retorna_info_com_dados_corretos(self, mock_settings_with_key):
        """Deve retornar InfoGooglePlaces com dados corretos."""
        mock_response = MagicMock()
        mock_response.json.return_value = GOOGLE_PLACES_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch(
            "app.services.grupos.hospital_google_places.get_http_client",
            return_value=mock_http_client,
        ):
            resultado = await buscar_hospital_google_places("Hospital São Luiz")

        assert resultado is not None
        assert isinstance(resultado, InfoGooglePlaces)
        assert resultado.place_id == "ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert resultado.nome == "Hospital São Luiz Morumbi"
        assert resultado.cidade == "São Paulo"
        assert resultado.estado == "SP"
        assert resultado.cep == "05605-050"
        assert resultado.latitude == -23.5989
        assert resultado.longitude == -46.7234
        assert resultado.telefone == "(11) 3093-1100"
        assert resultado.rating == 4.2
        assert resultado.confianca == 0.85  # hospital type = saúde

    @pytest.mark.asyncio
    async def test_retorna_none_sem_resultados(self, mock_settings_with_key):
        """Deve retornar None quando API não retorna resultados."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"places": []}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch(
            "app.services.grupos.hospital_google_places.get_http_client",
            return_value=mock_http_client,
        ):
            resultado = await buscar_hospital_google_places("Hospital Inexistente XYZ")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_confianca_baixa_para_nao_saude(self, mock_settings_with_key):
        """Deve ter confiança 0.5 quando tipos não são de saúde."""
        response_data = {
            "places": [
                {
                    "id": "abc123",
                    "displayName": {"text": "Hotel Hospital"},
                    "formattedAddress": "Rua XYZ, 123",
                    "location": {"latitude": -23.55, "longitude": -46.63},
                    "types": ["lodging", "point_of_interest"],
                    "addressComponents": [],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch(
            "app.services.grupos.hospital_google_places.get_http_client",
            return_value=mock_http_client,
        ):
            resultado = await buscar_hospital_google_places("Hotel Hospital")

        assert resultado is not None
        assert resultado.confianca == 0.5

    @pytest.mark.asyncio
    async def test_inclui_regiao_hint_na_query(self, mock_settings_with_key):
        """Deve incluir regiao_hint na query de busca."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"places": []}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch(
            "app.services.grupos.hospital_google_places.get_http_client",
            return_value=mock_http_client,
        ):
            await buscar_hospital_google_places("Hospital ABC", "Santo André")

        call_args = mock_http_client.post.call_args
        body = call_args.kwargs.get("json") or call_args[1].get("json")
        assert body is not None
        assert "Santo André" in body["textQuery"]

    @pytest.mark.asyncio
    async def test_retorna_none_em_erro_generico(self, mock_settings_with_key):
        """Deve retornar None em erro genérico (não HTTP)."""
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = Exception("Connection error")

        with patch(
            "app.services.grupos.hospital_google_places.get_http_client",
            return_value=mock_http_client,
        ):
            resultado = await buscar_hospital_google_places("Hospital ABC")

        assert resultado is None


# =====================================================================
# Constantes
# =====================================================================


class TestConstantes:
    """Testes de constantes do módulo."""

    def test_url_google_places(self):
        """URL deve apontar para API v1."""
        assert "v1/places:searchText" in GOOGLE_PLACES_URL

    def test_field_mask_inclui_campos_essenciais(self):
        """Field mask deve incluir campos necessários."""
        assert "places.id" in FIELD_MASK
        assert "places.displayName" in FIELD_MASK
        assert "places.location" in FIELD_MASK
        assert "places.addressComponents" in FIELD_MASK
