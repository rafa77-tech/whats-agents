"""
Testes unitários para a configuração do pipeline (setup.py).

Cobre:
- Todos os processadores esperados estão registrados
- Ordem: opt-out e handoff rodam ANTES do LLM
- Sem processadores duplicados
"""

import pytest

from app.pipeline.setup import criar_pipeline


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pipeline():
    """Pipeline configurado via criar_pipeline()."""
    return criar_pipeline()


# =============================================================================
# Testes: Processadores registrados
# =============================================================================


@pytest.mark.unit
class TestProcessadoresRegistrados:
    """Testes para verificar que todos os processadores esperados estão presentes."""

    def test_pre_processadores_esperados_registrados(self, pipeline):
        """Todos os pre-processadores esperados estão no pipeline."""
        nomes_pre = [p.name for p in pipeline.pre_processors]

        esperados = [
            "ingestao_grupo",
            "parse_message",
            "presence",
            "load_entities",
            "chip_mapping",
            "business_event_inbound",
            "chatwoot_sync",
            "optout",
            "bot_detection",
            "media",
            "long_message",
            "handoff_trigger",
            "handoff_keyword",
            "human_control",
        ]

        for esperado in esperados:
            assert esperado in nomes_pre, f"Pre-processador '{esperado}' não encontrado no pipeline"

    def test_post_processadores_esperados_registrados(self, pipeline):
        """Todos os pós-processadores esperados estão no pipeline."""
        nomes_post = [p.name for p in pipeline.post_processors]

        esperados = [
            "validate_output",
            "timing",
            "send_message",
            "save_interaction",
            "extraction",
            "metrics",
        ]

        for esperado in esperados:
            assert esperado in nomes_post, f"Pós-processador '{esperado}' não encontrado no pipeline"

    def test_core_processor_configurado(self, pipeline):
        """Core processor (LLM) está configurado."""
        assert pipeline._core_processor is not None
        assert pipeline._core_processor.name == "llm_core"

    def test_quantidade_pre_processadores(self, pipeline):
        """Quantidade mínima de pre-processadores registrados."""
        assert len(pipeline.pre_processors) >= 14, (
            f"Esperado >= 14 pre-processadores, encontrado {len(pipeline.pre_processors)}"
        )

    def test_quantidade_post_processadores(self, pipeline):
        """Quantidade mínima de pós-processadores registrados."""
        assert len(pipeline.post_processors) >= 6, (
            f"Esperado >= 6 pós-processadores, encontrado {len(pipeline.post_processors)}"
        )


# =============================================================================
# Testes: Ordenação por prioridade
# =============================================================================


@pytest.mark.unit
class TestOrdenacaoPrioridade:
    """Testes para verificar que processadores críticos rodam na ordem correta."""

    def test_opt_out_roda_antes_do_llm(self, pipeline):
        """OptOutProcessor deve rodar ANTES do LLM (é pre-processador)."""
        nomes_pre = [p.name for p in pipeline.pre_processors]
        assert "optout" in nomes_pre, "optout deve ser pre-processador"

    def test_handoff_roda_antes_do_llm(self, pipeline):
        """HandoffTriggerProcessor deve rodar ANTES do LLM (é pre-processador)."""
        nomes_pre = [p.name for p in pipeline.pre_processors]
        assert "handoff_trigger" in nomes_pre, "handoff_trigger deve ser pre-processador"
        assert "handoff_keyword" in nomes_pre, "handoff_keyword deve ser pre-processador"

    def test_parse_message_roda_antes_de_opt_out(self, pipeline):
        """ParseMessage deve rodar antes de OptOut (precisa do texto parseado)."""
        prioridades = {p.name: p.priority for p in pipeline.pre_processors}

        assert prioridades["parse_message"] < prioridades["optout"], (
            f"parse_message (prio={prioridades['parse_message']}) deve rodar antes de "
            f"opt_out (prio={prioridades['opt_out']})"
        )

    def test_load_entities_roda_antes_de_handoff(self, pipeline):
        """LoadEntities deve rodar antes de HandoffTrigger (precisa dos dados da conversa)."""
        prioridades = {p.name: p.priority for p in pipeline.pre_processors}

        assert prioridades["load_entities"] < prioridades["handoff_trigger"], (
            f"load_entities (prio={prioridades['load_entities']}) deve rodar antes de "
            f"handoff_trigger (prio={prioridades['handoff_trigger']})"
        )

    def test_human_control_roda_por_ultimo_entre_pre(self, pipeline):
        """HumanControl deve ter a maior prioridade (roda por último) entre pre-processadores."""
        prioridades = {p.name: p.priority for p in pipeline.pre_processors}

        assert prioridades["human_control"] == max(prioridades.values()), (
            f"human_control (prio={prioridades['human_control']}) deve ser o último "
            f"pre-processador (max={max(prioridades.values())})"
        )

    def test_validate_output_roda_primeiro_entre_post(self, pipeline):
        """ValidateOutput deve rodar primeiro entre pós-processadores."""
        prioridades = {p.name: p.priority for p in pipeline.post_processors}

        assert prioridades["validate_output"] == min(prioridades.values()), (
            f"validate_output (prio={prioridades['validate_output']}) deve ser o primeiro "
            f"pós-processador (min={min(prioridades.values())})"
        )

    def test_send_message_roda_antes_de_save_interaction(self, pipeline):
        """SendMessage deve rodar antes de SaveInteraction."""
        prioridades = {p.name: p.priority for p in pipeline.post_processors}

        assert prioridades["send_message"] < prioridades["save_interaction"], (
            f"send_message (prio={prioridades['send_message']}) deve rodar antes de "
            f"save_interaction (prio={prioridades['save_interaction']})"
        )

    def test_pre_processadores_ordenados_por_prioridade(self, pipeline):
        """Pre-processadores devem estar ordenados crescentemente por prioridade."""
        prioridades = [p.priority for p in pipeline.pre_processors]
        assert prioridades == sorted(prioridades), (
            f"Pre-processadores fora de ordem: {prioridades}"
        )

    def test_post_processadores_ordenados_por_prioridade(self, pipeline):
        """Pós-processadores devem estar ordenados crescentemente por prioridade."""
        prioridades = [p.priority for p in pipeline.post_processors]
        assert prioridades == sorted(prioridades), (
            f"Pós-processadores fora de ordem: {prioridades}"
        )


# =============================================================================
# Testes: Sem duplicatas
# =============================================================================


@pytest.mark.unit
class TestSemDuplicatas:
    """Testes para verificar que não há processadores duplicados."""

    def test_sem_pre_processadores_duplicados(self, pipeline):
        """Não deve haver pre-processadores com nomes duplicados."""
        nomes = [p.name for p in pipeline.pre_processors]
        duplicados = [n for n in nomes if nomes.count(n) > 1]

        assert len(duplicados) == 0, f"Pre-processadores duplicados: {set(duplicados)}"

    def test_sem_post_processadores_duplicados(self, pipeline):
        """Não deve haver pós-processadores com nomes duplicados."""
        nomes = [p.name for p in pipeline.post_processors]
        duplicados = [n for n in nomes if nomes.count(n) > 1]

        assert len(duplicados) == 0, f"Pós-processadores duplicados: {set(duplicados)}"
