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
    criar_hospital_minimo,
    normalizar_ou_criar_hospital,
    inferir_cidade_regiao,
    listar_hospitais_para_revisao,
    marcar_hospital_revisado,
    ResultadoHospitalAuto,
    REGIOES_CONHECIDAS,
    cnes_to_info_web,
    google_to_info_web,
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
            fonte="Google"
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
                content=[MagicMock(text='''
                {
                    "encontrado": true,
                    "nome_oficial": "Hospital São Luiz Anália Franco",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "confianca": 0.95
                }
                ''')]
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
            return_value=MagicMock(
                content=[MagicMock(text='{"encontrado": false}')]
            )
        )

        resultado = await buscar_hospital_web("Hospital XYZ 123")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_resposta_invalida(self, mock_anthropic):
        """Deve retornar None para resposta inválida."""
        mock_anthropic.messages.create = AsyncMock(
            return_value=MagicMock(
                content=[MagicMock(text="Resposta inválida sem JSON")]
            )
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
                data=[{
                    "out_hospital_id": hospital_id,
                    "out_nome": "Hospital ABC",
                    "out_foi_criado": True,
                }]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_criar_com_dados_completos(self, mock_supabase):
        """Deve criar hospital com todos os dados via RPC."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9
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

        info = InfoHospitalWeb(
            nome_oficial="Hospital XYZ",
            confianca=0.5
        )

        resultado = await criar_hospital(info, "XYZ")

        assert resultado is not None


class TestCriarHospitalMinimo:
    """Testes da criação mínima (via RPC — Sprint 60)."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[{
                    "out_hospital_id": hospital_id,
                    "out_nome": "Hospital Novo",
                    "out_foi_criado": True,
                }]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_criar_com_regiao(self, mock_supabase):
        """Deve criar hospital inferindo cidade da região via RPC."""
        mock, hospital_id = mock_supabase

        resultado = await criar_hospital_minimo("Hospital Novo", "ABC")

        assert resultado is not None

    @pytest.mark.asyncio
    async def test_criar_sem_regiao(self, mock_supabase):
        """Deve criar hospital sem cidade se região desconhecida via RPC."""
        mock, hospital_id = mock_supabase

        resultado = await criar_hospital_minimo("Hospital Novo", "")

        assert resultado is not None


class TestNormalizarOuCriarHospital:
    """Testes da função principal."""

    @pytest.fixture
    def mock_normalizador(self):
        """Mock das funções do normalizador."""
        with patch("app.services.grupos.normalizador.buscar_hospital_por_alias") as alias, \
             patch("app.services.grupos.normalizador.buscar_hospital_por_similaridade") as sim:
            yield alias, sim

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase com RPC."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.rpc.return_value.execute.return_value = MagicMock(
                data=[{
                    "out_hospital_id": hospital_id,
                    "out_nome": "Hospital ABC",
                    "out_foi_criado": True,
                }]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_encontra_alias_exato(self, mock_normalizador, mock_supabase):
        """Deve retornar match de alias exato."""
        alias_mock, sim_mock = mock_normalizador

        from app.services.grupos.normalizador import ResultadoMatch

        alias_mock.return_value = ResultadoMatch(
            entidade_id=uuid4(),
            nome="Hospital ABC",
            score=1.0,
            fonte="alias_exato"
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
            entidade_id=uuid4(),
            nome="Hospital ABC",
            score=0.85,
            fonte="nome_similar"
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
            hospital_id=uuid4(),
            nome="Hospital ABC",
            score=0.9,
            foi_criado=True,
            fonte="web"
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
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("Erro")

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
        info = InfoCNES(
            cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.95
        )

        result = cnes_to_info_web(info)

        assert result.confianca == 1.0

    def test_confianca_soma_correta(self):
        """Deve somar 0.2 ao score CNES."""
        info = InfoCNES(
            cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.5
        )

        result = cnes_to_info_web(info)

        assert result.confianca == 0.7

    def test_google_place_id_none(self):
        """Deve ter google_place_id como None."""
        info = InfoCNES(
            cnes_codigo="123", nome_oficial="H", cidade="SP", estado="SP", score=0.5
        )

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
        info = InfoGooglePlaces(
            place_id="abc", nome="H", endereco_formatado="", confianca=0.5
        )

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
                data=[{
                    "out_hospital_id": hospital_id,
                    "out_nome": "Hospital CNES",
                    "out_foi_criado": True,
                }]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
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
        update_calls = [
            c for c in mock.table.return_value.update.call_args_list
        ]
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

        update_calls = [
            c for c in mock.table.return_value.update.call_args_list
        ]
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
        with patch("app.services.grupos.normalizador.buscar_hospital_por_alias", return_value=None) as alias, \
             patch("app.services.grupos.normalizador.buscar_hospital_por_similaridade", return_value=None) as sim:
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
                data=[{
                    "out_hospital_id": hospital_id,
                    "out_nome": "Hospital Via CNES",
                    "out_foi_criado": True,
                }]
            )
            mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
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

        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=cnes_low,
        ), patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=google_info,
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

        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=google_low,
        ), patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=llm_info,
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital XYZ", "SP")

        assert resultado is not None
        assert resultado.fonte == "web"

    @pytest.mark.asyncio
    async def test_pipeline_cnes_erro_nao_bloqueia(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Erro no CNES não deve bloquear pipeline — continua para Google/LLM."""
        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            side_effect=Exception("CNES falhou"),
        ), patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Erro", "SP")

        # Deve chegar até o fallback sem explodir
        assert resultado is not None
        assert resultado.fonte == "fallback"

    @pytest.mark.asyncio
    async def test_pipeline_google_erro_nao_bloqueia(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Erro no Google não deve bloquear pipeline — continua para LLM."""
        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            side_effect=Exception("Google falhou"),
        ), patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Erro", "SP")

        assert resultado is not None
        assert resultado.fonte == "fallback"

    @pytest.mark.asyncio
    async def test_pipeline_sem_cnes_sem_google_usa_llm(
        self, mock_normalizador, mock_validador, mock_supabase, mock_emit
    ):
        """Pipeline completo: CNES vazio + Google vazio → LLM fallback."""
        with patch(
            "app.services.grupos.hospital_cnes.buscar_hospital_cnes",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_google_places.buscar_hospital_google_places",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.grupos.hospital_web.buscar_hospital_web",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resultado = await normalizar_ou_criar_hospital("Hospital Teste", "SP")

        assert resultado is not None
        assert resultado.fonte == "fallback"
