"""
Testes do pipeline de processamento de grupos.

Sprint 14 - E11 - Worker e Orquestração
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

from app.services.grupos.pipeline_worker import (
    PipelineGrupos,
    ResultadoPipeline,
    mapear_acao_para_estagio,
    THRESHOLD_HEURISTICA,
    THRESHOLD_HEURISTICA_ALTO,
    THRESHOLD_LLM,
)
from app.services.grupos.heuristica import ResultadoHeuristica
from app.services.grupos.classificador_llm import ResultadoClassificacaoLLM
from app.services.grupos.extrator import ResultadoExtracao, VagaExtraida, DadosVagaExtraida, ConfiancaExtracao
from app.services.grupos.normalizador import ResultadoNormalizacao
from app.services.grupos.deduplicador import ResultadoDedup
from app.services.grupos.importador import ResultadoImportacao


# =============================================================================
# Testes de Constantes
# =============================================================================

class TestConstantes:
    """Testes das constantes de threshold."""

    def test_threshold_heuristica(self):
        """Threshold mínimo de heurística."""
        assert THRESHOLD_HEURISTICA == 0.25

    def test_threshold_heuristica_alto(self):
        """Threshold alto para pular LLM."""
        assert THRESHOLD_HEURISTICA_ALTO == 0.8

    def test_threshold_llm(self):
        """Threshold de confiança do LLM."""
        assert THRESHOLD_LLM == 0.7


# =============================================================================
# Testes do ResultadoPipeline
# =============================================================================

class TestResultadoPipeline:
    """Testes do dataclass ResultadoPipeline."""

    def test_criar_resultado_minimo(self):
        """Cria resultado com ação mínima."""
        resultado = ResultadoPipeline(acao="descartar")
        assert resultado.acao == "descartar"
        assert resultado.mensagem_id is None

    def test_criar_resultado_completo(self):
        """Cria resultado completo."""
        mensagem_id = uuid4()
        vaga_grupo_id = uuid4()

        resultado = ResultadoPipeline(
            acao="normalizar",
            mensagem_id=mensagem_id,
            vaga_grupo_id=vaga_grupo_id,
            motivo=None,
            score=0.85,
            confianca=0.92,
            vagas_criadas=["vaga1", "vaga2"],
            detalhes={"hospital": "São Luiz"}
        )

        assert resultado.mensagem_id == mensagem_id
        assert resultado.score == 0.85
        assert len(resultado.vagas_criadas) == 2


# =============================================================================
# Testes do mapear_acao_para_estagio
# =============================================================================

class TestMapearAcaoParaEstagio:
    """Testes do mapeamento de ações."""

    def test_mapear_descartar(self):
        """Descartar -> descartado."""
        assert mapear_acao_para_estagio("descartar") == "descartado"

    def test_mapear_classificar(self):
        """Classificar -> classificacao."""
        assert mapear_acao_para_estagio("classificar") == "classificacao"

    def test_mapear_extrair(self):
        """Extrair -> extracao."""
        assert mapear_acao_para_estagio("extrair") == "extracao"

    def test_mapear_normalizar(self):
        """Normalizar -> normalizacao."""
        assert mapear_acao_para_estagio("normalizar") == "normalizacao"

    def test_mapear_deduplicar(self):
        """Deduplicar -> deduplicacao."""
        assert mapear_acao_para_estagio("deduplicar") == "deduplicacao"

    def test_mapear_importar(self):
        """Importar -> importacao."""
        assert mapear_acao_para_estagio("importar") == "importacao"

    def test_mapear_finalizar(self):
        """Finalizar -> finalizado."""
        assert mapear_acao_para_estagio("finalizar") == "finalizado"

    def test_mapear_erro(self):
        """Erro -> erro."""
        assert mapear_acao_para_estagio("erro") == "erro"

    def test_mapear_desconhecido(self):
        """Ação desconhecida -> erro."""
        assert mapear_acao_para_estagio("desconhecido") == "erro"


# =============================================================================
# Testes do PipelineGrupos
# =============================================================================

class TestPipelineProcessarPendente:
    """Testes do estágio pendente."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_mensagem_nao_encontrada(self, pipeline):
        """Descarta se mensagem não encontrada."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            resultado = await pipeline.processar_pendente({"mensagem_id": str(mensagem_id)})

            assert resultado.acao == "descartar"
            assert resultado.motivo == "mensagem_nao_encontrada"

    @pytest.mark.asyncio
    async def test_mensagem_sem_texto(self, pipeline):
        """Descarta se mensagem sem texto."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "", "nome_grupo": "Teste"}
            )

            resultado = await pipeline.processar_pendente({"mensagem_id": str(mensagem_id)})

            assert resultado.acao == "descartar"
            assert resultado.motivo == "sem_texto"

    @pytest.mark.asyncio
    async def test_heuristica_baixa_descarta(self, pipeline):
        """Descarta se heurística baixa."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "Oi pessoal, tudo bem?", "nome_grupo": "Teste"}
            )

            with patch("app.services.grupos.pipeline_worker.calcular_score_heuristica") as mock_heuristica:
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=False,
                    score=0.1,
                    keywords_encontradas=[],
                    motivo_rejeicao="score_baixo"
                )

                resultado = await pipeline.processar_pendente({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "descartar"
                assert resultado.motivo == "heuristica_baixa"

    @pytest.mark.asyncio
    async def test_heuristica_alta_pula_llm(self, pipeline):
        """Score alto pula classificação LLM."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "Plantão dia 28/12 no Hospital São Luiz, R$ 1.800 noturno", "nome_grupo": "Vagas"}
            )

            with patch("app.services.grupos.pipeline_worker.calcular_score_heuristica") as mock_heuristica:
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=True,
                    score=0.9,
                    keywords_encontradas=["plantão", "hospital"],
                    motivo_rejeicao=None
                )

                resultado = await pipeline.processar_pendente({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "extrair"
                assert resultado.score == 0.9

    @pytest.mark.asyncio
    async def test_heuristica_media_vai_para_llm(self, pipeline):
        """Score médio vai para classificação LLM."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "Vaga disponível amanhã", "nome_grupo": "Vagas"}
            )

            with patch("app.services.grupos.pipeline_worker.calcular_score_heuristica") as mock_heuristica:
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=True,
                    score=0.5,
                    keywords_encontradas=["vaga"],
                    motivo_rejeicao=None
                )

                resultado = await pipeline.processar_pendente({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "classificar"
                assert resultado.score == 0.5


class TestPipelineProcessarClassificacao:
    """Testes do estágio classificação."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_classificacao_positiva(self, pipeline):
        """LLM confirma oferta."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "Plantão disponível", "nome_grupo": "Vagas", "nome_contato": "Dr."}
            )

            with patch("app.services.grupos.pipeline_worker.classificar_com_llm") as mock_llm:
                mock_llm.return_value = ResultadoClassificacaoLLM(
                    eh_oferta=True,
                    confianca=0.85,
                    motivo="Contém palavras-chave de oferta"
                )

                resultado = await pipeline.processar_classificacao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "extrair"
                assert resultado.confianca == 0.85

    @pytest.mark.asyncio
    async def test_classificacao_negativa(self, pipeline):
        """LLM rejeita como oferta."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"texto": "Bom dia pessoal", "nome_grupo": "Vagas", "nome_contato": "Fulano"}
            )

            with patch("app.services.grupos.pipeline_worker.classificar_com_llm") as mock_llm:
                mock_llm.return_value = ResultadoClassificacaoLLM(
                    eh_oferta=False,
                    confianca=0.2,
                    motivo="Cumprimento genérico"
                )

                resultado = await pipeline.processar_classificacao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "descartar"
                assert resultado.motivo == "nao_eh_oferta"


class TestPipelineProcessarExtracao:
    """Testes do estágio extração."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_extracao_sucesso(self, pipeline):
        """Extração bem-sucedida (usando v1 para teste)."""
        import os
        mensagem_id = uuid4()
        vaga_id = uuid4()

        # Force v1 extractor for this test (testes escritos para v1)
        with patch.dict(os.environ, {"EXTRATOR_V2_ENABLED": "false"}):
            with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
                # Mock busca mensagem
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={
                        "texto": "Plantão Hospital São Luiz",
                        "nome_grupo": "Vagas",
                        "regiao": "SP",
                        "nome_contato": "Escalista",
                        "grupo_id": str(uuid4())
                    }
                )

                # Mock criação vaga
                mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                    data=[{"id": str(vaga_id)}]
                )

                with patch("app.services.grupos.pipeline_worker.extrair_dados_mensagem") as mock_extrator:
                    mock_extrator.return_value = ResultadoExtracao(
                        vagas=[
                            VagaExtraida(
                                dados=DadosVagaExtraida(hospital="São Luiz", especialidade="Clínica"),
                                confianca=ConfiancaExtracao(hospital=0.9, especialidade=0.7)
                            )
                        ],
                        total_vagas=1
                    )

                    resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                    assert resultado.acao == "normalizar"
                    assert len(resultado.vagas_criadas) == 1

    @pytest.mark.asyncio
    async def test_extracao_falha(self, pipeline):
        """Extração sem vagas (usando v1 para teste)."""
        import os
        mensagem_id = uuid4()

        # Force v1 extractor for this test (testes escritos para v1)
        with patch.dict(os.environ, {"EXTRATOR_V2_ENABLED": "false"}):
            with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"texto": "Texto confuso", "nome_grupo": "Vagas"}
                )

                with patch("app.services.grupos.pipeline_worker.extrair_dados_mensagem") as mock_extrator:
                    mock_extrator.return_value = ResultadoExtracao(
                        vagas=[],
                        total_vagas=0
                    )

                    resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                    assert resultado.acao == "descartar"
                    assert resultado.motivo == "extracao_falhou"


class TestPipelineProcessarNormalizacao:
    """Testes do estágio normalização."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_normalizacao_sucesso(self, pipeline):
        """Normalização bem-sucedida."""
        vaga_grupo_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.normalizar_vaga") as mock_normalizar:
            mock_normalizar.return_value = ResultadoNormalizacao(
                hospital_id=uuid4(),
                hospital_nome="Hospital São Luiz",
                hospital_score=0.95,
                especialidade_id=uuid4(),
                especialidade_nome="Clínica Médica",
                especialidade_score=0.9,
                status="normalizada"
            )

            resultado = await pipeline.processar_normalizacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "deduplicar"

    @pytest.mark.asyncio
    async def test_normalizacao_sem_vaga_id(self, pipeline):
        """Erro se não tem vaga_grupo_id."""
        resultado = await pipeline.processar_normalizacao({})

        assert resultado.acao == "erro"
        assert resultado.motivo == "vaga_grupo_id_ausente"


class TestPipelineProcessarDeduplicacao:
    """Testes do estágio deduplicação."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_vaga_unica(self, pipeline):
        """Vaga não é duplicata."""
        vaga_grupo_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.processar_deduplicacao") as mock_dedup:
            mock_dedup.return_value = ResultadoDedup(
                duplicada=False,
                principal_id=None,
                hash_dedup="abc123"
            )

            resultado = await pipeline.processar_deduplicacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "importar"

    @pytest.mark.asyncio
    async def test_vaga_duplicata(self, pipeline):
        """Vaga é duplicata."""
        vaga_grupo_id = uuid4()
        vaga_principal_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.processar_deduplicacao") as mock_dedup:
            mock_dedup.return_value = ResultadoDedup(
                duplicada=True,
                principal_id=vaga_principal_id,
                hash_dedup="abc123"
            )

            resultado = await pipeline.processar_deduplicacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "finalizar"
            assert resultado.motivo == "duplicada"


class TestPipelineProcessarImportacao:
    """Testes do estágio importação."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_importacao_automatica(self, pipeline):
        """Importação automática."""
        vaga_grupo_id = uuid4()
        vaga_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.processar_importacao") as mock_importar:
            mock_importar.return_value = ResultadoImportacao(
                vaga_grupo_id=str(vaga_grupo_id),
                acao="importar",
                score=0.95,
                status="importada",
                vaga_id=str(vaga_id)
            )

            resultado = await pipeline.processar_importacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "finalizar"
            assert resultado.detalhes["vaga_id"] == str(vaga_id)

    @pytest.mark.asyncio
    async def test_importacao_revisao(self, pipeline):
        """Importação para revisão."""
        vaga_grupo_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.processar_importacao") as mock_importar:
            mock_importar.return_value = ResultadoImportacao(
                vaga_grupo_id=str(vaga_grupo_id),
                acao="revisar",
                score=0.65,
                status="aguardando_revisao",
                motivo="confianca_media"
            )

            resultado = await pipeline.processar_importacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "finalizar"
            assert resultado.detalhes["acao"] == "revisar"
