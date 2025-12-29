"""
Testes para o importador de vagas.

Sprint 14 - E09 - Importação Automática
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock

from app.services.grupos.importador import (
    calcular_confianca_geral,
    validar_para_importacao,
    criar_vaga_principal,
    atualizar_vaga_grupo_importada,
    decidir_acao,
    aplicar_acao,
    processar_importacao,
    processar_batch_importacao,
    listar_vagas_para_revisao,
    aprovar_vaga_revisao,
    rejeitar_vaga_revisao,
    obter_estatisticas_importacao,
    ScoreConfianca,
    ResultadoValidacao,
    ResultadoImportacao,
    AcaoImportacao,
    THRESHOLD_IMPORTAR,
    THRESHOLD_REVISAR,
)


class TestCalcularConfiancaGeral:
    """Testes do cálculo de confiança."""

    def test_confianca_alta(self):
        """Vaga com todos os scores altos deve ter confiança alta."""
        vaga = {
            "hospital_match_score": 1.0,
            "especialidade_match_score": 1.0,
            "data": "2024-12-28",
            "confianca_data": 0.9,
            "periodo_id": str(uuid4()),
            "valor": 1500,
        }

        score = calcular_confianca_geral(vaga)

        assert score.geral >= 0.9
        assert score.hospital == 1.0
        assert score.especialidade == 1.0

    def test_confianca_media(self):
        """Vaga com scores médios deve ter confiança média."""
        vaga = {
            "hospital_match_score": 0.8,
            "especialidade_match_score": 0.7,
            "data": "2024-12-28",
            "confianca_data": 0.8,
            "periodo_id": None,
            "valor": None,
        }

        score = calcular_confianca_geral(vaga)

        assert 0.5 < score.geral < 0.9

    def test_confianca_baixa(self):
        """Vaga com scores baixos deve ter confiança baixa."""
        vaga = {
            "hospital_match_score": 0.3,
            "especialidade_match_score": 0.3,
            "data": None,
            "periodo_id": None,
            "valor": None,
        }

        score = calcular_confianca_geral(vaga)

        assert score.geral < 0.5

    def test_pesos_corretos(self):
        """Deve aplicar pesos corretos."""
        # Só hospital 100%, resto 0
        vaga = {
            "hospital_match_score": 1.0,
            "especialidade_match_score": 0.0,
            "data": None,
            "periodo_id": None,
            "valor": None,
        }

        score = calcular_confianca_geral(vaga)

        # Hospital = 30%, período sem ID = 5%, valor sem = 1.5%
        assert 0.30 <= score.geral <= 0.40

    def test_detalhes_preenchidos(self):
        """Deve preencher detalhes."""
        vaga = {
            "hospital_match_score": 0.9,
            "especialidade_match_score": 0.8,
        }

        score = calcular_confianca_geral(vaga)

        assert "hospital" in score.detalhes
        assert "especialidade" in score.detalhes
        assert score.detalhes["hospital"] == 0.9

    def test_valor_fora_range(self):
        """Valor fixo fora do range normal deve ter score menor."""
        # Sprint 19: precisa especificar valor_tipo para teste de range
        vaga_normal = {"valor_tipo": "fixo", "valor": 1500}
        vaga_alto = {"valor_tipo": "fixo", "valor": 50000}

        score_normal = calcular_confianca_geral(vaga_normal)
        score_alto = calcular_confianca_geral(vaga_alto)

        # valor=1500 está no range (100-10000), score=1.0
        # valor=50000 está fora do range, score=0.3
        assert score_normal.valor > score_alto.valor
        assert score_normal.valor == 1.0
        assert score_alto.valor == 0.3

    def test_valor_tipo_a_combinar(self):
        """Valor a combinar deve ter score aceitável (Sprint 19)."""
        vaga = {"valor_tipo": "a_combinar"}
        score = calcular_confianca_geral(vaga)
        assert score.valor == 0.7
        assert score.detalhes["valor_tipo"] == "a_combinar"

    def test_valor_tipo_faixa_com_limites(self):
        """Valor em faixa com limites deve ter bom score (Sprint 19)."""
        vaga = {"valor_tipo": "faixa", "valor_minimo": 1500, "valor_maximo": 2000}
        score = calcular_confianca_geral(vaga)
        assert score.valor == 0.9

    def test_valor_tipo_faixa_sem_limites(self):
        """Valor em faixa sem limites é inconsistente (Sprint 19)."""
        vaga = {"valor_tipo": "faixa"}  # Sem valor_minimo nem valor_maximo
        score = calcular_confianca_geral(vaga)
        assert score.valor == 0.3  # Inconsistente


class TestValidarParaImportacao:
    """Testes de validação."""

    def test_vaga_valida(self):
        """Vaga com todos os campos deve ser válida."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": amanha,
            "periodo_id": str(uuid4()),
            "valor": 1500,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True
        assert len(resultado.erros) == 0

    def test_sem_hospital(self):
        """Sem hospital deve ser inválida."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "especialidade_id": str(uuid4()),
            "data": amanha,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is False
        assert "hospital_id ausente" in resultado.erros

    def test_sem_especialidade(self):
        """Sem especialidade deve ser inválida."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "data": amanha,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is False
        assert "especialidade_id ausente" in resultado.erros

    def test_sem_data(self):
        """Sem data deve ser inválida."""
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is False
        assert "data ausente" in resultado.erros

    def test_data_passada(self):
        """Data passada deve ser inválida."""
        ontem = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": ontem,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is False
        assert "data no passado" in resultado.erros

    def test_data_distante_aviso(self):
        """Data muito distante deve gerar aviso."""
        futuro = (datetime.now(UTC) + timedelta(days=100)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": futuro,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True  # Não bloqueia
        assert any("distante" in a for a in resultado.avisos)

    def test_sem_periodo_aviso(self):
        """Sem período deve gerar aviso mas ser válida."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": amanha,
            "periodo_id": None,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True
        assert any("período" in a for a in resultado.avisos)

    def test_valor_tipo_fixo_sem_valor_aviso(self):
        """valor_tipo=fixo sem valor deve gerar aviso (Sprint 19)."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": amanha,
            "valor_tipo": "fixo",
            "valor": None,
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True  # Não bloqueia
        assert any("fixo" in a for a in resultado.avisos)

    def test_valor_tipo_faixa_sem_limites_aviso(self):
        """valor_tipo=faixa sem limites deve gerar aviso (Sprint 19)."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": amanha,
            "valor_tipo": "faixa",
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True  # Não bloqueia
        assert any("faixa" in a for a in resultado.avisos)

    def test_valor_tipo_a_combinar_sem_aviso(self):
        """valor_tipo=a_combinar não deve gerar aviso (Sprint 19)."""
        amanha = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
        vaga = {
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": amanha,
            "valor_tipo": "a_combinar",
        }

        resultado = validar_para_importacao(vaga)

        assert resultado.valido is True
        # Não deve ter aviso de valor
        assert not any("valor" in a.lower() for a in resultado.avisos)


class TestDecidirAcao:
    """Testes de decisão de ação."""

    def test_importar_confianca_alta(self):
        """Confiança >= 90% deve importar."""
        score = ScoreConfianca(geral=0.95)
        validacao = ResultadoValidacao(valido=True)

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.IMPORTAR

    def test_revisar_confianca_media(self):
        """Confiança 70-90% deve revisar."""
        score = ScoreConfianca(geral=0.80)
        validacao = ResultadoValidacao(valido=True)

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.REVISAR

    def test_descartar_confianca_baixa(self):
        """Confiança < 70% deve descartar."""
        score = ScoreConfianca(geral=0.50)
        validacao = ResultadoValidacao(valido=True)

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.DESCARTAR

    def test_descartar_invalido(self):
        """Vaga inválida deve descartar independente do score."""
        score = ScoreConfianca(geral=0.99)
        validacao = ResultadoValidacao(valido=False, erros=["data ausente"])

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.DESCARTAR

    def test_threshold_exato_importar(self):
        """Score exatamente 0.90 deve importar."""
        score = ScoreConfianca(geral=0.90)
        validacao = ResultadoValidacao(valido=True)

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.IMPORTAR

    def test_threshold_exato_revisar(self):
        """Score exatamente 0.70 deve revisar."""
        score = ScoreConfianca(geral=0.70)
        validacao = ResultadoValidacao(valido=True)

        acao = decidir_acao(score, validacao)

        assert acao == AcaoImportacao.REVISAR


class TestCriarVagaPrincipal:
    """Testes de criação de vaga."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            vaga_id = str(uuid4())
            mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": vaga_id}]
            )
            yield mock, vaga_id

    @pytest.mark.asyncio
    async def test_criar_vaga(self, mock_supabase):
        """Deve criar vaga com campos mapeados."""
        mock, vaga_id = mock_supabase

        vaga_grupo = {
            "id": str(uuid4()),
            "hospital_id": str(uuid4()),
            "especialidade_id": str(uuid4()),
            "data": "2024-12-28",
            "periodo_id": str(uuid4()),
            "valor": 1500,
        }

        resultado = await criar_vaga_principal(vaga_grupo)

        assert resultado is not None
        mock.table.return_value.insert.assert_called_once()


class TestAtualizarVagaGrupoImportada:
    """Testes de atualização de status."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_atualizar_status(self, mock_supabase):
        """Deve atualizar status para importada."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        await atualizar_vaga_grupo_importada(uuid4(), uuid4())

        mock_supabase.table.return_value.update.assert_called_once()
        call_args = mock_supabase.table.return_value.update.call_args[0][0]
        assert call_args["status"] == "importada"


class TestProcessarImportacao:
    """Testes do processador."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_nao_encontrada(self, mock_supabase):
        """Deve retornar erro se vaga não existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        resultado = await processar_importacao(uuid4())

        assert resultado.erro == "vaga_nao_encontrada"

    @pytest.mark.asyncio
    async def test_vaga_ja_processada(self, mock_supabase):
        """Deve retornar erro se vaga já processada."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"status": "importada"}
        )

        resultado = await processar_importacao(uuid4())

        assert resultado.erro == "vaga_ja_processada"

    @pytest.mark.asyncio
    async def test_vaga_duplicada(self, mock_supabase):
        """Deve retornar erro se vaga é duplicada."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"status": "nova", "eh_duplicada": True}
        )

        resultado = await processar_importacao(uuid4())

        assert resultado.erro == "vaga_duplicada"


class TestAcaoImportacao:
    """Testes do enum AcaoImportacao."""

    def test_valores(self):
        """Deve ter valores corretos."""
        assert AcaoImportacao.IMPORTAR.value == "importar"
        assert AcaoImportacao.REVISAR.value == "revisar"
        assert AcaoImportacao.DESCARTAR.value == "descartar"


class TestScoreConfianca:
    """Testes da dataclass ScoreConfianca."""

    def test_valores_default(self):
        """Deve ter valores default corretos."""
        score = ScoreConfianca()

        assert score.hospital == 0.0
        assert score.geral == 0.0
        assert score.detalhes == {}

    def test_valores_preenchidos(self):
        """Deve aceitar valores."""
        score = ScoreConfianca(
            hospital=0.9,
            especialidade=0.8,
            geral=0.85
        )

        assert score.hospital == 0.9
        assert score.geral == 0.85


class TestResultadoValidacao:
    """Testes da dataclass ResultadoValidacao."""

    def test_valido(self):
        """Deve criar resultado válido."""
        resultado = ResultadoValidacao(valido=True)

        assert resultado.valido is True
        assert resultado.erros == []

    def test_invalido(self):
        """Deve criar resultado inválido."""
        resultado = ResultadoValidacao(
            valido=False,
            erros=["campo ausente"]
        )

        assert resultado.valido is False
        assert len(resultado.erros) == 1


class TestResultadoImportacao:
    """Testes da dataclass ResultadoImportacao."""

    def test_criacao(self):
        """Deve criar resultado corretamente."""
        resultado = ResultadoImportacao(
            vaga_grupo_id=str(uuid4()),
            acao="importar",
            score=0.95,
            status="importada",
            vaga_id=str(uuid4())
        )

        assert resultado.acao == "importar"
        assert resultado.status == "importada"


class TestThresholds:
    """Testes dos thresholds."""

    def test_threshold_importar(self):
        """Threshold de importação deve ser 90%."""
        assert THRESHOLD_IMPORTAR == 0.90

    def test_threshold_revisar(self):
        """Threshold de revisão deve ser 70%."""
        assert THRESHOLD_REVISAR == 0.70


class TestListarVagasParaRevisao:
    """Testes de listagem para revisão."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_lista_vagas(self, mock_supabase):
        """Deve listar vagas em revisão."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}, {"id": str(uuid4())}]
        )

        resultado = await listar_vagas_para_revisao()

        assert len(resultado) == 2


class TestAprovarVagaRevisao:
    """Testes de aprovação."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_aprovar_vaga(self, mock_supabase):
        """Deve aprovar e importar vaga."""
        vaga_id = str(uuid4())

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(uuid4()),
                "status": "aguardando_revisao",
                "hospital_id": str(uuid4()),
                "especialidade_id": str(uuid4()),
                "data": "2024-12-28",
            }
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": vaga_id}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await aprovar_vaga_revisao(uuid4(), "admin")

        assert resultado.get("status") == "importada"


class TestRejectarVagaRevisao:
    """Testes de rejeição."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.importador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_rejeitar_vaga(self, mock_supabase):
        """Deve rejeitar vaga."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        resultado = await rejeitar_vaga_revisao(uuid4(), "dados incorretos", "admin")

        assert resultado["status"] == "rejeitada"
        assert resultado["motivo"] == "dados incorretos"
