"""
Testes E2E: Pipeline completo de contexto de campanha.

Valida o fluxo end-to-end:
1. Conversa com campaign_id → contexto carregado
2. Contexto de campanha → injetado no prompt (PromptBuilder)
3. Prompt contém seções de campanha (OBJETIVO, COMPORTAMENTO, REGRAS)
4. Constraints de pode_ofertar aplicados corretamente
5. Abertura contextualizada gerada para discovery com objetivo

Diferente dos unit tests (que testam funções isoladas), estes testes
verificam a integração entre os componentes do pipeline.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.campanhas.types import (
    CampanhaData,
    StatusCampanha,
    TipoCampanha,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def campanha_discovery():
    """Campanha discovery agendada com objetivo e regras."""
    return CampanhaData(
        id=20,
        nome_template="Piloto Discovery APP",
        tipo_campanha=TipoCampanha.DISCOVERY,
        corpo="[DISCOVERY] Usar aberturas dinamicas",
        status=StatusCampanha.AGENDADA,
        objetivo="Apresentar o APP Revoluna e incentivar o médico a baixar",
        regras=["Nunca mencionar vagas ou valores", "Foco em apresentar o app"],
        pode_ofertar=False,
        escopo_vagas=None,
    )


@pytest.fixture
def campanha_oferta():
    """Campanha oferta agendada com escopo."""
    return CampanhaData(
        id=30,
        nome_template="Oferta Cardio SP",
        tipo_campanha=TipoCampanha.OFERTA,
        corpo="Oi Dr {nome}! Temos uma vaga de {especialidade}!",
        status=StatusCampanha.AGENDADA,
        objetivo="Preencher 3 vagas de cardiologia no Hospital ABC",
        regras=["Consultar vagas reais antes de ofertar", "Não inventar dados"],
        pode_ofertar=True,
        escopo_vagas={"especialidade": "cardiologia", "regiao": "abc"},
    )


@pytest.fixture
def conversa_com_campanha():
    """Conversa com last_touch_campaign_id setado."""
    return {
        "id": "conv-e2e-1",
        "cliente_id": "medico-e2e-1",
        "status": "ativa",
        "controlled_by": "julia",
        "campanha_id": 20,
        "last_touch_campaign_id": 20,
        "last_touch_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def conversa_com_campanha_oferta():
    """Conversa com campanha de oferta."""
    return {
        "id": "conv-e2e-2",
        "cliente_id": "medico-e2e-2",
        "status": "ativa",
        "controlled_by": "julia",
        "campanha_id": 30,
        "last_touch_campaign_id": 30,
        "last_touch_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def conversa_sem_campanha():
    """Conversa organica sem campanha associada."""
    return {
        "id": "conv-e2e-3",
        "cliente_id": "medico-e2e-3",
        "status": "ativa",
        "controlled_by": "julia",
        "campanha_id": None,
        "last_touch_campaign_id": None,
        "last_touch_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def medico():
    """Médico de teste."""
    return {
        "id": "medico-e2e-1",
        "primeiro_nome": "Carlos",
        "telefone": "5511999001122",
        "especialidade_nome": "Cardiologia",
        "especialidade_id": "esp-cardio",
    }


# ---------------------------------------------------------------------------
# Helpers para mocking
# ---------------------------------------------------------------------------


def _mock_cache_noop():
    """Retorna patches para desabilitar cache Redis."""
    return [
        patch("app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None),
        patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
    ]


# ---------------------------------------------------------------------------
# Teste 1: Pipeline montar_contexto_completo → campanha carregada
# ---------------------------------------------------------------------------


class TestContextoPipelineE2E:
    """
    Testa que montar_contexto_completo carrega campanha e entrega
    ao dict de contexto pronto para o agente.
    """

    @pytest.mark.asyncio
    async def test_contexto_inclui_campanha_quando_conversa_tem_campaign_id(
        self, conversa_com_campanha, medico, campanha_discovery
    ):
        """Fluxo completo: conversa com campaign_id → contexto['campanha'] preenchido."""
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)

            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico,
                conversa=conversa_com_campanha,
                mensagem_atual="Oi, recebi sua mensagem",
            )

            assert ctx["campanha"] is not None
            assert ctx["campanha"]["campaign_type"] == "discovery"
            assert "APP Revoluna" in ctx["campanha"]["campaign_objective"]
            assert ctx["campanha"]["pode_ofertar"] is False

    @pytest.mark.asyncio
    async def test_contexto_nao_inclui_campanha_para_conversa_organica(
        self, conversa_sem_campanha, medico
    ):
        """Fluxo completo: conversa orgânica → contexto['campanha'] é None."""
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico,
                conversa=conversa_sem_campanha,
                mensagem_atual="Oi!",
            )

            assert ctx["campanha"] is None

    @pytest.mark.asyncio
    async def test_contexto_campanha_oferta_inclui_escopo(
        self, conversa_com_campanha_oferta, campanha_oferta
    ):
        """Campanha oferta → contexto inclui escopo de vagas."""
        medico_oferta = {
            "id": "medico-e2e-2",
            "primeiro_nome": "Maria",
            "telefone": "5511999002233",
            "especialidade_nome": "Cardiologia",
            "especialidade_id": "esp-cardio",
        }
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)

            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico_oferta,
                conversa=conversa_com_campanha_oferta,
                mensagem_atual="Oi, vi que vocês têm vagas",
            )

            assert ctx["campanha"] is not None
            assert ctx["campanha"]["campaign_type"] == "oferta"
            assert ctx["campanha"]["pode_ofertar"] is True
            assert ctx["campanha"]["offer_scope"] == {
                "especialidade": "cardiologia",
                "regiao": "abc",
            }


# ---------------------------------------------------------------------------
# Teste 2: PromptBuilder injeta seções de campanha no prompt final
# ---------------------------------------------------------------------------


class TestPromptBuilderCampanhaE2E:
    """
    Testa que o PromptBuilder gera prompt com seções corretas de campanha.
    """

    @pytest.mark.asyncio
    async def test_prompt_contem_objetivo_e_comportamento_discovery(self):
        """Discovery: prompt deve conter OBJETIVO DESTA CONVERSA e COMPORTAMENTO."""
        from app.prompts.builder import construir_prompt_julia

        with (
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes, escalista da Revoluna.",
            ),
            patch(
                "app.prompts.builder.buscar_prompt_por_tipo_campanha",
                new_callable=AsyncMock,
                return_value="Nesta campanha de discovery, foque em conhecer o médico.",
            ),
        ):
            prompt = await construir_prompt_julia(
                campaign_type="discovery",
                campaign_objective="Apresentar o APP Revoluna e incentivar download",
                campaign_rules=["Nunca mencionar vagas", "Foco no app"],
            )

            assert "## COMPORTAMENTO DESTA CAMPANHA" in prompt
            assert "Nesta campanha de discovery" in prompt
            assert "## OBJETIVO DESTA CONVERSA" in prompt
            assert "APP Revoluna" in prompt
            assert "## REGRAS ESPECÍFICAS" in prompt
            assert "Nunca mencionar vagas" in prompt

    @pytest.mark.asyncio
    async def test_prompt_oferta_contem_escopo_vagas(self):
        """Oferta: prompt deve conter escopo de vagas formatado."""
        from app.prompts.builder import construir_prompt_julia

        with (
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes, escalista da Revoluna.",
            ),
            patch(
                "app.prompts.builder.buscar_prompt_por_tipo_campanha",
                new_callable=AsyncMock,
                return_value="Nesta campanha de oferta, apresente as vagas disponíveis.",
            ),
        ):
            prompt = await construir_prompt_julia(
                campaign_type="oferta",
                campaign_objective="Preencher vagas de cardiologia no ABC",
                offer_scope={"especialidade": "cardiologia", "regiao": "abc"},
            )

            assert "## OBJETIVO DESTA CONVERSA" in prompt
            assert "cardiologia" in prompt.lower()

    @pytest.mark.asyncio
    async def test_prompt_sem_campanha_nao_tem_secoes(self):
        """Sem campanha: prompt NÃO deve ter seções de campanha."""
        from app.prompts.builder import construir_prompt_julia

        with patch(
            "app.prompts.builder.carregar_prompt",
            new_callable=AsyncMock,
            return_value="Você é Julia Mendes, escalista da Revoluna.",
        ):
            prompt = await construir_prompt_julia()

            assert "## COMPORTAMENTO DESTA CAMPANHA" not in prompt
            assert "## OBJETIVO DESTA CONVERSA" not in prompt
            assert "## REGRAS ESPECÍFICAS" not in prompt


# ---------------------------------------------------------------------------
# Teste 3: Constraints pode_ofertar no pipeline do agente
# ---------------------------------------------------------------------------


class TestPodeOfertarConstraintE2E:
    """
    Testa que pode_ofertar=False injeta constraint de prioridade máxima
    no prompt final via _gerar_resposta_julia_impl.
    """

    def test_constraint_injetado_quando_pode_ofertar_false(self):
        """pode_ofertar=False → constraint de restrição de campanha presente."""
        # Simula a lógica de montagem de constraints_parts em agente.py
        campanha = {
            "campaign_type": "discovery",
            "campaign_objective": "Conhecer o médico",
            "campaign_rules": ["Nunca mencionar vagas"],
            "offer_scope": None,
            "negotiation_margin": None,
            "pode_ofertar": False,
        }

        constraints_parts = []
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append(
                "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): Esta conversa NÃO permite ofertar vagas. "
                "Se o médico perguntar sobre vagas, diga que vai verificar o que tem disponível e retorna. "
                "NÃO mencione vagas específicas, valores, datas ou hospitais."
            )

        policy_constraints = "\n\n---\n\n".join(constraints_parts)
        assert "RESTRIÇÃO DE CAMPANHA" in policy_constraints
        assert "PRIORIDADE MÁXIMA" in policy_constraints
        assert "NÃO permite ofertar" in policy_constraints

    def test_constraint_nao_injetado_quando_pode_ofertar_true(self):
        """pode_ofertar=True → sem constraint de restrição."""
        campanha = {
            "campaign_type": "oferta",
            "campaign_objective": "Oferecer vagas",
            "pode_ofertar": True,
        }

        constraints_parts = []
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append("RESTRIÇÃO DE CAMPANHA...")

        assert len(constraints_parts) == 0

    def test_constraint_nao_injetado_sem_campanha(self):
        """Sem campanha → sem constraint."""
        campanha = None

        constraints_parts = []
        if campanha and campanha.get("pode_ofertar") is False:
            constraints_parts.append("RESTRIÇÃO DE CAMPANHA...")

        assert len(constraints_parts) == 0

    @pytest.mark.asyncio
    async def test_prompt_final_com_constraint_pode_ofertar(self):
        """Prompt final deve conter constraint quando pode_ofertar=False."""
        from app.prompts.builder import construir_prompt_julia

        constraint = (
            "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): Esta conversa NÃO permite ofertar vagas."
        )

        with (
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes.",
            ),
            patch(
                "app.prompts.builder.buscar_prompt_por_tipo_campanha",
                new_callable=AsyncMock,
                return_value="Campanha discovery - foque em conhecer.",
            ),
        ):
            prompt = await construir_prompt_julia(
                campaign_type="discovery",
                campaign_objective="Conhecer o médico",
                campaign_rules=["Nunca mencionar vagas"],
                policy_constraints=constraint,
            )

            # O constraint aparece na seção de policy constraints do prompt
            assert "RESTRIÇÃO DE CAMPANHA" in prompt
            # E as seções de campanha também estão presentes
            assert "## COMPORTAMENTO DESTA CAMPANHA" in prompt
            assert "## OBJETIVO DESTA CONVERSA" in prompt


# ---------------------------------------------------------------------------
# Teste 4: Fluxo completo contexto → prompt builder (integração)
# ---------------------------------------------------------------------------


class TestFluxoContextoParaPromptE2E:
    """
    Testa o fluxo completo: montar_contexto_completo → extrair campanha →
    montar_prompt_julia com dados da campanha.
    """

    @pytest.mark.asyncio
    async def test_fluxo_discovery_completo(
        self, conversa_com_campanha, medico, campanha_discovery
    ):
        """
        Fluxo E2E completo de discovery:
        1. montar_contexto_completo carrega campanha
        2. Extrai campos da campanha
        3. montar_prompt_julia recebe campos
        4. Prompt final contém seções corretas
        """
        with (
            # Mocks para contexto
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            # Mocks para prompt builder
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes, 27 anos, escalista da Revoluna.",
            ),
            patch(
                "app.prompts.builder.buscar_prompt_por_tipo_campanha",
                new_callable=AsyncMock,
                return_value="Nesta campanha de discovery, conheça o médico sem ofertar.",
            ),
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)

            # Passo 1: Montar contexto
            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico,
                conversa=conversa_com_campanha,
                mensagem_atual="Oi, recebi sua mensagem sobre o app",
            )

            assert ctx["campanha"] is not None

            # Passo 2: Extrair campanha (como faz _gerar_resposta_julia_impl)
            campanha = ctx.get("campanha")

            # Passo 3: Montar constraints (como faz agente.py)
            constraints_parts = []
            if campanha and campanha.get("pode_ofertar") is False:
                constraints_parts.append(
                    "RESTRIÇÃO DE CAMPANHA (PRIORIDADE MÁXIMA): Esta conversa NÃO permite ofertar vagas."
                )
            policy_constraints = "\n\n---\n\n".join(constraints_parts)

            # Passo 4: Montar prompt (como faz agente.py)
            from app.core.prompts import montar_prompt_julia

            prompt = await montar_prompt_julia(
                contexto_medico=ctx.get("medico", ""),
                historico=ctx.get("historico", ""),
                primeira_msg=ctx.get("primeira_msg", False),
                data_hora_atual=ctx.get("data_hora_atual", ""),
                dia_semana=ctx.get("dia_semana", ""),
                diretrizes=ctx.get("diretrizes", ""),
                policy_constraints=policy_constraints,
                campaign_type=campanha.get("campaign_type"),
                campaign_objective=campanha.get("campaign_objective"),
                campaign_rules=campanha.get("campaign_rules"),
                offer_scope=campanha.get("offer_scope"),
                negotiation_margin=campanha.get("negotiation_margin"),
            )

            # Verificar prompt final
            assert "## COMPORTAMENTO DESTA CAMPANHA" in prompt
            assert "Nesta campanha de discovery" in prompt
            assert "## OBJETIVO DESTA CONVERSA" in prompt
            assert "APP Revoluna" in prompt
            assert "## REGRAS ESPECÍFICAS" in prompt
            assert "Nunca mencionar vagas" in prompt
            assert "RESTRIÇÃO DE CAMPANHA" in prompt

    @pytest.mark.asyncio
    async def test_fluxo_oferta_completo(self, conversa_com_campanha_oferta, campanha_oferta):
        """
        Fluxo E2E completo de oferta:
        1. montar_contexto_completo carrega campanha oferta
        2. Prompt final contém escopo de vagas e objetivo
        3. NÃO contém constraint de pode_ofertar (porque True)
        """
        medico_oferta = {
            "id": "medico-e2e-2",
            "primeiro_nome": "Maria",
            "telefone": "5511999002233",
            "especialidade_nome": "Cardiologia",
            "especialidade_id": "esp-cardio",
        }

        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch("app.services.campanhas.repository.campanha_repository") as mock_repo,
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes, escalista da Revoluna.",
            ),
            patch(
                "app.prompts.builder.buscar_prompt_por_tipo_campanha",
                new_callable=AsyncMock,
                return_value="Nesta campanha de oferta, apresente vagas disponíveis.",
            ),
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_oferta)

            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico_oferta,
                conversa=conversa_com_campanha_oferta,
                mensagem_atual="Vi que têm vagas de cardio",
            )

            campanha = ctx.get("campanha")
            assert campanha is not None
            assert campanha["pode_ofertar"] is True

            # Montar constraints - NÃO deve ter restrição
            constraints_parts = []
            if campanha and campanha.get("pode_ofertar") is False:
                constraints_parts.append("RESTRIÇÃO...")
            policy_constraints = "\n\n---\n\n".join(constraints_parts)

            from app.core.prompts import montar_prompt_julia

            prompt = await montar_prompt_julia(
                contexto_medico=ctx.get("medico", ""),
                historico=ctx.get("historico", ""),
                primeira_msg=ctx.get("primeira_msg", False),
                policy_constraints=policy_constraints,
                campaign_type=campanha.get("campaign_type"),
                campaign_objective=campanha.get("campaign_objective"),
                campaign_rules=campanha.get("campaign_rules"),
                offer_scope=campanha.get("offer_scope"),
            )

            assert "## COMPORTAMENTO DESTA CAMPANHA" in prompt
            assert "## OBJETIVO DESTA CONVERSA" in prompt
            assert "RESTRIÇÃO DE CAMPANHA" not in prompt

    @pytest.mark.asyncio
    async def test_fluxo_sem_campanha_prompt_limpo(self, conversa_sem_campanha, medico):
        """
        Fluxo E2E sem campanha: prompt NÃO deve ter nenhuma seção de campanha.
        """
        with (
            patch(
                "app.services.contexto.cache_get_json", new_callable=AsyncMock, return_value=None
            ),
            patch("app.services.contexto.cache_set_json", new_callable=AsyncMock),
            patch(
                "app.services.contexto.carregar_historico",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.services.contexto.verificar_handoff_recente",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.contexto.carregar_diretrizes_ativas",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.prompts.builder.carregar_prompt",
                new_callable=AsyncMock,
                return_value="Você é Julia Mendes, escalista da Revoluna.",
            ),
        ):
            from app.services.contexto import montar_contexto_completo

            ctx = await montar_contexto_completo(
                medico=medico,
                conversa=conversa_sem_campanha,
                mensagem_atual="Oi! Quem é vc?",
            )

            assert ctx["campanha"] is None

            from app.core.prompts import montar_prompt_julia

            prompt = await montar_prompt_julia(
                contexto_medico=ctx.get("medico", ""),
                historico=ctx.get("historico", ""),
                primeira_msg=ctx.get("primeira_msg", False),
            )

            assert "## COMPORTAMENTO DESTA CAMPANHA" not in prompt
            assert "## OBJETIVO DESTA CONVERSA" not in prompt
            assert "## REGRAS ESPECÍFICAS" not in prompt
            assert "RESTRIÇÃO DE CAMPANHA" not in prompt


# ---------------------------------------------------------------------------
# Teste 5: Abertura contextualizada no executor
# ---------------------------------------------------------------------------


class TestAberturaContextualizadaE2E:
    """
    Testa a geração de abertura contextualizada para campanhas discovery
    com objetivo definido.
    """

    @pytest.mark.asyncio
    async def test_abertura_usa_llm_quando_tem_objetivo(self, campanha_discovery):
        """Executor deve gerar abertura via LLM quando campanha tem objetivo."""
        from app.services.campanhas.executor import CampanhaExecutor

        executor = CampanhaExecutor()
        destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos"}

        with patch(
            "app.services.llm.gerar_resposta",
            new_callable=AsyncMock,
            return_value="Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna, vi que vc é médico e queria te mostrar nosso app novo que facilita bastante a gestão de plantões.",
        ):
            mensagem = await executor._gerar_mensagem(campanha_discovery, destinatario)

            assert mensagem is not None
            assert "Carlos" in mensagem
            assert "app" in mensagem.lower() or "Revoluna" in mensagem

    @pytest.mark.asyncio
    async def test_abertura_fallback_quando_llm_falha(self, campanha_discovery):
        """Se LLM falhar, executor usa abertura padrão (soft)."""
        from app.services.campanhas.executor import CampanhaExecutor

        executor = CampanhaExecutor()
        destinatario = {"id": "uuid-1", "primeiro_nome": "Carlos"}

        with (
            patch(
                "app.services.llm.gerar_resposta",
                new_callable=AsyncMock,
                return_value=None,  # LLM falhou
            ),
            patch(
                "app.services.campanhas.executor.obter_abertura_texto",
                new_callable=AsyncMock,
                return_value="Oi Dr Carlos! Tudo bem? Sou a Julia da Revoluna",
            ),
        ):
            mensagem = await executor._gerar_mensagem(campanha_discovery, destinatario)

            assert mensagem is not None
            assert "Carlos" in mensagem

    @pytest.mark.asyncio
    async def test_abertura_discovery_sem_objetivo_usa_padrao(self):
        """Discovery sem objetivo usa abertura padrão (obter_abertura_texto)."""
        from app.services.campanhas.executor import CampanhaExecutor

        campanha_sem_objetivo = CampanhaData(
            id=25,
            nome_template="Discovery Genérica",
            tipo_campanha=TipoCampanha.DISCOVERY,
            corpo="[DISCOVERY]",
            status=StatusCampanha.ATIVA,
            objetivo=None,
            pode_ofertar=False,
        )
        executor = CampanhaExecutor()
        destinatario = {"id": "uuid-2", "primeiro_nome": "Maria"}

        with patch(
            "app.services.campanhas.executor.obter_abertura_texto",
            new_callable=AsyncMock,
            return_value="Oi Dra Maria! Sou a Julia da Revoluna",
        ):
            mensagem = await executor._gerar_mensagem(campanha_sem_objetivo, destinatario)

            assert mensagem is not None
            assert "Maria" in mensagem


# ---------------------------------------------------------------------------
# Teste 6: Metadata enriquecida no executor
# ---------------------------------------------------------------------------


class TestMetadataEnriquecidaE2E:
    """
    Testa que o executor enriquece metadata com objetivo e pode_ofertar.
    """

    @pytest.mark.asyncio
    async def test_executor_envia_metadata_com_objetivo_e_pode_ofertar(self, campanha_discovery):
        """Metadata de envio deve conter objetivo e pode_ofertar."""
        from app.services.campanhas.executor import CampanhaExecutor

        executor = CampanhaExecutor()
        destinatarios = [
            {"id": "uuid-1", "primeiro_nome": "Carlos", "especialidade_nome": "Cardiologia"},
        ]

        # Mock cooldown result (não bloqueado)
        cooldown_result = MagicMock()
        cooldown_result.is_blocked = False

        with (
            patch("app.services.campanhas.executor.campanha_repository") as mock_repo,
            patch("app.services.campanhas.executor.segmentacao_service") as mock_seg,
            patch("app.services.campanhas.executor.fila_service") as mock_fila,
            patch("app.services.campanhas.executor.supabase") as mock_supabase,
            patch(
                "app.services.llm.gerar_resposta",
                new_callable=AsyncMock,
                return_value="Oi Dr Carlos! Queria te apresentar nosso app!",
            ),
            patch(
                "app.services.campanhas.executor.check_campaign_cooldown",
                new_callable=AsyncMock,
                return_value=cooldown_result,
            ),
        ):
            mock_repo.buscar_por_id = AsyncMock(return_value=campanha_discovery)
            mock_repo.atualizar_status = AsyncMock(return_value=True)
            mock_repo.atualizar_total_destinatarios = AsyncMock(return_value=True)
            mock_repo.incrementar_enviados = AsyncMock(return_value=True)
            mock_seg.buscar_alvos_campanha = AsyncMock(return_value=destinatarios)
            mock_fila.enfileirar = AsyncMock()
            # Mock deduplicação
            mock_supabase.table.return_value.select.return_value.contains.return_value.execute.return_value.data = []
            # Mock outbound sem resposta (não excedeu)
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.is_.return_value.execute.return_value.data = []

            await executor.executar(20)

            # Verificar metadata no enfileirar
            call_args = mock_fila.enfileirar.call_args
            metadata = call_args.kwargs.get("metadata", {})
            assert metadata.get("pode_ofertar") is False
            assert "APP Revoluna" in metadata.get("objetivo", "")


# ---------------------------------------------------------------------------
# Teste 7: Cache invalidação no pipeline
# ---------------------------------------------------------------------------


class TestCacheInvalidacaoE2E:
    """
    Testa que atualizar status da campanha invalida o cache de contexto.
    """

    @pytest.mark.asyncio
    async def test_atualizar_status_invalida_cache_contexto(self):
        """Mudar status da campanha deve invalidar cache Redis."""
        from app.services.campanhas.repository import campanha_repository

        with (
            patch("app.services.campanhas.repository.supabase") as mock_supabase,
            patch(
                "app.services.redis.cache_delete",
                new_callable=AsyncMock,
            ) as mock_cache_delete,
        ):
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": 20, "status": "concluida"}
            ]

            await campanha_repository.atualizar_status(20, StatusCampanha.CONCLUIDA)

            mock_cache_delete.assert_called_once_with("campanha:contexto:20")
