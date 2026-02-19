"""
Testes para o normalizador de entidades.

Sprint 14 - E06 - Fuzzy Match
"""

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock

from app.services.grupos.normalizador import (
    normalizar_para_busca,
    extrair_tokens,
    extrair_qualificador,
    expandir_abreviacoes_hospital,
    buscar_hospital_por_alias,
    buscar_hospital_por_similaridade,
    normalizar_hospital,
    buscar_especialidade_por_alias,
    normalizar_especialidade,
    normalizar_periodo,
    normalizar_setor,
    normalizar_tipo_vaga,
    normalizar_forma_pagamento,
    normalizar_vaga,
    ResultadoMatch,
    ResultadoNormalizacao,
    MAPA_PERIODOS,
    MAPA_SETORES,
    MAPA_TIPOS_VAGA,
    MAPA_FORMAS_PAGAMENTO,
)


class TestNormalizarParaBusca:
    """Testes de normalização de texto."""

    def test_lowercase(self):
        """Deve converter para minúsculas."""
        assert normalizar_para_busca("HOSPITAL ABC") == "hospital abc"

    def test_remove_acentos(self):
        """Deve remover acentos."""
        assert normalizar_para_busca("São Luíz") == "sao luiz"
        assert normalizar_para_busca("Cirúrgico") == "cirurgico"

    def test_remove_caracteres_especiais(self):
        """Deve remover caracteres especiais."""
        assert normalizar_para_busca("Hospital - ABC") == "hospital abc"
        assert normalizar_para_busca("H.S.L.") == "hsl"

    def test_remove_espacos_extras(self):
        """Deve remover espaços extras."""
        assert normalizar_para_busca("Hospital   ABC") == "hospital abc"
        assert normalizar_para_busca("  Hospital  ") == "hospital"

    def test_texto_vazio(self):
        """Deve retornar vazio para entrada vazia."""
        assert normalizar_para_busca("") == ""
        assert normalizar_para_busca(None) == ""

    def test_caso_complexo(self):
        """Deve normalizar caso complexo."""
        assert normalizar_para_busca("Hosp. São Luiz - ABC") == "hosp sao luiz abc"


class TestExtrairTokens:
    """Testes de extração de tokens."""

    def test_extrai_tokens(self):
        """Deve extrair tokens."""
        tokens = extrair_tokens("Hospital São Luiz")
        assert "hospital" in tokens
        assert "sao" in tokens
        assert "luiz" in tokens

    def test_remove_stopwords(self):
        """Deve remover stopwords."""
        tokens = extrair_tokens("Hospital de São Paulo")
        assert "de" not in tokens
        assert "hospital" in tokens

    def test_texto_vazio(self):
        """Deve retornar set vazio."""
        assert extrair_tokens("") == set()


class TestMapasNormalizacao:
    """Testes dos mapas de normalização."""

    def test_mapa_periodos(self):
        """Verifica mapa de períodos."""
        assert MAPA_PERIODOS["noturno"] == "Noturno"
        assert MAPA_PERIODOS["diurno"] == "Diurno"
        assert MAPA_PERIODOS["sn"] == "Noturno"
        assert MAPA_PERIODOS["sd"] == "Diurno"

    def test_mapa_setores(self):
        """Verifica mapa de setores."""
        assert MAPA_SETORES["ps"] == "Pronto atendimento"
        assert MAPA_SETORES["uti"] == "Hospital"
        assert MAPA_SETORES["cc"] == "C. Cirúrgico"

    def test_mapa_tipos_vaga(self):
        """Verifica mapa de tipos."""
        assert MAPA_TIPOS_VAGA["cobertura"] == "Cobertura"
        assert MAPA_TIPOS_VAGA["fixo"] == "Fixo"

    def test_mapa_formas_pagamento(self):
        """Verifica mapa de pagamento."""
        assert MAPA_FORMAS_PAGAMENTO["pj"] == "Pessoa jurídica"
        assert MAPA_FORMAS_PAGAMENTO["pf"] == "Pessoa fisica"


class TestBuscarHospitalPorAlias:
    """Testes de busca por alias de hospital."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_alias_encontrado(self, mock_supabase):
        """Deve retornar match quando alias existe."""
        hospital_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"hospital_id": hospital_id, "hospitais": {"nome": "Hospital São Luiz"}}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"vezes_usado": 5}
        )

        resultado = await buscar_hospital_por_alias("HSL")

        assert resultado is not None
        assert resultado.nome == "Hospital São Luiz"
        assert resultado.score == 1.0
        assert resultado.fonte == "alias_exato"

    @pytest.mark.asyncio
    async def test_alias_nao_encontrado(self, mock_supabase):
        """Deve retornar None quando alias não existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        resultado = await buscar_hospital_por_alias("XPTO")

        assert resultado is None

    @pytest.mark.asyncio
    async def test_texto_vazio(self, mock_supabase):
        """Deve retornar None para texto vazio."""
        resultado = await buscar_hospital_por_alias("")
        assert resultado is None


class TestBuscarHospitalPorSimilaridade:
    """Testes de busca por similaridade."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_similaridade_encontrada(self, mock_supabase):
        """Deve retornar match com score."""
        hospital_id = str(uuid4())
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "hospital_id": hospital_id,
                    "nome": "Hospital São Luiz",
                    "score": 0.85,
                    "fonte": "alias",
                }
            ]
        )

        resultado = await buscar_hospital_por_similaridade("sao luiz")

        assert resultado is not None
        assert resultado.score == 0.85
        assert resultado.fonte == "alias_similar"

    @pytest.mark.asyncio
    async def test_similaridade_abaixo_threshold(self, mock_supabase):
        """Deve retornar None quando score baixo."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data=[{"hospital_id": str(uuid4()), "nome": "Hospital", "score": 0.2, "fonte": "nome"}]
        )

        resultado = await buscar_hospital_por_similaridade("xyz", threshold=0.3)

        assert resultado is None


class TestNormalizarHospital:
    """Testes da função principal de normalização."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_prioriza_alias_exato(self, mock_supabase):
        """Deve priorizar alias exato sobre similaridade."""
        hospital_id = str(uuid4())
        # Mock para alias exato
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"hospital_id": hospital_id, "hospitais": {"nome": "Hospital ABC"}}]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"vezes_usado": 1}
        )

        resultado = await normalizar_hospital("ABC")

        assert resultado is not None
        assert resultado.score == 1.0
        assert resultado.fonte == "alias_exato"


class TestNormalizarEspecialidade:
    """Testes de normalização de especialidade."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_alias_exato(self, mock_supabase):
        """Deve encontrar especialidade por alias."""
        esp_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"especialidade_id": esp_id, "especialidades": {"nome": "Clínica Médica"}}]
        )

        resultado = await buscar_especialidade_por_alias("CM")

        assert resultado is not None
        assert resultado.nome == "Clínica Médica"


class TestNormalizarPeriodo:
    """Testes de normalização de período."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_periodo_noturno(self, mock_supabase):
        """Deve normalizar período noturno."""
        periodo_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": periodo_id}]
        )

        resultado = await normalizar_periodo("plantão noturno")

        assert resultado is not None

    @pytest.mark.asyncio
    async def test_periodo_vazio(self, mock_supabase):
        """Deve retornar None para vazio."""
        resultado = await normalizar_periodo("")
        assert resultado is None

    @pytest.mark.asyncio
    async def test_periodo_desconhecido(self, mock_supabase):
        """Deve retornar None para período desconhecido."""
        resultado = await normalizar_periodo("xyz123")
        assert resultado is None


class TestNormalizarSetor:
    """Testes de normalização de setor."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_setor_ps(self, mock_supabase):
        """Deve normalizar PS para Pronto atendimento."""
        setor_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": setor_id}]
        )

        resultado = await normalizar_setor("PS")

        assert resultado is not None

    @pytest.mark.asyncio
    async def test_setor_uti(self, mock_supabase):
        """Deve normalizar UTI para Hospital."""
        setor_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": setor_id}]
        )

        resultado = await normalizar_setor("UTI")

        assert resultado is not None


class TestNormalizarVaga:
    """Testes do processador de normalização."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_vaga_nao_encontrada(self, mock_supabase):
        """Deve retornar erro quando vaga não existe."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        resultado = await normalizar_vaga(uuid4())

        assert resultado.status == "erro"
        assert resultado.motivo_status == "vaga_nao_encontrada"

    @pytest.mark.asyncio
    async def test_vaga_normalizada_completa(self, mock_supabase):
        """Deve normalizar vaga com todos os campos."""
        vaga_id = uuid4()
        hospital_id = str(uuid4())
        esp_id = str(uuid4())

        # Mock da vaga
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": str(vaga_id),
                "hospital_raw": "Hospital ABC",
                "especialidade_raw": "Cardiologia",
                "periodo_raw": "noturno",
            }
        )

        # Mock do hospital - alias exato
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"hospital_id": hospital_id, "hospitais": {"nome": "Hospital ABC"}}]
        )

        # Mock do update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Simular match para atualizar vezes_usado
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"vezes_usado": 1}
        )

        resultado = await normalizar_vaga(vaga_id)

        # Verifica que tentou atualizar a vaga
        mock_supabase.table.assert_called()


class TestResultadoMatch:
    """Testes da dataclass ResultadoMatch."""

    def test_criacao(self):
        """Deve criar resultado corretamente."""
        resultado = ResultadoMatch(
            entidade_id=uuid4(), nome="Hospital ABC", score=0.95, fonte="alias_exato"
        )

        assert resultado.nome == "Hospital ABC"
        assert resultado.score == 0.95
        assert resultado.fonte == "alias_exato"


class TestResultadoNormalizacao:
    """Testes da dataclass ResultadoNormalizacao."""

    def test_valores_default(self):
        """Deve ter valores default corretos."""
        resultado = ResultadoNormalizacao()

        assert resultado.hospital_id is None
        assert resultado.hospital_score == 0.0
        assert resultado.status == "pendente"

    def test_valores_preenchidos(self):
        """Deve aceitar valores."""
        hospital_id = uuid4()
        resultado = ResultadoNormalizacao(
            hospital_id=hospital_id,
            hospital_nome="Hospital ABC",
            hospital_score=0.9,
            status="normalizada",
        )

        assert resultado.hospital_id == hospital_id
        assert resultado.status == "normalizada"


# =============================================================================
# Sprint 63 - Testes de Expansão de Abreviações
# =============================================================================


class TestExpandirAbreviacoesHospital:
    """Testes da expansão de abreviações de hospital."""

    def test_h_ponto_para_hospital(self):
        """H. deve expandir para hospital."""
        assert (
            expandir_abreviacoes_hospital("H. BENEDICTO MONTENEGRO")
            == "hospital BENEDICTO MONTENEGRO"
        )

    def test_h_sem_ponto_para_hospital(self):
        """H sem ponto deve expandir para hospital."""
        assert expandir_abreviacoes_hospital("H BENEDICTO") == "hospital BENEDICTO"

    def test_hm_para_hospital_municipal(self):
        """HM deve expandir para hospital municipal."""
        assert (
            expandir_abreviacoes_hospital("HM Dr. José Silva")
            == "hospital municipal doutor José Silva"
        )

    def test_hr_para_hospital_regional(self):
        """HR deve expandir para hospital regional."""
        assert expandir_abreviacoes_hospital("HR. Mário Gatti") == "hospital regional Mário Gatti"

    def test_upa_nao_altera(self):
        """UPA não deve ser alterado (nome próprio)."""
        assert expandir_abreviacoes_hospital("UPA VERGUEIRO") == "UPA VERGUEIRO"

    def test_santa_casa_nao_altera(self):
        """Santa Casa não abreviada não deve mudar."""
        assert expandir_abreviacoes_hospital("Santa Casa") == "Santa Casa"

    def test_sta_para_santa(self):
        """STA. deve expandir para santa."""
        assert expandir_abreviacoes_hospital("STA. Casa de Sao Paulo") == "santa Casa de Sao Paulo"

    def test_dr_para_doutor(self):
        """Dr. deve expandir para doutor."""
        assert expandir_abreviacoes_hospital("Dr. Benedicto") == "doutor Benedicto"

    def test_prof_para_professor(self):
        """Prof. deve expandir para professor."""
        assert expandir_abreviacoes_hospital("Prof. Almeida") == "professor Almeida"

    def test_texto_sem_abreviacoes(self):
        """Texto sem abreviações não deve mudar."""
        assert expandir_abreviacoes_hospital("Hospital Sao Paulo") == "Hospital Sao Paulo"

    def test_texto_vazio(self):
        """Texto vazio deve retornar vazio."""
        assert expandir_abreviacoes_hospital("") == ""

    def test_texto_none(self):
        """None deve retornar None."""
        assert expandir_abreviacoes_hospital(None) is None


class TestExtrairQualificador:
    """Testes da extração de qualificador entre parênteses."""

    def test_qualificador_iva(self):
        """Deve extrair IVA."""
        assert extrair_qualificador("H. BENEDICTO MONTENEGRO (IVA)") == "iva"

    def test_qualificador_sede(self):
        """Deve extrair SEDE."""
        assert extrair_qualificador("Hospital Sao Paulo (SEDE)") == "sede"

    def test_qualificador_24h(self):
        """Deve extrair 24h."""
        assert extrair_qualificador("UPA (24h)") == "24h"

    def test_sem_qualificador(self):
        """Deve retornar None sem parênteses."""
        assert extrair_qualificador("Hospital Sao Paulo") is None

    def test_texto_vazio(self):
        """Deve retornar None para vazio."""
        assert extrair_qualificador("") is None

    def test_texto_none(self):
        """Deve retornar None para None."""
        assert extrair_qualificador(None) is None


class TestNormalizacaoIntegradaAbreviacoes:
    """Testes que verificam que abreviações funcionam na cadeia completa."""

    def test_h_ponto_normalizado_para_busca(self):
        """H. BENEDICTO MONTENEGRO (IVA) deve virar 'hospital benedicto montenegro'."""
        expandido = expandir_abreviacoes_hospital("H. BENEDICTO MONTENEGRO (IVA)")
        normalizado = normalizar_para_busca(expandido)
        assert normalizado == "hospital benedicto montenegro"

    def test_hm_dr_normalizado(self):
        """HM Dr. José Silva deve virar 'hospital municipal doutor jose silva'."""
        expandido = expandir_abreviacoes_hospital("HM Dr. José Silva")
        normalizado = normalizar_para_busca(expandido)
        assert normalizado == "hospital municipal doutor jose silva"

    def test_sta_casa_normalizado(self):
        """STA. CASA DE SÃO PAULO deve virar 'santa casa de sao paulo'."""
        expandido = expandir_abreviacoes_hospital("STA. CASA DE SÃO PAULO")
        normalizado = normalizar_para_busca(expandido)
        assert normalizado == "santa casa de sao paulo"

    @pytest.fixture
    def mock_supabase(self):
        """Mock do Supabase."""
        with patch("app.services.grupos.normalizador.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_busca_alias_expande_abreviacoes(self, mock_supabase):
        """buscar_hospital_por_alias deve expandir H. para hospital antes de buscar."""
        hospital_id = str(uuid4())
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"hospital_id": hospital_id, "hospitais": {"nome": "Hospital Benedicto Montenegro"}}
            ]
        )

        resultado = await buscar_hospital_por_alias("H. BENEDICTO MONTENEGRO (IVA)")

        assert resultado is not None
        assert resultado.nome == "Hospital Benedicto Montenegro"
        # Verifica que buscou com texto expandido/normalizado
        mock_supabase.table.return_value.select.return_value.eq.assert_called_with(
            "alias_normalizado", "hospital benedicto montenegro"
        )
