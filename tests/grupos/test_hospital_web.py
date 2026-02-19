"""
Testes para criação automática de hospitais.

Sprint 14 - E07 - Criação de Hospital via Web
"""

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.grupos.hospital_web import (
    InfoHospitalWeb,
    buscar_hospital_web,
    criar_hospital,
    mergear_hospitais,
    hospital_tem_endereco_completo,
    normalizar_ou_criar_hospital,
    inferir_cidade_regiao,
    listar_hospitais_para_revisao,
    marcar_hospital_revisado,
    ResultadoHospitalAuto,
    REGIOES_CONHECIDAS,
    cnes_to_info_web,
    google_to_info_web,
    _buscar_existente,
    _criar_e_rastrear_hospital,
    _buscar_e_criar_via_cnes,
    _buscar_e_criar_via_google,
    _buscar_e_criar_via_web,
)
from app.services.grupos.hospital_cnes import InfoCNES
from app.services.grupos.hospital_google_places import InfoGooglePlaces


class TestInfoHospitalWeb:
    """Testes da dataclass InfoHospitalWeb."""

    def test_criacao_completa(self):
        """Deve criar info com todos os campos."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital São Luiz",
            logradouro="Rua das Flores",
            numero="123",
            bairro="Centro",
            cidade="São Paulo",
            estado="SP",
            cep="01234-567",
            confianca=0.95,
            fonte="Google",
        )

        assert info.nome_oficial == "Hospital São Luiz"
        assert info.cidade == "São Paulo"
        assert info.confianca == 0.95

    def test_criacao_minima(self):
        """Deve criar info com campos mínimos."""
        info = InfoHospitalWeb(nome_oficial="Hospital ABC")

        assert info.nome_oficial == "Hospital ABC"
        assert info.cidade is None
        assert info.confianca == 0.0


class TestInferirCidadeRegiao:
    """Testes de inferência de cidade/estado."""

    def test_regiao_abc(self):
        """Deve inferir ABC como Santo André/SP."""
        cidade, estado = inferir_cidade_regiao("Plantões ABC")
        assert cidade == "Santo André"
        assert estado == "SP"

    def test_regiao_sp(self):
        """Deve inferir SP como São Paulo/SP."""
        cidade, estado = inferir_cidade_regiao("SP Capital")
        assert cidade == "São Paulo"
        assert estado == "SP"

    def test_regiao_rj(self):
        """Deve inferir RJ como Rio de Janeiro/RJ."""
        cidade, estado = inferir_cidade_regiao("Vagas RJ")
        assert cidade == "Rio de Janeiro"
        assert estado == "RJ"

    def test_regiao_campinas(self):
        """Deve inferir Campinas."""
        cidade, estado = inferir_cidade_regiao("Região Campinas")
        assert cidade == "Campinas"
        assert estado == "SP"

    def test_regiao_desconhecida(self):
        """Deve retornar None para região desconhecida."""
        cidade, estado = inferir_cidade_regiao("XYZ 123")
        assert cidade is None
        assert estado is None

    def test_regiao_vazia(self):
        """Deve retornar None para região vazia."""
        cidade, estado = inferir_cidade_regiao("")
        assert cidade is None
        assert estado is None


class TestRegioesConhecidas:
    """Testes do mapa de regiões."""

    def test_mapa_tem_principais_regioes(self):
        """Verifica regiões principais."""
        assert "abc" in REGIOES_CONHECIDAS
        assert "sp" in REGIOES_CONHECIDAS
        assert "rj" in REGIOES_CONHECIDAS
        assert "campinas" in REGIOES_CONHECIDAS

    def test_formato_valores(self):
        """Verifica formato dos valores (cidade, estado)."""
        for regiao, (cidade, estado) in REGIOES_CONHECIDAS.items():
            assert isinstance(cidade, str)
            assert len(estado) == 2


class TestBuscarHospitalWeb:
    """Testes da busca web."""

    @pytest.fixture
    def mock_anthropic(self):
        """Mock do cliente AsyncAnthropic."""
        with patch("app.services.grupos.hospital_web.anthropic.AsyncAnthropic") as mock:
            instance = mock.return_value
            instance.messages = MagicMock()
            yield instance

    @pytest.mark.asyncio
    async def test_hospital_encontrado(self, mock_anthropic):
        """Deve retornar info quando hospital encontrado."""
        mock_anthropic.messages.create = AsyncMock(
            return_value=MagicMock(
                content=[
                    MagicMock(
                        text="""
                {
                    "encontrado": true,
                    "nome_oficial": "Hospital São Luiz Anália Franco",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "confianca": 0.95
                }
                """
                    )
                ]
            )
        )

        resultado = await buscar_hospital_web("HSL Anália Franco")

        assert resultado is not None
        assert resultado.nome_oficial == "Hospital São Luiz Anália Franco"
        assert resultado.confianca == 0.95

    @pytest.mark.asyncio
    async def test_hospital_nao_encontrado(self, mock_anthropic):
        """Deve retornar None quando hospital não encontrado."""
        mock_anthropic.messages.create = AsyncMock(
            return_value=MagicMock(content=[MagicMock(text='{"encontrado": false}')])
        )

        resultado = await buscar_hospital_web("Hospital XYZ 123")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_resposta_invalida(self, mock_anthropic):
        """Deve retornar None para resposta inválida."""
        mock_anthropic.messages.create = AsyncMock(
            return_value=MagicMock(content=[MagicMock(text="Resposta inválida sem JSON")])
        )

        resultado = await buscar_hospital_web("Hospital")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_texto_vazio(self, mock_anthropic):
        """Deve retornar None para texto vazio."""
        resultado = await buscar_hospital_web("")
        assert resultado is None


class TestCriarHospital:
    """Testes da criação de hospital (via RPC — Sprint 60)."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital ABC",
                        "out_foi_criado": True,
                    }
                ]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_criar_com_dados_completos(self, mock_supabase):
        """Deve criar hospital com todos os dados via RPC."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC", cidade="São Paulo", estado="SP", confianca=0.9
        )

        resultado = await criar_hospital(info, "HSL ABC")

        assert resultado is not None
        mock.rpc.assert_called_once_with(
            "buscar_ou_criar_hospital",
            {
                "p_nome": "Hospital ABC",
                "p_alias_normalizado": "hsl abc",
                "p_cidade": "São Paulo",
                "p_estado": "SP",
                "p_confianca": 0.9,
                "p_criado_por": "busca_web",
            },
        )

    @pytest.mark.asyncio
    async def test_criar_com_dados_minimos(self, mock_supabase):
        """Deve criar hospital com dados mínimos via RPC."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(nome_oficial="Hospital XYZ", confianca=0.5)

        resultado = await criar_hospital(info, "XYZ")

        assert resultado is not None


class TestNormalizarOuCriarHospital:
    """Testes da função principal."""

    @pytest.fixture
    def mock_normalizador(self):
        """Mock das funções do normalizador."""
        with (
            patch("app.services.grupos.normalizador.buscar_hospital_por_alias") as alias,
            patch("app.services.grupos.normalizador.buscar_hospital_por_similaridade") as sim,
        ):
            yield alias, sim

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital ABC",
                        "out_foi_criado": True,
                    }
                ]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_encontra_alias_exato(self, mock_normalizador, mock_supabase):
        """Deve retornar match de alias exato."""
        alias_mock, sim_mock = mock_normalizador

        from app.services.grupos.normalizador import ResultadoMatch

        alias_mock.return_value = ResultadoMatch(
            entidade_id=uuid4(), nome="Hospital ABC", score=1.0, fonte="alias_exato"
        )

        resultado = await normalizar_ou_criar_hospital("ABC")

        assert resultado is not None
        assert resultado.foi_criado is False
        assert resultado.fonte == "alias_exato"

    @pytest.mark.asyncio
    async def test_encontra_similaridade(self, mock_normalizador, mock_supabase):
        """Deve retornar match de similaridade."""
        alias_mock, sim_mock = mock_normalizador

        from app.services.grupos.normalizador import ResultadoMatch

        alias_mock.return_value = None
        sim_mock.return_value = ResultadoMatch(
            entidade_id=uuid4(), nome="Hospital ABC", score=0.85, fonte="nome_similar"
        )

        resultado = await normalizar_ou_criar_hospital("ABC Hospital")

        assert resultado is not None
        assert resultado.foi_criado is False
        assert resultado.fonte == "similaridade"

    @pytest.mark.asyncio
    async def test_texto_vazio(self, mock_normalizador, mock_supabase):
        """Deve retornar None para texto vazio."""
        resultado = await normalizar_ou_criar_hospital("")
        assert resultado is None


class TestResultadoHospitalAuto:
    """Testes da dataclass ResultadoHospitalAuto."""

    def test_criacao(self):
        """Deve criar resultado corretamente."""
        resultado = ResultadoHospitalAuto(
            hospital_id=uuid4(), nome="Hospital ABC", score=0.9, foi_criado=True, fonte="web"
        )

        assert resultado.nome == "Hospital ABC"
        assert resultado.foi_criado is True
        assert resultado.fonte == "web"


class TestListarHospitaisParaRevisao:
    """Testes da listagem de hospitais para revisão."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_lista_hospitais(self, mock_supabase):
        """Deve listar hospitais que precisam revisão."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "nome": "Hospital A"},
                {"id": str(uuid4()), "nome": "Hospital B"},
            ]
        )

        resultado = await listar_hospitais_para_revisao()

        assert len(resultado) == 2


class TestMarcarHospitalRevisado:
    """Testes de marcar hospital como revisado."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_marcar_revisado(self, mock_supabase):
        """Deve marcar hospital como revisado."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await marcar_hospital_revisado(uuid4(), "admin")

        assert resultado is True

    @pytest.mark.asyncio
    async def test_erro_ao_marcar(self, mock_supabase):
        """Deve retornar False em caso de erro."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
            Exception("Erro")
        )

        resultado = await marcar_hospital_revisado(uuid4(), "admin")

        assert resultado is False


# =====================================================================
# Sprint 61 — Conversion Helpers
# =====================================================================


class TestCnesToInfoWeb:
    """Testes do helper cnes_to_info_web."""

    def test_converte_dados_completos(self):
        """Deve converter InfoCNES para InfoHospitalWeb com todos os campos."""
        info = InfoCNES(
            cnes_codigo="2077485",
            nome_oficial="Hospital São Luiz",
            cidade="São Paulo",
            estado="SP",
            logradouro="Rua ABC",
            numero="123",
            bairro="Centro",
            cep="01234-567",
            telefone="(11) 1234-5678",
            latitude=-23.55,
            longitude=-46.63,
            score=0.8,
        )

        result = cnes_to_info_web(info)

        assert result.nome_oficial == "Hospital São Luiz"
        assert result.cidade == "São Paulo"
        assert result.estado == "SP"
        assert result.logradouro == "Rua ABC"
        assert result.cnes_codigo == "2077485"
        assert result.telefone == "(11) 1234-5678"
        assert result.latitude == -23.55
        assert result.longitude == -46.63
        assert result.fonte == "cnes"
        assert result.confianca == 1.0  # 0.8 + 0.2 = 1.0 (capped)

    def test_confianca_cap_1_0(self):
        """Deve limitar confiança em 1.0."""
        info = InfoCNES(cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.95)

        result = cnes_to_info_web(info)

        assert result.confianca == 1.0

    def test_confianca_soma_correta(self):
        """Deve somar 0.2 ao score CNES."""
        info = InfoCNES(cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.5)

        result = cnes_to_info_web(info)

        assert result.confianca == 0.7

    def test_google_place_id_none(self):
        """Deve ter google_place_id como None."""
        info = InfoCNES(cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.5)

        result = cnes_to_info_web(info)

        assert result.google_place_id is None


class TestGoogleToInfoWeb:
    """Testes do helper google_to_info_web."""

    def test_converte_dados_completos(self):
        """Deve converter InfoGooglePlaces para InfoHospitalWeb."""
        info = InfoGooglePlaces(
            place_id="ChIJ_abc",
            nome="Hospital São Luiz Morumbi",
            endereco_formatado="Rua XYZ, 456 - SP",
            cidade="São Paulo",
            estado="SP",
            cep="05605-050",
            latitude=-23.5989,
            longitude=-46.7234,
            telefone="(11) 3093-1100",
            rating=4.2,
            confianca=0.85,
        )

        result = google_to_info_web(info)

        assert result.nome_oficial == "Hospital São Luiz Morumbi"
        assert result.cidade == "São Paulo"
        assert result.estado == "SP"
        assert result.cep == "05605-050"
        assert result.google_place_id == "ChIJ_abc"
        assert result.telefone == "(11) 3093-1100"
        assert result.latitude == -23.5989
        assert result.confianca == 0.85
        assert result.fonte == "google_places"

    def test_cnes_codigo_none(self):
        """Deve ter cnes_codigo como None."""
        info = InfoGooglePlaces(place_id="abc", nome="H", endereco_formatado="", confianca=0.5)

        result = google_to_info_web(info)

        assert result.cnes_codigo is None


# =====================================================================
# Sprint 61 — InfoHospitalWeb novos campos
# =====================================================================


class TestInfoHospitalWebSprint61:
    """Testes dos novos campos na dataclass."""

    def test_campos_enriquecimento_default_none(self):
        """Novos campos devem ser None por padrão."""
        info = InfoHospitalWeb(nome_oficial="Hospital ABC")

        assert info.cnes_codigo is None
        assert info.google_place_id is None
        assert info.telefone is None
        assert info.latitude is None
        assert info.longitude is None

    def test_campos_enriquecimento_preenchidos(self):
        """Deve aceitar novos campos preenchidos."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            cnes_codigo="2077485",
            google_place_id="ChIJ_abc",
            telefone="(11) 1234-5678",
            latitude=-23.55,
            longitude=-46.63,
        )

        assert info.cnes_codigo == "2077485"
        assert info.google_place_id == "ChIJ_abc"
        assert info.telefone == "(11) 1234-5678"


# =====================================================================
# Sprint 61 — Enrichment in criar_hospital
# =====================================================================


class TestCriarHospitalEnrichment:
    """Testes da persistência de enriquecimento em criar_hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC + update."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital CNES",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_persiste_cnes_codigo(self, mock_supabase):
        """Deve fazer UPDATE com cnes_codigo quando presente."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital CNES",
            cidade="São Paulo",
            estado="SP",
            confianca=0.8,
            fonte="cnes",
            cnes_codigo="2077485",
        )

        await criar_hospital(info, "Hospital CNES")

        # Verifica que update foi chamado (table("hospitais").update(...))
        update_calls = [c for c in mock.table.return_value.update.call_args_list]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][0]
        assert update_data["cnes_codigo"] == "2077485"
        assert update_data["enriched_by"] == "cnes"
        assert "enriched_at" in update_data

    @pytest.mark.asyncio
    async def test_persiste_google_place_id(self, mock_supabase):
        """Deve fazer UPDATE com google_place_id quando presente."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital Google",
            cidade="São Paulo",
            estado="SP",
            confianca=0.85,
            fonte="google_places",
            google_place_id="ChIJ_abc123",
            telefone="(11) 1234-5678",
            latitude=-23.55,
            longitude=-46.63,
        )

        await criar_hospital(info, "Hospital Google")

        update_calls = [c for c in mock.table.return_value.update.call_args_list]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][0]
        assert update_data["google_place_id"] == "ChIJ_abc123"
        assert update_data["telefone"] == "(11) 1234-5678"
        assert update_data["latitude"] == -23.55
        assert update_data["longitude"] == -46.63

    @pytest.mark.asyncio
    async def test_nao_faz_update_sem_dados_enriquecimento(self, mock_supabase):
        """Não deve fazer UPDATE quando não há dados de enriquecimento."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital Normal",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9,
        )

        await criar_hospital(info, "Hospital Normal")

        # Update não deve ter sido chamado para enriquecimento
        # (pode ter sido chamado por alias, mas não por enriquecimento)
        update_calls = mock.table.return_value.update.call_args_list
        for call in update_calls:
            update_data = call[0][0]
            assert "cnes_codigo" not in update_data
            assert "google_place_id" not in update_data


# =====================================================================
# Sprint 61 — Pipeline CNES/Google steps
# =====================================================================


class TestNormalizarOuCriarHospitalSprint61:
    """Testes dos novos steps CNES e Google no pipeline."""

    @pytest.fixture
    def mock_normalizador(self):
        """Mock das funções do normalizador — nenhum match."""
        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias", return_value=None
            ) as alias,
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                return_value=None,
            ) as sim,
        ):
            yield alias, sim

    @pytest.fixture
    def mock_validador(self):
        """Mock do validador — sempre válido."""
        with patch("app.services.grupos.hospital_validator.validar_nome_hospital") as mock:
            mock.return_value = MagicMock(valido=True, motivo=None)
            yield mock

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital Via CNES",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            yield mock, hospital_id

    @pytest.fixture
    def mock_emit(self):
        """Mock do emit_event."""
        with patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock):
            yield

    @pytest.mark.asyncio
    async def test_pipeline_usa_cnes_quando_match(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Deve retornar fonte='cnes' quando CNES encontra match >= 0.6."""
        cnes_info = InfoCNES(
            cnes_codigo="2077485",
            nome_oficial="Hospital São Luiz",
            cidade="São Paulo",
            estado="SP",
            score=0.75,
        )

        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=cnes_info,
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital São Luiz", "SP")

        assert resultado is not None
        assert resultado.fonte == "cnes"
        assert resultado.foi_criado is True

    @pytest.mark.asyncio
    async def test_pipeline_pula_cnes_score_baixo_vai_google(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Deve pular CNES com score < 0.6 e tentar Google."""
        cnes_low = InfoCNES(
            cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.4
        )
        google_info = InfoGooglePlaces(
            place_id="ChIJ_abc",
            nome="Hospital ABC Google",
            endereco_formatado="Rua XYZ",
            cidade="São Paulo",
            estado="SP",
            confianca=0.85,
        )

        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=cnes_low,
            ),
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                return_value=google_info,
            ),
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital ABC", "SP")

        assert resultado is not None
        assert resultado.fonte == "google_places"

    @pytest.mark.asyncio
    async def test_pipeline_pula_google_confianca_baixa_vai_llm(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Deve pular Google com confianca < 0.7 e usar LLM."""
        google_low = InfoGooglePlaces(
            place_id="abc", nome="H", endereco_formatado="", confianca=0.5
        )

        llm_info = InfoHospitalWeb(
            nome_oficial="Hospital Via LLM",
            cidade="São Paulo",
            estado="SP",
            confianca=0.8,
        )

        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                return_value=google_low,
            ),
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=llm_info,
            ),
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital XYZ", "SP")

        assert resultado is not None
        assert resultado.fonte == "web"

    @pytest.mark.asyncio
    async def test_pipeline_cnes_erro_nao_bloqueia(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Erro no CNES não deve bloquear pipeline — continua para Google/LLM."""
        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                side_effect=Exception("CNES falhou"),
            ),
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Erro", "SP")

        # Sem match em nenhuma fonte → retorna None para revisão humana
        assert resultado is None

    @pytest.mark.asyncio
    async def test_pipeline_google_erro_nao_bloqueia(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Erro no Google não deve bloquear pipeline — continua para LLM."""
        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                side_effect=Exception("Google falhou"),
            ),
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Erro", "SP")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_pipeline_sem_cnes_sem_google_sem_llm_retorna_none(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Pipeline completo: CNES vazio + Google vazio + LLM vazio → None (revisão humana)."""
        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Teste", "SP")

        assert resultado is None


# =====================================================================
# hospital_tem_endereco_completo
# =====================================================================


class TestHospitalTemEnderecoCompleto:
    """Testes do helper hospital_tem_endereco_completo."""

    def test_completo_true(self):
        """Deve retornar True com lat/long + cidade + estado."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            latitude=-23.55,
            longitude=-46.63,
            cidade="São Paulo",
            estado="SP",
        )
        assert hospital_tem_endereco_completo(info) is True

    def test_false_sem_latitude(self):
        """Deve retornar False sem latitude."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            longitude=-46.63,
            cidade="São Paulo",
            estado="SP",
        )
        assert hospital_tem_endereco_completo(info) is False

    def test_false_sem_longitude(self):
        """Deve retornar False sem longitude."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            latitude=-23.55,
            cidade="São Paulo",
            estado="SP",
        )
        assert hospital_tem_endereco_completo(info) is False

    def test_false_sem_cidade(self):
        """Deve retornar False sem cidade."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            latitude=-23.55,
            longitude=-46.63,
            estado="SP",
        )
        assert hospital_tem_endereco_completo(info) is False

    def test_false_sem_estado(self):
        """Deve retornar False sem estado."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            latitude=-23.55,
            longitude=-46.63,
            cidade="São Paulo",
        )
        assert hospital_tem_endereco_completo(info) is False

    def test_false_cidade_vazia(self):
        """Deve retornar False com cidade vazia."""
        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            latitude=-23.55,
            longitude=-46.63,
            cidade="",
            estado="SP",
        )
        assert hospital_tem_endereco_completo(info) is False


# =====================================================================
# criar_hospital persiste endereço do LLM
# =====================================================================


class TestCriarHospitalPersisteEnderecoLLM:
    """Testes de que criar_hospital persiste dados de endereço do LLM."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC + update."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital LLM",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_persiste_endereco_llm(self, mock_supabase):
        """Deve persistir logradouro/bairro/cep quando vem do LLM (sem CNES/Google)."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital LLM",
            cidade="São Paulo",
            estado="SP",
            confianca=0.8,
            fonte="web",
            logradouro="Rua das Flores",
            bairro="Centro",
            cep="01234-567",
            latitude=-23.55,
            longitude=-46.63,
        )

        await criar_hospital(info, "Hospital LLM")

        update_calls = [c for c in mock.table.return_value.update.call_args_list]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][0]
        assert update_data["logradouro"] == "Rua das Flores"
        assert update_data["bairro"] == "Centro"
        assert update_data["cep"] == "01234-567"
        assert update_data["latitude"] == -23.55
        assert update_data["longitude"] == -46.63
        assert update_data["endereco_verificado"] is True

    @pytest.mark.asyncio
    async def test_persiste_logradouro_sem_cnes_google(self, mock_supabase):
        """Deve fazer UPDATE mesmo sem cnes_codigo ou google_place_id."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital Só Endereço",
            cidade="São Paulo",
            estado="SP",
            confianca=0.7,
            fonte="web",
            logradouro="Av. Brasil",
        )

        await criar_hospital(info, "Hospital Só Endereço")

        update_calls = [c for c in mock.table.return_value.update.call_args_list]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][0]
        assert update_data["logradouro"] == "Av. Brasil"
        assert "endereco_verificado" not in update_data  # sem lat/long

    @pytest.mark.asyncio
    async def test_marca_verificado_com_latlong(self, mock_supabase):
        """Deve setar endereco_verificado=True quando tem lat/long."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital Coords",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9,
            fonte="cnes",
            cnes_codigo="2077485",
            latitude=-23.55,
            longitude=-46.63,
        )

        await criar_hospital(info, "Hospital Coords")

        update_calls = [c for c in mock.table.return_value.update.call_args_list]
        assert len(update_calls) >= 1
        update_data = update_calls[0][0][0]
        assert update_data["endereco_verificado"] is True


# =====================================================================
# mergear_hospitais
# =====================================================================


class TestMergearHospitais:
    """Testes do helper mergear_hospitais."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_chama_rpc_corretamente(self, mock_supabase):
        """Deve chamar RPC mergear_hospitais com parâmetros corretos."""
        fonte = uuid4()
        destino = uuid4()
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={
                "vagas": 2,
                "vagas_grupo": 1,
                "grupos": 0,
                "eventos": 3,
                "alertas": 0,
                "aliases": 1,
            }
        )

        resultado = await mergear_hospitais(fonte, destino)

        mock_supabase.rpc.assert_called_once_with(
            "mergear_hospitais",
            {"p_fonte_id": str(fonte), "p_destino_id": str(destino)},
        )
        assert resultado["vagas"] == 2

    @pytest.mark.asyncio
    async def test_erro_rpc_vazio(self, mock_supabase):
        """Deve levantar exceção quando RPC retorna vazio."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=None)

        with pytest.raises(Exception, match="retornou vazio"):
            await mergear_hospitais(uuid4(), uuid4())


# =====================================================================
# Dedup em criar_hospital
# =====================================================================


class TestCriarHospitalDedup:
    """Testes do dedup automático em criar_hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC + dedup."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            novo_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": novo_id,
                        "out_nome": "Hospital Novo",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            yield mock, novo_id

    @pytest.mark.asyncio
    async def test_merge_quando_cnes_duplicado(self, mock_supabase):
        """Deve mergear quando outro hospital já tem o mesmo cnes_codigo."""
        mock, novo_id = mock_supabase
        destino_id = str(uuid4())

        # Primeira chamada a table() para select (dedup check) retorna match
        # Segunda chamada para rpc (merge) retorna resultado
        select_mock = MagicMock()
        select_mock.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": destino_id}]
        )

        # Setup table mock to return select_mock on first call
        mock.table.return_value = select_mock

        # RPC for merge (second rpc call)
        merge_result = MagicMock(
            data={
                "vagas": 0,
                "vagas_grupo": 0,
                "grupos": 0,
                "eventos": 0,
                "alertas": 0,
                "aliases": 1,
            }
        )
        mock.rpc.return_value.execute.side_effect = [
            # First call: buscar_ou_criar_hospital
            MagicMock(
                data=[
                    {
                        "out_hospital_id": novo_id,
                        "out_nome": "Hospital Novo",
                        "out_foi_criado": True,
                    }
                ]
            ),
            # Second call: mergear_hospitais
            merge_result,
        ]

        info = InfoHospitalWeb(
            nome_oficial="Hospital Novo",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9,
            fonte="cnes",
            cnes_codigo="2077485",
        )

        result = await criar_hospital(info, "Hospital Novo")

        # Should return the destino_id (existing hospital)
        assert str(result) == destino_id


# =====================================================================
# Sprint 63 — Testes das funções extraídas (refatoração god function)
# =====================================================================


class TestBuscarExistente:
    """Testes da função _buscar_existente."""

    @pytest.mark.asyncio
    async def test_encontra_alias_exato(self):
        """Deve retornar resultado quando alias exato é encontrado."""
        from app.services.grupos.normalizador import ResultadoMatch

        hospital_id = uuid4()

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=ResultadoMatch(
                    entidade_id=hospital_id, nome="Hospital ABC", score=1.0, fonte="alias_exato"
                ),
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_existente("Hospital ABC")

        assert resultado is not None
        assert resultado.hospital_id == hospital_id
        assert resultado.fonte == "alias_exato"
        assert resultado.foi_criado is False

    @pytest.mark.asyncio
    async def test_encontra_similaridade(self):
        """Deve retornar resultado quando similaridade é encontrada."""
        from app.services.grupos.normalizador import ResultadoMatch

        hospital_id = uuid4()

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=ResultadoMatch(
                    entidade_id=hospital_id, nome="Hospital ABC", score=0.85, fonte="nome_similar"
                ),
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_existente("Hospital ABC Teste")

        assert resultado is not None
        assert resultado.fonte == "similaridade"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_match(self):
        """Deve retornar None quando nenhuma busca encontra match."""
        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resultado = await _buscar_existente("Hospital XYZ Nao Existe")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_safety_net_encontra_sem_sufixo(self):
        """Deve encontrar hospital removendo sufixo com separador."""
        from app.services.grupos.normalizador import ResultadoMatch

        hospital_id = uuid4()

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                side_effect=[
                    None,
                    ResultadoMatch(
                        entidade_id=hospital_id,
                        nome="Hospital ABC",
                        score=0.95,
                        fonte="alias_exato",
                    ),
                ],
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_existente("Hospital ABC - Ala Norte")

        assert resultado is not None
        assert resultado.fonte == "safety_net_sem_sufixo"


class TestCriarERastrearHospital:
    """Testes da função _criar_e_rastrear_hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital Teste",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            mock.table.return_value.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_cria_hospital_e_emite_evento(self, mock_supabase):
        """Deve criar hospital e emitir evento HOSPITAL_CREATED."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital CNES", cidade="SP", estado="SP", confianca=0.8, fonte="cnes"
        )

        with patch(
            "app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock
        ) as mock_emit:
            resultado = await _criar_e_rastrear_hospital(info, "H CNES", "cnes", {"cnes": "123"})

        assert resultado.foi_criado is True
        assert resultado.fonte == "cnes"
        assert resultado.nome == "Hospital CNES"

    @pytest.mark.asyncio
    async def test_marca_revisao_sem_endereco_completo(self, mock_supabase):
        """Deve marcar para revisão quando endereço incompleto."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(nome_oficial="Hospital Simples", confianca=0.7)

        with patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock):
            await _criar_e_rastrear_hospital(info, "H Simples", "web")

        # Verifica que update com precisa_revisao=True foi chamado
        update_calls = mock.table.return_value.update.call_args_list
        revisao_chamada = any(call[0][0].get("precisa_revisao") is True for call in update_calls)
        assert revisao_chamada


class TestBuscarECriarViaCnes:
    """Testes da função _buscar_e_criar_via_cnes."""

    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital CNES",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            mock.table.return_value.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            yield mock

    @pytest.mark.asyncio
    async def test_retorna_resultado_quando_cnes_encontra(self, mock_supabase):
        """Deve retornar resultado quando CNES encontra hospital com score >= 0.6."""
        cnes_info = InfoCNES(
            cnes_codigo="2077485", nome_oficial="Hospital CNES", cidade="SP", estado="SP", score=0.7
        )

        with (
            patch(
                "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
                new_callable=AsyncMock,
                return_value=cnes_info,
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_e_criar_via_cnes("Hospital CNES", "São Paulo", "SP")

        assert resultado is not None
        assert resultado.fonte == "cnes"

    @pytest.mark.asyncio
    async def test_retorna_none_quando_cnes_score_baixo(self, mock_supabase):
        """Deve retornar None quando CNES tem score < 0.6."""
        cnes_info = InfoCNES(
            cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.3
        )

        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=cnes_info,
        ):
            resultado = await _buscar_e_criar_via_cnes("Hospital XYZ", None, None)

        assert resultado is None

    @pytest.mark.asyncio
    async def test_retorna_none_quando_cnes_falha(self, mock_supabase):
        """Deve retornar None quando CNES lança exceção."""
        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            side_effect=Exception("CNES offline"),
        ):
            resultado = await _buscar_e_criar_via_cnes("Hospital Erro", None, None)

        assert resultado is None


class TestBuscarECriarViaGoogle:
    """Testes da função _buscar_e_criar_via_google."""

    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital Google",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            mock.table.return_value.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            yield mock

    @pytest.mark.asyncio
    async def test_retorna_resultado_quando_google_encontra(self, mock_supabase):
        """Deve retornar resultado quando Google Places encontra hospital."""
        google_info = InfoGooglePlaces(
            place_id="ChIJ_abc",
            nome="Hospital Google",
            endereco_formatado="Rua XYZ",
            cidade="São Paulo",
            estado="SP",
            confianca=0.85,
        )

        with (
            patch(
                "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
                new_callable=AsyncMock,
                return_value=google_info,
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_e_criar_via_google("Hospital Google", "SP")

        assert resultado is not None
        assert resultado.fonte == "google_places"

    @pytest.mark.asyncio
    async def test_retorna_none_quando_google_confianca_baixa(self, mock_supabase):
        """Deve retornar None quando Google tem confiança < 0.7."""
        google_low = InfoGooglePlaces(
            place_id="abc", nome="H", endereco_formatado="", confianca=0.5
        )

        with patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=google_low,
        ):
            resultado = await _buscar_e_criar_via_google("Hospital XYZ", "SP")

        assert resultado is None


class TestBuscarECriarViaWeb:
    """Testes da função _buscar_e_criar_via_web."""

    @pytest.fixture
    def mock_supabase(self):
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "out_hospital_id": hospital_id,
                        "out_nome": "Hospital LLM",
                        "out_foi_criado": True,
                    }
                ]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
            mock.table.return_value.select.return_value.eq.return_value.neq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            yield mock

    @pytest.mark.asyncio
    async def test_retorna_resultado_quando_llm_encontra(self, mock_supabase):
        """Deve retornar resultado quando LLM web encontra hospital."""
        llm_info = InfoHospitalWeb(
            nome_oficial="Hospital LLM", cidade="SP", estado="SP", confianca=0.8
        )

        with (
            patch(
                "app.services.grupos.hospital_web.buscar_hospital_web",
                new_callable=AsyncMock,
                return_value=llm_info,
            ),
            patch("app.services.grupos.hospital_web.emit_event", new_callable=AsyncMock),
        ):
            resultado = await _buscar_e_criar_via_web("Hospital LLM", "SP")

        assert resultado is not None
        assert resultado.fonte == "web"

    @pytest.mark.asyncio
    async def test_retorna_none_quando_llm_confianca_baixa(self, mock_supabase):
        """Deve retornar None quando LLM tem confiança < 0.6."""
        llm_low = InfoHospitalWeb(nome_oficial="Hospital?", confianca=0.3)

        with patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=llm_low,
        ):
            resultado = await _buscar_e_criar_via_web("Hospital XYZ", "SP")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_retorna_none_quando_llm_retorna_none(self, mock_supabase):
        """Deve retornar None quando LLM não encontra nada."""
        with patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await _buscar_e_criar_via_web("Hospital XYZ", "SP")

        assert resultado is None
