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
    AcaoPipeline,
    mapear_acao_para_estagio,
    THRESHOLD_HEURISTICA,
    THRESHOLD_HEURISTICA_ALTO,
    THRESHOLD_LLM,
    MAX_VAGAS_POR_MENSAGEM,
    PIPELINE_V3_ENABLED,
)
from app.services.grupos.heuristica import ResultadoHeuristica
from app.services.grupos.classificador_llm import ResultadoClassificacaoLLM
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    ResultadoExtracaoV2,
    DiaSemana,
    Periodo,
)
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


class TestAcaoPipeline:
    """Testes do enum AcaoPipeline."""

    def test_str_enum_compatibilidade(self):
        """AcaoPipeline deve ser compatível com strings."""
        assert AcaoPipeline.DESCARTAR == "descartar"
        assert AcaoPipeline.CLASSIFICAR == "classificar"
        assert AcaoPipeline.EXTRAIR == "extrair"
        assert AcaoPipeline.NORMALIZAR == "normalizar"
        assert AcaoPipeline.DEDUPLICAR == "deduplicar"
        assert AcaoPipeline.IMPORTAR == "importar"
        assert AcaoPipeline.FINALIZAR == "finalizar"
        assert AcaoPipeline.ERRO == "erro"

    def test_mapeamento_com_enum(self):
        """mapear_acao_para_estagio deve funcionar com AcaoPipeline."""
        assert mapear_acao_para_estagio(AcaoPipeline.DESCARTAR) == "descartado"
        assert mapear_acao_para_estagio(AcaoPipeline.CLASSIFICAR) == "classificacao"
        assert mapear_acao_para_estagio(AcaoPipeline.EXTRAIR) == "extracao"
        assert mapear_acao_para_estagio(AcaoPipeline.NORMALIZAR) == "normalizacao"
        assert mapear_acao_para_estagio(AcaoPipeline.DEDUPLICAR) == "deduplicacao"
        assert mapear_acao_para_estagio(AcaoPipeline.IMPORTAR) == "importacao"
        assert mapear_acao_para_estagio(AcaoPipeline.FINALIZAR) == "finalizado"
        assert mapear_acao_para_estagio(AcaoPipeline.ERRO) == "erro"

    def test_mapeamento_com_string_backward_compat(self):
        """mapear_acao_para_estagio deve funcionar com strings puras."""
        assert mapear_acao_para_estagio("descartar") == "descartado"
        assert mapear_acao_para_estagio("extrair") == "extracao"

    def test_mapeamento_acao_desconhecida(self):
        """Ação desconhecida deve retornar 'erro'."""
        assert mapear_acao_para_estagio("acao_inventada") == "erro"


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
            detalhes={"hospital": "São Luiz"},
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

            with (
                patch(
                    "app.services.grupos.pipeline_worker.calcular_score_heuristica"
                ) as mock_heuristica,
                patch(
                    "app.services.grupos.pipeline_worker.atualizar_resultado_heuristica",
                    new_callable=AsyncMock,
                ),
            ):
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=False, score=0.1, keywords_encontradas=[], motivo_rejeicao="score_baixo"
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
                data={
                    "texto": "Plantão dia 28/12 no Hospital São Luiz, R$ 1.800 noturno",
                    "nome_grupo": "Vagas",
                }
            )

            with (
                patch(
                    "app.services.grupos.pipeline_worker.calcular_score_heuristica"
                ) as mock_heuristica,
                patch(
                    "app.services.grupos.pipeline_worker.atualizar_resultado_heuristica",
                    new_callable=AsyncMock,
                ),
            ):
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=True,
                    score=0.9,
                    keywords_encontradas=["plantão", "hospital"],
                    motivo_rejeicao=None,
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

            with (
                patch(
                    "app.services.grupos.pipeline_worker.calcular_score_heuristica"
                ) as mock_heuristica,
                patch(
                    "app.services.grupos.pipeline_worker.atualizar_resultado_heuristica",
                    new_callable=AsyncMock,
                ),
            ):
                mock_heuristica.return_value = ResultadoHeuristica(
                    passou=True, score=0.5, keywords_encontradas=["vaga"], motivo_rejeicao=None
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

            with (
                patch("app.services.grupos.pipeline_worker.classificar_com_llm") as mock_llm,
                patch(
                    "app.services.grupos.pipeline_worker.atualizar_resultado_classificacao_llm",
                    new_callable=AsyncMock,
                ),
            ):
                mock_llm.return_value = ResultadoClassificacaoLLM(
                    eh_oferta=True, confianca=0.85, motivo="Contém palavras-chave de oferta"
                )

                resultado = await pipeline.processar_classificacao(
                    {"mensagem_id": str(mensagem_id)}
                )

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

            with (
                patch("app.services.grupos.pipeline_worker.classificar_com_llm") as mock_llm,
                patch(
                    "app.services.grupos.pipeline_worker.atualizar_resultado_classificacao_llm",
                    new_callable=AsyncMock,
                ),
            ):
                mock_llm.return_value = ResultadoClassificacaoLLM(
                    eh_oferta=False, confianca=0.2, motivo="Cumprimento genérico"
                )

                resultado = await pipeline.processar_classificacao(
                    {"mensagem_id": str(mensagem_id)}
                )

                assert resultado.acao == "descartar"
                assert resultado.motivo == "nao_eh_oferta"


class TestPipelineProcessarExtracao:
    """Testes do estágio extração (v2)."""

    @pytest.fixture
    def pipeline(self):
        """Cria instância do pipeline."""
        return PipelineGrupos()

    @pytest.mark.asyncio
    async def test_extracao_v2_sucesso(self, pipeline):
        """Extração v2 bem-sucedida."""
        from datetime import date

        mensagem_id = uuid4()
        vaga_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "texto": "Plantão Hospital São Luiz",
                    "nome_grupo": "Vagas",
                    "grupo_id": str(uuid4()),
                    "sender_nome": "Escalista",
                }
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(vaga_id)}]
            )

            with patch("app.services.grupos.pipeline_worker.extrair_vagas_v2") as mock_extrator:
                mock_extrator.return_value = ResultadoExtracaoV2(
                    vagas=[
                        VagaAtomica(
                            data=date(2026, 3, 15),
                            dia_semana=DiaSemana.SEGUNDA,
                            periodo=Periodo.DIURNO,
                            valor=2500,
                            hospital_raw="São Luiz",
                            especialidade_raw="Clínica Médica",
                        )
                    ],
                    total_vagas=1,
                )

                resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "normalizar"
                assert len(resultado.vagas_criadas) == 1

    @pytest.mark.asyncio
    async def test_extracao_v2_falha(self, pipeline):
        """Extração v2 sem vagas."""
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "texto": "Texto confuso",
                    "nome_grupo": "Vagas",
                    "grupo_id": str(uuid4()),
                }
            )

            with patch("app.services.grupos.pipeline_worker.extrair_vagas_v2") as mock_extrator:
                mock_extrator.return_value = ResultadoExtracaoV2(
                    erro="nao_eh_vaga", vagas=[], total_vagas=0
                )

                resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "descartar"


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
                status="normalizada",
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
                duplicada=False, principal_id=None, hash_dedup="abc123"
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
                duplicada=True, principal_id=vaga_principal_id, hash_dedup="abc123"
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
                vaga_id=str(vaga_id),
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
                motivo="confianca_media",
            )

            resultado = await pipeline.processar_importacao({"vaga_grupo_id": str(vaga_grupo_id)})

            assert resultado.acao == "finalizar"
            assert resultado.detalhes["acao"] == "revisar"


# =============================================================================
# Testes do Fan-out Cap
# =============================================================================


class TestFanOutCap:
    """Testes do limite de vagas por mensagem."""

    def test_max_vagas_configurado(self):
        """MAX_VAGAS_POR_MENSAGEM deve ter valor razoável."""
        assert MAX_VAGAS_POR_MENSAGEM > 0
        assert MAX_VAGAS_POR_MENSAGEM == 20

    @pytest.mark.asyncio
    async def test_extracao_v2_respeita_cap(self):
        """Extração v2 deve limitar vagas ao MAX_VAGAS_POR_MENSAGEM."""
        from datetime import date

        mensagem_id = uuid4()
        pipeline = PipelineGrupos()

        # Gerar mais vagas que o limite
        n_vagas = MAX_VAGAS_POR_MENSAGEM + 10
        vagas = [
            VagaAtomica(
                data=date(2026, 3, 15),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.DIURNO,
                valor=2000,
                hospital_raw=f"Hospital {i}",
                especialidade_raw="Clínica Médica",
            )
            for i in range(n_vagas)
        ]

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "texto": "Muitas vagas",
                    "nome_grupo": "Vagas",
                    "grupo_id": str(uuid4()),
                }
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(uuid4())}]
            )

            with patch("app.services.grupos.pipeline_worker.extrair_vagas_v2") as mock_extrator:
                mock_extrator.return_value = ResultadoExtracaoV2(vagas=vagas, total_vagas=n_vagas)

                resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "normalizar"
                assert len(resultado.vagas_criadas) == MAX_VAGAS_POR_MENSAGEM

    @pytest.mark.asyncio
    async def test_extracao_dentro_do_cap_nao_trunca(self):
        """Extração com poucas vagas não deve truncar."""
        from datetime import date

        mensagem_id = uuid4()
        pipeline = PipelineGrupos()

        vagas = [
            VagaAtomica(
                data=date(2026, 3, 15),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.DIURNO,
                valor=2000,
                hospital_raw="Hospital A",
                especialidade_raw="Clínica Médica",
            )
            for _ in range(3)
        ]

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "texto": "Poucas vagas",
                    "nome_grupo": "Vagas",
                    "grupo_id": str(uuid4()),
                }
            )
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": str(uuid4())}]
            )

            with patch("app.services.grupos.pipeline_worker.extrair_vagas_v2") as mock_extrator:
                mock_extrator.return_value = ResultadoExtracaoV2(vagas=vagas, total_vagas=3)

                resultado = await pipeline.processar_extracao({"mensagem_id": str(mensagem_id)})

                assert resultado.acao == "normalizar"
                assert len(resultado.vagas_criadas) == 3


# =============================================================================
# Testes dos helpers compartilhados
# =============================================================================


class TestFetchMensagem:
    """Testes do helper _fetch_mensagem."""

    @pytest.mark.asyncio
    async def test_fetch_retorna_dados(self):
        """Deve retornar dados da mensagem."""
        pipeline = PipelineGrupos()
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"id": str(mensagem_id), "texto": "plantão CM"}
            )

            result = await pipeline._fetch_mensagem(mensagem_id)

            assert result is not None
            assert result["texto"] == "plantão CM"

    @pytest.mark.asyncio
    async def test_fetch_retorna_none_sem_dados(self):
        """Deve retornar None se mensagem não existe."""
        pipeline = PipelineGrupos()
        mensagem_id = uuid4()

        with patch("app.services.grupos.pipeline_worker.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await pipeline._fetch_mensagem(mensagem_id)

            assert result is None


class TestAplicarFanOutCap:
    """Testes do helper _aplicar_fan_out_cap."""

    def test_trunca_quando_excede(self):
        """Deve truncar lista quando excede o limite."""
        pipeline = PipelineGrupos()
        mensagem_id = uuid4()
        vagas = list(range(MAX_VAGAS_POR_MENSAGEM + 5))

        resultado = pipeline._aplicar_fan_out_cap(vagas, mensagem_id)

        assert len(resultado) == MAX_VAGAS_POR_MENSAGEM

    def test_nao_trunca_dentro_do_limite(self):
        """Não deve truncar quando dentro do limite."""
        pipeline = PipelineGrupos()
        mensagem_id = uuid4()
        vagas = list(range(3))

        resultado = pipeline._aplicar_fan_out_cap(vagas, mensagem_id)

        assert len(resultado) == 3

    def test_label_no_log(self):
        """Deve aceitar label para log."""
        pipeline = PipelineGrupos()
        mensagem_id = uuid4()
        vagas = list(range(MAX_VAGAS_POR_MENSAGEM + 1))

        resultado = pipeline._aplicar_fan_out_cap(vagas, mensagem_id, "[v3] ")

        assert len(resultado) == MAX_VAGAS_POR_MENSAGEM


class TestPipelineV3Enabled:
    """Testes da feature flag como constante."""

    def test_pipeline_v3_enabled_eh_bool(self):
        """PIPELINE_V3_ENABLED deve ser booleano."""
        assert isinstance(PIPELINE_V3_ENABLED, bool)

    @pytest.mark.asyncio
    async def test_extracao_usa_v3_quando_habilitado(self):
        """processar_extracao deve chamar v3 quando PIPELINE_V3_ENABLED=True."""
        pipeline = PipelineGrupos()
        item = {"mensagem_id": str(uuid4())}

        with patch.object(pipeline, "processar_extracao_v3", new_callable=AsyncMock) as mock_v3:
            mock_v3.return_value = ResultadoPipeline(acao="normalizar")

            with patch("app.services.grupos.pipeline_worker.PIPELINE_V3_ENABLED", True):
                resultado = await pipeline.processar_extracao(item)

            mock_v3.assert_called_once_with(item)
            assert resultado.acao == "normalizar"

    @pytest.mark.asyncio
    async def test_extracao_usa_v2_quando_desabilitado(self):
        """processar_extracao deve chamar v2 quando PIPELINE_V3_ENABLED=False."""
        pipeline = PipelineGrupos()
        item = {"mensagem_id": str(uuid4())}

        with patch.object(pipeline, "processar_extracao_v2", new_callable=AsyncMock) as mock_v2:
            mock_v2.return_value = ResultadoPipeline(acao="normalizar")

            with patch("app.services.grupos.pipeline_worker.PIPELINE_V3_ENABLED", False):
                resultado = await pipeline.processar_extracao(item)

            mock_v2.assert_called_once_with(item)
            assert resultado.acao == "normalizar"
