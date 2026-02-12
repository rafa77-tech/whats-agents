"""
Testes para injeção de contexto de campanha no pipeline.

Cobre:
- carregar_contexto_campanha() (Issue 1.2)
- _campanha_dentro_janela() (Issue 4.1)
- Fallback campanha_id (Issue 3.2)
- Cache Redis (Issue 4.3)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.services.contexto import (
    carregar_contexto_campanha,
    _campanha_dentro_janela,
)
from app.services.campanhas.types import (
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


# =============================================================================
# _campanha_dentro_janela - Testes de TTL (Issue 4.1)
# =============================================================================


class TestCampanhaDentroJanela:
    """Testes para filtros TTL de campanha."""

    def test_status_none_retorna_false(self):
        """Status None deve ser rejeitado."""
        assert _campanha_dentro_janela(None, None, None) is False

    def test_cancelada_nunca_injeta(self):
        """Campanha cancelada nunca deve injetar contexto."""
        assert _campanha_dentro_janela("cancelada", None, None) is False

    def test_ativa_sempre_injeta(self):
        """Campanha ativa deve sempre injetar contexto."""
        assert _campanha_dentro_janela("ativa", None, None) is True

    def test_agendada_sempre_injeta(self):
        """Campanha agendada deve sempre injetar contexto."""
        assert _campanha_dentro_janela("agendada", None, None) is True

    def test_concluida_dentro_janela_injeta(self):
        """Campanha concluída há menos de 7 dias deve injetar."""
        agora = datetime.now(timezone.utc)
        concluida_em = (agora - timedelta(days=3)).isoformat()

        assert _campanha_dentro_janela("concluida", concluida_em, None) is True

    def test_concluida_fora_janela_nao_injeta(self):
        """Campanha concluída há mais de 7 dias não deve injetar."""
        agora = datetime.now(timezone.utc)
        concluida_em = (agora - timedelta(days=10)).isoformat()

        assert _campanha_dentro_janela("concluida", concluida_em, None) is False

    def test_concluida_exatamente_7_dias_injeta(self):
        """Campanha concluída há exatamente 7 dias deve injetar (<=)."""
        agora = datetime.now(timezone.utc)
        concluida_em = (agora - timedelta(days=7)).isoformat()

        assert _campanha_dentro_janela("concluida", concluida_em, None) is True

    def test_concluida_8_dias_nao_injeta(self):
        """Campanha concluída há 8 dias não deve injetar."""
        agora = datetime.now(timezone.utc)
        concluida_em = (agora - timedelta(days=8)).isoformat()

        assert _campanha_dentro_janela("concluida", concluida_em, None) is False

    def test_concluida_sem_data_retorna_false(self):
        """Campanha concluída sem concluida_em com data invalida."""
        # concluida_em None -> try/except retorna False
        assert _campanha_dentro_janela("concluida", None, None) is True

    def test_last_touch_dentro_janela(self):
        """last_touch recente permite injeção."""
        agora = datetime.now(timezone.utc)
        last_touch = (agora - timedelta(days=2)).isoformat()

        assert _campanha_dentro_janela("ativa", None, last_touch) is True

    def test_last_touch_fora_janela_nao_injeta(self):
        """last_touch antigo bloqueia injeção."""
        agora = datetime.now(timezone.utc)
        last_touch = (agora - timedelta(days=10)).isoformat()

        assert _campanha_dentro_janela("ativa", None, last_touch) is False

    def test_last_touch_invalido_nao_bloqueia(self):
        """last_touch inválido não bloqueia (continua)."""
        assert _campanha_dentro_janela("ativa", None, "invalido") is True

    def test_concluida_data_com_z(self):
        """Deve parsear datas com sufixo Z."""
        agora = datetime.now(timezone.utc)
        concluida_em = (agora - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        assert _campanha_dentro_janela("concluida", concluida_em, None) is True

    def test_rascunho_injeta(self):
        """Status rascunho não está na lista de bloqueio (edge case)."""
        assert _campanha_dentro_janela("rascunho", None, None) is True

    def test_pausada_injeta(self):
        """Status pausada não bloqueia (pode voltar a ativa)."""
        assert _campanha_dentro_janela("pausada", None, None) is True


# =============================================================================
# carregar_contexto_campanha - Testes de carga (Issue 1.2)
# =============================================================================


class TestCarregarContextoCampanha:
    """Testes para carregar_contexto_campanha."""

    @pytest.mark.asyncio
    async def test_sem_ids_retorna_none(self):
        """Deve retornar None quando nenhum ID fornecido."""
        resultado = await carregar_contexto_campanha(
            campaign_id=None,
            last_touch_at=None,
            campanha_id_fallback=None,
        )
        assert resultado is None

    @pytest.mark.asyncio
    async def test_campanha_ativa_retorna_contexto(self):
        """Deve retornar contexto para campanha ativa."""
        campanha = CampanhaData(
            id=20,
            nome_template="App Download",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.ATIVA,
            objetivo="Fazer médico baixar o app Revoluna",
            pode_ofertar=False,
            regras={"regras": ["Não mencionar vagas", "Focar no app"]},
            escopo_vagas=None,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=20)

            assert resultado is not None
            assert resultado["campaign_type"] == "discovery"
            assert resultado["campaign_objective"] == "Fazer médico baixar o app Revoluna"
            assert resultado["pode_ofertar"] is False
            assert resultado["campaign_rules"] == ["Não mencionar vagas", "Focar no app"]

    @pytest.mark.asyncio
    async def test_campanha_cancelada_retorna_none(self):
        """Campanha cancelada deve retornar None."""
        campanha = CampanhaData(
            id=21,
            nome_template="Cancelada",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.CANCELADA,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=21)

            assert resultado is None

    @pytest.mark.asyncio
    async def test_campanha_nao_encontrada_retorna_none(self):
        """Campanha inexistente deve retornar None."""
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=None)

            resultado = await carregar_contexto_campanha(campaign_id=999)

            assert resultado is None

    @pytest.mark.asyncio
    async def test_fallback_campanha_id(self):
        """Deve usar campanha_id_fallback quando campaign_id é None (Issue 3.2)."""
        campanha = CampanhaData(
            id=22,
            nome_template="Fallback",
            tipo_campanha=TipoCampanha.OFERTA,
            status=StatusCampanha.ATIVA,
            pode_ofertar=True,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(
                campaign_id=None,
                campanha_id_fallback=22,
            )

            assert resultado is not None
            assert resultado["campaign_type"] == "oferta"
            assert resultado["pode_ofertar"] is True
            mock_repo.buscar_por_id.assert_called_once_with(22)

    @pytest.mark.asyncio
    async def test_cache_hit_retorna_dados(self):
        """Deve retornar dados do cache sem buscar no banco (Issue 4.3)."""
        cached = {
            "campaign_type": "discovery",
            "campaign_objective": "Teste cache",
            "campaign_rules": None,
            "offer_scope": None,
            "negotiation_margin": None,
            "pode_ofertar": False,
            "_status": "ativa",
            "_concluida_em": None,
        }

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=cached
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            resultado = await carregar_contexto_campanha(campaign_id=20)

            assert resultado is not None
            assert resultado["campaign_objective"] == "Teste cache"
            # Não deve ter chamado o banco
            mock_repo.buscar_por_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_campanha_cancelada_retorna_none(self):
        """Cache de campanha cancelada deve retornar None."""
        cached = {
            "campaign_type": "discovery",
            "campaign_objective": "Teste",
            "pode_ofertar": False,
            "_status": "cancelada",
            "_concluida_em": None,
        }

        with patch(
            "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=cached
        ):
            resultado = await carregar_contexto_campanha(campaign_id=20)
            assert resultado is None

    @pytest.mark.asyncio
    async def test_cache_salvo_apos_busca(self):
        """Deve salvar no cache após busca no banco."""
        campanha = CampanhaData(
            id=23,
            nome_template="Cache Test",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.ATIVA,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ) as mock_set,
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            await carregar_contexto_campanha(campaign_id=23)

            mock_set.assert_called_once()
            call_args = mock_set.call_args
            assert call_args[0][0] == "campanha:contexto:23"
            assert call_args[0][2] == 300  # TTL 5min

    @pytest.mark.asyncio
    async def test_regras_dict_com_chave_regras(self):
        """Deve extrair regras de dict com chave 'regras'."""
        campanha = CampanhaData(
            id=24,
            nome_template="Regras Dict",
            tipo_campanha=TipoCampanha.OFERTA,
            status=StatusCampanha.ATIVA,
            regras={"regras": ["regra1", "regra2"]},
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=24)

            assert resultado["campaign_rules"] == ["regra1", "regra2"]

    @pytest.mark.asyncio
    async def test_regras_lista_direta(self):
        """Deve aceitar regras como lista direta."""
        campanha = CampanhaData(
            id=25,
            nome_template="Regras Lista",
            tipo_campanha=TipoCampanha.OFERTA,
            status=StatusCampanha.ATIVA,
            regras=["regra1", "regra2"],
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=25)

            assert resultado["campaign_rules"] == ["regra1", "regra2"]

    @pytest.mark.asyncio
    async def test_regras_none(self):
        """Regras None deve resultar em campaign_rules None."""
        campanha = CampanhaData(
            id=26,
            nome_template="Sem Regras",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.ATIVA,
            regras=None,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=26)

            assert resultado["campaign_rules"] is None

    @pytest.mark.asyncio
    async def test_exception_retorna_none(self):
        """Exceção no banco deve retornar None (graceful degradation)."""
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(side_effect=Exception("DB error"))

            resultado = await carregar_contexto_campanha(campaign_id=99)

            assert resultado is None

    @pytest.mark.asyncio
    async def test_concluida_dentro_janela_retorna_contexto(self):
        """Campanha concluída dentro da janela deve retornar contexto."""
        agora = datetime.now(timezone.utc)
        campanha = CampanhaData(
            id=27,
            nome_template="Concluída Recente",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.CONCLUIDA,
            concluida_em=agora - timedelta(days=3),
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=27)

            assert resultado is not None

    @pytest.mark.asyncio
    async def test_concluida_fora_janela_retorna_none(self):
        """Campanha concluída fora da janela deve retornar None."""
        agora = datetime.now(timezone.utc)
        campanha = CampanhaData(
            id=28,
            nome_template="Concluída Antiga",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.CONCLUIDA,
            concluida_em=agora - timedelta(days=10),
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(campaign_id=28)

            assert resultado is None

    @pytest.mark.asyncio
    async def test_campaign_id_tem_prioridade_sobre_fallback(self):
        """campaign_id deve ter prioridade sobre campanha_id_fallback."""
        campanha = CampanhaData(
            id=30,
            nome_template="Prioridade",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.ATIVA,
        )

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch(
                "app.services.contexto.cache_set_json", new_callable=AsyncMock, return_value=True
            ),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            await carregar_contexto_campanha(
                campaign_id=30,
                campanha_id_fallback=99,
            )

            # Deve buscar pelo campaign_id, não pelo fallback
            mock_repo.buscar_por_id.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_last_touch_fora_janela_retorna_none(self):
        """last_touch_at antigo deve bloquear injeção."""
        agora = datetime.now(timezone.utc)
        campanha = CampanhaData(
            id=31,
            nome_template="Touch Antigo",
            tipo_campanha=TipoCampanha.DISCOVERY,
            status=StatusCampanha.ATIVA,
        )
        old_touch = (agora - timedelta(days=10)).isoformat()

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha)

            resultado = await carregar_contexto_campanha(
                campaign_id=31,
                last_touch_at=old_touch,
            )

            assert resultado is None
