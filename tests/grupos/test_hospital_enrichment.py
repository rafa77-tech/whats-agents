"""
Testes para enriquecimento batch de hospitais.

Sprint 61 - Épico 4.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.grupos.hospital_enrichment import (
    ResultadoEnriquecimento,
    enriquecer_hospitais_batch,
    _aplicar_enriquecimento_cnes,
    _aplicar_enriquecimento_google,
)
from app.services.grupos.hospital_cnes import InfoCNES
from app.services.grupos.hospital_google_places import InfoGooglePlaces


# =====================================================================
# Fixtures
# =====================================================================


def _make_hospital(id="h1", nome="Hospital ABC", cidade="São Paulo", estado="SP"):
    return {"id": id, "nome": nome, "cidade": cidade, "estado": estado}


def _make_info_cnes(score=0.7):
    return InfoCNES(
        cnes_codigo="2077485",
        nome_oficial="Hospital ABC Oficial",
        cidade="São Paulo",
        estado="SP",
        logradouro="Rua das Flores",
        numero="123",
        bairro="Centro",
        cep="01234-567",
        telefone="(11) 1234-5678",
        latitude=-23.55,
        longitude=-46.63,
        score=score,
    )


def _make_info_google(confianca=0.85):
    return InfoGooglePlaces(
        place_id="ChIJ_abc123",
        nome="Hospital ABC Google",
        endereco_formatado="Rua XYZ, 456 - SP",
        cidade="São Paulo",
        estado="SP",
        cep="01234-567",
        latitude=-23.55,
        longitude=-46.63,
        telefone="(11) 9876-5432",
        rating=4.5,
        confianca=confianca,
    )


@pytest.fixture
def mock_supabase():
    """Mock do Supabase."""
    with patch("app.services.grupos.hospital_enrichment.supabase") as mock:
        yield mock


# =====================================================================
# _aplicar_enriquecimento_cnes
# =====================================================================


class TestAplicarEnriquecimentoCnes:
    """Testes de aplicação de dados CNES."""

    @pytest.mark.asyncio
    async def test_atualiza_campos_cnes(self, mock_supabase):
        """Deve atualizar hospital com dados CNES completos."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        info = _make_info_cnes()
        await _aplicar_enriquecimento_cnes("h1", info)

        call_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert call_args["cnes_codigo"] == "2077485"
        assert call_args["enriched_by"] == "cnes_batch"
        assert call_args["logradouro"] == "Rua das Flores"
        assert call_args["telefone"] == "(11) 1234-5678"
        assert call_args["latitude"] == -23.55
        assert "enriched_at" in call_args

    @pytest.mark.asyncio
    async def test_nao_inclui_campos_none(self, mock_supabase):
        """Deve omitir campos que são None."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        info = InfoCNES(
            cnes_codigo="123",
            nome_oficial="Hospital X",
            cidade="SP",
            estado="SP",
            score=0.5,
        )
        await _aplicar_enriquecimento_cnes("h1", info)

        call_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert "logradouro" not in call_args
        assert "telefone" not in call_args
        assert "latitude" not in call_args


# =====================================================================
# _aplicar_enriquecimento_google
# =====================================================================


class TestAplicarEnriquecimentoGoogle:
    """Testes de aplicação de dados Google Places."""

    @pytest.mark.asyncio
    async def test_atualiza_campos_google(self, mock_supabase):
        """Deve atualizar hospital com dados Google completos."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        info = _make_info_google()
        await _aplicar_enriquecimento_google("h1", info)

        call_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert call_args["google_place_id"] == "ChIJ_abc123"
        assert call_args["enriched_by"] == "google_batch"
        assert call_args["cidade"] == "São Paulo"
        assert call_args["telefone"] == "(11) 9876-5432"
        assert "enriched_at" in call_args


# =====================================================================
# enriquecer_hospitais_batch
# =====================================================================


class TestEnriquecerHospitaisBatch:
    """Testes do enriquecimento batch."""

    @pytest.mark.asyncio
    async def test_enriquece_com_cnes(self, mock_supabase):
        """Deve enriquecer hospital quando CNES encontra match."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[_make_hospital()]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=_make_info_cnes(score=0.7),
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.total == 1
        assert resultado.enriquecidos_cnes == 1
        assert resultado.enriquecidos_google == 0
        assert resultado.sem_match == 0

    @pytest.mark.asyncio
    async def test_fallback_google_quando_cnes_falha(self, mock_supabase):
        """Deve tentar Google Places quando CNES não encontra."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[_make_hospital()]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=_make_info_google(confianca=0.85),
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.total == 1
        assert resultado.enriquecidos_cnes == 0
        assert resultado.enriquecidos_google == 1

    @pytest.mark.asyncio
    async def test_sem_match_quando_ambos_falham(self, mock_supabase):
        """Deve contar sem_match quando CNES e Google falham."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[_make_hospital()]
        )

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.sem_match == 1
        assert resultado.enriquecidos_cnes == 0
        assert resultado.enriquecidos_google == 0

    @pytest.mark.asyncio
    async def test_cnes_score_baixo_vai_para_google(self, mock_supabase):
        """Deve ir para Google quando CNES retorna score < 0.4."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[_make_hospital()]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        low_score_cnes = _make_info_cnes(score=0.3)

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=low_score_cnes,
        ), patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=_make_info_google(),
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.enriquecidos_cnes == 0
        assert resultado.enriquecidos_google == 1

    @pytest.mark.asyncio
    async def test_erro_nao_bloqueia_processamento(self, mock_supabase):
        """Deve continuar processando após erro em um hospital."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                _make_hospital(id="h1", nome="Hospital Erro"),
                _make_hospital(id="h2", nome="Hospital OK"),
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        call_count = 0

        async def cnes_side_effect(nome, cidade, estado):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Erro simulado")
            return _make_info_cnes()

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            side_effect=cnes_side_effect,
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.total == 2
        assert resultado.erros == 1
        assert resultado.enriquecidos_cnes == 1
        assert len(resultado.erros_detalhe) == 1

    @pytest.mark.asyncio
    async def test_lista_vazia(self, mock_supabase):
        """Deve retornar resultado zerado quando não há hospitais."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await enriquecer_hospitais_batch()

        assert resultado.total == 0
        assert resultado.enriquecidos_cnes == 0
        assert resultado.enriquecidos_google == 0

    @pytest.mark.asyncio
    async def test_contadores_multiplos(self, mock_supabase):
        """Deve acumular contadores corretamente com múltiplos hospitais."""
        mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                _make_hospital(id="h1", nome="Hospital A"),
                _make_hospital(id="h2", nome="Hospital B"),
                _make_hospital(id="h3", nome="Hospital C"),
            ]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        cnes_responses = [_make_info_cnes(), None, _make_info_cnes()]

        with patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_cnes",
            new_callable=AsyncMock,
            side_effect=cnes_responses,
        ), patch(
            "app.services.grupos.hospital_enrichment.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await enriquecer_hospitais_batch()

        assert resultado.total == 3
        assert resultado.enriquecidos_cnes == 2
        assert resultado.sem_match == 1


# =====================================================================
# ResultadoEnriquecimento
# =====================================================================


class TestResultadoEnriquecimento:
    """Testes da dataclass de resultado."""

    def test_defaults(self):
        """Deve inicializar com zeros."""
        r = ResultadoEnriquecimento()
        assert r.total == 0
        assert r.enriquecidos_cnes == 0
        assert r.enriquecidos_google == 0
        assert r.sem_match == 0
        assert r.erros == 0
        assert r.erros_detalhe == []
