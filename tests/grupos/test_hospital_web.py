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
)


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
    """Testes da criação de hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": hospital_id}]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_criar_com_dados_completos(self, mock_supabase):
        """Deve criar hospital com todos os dados."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital ABC",
            cidade="São Paulo",
            estado="SP",
            confianca=0.9
        )

        resultado = await criar_hospital(info, "HSL ABC")

        assert resultado is not None
        # Verifica que chamou insert na tabela hospitais
        mock.table.assert_called()

    @pytest.mark.asyncio
    async def test_criar_com_dados_minimos(self, mock_supabase):
        """Deve criar hospital com dados mínimos."""
        mock, hospital_id = mock_supabase

        info = InfoHospitalWeb(
            nome_oficial="Hospital XYZ",
            confianca=0.5
        )

        resultado = await criar_hospital(info, "XYZ")

        assert resultado is not None


class TestCriarHospitalMinimo:
    """Testes da criação mínima."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": hospital_id}]
            )
            yield mock, hospital_id

    @pytest.mark.asyncio
    async def test_criar_com_regiao(self, mock_supabase):
        """Deve criar hospital inferindo cidade da região."""
        mock, hospital_id = mock_supabase

        resultado = await criar_hospital_minimo("Hospital Novo", "ABC")

        assert resultado is not None

    @pytest.mark.asyncio
    async def test_criar_sem_regiao(self, mock_supabase):
        """Deve criar hospital sem cidade se região desconhecida."""
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
        """Mock do Supabase."""
        with patch("app.services.grupos.hospital_web.supabase") as mock:
            hospital_id = str(uuid4())
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": hospital_id}]
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
